"""角色定义（文档 §4：理解者 / 支持者 / 反方 / 现实主义者 / 战略顾问）。

每个角色从自身立场出发：先提问题（Role Questioning），再在共享上下文基础上
逐个形成观点（Sequential Council）。顺序与文档 §8 保持一致。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Role:
    key: str
    name: str
    goal: str                       # 核心目标
    stance: str                    # 提问/分析时的立场描述
    example_questions: List[str]   # 典型问题（供 prompt 参考，不强制使用）


ROLES: List[Role] = [
    Role(
        key="understander",
        name="理解者",
        goal="尽可能理解用户真正想解决什么。",
        stance="站在共情与澄清的立场，剥离情绪外壳，找到用户真正的诉求。",
        example_questions=[
            "你为什么产生这个想法？",
            "这个问题持续多久了？",
            "如果不考虑钱，你仍然会做这个选择吗？",
            "你真正担心的是什么？",
        ],
    ),
    Role(
        key="supporter",
        name="支持者",
        goal="找到用户当前观点中合理、真实、有价值的部分。",
        stance="帮助用户识别诉求中真实、合理的部分，而不是无条件赞同。",
        example_questions=[
            "当前事情中最让你长期消耗的是什么？",
            "如果继续维持现状，你最担心什么？",
            "有没有什么事情让你觉得继续下去已经没有意义？",
        ],
    ),
    Role(
        key="opponent",
        name="反方",
        goal="寻找用户当前判断中的漏洞、假设和潜在认知偏差。",
        stance="挑战默认假设，寻找反例与未经验证的论断。",
        example_questions=[
            "你为什么认为这个选择能够解决问题？",
            "有没有可能你真正想逃避的是另一个问题？",
            "如果最坏情况发生，你能接受吗？",
            "有没有证据证明你的判断？",
        ],
    ),
    Role(
        key="realist",
        name="现实主义者",
        goal="识别现实约束和硬条件。",
        stance="把讨论拉回收入、支出、储蓄、时间、能力、家庭责任、市场与风险等硬约束。",
        example_questions=[
            "当前收入是多少？",
            "每月固定支出是多少？",
            "有多少个月现金储备？",
            "有没有下一份工作？",
            "当前能力是否足以支撑下一步？",
        ],
    ),
    Role(
        key="strategist",
        name="战略顾问",
        goal="判断用户真正想去哪里，以及有哪些路径。",
        stance="提炼真正目标，形成选项、比较路径、给出低成本验证方案。",
        example_questions=[
            "如果解决当前问题，你最终希望获得什么？",
            "下一步具体想进入什么方向？",
            "有没有可能先低成本验证？",
            "有没有不需要立即做重大改变的替代方案？",
        ],
    ),
]

ROLE_BY_KEY = {r.key: r for r in ROLES}


def role_name(key: str) -> str:
    return ROLE_BY_KEY.get(key, Role(key, key, "", "", [])).name
