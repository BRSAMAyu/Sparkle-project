# Unified Ops Surface — Kill Switch / Release / Rollback（O-06）

> 2026-09-28 由 wt765 随卡 O-06 落地。本文是操作面的入口文档；机制权威在代码（下表），本文不复制实现。

## 1. 面由什么构成

| 层 | 位置 | 职责 |
|---|---|---|
| 模式判定权威 | `backend/app/core/kill_switch.py` | read_mode/write_mode：Redis 现值优先、settings tri-state 判据、legacy bool 兜底、Prometheus `KILL_SWITCH_MODE` gauge |
| 绑定权威 | 各 `aurora_*_kill_switch_service` / `fme_*` / `auto_degrade` / `routing_parameter_registry` / `fme_l3_closure_bridge` | 每个能力的 KillSwitchBinding 实例（本面零复制） |
| 统一注册表 | `backend/app/core/ops_surface.py` | `CAPABILITY_SPECS`：64 个既有绑定的惰性索引 + 受控翻转 + per-capability 回滚史 |
| Release manifest | `backend/app/core/release_manifest.py` | model/config/migration 一次性只读快照 |
| Internal API | `backend/app/api/internal/ops_release.py`（挂载 `/api/internal/ops`） | `X-Internal-API-Key` 门禁，语义同 auto_degrade |
| 冒烟工具 | `scripts/ops_rollback_smoke.py` | 默认进程内 fakeredis；真实 Redis 需双显式确认，只翻 `shadow` 并回滚 |

## 2. 能力清单与观测

- `GET /api/internal/ops/capabilities`：全量 64 能力（capability_id / domain / 运行时 mode / settings_mode / fallback / redis_key / 描述）。
- `capability_id = <binding.stage>.<binding.feature>`，与 Prometheus `KILL_SWITCH_MODE{stage,feature}` 标签逐字一致。
- domain 词表封闭：`aurora(53) / memory(4) / fme(2) / infra(5)`。
- 注册表完整性由 `backend/tests/unit/test_ops_surface_registry.py` 的 **AST 生成式对账**守卫：源码每增一个 `KillSwitchBinding` 而不登 spec、或删绑定留幽灵 spec，测试即红。

## 3. 翻转与回滚语义

- `POST /capabilities/{cid}/mode`：词表外 mode **显式 400**（不静默回落）；Redis 缺席 **503 拒写**（绝不把未落盘写冒充成功）；每次翻转先压回滚史（`sparkle:ops:rollback_history:<cid>`，上限 20 条，TTL 30 天），再走核心 `write_mode`。
- `POST /capabilities/{cid}/rollback`：在 `action=="set"` 记录中找最近的「from ≠ 当前值」恢复点步进恢复；rollback 标记不是恢复点（防震荡）；无恢复点 409。
- 用户 state 不经过本面：翻转只写能力模式键（api 测试以哨兵用户键逐字不变为验收）。
- 本路由**无批量/一键端点**；off/live 都须调用方逐次显式给出。

## 4. Release manifest

`GET /api/internal/ops/release-manifest`：

```json
{
  "manifest_version": 1,
  "model":     { "llm_provider", "llm_model_name", "llm_reason_model_name", "batch_llm_provider", "embedding_model" },
  "config":    { "release_flags(五旗契约键集)", "capability_mode_count", "capability_settings_modes(64 能力 settings 判据快照)" },
  "migration": { "database_revision(alembic_version 表)", "code_head(ScriptDirectory)", "up_to_date", "error" }
}
```

任一数据源缺席/失败即如实降级为 `null` + `error` 注记，不伪造（Forbidden #2）。

## 5. 新能力接线契约（registered-iff-read，V3-FIX-345 学说不变）

1. 在拥有方模块声明 `KillSwitchBinding`（真实读者在场）+ Settings tri-state 字段；
2. `CAPABILITY_SPECS` 追加一行 spec（id 与 stage.feature 逐字对齐，prefix 与拥有方传参逐字一致）；
3. 完整性测试自动红/绿把关；AV / AURORA-CONFIG 守卫照常生效。

## 6. 已知边界（如实登记，不藏账）

- 5 个元认知 confidence proxy（`metacognition_registry.ConfidenceProxyDefinition`）直读 settings 三态字段（`!= "off"` 语义），未走 kill_switch 核心——无运行时翻转、无 gauge，与统一面语义不一致；已预占 **V3-FIX-501**。
- `AURORA_DEFAULT_MODE`（.env.example 声明的"总默认"，AURORA-CONFIG 守卫托管）在 runtime **零读者**——声明面与行为面脱钩；已预占 **V3-FIX-500**。
- 回滚史存 Redis（引擎重启不丢、跨进程共享），但不落 DB；需要审计级持久史时由后续卡评估 EventBus/DB 落账。
