# DL-R1-AUDIT · Top 20 UX 罪状代码级现状验证（TRIAGE）

> 2026-09-22 ｜ 验证员 worktree wt83（分支 wt83-v3，HEAD=75a3157f，与 main 同步）｜ 零代码改动（LIGHT 静态验证）
> 输入：同目录 AUDIT.md（B-04 截图基线自审报告）。方法：以当前 HEAD 代码为准逐条重新定位证据，区分「已被修复链修掉」与「仍然存活」。
> 修复链背景核对：FIX-51(33401769)/52(5f544bb3)/53(d693cca7)/54(d8754597)/55(c4ca4b13)、U-01 Step0-7（4799997d…7590aa1a）、295fd59a(U-03) 均在本树历史内，逐条看过 commit 与落点代码。

---

## 0. 总表

判定口径：`已修复`＝修复 commit 在案且当前代码核实；`部分修复`＝修复链覆盖了一部分，剩余部分存活；`仍存在`＝当前代码仍可复现报告证据；`需运行时`＝静态无法终判（附验证方案）。

| # | 罪状（严重度） | 现状判定 | 当前证据（file:line，wt83 HEAD） | 修复落点 |
|---|---|---|---|---|
| S1 | 单色米棕海洋（4） | **仍存在** | token 层有语义色（design_system.dart:605-611 success/warning/info 经 theme_manager.dart:713-722 管理），但无第二/三层级色阶与冷色使用规范；U-01 Step5 只清了颜色字面量（136→100），未建层级 | 设计 token 层＋设计规范（新增层级色阶 token），非单点代码 |
| S2 | 机话与数据字面量直出（5） | **仍存在**（5 个代表例全部存活，见 §3 深挖） | goal_detail_screen.dart:249/:253、pending_commitments_section.dart:55、memory_panel_screen.dart:850、experience_readouts.py:186、test_galaxy_concurrency.py:25 | engine 数据格式化层＋mobile 数据词典（新组件 `enum→文案` 映射） |
| S3 | 截断与折行成片（4） | **仍存在** | chat_screen.dart:1240-1247 静态标题「AI学习助手」(arb:1953) 在 Expanded 内 maxLines:1+ellipsis，被 :1264-1311 的 4 icon+popup 挤压 → 必现「AI…」；arb:1141 personaGoalHint「例如：备考期末 / 学会Flutter」未改；intent_prediction_bar.dart 全 ellipsis 无渐隐/滚动提示 | mobile UI 布局＋l10n 文案＋截断规范（ellipsis/渐隐/滚动三选一策略） |
| S4 | 字号即层级失效＋装饰图表（3） | **仍存在** | fontSize 字面量：chat+home 310 处、全部 features 1293 处（U-01 仅收了按钮/chip）；statistics_card.dart:101-130 折线图 left/right/top `AxisTitles()` 全空、gridData 关闭，且数据是**硬编码 FlSpot**（:91-98）——纯装饰图 | typography token 迁移（长期）＋图表组件规范（轴/单位/口径三要素） |
| S5 | 星图亮暗两截＋标签噪声（4） | **仍存在** | star_map_painter.dart（现路径 features/galaxy/presentation/widgets/galaxy/）仍 2793 行，`_selectVisibleNodes` LOD 在 :344/:922，**无标签碰撞消隐 pass**（唯一 overlap 命中是 :2506 hit-test）；galaxy_screen.dart:2799-2806 局部暗主题只包屏内内容，shell_navigation.dart:242 galaxy 是 shell tab、底导航无按路由沉浸化/隐藏 | engine 无涉；mobile painter 标签消隐＋shell 导航按路由换肤 |
| S6 | home 装饰超预算（3） | **部分修复** | 7729f5a1(Step2) 门控 1→6 挂载点：particle_layer.dart:118-127（low→关、medium/disableAnimations→静帧）、effect_layer.dart:23-28（同）、background_layer.dart:89-91（ultra/high 才开重效）；**weather_layer.dart 零门控仍直通**；预算数字裁决机制仍无（particle 202/glow 85/BoxDecoration 178/渐变 51，home 现量粗口径） | mobile 层门控补全（weather）＋装饰预算守卫（可入 rule_guard） |
| S7 | 数据自相矛盾（5） | **仍存在**（深挖见 §1） | arb:9004 `taskBoardNoTasksToday` 与 arb:9212 `taskBoardTodayNoTasks` 双 key 均在，分别被 task_board_card.dart:271 与 task_board_provider.dart:26 引用；「今日任务」三源口径互不相认（§1 对照表） | provider 层「今日任务单一事实源」裁决＋arb 去重 |
| S8 | chat 首屏被系统件挤占（5） | **部分修复** | chat_screen.dart:1389-1439 顶部仍叠 8 件系统组件（WorkingMemoryPanel/StatusAwarenessBar/UnderstandingDrawerButton/ResumeBanner/DualCoreModeChip/ReviewNodeBanner/DailyStartupRetryBanner/ComebackBanner）；改善面：ChatWorkingMemoryPanel 有 _expanded/_dismissed（working_memory_drawer.dart:38-39）可折叠可关；面积预算与折叠策略仍无 | mobile chat 屏面积预算（折叠策略/收进 dock） |
| S9 | 一答十 chip＋chip 语言分裂（4） | **部分修复** | U-01 Step1(c99838d5) 守卫口径 rawChip 75→11；owner SemanticPill 采用 79 refs/38 files；但 features 内仍有 **178 个私有 chip/pill 类（119 文件）**，status_awareness_bar.dart:1093-:1426 **7 个私有 pill 类原样健在**（与报告所指一致） | mobile 组件迁移门禁＋status_awareness_bar 专项收敛 |
| S10 | home 底部三叠层＋首屏无操作入口（4） | **仍存在** | dashboard_screen.dart:619-713 仍挂 15+ slot（understanding 卡无 collapse/dismiss——understanding_snapshot_card.dart 通篇无相关逻辑）；UnifiedOmniBar+快捷 chip+5Tab 三叠层结构未动（:192-244 omni 高度管理） | IA 层面积预算＋slot 裁决（结构批） |
| S11 | 空态当内容＋悬空主 CTA（4） | **仍存在** | minimum_criteria_card.dart:76-99：`thresholds.isEmpty` 时显示「还没有最低达标线」，但确认按钮块 `if (!criteria.isConfirmed)`（:84）**独立于 emptiness 渲染** → 空态+「确认」FilledButton 悬空实锤；arb:12517-12518「初始画像/点击展开/收起」文案原样 | mobile 空态组件规范（空态禁主 CTA）＋该卡一行逻辑修复 |
| S12 | galaxy 状态链三连故障（5） | **部分修复**（大头已修，深挖见 §2） | V25 已修（FIX-55）；V24 已修三层（FIX-52/53/54＋galaxy_screen.dart:415-421 加载门）；V26 客户端侧已修（FIX-51 receiveTimeout:null，30s+5s≈35s 周期来源消除），**引擎端 SSE 无 heartbeat 欠账仍在**（app/core/sse.py:181-211） | 已修部分维持；剩余：engine SSE heartbeat＋运行时复测 |
| S13 | 保存/确认语义混乱（3） | **仍存在** | unified_settings_screen.dart（现路径 lib/features/user/presentation/screens/）:553-560 AppBar「确定」SparkleButton.ghost 的 onPressed **只做 `context.pop()`**——假保存按钮实锤（原报告行号已漂移，逻辑未变）；pending_commitments_section.dart 无 overdue/expired 逻辑（0 命中），过期承诺仍挂待处理 | mobile：脏状态标识或按钮语义改名；memory 过期态 |
| S14 | 控件歧义＋选中态弱对比（3） | **部分修复** | interactive_task_card.dart:101-117 仍是「快完成钮+chevron」并排，但完成键已**带文字标签**（task_card.dart:205 起为「完成」文案 pill），chevron 亦有 AnimatedRotation 展开反馈——歧义减半；裸图标 chevron 紧邻按钮＋选中态对比度规范仍无 | 设计 token（selected 态对比度）＋控件层级规范 |
| S15 | 导航断链：/tasks 无入口＋设置页双无障碍（3） | **仍存在**（子项2存疑） | /tasks 注册在 task_routes.dart:19-20；正常态唯一入口=看板头 onOpenTasks（dashboard_screen.dart:637/:1156）；:489 处「打开任务列表」按钮**只在 _buildFirstGoalEmptyState(:404) 空态里**——正常态无「任务库」入口卡；settings 无障碍独立卡现 :687-697 单处，报告所称「折叠项内嵌第二处」静态未见（可能已收敛，需实机确认） | IA：任务库入口卡；settings 卡视觉语法区分 |
| S16 | 动效令牌多套并存、数值打架（3） | **仍存在**（深挖见 §4，报告有一处需修正） | 同名 token 数值双轨：DS.motionDuration（design_system.dart:1061-1088）映射 standard→220ms/hero→620ms，而 sparkle_route_transition.dart:54-77 **内联复制了一份映射** standard→200ms/hero→300ms——同一个 SparkleMotionToken 枚举，两个数值体系 | mobile：路由内联映射改调 DS.motionDuration（一处收敛） |
| S17 | 庆祝/氛围动效无预算终审（3） | **部分修复** | 双重庆祝已修：7590aa1a(Step6) 移除 task_feedback_dialog 的 SparkleConfetti 双挂载＋_showStreakCelebration 死代码链；task_execution_screen.dart:91/:277/:383/:1173 现为单一 owner 挂载（_playCompletionConfetti 单开关）；UX-COMP 守卫已入 manifest（Step7）。**每屏特效层数/粒子数/celebrations 上限的数字裁决仍无** | 守卫层（数字预算入 rule_guard） |
| S18 | 假卡：等待反馈无进度感（4） | **部分修复**（默认观感需运行时） | 分期数据链已在：chat_state.dart:11-22 `ChatRunPhase{idle,sending,streaming,finalizing,…}`＋chat_screen.dart:2778-2800 TransparencyFloatingCapsule（runPhase/当前 agent/activeTools/step index）；M6-09 中断保留=可取消已在。但 _TypingIndicator 三点动画仍在（:1552/:3531），胶囊默认可见性受 TransparencyDisplayMode 条件控制——3-7s 静默期用户实际看到什么需实机确认 | mobile：默认等待观感策略（分期可见性/骨架） |
| S19 | 加载语言分裂（3） | **部分修复** | 双 skeleton 家族已统一：4799997d(Step0) shimmer 4 类迁入 sparkle_skeleton.dart 单 owner、loading_indicator.dart 剥离骨架职责、死文件 async_state_builder 删除；守卫口径 rawSpinner 79→8（76847722）。但本验证粗口径 features 内仍散布裸 CircularProgressIndicator/LinearProgressIndicator 约 103 处/79 文件（与守卫口径不同，见 §5 申报）；「骨架必须匹配最终布局」验收仍无 | 守卫口径对齐＋骨架贴布局验收规范 |
| S20 | 冷启动 900ms 编排＋首屏重装饰（3） | **部分修复**（定性修正） | splash_screen.dart:28-29 的 900ms 四段编排未改，但它**与 auth 判定并行、不阻塞**：app/routes.dart:127-159 isLoading 期间停在 splash、auth 完成即 redirect（报告「900ms 在任何 auth 判定之前就开始跑」的隐含"串行阻塞"不成立）；:48-49 `_kPendingRedirectQuery` 已保深链（M6-04 修复）。剩余真实成本＝home 首帧重装饰（衔接 S6） | home 首帧减配（装饰延后一帧/卡槽懒加载） |

