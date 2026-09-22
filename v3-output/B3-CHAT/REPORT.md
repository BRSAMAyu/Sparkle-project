# B3-CHAT · chat 屏面积重划（S8，severity 5）实施报告

> 卡号：B3-CHAT ｜ 批次：SPEC v1.0 批 3 首卡 ｜ worktree：wt123（基于 main@de2f24c2）
> 日期：2026-09-22 ｜ 纪律：LIGHT（零模拟器、零平台构建；仅 flutter test/analyze + 守卫脚本）
> 产物：`v3-output/B3-CHAT/changes.patch`（13 文件，+1614/−466）+ 本报告。未 commit/push。

---

## 0. 结论摘要

- **面积预算达成**：chat 屏会话本体（气泡流视口）在 canonical 390×844 下 **71.8%**（改前审计实测 ≈25%，S8）；常驻系统面板（记忆面板/六态条/模式 pill 行/建议大卡/accessory 三 chip）**常驻面积 0**。
- **等待分期诚实达成**（S18/§4.5）：三点 `_TypingIndicator` 退役（类已删除），首流前统一为单行 `ChatRunPhaseIndicator`——检索→思考→生成三态 + 「通常几秒到十几秒」预期 + 可取消，数据链沿用既有 `ChatRunPhase`/`aiStatus`，引擎协议零改动。
- **红线零接触**：chat 流式协议/V13 citations/BP-3B 纠正/NBP-1 记忆捕获路径未改动；对应回归测试 24/24 绿。
- **守卫三件套绿**：UX-COMP / DL-SPEC / UI-TOKENS ratchet 全 PASS（新增文件零基线增量，无需刷基线）。
- 既有失败 5 例均为基线已有（/tmp 基线克隆复现确认），与本卡无关，见 §5。

---

## 1. 五大件收容落点表（§5.2 系统件三合法形态）

| # | 大件 | 改前形态（审计 S8 证据） | 改后收容落点 | 合法形态 | 实现 |
|---|---|---|---|---|---|
| ① | 「AI 当前记住」面板 | 顶部常驻卡（含「0 条」空态占最贵位置），加载中/错误态也占位 | **消息旁微内联信号**：`ChatWorkingMemorySignal`（chip 级 SemanticPill「已记住 N 条」，**0 条/不可用时零面积**）；点开按需 bottom sheet 承载原 `ChatWorkingMemoryPanel` 全量操作（原 turn/忘记/标记正确，操作面无损） | §5.2-1 内联微件 | 新 `chat_inline_signals.dart`；条数走 `chatWorkingMemoryCountProvider`（失败→null→不渲染，杜绝「0 条」常驻） |
| ② | Aurora 确认队列（六态条） | 顶部常驻 StatusAwarenessBar（collapsed 单行+可展开确认层）+ 底部 `_AuroraQuickTrigger` 重复入口 | **收件箱单一入口**：AppBar 新增 `ChatInboxEntryIcon`（ghost icon + actionable 徽标）→ `/notification-center`（D8 收件箱）；**按需确认入口**：`ChatAuroraConfirmSignal` 单行 chip（仅 needs_confirm/risk_found/calibration_available 出现），点开按需 sheet 承载 `StatusAwarenessBar` 确认队列（确认对象同屏可见，§4.2.3）；常规状态零面积 | §5.2-2 收件箱 + 按需取用 | 轮询生命周期（原 bar 的 `startPeriodicRefresh`）迁至 `ChatInboxEntryIcon` 自有 30s Timer（独立启停，防双实例互停）；BGM 感官联动（`_syncAuroraSensoryState`）一并迁入；`_AuroraQuickTrigger` 类删除 |
| ③ | 模式条（均衡·标准对话·未绑定计划） | header `_DualCoreModeChip` + 底部 PlanSelector/AiReasoningMode/ChatModeSelector/GuidanceMode 四行 pill 常驻（非紧凑机不受折叠门控） | **输入条上方单行紧凑指示**：`ChatContextToggle` 全形态常驻单行（推理·对话·计划）；四 pill + 理解入口 + 过渡横幅全部收进折叠展开态（`_showContextControls`）；`_DualCoreModeChip` 撤出 header，改随阶段胶囊一行透明（仅 run 期间） | 输入条关联区折叠行（任务卡③款） | chat_screen `_buildBottomInputArea` 重构；`ChatUnderstandingDrawerButton` 移入展开态 |
| ④ | 「你现在可以先做」六 chip 建议卡 | 底部建议大卡常驻展开（idle 4 预测 + 2 话术 = 6 chip），话术点按**直接发送** | **输入条关联区 + C-11 填入式**：默认**收起为单行 headline**（SharedPreferences 默认值 true→false）；展开态同屏 chip 合计 **≤3**（`resolveChipBudgets` 纯函数：话术占 2 席、预测占剩余）；话术 chip 点按=**填入草稿+聚焦输入框**（发送键随文本高亮），不再直发 | C-11 裁决 | `chat_prediction_dock.dart` 预算化；`chat_input.dart` 新增外部 `controller`/`focusNode` 注入；chat_screen `_fillDraftFromPrompt` |
| ⑤ | 底部 dock 吞 swipe（V14） | 底部区 `SingleChildScrollView` 无条件 `ClampingScrollPhysics`，内容不溢出也捕获竖向拖拽 | **可测量的物理切换**：`_BottomAreaScroll`+`_MeasureSize`（RenderProxyBox post-frame 测高），内容不溢出（常驻态绝大多数情况）→ `NeverScrollableScrollPhysics`（不再吞 swipe）；溢出（模式行展开等）→ 保留 Clamping 兜底，A-5 防溢出契约不破坏 | V14 核验修复 | chat_screen 尾部新增两私有组件；配套收敛 `_calculateBottomPadding`（原值按已撤出的三行 pill 叠加，152/164 + 展开态增量） |

