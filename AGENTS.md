# AGENTS 开发指南

本文件为本项目（warden-stock-data）的 AI 协作开发规范。任何前端或后端开发任务，都必须遵守以下约定。

## 项目文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| 需求文档（PRD） | `docs/PRD.md` | 系统整体功能、业务流程、M1–M11 模块、需求边界 |
| 前端技术文档 | `docs/FRONTEND.md` | 前端架构、技术栈、目录与编码规范 |
| 后端技术文档 | `docs/BACKEND.md` | 后端架构（Python/FastAPI）、分层、数据库与服务设计 |
| 量化引擎设计 | `docs/QUANT_ENGINE.md` | 回测 / 因子 / 执行 / 风控 / 绩效引擎内部设计 |
| 行情数据接入 | `docs/DATA_ACCESS.md` | 对接 warden-stock-data 开放 API + 文件导入 + 本地数据集 |
| 接口文档 | `docs/openapi.yaml` | API 契约、请求/响应结构、错误码 |
| 项目说明 | `README.md` | 项目概览、启动方式、整体说明 |

---

## 一、全栈开发规范（核心约束）

### 技术选型决策

根据业务场景选择对应技术栈：

| 业务场景 | 技术栈 | 请求器 | 适用说明 |
|---------|--------|-------|---------|
| 纯 Web 业务 | React + Vite + shadcn/ui + Tailwind CSS | ky + TanStack Query | 管理后台、Web 应用、数据看板等 |
| 跨三端（iOS/Android/Web） | Expo RN + Tamagui | ky-universal + TanStack Query | 需要同时覆盖移动端和 Web 的业务 |
| 跨双端追求性能 | Flutter + GetX | Dio | iOS/Android 高性能渲染场景 |
| SSR 服务 | Next.js | ky + TanStack Query | 仅做数据获取和页面渲染，不直接连数据库 |
| 轻量级 API 服务 | Bun + Hono + 中间件 | — | BFF 层、简单 CRUD、代理转发 |
| 核心后端服务 | Go + Gin + GORM | — | 主业务逻辑、需要高并发和事务支持的服务 |
| 量化计算服务（本项目） | Python + FastAPI + Celery | httpx | 回测/因子/实盘等量化逻辑，依赖 backtrader/vnpy/pandas 等 Python 量化生态 |

> **本项目（warden-stock-quant）后端语言级决策**：因量化生态（backtrader/vnpy/pandas/alphalens 等）几乎全在 Python，本仓库核心后端以 **Python + FastAPI** 为权威实现，是在上表「核心后端服务」之上针对量化特性的项目级特化，理由详见 `docs/BACKEND.md` §1。

### 通用编码约束（贯穿所有技术栈）

1. **封装解耦**：逻辑职责单一，模块间通过接口/类型约束交互，禁止跨层直接调用。
2. **目录规范**：严格划分 `core/`（核心可移植模块）与 `features/`（业务模块），功能目录使用 kebab-case 命名，通过 `index.ts` 统一导出。
3. **DRY 原则**：相同/相似逻辑出现 >= 3 次时，必须抽象为公共模块。
4. **具名导出**：TypeScript 项目禁止 `export default`，统一使用具名导出 `export`。
5. **类型前缀**：type 用 `T` 前缀（`TUser`），enum 用 `E` 前缀（`EStatus`），interface 用 `I` 前缀（`IService`）。
6. **请求器选型**：纯 Web 用 ky，Expo 用 ky-universal，Flutter 用 Dio，均搭配 TanStack Query（Flutter 除外）。
7. **状态管理**：TypeScript 前端统一使用 zustand 管理跨组件状态。
8. **多语言支持**：i18n 模块放在 `core/i18n/`，语言包放在 `core/i18n/locales/`。

### 后端核心要求

- 所有 API 必须实现限流和超时中断（context 传播）中间件。
- 核心业务操作必须支持接口层和数据库层的逻辑中断 + 事务回滚。
- 采用 TDD 驱动开发，先写测试再写实现。
- 使用中间件封装认证、日志、CORS、限流、超时等公共逻辑。

### 基础设施要求

- PostgreSQL、Redis、RabbitMQ 均通过 Docker 容器启动。
- 每个服务独立容器，通过 docker-compose 统一编排。
- 所有环境配置通过环境变量注入，不硬编码。

### Docker 部署规范

1. **PostgreSQL 数据持久化到本项目目录**：PostgreSQL 的数据目录 `/var/lib/postgresql/data` 必须通过 bind mount 持久化到**本项目内的目录**（如 `backend/deploy/pgdata`），不得使用项目外的宿主机路径或匿名卷，确保数据可随项目管理与查看。该数据目录须加入 `.gitignore`，禁止提交到仓库。
2. **镜像名称自动加项目名前缀**：后端启动 Docker 服务时，构建出的镜像名称必须自动带上项目名前缀（前缀取当前项目名，如 `<project>-backend`）。通过在 `docker-compose.yml` 顶层设置 `name: <project>`（统一项目名与容器/网络前缀），并为自建服务显式指定 `image: <project>-<service>` 实现。


## 二、开发前置阅读要求

### 通用前提

进行任何前端或后端开发前，**必须先阅读 `docs/PRD.md`**，把握系统整体功能与业务上下文，避免脱离需求实现。

### 前端开发流程

进行前端开发前，须按顺序阅读：