**统计：已修复 0 ｜ 部分修复 9（S6/S8/S9/S12/S14/S17/S18/S19/S20）｜ 仍存在 11（S1/S2/S3/S4/S5/S7/S10/S11/S13/S15/S16）｜ 需运行时 0（作为独立判定；S12-V26、S18 含运行时子项）**

> 判读：修复链（FIX-51~55、U-01 Step0-7）集中消化了「功能性故障＋组件收敛」，20 条里 9 条已部分受益；但「数据词典、单一事实源、面积/装饰预算、动效数值收敛」四类系统性缺口对应的 11 条原样存活——与 AUDIT.md §7 交叉根因判断一致。

---

## 1. 深挖 S7 · 数据自相矛盾

### 1.1 双 key 现状（报告证据核实：仍在）

- `mobile/lib/l10n/app_zh.arb:9004` `"taskBoardNoTasksToday": "今日无任务"`
- `mobile/lib/l10n/app_zh.arb:9212` `"taskBoardTodayNoTasks": "今日无任务"`
- 消费者（均不跨屏，同在任务看板域）：
  - `task_board_card.dart:271`（`_summaryLabel`）→ 用 `taskBoardNoTasksToday`
  - `task_board_provider.dart:26`（`TaskBoardTodaySummary.label` getter）→ 用 `taskBoardTodayNoTasks`