**附带收容（审计 S8 清单内的其余叠压件）**：ChatInput 常驻 accessory 托盘（学习资料/2 份资料可用/Aurora 理解错了？三 chip）新增 `showAccessoryTray` 门控，默认收进模式行展开态；顶栏为容纳收件箱入口并回应 S15「顶栏 8 元素密集」，openclaw/因果时间线并入「更多」菜单（徽标聚合attention）。回归接管屏（ComebackBanner→独立屏）属批 3 后续卡，本卡保留其事件驱动条件渲染。

---

## 2. 阶段胶囊实现方式（S18 / §4.5 / §8.2-2）

- **组件**：`lib/features/chat/presentation/widgets/chat_run_phase_indicator.dart`（类名 `ChatRunPhaseIndicator`——"Capsule" 语义类名被 UX-COMP 收归 core/design owner，features 域禁新增，故以 Indicator 落名）。
- **三态映射（纯函数 `resolveChatRunStage`，可静态断言）**：
  - `sending` + 无状态/`SEARCHING` 类 → **检索资料**；
  - `sending` + `THINKING/ANALYZING/PLANNING/REVIEWING/REASONING` → **思考中**；
  - `streaming`/`finalizing` → **生成回答**（阶段间 `chevron_right` 串联）。
- **预期时长**：单行内附「通常几秒到十几秒」（arb `chatRunPhaseDurationHint`）；**可取消**：尾部 close IconButton（语义「取消」）→ `cancelActiveRun(reason: 'phase_capsule_cancel')`，与 ChatInput onStop 同链路。
- **接线**：chat_screen 消息流内，首流前（`hasActiveRun && streamingContent.isEmpty`）吸收原 `AiStatusIndicator` 位与三点动画位——`_TypingIndicator` 类删除（§8.2-2「退役」）；首 token 到达后流式气泡照常接管。
- **语义**：外层 `Semantics(container+explicitChildNodes, liveRegion, label:「正在{stage}，可取消」)`——liveRegion 播报阶段切换；不整体声明 button（取消是独立 IconButton 语义节点，避免嵌套 button）。双核模式（`dualCoreMode`）以人话 label 随胶囊一行呈现，仅 run 期间。
- **动效**：激活段单点 700ms 透明度脉冲（G1 白名单内、无位移过冲，§2.2.1）；reduce-motion 走静态点（§2.3）。同屏持续源候选仅此一处且等待期结束即消失（§5.2-3 阶段胶囊完成即消失）。
- **协议零改动**：仅消费既有 `ChatRunPhase`（chat_state.dart）与 `aiStatus` 字段，未触 proto/gRPC。

