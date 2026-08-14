# Personal Decision Council（个人决策议会）v0.2

> 一个「结构化个人决策系统」：AI 角色**先问清楚**，再讨论，逐个回应，互相质疑，
> 必要时再次询问用户，最后帮助你形成自己的判断。**决定权始终在你。**

本仓库实现《Personal Decision Council｜第二阶段架构迭代总结》的核心链路：

```
用户提出困惑
   ↓
Context Builder（会前调查：识别缺口）
   ↓
各角色分别提问（理解者/支持者/反方/现实主义者/战略顾问）
   ↓
用户补充
   ↓
角色逐个发言（后一个读取前面观点，可 SKIP）
   ↓
Cross Examination（集中质询）
   ↓
Moderator（回答 7 个核心问题）
   ↓
必要时再问用户 → 否则 Action Plan + Review
```

## 技术栈

| 层 | 技术 | 说明 |
| --- | --- | --- |
| 前端 | uni-app (Vue3 + Vite) | 一套代码打包 **Android / iOS / H5** |
| 后端 | Python + FastAPI | 议会状态机编排 |
| Agent | 角色化 Prompt + 顺序上下文 | 5 角色 + Moderator |
| 存储 | 本地 SQLite | 零外部依赖 |
| LLM | DeepSeek（OpenAI 兼容）/ Mock | 未配 key 自动用 Mock，便于自测 |

## 目录结构

```
persion-decision/
├── backend/                  # Python + FastAPI 后端
│   ├── app/
│   │   ├── schemas.py        # ProblemContext / RoleQuestion / AgentOpinion / ModeratorReport
│   │   ├── config.py         # 环境变量配置（LLM 提供方、DeepSeek key 等）
│   │   ├── llm.py            # LLM 抽象：MockLLM + DeepSeekLLM（urllib，无 requests 依赖）
│   │   ├── prompts.py        # 各阶段 Prompt 模板（内嵌 TASK 标记供 Mock 分支）
│   │   ├── roles.py          # 5 个角色定义
│   │   ├── db.py             # SQLite 仓储层
│   │   ├── council/          # 议会状态机 Orchestrator
│   │   └── main.py           # FastAPI 路由
│   ├── tests/                # Mock 自测 + 端到端集成测试
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py                # 启动入口
└── frontend/                 # uni-app 前端（Android/iOS/H5）
    └── src/pages/index/index.vue
```

## 快速开始

### 1. 启动后端

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 默认 Mock 模式（无需 key，自测可直接跑）
python run.py
# 或：uvicorn app.main:app --reload --port 8000

# 健康检查
curl http://localhost:8000/api/health
```

后端默认在 `http://localhost:8000`，并自动允许跨域（H5 调试方便）。

### 2. 配置 DeepSeek（可选）

后端会在启动时**自动读取 `backend/.env`**（无需任何额外依赖）。复制 `.env.example` 为 `.env` 并填入你的 key：

```ini
# LLM_PROVIDER 留空即可：检测到 key 会自动用 DeepSeek；无 key 自动用 Mock
LLM_PROVIDER=
DEEPSEEK_API_KEY=sk-你的key
DEEPSEEK_MODEL=deepseek-chat
```

- 后端现已**自动加载 `.env`**，不再需要把变量手动塞进系统环境变量。
- `LLM_PROVIDER` 三态：`留空`（推荐，按 key 自动切换）/ `deepseek`（强制）/ `mock`（强制，调试用）。
- 只要 `DEEPSEEK_API_KEY` 非空且 `LLM_PROVIDER≠mock`，重启后端即与真实 DeepSeek 交互；无 key 时自动回退 **Mock LLM**（服务不崩、可自测）。

**验证是否真的用上了 DeepSeek：**

```bash
curl http://localhost:8000/api/health
# 期望看到：{"status":"ok","llm_provider":"deepseek","deepseek_configured":true}
# 若仍是 "mock"，说明 key 未被读到——检查 .env 是否在 backend/ 目录下、key 是否填好。
```

> 如果你之前设置了系统环境变量 `LLM_PROVIDER=mock`，它的优先级高于 `.env`，会导致仍是 Mock。
> 可在启动前执行 `unset LLM_PROVIDER`（Linux/macOS）或 `set LLM_PROVIDER=`（Windows）清掉它。

### 3. 运行前端