- 性质修正：两处消费**同一份** `TaskBoardTodaySummary`（同源于 taskListProvider），双 key 是纯 i18n 重复债；**同屏矛盾的真实来源不是"两个数据源各说各话"，而是头部"今日"口径与正文"本周/无日期"分组口径相邻呈现、无调和表达**。跨屏矛盾才是多源问题（见下）。

### 1.2 「今日任务」三源对照（单一事实源缺失的证据底稿）

| 数据源 | 计算位置 | 「今日」口径 | 呈现 |
|---|---|---|---|
| ① 任务看板（header/summary/分组） | `task_board_provider.dart:204-226`，源=`taskListProvider`（task_provider.dart:1350 TaskNotifier → /tasks API） | **客户端过滤**：`isSameDay(task.dueDate) \|\| isSameDay(task.completedAt)` | 「今日无任务」header＋今日/本周/无日期分组 |
| ② goal 详情「今日最小下一步」 | `goal_detail_provider.dart:330-356` `TodaysMinimalNextStep.hasTask = taskId!=null && title!=null`，源=引擎 goal-detail API 字段（today_next_step） | **引擎计算**：只看有没有"下一步任务"实体，与 dueDate 无关 | 「今天没有待执行任务」（goal_detail_l10n.dart:40，硬编码绕过 arb） |
| ③ home 快照/驾驶舱（理解卡、达标线、风险） | `understanding_snapshot_card.dart:20` → `understandingSnapshotProvider` → 引擎 experience API（experience_models.dart:160-193） | **引擎聚合**：快照 criteria/风险/进度，独立时间窗 | 「图论概念梳理完成 0/1」「风险：…」等叙事 |

