# A-SPEC4 · 设计语言第四轮：两新面（启动与转场性能感知 / 通知与打断节律）UX 研究 → 自审 → 辩论 → SPEC v1.4 提案

> 卡：北极星全旅程战役 · A 纵队（设计语言线）研究卡第四轮 ｜ 2026-09-23 ｜ worktree **wt242**（分支 wt242-aspec4，base **7f855d70**）
> 性质：**纯研究卡，零产品代码改动**。所有代码引用只读走查（rg/read），file:line 均为 @7f855d70 实测。
> 前置读透：`v3-output/A-SPEC3/REPORT.md`（第三轮范本，本卡形制对齐它）+ `v3-output/DL-R3/SPEC.md`（v1.0+v1.1 正文）+ `v3-output/V13/REPORT.md`、`V13-RETEST/REPORT.md`（真机实测，计时与截图编号引用）+ `v3-output/V13-MAJORS/REPORT.md`（引导链 29s→6-8s 的拆解依据）+ `v3-output/COLDSTART/REPORT.md`（galaxy 冷启动定性，本卡「冷启动」语义与其不同——彼卡是图面数据冷启动，本卡是**端上启动/转场的等待感**）。本提案**不推翻 v1.0-v1.3 任何条款**，全部为增量/澄清/存量靶登记，编号接续 v1.3 的 N19（N20 起）。
> 对标研究方法声明：本会话外部搜索配额耗尽（web_search 429，与前两轮同况），对标做法基于公开常识 + UX 专业判断（沿用 A-SPEC-V1_1/A-SPEC2/A-SPEC3 三轮卡内授权先例）；引用代码均为树内实测，V13 实证均为报告编号实读。
> 两面范围界定（按卡）：①启动与转场性能感知=冷启动全链（main→splash→home）+ 路由转场语法 + 操作→反馈微延迟 + 骨架/spinner 等待表达（与第三轮三态矩阵衔接但聚焦「等待感」）；②通知与打断节律=全 app 打断面（SnackBar/Dialog/Sheet/banner/badge）分布与频次 + 连续打断链审计 + 通知中心内容分级（§7.3-5 集中制既定落点之上看「哪些该进中心、哪些只该 toast、哪些沉默」）。

---

## 0. 方法与多轮过程记录

照前三轮四步执行：

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 研究 | 面1 按 iOS 冷启动手感基线（首帧即刻有形、splash 是品牌一瞬不是加载闸）、Telegram/Flighty 的「转场不挡点击」、Things 的静默成功提四维做法；面2 按 HIG 通知分级（即时/摘要/静默）、Linear inbox 集中制、系统专注模式提节律做法 | §1 两张对标表 | 两面共性直指北极星：**备考用户的等待感和被打断，都是「专注」的反面**；新增两条面性公约：**等待必须有形状（结构/阶段/乐观 三选一），白屏与无限转圈是唯一禁答**；**打断必须声明三件事（为何现在、点去哪、怎么消失）** |
| R2 自审 | 冷启动链逐行走查（main.dart→app.dart→routes.dart→splash→auth）；转场语法 32 个 route 文件全量比对；骨架/spinner/乐观更新三面 grep 计数；打断面四类（toast/dialog/sheet/banner）+badge 全库计数与链路追踪（AppFeedback 625 处逐域分布、unreadMessageCountProvider 全引用面） | §2 两张全景表 + 差距清单 12 条（带 file:line） | **冷启动表现层三段动画叠加 1.6s+ 无总预算条款**（320ms 全壳 fade + 900ms 四段 splash + 400ms 落地转场，D-3 台账未开工）；**badge 计数器只增不清**（unreadMessageCountProvider 全库 0 处 decrement/reset）；**通知 priority 字段存在但零分级决策**（每个 WS 通知一律 toast+进中心双写） |
| R3 辩论 | 12 条逐条过三关（真差距？收益/成本/风险？北极星加权值不值？） | §3 辩论记录：采纳 8 / 改写采纳 2 / 砍 1 / 转台账 1 | 被砍主导理由：spinner 残余属 §4.4.2 既有条款的执行批，不属新差距；转台账项卡在活栈复测定性（离线冷启动登出） |
| R4 成文 | 过关差距 → v1.4 增量条目 N20-N24 + 台账行 + top8 | §4 / §5 | v1.4 共 5 条增量，全部为 v1.0-v1.3 的增补/执行令/生命周期登记，无推翻 |

**结构性结论先行（两条，均为「节律级」）**：
1. **等待感的三段无人总账**：cold start 的表现层开销分散在三个互不隶属的文件（app.dart 的 `_ColdStartFade` 320ms、splash_screen 的 900ms 四段编排、sparkle_route_transition 的落地 400ms），任何一处都不觉得自己是问题，叠加后纯动画串行开销 ≈1.62s——且其中 splash 段实际被 auth 网络往返门控（routes.dart:161-172 redirect 在 `isLoading` 期间钉在 splash），**900ms 是下限不是上限**。§2.5 D-3 只管了 splash 自己（≤400ms），没有「冷启动表现层总预算」的条款。
2. **打断是「单点合规、全局失律」**：单个打断面全部走了 owner（AppFeedback 625 处收敛、raw SnackBar 构造残余仅 2 处），但全局没有任何节律机制——`_show` 的 `hideCurrentSnackBar()` 顶替语义（app_feedback.dart:85）意味着 toast 之间互相踩踏而非排队；通知的 `priority` 字段（unified_notification_model.dart:34）只被 demo 模式的假分析消费（notification_center_repository.dart:438/488/509），真实链路里**每个 WS 通知都是「toast+进中心」双写直通**（chat_notifier_actions.dart:776-800）；badge 计数器只增不清，一次触发永久驻留。打断面是「合规的砖」，缺的是「节律的梁」。

---

