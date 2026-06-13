# 守望者量化交易系统 · 前端技术开发文档

> Warden Stock Quant · Frontend Engineering Doc
>
> 前置阅读：[`PRD.md`](./PRD.md) → [`BACKEND.md`](./BACKEND.md) → [`openapi.yaml`](./openapi.yaml)（接口契约，前端据此对齐）
>
> 遵循 `AGENTS.md`：纯 Web 业务 → React + Vite + shadcn/ui + Tailwind；请求器 ky + TanStack Query；状态 zustand；具名导出；`core/` 与 `features/` 划分；类型前缀 `T/E/I`。

---

## 1. 技术栈与选型

### 1.1 主要技术栈

| 类别 | 选型 | 说明 |
|------|------|------|
| 框架 | React 18 + TypeScript | 函数组件 + Hooks |
| 构建 | Vite | 快速 HMR |
| UI | shadcn/ui + Tailwind CSS | 组件库 + 原子化样式，Light/Dark |
| 路由 | React Router v6 | 受保护路由 + 角色路由 |
| 请求器 | **ky** | 轻量 fetch 封装（注入鉴权头/错误处理）|
| 服务端状态 | **TanStack Query** | 缓存、轮询（任务进度）、失效 |
| 客户端状态 | **zustand** | 鉴权、主题、全局 UI |
| 表单 | react-hook-form + zod | 策略/因子/风控参数表单校验 |
| 图表 | **ECharts**（净值/回撤/IC/分层/热力图）+ lightweight-charts（K 线）| 量化可视化 |
| 代码编辑 | **Monaco Editor** | 代码式策略/表达式因子编辑 |
| 表格 | TanStack Table | 交易/持仓/因子大表，虚拟滚动 |
| i18n | i18next（`core/i18n/locales/`）| 中文优先，预留多语言 |
| 报告 | 后端生成 HTML/PDF，前端内嵌/下载 | 见 M5 |

### 1.2 强制编码约束（遵循 AGENTS.md）

- 禁止 `export default`，统一具名导出。
- 类型：`type` 用 `T` 前缀（`TBacktest`），`enum` 用 `E`（`EOrderStatus`），`interface` 用 `I`（`IApiClient`）。
- `core/`（可移植：http、auth、i18n、decimal、charts 封装）与 `features/`（业务）严格分离，功能目录 kebab-case，`index.ts` 统一导出。
- 相同逻辑出现 ≥3 次必抽公共模块（DRY）。

---

## 2. 项目目录结构

```
frontend/
├── src/
│   ├── main.tsx
│   ├── app/
│   │   ├── router.tsx              # 路由 + 受保护/角色路由
│   │   ├── providers.tsx           # QueryClient / Theme / i18n
│   │   └── layout/                 # 全局布局（侧边栏/顶栏）
│   ├── core/
│   │   ├── http/                   # ky 实例 + 鉴权拦截 + 统一响应/错误码
│   │   ├── auth/                   # JWT 存储/刷新, useAuth, RBAC
│   │   ├── query/                  # QueryClient, use-polling-query（任务轮询）
│   │   ├── i18n/                   # i18next + locales/
│   │   ├── lib/                    # decimal.ts（decimal 字符串→number）, format, date
│   │   ├── charts/                 # ECharts/lightweight-charts 封装组件
│   │   └── ui/                     # shadcn 复用组件、表格、表单控件
│   ├── features/
│   │   ├── auth/                   # 登录/注册/找回
│   │   ├── account/                # 个人设置/API Key/配额套餐
│   │   ├── datasets/               # 数据集状态/同步/质量
│   │   ├── strategies/             # 策略列表/编辑（config+code）/版本/模板
│   │   ├── backtests/              # 新建/进度/报告/对比/寻优
│   │   ├── factors/                # 因子库/计算/IC分层/合成
│   │   ├── portfolios/             # 组合/再平衡/持仓
│   │   ├── trading/                # 仿真账户/订单/成交/信号推送/实盘监控
│   │   ├── risk/                   # 风控规则/事件/敞口
│   │   ├── alerts/                 # 告警渠道/告警记录
│   │   └── admin/                  # 用户/数据源凭证/套餐/审计/监控
│   └── types/                      # 全局类型（与 openapi 对齐）
├── public/
├── index.html
├── package.json
├── tailwind.config.ts
├── vite.config.ts
└── .env
```

---

## 3. 核心基础设施

### 3.1 HTTP 请求器（core/http）

