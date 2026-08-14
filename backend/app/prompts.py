"""Prompt 模板（文档 §12 Prompt 设计）。

约定：
- system 提示词首部嵌入 `###TASK:XXX###` 标记，供 MockLLM 分支。
- 每个任务都明确给出“只返回 JSON”的约束，以及对应 Schema 字段说明，
  以便 DeepSeek（response_format=json_object）产出可解析结构。
- Agent 任务在 user 中注入 `[ROLE:key]`，供 Mock 识别当前角色。
"""
from __future__ import annotations

import json
from typing import Dict, List

from .roles import ROLES, Role
from .schemas import ProblemContext, AgentOpinion, ModeratorReport, to_dict

_JSON_ORDER = "只输出 JSON，不要包含任何解释性文字、不要使用 markdown 代码块围栏。"


def _ctx_text(ctx: Dict) -> str:
    return json.dumps(ctx, ensure_ascii=False, indent=2)


# ----------------------------- 1. Context Builder -----------------------------

def context_builder(problem_text: str):
    system = (
        "###TASK:CONTEXT_BUILDER###\n"
        "你是议会『会前调查部门』（Problem Discovery Engine）。用户提出一个模糊的困惑，"
        "你需要：(1) 识别表面问题；(2) 推测潜在问题；(3) 列出背景信息缺口；(4) 判断哪些缺失"
        "信息会影响决策。不要急于给答案，先把问题结构化。\n"
        + _JSON_ORDER + "\n"
        "返回 JSON 字段（ProblemContext）：\n"
        "problem{statement,surface,underlying}, user_background{}, current_situation{}, "
        "constraints{}, goals[], concerns[], unknowns[], gaps[], ready_for_council(bool)"
    )
    user = f"用户的困惑原文：\n{problem_text}"
    return system, user


# ----------------------------- 2. Role Questions -----------------------------

def role_questions(ctx: ProblemContext, problem_text: str):
    system = (
        "###TASK:ROLE_QUESTIONS###\n"
        "你是议会调度器。基于当前 Problem Context，让每个角色从自身立场提出"
        "最需要向用户澄清的 1~2 个问题。问题要有角色归属、理由与重要级。"
        "避免重复提问。\n" + _JSON_ORDER + "\n"
        "返回 JSON：{\"questions\":[{question_id, asked_by, question, reason, importance}]}"
    )
    roles_block = "\n".join(
        f"- {r.name}（{r.key}）：目标={r.goal}；参考问题={ ' / '.join(r.example_questions) }"
        for r in ROLES
    )
    user = (
        f"原始困惑：{problem_text}\n\n"
        f"当前 Problem Context：\n{_ctx_text(to_dict(ctx))}\n\n"
        f"可用角色：\n{roles_block}"
    )
    return system, user


# ----------------------------- 3. Context Build (update) -----------------------------

def context_build(prev_ctx: ProblemContext, answers_text: str, questions: List[Dict]):
    system = (
        "###TASK:CONTEXT_BUILD###\n"
        "你负责把『用户的新回答』合并进上一版 Problem Context，形成新版本（动态 Context）。"
        "补充已知事实、缩小 unknowns、更新 gaps。\n" + _JSON_ORDER + "\n"
        "返回完整 ProblemContext JSON（同 CONTEXT_BUILDER 的结构）。"
    )
    q_block = "\n".join(f"- [{q.get('asked_by')}] {q.get('question')}" for q in questions)
    user = (
        f"上一版 Context：\n{_ctx_text(to_dict(prev_ctx))}\n\n"
        f"本轮各角色提出的问题：\n{q_block}\n\n"
        f"用户回答：\n{answers_text}"
    )
    return system, user


# ----------------------------- 4. Agent Opinion (sequential) -----------------------------