三源各自取数、各自判定"今天"，无任何对齐机制——这就是 home 指挥台「0/1」、goal 详情「今天没有待执行任务」、看板「今日无任务 vs 本周 3 个」互相打架的结构性原因。
附：goal 详情域存在**私有硬编码词典** `goal_detail_l10n.dart`（约 80 条 zh/en 三目字符串），与 arb 内同前缀 key（如 arb:14416 `goalDetailMinimumLine`）双重定义并存——翻译层碎片化的典型现场。

---

## 2. 深挖 S12 · galaxy 三连故障

### 2.1 V25 审核流 crash → **已修复**（FIX-55, c4ca4b13）

- 根修：`galaxy_draft_review_screen.dart:634-635` 现为 `.toList()..removeLast()`（growable，安全）；FIX-55 把 `toList(growable:false)..removeLast()` 的一行改为语义不变。:278 另一处 `toList(growable:false)` 后无 removeLast，安全。
- 双溢出：`_DraftReviewCard` 中部收进 `Expanded(SingleChildScrollView)` 弹性沉没点。
- 测试：新增 `galaxy_draft_review_screen_test.dart`（198 行，红→绿）。**建议修复排期只留一条实机回归。**

### 2.2 V24 首载假空态 → **已修复**（三层防线，均在当前代码）

1. 上游：FIX-53(d693cca7)/FIX-54(d8754597) 网关 GetGraph 等 5 个 gRPC 载荷形状对齐 REST（galaxy_handler.go 显式映射＋shape 测试）。
2. 解析层：`galaxy_model.dart:199-204` gRPC 形状别名（`node_id→id`、`label→name` 等，P1-13 null-safe）。
3. 仓库层：`enhanced_galaxy_repository.dart:55-91` 契约守卫——声明节点但解析出 0 可用 → 抛 `GalaxyGraphContractException`（:589/:599），**failure 不写 10min 缓存**，UI 呈可重试错误态而非空宇宙。
4. 屏幕层兜底：`galaxy_screen.dart:415-421` 显式注释的加载门——`isLoading && nodes.isEmpty && _graph==null` 时跳过空图应用，「加载中≠空」判定成立。