```ts
// core/http/client.ts
import ky from "ky";
import { useAuthStore } from "@/core/auth/store";

export const api = ky.create({
  prefixUrl: import.meta.env.VITE_API_BASE ?? "/api/v1",
  hooks: {
    beforeRequest: [
      (req) => {
        const token = useAuthStore.getState().accessToken;
        if (token) req.headers.set("Authorization", `Bearer ${token}`);
      },
    ],
    afterResponse: [
      async (_req, _opt, res) => {
        if (res.status === 401) useAuthStore.getState().tryRefreshOrLogout();
        return res;
      },
    ],
  },
});

// 统一响应解包：{ code, message, data }
export async function unwrap<T>(p: Promise<Response>): Promise<T> {
  const body = await (await p).json<{ code: number; message: string; data: T }>();
  if (body.code !== 0) throw new ApiError(body.code, body.message);
  return body.data;
}
```

### 3.2 decimal 工具（core/lib/decimal.ts）

后端金额/比率为 **decimal 字符串**，展示/计算前转换：

```ts
export const toNum = (v: string | number | null): number =>
  v == null ? NaN : typeof v === "number" ? v : Number(v);
export const fmtPct = (v: string | number) => `${(toNum(v) * 100).toFixed(2)}%`;
export const fmtMoney = (v: string | number) => toNum(v).toLocaleString("zh-CN", { minimumFractionDigits: 2 });
```

### 3.3 任务进度轮询（core/query/use-polling-query）

异步资源（回测/因子/同步）走「提交→轮询」：

```ts
export function useJobQuery(jobId?: string) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => unwrap<TJob>(api.get(`jobs/${jobId}`)),
    enabled: !!jobId,
    refetchInterval: (q) =>
      ["succeeded", "failed", "canceled"].includes(q.state.data?.status ?? "") ? false : 2000,
  });
}
```

### 3.4 全局状态（zustand）

- `useAuthStore`：access/refresh token、当前用户、角色、刷新逻辑、登出。
- `useThemeStore`：Light/Dark。
- `useUiStore`：侧边栏、当前 portfolio 上下文等。

---

## 4. 路由与页面规划

### 4.1 路由表

| 路径 | 页面 | 权限 |
|------|------|------|
| `/login` `/register` | 登录/注册 | 公开 |
| `/` | 概览仪表盘（我的策略/回测/组合/告警概要）| 用户 |
| `/datasets` | 数据集状态/同步/质量 | 用户（同步按权限）|
| `/strategies` `/strategies/:id` | 策略列表/编辑 | 用户 |
| `/backtests` `/backtests/:id` | 回测列表/报告 | 用户 |
| `/backtests/new` | 新建回测/寻优 | 用户 |
| `/factors` `/factors/:id` | 因子库/分析 | 用户 |
| `/portfolios` `/portfolios/:id` | 组合/持仓/再平衡 | 用户 |
| `/trading` | 仿真账户/订单/成交/信号/实盘监控 | 用户（实盘需授权）|
| `/risk` | 风控规则/事件 | 用户 |
| `/alerts` | 告警渠道/记录 | 用户 |
| `/account` | 设置/API Key/配额 | 用户 |
| `/admin/*` | 用户/凭证/套餐/审计/监控 | 管理员 |

### 4.2 全局布局

- 左侧导航（按模块分组）+ 顶栏（用户/主题/告警铃铛）+ 内容区。
- 受保护路由：未登录跳 `/login`；`/admin/*` 校验 `role==='admin'`，否则 403 页。

---

## 5. 各页面核心功能与实现

### 5.1 认证与账户（features/auth、account）
- 登录/注册（zod 校验），登录存 token；个人设置改密。
- **API Key**：创建后**一次性**弹窗展示明文（复制后不再可见），列表显示 prefix/scope/状态，可吊销/轮换。
- 配额套餐：展示当前套餐与各项用量（并发回测/存储/调用），进度条提示。

### 5.2 数据集（features/datasets）
- 状态卡片：最新交易日、各表更新至、证券数、缺口、`stale` 提示。
- 同步操作：触发证券/日 K/指标同步（有权用户/管理员），进度轮询。
- 文件导入：上传/指定导出文件，导入进度 + 质量报告（覆盖区间/缺口/异常）。

