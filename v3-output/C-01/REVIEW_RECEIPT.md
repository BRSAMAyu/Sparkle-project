# C-01 REVIEW RECEIPT · Reviewer 1（独立复核）

- **Reviewer**: R1（独立执行验收，未依赖 Worker 自报）
- **Date**: 2026-09-19
- **被审对象**: wt5 未 commit 工作树（base `2f52a972`，已核实 HEAD == base）+ `v3-output/C-01/{REPORT.md,changes.patch}`
- **对照裁决**: 主仓 B-06 `v3-output/B-06/`（D-CTX：ContextPack 为唯一上下文契约，ContextBuilderMixin 平行装配为应收敛方）
- **环境注记**: wt5 无 venv，借用 `/Users/brsama/code/GitHub/sparkle-cosmos/backend/.venv`（Python 3.11）只读运行；按 Worker 同法从主仓只读拷入 `app/gen/` 供测试，收工已删。`/opt/home/bin/python3.11` 不存在（实为 `/opt/homebrew/bin/python3.11`），未影响验证。

## 1. 设计审查（卡面符合性）

| 卡面要求 | 实现 | 判定 |
|---|---|---|
| 优先 extend 现有 contract | `ContextPack.decision_context: DecisionContext \| None = None` 可选尾字段；无新真源 | ✅ |
| 字段携带 ref/type/scope/version/why_included | `ContextItemDescriptor`/`DecisionStateSignal` 全字段齐备，`ttl_or_epoch` 由 `validate()` 强校验（至少其一） | ✅ |
| proto/DTO 变化走单一生成链 | 前提不成立：纯 Python 消费，proto 零触碰（diff 无 proto 文件） | ✅（条件未触发） |
| parity guard（如跨层消费） | 无 Go/Dart 契约依赖 → 契约快照测试（字段集+词表+sha256 指纹+prompt 面 key 冻结，15 项） | ✅ |
| 不存在 parallel UserContextV3 真源 | 全仓 grep `UserContextV3` 仅命中 decision_context.py 自己的 docstring | ✅ |

**封闭词表**：scope(5)/ref-scheme(5)/why_included(10)/item-type(6) 均为 `frozenset`，契约测试以精确集相等断言冻结；builder 是当前唯一生产者，其产出的每个 reason 均来自 `_decision_item_reasons`/`("state_signal",)`/`("plan_scope",)` 白名单组合。**注意**：词表执行是 `validate()` 返回违规（opt-in），不在 `__post_init__` 强制——见 §6 观察 1。

**降级两层核实（读代码+测试）**：
- kill switch：`settings.ENABLE_DECISION_CONTEXT` 在 build() 内实时读取 → `decision_ctx=None`；`test_builder_decision_context_kill_switch` 实测可达 ✅
- 逐字段降级：`_collect_decision_signals` 每字段独立 try/except + envelope 空值 → `degraded_fields` 登记；`test_builder_signals_degrade_gracefully`（聚合器爆炸 → signals=() + 三字段 degraded + items 不受影响 + pack 正常返回）✅
- 整段 try/except（`_build_decision_context` 抛异常 → None 不阻断）：代码在（context_pack.py:1647-1678），无直接测试强制其触发——见 §6 观察 2（轻微）。

## 2. 无平行真源验证

- `git diff` 仅 4 个代码文件（settings/context_pack/decision_context/契约测试）；`orchestration/context_builder.py`（ContextBuilderMixin）、`state_aggregator/schema.py`（UserStateV1）、memory 表模型**零改动** ✅
- signals 均经 `state_signal_from_envelope()` 构造：`ref=user_state://<field>` 指针 + `ttl_seconds` 取自权威表 `StateAggregatorService.FIELD_TTLS_SECONDS`（已核实三默认字段在表内）+ `epoch=state.schema_version`（实测 `user_state.v1.13`）+ 原样携带 `computed_at/freshness_seconds/source_snapshot_ids`；value 为最小投影（engagement 3 键/emotion 3 键/srl 4 键），非 20 字段全量拷贝。契约测试断言 signal TTL == 权威表值 ✅
- 改动文件无对 ContextBuilderMixin 的引用或语义变更 ✅

## 3. 独立测试执行（串行，sqlite 内存库，SECRET_KEY 内联，未触碰 dev DB）

| 套件 | Worker 自报 | 我的实测 | 一致 |
|---|---|---|---|
| `tests/contract/test_decision_context_contract.py` | 15 | **15 passed** (15.29s) | ✅ |
| `tests/unit/test_context_pack*.py`（6 文件） | 12 | **12 passed** (9.86s) | ✅ |
| `test_state_aggregator_service.py` + `test_aggregator_schema_v1_{5,10,11}.py` | 16 | **16 passed** (5.66s) | ✅ |
| `test_context_focusing.py` + `test_memory_eval_service.py` | 21 | **21 passed** (1.98s) | ✅ |