1. `docs/PRD.md` —— 明确需求与业务功能
2. `docs/FRONTEND.md` —— 明确前端架构与技术规范
3. `docs/openapi.yaml` —— 明确接口契约与数据结构

完成阅读后再开始编写前端代码。**编码完成后必须执行测试验证（见下「测试验证强制要求」），不得跳过。**

#### 前端可解释性要求（info 提示规范）

> 为让用户快速理解界面背后的逻辑与含义，凡涉及**核心数据、重要表单项、或承载后端核心逻辑**的展示位置，必须在对应标题/字段右侧增加一个 **info icon**，hover 时展示该项的含义说明。

1. **统一组件**：使用 `core/ui` 的 `InfoTip` 组件（Info 图标 + hover 气泡，纯 CSS，无额外依赖），禁止各页面各自造轮子。
2. **适用范围（满足其一即需添加）**：
   - 核心数据指标（如绩效指标、风险指标、因子值、回测结果等）；
   - 重要表单项（如策略参数、风控阈值、股票池配置等任何会影响后端计算的输入）；
   - 承载后端核心逻辑/算法语义的字段（如信号类型、乖离率、移动止盈、再平衡频率等专业术语）。
3. **文案要求**：说明须解释「这是什么 + 取值含义/示例 + 注意事项」，面向不熟悉量化的用户也能看懂，避免仅重复字段名。
4. **对齐与溢出**：图标贴近容器右侧时使用 `align="right"`，避免气泡溢出容器/视口；`InfoTip` 已内置最大宽度兜底。
5. **豁免**：纯展示性、含义自明的字段（如「名称」「描述」）可酌情省略，但只要存在歧义或专业术语，一律补充。

### 后端开发流程

进行后端开发前，须按顺序阅读：

1. `docs/PRD.md` —— 明确需求与业务功能
2. `docs/BACKEND.md` —— 明确后端架构与技术规范
3. `docs/openapi.yaml` —— 明确接口契约与数据结构

阅读后**先编写 TDD 测试用例**，再开始编写后端实现代码（测试先行）。**实现完成后必须执行测试验证（见下「测试验证强制要求」），不得跳过。**

### 测试验证强制要求（每次开发收尾必做）

> 任何前端或后端开发任务，**编码完成后都必须主动运行测试并确认通过**，再向用户交付。**无需用户每次提醒**；未跑测试或测试未通过的任务，一律视为未完成。

**后端（Python + FastAPI，TDD）**

- 测试先行：先在 `backend/tests/` 编写/补充用例，再写实现。
- 统一在 Docker 容器内运行（环境与运行时一致，避免本地 Python 版本漂移），示例：

```bash
cd backend/deploy && docker compose -f docker-compose.yml run --rm --no-deps \
  -v "$(cd .. && pwd)/app":/app/app:ro \
  -v "$(cd .. && pwd)/tests":/app/tests:ro \
  api sh -c "pip install pytest pytest-asyncio aiosqlite -q && python -m pytest -q"
```

- 涉及表结构变更时，需同步新增 Alembic 迁移并执行 `alembic upgrade head` 验证。
- 验收：相关用例（CRUD、租户隔离、校验、错误码等）全部通过。

**前端（React + Vite + TS）**

- 至少执行类型检查与构建：`cd frontend && npm run build`（含 `tsc --noEmit`），确保零类型错误。
- 含 Vitest 单测的模块（关键表单校验、工具函数、轮询逻辑等）执行：`npm run test`。
- 改动文件结构（如 `index.tsx` 改名 `index.ts`）后，需重启 dev server 并清理 `node_modules/.vite` 缓存，确认页面可正常加载。

**收尾自检清单**

- [ ] 后端用例已编写并在容器内全部通过
- [ ] 前端 `npm run build` 通过（零类型错误），相关单测通过
- [ ] 数据库迁移（如有）已执行并验证
- [ ] 相关文档已同步（见第三节）

---

## 三、文档同步要求

当涉及**核心功能的新增或修改**时，必须同步更新以下文档，保持代码与文档一致：

- `README.md` —— 项目说明
- `docs/PRD.md` —— 需求文档
- `docs/FRONTEND.md` —— 前端技术文档
- `docs/BACKEND.md` —— 后端技术文档
- `docs/openapi.yaml` —— 接口文档

> 任一核心功能变更未同步文档，视为该任务未完成。

---

## 四、协作输出与提交规范

### 对话输出语言

- 与用户的对话输出一律使用**中文**，不得使用英文作答。

### Git 提交规范

1. **强制账号配置**：提交前必须检查 `git config user.name` 与 `git config user.email`。任一为空时**阻断提交**，并提醒用户先完成 git 账号配置（`git config user.name` / `git config user.email`），不得擅自代为设置。
2. **提交信息格式**：`git commit` 信息遵循 Conventional Commits。类型与作用域前缀（如 `feat(scope)`、`fix`、`refactor`、`docs`、`chore` 等）**保持英文**；冒号之后的描述（含标题描述与正文）**使用中文**撰写。例如：`refactor(backend): 移除 stub 行情源并统一 gotdx 构建`。
3. **禁止 AI 署名**：提交信息中不得添加 Cursor / cursoragent 等 AI 工具的 `Co-authored-by` 或任何类似署名，提交的 author 与 committer 仅为用户本人。