def agent_opinion(role: Role, problem_text: str, ctx: ProblemContext,
                  prior_opinions: List[AgentOpinion]):
    system = (
        f"###TASK:AGENT_OPINION###\n"
        f"你是议会中的「{role.name}」。核心目标：{role.goal}\n"
        f"你的立场：{role.stance}\n"
        "重要：后发言的角色必须阅读前面角色的观点，并明确回应/修正/质疑它们；"
        "若你判断自己没有新增信息，可返回 skipped=true 而不要强行发言。\n"
        + _JSON_ORDER + "\n"
        "返回 JSON（Opinion）：{role, role_name, type:'opinion', skipped, position, reasoning, "
        "supporting_points[], concerns[], counterarguments[], missing_information[], recommendations[]}"
    )
    prior_block = "\n\n".join(o.to_prompt_block() for o in prior_opinions) or "（你是第一个发言者，无前置观点）"
    user = (
        f"[ROLE:{role.key}]\n"
        f"用户原始困惑：{problem_text}\n\n"
        f"当前 Problem Context：\n{_ctx_text(to_dict(ctx))}\n\n"
        f"前面角色的观点（你必须基于这些内容继续思考）：\n{prior_block}"
    )
    return system, user


# ----------------------------- 5. Cross Examination -----------------------------

def cross_exam(problem_text: str, ctx: ProblemContext, opinions: List[AgentOpinion]):
    system = (
        "###TASK:CROSS_EXAM###\n"
        "进入集中质询（Cross Examination）。只关注：分歧、漏洞、未验证假设、关键风险、信息缺口。"
        "不要重新回答完整问题，最多形成 3~5 条尖锐质询。\n" + _JSON_ORDER + "\n"
        "返回 JSON：{\"points\":[string, ...]}"
    )
    op_block = "\n\n".join(o.to_prompt_block() for o in opinions)
    user = (
        f"用户困惑：{problem_text}\n\n"
        f"Context：\n{_ctx_text(to_dict(ctx))}\n\n"
        f"各角色观点：\n{op_block}"
    )
    return system, user


# ----------------------------- 6. Moderator -----------------------------

def moderator(problem_text: str, ctx: ProblemContext, opinions: List[AgentOpinion],
              cross_points: List[str]):
    system = (
        "###TASK:MODERATOR###\n"
        "你是 Moderator。不要机械罗列每个角色，必须回答以下 7 个问题：\n"
        "1) 真正讨论的是什么（表面 vs 真实）；2) 哪些已确定（事实）；3) 哪些只是推测；"
        "4) 真正的分歧在哪里（为什么不同）；5) 还缺什么信息；6) 当前有哪些选择；"
        "7) 下一步最值得做什么（未来3/7/30天）。\n"
        "若发现关键事实无法判断，设置 need_clarification=true 并在 clarification_questions 给出要问用户的问题。\n"
        + _JSON_ORDER + "\n"
        "返回 JSON（ModeratorReport）：real_question{surface,underlying}, facts[], speculations[], "
        "disagreements[], missing_information[], options[{name,desc}], risks[], "
        "next_steps{d3[],d7[],d30[]}, need_clarification(bool), clarification_questions[]"
    )
    op_block = "\n\n".join(o.to_prompt_block() for o in opinions)
    user = (
        f"用户困惑：{problem_text}\n\n"
        f"Context：\n{_ctx_text(to_dict(ctx))}\n\n"
        f"各角色观点：\n{op_block}\n\n"
        f"质询要点：\n" + ("\n".join(f"- {p}" for p in cross_points) or "（无）")
    )
    return system, user


# ----------------------------- 7. Action Plan + Review -----------------------------

def action_plan(moderator_report: ModeratorReport):
    system = (
        "###TASK:ACTION_PLAN###\n"
        "基于 Moderator 的结论，输出可执行的 Action Plan 与一次复盘提示。\n" + _JSON_ORDER + "\n"
        "返回 JSON：{d3[], d7[], d30[], review_prompt}"
    )
    user = f"Moderator 结论：\n{_ctx_text(to_dict(moderator_report))}"
    return system, user
