# Personal Decision Council｜第二阶段架构迭代总结

> 基于《Personal Decision Council｜个人思考议会 项目落地计划 v0.1》以及本轮讨论整理。
>
> 核心结论：第一版目前真正缺少的不是更多 Agent，而是 **“背景补齐 → 角色提问 → 用户补充 → 基于已有观点逐个讨论”** 的机制。

---

## 1. 当前 V1 的核心问题

当前设计基本是：

```text
用户提出困惑
  ↓
Problem Decomposer
  ↓
5 个角色独立分析
  ↓
角色互相质疑
  ↓
Moderator
  ↓
Decision Report
```

这个流程存在一个关键假设：

> 用户已经把问题描述清楚，并且提供了足够背景。

但真实场景往往不是这样。

例如用户说：

> “我最近特别焦虑，感觉做程序员已经没前途了，不知道是不是应该转 AI。”

系统如果直接让多个 Agent 回答，很容易出现：

- Agent 大量依赖猜测
- 不同 Agent 实际在重复回答
- 看起来观点很多，实际上没有真正形成讨论
- 建议可能建立在错误或缺失的背景之上

因此，当前 V1 最大的问题不是 Agent 数量不足，而是：

> **Agent 在信息不足的情况下过早开始推理。**

---

# 2. 核心架构升级

建议把原来的：

```text
Problem Decomposer
        ↓
5 Agent
        ↓
Debate
        ↓
Moderator
```

升级为：

```text
用户提出困惑
      ↓
Context Builder / Problem Discovery
      ↓
发现背景信息缺口
      ↓
各角色基于自身立场提出问题
      ↓
用户补充信息
      ↓
形成 Problem Context
      ↓
角色逐个分析
      ↓
后续角色读取前面角色的观点
      ↓
Cross Examination / 相互质询
      ↓
Moderator
      ↓
Decision Report
      ↓
Action Plan
      ↓
Review
      ↓
Memory
```

核心变化：

> **议会不是直接开会，而是先进行“会前调查”。**

---

# 3. 新增第一阶段：Problem Discovery

原来的 Problem Decomposer 主要负责：

> 把模糊的情绪表达转换成可讨论的问题。

建议升级为：

# Problem Discovery Engine

职责：

1. 识别用户表面问题
2. 识别可能的潜在问题
3. 识别背景信息缺口
4. 判断哪些缺失信息会影响决策
5. 让不同角色提出问题
6. 收集用户回答
7. 形成 Problem Context
8. 判断是否已经具备进入议会讨论的条件

它不只是“拆问题”，而是：

> **整个议会的会前调查部门。**

---

# 4. 第二阶段：不同角色先提问题

这是本轮最重要的架构变化。

不同角色不仅负责回答，也负责提问。

流程：

```text
用户提出问题
      ↓
Problem Discovery
      ↓
识别缺失信息
      ↓
不同角色分别提出问题
      ↓
用户回答
      ↓
Problem Context
```

每个角色应该从自己的立场提出问题。

---

## 4.1 理解者

核心目标：

> 尽可能理解用户真正想解决什么。

典型问题：

- 你为什么产生这个想法？
- 这个问题持续多久了？
- 如果不考虑钱，你仍然会做这个选择吗？
- 你真正担心的是什么？

---

## 4.2 支持者

核心目标：

> 找到用户当前观点中合理、真实、有价值的部分。

典型问题：

- 当前事情中最让你长期消耗的是什么？
- 如果继续维持现状，你最担心什么？
- 有没有什么事情让你觉得继续下去已经没有意义？

注意：

> 支持者不是无条件赞同用户，而是帮助识别用户诉求中真实、合理的部分。

---

## 4.3 反方

核心目标：

> 寻找用户当前判断中的漏洞、假设和潜在认知偏差。

典型问题：

- 你为什么认为这个选择能够解决问题？
- 有没有可能你真正想逃避的是另一个问题？
- 如果最坏情况发生，你能接受吗？
- 有没有证据证明你的判断？

---

## 4.4 现实主义者

核心目标：

> 识别现实约束和硬条件。

重点：

- 收入
- 支出
- 存款
- 时间
- 能力
- 家庭责任
- 市场
- 工作机会
- 风险
- 机会成本

典型问题：

- 当前收入是多少？
- 每月固定支出是多少？
- 有多少个月现金储备？
- 有没有下一份工作？
- 当前能力是否足以支撑下一步？

---

## 4.5 战略顾问

