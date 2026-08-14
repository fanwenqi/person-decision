"""LLM 抽象层。

- BaseLLM：统一接口 structured(system, user) -> dict
- MockLLM：确定性结构化输出，用于自测 / 无 key 场景
- DeepSeekLLM：OpenAI 兼容接口，使用标准库 urllib 调用，无需 requests

MockLLM 通过识别 system 提示词中的 `###TASK:XXX###` 标记来分支，
保证在没有真实模型时也能产出符合 Schema 的结构化结果，使端到端自测可跑通。
"""
from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict

from . import config as cfg


class LLMError(Exception):
    pass


def parse_json(text: str) -> Dict[str, Any]:
    """容错解析：去掉 ```json 代码块、取首个 { 到末个 } 的内容。"""
    if text is None:
        raise LLMError("LLM 返回为空")
    s = text.strip()
    # 去掉 markdown 代码块围栏
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s, flags=re.IGNORECASE)
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMError(f"无法从 LLM 输出中解析 JSON：{text[:200]}")
    try:
        return json.loads(s[start:end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"JSON 解析失败：{e} | 原文前 200 字符：{text[:200]}")


def _extract_task(system: str) -> str:
    m = re.search(r"###TASK:([A-Z_]+)###", system)
    return m.group(1) if m else ""


def _snippet(text: str, n: int = 40) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[:n] + ("…" if len(text) > n else "")


class BaseLLM:
    def structured(self, system: str, user: str) -> Dict[str, Any]:
        raise NotImplementedError


class MockLLM(BaseLLM):
    """确定性 Mock：根据 TASK 标记返回符合各 Schema 的结构化数据。"""

    def structured(self, system: str, user: str) -> Dict[str, Any]:
        task = _extract_task(system)
        if task == "CONTEXT_BUILDER":
            return self._context_builder(user)
        if task == "ROLE_QUESTIONS":
            return self._role_questions(user)
        if task == "CONTEXT_BUILD":
            return self._context_build(user)
        if task == "AGENT_OPINION":
            return self._agent_opinion(user)
        if task == "CROSS_EXAM":
            return self._cross_exam(user)
        if task == "MODERATOR":
            return self._moderator(user)
        if task == "ACTION_PLAN":
            return self._action_plan(user)
        return {"note": "mock-unknown-task"}

    # ---- 各任务的具体 Mock 实现 ----

    def _context_builder(self, user: str) -> Dict[str, Any]:
        prob = _snippet(user, 60)
        return {
            "problem": {
                "statement": prob,
                "surface": "用户表达了关于职业/人生方向的困惑",
                "underlying": "真正需要确认的是：是否应在信息不足时贸然做重大改变",
            },
            "user_background": {"age": "未知", "experience": "未知"},
            "current_situation": {"job": "用户描述中存在不确定性", "motivation": "希望找到更清晰的方向"},
            "constraints": {},
            "goals": ["获得更清晰的决策依据"],
            "concerns": ["担心做出错误选择", "担心错过时机"],
            "unknowns": ["真实收入与储备", "现有能力是否匹配目标", "具体目标岗位"],
            "gaps": [
                "用户的年龄与从业经验",
                "当前收入与现金储备（现实约束）",
                "是否已有相关尝试/项目经验",
                "不行动的最坏后果是什么",
            ],
            "ready_for_council": False,
        }

    def _role_questions(self, user: str) -> Dict[str, Any]:
        # 每个角色各出 1~2 个代表性问题（确定性，便于自测断言）
        questions = [
            {"asked_by": "understander", "question": "你为什么会产生这个想法？它持续多久了？",
             "reason": "区分一时情绪与长期诉求", "importance": "high"},
            {"asked_by": "supporter", "question": "现状中让你长期消耗的是什么？",
             "reason": "识别真正值得改变的部分", "importance": "medium"},
            {"asked_by": "opponent", "question": "你有什么证据支撑“这个选择能解决问题”的判断？",
             "reason": "检验核心假设", "importance": "high"},
            {"asked_by": "realist", "question": "当前月收入与固定支出分别是多少？有多少个月现金储备？",
             "reason": "评估经济安全边际", "importance": "high"},
            {"asked_by": "strategist", "question": "如果解决当前问题，你最终希望获得什么？能否先低成本验证？",
             "reason": "明确目标与验证路径", "importance": "medium"},
        ]
        out = []
        for i, q in enumerate(questions, 1):
            out.append({
                "question_id": f"Q-{i:03d}",
                "answered": False,
                "answer": "",
                **q,
            })
        return {"questions": out}

    def _context_build(self, user: str) -> Dict[str, Any]:
        # user 包含上一版 context + 用户回答；这里做确定性合并
        return {
            "problem": {"statement": "是否应在补齐信息后做重大改变",
                        "surface": "职业/方向困惑", "underlying": "低风险验证 vs 直接行动"},
            "user_background": {"note": "已根据回答补充"},
            "current_situation": {"note": "已根据回答补充"},
            "constraints": {"note": "已根据回答补充现实约束"},
            "goals": ["明确下一步方向", "控制决策风险"],
            "concerns": ["决策错误", "错过时机"],
            "unknowns": ["验证结果"],

            "gaps": ["仍需低成本验证"],
            "ready_for_council": True,
        }

    def _agent_opinion(self, user: str) -> Dict[str, Any]:
        # 从 prompt 里取角色名（prompts 会注入 [ROLE:xxx] 标记）
        rm = re.search(r"\[ROLE:([a-z]+)\]", user)
        key = rm.group(1) if rm else "understander"
        names = {"understander": "理解者", "supporter": "支持者", "opponent": "反方",
                 "realist": "现实主义者", "strategist": "战略顾问"}
        return {
            "role": key,
            "role_name": names.get(key, key),
            "type": "opinion",
            "skipped": False,
            "position": f"[{names.get(key,key)}] 基于现有信息，建议先补齐关键约束再做判断。",
            "reasoning": "当前信息尚未完全覆盖现实约束与核心假设，过早下结论风险较高。",
            "supporting_points": ["用户已意识到需要更清晰的方向"],
            "concerns": ["关键现实数据仍缺失"],
            "counterarguments": ["直接行动可能建立在未验证的假设上"],
            "missing_information": ["收入/储备", "已有尝试"],
            "recommendations": ["先做一次低成本验证"],
        }

    def _cross_exam(self, user: str) -> Dict[str, Any]:
        return {
            "points": [
                "反方：'该选择能解决问题'这一假设仍缺少证据。",
                "现实主义者：目前经济安全边际尚未被充分讨论，不宜裸辞。",
                "战略顾问：但这不意味着维持现状，可先验证目标方向。",
            ]
        }

    def _moderator(self, user: str) -> Dict[str, Any]:
        return {
            "real_question": {"surface": "是否做出某个重大改变",
                               "underlying": "如何在信息不足时低风险地验证方向"},
            "facts": ["用户已表达明确困惑", "部分现实约束已补充"],
            "speculations": ["目标方向一定适合用户"],
            "disagreements": ["是否应直接行动 vs 先验证存在分歧"],
            "missing_information": ["验证结果尚未产生"],
            "options": [
                {"name": "Option A", "desc": "直接行动（高风险）"},
                {"name": "Option B", "desc": "先低成本验证（推荐）"},
                {"name": "Option C", "desc": "维持现状并持续观察"},
            ],
            "risks": ["裸辞带来的现金流风险", "方向误判的时间成本"],
            "next_steps": {
                "d3": ["列出可用于验证的最小行动"],
                "d7": ["完成一次低成本验证尝试"],
                "d30": ["根据验证结果决定是否加大投入"],
            },
            "need_clarification": False,
            "clarification_questions": [],
        }

    def _action_plan(self, user: str) -> Dict[str, Any]:
        return {
            "d3": ["明确可用于低成本验证的最小动作"],
            "d7": ["执行一次验证并收集反馈"],
            "d30": ["依据反馈决定是否追加投入"],
            "review_prompt": "一个月后回顾：验证是否改变了你原来的判断？",
        }


class DeepSeekLLM(BaseLLM):
    """DeepSeek（OpenAI 兼容）。使用 urllib，零额外依赖。"""

    def __init__(self, settings: cfg.Settings):
        self.settings = settings

    def structured(self, system: str, user: str) -> Dict[str, Any]:
        url = self.settings.deepseek_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.deepseek_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            raise LLMError(f"DeepSeek HTTP {e.code}: {body[:300]}")
        except urllib.error.URLError as e:
            raise LLMError(f"DeepSeek 连接失败：{e.reason}")
        try:
            parsed = json.loads(raw)
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise LLMError(f"DeepSeek 返回结构异常：{e} | {raw[:200]}")
        return parse_json(content)


def build_llm(settings: cfg.Settings) -> BaseLLM:
    if settings.llm_provider == "deepseek" and settings.deepseek_api_key:
        return DeepSeekLLM(settings)
    return MockLLM()