## 1. 两面对标研究表（R1）

### 1.1 启动与转场性能感知 · 对标：iOS 冷启动手感 / Telegram / Flighty / Things（公开常识，声明见页眉）

| 维度 | iOS/HIG 冷启动手感 | Telegram | Flighty | Things | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|---|
| 冷启动哲学 | 首帧即刻有形（launch screen 是首屏的静态预告，不是品牌剧场）；动画与初始化并行，永不串联 | 冷启动近零装饰：直接恢复上次会话，splash 一闪即过 | 启动即上次航班状态，「恢复」先于「欢迎」 | 打开即 inbox，无 splash | **splash 时长 = 品牌一瞬（≤400ms 量级），认证/数据门不该让它变长**；Sparkle 的 auth RTT 钉在 splash 上（routes.dart:161-172）是对标反例 |
| 等待三选一 | —— | 骨架/缓存先行，历史分叉逐条补 | 结构先出后填数据 | 本地库即开即读，零网络等待 | **等待必须有形状：结构（骨架贴布局）/阶段（分期文案）/乐观（本地先行）三选一**，白屏与无限转圈是唯一禁答（§4.4 精神的感知侧总括） |
| 转场不挡操作 | 转场期间目标页可交互、返回手势全程可用 | 消息列表转场中已可滚动 | push 进行中已可点返回 | —— | **转场是渐显不是闸门**：tap 可跳过、reverse ≤ forward（§2.1.1 既有）；Sparkle 冷启动转场已有 tap-skip（sparkle_route_transition.dart:201-203），是达标先例，应升格为全转场语法 |
| 微反馈 | <100ms 即有反应（按压态/乐观态），成功是预期不庆祝 | 消息发出立即上屏（时钟未转=已发出），失败才安静地标叹号 | —— | 勾选完成无 toast 无音效，勾完即完 | **静默成功是高频域默认**（§4.5 乐观 UI 行既有「成功不庆祝」，本轮发现执行缺口：成功 toast 229 处 vs undoable 12 处） |
| 转场语法统一 | 同一导航层级同一动效（tab 切换零转场、push 一律 forward-axis） | tab 切换零动画，push 统一 shared-axis | tab 零转场 | tab 零转场 | **tab 切换=零转场**是全品类默认；同层混用「即时 tab + 400ms 动画 tab」会让用户感知为「那个 tab 更重/卡」 |

**面性公约提炼**：①**splash 是一瞬，不是闸门**（认证判定与品牌动画并行且 splash 不得被网络 RTT 拉长——超时即给可交互的降级面）；②等待三选一（结构/阶段/乐观），白屏与裸转圈禁答；③tab 零转场、push 同语法、转场可跳过；④成功不庆祝（静默成功）是高频域执行令。

### 1.2 通知与打断节律 · 对标：HIG 通知分级 / Linear inbox / 系统专注模式 / Duolingo 打断克制

| 维度 | HIG/系统通知分级 | Linear inbox | 系统专注模式 | Duolingo | 对 Sparkle 的可迁移判断 |
|---|---|---|---|---|---|
| 分级哲学 | 即时（时间敏感）/ 摘要（定时汇总）/ 静默（仅入中心）三级，由发送方声明级别、系统按语境执行 | 一切通知进 inbox，未读数是唯一常驻打断；inbox 外零 toast | 专注时段按「允许名单」放行，其余静默收集 | 练习中零打断：连错不弹窗，错题留在结算页 | **三级制的关键不是「能不能弹」而是「谁有权决定弹」**——级别由内容声明，语境（是否专注中）拥有一票否决权 |
| 打断三声明 | 每条通知：为何现在（时间敏感理由）+ 点去哪（deep link）+ 怎么消失（可清） | 每条 inbox 项可标已读/可静音订阅源 | 允许名单可查可改 | —— | **打断必须声明三件事：为何现在、点去哪、怎么消失**；横幅点了没反应=欺骗性可供性（对标零先例） |
| badge 生命周期 | 角标数=未读事实，看即清（进 app 即清是系统默认行为） | 打开即清未读数 | —— | 红点跟随任务状态即时消长 | **badge 是债不是资产**：只增不清的角标从「召回钩子」退化为「狼来了」；进入目标面即清是底线 |
| 节律上限 | 摘要级天然聚合；时间敏感级稀缺（滥用即被系统降权） | 未读数天然聚合，不逐条打断 | 静默窗系统级 | 每日一条提醒，可关 | 连续打断必须有聚合（同源事件合并、toast 顶替不排队×节流）；本地提醒与远端推送同受静默窗约束（§7.3-2 的 23:00-8:00 应纳管本地通知） |

**面性公约提炼**：①**学习中的打断克制是北极星直接条款**（专注备考场景里，可延迟信息在中断学习 = 直接损害备考效果，与 §7.3 推送宪法同源的 app 内版）；②打断三声明（为何现在/点去哪/怎么消失）缺一即未完成；③badge 生命周期=触发条件+清除时机+到达路径三声明。

---

## 2. 自审差距清单（R2，全部 @7f855d70 实测）

### 2.0 先说达标项（诚实记录——等待感与打断面的 owner 化程度是本轮最大好消息）

