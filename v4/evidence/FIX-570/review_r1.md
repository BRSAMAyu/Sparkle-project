# FIX-570 独立审查 R1（reviewer: wtR1，未参与实现）

- 审查对象：`43da6829`（修复提交，7 文件纯 additive），台账头 `3ee3cf80`，base `0949da60`
- 审查日期：2026-09-28 ｜ 全部探针（M1/M2/M3）已 `git checkout --` 还原，审查结束时工作树干净、被审头未变

## VERDICT: PASS

## 靶点结论（按审查简报顺序）

1. **零生产 diff — 成立**。`git diff 0949da60 --name-status`：恰 8 文件 = 2 新测试（mobile/test）+ 5 证据件 + 台账 DYNAMIC_ISSUES.md 行更新；mobile/lib、backend、gateway、proto 零改动。
2. **①钉真实性 — 成立**。测试从 `TaskRoutes.routes` 真实装配 GoRouter（`navigatorKey` 全局根键）落 `/tasks/<uuid>/execute?origin=push&intervention_id=int-42`（wiring_test.dart:66-73），三重断言齐备（:106 闸类型 / :110-114 深链参数 / :118-124 仓储 404→已删除面）。非旁路 harness 的最强反证：M1/M3 直接变生产文件 task_routes.dart，钉立红。
3. **②裁量裁决 — 裁量成立（本审查最重项）**。`ef0901a5`（S02 一审 D2 整改）为被审 HEAD 祖先（merge-base 验证），其 diff 确证 `_currentScene` 写入+`_saveAmbientScene` 持久化从 `previousScene` 捕获后（门前）移至 `beginUserPlaybackSession()` 获批后。现文件 `mobile/lib/core/services/sensory_feedback_service.dart` 门序与声称行号逐字吻合：资产门 :600 → ambient 门 :611 → 会话获批 :619-623 → 提交点 :624-625。全文件 5 处 `_currentScene` 写入点清点：:209 初始化 / :270 D1 停止清空 / :624 获批后提交 / :645 stopAmbient / :675 dispose——门拒路径**零提前写**；提交点之后无门拒返回路径。故「门拒时回滚 previousScene」在现结构下无可回滚之物（回滚目标值恒等于现值），照台账补回滚=不可达死代码。裁量「先不写强于回滚」判断成立，无需照台账修法整改。
4. **②钉判别力 — 成立**。两钉亲跑绿（+2）。M2 重放（写入挪回 `previousScene` 捕获后、门前）：双红 exit 1，钉1 `Expected: AmbientScene.none / Actual: AmbientScene.rain`（残留）、钉2 `Expected: true / Actual: false`（重放被吞）——与 CH-2「none→rain 残留+重放被 `scene==_currentScene` 早退吞」逐字对应。
5. **mutation 独立杀（R1 自做）— 达成**。M3：闸仍在树上但 `taskId` 被路由丢弃（`taskId: 'dropped-by-router'`，U14 原始缺陷形态「路由忽略 :id」）→ 钉红 exit 1 于 wiring_test.dart:110 参数断言层，与 M1 的 :106 闸存在层为不同杀死面，验证钉的分层防御独立有效。
6. **回归与工具链 — 成立**。14 文件回归批亲跑 `+109: All tests passed!` exit 0；`flutter analyze --no-pub` `No issues found!` exit 0。
7. **台账行 — 成立**。V3-FIX-570 行 `OPEN → FIXED@43da6829`，②「结构性已闭合+钉缺失」裁量与门序行号均在行内登记。

## 编号发现

- **O1（Info，非阻塞）** `mobile/lib/core/services/sensory_feedback_service.dart:430` — `setAmbientScene(autoplay:true)` 仍在 playAmbient 各门**之前**持久化场景**偏好**（pref，非运行态）。门拒后 pref=新场景而运行态=none，设置页选中态显示可能与实际播放不一致。此为 base/main 同有的既有形态，且 CH-2 注册症状（运行态早退吞）不经过 pref——显式重放 `scene != _currentScene(none)` 恒可达（M2/钉2 实证）。不落入本卡裁量范围，留观察，不要求回滚。
- **O2（Info，非阻塞）** `v4/evidence/FIX-570/mutation_log.md` M1 记失败行号 `:107`，R1 重放实测栈帧为 `:106:5`——同一断言（闸类型 findsOneWidget），行号口径差 1，不影响结论。
- **O3（Info，非阻塞）** wiring 钉测试运行期打印 `_NotFoundTaskRepository` 的 `noSuchMethod` NoSuchMethodError 噪声（列表页其他 provider 加载触发，已被应用侧 try/catch 吞掉），测试确定性不受影响，全绿可复现。

## 命令与 exit code 清单（R1 亲跑）

| # | 命令 | exit | 结果 |
|---|------|------|------|
| 1 | `git diff 0949da60 --name-status` | 0 | 8 文件，零产品码 |
| 2 | `git merge-base --is-ancestor ef0901a5 HEAD` | 0 | 祖先成立 |
| 3 | `flutter test task_routes_fix570_gate_wiring_test.dart sensory_feedback_service_fix570_test.dart --no-pub` | 0 | +3 All passed |
| 4 | M1（gate→TaskExecutionScreen 直连）→ 路由钉 | 1 | 红 :106 闸消失 |
| 5 | M2（写入挪回门前）→ 两感官钉 | 1 | 双红：none→rain 残留 + 重放被吞（CH-2 逐字） |
| 6 | M3（taskId:'dropped-by-router'）→ 路由钉（R1 独立杀） | 1 | 红 :110 参数断言 |
| 7 | 14 文件回归批 --no-pub | 0 | +109 All passed |
| 8 | `flutter analyze --no-pub` | 0 | No issues found! |
| 9 | 每步探针后 `git checkout -- <file>` + `git status` | 0 | 还原，终态工作树干净 |

M1/M2 为复现实现方自验（独立重放成功）；M3 为 R1 原创独立 mutation，杀死面与 M1 互异。
