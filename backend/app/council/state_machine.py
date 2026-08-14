"""议会状态机 / Orchestrator（文档 §16、§17）。

状态流转：
INIT -> WAITING_ANSWERS -> (COUNCIL_DISCUSSION -> CROSS_EXAM -> MODERATOR)
  -> 若需澄清: WAITING_CLARIFICATION -> 回到议会讨论
  -> 否则: COMPLETED（Action Plan + Review）

关键设计（对应文档核心变化）：
- 先问清楚（Role Questioning），再讨论；
- 角色顺序发言，后一个读取前面观点（Sequential Council）；
- 角色可 SKIP（无新增则不强行发言）；
- Moderator 发现重大信息缺失时可再次询问用户。
"""
from __future__ import annotations

import json
from dataclasses import fields
from typing import Any, Dict, List, Optional

from .. import db as dbmod
from .. import prompts as P
from .. import roles as R
from ..llm import BaseLLM, LLMError
from ..schemas import (ProblemContext, AgentOpinion, ModeratorReport,
                       ActionPlan, to_dict)

# 状态常量
S_INIT = "INIT"
S_WAITING_ANSWERS = "WAITING_ANSWERS"
S_WAITING_CLARIFICATION = "WAITING_CLARIFICATION"
S_COMPLETED = "COMPLETED"


def _from_dict(cls, d: Dict[str, Any]):
    """把 LLM 返回的字典安全地转成 dataclass（忽略多余/缺失字段）。"""
    if d is None:
        d = {}
    valid = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in d.items() if k in valid}
    return cls(**kwargs)


