# WT358-U06-STATES 交付报告

**工号**：wt358 ｜ **卡**：U-06 · L4 状态完备性注入与统一错误/等待语义（UX 线，Risk: medium，Reviewer: 1）
**分支**：`wt358-u06-states` ｜ **Base SHA**：`22f99776`（main @ 09-25 发车时，含 wt353 U-02）｜ **Final SHA**：`b208e60d`

---

## 一、交付内容

### 1. core/state 四件套（新，状态矩阵单一事实源）

| 文件 | 职责 |
|---|---|
| `mobile/lib/core/state/surface_state.dart` | STATE_MATRIX.md 22 相位 1:1 代码化（`SurfacePhase`）+ 失败族 14 类（≥卡面 12 类下限）+ 等待族 + `SurfaceNextStep` 统一动作语言 + 「失败族必有非 wait 可操作下一步」不变式 + 既有 `error_lexicon` 类别→相位**纯绑定**（判定仍单源 `categorizeUiError`，零新增判定；N35 offlineQueued→executing 不落错误通道）+ `AsyncValue` 接缝适配 |
| `surface_state_injection.dart` | debug-only 注入 provider（`kReleaseMode` 守门，release 恒等直通）+ `SurfaceFailureScenario` 14 场景目录 + gate/staged 两级核心面登记表。**不 mock/seed 冒充**：注入只发生在渲染闸门，与真实错误走同一渲染分支，不伪造数据、不旁路 provider |
| `surface_state_view.dart` | `SurfaceStateView` 统一渲染：失败族=图标+标题+**至少一个可操作下一步**（调用方未给回调时死胡同守卫自动兜底「返回」）；offline/reconnecting=非阻断横幅+动作；partial=降级横幅叠加主内容；等待族=分阶加载。`SurfaceStateGate` 唯一接入点（注入拦截→矩阵分派；empty 绝不隐式回落 content，防 requireValue 崩溃） |
| `staged_loading.dart` | `StagedSurfaceLoader`：500ms 阈值前只出骨架；超时升格 stage feedback（准备中→加载中→快好了，2600ms 推进）+「可离开」提示 + `onLeave` 返回退路（Recoverable wait）；紧凑形态供卡内接缝。`StagedStageHint` 供已有骨架面叠加。全程零裸 spinner |

### 2. 外科手术式接入（6 面，状态分支补齐+复用统一组件）

- **闸门面**（`gateSurfaceIds`）：`community.feed`（feed_tab_content 错误手写 Column→统一闸门，空态/数据逻辑原样）、`profile.context`（loading 从静默 shrink 升格分阶骨架；error 从 CompactErrorCard 升格统一语义，A-4 重试退路保留）、`plan.diagnosticQuiz`（裸 spinner→分阶；手写错误列→闸门重试）
- **分阶接缝面**（`stagedSeamIds`）：`home.dashboard`（骨架照旧，叠加 >500ms `StagedStageHint`）、`galaxy.nodeDetail.history`（裸 spinner→紧凑分阶）、`shared.loadingState`（默认 loading 裸 spinner→分阶；默认 error→人话+可选重试，`build()` 增加可选 `onRetry` 向后兼容）

### 3. 附带真缺陷修复（合并复验重点）

`mobile/lib/core/design/adaptive/emotion_responsive_theme.dart`（**wt353/U-02 遗留，非本卡战区**）：`extensions: <ThemeExtension<dynamic>>[...]` 与 `ThemeData.copyWith` 上下文类型不匹配——analyzer E0 但 **flutter test 前端编译必炸**，凡传递引入该文件的测试一律 `Failed to load`（wt353 自证「测试执行 DEFERRED」故未暴露）。改为 where+followedBy 复用 map 值类型，零显式标注。U-02 既有测试（emotion_responsive_theme_test/calm_low_stimulation_test）全绿背书行为不变。

### 4. l10n

arb +22 词条（zh/en 双语：4 阶段等待文案+长等待提示、12 相位标题、6 动作标签），`flutter gen-l10n` 重生成三件。复用既有 `retry`/`back` 词条。

---

## 二、验收对照（卡面）

