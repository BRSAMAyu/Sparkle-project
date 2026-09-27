# WT673-U06-STATES 交付报告

**工号**：wt673 ｜ **卡**：U-06 · L4 状态完备性注入与统一错误/等待语义（UX 线，Risk: medium，Reviewer: 1）
**分支**：`agent/node-b/wt673/u06` ｜ **Base SHA**：`2127a5c0`（发车时 main）｜ **实施 commit**：`636d964b` ｜ **Final SHA**：`f6fbc6b0`（合并态：已 merge main @ `fda4f975`，含 wt666/667/672/675/676 集成，**零冲突**）

---

## 一、git 双证判定：卡面已完成部分（不重做）

U-06 非空白卡。**wt358 已于 f644de3a 落地卡面主体**，双证成立：

1. **commit 证**：f644de3a 在 main 祖先链（`git merge-base --is-ancestor` 过）；
2. **树内产物证**：worktree HEAD 树内实存 `mobile/lib/core/state/` 四件套（surface_state 22 相位 1:1 代码化+14 失败族、surface_state_injection debug-only 注入探针、surface_state_view 统一渲染+死胡同守卫、staged_loading 500ms 分阶）+ `test/core/state/` 三测件（50 用例，闸门面 22 相位真实渲染覆盖率 1.0≥0.95）；
3. **下游链证**：wt365 U-08（3f8299eb+f6357fae）在 U-06 渲染面上补 liveRegion/骨架语义，卡族依赖真实成立。

**wt358 如实登记的残余**（=本卡续做空间）：①chat/galaxy 主屏未整面接闸门（登记为后续卡空间）；②simulator 证据 DEFERRED；③U-06 未入 fleet done 列表（.sparkle_v3_fleet_state.json done 无 U-06 条目，tasks.json 规格权威仍 TODO——按纪律本卡不碰 tasks.json，状态核正移交协调面）。

## 二、本卡续做实施（10/4 红线内：仅低风险统一项）

### B. 等待语义统一——语义接缝扩面（cognitive 三面，B-01 CORE feature 首次入册）

| 面 | 原状 | 统一后 |
|---|---|---|
| `cognitive.capsules`（curiosity_capsule_screen） | 裸 spinner+手写双语 loading 字面量（`I18nService.isChinese` 直读，绕过 arb 单源） | `StagedSurfaceLoader`（<500ms 骨架零噪音；>500ms arb 阶段文案升格+可离开提示；零裸圆形 spinner） |
| `cognitive.capsuleJobs`（capsule_jobs_screen） | 裸 spinner+**无 locale 判定的纯中文串**「正在同步生成任务...」（英文用户也见中文=i18n 缺陷） | 同上（根治） |
| `cognitive.capsuleDetail`（capsule_detail_screen） | 裸 spinner+手写双语字面量 | 同上 |

`surface_state_injection.dart` 登记表 `stagedSeamIds` +3（与代码接入点同步维护，覆盖率测试聚合断言恒成立）。

### A. 错误文案对齐既有令牌——原始异常透传清零（14 文件，全部用户可感知 sink）

统一形制：`uiErrorMessage(l10n, categorizeUiError(e))`（错误判定单源 error_lexicon，类别→人话），**零新增 arb 词条**（防与 U-10 撞 arb；复用既有 {error} 占位键或既有无参键）。异常细节一律先落本地 `detail` 变量再进 l10n 调用（N9 守卫 sanctioned 形制，见 §四）。