- **转场 owner 覆盖近乎全量**：32 个 feature route 文件全部 `pageBuilder` + 自定义转场 helper（逐文件比对实测），`MaterialPageRoute` 残余仅 4 处（capsule_jobs_screen.dart:286、unified_settings_screen.dart:692/2079/3817）；5 个 tab 分支中 4 个 `NoTransitionPage`（routes.dart:226/244/348/365）。
- **冷启动转场可跳过**：`ColdStartRouteTransition` tap 即跳过动画直达内容（sparkle_route_transition.dart:173-182/:201-203），reduce-motion 独立降档（:129-134）。
- **首屏骨架贴布局**：dashboard 首载用按区块组合的 SparkleCardSkeleton（CompactStatusBar/AuroraBand/目标切换/指挥中心逐块，dashboard_screen.dart:552-585）；home 域骨架 24 处、plan 32 处、community 21 处（grep 实测）；A-SPEC3 EE-G5 的 tools 裸 spinner 已清偿为 ToolBodySkeleton（focus_stats_tool.dart:91、notes_tool.dart:228），EE-G2 通知中心双份错误已清偿（notification_center_screen.dart:261-276 修复注释在案）——第三轮批次已落本基线。
- **乐观更新主链在位**：任务完成乐观置 completed+syncStatus 标记（task_provider.dart:479-540，失败不回滚改标 failed 保留现场）；聊天发送 temp_user 气泡立即上屏+in-flight 禁发（chat_provider.dart:965-979/:1013-1026）；capsule/settings/seed_library/galaxy/subtask 均有乐观注释点（grep 46 处）。
- **启动工程面成熟**：main.dart 阻塞链与首帧后延迟 warmup 分离（main.dart:74-125 vs :199-214），`app_first_frame` 遥测已埋（:148-161）；同步引擎 auth 后延迟 900ms 才启动（app.dart:40-47 `deferredSyncBootstrapProvider`）；auth 会话世代竞态收口（auth_provider.dart:61-68 注释在案）。
- **导航感官语言一致**：`SensoryNavigationObserver` 统一路由 push/pop 触觉+BGM duck，160ms 去抖+首次路由豁免（sensory_navigation_observer.dart:22-33）。
- **打断面 owner 收敛完成**：AppFeedback 625 处单一入口（info/success/warning/error/loading/undoable 六档），raw `SnackBar(` 构造残余仅 2 处（§2.1b 矩阵行 + IR-G10）；错误 4s/成功 2.5s 分档时长（app_feedback.dart:135-138）；SparkleBottomSheet owner 在位（sensory_modals.dart:51-）。
- **消息横幅尊重专注模式**：InAppNotificationOverlay 在 focusMode 开启时不渲染（message_notification_service.dart:91）——「学习中的打断克制」已有第一个机制化先例。
- **通知中心能力面完整**：unread 99+ 截断、markAllAsRead、清已读、双维筛选（notification_center_screen.dart:27-90/:49-90）；intervention 卡 seen/accepted/snoozed(24h)/acted 四动作（notification_center_provider.dart:98-155）——「可延迟信息」机制已在中心内成型。
- **V13 实测等待感锚点**：注册→引导落地 **6-8s**（V13-RETEST 判定面 3，2s 粒度帧轮询；修复前 29s+30s 掷硬币）、聊天发送→AI 回复渲染 ≤3s、断流 75s 看门狗可见错误+重试 ≤4s 重启流、断网横幅+缓存不裸崩（V13 步骤 14 / RETEST 6a）。

### 2.1 面 1 · 等待感全景表（环节 × 现状 × 感知成本 × 改法）

| # | 环节 | 现状（file:line @7f855d70） | 感知成本 | 改法 |
|---|---|---|---|---|
| W1 | 原生帧→Flutter 首帧 | 阻塞链：Hive+Isar+认知迁移+prefs+Sentry+ViewStorage+Theme+Tracing（main.dart:74-125）；有 app_first_frame 遥测（:148-161） | 中（不可见但绝对时长） | 维持；遥测已有，增「表现层动画总时长」口径随 N20 |
| W2 | splash 段 | **900ms 四段编排**（logo scale→title→subtitle→indicator，splash_screen.dart:28-53）；**且被 auth 网络往返门控**——redirect 在 isLoading 期钉在 splash（routes.dart:161-172），`getCurrentUser` 是纯网络调用（auth_repository.dart:263-276），30s receiveTimeout 兜底 | 高（每次冷启动必然付费；弱网下无上限） | D-3 执行（≤400ms 合段）+ N20 总预算 + splash 期 auth 门给降级（见 IR-G12） |
| W3 | 落地段 | splash→home 400ms fade+slide 转场（sparkle_route_transition.dart:129-134）；另有全壳 `_ColdStartFade` 320ms（app.dart:227-231）与 `_ThemeTransitionShell` 280ms（:164）首帧叠加 | 中（三段叠加约 1.6s，用户读作「慢」） | N20 叠段禁令（表现层动画串行总预算 ≤600ms） |
| W4 | 注册→引导冷旅程 | 修复后 6-8s（V13-RETEST 判定面 3）：prefs ~1s+种子 <1s+first_message 8s 有界且在 2-5 步期间并行 | 中（新用户第一印象，已从 29s 修复） | 维持；V13-MAJORS 预期「常态 3-5s」需实机复测确认 |
| W5 | 首屏 home | 骨架贴布局（:552-585），骨架→内容无布局跳变设计 | 低（达标） | 维持 |
| W6 | tab 切换 | 4/5 tab `NoTransitionPage` 零转场（routes.dart:226/244/348/365），**chat tab 唯一 400ms 冷启动转场**（:321-338 + :120-153） | 中（同层两种时感，chat 显得重） | N20 子句：tab 切换零转场是唯一语法（IR-G9） |
| W7 | 二级屏 push | 全量自定义转场 200-300ms+fade（sparkle_route_transition.dart:57-76）；骨架覆盖 22 域 63 处 vs 面板级裸 spinner 残余（insights learning_dashboard_screen.dart:392-394 居中转圈） | 低-中 | 中屏 spinner 残余并入 §4.4.2 执行批（IR-G11，不立新条） |
| W8 | 操作→反馈 | 主链乐观达标（§2.0）；**task 快捷菜单双 toast**：loading+success 串弹（task_quick_action_menu.dart:101→105/:122→126）且错误路径 `error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '')` 洗 text 直出（:111/:133，N15 同型） | 高（每次暂停/跳过/标记太难=三次打断：sheet+2 toast） | N23 静默成功执行令 + N15 批次续（IR-G8） |
| W9 | 消息发送 | temp_user 立即上屏+in-flight 禁发（chat_provider.dart:965-1026） | 低（达标） | 维持 |
| W10 | 弱网/断网 | OfflineBanner 全局（app.dart:116）+缓存不裸崩（V13 PASS）；但 chat 域 WS 重连另有 toast 循环（IR-G5） | 中（双报告源互相竞争） | N21 连接状态单一报告源 |