**快照测试实质核验（非空壳）**：15 项 = schema_version 冻结 / 三 dataclass 字段名+顺序+(name,type) sha256 指纹双重冻结 / 四词表精确集 / 默认信号集 / ttl_or_epoch 规则正反例 / 词表违规+ref 格式违规 / validate 聚合 / JSON-safe 序列化 + omitted_counts MappingProxy 只读（TypeError 实测）/ cache_key 确定性 / **ContextPack 旧签名可构造 + decision_context 默认 None + `to_prompt_context()` 内外层 key 集精确冻结（prompt 面零变化被钉死）** / builder 填充（manifest 与注入集合精确互证、TTL==权威表、epoch、ref 前缀、why ⊆ 词表）/ 聚合器故障降级 / kill switch / goal→plan scope 规则 / 与 memory governance 共存。判定：**实质契约快照，冻结强度足够**。

**RED 独立复现**：临时移走 `app/core/decision_context.py` → `ModuleNotFoundError: No module named 'app.core.decision_context'`（收集期失败，与 Worker 自报逐字一致），已恢复原状 ✅

## 4. telemetry 遮蔽修复审查

- **缺陷属实**：HEAD 原码 telemetry 块（`if settings.ENABLE_CONTEXT_PACK_TELEMETRY:`）将 `pref_scores/goal_scores/episodic_scores` 就地从 dict 重绑为 list。**原代码中该块之后无任何再读取**（`grep` 逐行核实：最后一次使用在块前 1473/1477 行），故是潜伏缺陷，非既有行为错误。
- **修复正确且行为中性**：重命名为 `telemetry_*` 后，既有路径（块后仅 `original_usage` 循环与 `return ContextPack`）零行为变化；新代码因本卡在块后消费这两个 dict（`_build_decision_context` 的 `.get()`），不修则新功能必炸——Worker 在 RED 调试中实锤命中，叙述可信。
- 回归 12+21 passed 覆盖 telemetry 开启路径（默认 True），无回归。无守卫弱化（memory governance 共存测试通过）。

## 5. patch 完整性

- `changes.patch` 与工作树 diff 逐行一致（仅 index 行差异）✅
- 5 文件 +1267/-7：无 .env、无密钥、无 gen/SQLC 产物、无 proto、无迁移、无 schema.sql ✅
- settings.py 仅 +2 行（注释 + `ENABLE_DECISION_CONTEXT: bool = True`）；black 对该文件报的 3 处重排全在**既有** JWT 注释行（151-156/215-220），非本卡引入 ✅
- ruff 对 4 个改动文件全过；Worker 新增/改动行 black(120) 干净 ✅
- REPORT §2.2 备选取舍表与实现逐条相符：无 UserContextV3 ✅、默认 3 信号字段（task/context_sufficiency 未纳入，理由成立——pack build 无 turn parse 输入）✅、DecisionContext 不进 prompt（测试钉死）✅、ref 用记录 id ✅
- base SHA `2f52a972` 与 HEAD 一致；wt5 仓 main 自 base 起在涉改文件上无分叉（无冲突风险）✅

## 6. 非阻塞观察（建议随消费方接入卡处理）

1. **词表执行为 opt-in**：`validate()` 不在 `__post_init__` 强制，`frozen=True` 只防改不防造；未来新生产者若不走 builder 可构造出词表外值。建议消费方接入卡在构造路径（或 Aurora/Router 读取入口）调用 `validate()`，或升级为构造期断言。
2. **整段降级无直接测试**：kill switch 与逐字段降级均有测试，`_build_decision_context` 整体异常→None 路径仅靠代码审查（4 行 handler，风险低）。
3. **“无 Go/Dart 引用”表述略有过报**：`gateway/internal/db/models.go:2597` 有 `ContextPackFeedback/ContextPackRun`（CQRS 遥测**行结构**，非契约依赖），mobile 有 prefValue 内 `context_pack` map 键（非本契约）；REPORT §3.2 已如实披露 DB 行级消费，实质结论（纯 Python 契约、proto 零触碰）成立。
4. **命名邻近**：orchestration 已有 planner brief 的 `decision_context` dict 键与 `AuroraDecisionContext` 类型（非同名冲突）；新消费方 import 时注意区分 `app.core.decision_context.DecisionContext`。
5. plan item 的 `epoch` 在 `plan_context` 缺 `version` 时回退 `"unknown"`（实测该键存在，plan_context.py:99）；可接受。

## 7. 结论

C-01 交付与卡面、B-06 D-CTX 裁决完全一致：extend-only、字段/词表/兼容面冻结扎实、降级真实可达、无平行真源、proto 零触碰、全部自报测试数字经独立复跑吻合、telemetry 顺带修复经 diff 考古证实为行为中性且必要。5 项非阻塞观察不构成本卡验收障碍。

**VERDICT: ACCEPT**