| 验收项 | 证据 |
|---|---|
| 核心 surfaces state matrix ≥95% covered | `test/core/state/surface_state_coverage_test.dart`：gateSurfaceIds 3 面各经闸门对全部 22 相位**真实泵入渲染树**逐相驱动，断言覆盖=1.0（≥0.95 达标）；stagedSeamIds 3 面由共享组件行为断言覆盖；登记表与代码接入点一一对应 |
| 所有错误有下一步 | 矩阵不变式测试（失败族每相 `hasActionableNextStep`）+ 组件级死胡同守卫测试（14 失败相位无回调泵入，动作行永不为空）——该守卫在覆盖率测试驱动下反抓出 reconnecting 被等待族吞掉的真缺陷，已修 |
| >500ms 有 stage feedback | `StagedSurfaceLoader` 500ms 阈值测试（100ms 无文案/600ms 出文案/推进/长等待提示/紧凑形态/onLeave） |
| 无 terminal spinner | 覆盖率测试断言：统一组件对全部 22 相位渲染全程 `CircularProgressIndicator` findsNothing；三处裸 spinner 接缝（quiz/node_detail/loading_state 默认）已换分阶加载 |
| Required evidence | base/final SHA 见上；targeted tests 50+57 全绿（明细见三）；simulator evidence **DEFERRED**（内存纪律：swap 1136-1236M <1.2G 门，未起模拟器；widget 测试真实渲染树驱动为行为证据，非静态阅读）；review receipt 待独立会话 |

## 三、测试与门禁证据

- **新增定向**：`flutter test test/core/state --concurrency=1` → **50/50 绿**（矩阵 12+组件 31+覆盖率 7）
- **定向回归**（全绿）：node_detail_sheet 4、diagnostic_quiz+emotion_responsive_theme+calm_low_stimulation 22、dashboard_screen_structure+shared_state_widgets+loading_indicator+compact_error_card 22、main_pages_load_smoke+community_remaining_closure 17（真实泵入 CommunityMainScreen/ProfileScreen/FeedTabContent）、profile_rarity_accent+a11y_batch2+dashboard_growth_sections_l2 10
- **行为迁移说明**：node_detail_sheet_test 一处断言由「期待裸 spinner」改为「期待 StagedSurfaceLoader 且 spinner findsNothing」——该断言主体正是本卡要替换的旧行为，非弱化验收
- **analyze 门**：E0/W15/I587 = 合并态基线，零推高（gate 脚本 ✅）
- **守卫**：`run_all_rule_guards.sh` **84 条 exit 0**（/tmp/u06_guards.log）

## 四、Forbidden 自查

- 未重建既有权威真源：错误判定/文案单源仍是 error_lexicon，本卡只做类别→相位纯绑定；视觉预算复用 U-02 令牌体系（未另起体系、零新颜色）
- 未用 mock/seed 冒充：注入仅 debug 渲染探针、release 零生效；无任何假数据入库路径
- 未弱化安全/幂等/审计守卫：守卫 84 全绿；既有 A-4（profile 错误退路）、N35（offlineQueued 语义）、G-03（节点身份先见）行为均保持或升格
- 未以静态阅读宣称 UX 通过：全部证据为真实渲染树行为测试；模拟器证据如实标注 DEFERRED

## 五、交接与风险（供合并复验）

1. **emotion_responsive_theme.dart 属 wt353 战区**：类型修复 3 行级，语义等价（same elements, 类型正确化），建议主会话合并时让 wt353 侧复验一次
2. **与在航 wt356（导航入口）**：本卡未碰 `core/navigation/*` 与 `app/routes.dart`，无同文件冲突；`dashboard_screen.dart`/`profile_screen.dart`/`feed_tab_content.dart` 近期有 wt336/wt329/wt315 合入，本卡从最新 main 起步、逐 hunk 外科修改
3. l10n 三件为 gen 产物，随 arb 提交；合并若遇 arb 冲突以「尾部追加块」为界手工合
4. chat/galaxy 主屏未整面接闸门（chat 面近期合入密集+本卡窗口内不宜大动），其 ws 重连/加载既有分支保持原样——登记为后续卡空间，不虚报