### 2.1b 面 2 · 打断面矩阵（类型 × 全库计数 × 分域头部 × 节律判定）

| 打断面 | 全库计数（grep 实测） | 分域头部 | 节律判定 |
|---|---|---|---|
| toast（AppFeedback） | **625 处**（error 271 / success 229 / info 95 / warning 14 / undoable 12 / loading 3） | user 106、community 103、chat 61、task 52、plan 41、memory 33、tools 31、home 28、seed_library 24 | owner 收敛达标；但 success:undoable = 229:12，§4.5「静默成功」执行率低；`hideCurrentSnackBar` 顶替语义（app_feedback.dart:85）=连续 toast 互相踩踏，最后一手赢、前手未读 |
| toast（raw SnackBar 构造） | 2 处 | galaxy_error_dialog.dart:172（私有 `GalaxyErrorSnackBar`，类型化映射+自有配色）；experience_envelope_indicator.dart:254（含硬编码中文「已记录你的纠正」） | galaxy 私有 error toast owner=N16「新域禁私有映射」的存量续记；envelope 处为 N18 同型内联中文 |
| Dialog | 62 处 show | user 13、translation 6、error_book 6、seed_library 5、task 4、chat 4 | 无分级（确认类/信息类/成就庆典类同权）；成就解锁 dialog 与 toast 双通道（IR-G4） |
| BottomSheet | 17 处 raw `showModalBottomSheet` + 1 处 owner（theater 3、report 2、plan 2、galaxy 2、chat 2、core/statistics 2…） | —— | SparkleBottomSheet owner 在位但几乎无人用（A-SPEC3 PD-G1 同型的 sheet 版，触碰即迁不立项） |
| banner | OfflineBanner（全局，app.dart:116）+ HomeNotificationCard（home_notification_card.dart:16-34）+ InAppNotificationBanner（message_notification_service.dart:91-） | —— | OfflineBanner 合规；HomeNotificationCard 消费永不归零的 badge 计数（IR-G2 连带）；消息横幅 onTap 死链（IR-G6） |
| badge/红点 | community tab 角标（shell_navigation.dart:250/:284-306）+ 同一计数驱动 home 横幅与 dashboard:2950 | 唯一计数源 unreadMessageCountProvider | **只增不清**：increment 3 处（community_provider.dart:1042/1828/1878），decrement/reset 全库 0 调用（IR-G2） |
| 端外推送/本地提醒 | NotificationService+UnifiedPushService+TaskNotificationScheduler（1440/60/15 分钟三档，task_notification_scheduler.dart:15-17） | —— | 本地提醒无静默窗钳制（IR-G7）；调度面 grep quiet/night 0 命中 |

### 2.2 差距清单（12 条）