### 2.3 V26 SSE 每 ~35s 重连 → **客户端侧大概率已修；服务端欠账仍在；需运行时复测**

- 35s 数值溯源成立：FIX-51 前客户端全局 `receiveTimeout=30s` 把静默期误判断流＋`galaxy_provider.dart:450-451` 断流后 5s 重连 Timer → 30+5≈35s 周期。
- FIX-51(33401769) 当前现场：`galaxy_repository.dart:75-89` 改用 `_apiClient.dio`（带 auth/device 拦截器）＋请求级 `receiveTimeout: null`（:84-86，注释明示原因）——周期性断连的两个客户端因子（恒 401＋30s 超时）均已消除。
- 残余风险（静态确认）：引擎 `app/core/sse.py:181-211` `event_generator` 阻塞在 `queue.get()`，**无 heartbeat/ping 机制**；网关 `galaxy_handler.go:911` ProxyToBackend 仅设 `FlushInterval=-1`(:49)。链路上任何中间层 idle 超时仍可杀静默连接。
- 运行时验证方案：logcat 抓 `/galaxy/events`，静置 3 分钟，断言 0 次 reconnect；对照 B-04 的 V26 logcat 模式。

---

## 3. 深挖 S2 · 机话直出五例「翻译层缺失点」清单（数据词典批次施工图）

> 反例先立标杆：`plan_context_summary.dart:398-423 _statusLabel` 已给 plan 状态做了词典（active/paused/completed/archived→l10n）——翻译层该长这样，以下 5 例全部缺这一层。

| # | 用户看到的 | 原始字符串进入 UI 的完整路径 | 翻译层缺失点（精确位置） |
|---|---|---|---|
| 1 | 「图论概念梳理完成 **>= 1boolean**」 | 引擎生成 `goal_decomposition_service.py:147-157`（`{threshold:"1", unit:"boolean"}`）→ 引擎拼接 `experience_readouts.py:177-187 _criterion_label` 的 `f"{title} >= {threshold}{unit}"` → mobile 透传 `experience_models.dart:176`（criteria）＋`:261-274 _readableLine`（map 命中 `label` key 原样返回）→ 渲染 `understanding_snapshot_card.dart:138 _TinyEvidenceChip` | ①引擎 `_criterion_label`：unit 为枚举型（boolean）时不应数值化拼接，应整句词典化（「完成「X」即达标」）；②mobile `_readableLine` 无 unit/type 词典兜底 |
| 2 | 「截止： **2026-09-20 15:00:00.000**」 | `pending_commitments_section.dart:55`：`'截止: ${c.dueAt}'`——DateTime 原始 toString 直出（且 '截止: ' 硬编码中文，绕过 l10n 双重违规） | 该行：`DateFormat`/`l10n.dateFormat` 格式化＋文案入 arb |
| 3 | 状态 chip「**active**」「**normal**」 | `goal_detail_screen.dart:249` `label: data.goal.status` 与 `:253` `label: data.goal.priority`——引擎枚举原样进 `_InfoChip`（semanticsLabel :250-251 同样直出） | 该两行：status/priority 枚举词典（可复用/扩展 plan 的 _statusLabel 模式，升为共享组件） |
| 4 | 「**completed …**」事件名堆叠 | `memory_panel_screen.dart:850` `_buildGoalCard` 的 `subtitle: item.status` 原始状态直出；另 `:825` `'Q ${qualityScore.toStringAsFixed(2)}'` 机器指标 pill、`:886-898` 原始 tags 直出 pill | :850 状态词典；:825 Q 值应隐藏或释义化；tags 入词典或过滤 |
| 5 | 「**并发测试节点-5c2d9cff**」 | **测试数据污染**：`backend/tests/unit/test_galaxy_concurrency.py:25` `name=f"并发测试节点-{node_id.hex[:8]}"` 直接写业务库（AsyncSessionLocal），**全文件无 cleanup/teardown fixture**（文件尾只有断言）→ 节点永久留存并被真实星图查询命中 | 测试卫生：加 fixture 清理（或独立测试 schema/事务回滚）；一次性清库脚本（scripts/devtools/）。mobile 无需改 |

