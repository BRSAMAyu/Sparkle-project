# FIX-570 修复回执 — U14 遗留双缺陷（深链闸路由接线测试钉 + playAmbient 门拒状态残留钉）

日期：2026-09-28 ｜ 分支：`fix/v4/f570-deeplink-pin-scene-rollback`（worktree `wtF570`，基于 main@0949da60）｜ 台账：V3-FIX-570（P3，U14 一审 CH-1/CH-2）

## 0. 定性（先读实现后落锤的裁量，与台账修法的落差如实登记）

台账修法原文：「①补路由接线测试钉；②门拒绝时回滚 previousScene」。执行时按实际代码状态复核：

- **①照修**：接线点 `mobile/lib/features/task/task_routes.dart:94`（`TaskExecutionDeepLinkGate(taskId/origin/interventionId)`）。U14 的闸测直泵 widget 不走路由表，`full_route_coverage_test.dart` 只查路径存在——还原接线（删 gate 调用）确实无测试变红。补路由级测试钉（见 §2）。
- **②判定为「结构性已闭合、钉缺失」**：CH-2 描述的「playAmbient 在门判定前写 `_currentScene`（:489 vs 门 :496，U14 时点行号）」在 main HEAD 已不存在——S02 一审 D2 整改（ef0901a5，2026-09-29 07:58，先于本卡派发提交 0949da60 入 main）已把写入与持久化移到**全部门之后**（资产门 :600 → U14 ambient 门 :611 → 焦点会话获批 :619-623 → 提交点 :624-625）。台账要求的语义「门拒后 `_currentScene` 不残留」以更强形式成立：**先不写，无需回滚**。在此形态下再添「门拒后恢复 previousScene」是死代码（门拒路径根本无写入可回滚），违背「修法最小化、只动门拒路径状态一致性」。故 ② 的落地物 = 为该不变量补可失败测试钉 + mutation 红证（与 ① 同构：无钉状态下的裸奔回归面）。此裁量与台账修法第一选项不冲突——台账文字是对 U14 时点代码状态的描述，其意图（门拒零残留、同场景显式重放可达）被原样钉住。

## 1. 向量（U14 一审 review_r1.md §7 CH-1/CH-2，v4/evidence/V4-U14/）

- **CH-1**：`task_routes.dart` 改经闸无自动化锚定。集成合并若还原接线，`/tasks/:id/execute` 重新忽略 `:id`、通知深链落到已删任务时渲染 activeTaskProvider 残留快照（错误任务）或泛化空面——U14 卡验收 3 的核心面回归且不可测。
- **CH-2**：release-only（`_ambientPlayer` 仅由 `_playSound` 懒 init；debug 走 SystemSound 早退构造不出播放器）。门拒调用若残留 `_currentScene=场景`，则 `setAmbientEnabled(true)`（不复位运行态）后，用户显式重选**同场景**被 `playAmbient` 首行 `scene == _currentScene` 早退吞掉——显式点播无响应。基线同构（基线门同位置同残留学生），非 U14 引入。

## 2. 修法

**零生产代码变更**（`git diff 0949da60..HEAD -- mobile/lib/` 为空）。两缺陷同构，落地物均为测试钉：

- ① `mobile/test/features/task/task_routes_fix570_gate_wiring_test.dart`（1 例）：从 `TaskRoutes.routes` 真实装配 `GoRouter`（`navigatorKey: navigatorKey` 全局根键，与 app/routes.dart:117 同约定），`initialLocation` 直落 `/tasks/<uuid>/execute?origin=push&intervention_id=int-42`。三重断言：
  1. 树中是**闸**（`find.byType(TaskExecutionDeepLinkGate)` findsOneWidget）——mutation 还原接线即红；
  2. 闸携带完整深链参数（`taskId == :id`、`origin == 'push'`、`interventionId == 'int-42'`、`missingReplacementRoute == TaskRoutes.home`）——「路由忽略 :id」形态即红；
  3. 闸真实消费确证路径：仓储以 `:id` 被调 1 次且 404 → 已删除面上树——该面只有闸能产出，接线断了它不存在（第二重红面）。