```bash
cd frontend
npm install
npm run dev:h5        # 本地 H5 开发（默认 http://localhost:5173，已代理 /api 到后端 8000）
```

#### 三端打包

```bash
npm run build:h5          # 产出 dist/build/h5 —— 部署到任意静态服务器即为网页版
npm run build:app         # 产出 dist/build/app-plus —— 用 HBuilderX 云打包/本地打包成 Android/iOS 安装包
```

> App（Android/iOS）说明：uni-app 的 `app-plus` 产物需借助 **HBuilderX** 进行原生打包。
> 本工程已配置好 `manifest.json`（含 INTERNET 权限、vueVersion=3）。
> 打包前请在 App 内「设置」里把后端地址改为**真实可达地址**（如 `http://192.168.1.10:8000/api`），
> 因为手机无法访问电脑上的 `localhost`。

### 关于 `@dcloudio` 依赖版本（重要）

`@dcloudio` 的包**只发布带日期戳的预发布版本**（如 `3.0.0-5020420260813001`），因此：

- ❌ 不能用 `^3.0.0` 这类语义化范围（预发布版本被 semver 排除，报 `ETARGET`）。
- ✅ **所有 `@dcloudio/*` 必须锁成同一个版本字符串**（它们同批次发布、必须互相匹配）。
- ✅ `@dcloudio/types` 用 `^3.4.8`（与官方 `uni-preset-vue#vite` 模板一致），否则报 `ERESOLVE` peer 冲突。

本工程 `package.json` 已直接对齐官方模板的稳定版本：

```jsonc
"@dcloudio/uni-app":         "3.0.0-5020420260813001",
"@dcloudio/uni-app-plus":    "3.0.0-5020420260813001",
"@dcloudio/uni-components":  "3.0.0-5020420260813001",
"@dcloudio/uni-h5":          "3.0.0-5020420260813001",
"@dcloudio/uni-cli-shared":  "3.0.0-5020420260813001",
"@dcloudio/uni-stacktracey": "3.0.0-5020420260813001",
"@dcloudio/vite-plugin-uni": "3.0.0-5020420260813001",
"@dcloudio/uni-automator":   "3.0.0-5020420260813001",
"@dcloudio/types": "^3.4.8",
"vite": "5.2.8",
"rollup": "4.14.3"
```

若安装时遇到 npm 的 `safe-delete` 批量删除确认报错（非交互环境常见问题），先彻底删除 `node_modules` 再重装即可：

```bash
# Windows
rmdir /s /q node_modules
npm install
# 或换用国内镜像加速
npm install --registry https://registry.npmmirror.com
```

## 测试

后端核心逻辑仅依赖标准库，Mock 自测**无需安装任何第三方包**即可通过：

```bash
cd backend
python tests/test_council_mock.py
```

端到端（需安装 fastapi/uvicorn/httpx，验证真实 HTTP 服务在 Mock 模式下可交互）：

```bash
python tests/test_server_mock.py
```

测试覆盖：完整会话流程（提问→回答→5 角色观点→质询→Moderator→行动计划）、
配置回退逻辑（deepseek 无 key 自动用 mock）、DeepSeek 请求构造与响应解析（离线 mock）、JSON 容错解析。

## API 速览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查，返回当前 LLM 提供方 |
| POST | `/api/sessions` | 创建议会会话，返回 `session_id` |
| GET | `/api/sessions/{id}` | 获取会话状态与全部消息 |
| POST | `/api/sessions/{id}/messages` | 发送一条用户消息，驱动状态机，返回新增消息 |

消息类型（`metadata.kind`）：`role_questions` / `agent` / `cross_exam` / `moderator` / `action_plan` / `clarification` / `system`。

## 设计要点（对应架构文档）

- **先问后答**：角色先提问题补齐背景，避免信息不足时过早下结论（文档 §3/§4）。
- **顺序讨论**：后一个角色读取前面全部观点并明确回应/质疑（文档 §7/§8）。
- **可跳过**：角色无新增观点时返回 `skipped`，不强行发言（文档 §12）。
- **动态 Context**：每轮补充都会生成新版本 Problem Context（文档 §6）。
- **可暂停询问**：Moderator 发现关键缺失可再次向用户澄清（文档 §15）。
- **状态机编排**：`INIT → WAITING_ANSWERS → COUNCIL → CROSS_EXAM → MODERATOR → (CLARIFICATION) → COMPLETED`（文档 §16/§17）。