| # | 差距 | 证据（file:line @7f855d70） | 违反/衔接条款 |
|---|---|---|---|
| IR-G1 | **冷启动表现层三叠段无总预算**：320ms 全壳 fade（app.dart:227-231）+900ms 四段 splash（splash_screen.dart:28-53，D-3 删除清单台账未开工）+400ms 落地转场（sparkle_route_transition.dart:129-134）串行叠加 ≈1.62s；splash 段还被 auth 网络往返拉长（routes.dart:161-172 + auth_repository.dart:263-276 纯网络 getCurrentUser） | 同列 | §2.5 D-3 只管 splash 自身；无「冷启动表现层总预算」条款；对标 §1.1 冷启动哲学行 |
| IR-G2 | **badge 计数只增不清**：unreadMessageCountProvider 定义 increment/decrement/reset 四方法（message_notification_service.dart:41-46），全库实际调用仅 increment×3（community_provider.dart:1042/1828/1878），decrement/reset 0 处——community tab 角标+home 横幅（home_notification_card.dart:19-34）一次触发永久驻留，重启才清 | 同列 | 对标 §1.2 badge 生命周期行；「仪表数字必须有真源」精神的节律版（角标不再是未读事实） |
| IR-G3 | **通知零分级双写直通**：WS NotificationEvent 一律「toast+进中心」双写（chat_notifier_actions.dart:776-800）；`priority` 字段存在（unified_notification_model.dart:34）但仅被 demo 假分析消费（notification_center_repository.dart:438/488/509）——分级数据在、分级决策无 | 同列 | §7.3-5 集中制只定了「进中心」，未定「何时还可 toast/何时沉默」；对标 §1.2 三级制 |
| IR-G4 | **成就解锁双通道打断**：同一事件同时 setPending 弹全屏 dialog（chat_notifier_actions.dart:654-656 → shell_navigation.dart:89-99/:180-190）与 toast（:659-666）；dialog 通道无 focusMode 豁免（对照消息横幅有豁免 message_notification_service.dart:91） | 同列 | §4.5 成功不庆祝精神（庆典类是例外但应单通道）；对标 §1.2 打断三声明 |
| IR-G5 | **连接状态双报告源**：chat WS 重连循环 toast（reconnecting→loading / connected→success / failed→error，chat_screen.dart:305-332）与全局 OfflineBanner（app.dart:116）同屏竞争；弱网下 toast 顶替循环闪烁 | 同列 | 对标 §1.1「等待三选一」（连接状态是状态不是事件，该常驻不该闪现）；§2.6 同屏源纪律的节律版 |
| IR-G6 | **消息横幅 onTap 死链**：InAppNotificationOverlay 的 onTap 只 dismiss，注释自认「Navigate to chat - this would need the navigator key or context」（message_notification_service.dart:96-99）；且社区 WS 处理器在可见消息标记已读的同一分支仍 increment+show（community_provider.dart:1036-1051，正在看聊天也弹横幅——此点需活栈确认，见 §6 申报） | 同列 | 打断三声明之「点去哪」缺席；欺骗性可供性 |
| IR-G7 | **本地任务提醒无静默窗**：1440/60/15 分钟三档只按 dueTime 倒排（task_notification_scheduler.dart:15-17/:104-143），无 23:00-8:00 钳制（grep quiet/night/silent 0 命中）——清晨截止的任务会在前夜深夜连响 | 同列 | §7.3-2 静默窗条款只管了远端推送，本地提醒未纳管 |
| IR-G8 | **快操作 loading→success 双 toast+洗 text**：task_quick_action_menu.dart:101→105/:122→126 每动作两 toast（sheet 之外第三次打断）；错误路径 `error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '')` 直出（:111/:133，N15 同型存活；同型 task_provider.dart:1059） | 同列 | §4.5 乐观 UI 行「成功不庆祝」明文；N15 洗 text 禁令的同型未清项 |
| IR-G9 | **chat tab 转场语义错位**：唯一带 400ms 冷启动转场的 tab（routes.dart:321-338；其余 4 tab NoTransitionPage）——400ms 属 M4 级时长且无手势动量驱动（§2.1.2 判定违） | 同列 | §2.1.2（M4 须手势动量）；对标 §1.1「tab 切换零转场」 |
| IR-G10 | **galaxy 私有 error toast owner 并存**：`GalaxyErrorSnackBar`（galaxy_error_dialog.dart:167-209，类型化 GalaxyError 映射+自有配色+自带 hideCurrentSnackBar）为 SparkleSnackBar 之外的第二个 error toast 形制 | 同列 | N16（映射单一 owner）的 toast 形制域续记 |
| IR-G11 | **中屏面板级裸 spinner 残余**：insights learning_dashboard_screen.dart:392-394 居中转圈（面板级）；weekly_growth_narrative_card.dart:349；对照 learning_path_dialog.dart:178/192 行内 spinner 属合规位 | 同列 | §4.4.2（裸 spinner 禁新增于首屏主路径——中屏面板级属存量清偿批） |
| IR-G12 | **离线冷启动=强制登出+本地数据清除（待活栈定性）**：checkAuthStatus 内层/外层 catch 不分错误类型一律 `_resetInvalidStoredSession`（auth_provider.dart:161-162/:167-168）→ clearTokens+清聊天缓存/视图状态/Isar 用户域（:86-99/:101-122）；getCurrentUser 无本地缓存回退（auth_repository.dart:263-276）——冷启动时网络不可达可能被当作会话失效 | 同列 | 「重试必须保留用户已输入内容」（§4.5 错误态）精神的启动版；**本卡零代码未复测，V13-RETEST ④-1 社群域重启 401 或与此同源，转台账** |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。每条给出裁决：**采纳 / 改写采纳 / 砍 / 转台账**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| IR-G1 | 冷启动三叠段 1.62s 无总账，D-3 单点条款管不住叠加，必须立「表现层总预算」 | 蓝方：三段分属三文件各有机能（品牌/防白屏/落地），且 tap-skip 已在；总预算条款执行难测量 | G1 真差距（V13 实测首启观感「慢」的直接构成；900ms splash 还被 auth RTT 拉长成变量）；G2 收益高/成本 M（D-3 本就待执行，叠段禁令是条款不是代码）；G3 高——新用户第一 impressions 即备考工具的「快」签名 | **采纳**（N20 立条；改造 #6 执行 D-3+叠段收敛） |
| IR-G2 | badge 永不清除是硬缺陷，角标失去信息价值且连带 home 横幅假警报 | 蓝方：S 级一行修复；且当前无「进入即清」的机制化约定，修计数器不修机制还会复发 | G1 真差距（grep 全库 0 清除点实锤）；G2 成本 S（进入 /community 即 reset）+条款 S；G3 中-高（社群是冲刺小队/自习室载体，假角标直接侵蚀协作召回） | **采纳**（N24 立条含清除时机声明；改造 #1 修复计数器） |
| IR-G3 | 通知必须按 priority 三级分流，中心是全量落点、toast 是特权 | 蓝方：优先级数据引擎侧质量未知，贸然静默 medium 可能漏掉重要干预；改造动 WS 事件链 | G1 真差距（双写直通实锤：776-800）；G2 分级门控=客户端单点（chat_notifier_actions 一处 switch），引擎数据质量另核；G3 高——备考中每个 toast 都在学习中段打断（§1.2 公约①） | **采纳**（N22 立条：high 即时/medium 摘要（仅中心+红点）/low 静默；medium 静默的默认档宁高勿低，见条目内保守条款） |
| IR-G4 | 成就双通道（dialog+toast）重复打断，且 dialog 不受专注豁免 | 蓝方：成就是设计好的庆典时刻（§2.4 签名位同族），双通道是冗余不是冲突；改它动庆典仪式 | G1 真差距（654-666 双写实锤）；G2 成本 S（toast 侧加 dialog-pending 门，shell 已有 `_isShowingAchievementDialog` mutex 可复用）；G3 中——庆典保留最强通道（dialog），toast 冗余 | **采纳**（并入 N22 子句：庆典单通道+专注豁免对齐） |
| IR-G5 | 连接状态应单一报告源，chat 重连 toast 循环砍掉 | 蓝方：OfflineBanner 只报断网，不报 WS 半连接（HTTP 通 WS 断）；重连 toast 有信息量 | G1 真差距（两源竞争实锤）；G2 改写：不砍信息、改承载——重连状态走 chat 已有的常驻状态件（阶段胶囊族），事件化 toast 只保留 failed 终态；G3 中-高（弱网宿舍/地铁是备考常态，toast 闪烁正发生在学习流中段） | **改写采纳**（N21 立条：OfflineBanner=全局唯一横幅源，域内连接状态必须常驻形（状态行/胶囊），禁事件化 toast 循环） |
| IR-G6 | 横幅 onTap 死链必须修，打断三声明缺「点去哪」 | 蓝方：banner 是社区消息提示，点横幅 vs 点 tab 差别小；navigatorKey 已全局可用，修复极低成本 | G1 真差距（:96-99 注释自认）；G2 成本 S；G3 中（低频面）；正在看聊天仍弹横幅的半段需活栈确认，不并入裁决 | **采纳**（N24 三声明条款覆盖；改造 #2 深链修复；「可见即弹」半段转观察行） |
| IR-G7 | 本地提醒纳入 23:00-8:00 静默窗 | 蓝方：任务提醒是用户自设 deadline 的衍生品，深夜响是用户自己的时间安排；加钳制可能吞掉「黎明截止」的有效提醒 | G1 真差距（0 钳制实锤）；G2 成本 S（调度时钳制+静默窗内改为首帧后补发摘要）；蓝方「自设 deadline」不成立——三档提醒是系统默认策略非逐条用户意志；G3 中（睡眠是备考效果的一部分，凌晨推送直接反北极星） | **采纳**（并入 N22 静默窗子句；改造 #3） |
| IR-G8 | 快操作双 toast 改静默成功+洗 text 清偿 | 蓝方：暂停/跳过是低频管理动作，双 toast 是「确认感」；洗 text 已有 N15 批次 | G1 真差距（§4.5 明文「成功不庆祝」，task 恰是高频域；sheet+loading+success 三连打断）；G2 成本 S（删 loading toast、success 改静默/或仅 onChanged 刷列表）；G3 高——暂停/跳过正是备考周高频自我调节动作 | **采纳**（N23 立条：AppFeedback.success 229 处 ratchet 冻结+高频域先清；洗 text 两靶并入 N15 批次续记） |
| IR-G9 | chat tab 400ms 转场违 tab 零转场语法 | 蓝方：400ms 转场是给深链冷启动进 chat 用的，tab 切换复用同一 pageBuilder 属实现耦合；改 NoTransitionPage 会伤深链入场 | G1 真差距（同层两种时感实测在码）；G2 成本 S（tab 分支与深链分支拆 pageBuilder）；蓝方承认实现耦合=承认应拆；G3 低-中 | **采纳**（N20 子句：tab 零转场唯一语法；冷启动转场仅限 splash/auth→shell 落地段；改造 #4） |
| IR-G10 | galaxy 私有 error toast owner 迁编 | 蓝方：GalaxyErrorSnackBar 类型化映射是 N16 认证的正解形制，且 galaxy 域内自洽；迁编=工艺债 | G1 半差距（形制正确、位置违单源）；G2 按 N16 先例「触碰即迁不专项」；G3 低 | **改写采纳**（不立新条；N16 台账续记一行，galaxy 私有 toast owner 触碰即迁编 core） |
| IR-G11 | 中屏面板级 spinner 残余清偿 | 蓝方：§4.4.2 已有条款，属执行批不属新差距；insights 两处是次级卡内件 | G1 非新差距（条款在、A-SPEC3 三态矩阵已立面）；G2 成本 S；G3 低 | **砍**（不立条）；learning_dashboard:392-394 与 weekly_growth:349 并入 §5 改造清单 #7 顺手批，随同域触碰执行 |
| IR-G12 | 离线冷启动强制登出+清数据，必须改会话保护 | 蓝方：本卡零代码未活栈复测，且涉及鉴权语义（token 究竟失效没有要后端定），UI 单侧改可能掩盖真实 401 | G1 疑似真差距（代码链实锤但行为未实测——诚实性优先）；G2 修复需与 C 线/后端协同（refresh 语义+离线兜底策略），且 V13-RETEST ④-1「社群域重启 401」或与此同源；G3 高-风险（若坐实，弱网宿舍冷启动=登出+聊天缓存被清，对备考周是灾难级） | **转台账**（观察行：活栈复测定性→派修复卡；改造清单 #8 预挂 M 项供直取） |

