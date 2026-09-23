# A-SPEC6 · 设计语言第六轮：两新面（可访问性全维 / 离线与弱网体验）UX 研究 → 自审 → 辩论 → SPEC v1.6 提案

> 卡：北极星全旅程战役 · A 纵队（设计语言线）研究卡第六轮 ｜ 2026-09-22 ｜ worktree **wt255**（分支 wt255-aspec6，base **f7343ae5**）
> 性质：**纯研究卡，零产品代码改动**。所有代码引用只读走查（rg/read），file:line 均为 @f7343ae5 实测。
> 前置读透：`v3-output/A-SPEC5/REPORT.md`（第五轮范本，本卡形制对齐它）+ `v3/FLEET-BRIEF.md`（战役上下文）+ `v3-output/DL-R3/SPEC.md`（v1.0 正文，§2 动效系统/§4 组件语法/§6 文案与数据呈现/§7 交互流程为本轮两面的条款挂靠点）。本提案**不推翻 v1.0-v1.5 任何条款**，全部为增量/澄清/存量靶登记，编号接续 v1.5 的 N30（N31 起；A-SPEC5 §4 的「N30」系其台账表格号，本轮正式启用 N31）。
> 对标研究方法声明：本会话外部搜索配额耗尽（web_search 429，实测报错「Weekly/Monthly Limit Exhausted，reset 2026-09-24」，与前五轮同况），对标做法基于公开常识 + UX 专业判断（沿用 A-SPEC-V1_1/A-SPEC2/A-SPEC3/A-SPEC4/A-SPEC5 五轮卡内授权先例）；引用代码均为树内实测。
> 两面范围界定（按卡）：①可访问性全维=语义标注覆盖分布（Semantics/MergeSemantics/label + 既有 a11y 测试先例盘点 + 图片/图标钮/自定义绘制三盲区）+ 动态字号与对比度（textScaler 传导、大字号溢出面、DS 令牌对比度抽检）+ 动效可达（系统 reduce motion 尊重度 + 持续动画清单）；②离线与弱网=各数据面离线行为三态盘点（报错/缓存/骨架永转）+ ws 断线重连覆盖与用户感知 + 写操作离线处理 + 本地缓存覆盖度与 stale 处理 + 超时阈值分级审计。

---

## 0. 方法与多轮过程记录