---

## 4. 深挖 S16 · 动效令牌现状（对报告的一处修正）

**文件级「三套并存」仍在，但数值关系与报告描述有出入：**

1. `animation_token.dart:23-31` AnimationSystem：standard 220ms / normal 250 / slow 400 / hero 620 / pageTransition 350——未变。
2. `motion.dart:20-29` SparkleMotion：**并非第三套数值**——`fast=AnimationSystem.quick`、`normal=AnimationSystem.normal`、`slow=AnimationSystem.slow`、`slower=AnimationSystem.deliberate`，纯别名（三文件自 clean-slate 初始提交 1722e6dc 后从未改动，别名关系从一开始就在）。报告把它当作第三套数值体系，属误判。
3. **真正的数值打架在"同一个枚举的两份映射"**：
   - `design_system.dart:1061-1088 DS.motionDuration`：SparkleMotionToken.standard→AnimationSystem.**standard(220ms)**、hero→**620ms**；
   - `sparkle_route_transition.dart:54-77 buildSparkleTransitionPage` **内联重新实现了一份 switch**：standard→**200ms**、hero→**300ms**（含各自的 reverse 时长表）。
   - 结果：组件动画里 standard=220/hero=620，页面转场里同名 token=200/300。报告观察到的"路由与组件时长语言不一致"成立，根因即这份内联副本。

**引用计数（rg 精确口径，排除定义文件）：**

| 体系 | 引用 |
|---|---|
| AnimationSystem | 42 refs / 7 files |
| SparkleMotionToken | 131 refs / 48 files（含 51 files 经 sparkle_route_transition 走路由转场） |
| SparkleMotion（别名类，严格词界） | 17 refs / 4 files |
| 裸 `Duration(milliseconds:)` 字面量（lib/features） | **373 处**（长期债，另账） |

**修复落点（一处收敛）**：`sparkle_route_transition.dart` 的两份内联 switch 改调 `DS.motionDuration`（保留 reduce-motion 140ms 直通——该无障碍分支在 :46-49 健在），删掉数值副本；hero 620 vs 300 的语义差通过给 token 表加"路由级缩放系数"裁决而非双表并存。触达文件 ~2，收益覆盖 131 处引用。

---

## 5. 修复批次草案（排期用）

### 批次 A · Quick-win：copy＋数据词典（预计触达 10–14 文件，观感收益/成本比最高）

| 动作 | 文件 | 说明 |
|---|---|---|
| criteria 拼接词典化 | backend/app/api/v1/experience_readouts.py:186；goal_decomposition_service.py:153 | boolean 型 unit 走整句模板 |
| status/priority 枚举词典 | mobile goal_detail_screen.dart:249-253 | 建 `enum→l10n` 共享映射（参照 plan _statusLabel） |
| memory 状态/指标直出清理 | mobile memory_panel_screen.dart:850/:825（tags 视情况 :886-898） | |
| 截止时间格式化 | mobile pending_commitments_section.dart:55 | DateFormat＋文案入 arb |
| arb 双 key 去重 | mobile l10n arb :9004 vs :9212 | 留一个，改 2 个消费者 |
| 测试污染清理 | backend/tests/unit/test_galaxy_concurrency.py ＋ scripts/devtools/ 清库一次性脚本 | fixture＋存量「并发测试节点-*」清洗 |
| （可拆大项）goal_detail_l10n 硬编码 80+ 条迁 arb | mobile goal_detail_l10n.dart | 消灭 arb/extension 双重定义 |

### 批次 B · 状态机：加载/空/失败/不一致四态（预计触达 8–12 文件）

| 动作 | 文件 | 说明 |
|---|---|---|
| 空态禁主 CTA | mobile minimum_criteria_card.dart:76-99 | thresholds.isEmpty 时隐藏确认/改为「去设置」；一行级修复 |
| 「今日任务」单一事实源裁决 | mobile task_board_provider.dart＋goal_detail_provider.dart＋experience_provider.dart（三源对齐或新增聚合 provider）＋2 屏呈现 | S7 结构修复；先立口径（dueDate 口径为事实源，引擎叙事引用之） |
| 假保存按钮治理 | mobile unified_settings_screen.dart:553-560 | 加脏状态标识或按钮改「返回」语义 |
| memory 承诺过期态 | mobile pending_commitments_section.dart（新增 overdue 分支） | |
| SSE 服务端 heartbeat | backend/app/core/sse.py:181-211（30s ping 帧）＋网关透传确认 | V26 收尾 |
| 等待分期默认可见性 | mobile chat_screen.dart 胶囊显示策略 | S18 收尾（配合实机验证） |