**辩论统计**：12 条 → 采纳 8（IR-G1/IR-G2/IR-G3/IR-G4/IR-G6/IR-G7/IR-G8/IR-G9；其中 IR-G4/IR-G7 为子句并入 N22，IR-G9 为子句并入 N20）/ 改写采纳 2（IR-G5/IR-G10）/ 砍 1（IR-G11）/ 转台账 1（IR-G12）+1 观察半段（IR-G6 的「可见即弹」）。砍单主导理由：**条款已在、属执行批**（spinner 残余）；转台账主导理由：**活栈未定性行为不动**（离线登出）。

---

## 4. SPEC v1.4 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0-v1.3：编号规则 + 依据 + 可验收数字；不推翻 v1.0/v1.1/v1.2/v1.3 任何条款。编号接续 v1.3 的 N19。生效方式建议沿用 §1.7 两段门禁先例（文本即生效 / 守卫绑合入时点）。

**N20（§2 增补）· 冷启动表现层总预算与转场语法唯一（一段式冷启动）**
- 冷启动全程（原生首帧→可交互 home）的表现层动画**串行总预算 ≤600ms**：叠段禁令——`_ColdStartFade`（app.dart:227-231）、splash 编排（splash_screen.dart）、落地转场三者不得全额串联；D-3 执行口径并入本条（splash ≤400ms 一轮、logo→title→subtitle→indicator 四段并一段）。`app_first_frame` 遥测（main.dart:148-161）增补「表现层动画总时长」口径作验收数字。
- **tab 切换零转场是唯一语法**：`StatefulShellRoute` 各分支一律 `NoTransitionPage`；`buildColdStartTransitionPage`（400ms 档）仅限 splash/auth→shell 的落地面与深链冷入场，禁复用于 tab 分支（存量靶 routes.dart:321-338 chat 分支）。
- **splash 不是闸门**：认证判定与 splash 并行的 TRIAGE 结论（§11 R6）升格为条款——splash 期认证等待不得延长品牌动画；等待超 2s 必须给可交互降级（跳登录/重试），禁无限 spinner（§4.4.2 同源）。
- 【依据：§2.2 IR-G1/IR-G9；§2.5 D-3 既有删除清单；对标 §1.1 冷启动哲学/tab 零转场行；V13 首启实测观感】