| 文件 | sink 数 | 原形态 |
|---|---|---|
| task/task_detail_screen | 3 | `loadZh ? '加载计划失败: $e' : ...` 手写双语拼接×2 + `taskDetailGuideGenerateFailed('$e')` 占位透传 |
| task/task_execution_screen | 1 | `taskExecutionAuroraDiagnosticUnavailable('$error')` |
| goal/goal_detail_screen | 2 | `'${l10n.goalDetailStart}: $e'`（按钮标签当错误前缀+泄漏）×2 |
| memory/memory_panel_screen | 6 | `memoryGovFailed('$e')` 等五键占位透传 |
| memory/understanding_overview_view | 6 | `provenanceErrorDetail(e) ?? '$e'`——服务端 detail 缺失时回落**原始异常** |
| memory/why_this_receipt_sheet | 1 | 同上 |
| memory/memory_detail_screen | 1 | `memoryCorrectionFailedWithDetail('$e')` |
| cognitive/capsule 三文件 | 4 | `capsuleLoadFailed('$err')`×3 + `capsuleSubmitFailed('$e')`（回落统一为类别人话） |
| user/system_updates_screen | 1 | `systemUpdatesLoadFailed('$err')` |
| community/user_search_screen | 2 | 错误 `'Failed to send request: $e'` + 成功 `'Friend request sent to ...'` 手写英文（成功改用既有 `friendRequestSent` 词条） |
| community/group_tasks_screen | 1 | `'${l10n.communityOperationFailed}: $e'` |
| community/accountability_detail_screen | 3 | `accountabilityLikeFailed/SendFailed/CheckinFailed` 前缀+泄漏 |

**查证后如实不动**（非用户面）：smart_push_settings（`UserFacingError.from(e)` 已是类型化封装+$e 仅入 logger）、action_card:3693（`'$e'` 系 retry_options 数据映射非异常）、各 provider 内 logger 行（诊断语义保留）。

### C. 如实登记不实施（重构级/越卡界，移交不虚报）

- **chat/galaxy 主屏整面接闸门**：维持 wt358 登记；chat 自有 ws 状态机（reconnecting/error 分支+AppFeedback 已齐），整面换闸门=重构级。
- **goal_trajectory_card / journey_progress 二级增强卡 `error→SizedBox.shrink`**：卡内注释已声明的设计决策（二级增强失败静默降级，空态不渲染空壳），改动属 UX 设计变更非低风险统一。
- **`.when(` 全 lib 括号平衡扫描=0 缺口**（49 初筛误报全部复核为嵌套闭包误判）：loading/error 分支纪律已全量成立。
- **剩余 34 处 CircularProgressIndicator 复核**：均为有界（按钮内进度/环形确定性 `value:`/图片区）或已带文案反馈（weekly_growth_narrative 卡 loading 态已配 `wgnLoadingNarrative` 文案）；核心面无终结态裸 spinner。

## 三、验收对照（卡面）

| 验收项 | 判定 | 证据 |
|---|---|---|
| 核心 surfaces state matrix ≥95% covered | 续做后成立（口径=登记表面） | 登记表 9 面（3 闸门+6 接缝）；闸门面覆盖率测试 22 相位 1.0；接缝面共享组件行为断言；本卡 +3 cognitive 面。**如实边界**：登记表≠B-01 全部 15 CORE feature——chat 闸门等维持登记残余，不虚报 |
| 所有错误有下一步 | 成立（已覆盖面） | surface_state_view 死胡同守卫（失败族无回调自动兜底「返回」）；capsule 三面错误分支自带 `onRetry`；本卡清零的错误面均经 toast/错误组件有类别人话 |
| 长等待 >500ms 有 stage feedback | 成立（扩面后） | StagedSurfaceLoader 500ms 阈值组件级测试 + cognitive 三面接入 |
| 无 terminal spinner | 成立（核心面） | 覆盖率测试断言统一组件 22 相位全程 `CircularProgressIndicator findsNothing`；核心面残余 spinner 复核均为有界/确定性（§二 C） |
| Work 1 可注入 network/model/auth/permission/conflict/partial/unknown | wt358 完成（双证） | `SurfaceFailureScenario` 14 场景 ≥12 类下限，kReleaseMode 守门不 mock 生产 |
| Work 2 统一组件和用户语言 | wt358+本卡续做 | 本卡错误文案单源对齐（上表）+等待组件三面统一 |
| Work 3 核心 Journey 自动注入 ≥12 类失败 | wt358 完成（双证） | 14 失败族+注入闸门 |

**Required evidence**：base/final SHA 见头部；targeted tests 95/95（§四）；**integration/simulator 证据 DEFERRED**（内存纪律：本机 swap 全程 <1.2G 门/有并行卡在航，widget 测试真实渲染树驱动为行为证据，非静态阅读——与 wt358/wt362 同口径不虚报）；**review receipt 待独立会话**（本卡自评 READY_FOR_REVIEW 不自行 DONE）。

