# Aurora Stage 29 Scaffolding Extension

版本：v1.0  
日期：2026-04-21  
对应实现：`backend/app/scaffolding/scaffolding_fsm.py`、`backend/app/services/intervention_service.py`

## 1. Boundary

Stage 29 只扩展 ScaffoldingFSM 的输入，不重写既有 capability-zone 逻辑。

保留不变：

- `flow`
- `frustration`
- `boredom`

新增输入：

- `srl_phase` phase hint
- traits 弱先验映射出的初始 `support_level`
- reflection prompt style

硬约束：

- ScaffoldingFSM 不 import `SRLPhaseTrackerService`
- FSM 不 import Aggregator service
- phase hint 由调用方读取 Aggregator 后以参数传入

## 2. Read Path

主路径：

1. `InterventionService.create_adaptive_intervention()`
2. `StateAggregatorService.get_user_state(required_fields=("srl_phase",))`
3. `ScaffoldingFSM.snapshot(... phase_value=srl_phase_hint ...)`
4. `resolve_support_level()` 计算有效支持强度

热路径补偿：

- `apply_feedback(..., srl_phase: str | None = None)` 支持调用方透传最新 phase
- 该参数仅用于反馈历史记录与缓存延迟补偿，不改变 “主读取路径经 Aggregator” 的架构约束

## 3. Support Level Rule

| Phase | Delta | 说明 |
| --- | --- | --- |
| `FORETHOUGHT` | `+1` | 鼓励更清晰地规划下一步 |
| `PERFORMANCE` | `+0` | 保持 capability zone 默认值 |
| `SELF_REFLECTION` | `+1` | 鼓励更完整地复盘与调整 |
| `UNKNOWN` | `+0` | 不调整 |

实际应用规则：

- 只有 `consume_mode == "live"` 时才真正上浮
- `shadow` 模式只记录 `delta` 与 decision，不改变最终 `support_level`
- 上浮后仍封顶到 `4`

## 4. Snapshot Contract

Scaffolding snapshot 当前输出：

- `support_level`
- `base_support_level`
- `current_zone`
- `srl_phase`
- `srl_adjustment_applied`
- `srl_support_delta`
- `reflection_prompt_style`

其中：

- `support_level`：最终用于 template 选择与 intervention 内容
- `base_support_level`：未叠加 SRL 调整前的原始支持级别

## 5. Aggregator Freshness

`srl_phase` 在 Aggregator 中单独使用更短 TTL：

- TTL：`15s`

原因：

- SRL 阶段切换比大多数 profile summary 更敏感
- 需要降低 `FORETHOUGHT -> PERFORMANCE`、`PERFORMANCE -> SELF_REFLECTION` 的感知滞后

## 6. Traits Weak Prior Mapping

当前冻结映射：

### 6.1 Initial Support Level

- `conscientiousness >= 0.6` 且 `confidence >= 0.1` → `support_level = 2`
- `conscientiousness <= -0.2` 且 `confidence >= 0.1` → `support_level = 4`
- traits 缺失或 `confidence < 0.1` → `support_level = 3`

### 6.2 Reflection Prompt Style

- `openness >= 0.4` 且 `confidence >= 0.1` → `alternative_exploration`
- `openness <= -0.2` 且 `confidence >= 0.1` → `single_path_deepening`
- 其他情况 → `default`

该映射仍为弱先验：

- 不进入 Router
- 不覆盖行为观测
- ≥10 个 phase transition 之后，实际 SRL 行为信号优先

## 7. Mobile Read-Only Exposure

只读展示入口：

- intervention card / toast / modal 显示 `srlPhaseHint` badge
- profile 页显示 `SrlPhaseBadgeCard`

UI 约束：

- 只显示 badge 与轻量提示文案
- 不做诊断式解释
- 不进入策略分流