### 5.3 策略（features/strategies）— 核心
- 列表（按用户隔离）+ 版本时间线。
- **配置式编辑器**：表单化信号积木（均线交叉/因子选股/再平衡/止损止盈），react-hook-form + zod，实时预览 JSON。
- **代码式编辑器**：Monaco（Python/backtrader），保存前调 `/validate` 做沙箱/静态校验，错误内联提示。
- 模板库：从内置模板一键派生新策略。

### 5.4 回测与报告（features/backtests、reports）— 核心
- 新建：选策略版本/参数/股票池/区间/初始资金/成本配置；提交后入队，进度条轮询。
- 报告页：
  - 指标卡（年化/夏普/最大回撤/卡玛/胜率…）；
  - **净值曲线**（策略 vs 基准）+ **回撤曲线**（ECharts，区域填充）；
  - 月度收益热力图、滚动夏普、行业暴露随时间；
  - 交易明细 / 每日持仓（TanStack Table 虚拟滚动）；
  - 导出 HTML/PDF、生成只读分享链接。
- **多回测对比**：并排指标 + 净值叠加。
- **参数寻优**：参数热力图/平台稳定性，过拟合提示。

### 5.5 因子研究（features/factors）
- 因子库（内置+自定义），表达式/代码编辑。
- 计算：选股票池/区间触发，进度轮询。
- 分析报告：**IC 序列与 IC 衰减**折线、**分层净值**（各档单调性）、多空组合净值、换手率、覆盖度。
- 多因子合成：选子因子 + 权重方案 + 中性化选项 → 生成合成因子 → 一键建策略回测。

### 5.6 组合与交易（features/portfolios、trading）
- 组合详情：净值 vs 基准、当前持仓表、行业/集中度暴露饼图、可用资金。
- 再平衡：展示目标权重 vs 当前持仓 diff、生成的调仓订单（过风控提示）。
- 交易：订单状态机时间线、成交列表、**信号推送清单**（可手动标记已执行）；实盘监控仅授权用户可见。
- 全站交易页展示**风险免责声明**。

### 5.7 风控（features/risk）
- 规则集编辑：规则类型 + 阈值 + 动作（拒单/告警/强平）表单。
- 风控事件流（按时间），敞口报表。

### 5.8 告警（features/alerts）
- 渠道配置：邮件/Webhook/钉钉/飞书/Server酱（连通性测试按钮）。
- 告警记录列表（级别/来源/时间/状态）。

### 5.9 运维（features/admin）
- 用户管理（角色/配额/启停/实盘授权）。
- **数据源凭证**：配置 warden-stock-data base_url / secretId / secretKey（secretKey 仅写入，不回显）。
- 套餐配额、审计日志检索、系统/任务监控、队列堆积。

---

## 6. 与后端的契约对齐

- **统一响应**：`{code,message,data}`，`unwrap` 解包，`code!=0` 抛 `ApiError`（按错误码提示，如 `42902` 配额超限引导升级套餐）。
- **分页**：`{list,total,page,size}`，表格组件统一适配。
- **decimal 字符串**：展示/计算前 `toNum`，图表数据先转 number。
- **异步资源**：提交返回 `job_id` → `useJobQuery` 轮询 → 完成后拉结果分片接口。
- **鉴权**：JWT 自动注入；401 触发刷新或登出；角色路由守护。
- **类型生成**：建议由 `openapi.yaml` 用 `openapi-typescript` 生成 `types/api.d.ts`，避免手抄漂移。

---

## 7. 测试策略

- 组件/逻辑：Vitest + Testing Library（关键表单校验、decimal 工具、轮询逻辑）。
- E2E：Playwright（登录→建策略→回测→看报告→建组合→仿真下单 主流程）。
- 契约：基于 openapi 的 mock（msw）做接口隔离测试。

---

## 8. 环境变量

```bash
# .env
VITE_API_BASE=/api/v1
VITE_APP_NAME=守望者量化
```

---

## 9. 并行开发约定（前端视角）

1. **契约先行**：以 `openapi.yaml` 为准，必要时用 mock(msw) 先行，不等后端。
2. **模块边界**：按 features 分工，跨模块经 `core/` 复用，禁跨 feature 直接依赖内部实现。
3. **异步轮询统一**：所有任务类资源用 `use-polling-query`。
4. **decimal 安全**：金额/比率统一经 `toNum`，禁止对字符串直接算术。
5. **文档同步**：核心交互/字段变更同步 `FRONTEND.md` 与 `openapi.yaml`（`AGENTS.md` 要求）。

---

> 接口字段以 `openapi.yaml` 为权威；UI 须实现角色权限隔离与移动端/暗色适配。