核心目标：

> 判断用户真正想去哪里，以及有哪些路径。

典型问题：

- 如果解决当前问题，你最终希望获得什么？
- 下一步具体想进入什么方向？
- 有没有可能先低成本验证？
- 有没有不需要立即做重大改变的替代方案？

---

# 5. 用户补充之后，形成 Problem Context

不要让 Agent 永远直接阅读完整聊天记录。

应该建立结构化的：

# Problem Context

示例：

```json
{
  "problem": {
    "statement": "是否应该辞职转向 AI Agent"
  },

  "user_background": {
    "age": 32,
    "experience": "8年Java开发",
    "income": "25K"
  },

  "current_situation": {
    "job": "业务下滑",
    "motivation": "希望转向AI Agent"
  },

  "constraints": {
    "savings": "20万",
    "monthly_fixed_cost": "6000"
  },

  "goals": [
    "进入AI Agent方向"
  ],

  "concerns": [
    "担心继续做Java没有前景",
    "担心转型失败"
  ],

  "unknowns": [
    "是否已经有AI项目经验",
    "是否尝试过内部转岗",
    "AI方向具体目标岗位"
  ]
}
```

---

# 6. Problem Context 必须是动态版本

Problem Context 不是一次生成后永久不变。

建议：

```text
Context v1
    ↓
用户补充
    ↓
Context v2
    ↓
角色讨论
    ↓
发现新的关键事实
    ↓
Context v3
    ↓
最终 Context
```

例如：

```text
v1：
用户：我想辞职。

v2：
发现：其实用户想转 AI。

v3：
发现：真正担心的是年龄和竞争力。

v4：
发现：用户已经在做 AI 项目。

v5：
最终问题：
是否应该从 Java 开发逐步转向 AI Agent，
而不是简单讨论“是否辞职”。
```

这是系统非常重要的价值：

> **用户最开始提出的问题，不一定是真正需要解决的问题。**

---

# 7. 第三阶段：角色逐个回答，而不是并行回答

原设计：

```text
用户
 ↓
A / B / C / D / E 并行
 ↓
Moderator
```

建议升级为：

```text
用户
 ↓
Problem Context
 ↓
理解者
 ↓
支持者
 ↓
反方
 ↓
现实主义者
 ↓
战略顾问
 ↓
Moderator
```

关键不是简单排队。

而是：

> **后一个角色必须阅读前面角色已经说过的内容，并基于这些内容继续思考。**

---

# 8. 每个角色拿到的 Context 应该逐步增加

## 理解者

```text
用户原始问题
+
Problem Context
```

负责：

> 建立对问题的第一层理解。

---

## 支持者

```text
用户原始问题
+
Problem Context
+
理解者观点
```

负责：

- 认同合理部分
- 补充遗漏
- 修正理解者可能忽略的内容

---

## 反方

```text
用户原始问题
+
Problem Context
+
理解者
+
支持者
```

负责：

- 挑战前面观点
- 寻找漏洞
- 提出反例
- 指出未经验证的假设

---

## 现实主义者

```text
用户
+
Problem Context
+
理解者
+
支持者
+
反方
```

负责：

> 把讨论重新拉回现实约束。

---

## 战略顾问

```text
用户
+
完整 Problem Context
+
前面所有角色观点
```

负责：

- 提炼真正目标
- 形成选项
- 比较路径
- 分析风险
- 提出低成本验证方案
- 形成行动路径

---

# 9. 角色不是简单重复回答

后一个角色应该明确回应前面的角色。

例如：

> 理解者认为：用户真正想解决的不是辞职，而是职业方向的不确定。

支持者：

> 我基本认同这一判断，但认为还有一个问题：当前工作已经产生了持续性的消耗。

反方：

> 我不同意前两位默认“职业方向”是核心问题。目前的信息不足以证明用户想离开的是 Java，而不是当前公司。

现实主义者：

> 前面的讨论主要集中在意愿和方向，但经济约束尚未被充分讨论……

战略顾问：

> 综合前面的分歧，目前真正需要解决的可能不是“辞不辞职”，而是“如何低风险验证 AI Agent 是否值得成为下一阶段职业方向”。

这样才真正形成：

# Council

而不是：

# 五次独立 ChatGPT 回答。

---

# 10. Agent 输出应该同时支持“问题”和“观点”

原来的 Agent 主要输出：