照前五轮四步执行：

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 研究 | 面1 按 WCAG 2.1/2.2 移动要点（1.4.4 Resize Text / 1.4.3 Contrast / 2.5.5 Target Size / 2.3.3 Animation from Interactions / 4.1.2 Name Role Value）+ HIG Accessibility（Dynamic Type 尊重系统、Reduce Motion 全量）+ Material a11y（48dp、TalkBack 标注）提三维做法；面2 按 iOS/Android 离线模式公约（outbox 乐观入队、stale-while-revalidate、恢复后静默冲刷）+ Telegram/Notion 弱网表达（状态常驻、操作可撤）提三态盘点法 | §1 两张对标表 | 两面共性直指北极星：**可访问性是「放大镜下的体验质量」——读屏/大字号/减弱动效用户走的正是备考周最疲惫时的使用状态；离线是「地铁与宿舍断网时的备考连续性」——错题本翻不开=复习中断**；新增两条面性公约：**辅助设置是叠加律不是替换律（系统×app）**；**离线排队成功≠操作失败，UI 三态必须诚实** |
| R2 自审 | 面1 全库 grep（Semantics 320/semanticLabel 76/Tooltip 63/IconButton 314/liveRegion 95/FocusTraversalGroup 0/textScaler 10/.repeat( 50 文件）+ a11y 设置屏与 provider 全读 + app.dart MediaQuery 注入走查 + galaxy 4266 行画布语义走查 + 45 个 CustomPainter 文件盘点；面2 离线层全读（sync_engine/offline_*/local_database 18 文件）+ 三域 repository 缓存读走查（task/error_book/community）+ ws 三服务退避比对 + Dio 超时与重试审计 | §2 两张全景表 + 差距清单 12 条（带 file:line） | **in-app a11y 设置加载后整体替换系统设置**（字号/减弱动效/辅助导航三值全被默认值覆盖，app.dart:120-134）；**图标钮语义标签覆盖 ~15%**（314 钮 46 标注）；**galaxy 星图读屏不可达且 a11y 服务是死代码**；**读路径离线断层**（task/error_book/community 零本地缓存）；**TASK-013 离线入队 UX 诺言未兑付**（排队成功被报成未知错误） |
| R3 辩论 | 12 条逐条过三关（真差距？收益/成本/风险？北极星加权值不值？） | §3 辩论记录：采纳 6 / 改写采纳 3 / 砍 1 / 转台账+观察 2 | 砍单主导理由：首帧离线横幅盲区 <1s 自愈；galaxy 完整读屏等效属 L 级工程降为观察行；超时全局冻结风险大于收益转登记制 |
| R4 成文 | 过关差距 → v1.6 增量条目 N31-N37 + 台账 N38 + top8 | §4 / §5 | v1.6 共 7 条增量，全部为 v1.0-v1.5 的增补/执行令/存量靶登记，无推翻 |

**结构性结论先行（两条）**：
1. **可访问性是「中枢已建、神经未接」**：U-01 已交付全库最完整的 a11y 设置中枢（字号 0.85-1.4 滑杆/高对比/色盲安全 Wong 调色板/触控三档/减弱动效/读屏/TTS/低载模式九项，accessibility_settings_screen.dart 全文 + 双端持久化），触控目标有 48dp 几何钉死与测试先例，对比度在 theme_manager 内有逐档校准注释——底子好；但三根神经没接上：**设置加载后反而覆盖系统设置**（系统大字号用户被打回 1.0）、**图标钮读屏无名**（~85% 无标签）、**32/50 持续动效不认减弱动效**；galaxy 更是「a11y 服务写了、一行没接线」的死代码孤岛。
2. **离线是「管道已通、水塔缺位」**：outbox 引擎（Isar+退避+ACK+去重）、聊天域离线全生命周期（持久化队列+三态指示器+重连恢复）、SyncCenter 面设置可达、统计三层缓存——基建成熟度超预期；但**只有 3 个域在往管道里写**（task 半个/cognitive/chat），**三个最高频备考读面（错题本/任务列表/社区）断网即白屏**，且唯一的离线入队 UX（task pause/resume）把「排队成功」报成「未知错误」——用户在地铁里暂停任务，看到的是报错，实际却会同步成功，诚实性红线（FLEET-BRIEF 共同约束 4）在此处被自己的基础设施违反。

---

## 1. 两面对标研究表（R1）

### 1.1 可访问性全维 · 对标：WCAG 2.1/2.2 移动要点 / HIG Accessibility / Material a11y（公开常识，声明见页眉）

| 维度 | WCAG 移动要点 | HIG Accessibility | Material a11y | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 语义标注 | 4.1.2 Name/Role/Value：一切交互件有名有角色；纯装饰图对读屏隐身 | 所有图标钮带 accessibilityLabel；装饰元素 `accessibilityElementsHidden` | 无 label 的 IconButton 是 TalkBack 反模式样板 | **图标钮必须有名**（icon-only 即无文本回退）；装饰动效用 ExcludeSemantics 剔除——Sparkle 后者已做（16 处），前者缺口 ~85% |
| 动态字号 | 1.4.4 Resize Text：支持 200% 放大不丢功能；app 内设置**叠加**系统设置不覆盖 | Dynamic Type：尊重系统字号，app 内可再调；@SF 符号随字缩放 | sp/dip 全随 textScaler 传导 | **叠加律是铁律**：`系统 × app` 合成，禁 `TextScaler.linear(app值)` 直替——直替等于替用户关掉系统无障碍 |
| 对比度 | 1.4.3 正文 ≥4.5:1、大字/图形 ≥3:1；禁用态豁免 | 系统增加对比度档位可检测（`accessibilityContrast`） | 同 WCAG | **令牌级校准 + 注释成文**是正解（Sparkle 已做）；需补「组合抽检」口径：textSecondary×surface/阴影/玻璃面叠加场景 |
| 动效可达 | 2.3.3 Animation from Interactions：动效可关；2.2.2 自动滚动/闪烁可暂停 | Reduce Motion：一切非必要运动停，淡变可留 | `Animator.areAnimationsScaled`/ MediaQuery disableAnimations 单一口径 | **持续动画清单必须逐个挂守卫**；「口徢单一」是关键——双源读法（系统直读 vs MediaQuery）等于两套开关互相打架 |
| 自定义绘制 | 画布内容对读屏等效可达（替代视图或语义节点） | `accessibilityActivate`/自定义 action | `Semantics` 包 CustomPaint + label/hint | 星图类画布至少给**容器级摘要+节点清单替代路径**；全画布一个标签=读屏黑洞 |
| 焦点遍历 | 2.4.3 焦点顺序合理 | automatic 遍历多为默认可用 | FocusTraversalGroup 显式分组 | 默认遍历可用时低优先；自定义画布/复杂组合屏才需显式分组 |

**面性公约提炼**：①**辅助设置叠加律**（系统×app，禁替换）；②**图标钮必有名**（新钮必标、存量登记制清偿）；③**动效口徢单一**（统一 MediaQuery 读法，持续动画逐个挂 reduce-motion）；④**画布读屏等效**（容器摘要+替代路径，禁全画布单标签黑洞）。

### 1.2 离线与弱网 · 对标：iOS/Android 离线模式公约 / Telegram / Notion（公开常识，声明见页眉）

| 维度 | 离线模式公约 | Telegram（弱网标杆） | Notion（离线同步标杆） | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|
| 读路径 | 核心数据本地必有 warm 缓存，断网开 app 仍可用（标注时点） | 会话列表/近期消息全部本地 | 全库缓存，离线全功能 | **备考资产（错题/任务）必须有离线读**——「地铁翻错题」是刚需动线；纯网络读=断网即白屏 |
| 写路径 | outbox 乐观入队：本地即时生效+入队+恢复冲刷；**排队成功≠失败** | 消息时钟图标（未发）→ 单勾（已发）→ 双勾（已达） | 同左+冲突可解 | **写操作三态诚实**（已排队/已发送/失败可重试）；把排队报成错误是诚实性违例 |
| 连接表达 | 断网全局横幅一次、域内状态常驻；禁 toast 循环（A-SPEC4 N21 已立） | 常驻「等待网络…」状态条 | 顶部同步状态胶囊 | N21 已立「单一报告源」条款——本轮只需盘点覆盖面（chat 达标，其余域缺常驻表达） |
| 重连 | 指数退避+终态停试+恢复冲刷；心跳保活 | 同左 | 同左 | Sparkle 三 ws 服务退避表健全（800ms→30s cap、终态停试 M-3）——达标，登记为正解范式 |
| 超时 | 分域分级：轻查询短、生成类长；连接/接收分开 | 连接快败+重试 | 分级 | **全局 10/30s 一刀切是盲点**：AI 生成与轻 GET 同阈值；但全局值改动风险大，走登记制 |
| stale | 缓存数据展示必带时点标记（「截至 X」） | —— | 离线徽标+同步时间 | **isFromCache 链路已在数据层**（统计域），UI 层零消费——接最后一公里即可 |

**面性公约提炼**：①**备考资产离线可读**（第一回找资产错题本先行）；②**写操作三态诚实**（排队成功必须有排队的样子）；③**stale 必带时点**；④**弱网参数分域登记**（不冻结全局、新域必查）。

---

## 2. 自审差距清单（R2，全部 @f7343ae5 实测）

### 2.0 先说达标项（诚实记录——a11y 中枢与离线基建是本轮最大好消息）

- **a11y 设置中枢全维建成（U-01 遗产）**：`accessibility_settings_screen.dart`（519 行）九项设置全量——fontScale 滑杆 0.85-1.4 十一档（:190-197）、高对比、色盲友好、触控三档 48/56/64（accessibility_provider.dart:14-23 TouchTargetSize 枚举）、reduceMotion、触感、读屏优化、TTS 朗读、低载模式一键打包（asLowLoadDefaults :156-167 连带提字号+大触控+减动效）；本地 SharedPreferences + 服务端 user_settings 双持久化（:184-189/:280-295），**离线与未接入后端时本地设置可用**（:292-294 catch 注释自证）；屏内还有 WCAG 自检清单展示区（:325-344）。
- **触控目标几何钉死+测试先例**：DS.touchTargetMinSize=48（design_system.dart:998）；SparkleButton/SparkleIconButton 以 `max(size, minTouchTarget)` 正方档约束任何槽位不变形（sparkle_button_v2.dart:505-549），且 in-app 触控档加载后即时生效（:523-525 watch accessibilitySettingsProvider）；测试三层钉住：sparkle_button_test.dart:308-311（「a11y 触控下限 48 不可被调用方压破」+ fabGeometry ≥48）、a11y_touch_target_test.dart（44dp 底线+间距）、c18_accessibility_semantics_test.dart（校正 chips 44dp+语义标签可点）。
- **语义基建有存量**：Semantics 320 处（core/design 20 + features 262）；liveRegion 95 处（LoadingIndicator 默认 liveRegion=true，loading_indicator.dart:30/:57/:78——加载中读屏自动播报）；ExcludeSemantics 16 处剔除装饰动效（status_awareness_bar 六处/aurora_status_band/feed_post_card 等）；a11y 语义测试先例四件（c18_accessibility_semantics_test 4 个 testWidgets、a11y_semantic_labels_test、login_screen_semantics_test、accessibility_settings_screen_test + provider test + golden test）。
- **对比度令牌级校准成文**：theme_manager.dart 内嵌逐档注释——textSecondary on S1：常规浅色 6.86（:442）、高对比浅色 15.89（:490）、情绪浅色 5.24（:549）、深色 8.16（:611）；textTertiary B2-3a 校准 ≥4.5:1（:440-442/:547-550）；textDisabled 2.62/5.09/2.50（禁用态 WCAG 豁免合规）；色盲友好=真 Wong 2011 CB-safe 调色板（:423-471，deuteranopia/protanopia/tritanopia 三色盲可辨），task 六色板与聊天气泡同步换装。
- **auth 离线冷启动已保护**：N20 stale-while-revalidate 落地——有 token 即放行进 app（auth_provider.dart:180-196），getCurrentUser 转后台校验且网络层失败保留会话（_handleSessionCheckFailure，IR-G12 存量），splash 不再被网络往返门控（routes.dart:168-172 N20 注释）。
- **聊天域离线全生命周期（全库正解范式）**：OfflineChatMessage Isar 持久化（local_database 模型族）；入队+溢出处理——队列超限丢最旧并报 `PENDING_QUEUE_OVERFLOW`+人话文案 chatErrorQueueOverflow、同步清本地 DB（websocket_chat_service_v2.dart:1965-1982）；extraContext JSON 无损编解码（A-2 修复，:1984-2030）；ACK/失败回写（markAcked/markFailed :2078-2148）；重连恢复重放（_restorePendingFromDb :2679-2693）；已 ACK 清理（:2886）；UI 三态指示器 OfflineQueueIndicator（queued/sending/complete+pendingCount，**带 Semantics liveRegion 语义容器** offline_queue_indicator.dart:47-52）由 chat_screen 挂载。
- **ws 重连工程三服务健全**：主聊天 v2 退避表 800ms→1.2s→2.2s→4.2s→8.2s→12.2s 共 6 次（websocket_chat_service_v2.dart:1340-1352），心跳 30s+pong 超时（:1403-1404），稳定连接 30s 阈值才刷新重连预算（M6-R2-01 :1354-1356）；core WebSocketService 同表（websocket_service.dart:14-21）；community ws 指数退避 1s→30s cap 10 次（community_websocket_service.dart:57-66）+ **终态停重试**（isTerminalCommunityWsFailure：401/403/404/retryable:false/4401-4404 close code 即停，M-3 反「×15 重连风暴」:68-90）；用户感知文案在位（chatReconnecting『正在重新连接...』zh:857、chatErrorMaxRetriesExceeded『重连 6 次后仍无法连接』zh:33585-33586、communityChatConnectionLost zh:8343）。
- **弱网重试克制**：RetryInterceptor 只对 502/503/504 重试 ×3、指数退避 1s/2s/4s（api_interceptor.dart:22-58）——连接类错误不重试，避免与 outbox 重放双重叠加；IdempotencyInterceptor 在链（api_client.dart:27）保写操作重放幂等。
- **统计三层缓存（stale 溯源数据层正解）**：HybridStatisticsRepository hot 内存 5min/warm Isar 24h/cold API（hybrid_statistics_repository.dart:11-19/:26-27），缓存命中一律 markFromCache 打溯源标（:105-107），legacy mock 缓存一次性清洗（:139 与 B-02 不变量）；导出服务把 isFromCache 转写为 dataSource 'local-cache'（statistics_export_service_impl.dart:189/:221）。
- **SyncCenter 面已建成且设置可达**：pendingByTopic/totalPending/lastSuccessAt 统计+状态过滤+本地化标签（sync_center_provider.dart:13-34）；路由 /profile/sync-center（user_routes.dart:47/:206-210），设置页入口在位（unified_settings_screen.dart:1944-1947）。
- **图片语义基本达标**：全库仅 1 处裸 Image.network/asset（其余经 SparkleNetworkImage，semanticLabel 参数+测试钉住 a11y_semantic_labels_test.dart:65-102「有标可查/无标即无」）。

### 2.1 面 1 · 可访问性矩阵（域 × 三维 × 判定）

| 域 | 语义标注 | 动态字号 | 动效可达 | 判定 |
|---|---|---|---|---|
| DS 组件层 | 良：SparkleButton/IconButton/Pressable/Avatar/NetworkImage/EmptyState/LoadingIndicator 全带 semanticLabel 参数+button/liveRegion 语义（320 处中 20 处在此层，是 owner 层） | 良：令牌随 textScaler 传导（responsive_system.dart:91-92 提供 textScaleFactor 读法；design_validator.dart:318-319 校验器自检） | 中：motion.dart `createBreathingController` **无条件 repeat(reverse:true)**（:97-104）——DS 自家 helper 不认减弱动效 | 中（helper 是 owned 缺口） |
| auth 四屏 | 良：login_screen_semantics_test 钉住；autofill/键盘齐（A-SPEC5 存量） | 良：标准组件随系统 | 良：无持续动效 | 良 |
| home/仪表盘 | 中：dashboard/omni_bar/aurora_band 有语义（aurora `_semanticLabel` :319+），metrics_row 有 textScale 适配 | 良：dashboard_screen.dart:1066、metrics_row.dart:33（compactMode ≥1.2 换布局）、compact_status_bar.dart:35——**全库仅 3 处 textScale 自适应读法**，其余组件靠流式布局兜底 | 中：dashboard_motion.dart:41 有 disableAnimations 检查 ✓；但 particle_layer/effect_layer 挂检查后仍有 weather/focus_card 等无守护持续动画 | 中 |
| chat 域 | 良：status_awareness_bar 六处 ExcludeSemantics、OfflineQueueIndicator liveRegion、c18 测试钉住 | 中：无 textScale 特配，流式布局兜底 | 中：typing_text 四处 disableAnimations 检查 ✓（:88/:110/:225/:288）、agent_status_indicator ✓（:275-276）；但 agent_avatar_switcher/collaboration_timeline/regeneration_prompt/action_card/plan_review_card/review_appeal_card 无守护 | 中-良 |
| galaxy 星图 | **差：全画布单容器语义**——galaxy_screen.dart:3041 唯一 `Semantics(container:true, label:'星图')`，4266 行画布内节点手动 hit-test（_hitTestNode :1068）、star_map_painter 2819 行零语义节点；galaxy_accessibility_service.dart 的 GalaxyNodeSemantics/GalaxyFocusManager/GalaxyKeyboardNavigation **全库 0 引用（死代码）**，getNodeSemanticLabel/l10n 文案（galaxyA11yNode* 全套）全部闲置 | ——（画布无文本缩放问题） | 中：galaxy_accessibility_service 有 reduceMotion 分支（:300-315）但**因无人调用同样闲置**；galaxy_edge_animation/graphrag_visualizer 无守护 repeat | **差（读屏黑洞+死代码）** |
| achievement/streak | 中：badge/indicator 有 Semantics（320 处中的主力域） | 良 | 差：streak_indicator/flame_indicator/achievement_map/contract/detail/streak_details 六文件 repeat 无守护 | 中 |
| focus 专注 | —— | —— | **差：star_background/flip_clock/timer_widget 三个持续动画全无守护**——专注场景恰是动效敏感用户最久停留的面 | 差 |
| community | 中：feed_post_card ExcludeSemantics ✓ | 良 | 差：bonfire_widget/community_widgets repeat 无守护 | 中 |
| 统计 charts | 良 | 良 | 良：statistics_heatmap/period_toggle 挂 context.reduceMotion（:101/:143）——正解范本 | 良 |
| a11y 设置屏 | 良：本域即 a11y 面（semanticLabel/TouchPreview/滑杆 label） | 良（自身即字号源） | —— | 良 |

**覆盖数字汇总**：图标钮合计 ~314（SparkleIconButton 245 + 裸 IconButton 69），带名 ~46（semanticLabel 23 + tooltip 23）≈ **15%**；Semantics features 262 处集中于 home/chat/achievement/insights 四域；MergeSemantics 0 处、BlockSemantics 0 处、header:true 仅 2 处、FocusTraversalGroup 0 处（默认遍历可用，低优先）。

### 2.1b 面 2 · 离线矩阵（域 × 离线行为 × 判定）

| 域 | 读路径（断网开屏） | 写路径（断网操作） | 缓存/过期 | 判定 |
|---|---|---|---|---|
| AI 聊天 | 历史按需加载=网络-only | **正解**：WS 断→消息本地持久化排队→指示器三态→重连重放（§2.0） | 消息队列持久化；ACK 清理 | **良（范式）** |
| 任务列表/执行 | **网络-only**：getTasks 无任何本地缓存读（task_repository 0 处 isar/Hive/cache），断网冷启动=错误空态 | **半正解**：pause/resume 离线入队 outbox（:1266-1309）；但见 OF-G2 三断 | 无读缓存 | 中-差 |
| 错题本 | **网络-only**：error_book_repository 0 处本地缓存（grep 实测） | 网络-only：添加/编辑失败=错误 toast（A-SPEC5：表单现场保留 ✓） | 无 | **差（第一回找资产断网不可翻）** |
| 社区/小队 | 网络-only（community_repository 0 处缓存） | 网络-only | 无 | 差-中（非备考核心资产） |
| galaxy 星图 | 会话级内存缓存：SmartCache 图谱 5-10min TTL（enhanced_galaxy_repository.dart:31-36/:80 注释自认），**冷启动断网=星图挂** | 打标走 outbox（cognitive 域）✓ | 会话级，无跨会话 | 中 |
| 词汇/翻译 | **正解**：Isar 持久化（translation_history_provider.dart:4 vocab_word/translation_record），离线可查 | 本地记录+同步 | 持久化 | 良 |
| 统计 | **正解**：三层缓存（warm 24h），断网见昨日数据 | —— | isFromCache 溯源在数据层（:105-107），**UI 层 0 消费**（presentation 0 处，仅导出标注） | 良-（缺最后展示一公里） |
| 认证会话 | **正解**：stale-while-revalidate 放行+网络错保留会话（auth_provider.dart:180-196） | 登录类必然需网 | token 本地 | 良 |
| 同步中心 | ——（本体即离线设施） | outbox 全域状态可视+重试 | —— | 良（入口在设置 :1944） |
| 光子/兑换 | 网络-only | 网络-only：失败报错（金融域不可离线入队是**正确**取舍——AST 反刷口径下离线记账有刷分风险，维持在线） | 无 | 合理（不动） |

**基础设施盘点（正解清单）**：SyncEngine outbox（batch 20/attempts 5/backoff 800ms→30s cap/waitingAckTtl 30s，sync_engine.dart:39-43；连通性恢复自动冲刷 :57-61；dedupeKey 防重）；生产者现仅 task(pause/resume)/cognitive fragment/chat message 三域；isOnlineProvider 驱动 OfflineBanner 全局横幅（offline_banner.dart:13-44，app.dart:116 挂载）；Dio 全局 connect 10s/receive 30s（api_client.dart:18-19），**全库无 per-request 超时覆盖**（仅 statistics 三 provider 重复自立同值 Dio、auth retry Dio 同值 :77-82、ApiConstants 30/30/30 :94-96——四处同一刀切）。

### 2.2 差距清单（12 条）

| # | 差距 | 证据（file:line @f7343ae5） | 违反/衔接条款 |
|---|---|---|---|
| AX-G1 | **图标钮语义标签 ~15%**：SparkleIconButton 245 调用仅 23 处 semanticLabel、裸 IconButton 69 处仅 23 处 tooltip——合计 ~314 钮 ~268 个读屏无名；SparkleIconButton 的 Semantics label 可空（sparkle_button_v2.dart:530-535），空即「按钮」无名播报 | 同列（perl 邻近计数实测） | WCAG 4.1.2；§4 组件语法「语义槽」的图标钮域执行缺口 |
| AX-G2 | **in-app 设置加载后覆盖系统设置**：app.dart:120-134——isLoaded 后 textScaler=`TextScaler.linear(fontScale)`（默认 1.0，accessibility_provider.dart:53）**替换**系统字号（系统 1.3x 用户被打回 1.0）；disableAnimations=reduceMotion（默认 false）**关掉**系统减弱动效；accessibleNavigation=screenReaderOptimized（默认 false）**覆盖**系统辅助导航。三值全是替换律非叠加律 | 同列 | WCAG 1.4.4；对标 §1.1 动态字号行（叠加律铁律）；「唯一交互源」精神的 a11y 版 |
| AX-G3 | **galaxy 星图读屏黑洞+死代码**：全画布唯一容器 Semantics（galaxy_screen.dart:3041），2819 行 painter 零节点语义；galaxy_accessibility_service.dart 的 GalaxyNodeSemantics/GalaxyFocusManager/GalaxyKeyboardNavigation 及全套 galaxyA11yNode* l10n 文案 **0 引用**——服务写了没接线 | grep 0 命中实测 | 对标 §1.1 自定义绘制行；「禁悬空」的语义版 |
| AX-G4 | **持续动效 32/50 无 reduce-motion 守护**：50 个含 `.repeat(` 文件仅 18 个检查 reduceMotion/disableAnimations；无守护清单含 focus/star_background、flip_clock、timer_widget（专注域三连）、bonfire、aurora_core_session_sheet、achievement 六文件、chat 五 widget、DS 自家 createBreathingController（motion.dart:97-104 无条件 repeat） | 同列（逐文件 grep 实测） | WCAG 2.3.3；HIG Reduce Motion；§2 动效系统未覆盖「可达性」维 |
| AX-G5 | **动效开关双源分裂**：sparkle_route_transition.dart:55/:126、cold_start_motion.dart:61、splash_screen.dart:32、dashboard_motion.dart:41、typing_text.dart:88-288、global_particle_counter.dart:14-15 直接读 `platformDispatcher.accessibilityFeatures`（只认系统、**无视 in-app 开关**）；而 context.reduceMotion 扩展（sparkle_context_extension.dart:28-31）读 MediaQuery（认 app.dart 注入的 in-app 值）——转场/启动/打字机动效 app 内关不掉 | 同列 | 对标 §1.1 动效可达行（口徢单一是关键）；与 AX-G2 构成同一根因两面 |
| AX-G6 | **header 语义 2 处、FocusTraversalGroup 0 处**：长列表屏（错题/任务/设置）读屏无法按标题跳转 | grep 实测 | WCAG 2.4.3 低优先登记（默认遍历可用） |
| OF-G1 | **备考资产读路径离线断层**：task_repository/error_book_repository/community_repository 三仓库 0 处本地缓存读（grep isar/Hive/cache 实测）——断网冷启动任务列表/错题本/社区=错误空态；galaxy 仅会话级 SmartCache，冷启动断网星图挂；**错题本是第一回找资产，地铁/宿舍断网不可翻** | 同列 | 对标 §1.2 读路径行；北极星「错题是第一回找资产」直接受损 |
| OF-G2 | **TASK-013 离线入队 UX 诺言未兑付（诚实性违例）**：docstring 承诺「queued as success + 'Offline — will sync' UX hint」（task_repository.dart:24-27），实际链路三断——①入队后 throw OfflineEnqueuedException（:1277/:1309）而 provider 无乐观更新（task_provider.dart:427-437 pauseTask：异常路径直接进 catch，任务状态不变）；②categorizeUiError 对 `OfflineEnqueuedException: pauseTask queued for sync` 无匹配模式（error_lexicon.dart:95+ 无此类别）→ 落 unknown 通用错误文案；③start/complete/abandon 三个离线入队方法（task_offline_queue.dart:20-95）**全库 0 调用（死代码）**——用户离线暂停任务看到「出错了」，实际会同步成功 | 同列 | FLEET-BRIEF 共同约束 4「诚实性」；§4.5 错误态「为何错必须真因」；§6 文案与数据呈现 |
| OF-G3 | **outbox 生产者仅 3 域**：task(pause/resume)/cognitive/chat——错题、社区、checkin、目标、计划写操作全部网络-only（失败即错，A-SPEC5 已保表单现场） | grep enqueue 调用面实测 | 对标 §1.2 写路径行；增量扩展须随 OF-G1 首批逐域评估，防一次性大工程 |
| OF-G4 | **stale 数据 UI 零标记**：isFromCache 溯源标在数据层/导出层闭环（hybrid :105-107、export :189/:221），但统计 presentation 层 0 处消费——断网看统计不知是昨天的数 | grep presentation 0 命中 | 对标 §1.2 stale 行；§6「仪表数字必须有真源」的时点标注延伸 |
| OF-G5 | **超时一刀切无分级**：全局 connect 10s/receive 30s（api_client.dart:18-19）；statistics 三 provider 自立同值 Dio（focus/capsule/agent_statistics_provider :108-145）；auth retry Dio 同值（api_interceptor.dart:77-82）；ApiConstants 30/30/30（:94-96）——AI 生成/长推理与轻量 GET 同阈值，且四处各写一份常量无单一事实源 | 同列 | 对标 §1.2 超时行；工程红线「口径单一事实源」的客户端版 |
| OF-G6 | **isOnlineProvider 乐观默认 true**：connectivity_provider.dart:20 `orElse: () => true`——冷启动首包未到时 OfflineBanner 不显（<1s 窗口），断网用户先白屏进面后横幅才补显 | 同列 | 轻微；连接表达归属 N21（A-SPEC4）既辖 |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。每条给出裁决：**采纳 / 改写采纳 / 砍 / 转台账+观察**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| AX-G1 | 图标钮补标注：新钮必标+核心屏首批清偿 | 蓝方：268 个钮逐个起名是机械活，且很多钮语义可从上下文推 | G1 真差距（15% 实锤；「上下文可推」恰是读屏用户的反命题——他们没有视觉上下文）；G2 成本 S-M（高频域 appbar/tab 20-30 钮先行+登记制防新增破口，a11y 测试先例四件可直接复制）；G3 中-高——疲惫+分心状态下的备考用户与读屏/大字号用户是同一类「低感知带宽」人群，无名按钮=每次操作都在猜 | **采纳**（N31 主条：图标钮必标+登记制） |
| AX-G2 | 三值改叠加律：textScaler 合成（系统×app）、两布尔 OR | 蓝方：现行为「让 in-app 设置有最终话语权」，改叠加后 app 内滑杆感知变弱 | G1 真差距（替换实锤；WCAG 1.4.4 明文 + HIG Dynamic Type 公约——app 内设置是**在系统之上**调节，不是接管系统）；蓝方顾虑不成立：合成后 app 滑杆依然在系统值基础上继续放大（×0.85-1.4），感知只增不减；G2 成本 S（app.dart 三行：`TextScaler.linear(sys.scale * app)` 或 composite scaler、`sys \|\| app` ×2）；G3 高——系统大字号用户（正是低视力人群）现在会在设置加载完成的一瞬被打回 1.0，是**主动制造**的无障碍事故 | **采纳**（N32 主条：叠加律） |
| AX-G3 | galaxy 星图读屏等效：接线闲置的 GalaxyNodeSemantics + 节点清单替代视图 | 蓝方：星图是空间视觉签名面，读屏等效需要「节点语义+焦点导航+替代列表」三件套，工程 L；且 galaxy 用户占比与读屏用户交集未知 | G1 真差距（黑洞+死代码双实锤——但蓝方指出量级存疑成立）；G2 改写：一期只做**零成本接线**（GalaxyNodeSemantics 包装节点渲染层+服务已备 l10n），替代视图与键盘导航转观察；G3 中（星图是成就感签名面，读屏用户至少应听到节点清单） | **改写采纳**（N38 台账观察行：一期接线、替代视图量级触发转 L 级改造卡） |
| AX-G4 | 32 文件持续动画补 reduce-motion 守护 | 蓝方：装饰性动效（粒子/篝火/火苗）关了伤氛围；逐文件补是长尾活 | G1 真差距（32/50 实锤；「氛围」论恰被 WCAG 2.3.3 反驳——必要运动停、淡变可留，不是全删）；G2 改写：DS helper 一处修复（createBreathingController 守护）+ **新动效必挂**登记制 + 专注域三文件（timer/flip_clock/star_background）首批——恰是动效敏感用户停留最久的面；G3 中-高 | **采纳**（N33 主条：新动效必挂+DS helper 修复令+专注域首批） |
| AX-G5 | 动效开关统一 MediaQuery 口径，platformDispatcher 直读触碰即迁 | 蓝方：直读系统值在「app 未加载设置前」反而更准确 | G1 真差距（双源实锤；蓝方说的场景恰是 N32 修完后的残局——叠加律下 MediaQuery 注入值=系统∨app，直读者漏掉 app 半边）；G2 成本 S（七处读法改 context.reduceMotion 一行/处，触碰即迁不专项）；G3 中 | **采纳**（并入 N32 子句：单一读法口径+登记制） |
| AX-G6 | header 语义铺列表屏+遍历分组 | 蓝方：读屏跳转是深度需求，当前读屏用户基数未知；FocusTraversalGroup 默认可用 | G1 半差距；G2 长尾；G3 低-中 | **转台账**（N38 登记行：列表 header 语义随触碰补，不专项） |
| OF-G1 | 错题本/任务列表加离线读（warm 缓存） | 蓝方：缓存一致性工程不小（失效/脏读），且后端口径单一事实源红线——本地读会不会造第二事实源？ | G1 真差距（三仓库 0 缓存实锤；「地铁翻错题」是备考周真实动线）；蓝方红线顾虑被反驳：统计域三层缓存已立先例（warm 只读快照+时间戳，写路径仍走唯一口径，不构成第二事实源）；G2 改写：分批——错题本先行（第一回找资产，列表快照+更新时间戳，M）、任务列表随批（M）、社区/galaxy 缓行；G3 高——断网连续性直接等于「备考不被打断」 | **改写采纳**（N34 主条：备考资产离线读红线，首批错题本+任务列表） |
| OF-G2 | 兑付 TASK-013：乐观更新+专用错误类别+死代码处置 | 蓝方：入队已在（基建对），UX 只是文案问题顺手改；死代码删了可惜也许以后用 | G1 真差距（三断实锤；「顺手改」恰是要点——基建 100% 就位，只差 provider 乐观更新与 lexicon 一类一条文案，S 级成本拿回诚实性红线）；死代码裁决：start/complete/abandon **接线**（与 pause/resume 同制三行）而非删除——task 生命周期离线入队本就该完整；G3 高——「报了错但实际成功了」直接腐蚀用户对全部错误提示的信任 | **采纳**（N35 主条：离线写三态诚实，含死代码接线令） |
| OF-G3 | outbox 铺到错题/社区/checkin 全域 | 蓝方：一次性铺全域=大工程+每域冲突语义不同；错题录入离线入队后图片附件怎么办？ | G1 真差距（3 域实锤）但**时机未到**——N34 首批（读缓存）落地前先验证 warm 快照模式；图片附件同步是真实工程盲点；G2 观察行合理；G3 中 | **转观察**（N38 观察行：随 N34 首批验收后逐域评估，附件类写操作暂缓） |
| OF-G4 | 统计 stale 标记上 UI | 蓝方：数据层已有标记，UI 加徽标是多一处视觉噪音 | G1 真差距（最后 1 公里 0 消费实锤）；G2 成本 S（一枚「截至 X 时」前缀徽章，复用既有时间格式化）；G3 中——「仪表数字必须有真源」（FLEET-BRIEF 约束 4）在离线场景的直译就是「标注这是何时的真源」 | **采纳**（N36 子句，随 N34 同批展示规范） |
| OF-G5 | 超时分域分级 + 常量归一 | 蓝方：全局值动一发牵全身（splash/auth/上传都挂同一 Dio），分级后弱网下轻查询超时报错反而变多 | G1 真差距（一刀切+四处重复常量实锤——但「归一常量」与「改数值」是两件事）；G2 改写：**归一进 ApiConstants 单一事实源（S）+ 登记制（新域必查：轻查询 10s/生成类流式不适用 receiveTimeout/SSE 靠心跳）**，不冻结全局数值、不强制改存量；G3 中 | **改写采纳**（N37：弱网参数登记制+常量归一） |
| OF-G6 | isOnlineProvider 冷启动盲区修复（首帧主动探一次） | 蓝方：<1s 窗口自愈，横幅随即补显；为它加启动探测反拖慢冷启动（N20 刚拆掉的又是延迟） | G1 半差距（窗口 <1s 且自愈）；G2 修复成本与冷启动预算（N20）正面冲突；G3 低 | **砍**（不立条；N38 备忘防重复立项） |

**辩论统计**：12 条 → 采纳 6（AX-G1/AX-G2/AX-G4/OF-G2/OF-G4；其中 AX-G5 并入 N32、OF-G4 为 N36 子句）/ 改写采纳 3（AX-G3/OF-G1/OF-G5）/ 砍 1（OF-G6）/ 转台账+观察 2（AX-G6/OF-G3）。砍单主导理由：**修复成本与既有战役成果（N20 冷启动预算）冲突且窗口自愈**；转观察主导理由：**量级未证、时机未到、先验证首批模式**。

---

## 4. SPEC v1.6 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0-v1.5：编号规则 + 依据 + 可验收数字；不推翻 v1.0/v1.1/v1.2/v1.3/v1.4/v1.5 任何条款。编号接续 v1.5 的 N30。生效方式建议沿用 §1.7 两段门禁先例（文本即生效 / 守卫绑合入时点）。

**N31（§4 增补）· 图标钮语义标签基线（读屏的 Name 底线）**
- 一切 icon-only 交互件（SparkleIconButton/裸 IconButton/可点 Icon 容器）必须带语义名：DS 组件走 `semanticLabel`（l10n 化），裸 IconButton 走 `tooltip`；**禁新增无标签 icon-only 交互件**（守卫并入 DL-SPEC ratchet 家族：icon-only 无名计数现值 **~268** 冻结只降不升）。
- 首批靶（改造 #3）：主导航 shell、四 tab appbar、task 快捷菜单、chat 输入行、galaxy 控制条——高频域 20-30 钮先行；断言测试照 a11y_semantic_labels_test/c18 形制复制。
- 【依据：§2.2 AX-G1；§2.0 语义基建存量与测试先例；对标 §1.1 语义标注行（WCAG 4.1.2）】

**N32（§7 增补）· 辅助设置叠加律与动效单一读法（系统是底座，app 是微调）**
- **叠加律**：in-app a11y 设置注入 MediaQuery 时禁替换系统值——textScaler 合成为系统×app（`TextScaler.linear(system.scale × fontScale)` 或 composite），disableAnimations/accessibleNavigation 取 `系统 ∨ in-app`；存量靶（改造 #2）：app.dart:120-134 三值。
- **动效单一读法**：组件判断减弱动效一律走 `context.reduceMotion`（sparkle_context_extension.dart:28-31 扩展，MediaQuery 口径）；`platformDispatcher.accessibilityFeatures` 直读为存量债登记制（存量七文件：sparkle_route_transition :55/:126、cold_start_motion :61、splash_screen :32、dashboard_motion :41、typing_text :88-288、global_particle_counter :14-15——触碰即迁，不专项）。
- 【依据：§2.2 AX-G2/AX-G5；对标 §1.1 动态字号/动效可达行（WCAG 1.4.4/2.3.3、HIG Dynamic Type）】

**N33（§2 增补）· 持续动效可达守护（reduce-motion 必挂）**
- 一切 `repeat()` 型持续动画（呼吸/粒子/流光/骨架/时钟）必须挂减弱动效守卫（`context.reduceMotion` 或 DS 等价判断）：守卫行为=停止 repeat 或降为静止终态（淡变静态可留），**新动效 PR 必查项（登记制）**。
- 执行令两件：①DS 自家 `SparkleMotion.createBreathingController`（motion.dart:97-104）加守护参数；②首批存量靶：focus 域三文件（timer_widget/flip_clock/star_background——专注场景是敏感用户停留最久的面）。
- 存量登记：无守护 repeat 文件现值 **32** 冻结只降不升（守卫并入 ratchet 家族）。
- 【依据：§2.2 AX-G4；§2.1 统计 charts 正解范本（statistics_heatmap.dart:101/:189）；对标 §1.1 动效可达行】

**N34（§7 增补）· 备考资产离线读红线（断网不断复习）**
- 条目化备考资产（错题本/任务列表）**必须有本地 warm 读路径**：列表快照+数据时点戳持久化（模式照统计域 HybridStatisticsRepository warm 层先例 :26-27/:105-107），断网开屏呈现快照+时点标记而非错误空态；**写路径仍走唯一后端口径，本地快照只读、不构成第二事实源**（口径单一红线不破）。
- 分批：首批错题本（第一回找资产，改造 #5）+任务列表（改造 #7）；社区/galaxy **缓行**（非备考核心资产/会话级缓存已可）；galaxy 跨会话快照转观察行。
- 【依据：§2.2 OF-G1；§2.1b 离线矩阵；对标 §1.2 读路径行；统计域三层缓存为机制先例】

**N35（§4.5 增补）· 离线写操作诚实三态（排队成功必须有排队的样子）**
- 写操作离线入队成功时 UI 必须呈现「已排队」态而非错误：①provider 收到入队信号先乐观更新本地状态（pause/resume 形制：task_repository.dart:1266-1309 已入队，task_provider.dart:427-437 补乐观更新）；②error_lexicon 增设 `offlineQueued` 类别+文案（『无网络，已保存操作，恢复网络后自动同步』式——三件套照 N25：什么发生了+接下来会怎样+无需用户动作）；③禁把入队成功落 unknown 错误通道。
- **死代码接线令**：task_offline_queue.dart 的 enqueueStart/enqueueComplete/enqueueAbandon（:20-95，现 0 调用）与 pause/resume 同制接线进 task_repository 离线分支，task 生命周期离线入队补全（改造 #1）。
- 金融/积分语义域（光子）维持在线-only 不入队（AST 反刷口径，明确豁免本条）。
- 【依据：§2.2 OF-G2；FLEET-BRIEF 共同约束 4 诚实性；§4.5 错误态真因要求；TASK-013 docstring 承诺（task_repository.dart:24-27）】

**N36（§6 增补）· 数据溯源时点标记（stale 必带「截至 X」）**
- 呈现本地缓存/非实时数据时必须带时点标记（『截至 X 时』前缀或徽章，复用既有时间格式化）：统计域 isFromCache 链路已备（hybrid :105-107 → presentation 0 消费，存量靶），N34 离线快照读随批执行本条。
- 【依据：§2.2 OF-G4；§6「仪表数字必须有真源」的时点延伸；对标 §1.2 stale 行】

**N37（§9 增补）· 弱网参数登记制与超时常量归一（不冻结数值）**
- 超时常量归一进 ApiConstants 单一事实源（存量靶：statistics 三 provider 自立 Dio :108-145、auth retry Dio :77-82——触碰即改引用，不专项）；**全局数值不冻结不强制改**。
- 新增网络域 PR 审查口径（登记制）：轻查询 connect/receive 10/30s 基线、AI 生成/长推理类**禁依赖 receiveTimeout 表达超时**（流式域以心跳/事件超时为准，参照 ws 既有 30s 心跳形制）、写操作必须答「离线时行为」一问（入队/报错/豁免，接 N35 三态）。
- 【依据：§2.2 OF-G5；§2.0 RetryInterceptor 克制重试为正解范式；工程红线「口径单一事实源」客户端版】

**N38（§10.5 台账新增行，随 v1.6 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N31 图标钮语义标签基线 | 未开工（登记即生效） | 改造 #3 |
| N32 辅助设置叠加律+动效单一读法 | 未开工 | 改造 #2 |
| N33 持续动效可达守护（32 冻结） | 未开工 | 改造 #4 |
| N34 备考资产离线读红线 | 未开工 | 改造 #5/#7 |
| N35 离线写三态诚实+死代码接线 | 未开工 | 改造 #1 |
| N36 stale 时点标记 | 未开工 | 改造 #6（随 #5 同批） |
| N37 弱网参数登记制+常量归一 | 未开工（登记即生效） | 随触碰批 |
| AX-G6 header 语义/FocusTraversalGroup | 台账登记（列表 header 随触碰补） | —— |
| AX-G3 galaxy 星图读屏等效 | 观察行（一期接线 GalaxyNodeSemantics；替代视图量级触发转 L 级卡） | —— |
| OF-G3 outbox 全域扩展 | 观察行（N34 首批验收后逐域评估；附件类写操作暂缓） | —— |
| OF-G6 isOnline 冷启动盲区 | **砍**（<1s 自愈窗口，与 N20 冷启动预算冲突；备忘防重复立项） | —— |

---

## 5. 改造清单（按北极星收益排序 top8，供后续卡池直接取用）

> 每条：文件/改什么/验收标准/预估工作量（S≤半天，M≈1 天，L≈2 天+）。排序依据：对「期末一周用户备考效果」的直接度 > 触达频次 > 成本。与前轮清单关系：本表为两新面的 v6 批次，前轮未清偿项不受影响。

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **离线入队 UX 兑付（N35 首案）** | task_provider.dart:427-437/:439-449 pause/resume 补乐观更新（入队即本地置位）；error_lexicon.dart 增 offlineQueued 类别+中英文案；task_offline_queue.dart:20-95 三方法接线进 task_repository（照 :1266-1309 同制） | 离线暂停任务显示「已排队」且列表即时置位，恢复网络后自动同步 | widget test：模拟连接错误→断言任务状态已置位+错误位为 offlineQueued 类别；手测飞行模式 | S |
| 2 | **辅助设置叠加律（N32 首案）** | app.dart:120-134：textScaler 合成（系统×app）、disableAnimations/accessibleNavigation 改 `系统 ∨ in-app`；:128-133 platformDispatcher 直读七处读法迁 context.reduceMotion（触碰即迁可同批） | 系统大字号用户加载设置后字号不回跳；系统减弱动效不被 app 默认值覆盖 | widget test：注入 systemScale 1.3 + app 1.0 → 有效 scale 1.3；手测 iOS「较大字体」 | S |
| 3 | **图标钮首批标注（N31 首案）** | shell_navigation + 四 tab appbar + task_quick_action_menu + chat 输入行 + galaxy 控制条 20-30 钮补 semanticLabel（l10n 化）；守卫脚本登记 icon-only 无名基线 ~268 | 高频域读屏全有名 | a11y 断言测试（照 a11y_semantic_labels_test 形制）+ 守卫计数只降不升 | S-M |
| 4 | **reduce-motion 首批+DS helper（N33）** | motion.dart:97-104 createBreathingController 加 `reduceMotion` 参数（默认读 context）；timer_widget/flip_clock/star_background 三文件挂守护 | 专注页在减弱动效下无持续运动 | widget test：disableAnimations 注入下无 repeat ticker 活跃断言 | S |
| 5 | **错题本离线读（N34 首案）** | error_book_repository 列表接口加 warm 快照层（Isar 快照+fetchedAt；模式照 hybrid warm 层 :26-27/:105-107）；列表屏断网命中快照+N36 时点标记 | 地铁里能翻上次加载过的错题 | 集成测试：先在线加载→断网重进→快照呈现+「截至 X」标记 | M |
| 6 | **统计 stale 标记（N36 子句）** | 统计 presentation 各卡头部接 isFromCache → 『截至 X 时』前缀（数据源 hybrid markFromCache :105-107 已备） | 离线看统计知道数据时点 | widget test：isFromCache=true 断言徽标可见 | S |
| 7 | **任务列表离线读（N34 #2）** | task_repository getTasks/getTodayTasks 同制 warm 快照；today 视图断网呈现+时点标记 | 断网开 app 今日任务可见 | 同 #5 测试法 | M |
| 8 | **超时常量归一（N37）** | statistics 三 provider 自立 Dio（:108-145 等）与 auth retry Dio（api_interceptor.dart:77-82）改引用 ApiConstants :94-96；守卫登记「新增网络域必答离线行为」 | 四处常量归一 | grep 断言：字面量 Duration(seconds:30) 在 network 层外 0 新增 | S |

**被砍项备忘**（防后续卡重复立项）：isOnlineProvider 冷启动盲区专项修复（OF-G6——<1s 自愈窗口，修复与 N20 冷启动预算冲突）；galaxy 星图完整读屏替代视图（AX-G3 后半——工程 L 且量级未证，一期只接线既有 GalaxyNodeSemantics，替代视图挂观察行）；outbox 一次性铺全域（OF-G3——等 N34 首批 warm 快照模式验收后逐域评估，错题图片附件同步是真实盲点需先设计）；全局超时数值调整（OF-G5 后半——只归一常量不改数值，动全局值风险大于收益）；FocusTraversalGroup 显式分组专项（AX-G6 后半——默认遍历可用，随触碰补）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC6/REPORT.md`（本文件，位于 worktree wt255）；零产品代码改动（`mobile/lib`、`backend`、`scripts` 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作；未 commit / 未 push
- [x] /tmp 无驻留（全程未写 /tmp）；无启动进程/模拟器/浏览器，无 HEAVY 资源占用；worktree 内无 build/.dart_tool 产生
- [x] 引用代码均为 @f7343ae5 实测（rg/read/perl 邻近计数）；计数类结论（Semantics 320＝core/design 20+features 262、semanticLabel 76、Tooltip 63/tooltip: 49、SparkleIconButton 245+裸 IconButton 69 带名 46、liveRegion 95/header 2/FocusTraversalGroup 0/MergeSemantics 0/ExcludeSemantics 16、repeat 文件 50 守护 18、textScaler 读法 10、CustomPainter 文件 45 含语义 9、Image.network/asset 1 处、GalaxyNodeSemantics 等 0 引用、离线生产域 3、task 离线分支 2 处/task_offline_queue 0 外部调用、isFromCache presentation 0 消费、超时字面量 4 处自立）均为 grep/perl 实测；关键文件（app.dart、accessibility_provider、galaxy_accessibility_service、sync_engine、hybrid_statistics_repository、api_client、api_interceptor、offline_banner、connectivity_provider、websocket 两服务、galaxy_screen 节选）为文件实读；无编造引用
- [x] 对标研究未做外部浏览（web_search 实测 429「Limit Exhausted reset 2026-09-24」），方法声明已按前五轮先例如实标注