## 四、验证件套（合并态复验：merge main @ fda4f975 后重跑）

- **flutter analyze**：`No issues found`（main 同口径同为 0，零新增）；arb 零触碰（gen-l10n 产物无差异需求）
- **定向 test（--concurrency=1，swap 门核验后执行）**：core/state 50 + capsule_detail 3 + understanding_overview 9 + memory_panel 4+goal_a6_l10n 3 + router_smoke 8 = **77/77 绿**（实施后）
- **合并态全量复跑**：上述+main_pages_load_smoke+community_remaining_closure+memory_auto = **95/95 绿**
- **守卫**：`run_all_rule_guards.sh` **86 条 exit 0**（合并态复跑 /tmp/wt673_guards3.log）
- **backend**：零触碰 → ruff/mypy 零新增口径成立
- **golden**：触达文件均非 golden 基线主体（chat/dashboard golden 面零触碰；错误/等待分支非 golden 捕获态）→ 走零触达留证口径，无 golden 重制需求
- **N9 棘轮基线刷新**（守卫自指令 `--update-baseline`，如实列明构成）：callSites bareCatchVar **78→76**（本卡 goal_detail/user_search/group_tasks/accountability 直排 lexicon 消灭既有占位命中）；同时入账**基线陈旧漂移**——arb {error} 308→260、assignmentFace 48→18 系**此前已合批次清理未刷新**（陈旧基线在只降不升语义下静默通过，本次如实锁定，非本卡行为变化）

## 五、FIX 号账（按预分配新规，本卡不自行占号）

- 发车时指令「V3-FIX-359 起」：grep 实占 357/358（wt671）；**359 随后被 wt666 占用**（撞号顺延在案）；**360 随后被 wt675 占用**（U-07「号段 357-359 已占用顺延用 360」）；361-363=wt672（U-10 renumber 批）；364=在航卡；365=wt675 renumber；366/367=wt678 预分配；368=wt676；369=wt679 预分配。**撞号根治新规（fda4f975）生效后号段由协调面 dispatch 预分配，wt673 未获号段，故本卡新账不自行占号。**
- **新发现待核拨**（OPEN，证据齐备，建议 P3）：`mobile/lib/main.dart:186-197` bootstrap 失败屏——`SelectableText('App failed to start:\n\n$e\n\n$stack')` 原始异常+完整栈直出终端用户，且无任何下一步（死胡同；违反 STATE_MATRIX「error terminal 给退路」与「所有错误有下一步」）。改动涉 bootstrap 行为=超出本卡低风险边界，建议后继卡收口（人话+重启入口+诊断码，栈走日志）。
- 本卡实施批 **FIX 零新增登记**（14 文件透传清零属 U-06 卡面本体语义统一，不另立账）。

## 六、并行卡避让记录

- wt666（backend insights）/wt670（backend mypy）：backend 零触碰 ✓
- wt667（mobile golden B-04）：golden 基线零触碰 ✓
- wt672（U-10 文案）：本卡 arb 零触碰、l10n gen 零触碰；UI 文件撞面=user_search/task_detail/memory_detail（wt672 改 label 词条与 hand-rolled 字面量，本卡改异常 sink，**同文件异 hunk**）——合并 main 实测**零冲突**（f6fbc6b0）；report 时点 wt672 已集成入 main，撞点风险已消解为已验证事实
- wt674/677/678/679：无同域触碰

## 七、运行级待验清单（移交）

1. simulator/真机 face-check：cognitive 三面分阶等待升格观感（500ms/2600ms 阶段推进节奏）与错误 toast 人话——需常驻引擎+真 LLM 窗口，协议链语义已由 widget 渲染树行为测试覆盖
2. `capsuleLoadFailed`/`memoryGovFailed` 等带 {error} 占位的 arb 键在本卡改用本地变量后仍被引用（无死键新增）；wt672 后续如做 {error} 键收敛，本卡触及的 19 处调用面已在台账
3. main.dart bootstrap 死胡同收口（§五待核拨号）
4. U-06 状态核正入 fleet done 列表+tasks.json（协调面权限，本卡不碰）