```json
{
  "position": "",
  "reasoning": "",
  "supporting_points": [],
  "concerns": [],
  "counterarguments": [],
  "missing_information": [],
  "recommendations": []
}
```

建议扩展为两种核心输出。

## Question

```json
{
  "type": "question",
  "question": "",
  "reason": "",
  "importance": "high"
}
```

## Opinion

```json
{
  "type": "opinion",
  "position": "",
  "reasoning": "",
  "supporting_points": [],
  "concerns": [],
  "counterarguments": [],
  "missing_information": [],
  "recommendations": []
}
```

因此 Agent 核心能力从：

```text
answer()
```

升级为：

```text
ask()
answer()
challenge()
```

---

# 11. 问题也应该拥有角色归属

建议保存：

```json
{
  "question_id": "Q-001",
  "asked_by": "realist",
  "question": "当前每月固定支出是多少？",
  "importance": "high",
  "answered": true,
  "answer": "6000"
}
```

这样以后可以：

- 判断哪些问题已经问过
- 避免重复询问
- 判断哪些角色关注过这个问题
- 在 Memory 中长期保存重要背景

---

# 12. 不是所有角色都必须强行发言

这是一个重要的优化。

如果某个角色判断：

> 当前没有新的观点。

可以：

```text
SKIP
```

或者：

> 当前没有新的现实层面观点，不重复发言。

避免：

> 五个 Agent 为了完成任务强行生成五段内容。

目标不是：

> 每个角色都说话。

而是：

> **每个角色只有在能够贡献新信息、新观点或新质疑时才说话。**

---

# 13. 第四阶段：Cross Examination

角色逐个发表之后，可以进行一轮集中质询。

重点只关注：

- 分歧
- 漏洞
- 未验证假设
- 关键风险
- 信息缺口

不要重新回答完整问题。

例如：

```text
反方：
我认为“辞职可以解决问题”这一假设没有证据。

现实主义者：
我同意，而且目前经济安全边际不足以支持裸辞。

战略顾问：
但这并不意味着必须维持现状，可以先验证 AI Agent 方向。
```

最多 1～2 轮。

避免 Token 爆炸。

---

# 14. Moderator 的职责需要进一步明确

Moderator 不应该只是：

> 综合以上观点。

它应该回答至少 7 个问题：

### 1. 我们真正讨论的是什么？

区分：

```text
表面问题
VS
真实问题
```

### 2. 哪些已经确定？

区分：

```text
事实
```

### 3. 哪些只是推测？

明确：

```text
推测
```

### 4. 真正的分歧在哪里？

不要机械总结每个角色。

应该找到：

> 为什么他们意见不同。

### 5. 还有什么信息不足？

不能为了生成结论而强行下结论。

### 6. 当前有哪些选择？

例如：

```text
Option A
Option B
Option C
```

### 7. 下一步最值得做什么？

最终落地：

```text
未来3天
未来7天
未来30天
```

---

# 15. Moderator 发现重大信息缺失时，可以重新询问用户

这是整个系统非常重要的一点。

流程可以是：

```text
角色讨论
    ↓
Moderator 检查
    ↓
发现关键问题无法判断
    ↓
暂停议会
    ↓
向用户询问
    ↓
用户补充
    ↓
更新 Problem Context
    ↓
继续议会
```

因此：

> **议会不是一次性执行，而是允许“暂停会议 → 向当事人询问 → 继续会议”。**

---

# 16. Orchestrator 应该改成状态机

建议状态：

```text
INIT
 ↓
UNDERSTANDING
 ↓
CONTEXT_GAP_DETECTION
 ↓
ROLE_QUESTIONING
 ↓
WAITING_USER
 ↓
CONTEXT_BUILDING
 ↓
COUNCIL_DISCUSSION
 ↓
CROSS_EXAMINATION
 ↓
MODERATOR_REVIEW
 ↓
NEED_USER_CLARIFICATION?
 ├── YES → WAITING_USER
 │          ↓
 │       COUNCIL_DISCUSSION
 │
 └── NO
      ↓
DECISION_REPORT
      ↓
ACTION_PLAN
      ↓
REVIEW
```

这比简单的：

```python
for agent in agents:
    agent.run()
```

更符合产品需求。

---

# 17. 建议的完整 Council 流程

