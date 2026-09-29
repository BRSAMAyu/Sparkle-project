# FIX-570 差量与证据面登记

分支：`fix/v4/f570-deeplink-pin-scene-rollback`（基线 main@0949da60）｜ 2026-09-28

## 1. 生产代码差量：零

`git diff 0949da60..HEAD -- mobile/lib/` 为空。两缺陷交付时点的生产行为已满足目标语义：

- **①** 闸接线本就在位：`mobile/lib/features/task/task_routes.dart:94`（基线行号）`TaskExecutionDeepLinkGate(taskId: taskId, origin: origin, interventionId: interventionId)`。缺陷在可证伪性（无钉），不在接线本体。
- **②** 门拒零残留语义本就在位：`playAmbient`（`mobile/lib/core/services/sensory_feedback_service.dart:582`）的 `_currentScene` 写入 + `_saveAmbientScene` 持久化在**全部门之后**提交（资产许可门 :600 → U14 ambient 门 `if (!await isAmbientEnabled()) return;` :611 → 焦点会话 `beginUserPlaybackSession` 获批 :619-623 → 提交点 `_currentScene = scene; await _saveAmbientScene(scene);` :624-625）。这是 S02 一审 D2 整改（ef0901a5，2026-09-29，先于本卡派发提交 0949da60 入 main）落下的形态，比台账修法「门拒绝时回滚 previousScene」更强：先不写，无需回滚。再补显式回滚是死代码，故不加。

## 2. 本卡差量（全部 additive）

| 文件 | 性质 | 内容 |
|---|---|---|
| `mobile/test/features/task/task_routes_fix570_gate_wiring_test.dart` | 新增 | ① 路由级接线钉 1 例：真实装配 GoRouter 落深链，断言闸上树 + 深链参数齐 + 404 确证落已删除面 |
| `mobile/test/core/services/sensory_feedback_service_fix570_test.dart` | 新增 | ② 门拒状态一致性钉 2 例：门拒零残留 + 门拒后同场景显式重放可达 |
| `v3/06_agent_fleet/DYNAMIC_ISSUES.md` | 台账行状态 | V3-FIX-570 OPEN → FIXED@<fix sha>（随 state 提交） |
| `v4/evidence/FIX-570/` | 证据 | 五件套（receipt / run_manifest / test_results / 本文件 / mutation_log） |

## 3. 既有测试零改动

U14 既有套件（task_execution_deep_link_gate_test 5 例 / sensory_feedback_service_u14_test 10 例 / voice_input_provider_u14_test 3 例等）与相邻 ambient/scene 套件一字未动；回归批 109 passed 为纯运行证据，非断言修改所得。

## 4. 行为差量

无（生产行为零变化）。两枚钉定义的行为契约即 U14 一审 CH-1/CH-2 挑战的回归面：

1. `/tasks/:id/execute` 必须经闸路由（闸消费 `:id`/`origin`/`intervention_id`，404 落已删除统一面）；
2. ambient 门拒的 `playAmbient` 调用必须零运行态/持久化残留，且其后「重开开关 → 同场景显式重放」必须真实可达。