**N21（§4.5/§7 增补）· 连接状态单一报告源（横幅唯一、状态常驻、事件终态）**
- 全局连接状态横幅唯一 owner=`OfflineBanner`（app.dart:116）；域内连接子状态（WS 重连/半连接）**必须以常驻形呈现**（状态行/阶段胶囊族，chat 已有 `ChatRunPhaseIndicator` 先例），**禁事件化 toast 循环**——同一连接状态迁移链 toast 触发 ≤1 次（终态 failed 才可 toast）。存量靶：chat_screen.dart:305-332 reconnecting/connected 循环 toast。
- 【依据：§2.2 IR-G5；§4.5 回归一等状态精神；对标 §1.1「等待三选一」；§2.6 同屏源纪律的节律域同型】

**N22（§7.3 增补，app 内推送宪法）· 打断三档分级 + 静默窗纳管本地 + 庆典单通道**
- **三档分级**：WS 通知按 `priority` 分流——`high`=即时 toast+进中心；`medium`=仅进中心+红点（摘要档，用户下次到中心/首页横幅时可见）；`low`=静默入中心。分级门控落点唯一（通知事件入口单点分流，chat_notifier_actions.dart:776-800 现直通处）；**保守条款**：引擎侧 priority 质量未标定前，intervention 与 aurora_confirm 两类一律按 high 处理（宁多一次 toast 不可漏干预），其余类按档执行。
- **静默窗**：23:00-8:00（§7.3-2 既有）纳管**本地任务提醒**（task_notification_scheduler.dart:104-143 调度时钳制：窗内时点顺延至窗后最近时点，黎明截止类保留为 high 时间敏感例外由用户自设）。
- **庆典单通道**：成就解锁 dialog 在场时抑制同事件 toast（dialog-pending 门）；庆典类打断受 focusMode 豁免约束（与消息横幅 message_notification_service.dart:91 同制）。
- 【依据：§2.2 IR-G3/IR-G4/IR-G7；§7.3 推送宪法的 app 内延伸；对标 §1.2 三级制/专注模式行；北极星「专注备考」直接性】

**N23（§4.5 执行令）· 静默成功 ratchet（成功不庆祝的机检落地）**
- 高频域（task/plan/chat 发送/勾选/开关类）操作成功**禁 toast**（§4.5 乐观 UI 行「成功不庆祝」既有条款的执行令）：成功反馈=状态本体变化（列表项勾选态、卡片位置），仅 undoable/低频里程碑可 toast。存量 ratchet：`AppFeedback.success` 调用面现值 **229 处**冻结只降不升（守卫并入 DL-SPEC ratchet 家族）；首批清偿：task_quick_action_menu 双 toast（:101→105/:122→126 改静默成功+删 loading toast，乐观上屏已存在）。同批清偿洗 text 两靶（task_quick_action_menu.dart:111/:133，N15 同型）。
- 【依据：§2.2 IR-G8；§4.5 既有明文；对标 §1.1 Things/Telegram 静默成功；N15/N18 的 ratchet 同制】

**N24（§4.2/§9.1 增补）· 打断面生命周期三声明（badge/横幅的触发·清除·到达）**
- 任何 badge/红点/横幅类打断件注册时必须声明三件事，缺一即未完成：①**触发条件**（什么事实发生）；②**清除时机**（进入目标面即清/事实消失即清——只增不清的计数器禁新增）；③**到达路径**（点按必达目标面，deep link 或等价跳转，禁 dismiss-only 的死链横幅）。存量靶：unreadMessageCountProvider 零清除点（改造 #1）、消息横幅 onTap 死链（message_notification_service.dart:96-99，改造 #2）。
- 机检登记（不冻结基线，登记制）：badge 计数类 provider 定义文件须含清除方法且有调用点（grep 可查），新打断件 PR 审查口径一条。
- 【依据：§2.2 IR-G2/IR-G6；对标 §1.2 打断三声明/badge 生命周期行；§7.3-1「点开直达最小动作」的 app 内同构】

**N25（§10.5 台账新增行，随 v1.4 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N20 冷启动总预算+tab 零转场 | 未开工 | 改造 #6/#4 |
| N21 连接状态单一报告源 | 未开工 | 改造 #5 |
| N22 打断三档+静默窗+庆典单通道 | 未开工 | 改造 #3/#5 |
| N23 静默成功 ratchet（229 冻结） | 未开工 | 改造 #7 |
| N24 打断面生命周期三声明 | 未开工（登记即生效） | 改造 #1/#2 |
| IR-G12 离线冷启动登出定性 | **观察行**（活栈复测：飞行模式冷启动→观察是否落地登录页且 token 被清；与 V13-RETEST ④-1 社群域 401 同源排查） | 改造 #8 |
| IR-G6 半段：正在查看会话仍弹横幅 | 观察行（活栈确认触发语境） | 随改造 #2 |
| galaxy `GalaxyErrorSnackBar` 私有 owner 迁编 | 观察行（N16 续记，触碰即迁） | —— |
| §2.1.3 motion_token_v3 迁移（本轮复核仍未开工：sparkle_route_transition.dart:57-76 旧 7 值内联表仍为事实源，v3 文件不存在） | 台账续记（批 2 B2-1 既有行，本卡不重复立项） | B2-1 |