```text
                    用户提出困惑
                         ↓
                Problem Discovery
                         ↓
                  信息缺口识别
                         ↓
              各角色分别提出问题
                         ↓
                    用户回答
                         ↓
                Problem Context v1
                         ↓
                      理解者
                         ↓
                      支持者
                         ↓
                       反方
                         ↓
                   现实主义者
                         ↓
                    战略顾问
                         ↓
                Cross Examination
                         ↓
                    Moderator
                         ↓
             是否仍缺少关键事实？
                    ↙         ↘
                  是           否
                  ↓             ↓
              用户补充       Decision Report
                  ↓             ↓
             更新 Context      Action Plan
                  ↓             ↓
                继续议会        Review
                                ↓
                              Memory
```

---

# 18. V1 下一阶段不要急着增加技术组件

当前不应该优先增加：

- MCP
- Milvus
- 复杂 RAG
- Kubernetes
- 大量 Tool
- 更多 Agent

优先把下面 5 个东西定下来：

```text
1. Problem Context Schema
2. Role Question Schema
3. Council State Machine
4. Sequential Agent Context Schema
5. Moderator Schema
```

这五个确定以后，再改现有第一版代码。

---

# 19. 新版 MVP

原来的 MVP：

> 5 个角色 + Moderator。

建议改成：

> **一个真实问题 → 系统主动发现背景缺口 → 不同角色从不同立场向用户提问 → 用户补充 → 角色逐个阅读前面观点并继续讨论 → Moderator 总结。**

第一阶段甚至可以暂时不做 Memory。

先把这条核心链路跑通。

---

# 20. MVP 核心模块

第一版只保留四个核心模块：

```text
01 Context Builder
        ↓
02 Role Question Engine
        ↓
03 Sequential Council
        ↓
04 Moderator
```

### Context Builder

回答：

> 用户说了什么？
> 
> 已知什么？
> 
> 未知什么？
> 
> 哪些信息会影响决策？

### Role Question Engine

回答：

> 不同角色分别还想知道什么？
> 
> 为什么想知道？

### Sequential Council

回答：

> 角色如何基于前面已经发生的讨论继续思考？

### Moderator

负责：

```text
共识
分歧
事实
推测
缺失信息
选择
风险
行动
```

---

# 21. 项目核心原则新增

在原有产品原则基础上，增加：

> **在信息不足时，不急于回答；先帮助用户补齐决定所需要的信息。**

以及：

> **角色之间不是独立回答同一个问题，而是在共享上下文的基础上逐步形成观点、质疑观点和修正观点。**

---

# 22. 当前产品定位的进一步明确

项目正在从：

> 多 Agent 聊天系统

升级为：

> **结构化个人决策系统**

真正的差异化不是：

```text
我有5个Agent
```

而是：

```text
我能让不同立场的 Agent：

先问问题
→ 获取背景
→ 形成观点
→ 阅读其他观点
→ 互相质疑
→ 发现信息不足
→ 再向当事人询问
→ 最终帮助当事人形成自己的判断
```

---

# 23. 最终产品闭环

```text
聊
 ↓
问
 ↓
补背景
 ↓
理解
 ↓
分析
 ↓
质疑
 ↓
形成选择
 ↓
行动
 ↓
复盘
 ↓
Memory
 ↓
下一次决策
```

核心目标仍然是：

> **不是让 AI 告诉我人生应该怎么过。**

而是：

> **在我不知道怎么办的时候，给我一个可以立即召集的、允许互相反驳的个人思考议会。**

最终：

> **决定仍然属于我。**
>
> **AI 的任务，是让我在做决定的时候，比没有它更清醒。**

---

# 24. 下一步具体工作

建议下一轮直接进入：

## Project 0.2 Architecture

依次完成：

1. Problem Context Schema
2. Context Version Schema
3. Role Question Schema
4. Agent Opinion Schema
5. Agent Context Schema
6. Council State Machine
7. Agent 顺序与跳过规则
8. Moderator Schema
9. 用户补充信息交互协议
10. API 设计
11. 数据库表结构
12. Prompt 设计
13. 基于当前 V1 代码的改造方案
14. 第一批真实测试 Case

---

## 25. 一句话总结

当前 V1 最大的问题不是：

> “AI 角色不够多。”

而是：

> **“AI 角色在还不了解用户真实情况的时候，就开始给答案。”**

因此下一版本的核心变化应该是：

```text
先问清楚
    ↓
再讨论
    ↓
逐个回应
    ↓
互相质疑
    ↓
必要时再次询问用户
    ↓
最后再形成决策
```

这将成为 Personal Decision Council 从“多 Agent Chat”走向“个人思考议会”的关键一步。