class CouncilOrchestrator:
    def __init__(self, llm: BaseLLM, repo: dbmod.Repository):
        self.llm = llm
        self.repo = repo

    # ---------------- 对外 API ----------------

    def create_session(self) -> str:
        return self.repo.create_session(S_INIT)

    def get_detail(self, sid: str) -> Optional[Dict]:
        sess = self.repo.get_session(sid)
        if not sess:
            return None
        msgs = self.repo.get_messages(sid)
        # 结构化消息的内容反序列化为对象，方便前端直接使用
        for m in msgs:
            kind = (m.get("metadata") or {}).get("kind")
            if kind in ("role_questions", "agent", "cross_exam", "moderator", "action_plan", "clarification"):
                try:
                    m["content"] = json.loads(m["content"]) if isinstance(m["content"], str) else m["content"]
                except (json.JSONDecodeError, TypeError):
                    pass
        return {"session": sess, "messages": msgs}

    def send(self, sid: str, text: str) -> Dict:
        """处理一条用户消息，推进状态机，返回 {state, messages:[新消息]}。"""
        sess = self.repo.get_session(sid)
        if not sess:
            raise ValueError(f"会话不存在：{sid}")
        state = sess["current_state"]
        events: List[Dict] = []

        if state == S_INIT:
            self._handle_init(sid, text, events)
        elif state == S_WAITING_ANSWERS:
            self._handle_answers(sid, text, events, clarification=False)
        elif state == S_WAITING_CLARIFICATION:
            self._handle_answers(sid, text, events, clarification=True)
        elif state == S_COMPLETED:
            # 已完成后仍允许追加发言：当作新的补充，重新进入讨论
            self._handle_answers(sid, text, events, clarification=True)
        else:
            raise ValueError(f"未知状态：{state}")

        new_state = self.repo.get_session(sid)["current_state"]
        return {"state": new_state, "messages": events}

    # ---------------- 各状态处理 ----------------

    def _emit(self, events: List[Dict], sid: str, sender: str, content,
              phase: Optional[str], metadata: Optional[Dict]) -> None:
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        mid = self.repo.add_message(sid, sender, content, phase, metadata)
        # 回放一条供前端使用（结构化内容还原为对象）
        kind = (metadata or {}).get("kind")
        disp = content
        if kind in ("role_questions", "agent", "cross_exam", "moderator", "action_plan", "clarification"):
            try:
                disp = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass
        events.append({"id": mid, "sender": sender, "phase": phase,
                       "content": disp, "metadata": metadata or {}})

    def _handle_init(self, sid: str, text: str, events: List[Dict]) -> None:
        self._emit(events, sid, "user", text, "problem", {})
        # 1) Context Builder
        ctx_dict = self._call(P.context_builder(text))
        self.repo.save_context(sid, 1, ctx_dict)
        ctx = _from_dict(ProblemContext, ctx_dict)
        # 2) Role Questions
        q_dict = self._call(P.role_questions(ctx, text))
        questions = q_dict.get("questions", [])
        self.repo.save_questions(sid, questions)
        # 3) 给用户呈现：上下文摘要 + 角色提问
        self._emit(events, sid, "system", ctx.summary_text(), "context", {"kind": "system"})
        self._emit(events, sid, "system", questions, "role_questions",
                   {"kind": "role_questions"})
        self.repo.update_state(sid, S_WAITING_ANSWERS)

    def _handle_answers(self, sid: str, text: str, events: List[Dict],
                        clarification: bool) -> None:
        self._emit(events, sid, "user", text, "answers", {})
        # 标记待回答的问题为已答（MVP：整段回复作为背景补充）
        qs = self.repo.get_questions(sid)
        open_qs = [{"question_id": q["question_id"], "answer": text} for q in qs if not q["answered"]]
        if open_qs:
            self.repo.answer_questions(sid, open_qs)
        # 更新 Context（动态版本）
        prev = self.repo.get_latest_context(sid)
        prev_ctx = _from_dict(ProblemContext, prev["data"]) if prev else ProblemContext()
        new_ctx_dict = self._call(P.context_build(prev_ctx, text, qs))
        new_version = (prev["version"] + 1) if prev else 2
        self.repo.save_context(sid, new_version, new_ctx_dict)
        new_ctx = _from_dict(ProblemContext, new_ctx_dict)
        self._emit(events, sid, "system", new_ctx.summary_text(), "context", {"kind": "system"})
        # 重新跑议会（讨论 -> 质询 -> Moderator）
        self._run_council(sid, new_ctx, events)

    def _run_council(self, sid: str, ctx: ProblemContext, events: List[Dict]) -> None:
        problem_text = ctx.problem.get("statement", "")
        opinions: List[AgentOpinion] = []
        for role in R.ROLES:
            op_dict = self._call(P.agent_opinion(role, problem_text, ctx, opinions))
            op = _from_dict(AgentOpinion, op_dict)
            if not op.role_name:
                op.role_name = R.role_name(op.role)
            opinions.append(op)
            self._emit(events, sid, "agent", to_dict(op), "council",
                       {"kind": "agent", "role": op.role, "role_name": op.role_name,
                        "skipped": op.skipped})
        # Cross Examination
        ce_dict = self._call(P.cross_exam(problem_text, ctx, opinions))
        ce_points = ce_dict.get("points", [])
        self._emit(events, sid, "system", ce_points, "cross_exam", {"kind": "cross_exam"})
        # Moderator
        mr_dict = self._call(P.moderator(problem_text, ctx, opinions, ce_points))
        mr = _from_dict(ModeratorReport, mr_dict)
        self._emit(events, sid, "moderator", to_dict(mr), "moderator", {"kind": "moderator"})
        # 是否需要继续向用户澄清
        if mr.need_clarification and mr.clarification_questions:
            self.repo.update_state(sid, S_WAITING_CLARIFICATION)
            self._emit(events, sid, "system", mr.clarification_questions, "clarification",
                       {"kind": "clarification"})
        else:
            self._finalize(sid, mr, events)

    def _finalize(self, sid: str, mr: ModeratorReport, events: List[Dict]) -> None:
        ap_dict = self._call(P.action_plan(mr))
        ap = _from_dict(ActionPlan, ap_dict)
        self._emit(events, sid, "system", to_dict(ap), "action_plan", {"kind": "action_plan"})
        self._emit(events, sid, "system", ap.review_prompt or "一个月后回来复盘你的判断变化。",
                   "review", {"kind": "system"})
        self.repo.update_state(sid, S_COMPLETED)

    # ---------------- LLM 调用（统一异常处理） ----------------

    def _call(self, prompt_pair) -> Dict[str, Any]:
        system, user = prompt_pair
        try:
            return self.llm.structured(system, user)
        except LLMError as e:
            # 让调用方感知，但避免整个会话崩溃；返回最小可用结构
            return {"error": str(e)}