- ② `mobile/test/core/services/sensory_feedback_service_fix570_test.dart`（2 例，harness 与 s02 测同形制：audioplayers 平台接口假体逐调用记账；`init()` 显式建播放器 = release 形态「播过提示音后 `_ambientPlayer` 非空」）：
  1. **反·门拒零残留**：开关关闭时 `playAmbient(rain)` 被门拒 → `currentScene` 保持 `none`、持久化场景保持 `none`、零播放调用——写入挪回门前即红；
  2. **反·重放可达**：门拒 → `setAmbientEnabled(true)`（不自动续播）→ 同场景 `playAmbient(rain)` 显式重放 → 真实播放（`played == true`）且 `currentScene/savedScene == rain`——残留存在时被同场景早退吞掉（`played == false`）即红，CH-2 症状逐字复现。

## 3. 验证（本机实跑 darwin arm64 / flutter 3.41.3 stable，全 exit code 见 run_manifest.json）

| 面 | 结果 | 备注 |
|---|---|---|
| ①接线钉单跑 | **1 passed**（exit 0） | 正常路由过闸：闸上树 + 深链参数齐 + 404 落已删除面 |
| ②门拒钉单跑 | **2 passed**（exit 0） | HEAD 提交点形态绿 |
| mutation ①（删 gate 调用，还原 U14 前直连执行屏） | **1 failed**（exit 1） | `Found 0 widgets with type "TaskExecutionDeepLinkGate"`；还原后复绿 |
| mutation ②（写入挪回 ambient 门之前，CH-2 形态） | **2 failed**（exit 1） | 钉1 `none→rain` 残留 + 钉2 重放被吞 `Expected true / Actual false`；还原后复绿 |
| 回归批（U14 既有套件 + ambient/scene 相邻套件 + 路由覆盖，14 文件） | **109 passed, 0 failed**（exit 0） | sensory_{fix570,u14,s02,p2_10,base} + audio_focus_s02 + audio_asset_gate_s02 + unified_settings_{ambient_toggle,bgm,sfx_volume} + 闸测 + voice_input_u14 + full_route_coverage |
| `flutter analyze --no-pub` | **No issues found!**（exit 0） | 新文件零告警（一次 unused import 已修） |

两次 mutation 均以 `git checkout --` 还原，`git status` 复核仅余两个新测试文件，零生产 diff。

## 4. 产物 diff 摘要

- `mobile/test/features/task/task_routes_fix570_gate_wiring_test.dart`：新增（+150 行级）。
- `mobile/test/core/services/sensory_feedback_service_fix570_test.dart`：新增（+210 行级）。
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：V3-FIX-570 行 OPEN → FIXED@<fix sha>（随 state 提交）。
- `v4/evidence/FIX-570/`：五件套。
- 生产代码（`mobile/lib/`、`mobile/asset_ledger` 等）：**零触碰**——两缺陷的生产行为本卡交付时点已满足目标语义（①接线本就在位、②提交点本就在门后），本卡补的是可证伪性。

## 5. 残留与边界

- ② 的「release-only 可达性」根源（`init()` 无生产调用点、`_ambientPlayer` 由 `_playSound` 懒 init）是 S02/U14 既有形态：debug 构造不出播放器、release 播过提示音后可达。本卡不改 init 策略（扩面须先立卡）；两枚钉在测试内以显式 `init()` 构造同形态，mutation 证明其对 CH-2 回归敏感。
- `setAmbientScene(scene, autoplay: true)` 的 prefs 先写（:430）不属本卡：设置 pill 在开关关闭时置灰（R1-C4），门拒路径生产不可达；如未来放开 pill 置灰需先钉 `setAmbientScene` 的同款不变量（登记为观察项，非缺陷）。
- ① 钉覆盖执行路由；detail/create/list 三路由的接线（SceneAudioScope/TaskDetailScreen(taskId)）无闸语义，不在 CH-1 面。
