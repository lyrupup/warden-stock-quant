# 类型对齐说明

本目录提供与 `docs/openapi.yaml` 对齐的前端类型。

## 采用方式（二选一）：手写核心类型为主

- `api-models.ts`：**手写**核心领域类型（`T`/`E` 前缀），覆盖骨架阶段用到的
  鉴权、账户、API Key、任务等模型。具备良好可读性与 IDE 提示，作为当前权威来源。
- 可选补充：执行 `pnpm gen:api`（或 `npm run gen:api`）调用 `openapi-typescript`
  由 `../docs/openapi.yaml` 生成 `src/types/api.d.ts`，用于后续大批量接口接入时
  做契约校对，避免手抄漂移。生成文件不参与 lint（已在 `.eslintrc.cjs` 忽略）。

> 选择「手写为主 + 生成为辅」是因为骨架阶段接口面较小、强调可读与稳定；
> 待 M4–M10 业务接口大规模接入时，可逐步切换为以生成类型为准。
