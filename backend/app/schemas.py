"""核心数据结构定义（对应文档 §5 / §24 的 Schema 设计）。

所有结构都用标准库 dataclass 描述，序列化时统一转 dict，
避免引入额外依赖，保证 Mock 自测可脱离第三方包运行。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


def to_dict(obj) -> Any:
    """递归把 dataclass / 列表 / 字典转成可 JSON 序列化的结构。"""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    return obj


@dataclass
class ProblemContext:
    """Problem Context Schema（文档 §5、§6 动态版本）。"""
    problem: Dict[str, str] = field(default_factory=lambda: {
        "statement": "", "surface": "", "underlying": ""
    })
    user_background: Dict[str, Any] = field(default_factory=dict)
    current_situation: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)          # 背景信息缺口
    ready_for_council: bool = False

    def summary_text(self) -> str:
        lines = []
        p = self.problem
        if p.get("statement"):
            lines.append(f"问题陈述：{p['statement']}")
        if p.get("underlying"):
            lines.append(f"潜在问题：{p['underlying']}")
        if self.user_background:
            lines.append("用户背景：" + "；".join(f"{k}={v}" for k, v in self.user_background.items()))
        if self.constraints:
            lines.append("现实约束：" + "；".join(f"{k}={v}" for k, v in self.constraints.items()))
        if self.goals:
            lines.append("目标：" + "、".join(self.goals))
        if self.concerns:
            lines.append("顾虑：" + "、".join(self.concerns))
        if self.gaps:
            lines.append("已知信息缺口：" + "、".join(self.gaps))
        return "\n".join(lines) if lines else "（暂无结构化背景）"


@dataclass
class RoleQuestion:
    """Role Question Schema（文档 §11）。"""
    question_id: str
    asked_by: str
    question: str
    reason: str = ""
    importance: str = "medium"   # high | medium | low
    answered: bool = False
    answer: str = ""

    def to_prompt_block(self) -> str:
        return f"[{self.asked_by} | {self.importance}] {self.question}（为什么想知道：{self.reason}）"


@dataclass
class AgentOpinion:
    """Agent Opinion Schema（文档 §10 Opinion）。"""
    role: str
    role_name: str = ""
    type: str = "opinion"
    skipped: bool = False
    position: str = ""
    reasoning: str = ""
    supporting_points: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    counterarguments: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        if self.skipped:
            return f"【{self.role_name}】：（本轮无新增观点，跳过）"
        parts = [f"【{self.role_name}】立场：{self.position}",
                 f"推理：{self.reasoning}"]
        if self.concerns:
            parts.append("顾虑：" + "；".join(self.concerns))
        if self.counterarguments:
            parts.append("反驳/质疑：" + "；".join(self.counterarguments))
        if self.recommendations:
            parts.append("建议：" + "；".join(self.recommendations))
        return "\n".join(parts)


@dataclass
class ModeratorReport:
    """Moderator Schema（文档 §14，必须回答 7 个问题）。"""
    real_question: Dict[str, str] = field(default_factory=lambda: {"surface": "", "underlying": ""})
    facts: List[str] = field(default_factory=list)
    speculations: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    options: List[Dict[str, str]] = field(default_factory=list)   # {"name","desc"}
    risks: List[str] = field(default_factory=list)
    next_steps: Dict[str, List[str]] = field(default_factory=lambda: {"d3": [], "d7": [], "d30": []})
    need_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        lines = [
            "我们真正讨论的（表面 vs 真实）：" + self.real_question.get("surface", "")
            + " / " + self.real_question.get("underlying", ""),
            "已确定的事实：" + "；".join(self.facts),
            "仍属推测：" + "；".join(self.speculations),
            "真正的分歧：" + "；".join(self.disagreements),
            "信息不足：" + "；".join(self.missing_information),
            "可选方案：" + "；".join(f"{o.get('name','')}: {o.get('desc','')}" for o in self.options),
            "风险：" + "；".join(self.risks),
        ]
        return "\n".join(lines)


@dataclass
class ActionPlan:
    """Action Plan + Review Schema（文档 §17、§23 的 Action/Review）。"""
    d3: List[str] = field(default_factory=list)
    d7: List[str] = field(default_factory=list)
    d30: List[str] = field(default_factory=list)
    review_prompt: str = ""


# ----------------- 类型别名，便于仓储层与路由层使用 -----------------
Json = Dict[str, Any]