---

## 3. 面积预算断言测试（P2-4 裁决：widget test 断言）

`test/widget/chat_area_budget_test.dart`——泵**真实 ChatScreen**（真实 provider 树 + 桩仓库，同 chat_history_sheet_regression 范本），带两轮会话消息，断言：

| 表面 | 视口实测 | 屏高 | 占比 | 断言 |
|---|---|---|---|---|
| **390×844（canonical）** | 606dp | 844dp | **71.8%** | **≥70% 硬预算（§5.1）PASS** |
| 375×667（小屏） | 429dp | 667dp | 64.3% | 回归下限 ≥62% PASS（披露值） |

- 同测试内置 **S8 撤出断言**：`ChatWorkingMemoryPanel`/`StatusAwarenessBar` 在屏上 `findsNothing`；`chatHeaderPanels` 实测 **0dp**（无事件时）。
- 小屏 64.3% 的缺口来自固定 chrome（AppBar 56 + 输入条区 ~180dp）的固定占比；结构性达标需输入条 overlay 化（底部区与列表叠压的结构改动），超出本卡五要素，登记为后续结构卡候选（REPORT §6）。
- 实测分解（390×844）：AppBar 56 + header 0 + 模式行 38 + ChatInput 90（tray 收起后）+ 底部杂项 ~54（含收起态建议单行）。

---

## 4. 红线面与回归统计

### 4.1 红线面（全部未触碰代码，仅跑测试证明）

| 红线 | 对应测试 | 结果 |
|---|---|---|
| V13 citations（历史回放引用） | `chat_message_model_citation_replay_test.dart`（4 用例） | 4/4 绿 |
| BP-3B 纠正链（纠正优先/确认载荷） | `aurora_correction_payload_test.dart` + `chat_input_correction_test.dart` + `memory_correction_test.dart` | 全绿 |
| NBP-1 记忆捕获面（工作记忆操作） | `working_memory_drawer_test.dart`（4 用例，操作面未改动仅迁移挂载点） | 4/4 绿 |
| 流式/WS 契约 | `websocket_chat_service_v2_*`（3 文件）+ `chat_notifier_stream/first_event_guard` | 全绿 |

红线专项合计 **24/24 绿**（`--concurrency=1`）。

### 4.2 chat 域全量回归

- 范围：`test/features/chat` + chat 相关 `test/unit`、`test/widget`、`test/goldens` + j5 闭包测试。
- 结果：**282 pass / 5 fail**；5 例失败全部为**基线已有**（以 /tmp HEAD 克隆复现确认），涉及文件与测试自 HEAD 零改动：
  1. `chat_design_language_widgets_test › avoid hard-coded Material shortcuts`——flagged `message_detail_view.dart:119`、`node_detail_sheet.dart:64`（initial commit 起即存在，非本卡文件）；
  2. `chat_design_system_dark_mode_test › avoids raw black and white`——flagged 同 `message_detail_view.dart`；
  3. `chat_design_language_widgets_test › chat polish widgets render in dark mode`——golden `chat_design_language_dark.png` 97.6% 像素差（golden 快照与 B2-3a token 变更/字体环境差异，goldens 目录未随 B2-3a 刷新；属批 2 golden 管道欠账）；
  4–5. `j5_frontend_closure_test` 两例——`unified_omni_bar.dart`（home 域）`SparkleThemeExtension not registered`（该测试泵的主题未挂扩展；基线克隆同样失败）。