---

## 5. 改造清单（按北极星收益排序 top8，供后续卡池直接取用）

> 每条：文件/改什么/验收标准/预估工作量（S≤半天，M≈1 天，L≈2 天+）。排序依据：对「期末一周用户备考效果」的直接度 > 触达频次 > 成本。与前轮清单关系：本表为两新面的 v4 批次，前轮未清偿项不受影响。

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **badge 清除时机修复（N24 首案）** | community_provider.dart:1042/1828/1878 计数源不变；进入 /community（或会话可见即清）调用 reset；shell_navigation.dart:230/home_notification_card.dart:19 连带自动归零 | unread 计数补「进入即清」；防复发=provider 文件含清除调用断言测试 | 进入社群 tab 角标归零的 widget test；全库 grep decrement/reset 调用 ≥1 | S |
| 2 | **消息横幅深链（N24 三声明）** | message_notification_service.dart:96-99 onTap → navigatorKey push 会话路由（NotificationMessage 已携带 type/targetId，private/group/mention 三态映射） | 死链横幅→点达目标会话；dismiss 保留 | 三种 NotificationType 的路由断言测试；手测点横幅进会话 | S |
| 3 | **本地提醒静默窗钳制（N22 子句）** | task_notification_scheduler.dart:104-143 排程处加 23:00-8:00 钳制（窗内顺延至窗后；自设黎明截止例外开关默认关） | 三档提醒过静默窗钳制 | 单测：07:00 截止任务的 1440/60/15 三提醒落点全部 ≥08:00 | S |
| 4 | **chat tab 转场归一（N20 子句）** | routes.dart:321-338 chat 分支拆 pageBuilder：tab 路径 NoTransitionPage，深链冷入场保留 buildColdStartTransitionPage | tab 零转场语法唯一 | 手测 tab 切换即时；深链进 chat 仍有落地转场 | S |
| 5 | **通知分级门控（N22 主条）** | chat_notifier_actions.dart:776-800 事件入口单点 switch：high 直通现状；medium/low 仅 handleNewNotification（toast 分支跳过）；intervention/aurora_confirm 强制 high | 分级分流+保守白名单 | widget test：medium 事件不触发 toast 仅入中心；intervention 恒 toast | M |
| 6 | **冷启动一段式（N20 主条）** | splash_screen.dart:28-53 四段并一段 ≤400ms（D-3 执行）；app.dart `_ColdStartFade` 320ms 与落地转场二选一（叠段禁令）；遥测加表现层总时长口径；splash 期 auth 等待 >2s 出跳过/重试降级 | 遥测总时长 ≤600ms；弱网（getCurrentUser 挂起）2s 后可见降级面 | 遥测数字+弱网模拟手测 | M |
| 7 | **静默成功首批+顺手批（N23 首批 + IR-G11）** | task_quick_action_menu.dart:101-105/122-126 删 loading toast、success 改静默（onChanged 刷列表即反馈）；:111/:133 洗 text 改经 UserFacingError（N15 同批）；learning_dashboard_screen.dart:392-394、weekly_growth_narrative_card.dart:349 骨架化 | AppFeedback.success 计数 229→首降；守卫 ratchet 落地 | ratchet 跑绿；quick action 单动作 toast 数 0-1 | S-M |
| 8 | **离线冷启动会话保护（IR-G12，观察行转正后执行）** | auth_provider.dart:161-162/:167-168 catch 分型：网络类错误（DioException connection 类型）→保留 token+缓存用户+isAuthenticated=true+OfflineBanner 承接；仅 401/403 走 `_resetInvalidStoredSession`；前置：活栈复测定性+后端 refresh 语义核对（与 V13-RETEST ④-1 同源排查） | 飞行模式冷启动落在 home+离线横幅，token 与聊天缓存完好 | 红绿测试：连接错误不清 session、401 照清 | M |

**被砍项备忘**（防后续卡重复立项）：中屏面板级 spinner 专项（§4.4.2 条款已在，IR-G11 随改造 #7 顺手批执行）；转场时长双轨专项（=批 2 B2-1 既有行，本卡台账续记不重复立项，见 N25 末行）；SparkleBottomSheet 零使用专项（owner 在位、raw 17 处按 A-SPEC3 N17「触碰即迁」同制处理，无专项）；「正在看聊天仍弹横幅」UI 单侧修（观察行，先活栈定性触发语境再裁决，避免在 WS 事件流语境不清时误加门）。

---

## 6. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC4/REPORT.md`（本文件，位于 worktree wt242）；零产品代码改动（`mobile/lib`、`backend`、`scripts` 未动，全部引用为只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean 类树操作；未 commit / 未 push
- [x] /tmp 无驻留（全程未写 /tmp）；无启动进程/模拟器/浏览器，无 HEAVY 资源占用；worktree 内无 build/.dart_tool 产生
- [x] 引用代码均为 @7f855d70 实测（rg/read）；计数类结论（AppFeedback 625、success 229、skeleton 63、CircularProgressIndicator 47、dialog 62、sheet 17+1、MaterialPageRoute 4、unreadMessageCountProvider 9 引用点）均为 grep 实测；V13/V13-RETEST/V13-MAJORS 引用为报告编号实读；IR-G12 代码链实锤但行为未活栈复测已如实标注；无编造引用
- [x] 对标研究未做外部浏览（搜索配额 429），方法声明已按前三轮先例如实标注