### 批次 C · 结构性：token 收敛＋面积预算（预计触达 50+ 文件，需分多轮）

| 动作 | 规模 | 说明 |
|---|---|---|
| 动效 token 收敛 | ~2 文件核心＋长期 373 处字面量 | sparkle_route_transition 内联映射→DS.motionDuration（详见 §4，性价比最高先做） |
| weather 层门控补全 | 1 文件 | S6 剩余半边 |
| home 首帧减配（S20/S6） | dashboard_screen＋layers | 装饰延后一帧/卡槽懒加载 |
| 星图标签消隐＋导航沉浸化 | star_map_painter.dart＋shell_navigation.dart | S5 |
| chip/pill 剩余 178 私有类迁移 | 长期迁移计划，status_awareness_bar（7 类）先行 | S9 |
| typography 1293 处字面量迁移 | 长期 | S4（先修硬编码数据装饰图表 1 文件） |
| 截断规范＋placeholder 缩短 | 规范文档＋arb 若干 | S3 |
| 色彩层级 token 规范 | 设计规范＋token 层 | S1 |
| 面积预算守卫 | rule_guard 新规则 | S8/S10/S17 的可执行验收（对齐 U-01 已验证的守卫模式） |

---

## 6. 诚实申报（静态验证边界）

1. **只能实机确认的项**：V25/V24 修复后的真机回归（静态已确认代码在位＋测试在案，但未跑模拟器）；V26 重连周期是否归零（方案见 §2.3）；S18 三点动画 vs 透明度胶囊在 3–7s 静默期的**默认**观感（取决于用户 TransparencyDisplayMode 设置）；S15「设置页第二处无障碍折叠项」是否仍存在（静态只在 :687 找到一处）；S1/S3 的实际视觉感知（截图级判断无法静态复核）。
2. **计数口径**：本报告 rg 计数（chip/pill 类 178、裸 spinner 103、fontSize 1293、动效引用 42/131/17/373）为验证员近似口径，与 U-01 守卫的 ratchet 口径（rawChip 75→11、rawSpinner 79→8）**定义不同**（守卫有精确 pattern 与白名单），两者不矛盾但不可互换引用；排期时应以守卫口径为进度基线、本报告口径为存量盘点。
3. **行号漂移**：AUDIT.md 引用的 unified_settings_screen.dart:2087/:3391 等行号已失效（文件现位于 lib/features/user/presentation/screens/，确认按钮现 :553-560）；本报告所有 file:line 以 wt83 HEAD=75a3157f 为准。
4. **报告勘误两处**：①S16 motion.dart 并非第三套数值（本就是 AnimationSystem 别名），真实冲突是路由转场内联映射 vs DS.motionDuration；②S7 双 key 两消费者同源（都是 taskListProvider 派生），跨屏矛盾的真因是三源口径而非双 key 本身。
5. 本轮零代码改动、零 commit/push、未触碰主仓；/tmp 无驻留文件。

## 7. Top 5 确认仍存活的最高价值靶子

1. **S7 三源「今日任务」口径**（仍存在）——信任头号杀手；修复入口＝立单一事实源裁决（批次 B），arb 双 key 去重是顺手 10 分钟活。
2. **S2 机话直出五例**（仍存在，含引擎侧拼接点）——一轮 copy＋词典批可全清，观感收益/成本比全榜第一；§3 已给逐例施工图。
3. **S11 悬空确认按钮**（仍存在）——minimum_criteria_card 一行级逻辑修复，用户困惑度/成本比最高。
4. **S16 路由转场内联映射**（仍存在）——2 文件收敛覆盖 131 处引用的时长统一，"不精致"体感的最大单点。
5. **S13 假保存按钮**（仍存在）——settings「确定」只做 pop()，语义误导零收益；加脏状态或改语义即可。