- 本卡新增测试：**16/16 绿**（面积预算 2 + 阶段胶囊 9 + dock C-11 5）。

### 4.3 analyze 与守卫

- `flutter analyze`：本卡域 **0 error / 0 warning**（新增文件与改动文件；残留 info 为既有 directives_ordering 风格类）。全仓 error 仅剩基线已有：integration_test 环境性（~100）、`user_persona_screen_test` 的 `UserRepository.redeemCode` 未实现（D-REDEEM 引入的存量测试漂移）、proto 相关（worktree 需 `make proto-gen` 生成，本卡已在本地生成，不入 patch）。
- 守卫三件套：`check_ux_component_convention.py` PASS（parallelClass 145/146，新文件零增量）；`check_dl_spec_ratchet.py` PASS（offLadderDuration 184/186，新文件零增量）；`check_ui_design_tokens_ratchet.py` PASS（color 239/275、fontSize 719/727）。**未刷任何基线**。

---

## 5. l10n 与组件规范

- **arb 前缀领取**：`chatRunPhase*`（6 key）、`chatMemoryInline*`（2）、`chatAuroraConfirmChip`、`chatOpenInboxButton`——zh/en 双语入库，`flutter gen-l10n` 重新生成（生成物随 patch）；全走角色后缀（Label/Hint/Button/Chip），zh chip 文案 ≤6 字（「已记住 N 条」「待确认 N/M」）。
- **owner 组件**：信号行用 `SemanticPill`；按钮用 `SparkleIconButton`；无 `Color(0x…)` 字面量、无 `Colors.*`（info 槽一律 `DS.info`）；无 `Text('…中文…')` 硬编码；动效时长 700ms（G1 白名单）/200ms 内。
- **代码风格**：black(120)/ruff 不涉及；Dart 经 `flutter analyze` 干净。

---

## 6. 残留与登记（交主会话）

1. **小屏（<700dp）70% 缺口**：64.3%，需输入条 overlay 化结构改造（底部区与列表叠压），建议立后续卡；
2. **回归接管屏**（ComebackBanner→独立屏）：SPEC §4.5 批 3 项，本卡未动（事件驱动条件渲染维持）；
3. **chat_input.dart 553/585 行既有硬编码英文语义**（'Stop AI generation'）：存量，非本卡引入，随下一 copy 批清偿；
4. **基线已有失败 5 例**（§4.2）：golden 快照刷新与 home 域 j5 测试修复建议各立小卡；
5. **Aurora 确认进收件箱的引擎侧数据桥**（确认项落 `unified_notification` 数据模型）：当前为 chat 侧按需入口 + 收件箱路由，端到端数据聚合需 engine/gateway 配合，登记 D8 批 4 范围。

---

## 7. 收工核查（磁盘与工作区纪律）

- [x] 修改全部在 wt123 内；未 commit/push；主仓只读未触碰（曾因 cwd 歧义误读主仓 `mobile/lib/gen` 列表，已改绝对路径并 `make proto-gen` 于 wt123 本地生成，gen/ 为 gitignored 不入 patch）
- [x] `/tmp` 清理：`b3-baseline-j5`、`b3-baseline-check`、probe 探针已删
- [x] 无模拟器/无浏览器/无平台构建进程（LIGHT 达成）；`flutter test --concurrency=1` 分批执行
- [x] 持久产物仅两类：`v3-output/B3-CHAT/changes.patch` + 本报告（规范目录）
- [x] worktree 内 `mobile/build`、`.dart_tool` 随 worktree 生命周期回收（未入库、未落主仓）
