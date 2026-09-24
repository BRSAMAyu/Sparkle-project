# A-SPEC8A · 第八轮 A 面：会话连续性与状态恢复（用户离开再回来时的一切）对标研究 → 自审 → 辩论 → SPEC v1.8 增量提案

> 卡：**wt271-res-sesscont** ｜ 北极星全旅程战役 · A 纵队研究卡第八轮 A 面 ｜ 2026-09-22 ｜ worktree **wt271-res-sesscont**（base **b9a7da3d**）
> 性质：**纯研究卡，零产品代码改动**。全部代码引用只读走查（grep/read/sed），file:line 均为 @b9a7da3d 实测。
> 研究面定义（按卡）：用户离开再回来时的一切连续性——①进程被杀/重启后的 UI 状态恢复；②未发送草稿保留；③表单半成品保留；④导航栈恢复；⑤离线期间动作的排队与回放；⑥弱网下发送中的优雅降级。
> 前置读透：`v3/FLEET-BRIEF.md`（战役上下文）+ `v3-output/A-SPEC7/REPORT.md`（形制范本，本卡对齐它）。本提案不推翻 v1.0-v1.7 任何条款，编号接续 v1.7 的 N45（N46 起）。
> 对标研究方法声明：WebSearch 实测 429（Weekly Limit，reset 2026-09-24，与 A-SPEC7 轮同况）；**WebFetch 本轮可用**，已直取 6 份官方一手文档（Apple UIKit 状态恢复 / Apple SwiftUI SceneStorage / Android 官方保存 UI 状态指南 / Flutter 官方状态恢复 / go_router 官方 State restoration / Telegram 官方草稿 API + 官方博客），凡引用均摘原文；Notion 离线页、微信、银行类、Things/Reminders 无一手官方文档可取（help 页 404/JS 渲染），相应论断**明确标注为推断**。引用代码均为树内实测，无编造。

---

## 0. 方法与多轮过程记录

| 轮 | 动作 | 产出 | 关键发现 |
|---|---|---|---|
| R1 对标研究 | WebFetch 直取官方文档 6 份（Apple ×2、Android ×1、Flutter/go_router ×2、Telegram ×2）；5-8 个顶级软件逐面提取「离开再回来」的连续性做法 | §1 对标发现 top8 | 对标公约高度收敛：**「进程死亡对用户应不可见」（Apple 原文 illusion）**；**「正在输入的文本是一等公民状态」（Apple 用它做官方示例、Android 点名列出）**；**「用户主动丢弃才不恢复，系统杀死必须恢复」（Android 明示分界）**；Telegram 把「用户离开未发送」定义为必须落库的草稿对象 |
| R2 自审 | 六面全库走查：a) AppLifecycleState 全库 grep + 逐 handler 实读；b) 聊天草稿链（chat/private/community 三输入面）；c) unsaved_changes_guard 全量交叉比对（含输入屏 vs 挂 guard 屏双清单）；d) restoration 体系全库 grep（0 命中）+ routes.dart redirect 全读；e) 发送队列三链路实读（主 AI 聊天 Isar 队列 / 社区群聊 Hive 队列 / 任务域 SyncEngine outbox）+ 发送失败路径；f) 离线降级面（OfflineBanner / N34 读缓存 / 队列横幅） | §2 达标项清单 + 差距 7 条（带 file:line） | **最大反转：Sparkle 的离线队列基建已达对标水准**（主聊天 Isar 持久队列 + 断线重连回放 + 重试预算，Telegram 式），真正的大差距集中在另外两端：**草稿零持久化**（对标 Telegram 的核心面）与**进程死亡恢复零接入**（全库 0 个 restorationId，对标 Apple/Android/Flutter 三家官方体系） |
| R3 辩论 | 7 条逐条过三关（真差距？收益/成本/风险？北极星加权） | §3 辩论记录 | 主导裁决：离线排队面**不再加码**（已达标的不要过度施工）；火力集中在**草稿落库（M）+ 进程恢复务实版（M）+ 吞单诚实化（S）**三个高痛低险面 |
| R4 成文 | 过关差距 → v1.8 增量 N46-N50 + 台账 N51 + 改造 top8 | §4 / §5 / §6 | 全部为增量/执行令/存量靶登记，无推翻 |

**结构性结论先行（两条）**：
1. **「排队与回放」已是资产，「草稿与恢复」才是负债**：主 AI 聊天有完整的离线队列（消息先落 Isar 再上 socket、每次连接成功先 `_restorePendingFromDb` 再 flush、重试预算 5 次、上限 50 条诚实溢出），社区群聊/私聊有 Hive pending 队列（nonce 去重 + ack 删除 + 初始化重试），任务生命周期四操作有 SyncEngine outbox（dedupeKey 幂等 + 离线入队人话提示）——这一面不输 Telegram。但用户**正打着的字**（聊天输入框、转账金额、长表单）在离开页面或进程被杀的瞬间**全部蒸发**：草稿持久化全库 0 处，Flutter 状态恢复体系全库 0 接入。
2. **连续性的最后一公里是「回到原处」**：冷启动永远落 `/`→home（routes.dart:115 `initialLocation: '/'`），认证期深链还原机制（N20 pending redirect）只在「认证未决」窗口有效；正常离开再回来，用户永远被送回大厅而不是原来的位置。对标 Apple「maintain the illusion that your app is always running」——用户不知道进程死过，也就不该被送回起点。

---

## 1. 对标发现 top8（R1，含来源）

| # | 软件/指南 | 发现 | 来源性质 |
|---|---|---|---|
| F1 | **Telegram**（草稿） | 草稿是被同步的一等对象：「If the user quits the app before sending, the unsent message should be saved as a draft via `messages.saveDraft`」（客户端义务：离开未发送→存草稿）；「New drafts are automatically sent to all devices via `updateDraftMessage` updates」（跨设备近实时同步）；官方博客：「all your drafts are now synced across all your devices」「you can start typing on your phone, then continue on your computer – right where you left off」 | **一手官方**（core.telegram.org/api/drafts + telegram.org/blog/drafts） |
| F2 | **Apple UIKit State Restoration** | 「Preserving your app's user interface **helps maintain the illusion that your app is always running**.」「users don't know that your app has been terminated and won't expect the state of your app to change.」保存时机：系统择机写入加密文件，被杀后重启时重建。官方示例代码恢复的正是**正在编辑的文本框内容**（encodeRestorableState 里 encode `firstNameField?.text`）。边界：状态恢复不替代数据持久化（列表存 ID 不存数据） | **一手官方**（developer.apple.com/documentation/uikit/preserving-your-app-s-ui-across-launches） |
| F3 | **Apple SwiftUI SceneStorage** | 「You use `SceneStorage` when you need automatic state restoration of the value.」适用：user input、selected tab、scroll position；约束：轻量（模型数据禁入）、**敏感数据禁入**（「Do not use SceneStorage with sensitive data」）、系统不保证落盘时机 | **一手官方**（developer.apple.com/documentation/swiftui/scenestorage） |
| F4 | **Android 官方保存 UI 状态指南** | 恢复分界线：「用户主动丢弃（最近任务划掉/finish()）→ 用户默认永久离开，**不应**恢复；系统在后台杀进程 → 必须恢复，否则「pantalla vuelve inesperadamente a su estado inicial」（屏意外回到初始态）」。**文本输入被官方点名为 saved state 的标准用例**（「la entrada en los campos de texto」） | **一手官方**（developer.android.com/topic/libraries/architecture/saving-states） |
| F5 | **Android 三层分工（divide and conquer）** | 本地持久化=「一切不想丢的数据」；ViewModel=内存中的 UI 状态；saved state=「重启所需的最小数据（搜索词、ID、文本输入）」；复杂事务对象（如购物车）=本地持久化存对象、saved state 只存 ID。另：instance state 上限 1MB，超限 `TransactionTooLargeException` 崩溃 | **一手官方**（同上 + Flutter restore-state-android 页引述） |
| F6 | **Flutter / go_router 官方恢复体系** | `restorationScopeId` 挂 MaterialApp 即自动注入 RootRestorationScope；TextField/ScrollView 内建 `restorationId` 即恢复输入与滚动位；自定义状态走 RestorationMixin+RestorableProperty；导航栈恢复用 restorablePush；go_router「fully supports state restoration」，ShellRoute/StatefulShellRoute **必须**在 pageBuilder 里给 Page 带 restorationId 才生效 | **一手官方**（docs.flutter.dev/platform-integration/android/restore-state-android + pub.dev go_router State restoration topic） |
| F7 | **Notion**（离线编辑缓冲） | 离线编辑在本地缓冲、重连自动同步、冲突可解——「离开再回来，编辑成果都在」。 | **推断**（公开常识+UX 判断；官方 help 页本轮抓取失败 404/JS 渲染，未取得一手原文） |
| F8 | **微信 / 银行类 App / Things·Reminders** | 微信：未发送草稿以「草稿」标签常驻会话列表，跨会话跨重启保留；银行类：转账/开户长表单半成品保留+放弃需确认（输入是劳动，金额尤其敏感）；Things/Reminders：重启回到原列表原位置。 | **推断**（公开常识；三家均无公开官方技术文档可引） |

**面性公约提炼（四条）**：
- **公约①（幻觉连续性）**：进程被系统杀死再回来，用户应感觉 App 一直在跑——位置、输入、滚动都在（Apple F2 措辞为正典）。
- **公约②（输入是一等状态）**：用户正在输入的文本是必须被保存的状态，且「用户主动丢弃」与「系统杀死」分界处理（F4）。
- **公约③（离开即存草稿）**：用户带着未发送内容离开（切页/杀进程），客户端有义务落库（F1 Telegram 把这写成 API 层义务）。
- **公约④（恢复要轻）**：恢复通道存 ID/短文本，不存大对象；敏感数据（金额可、密钥不可）分级（F3/F5）。

---

## 2. 自审（R2，全部 @b9a7da3d 实测）

### 2.0 先说达标项（诚实记录——离线排队面是本轮最大好消息，不许后续卡重复施工）

- **主 AI 聊天离线队列是完整的 Telegram 式实现**：发送路径先持久化后上网（websocket_chat_service_v2.dart:1523-1526 `if (isConnected) { _persistOutgoingMessage(payload); _sendMessage(payload); }`）；断线时入内存队列并同步落 Isar（:1963-1995 `_enqueuePendingMessage` + `_persistOutgoingMessage`）；上限 50 条（:1452），溢出删最旧并向用户广播 `PENDING_QUEUE_OVERFLOW` 不可重试错误（:1966-1981，诚实降级）；每次连接成功先从 Isar 恢复再回放（:1786-1795 `_restorePendingFromDb().then((_) => _flushPendingMessages())`）；状态机 pending/sent/failed/acked 四态（offline_chat_message.dart），**重试预算 5 次**（offline_chat_message.dart:132 `canRetry => status == failed && retryCount < 5`）；acked 24h 清理（offline_message_queue_service.dart:181-192）。由 R3 审计 finding O-01 与 A-2（extraContext JSON 化修复，:1986-1988 注释自证）迭代而来，血缘清晰。
- **投递状态全程可见**：气泡四态徽章 queued（时钟）/sending（spinner）/failed（错误+重试钮）（chat_bubble.dart:2640-2672）；重试钮接线 chat_screen.dart:1723-1727（重发原文）；队列横幅状态机 N-1/N-3 纯函数可单测（offline_providers.dart:100-139，注释自证 N-3 修「失败项与正在发送并存」矛盾），横幅组件 offline_queue_indicator.dart 挂 chat_screen（A-5/N-6 键盘压缩态都在）。
- **社区群聊/私聊有第二套 Hive pending 队列**：nonce 去重集合 + ack 删队 + 初始化时重试（community_provider.dart:887-889 `_pendingNonces`、:921 初始化重试、:961-969 ack 移除、:1274-1310 `_retryPendingGroupMessages`）；私聊同构（:2068-2100 失败入 `enqueuePendingPrivateMessage` + 气泡标 `hasError:true`）。
- **任务生命周期离线 outbox**：start/pause/resume/complete 四操作全入 SyncEngine（task_offline_queue.dart:19-65），dedupeKey 幂等（`task:$taskId:start` 式），服务端 409=已达标=成功（:9-12 注释自证）；入队向用户抛 `OfflineEnqueuedException`（task_repository.dart:35-42），词典落「已保存，恢复网络后自动同步」人话——**离线写的诚实降级范式**；指示器挂 task_list/task_execution 两屏。
- **读缓存（A-SPEC6 N34 在位）**：CacheAwareResult 带 fromCache+asOf 时点戳（list_read_cache.dart:12-17），只缓存真实 API 响应、demo 数据永不入库（:27-35 注释自证 B-02 口径），消费方 task/error_book/community 三域（含 feed_tab_content 等 UI 挂「截至 X」）。
- **全局离线横幅**：OfflineBanner 监听 isOnlineProvider（offline_banner.dart:12-16），挂 app.dart:116——离线时全 app 有一致的非侵入提示。
- **连接生命周期有管家**：paused/hidden/detached→断开并清内存队列（websocket_chat_service_v2.dart:2829-2840）；resumed→重连（:2841-2848），重连即触发上述 DB 恢复+回放。心跳超时（:2558-2570）与 terminal fallback 看门狗（:1879-1887）兜底假连接。
- **会话级深链还原存在**：认证未决期到达的深链经 splash redirect 参数中转还原（routes.dart:170-186 N20 注释自证「还原深链」）；未登录深链带 return_to 登录后还原（routes.dart:189-199）。认证态跨重启持久（auth_repository.dart:675+ token 缓存/存储），splash 品牌窗后自动放行 home。
- **计时器类对后台往返有防御**：focus_timer_tool.dart:316 / timer_widget.dart:131 / mindfulness_mode_screen.dart:163 / breathing_tool.dart:220 均在 resumed 时重算——专注场景的连续性有基本盘。
- **私聊有「代写草稿反悔通道」**：AI 代写草稿提升进输入框时可一键还原原文（private_chat_screen.dart:337-385 `_restoreOriginalDraft` / `_promoteAgentDraftToComposer`）——会话内的草稿交互是及格的，缺的是跨会话持久（见 SC-G1）。

### 2.1 六面差距清单（7 条，按用户痛感排序）

| # | 差距 | 证据（file:line @b9a7da3d） | 对标冲突 |
|---|---|---|---|
| SC-G1 | **聊天输入草稿零持久化**：主聊天 `_draftController` 是纯内存 TextEditingController，dispose 即蒸发（chat_screen.dart:188 声明、:1072 dispose，全文件无任何持久化调用）；私聊 `_composerController` 同构（private_chat_screen.dart:41 声明、:61 dispose）。用户打了一段话→切去查个单词/进程被杀→回到聊天，字全没了。全库 grep `saveDraft/draftKey/prefs.set*draft` 0 命中（唯一 draft 概念是 AI 代写草稿与任务草稿路由，chat_notifier_actions.dart:242） | 同列；群聊输入 community_chat_input.dart:68 `_voiceDraftText` 亦为 widget 内态 | 公约③（F1：Telegram 把「离开未发送→存草稿」写成客户端义务）；「输入是劳动」（A-SPEC5 N27 的同源精神，但 N27 只管返回确认，不管保存） |
| SC-G2 | **进程死亡恢复体系全库零接入**：`restorationId/RestorationMixin/restorablePush/restorationScopeId/RestorableText` 全库 grep **0 命中**；MaterialApp.router 无 restorationScopeId（app.dart:80-86）；GoRouter 无 restorationScopeId（routes.dart:114-115 `initialLocation: '/'`）。冷启动永远 splash→home，用户离开时的 tab、页面、滚动位置全部不还原——进程被杀与「被送回大厅」对用户等价 | 同列 | 公约①（F2：illusion that your app is always running）；F4（系统杀死必须恢复）；F6（官方体系现成，go_router 明示支持） |
| SC-G3 | **表单自动暂存为零 + guard 覆盖缺口 54 屏**：UnsavedChangesGuard（core/widgets/unsaved_changes_guard.dart，N27）已挂 8 个创建/向导屏，但全库含文本输入的 screen 共 **54** 个未挂，其中含 TextFormField 的**真表单 10 个**：register/login/forgot_password/reset_password/password_reset、photon_transfer（**光子转账屏无 PopScope 无 guard**，金额输入 :28/:172，误触返回即蒸发）、guest_upgrade（访客升级表单）、post_exam_review（考后复盘长文）、schedule_preferences、seed_library_detail。guard 之外**没有任何自动暂存**：guard 只挡「返回」这一种丢失路径，杀进程/切后台被杀/崩溃三种路径完全不设防，且全库 `autoSave/_saveDraft/restoreForm` 0 命中 | 同列；V13 D-02（注册表单返回丢）已登记但仅覆盖 auth 两屏 | 公约②③（F4 文本输入点名；F5 转账类事务对象该本地持久化）；银行类表单保全（推断 F8） |
| SC-G4 | **AI 代写私信发送失败被吞单伪装成功**：`_persistPrivateAgentMessage` 的 `catch (_)` 直接**返回伪造的 PrivateMessageInfo**（community_agent_provider.dart:665-680：假 `Uuid().v4()`、`isRead: true`）——私信根本没发出去（HTTP POST community_repository.dart:766-779 失败），UI 却呈现一条已读消息；该消息只存在于内存 provider state，**重启即凭空消失**，无失败提示、无重试、无恢复 | 同列 | 违反舰队诚实性红线（FLEET-BRIEF §四.4「不造默认值」的写路径同源）；对照同文件群聊侧有完整 pending 队列（community_provider.dart:2068-2100）——**同一 App 内双标** |
| SC-G5 | **重连反馈是一次性 snackbar，流式中断无「未完成」态**：重连中/成功/失败只各弹一次 AppFeedback（chat_screen.dart:306-337），转瞬即逝；弱网下正在流式输出的回复若中断，terminal fallback 只兜「必须出现终态」（websocket_chat_service_v2.dart:1879-1887），半截回复没有「未完成·可重新生成」的显式标记；75s 看门狗仅 modeling 访谈有（modeling_chat_screen.dart:48-50，A-SPEC7 已录），主聊天流式中断的降级形态没有对等物 | chat_screen.dart:306-337；:1879-1887 | F7（Notion 式：回来的东西要完整可用，半截要有交代——推断）；弱网优雅降级（卡面第⑥子面） |
| SC-G6 | **离线读缓存只覆盖三读域**：N34 缓存消费方=task/error_book/community（list_read_cache.dart 全部 put 调用点核实）；galaxy 星图、insights 洞察、plan 计划详情、统计屏离线时无缓存兜底，直接错误态——「地铁里看不了星图」 | list_read_cache.dart 消费面 grep 核实 | F7（Notion：读也应该离线可用——推断）；北极星「期末一周随时随地」 |
| SC-G7 | **群聊 pending 重试失败静默**：`_retryPendingGroupMessages` 的 catch 只 `debugPrint`（community_provider.dart:1308-1309），消息留在 Hive box 下次再试（不丢数据），但用户无任何失败感知——气泡停在发送态多久、何时放弃，无 UI 语义 | 同列 | 公约②（失败必须可见：主聊天的 failed 徽章+重试钮是正解，群聊缺同一待遇） |

---

## 3. 红蓝辩论记录（R3）

> 三关：**G1 真差距还是风格偏好？G2 收益/成本/风险？G3 北极星（期末一周备考效果）加权值不值？**
> 红方=主张改造；蓝方=主张维持/砍。裁决：**采纳 / 改写采纳 / 砍 / 转台账**。

| # | 红方主张 | 蓝方反驳 | 三关裁决 | 结论 |
|---|---|---|---|---|
| SC-G1 | 聊天草稿落库：三个聊天输入面按 conversationId 萘 Hive/Isar 草稿，debounce 写、发送/清空删 | 蓝方：输入框文字是瞬态，Telegram 同步草稿是跨设备重基建，值不当 | G1 真差距（0 持久化实锤+对标 F1 客户端义务原文）；蓝方后半成立：**跨设备同步不做**，改写为**单机草稿**（公约④轻量恢复）；G2 成本 M（一处草稿仓 + 三输入面接线，无后端改动）；G3 高——备考用户的提问草稿常是整段疑问/错题描述，蒸发一次痛感极强 | **改写采纳**（N46 主条：单机草稿，禁扩为跨设备同步） |
| SC-G2 | 全量接入 Flutter restoration 体系（restorationScopeId + 全路由 restorationId） | 蓝方：全量 restoration 是大工程，Android 1MB 上限悬顶，go_router ShellRoute 每条都要 pageBuilder 带 restorationId，回归面巨大 | G1 真差距（0 接入实锤）；蓝方成本论**部分成立**——全量接入 L 且回归风险真实；改写为**务实两步**：第一步「最后位置恢复」（记录 last meaningful route+参数，冷启动认证通过且无 pending redirect 时还原，白名单排除支付/计时中态，S-M 成本拿到 80% 收益）；第二步 restorationId 白名单试点（仅主聊天输入框+tab index，对标 SceneStorage 最小用法）登记观察；G3 高——「回来还在原地」是连续性的定义本身 | **改写采纳**（N47 主条：last-route 恢复制；N47 子句：restorationId 试点白名单登记） |
| SC-G3 | 高价值表单自动暂存+补 guard 缺口 | 蓝方：54 屏全挂 guard 是审美洁癖；搜索框也要 guard 是灾难 | G1 真差距（10 真表单实锤，photon_transfer 转账屏无防护最尖锐）；蓝方对「54 屏」的反驳成立——搜索/筛选框豁免；改写为**两档**：①guard 补口令只辖 10 个 TextFormField 真表单（其中 auth 三屏 V13 D-02 既辖只登记不双立项，实际新施工 7 屏）；②自动暂存**先做 photon_transfer+guest_upgrade+post_exam_review 三案**（金额、转化、长文三痛源），其余表单登记制只降；G3 高——光子是付费资产，转账表单蒸发直接伤付费信任 | **改写采纳**（N48 主条：guard 真表单补口+三案暂存；搜索框豁免明文） |
| SC-G4 | 吞单诚实化：代写私信失败必须走 pending 队列或失败气泡 | 蓝方：catch 返回本地消息是「优雅降级」，用户至少看到回复不白等 | G1 真差距+红线违反（假 UUID+isRead:true 实锤；重启即消失实锤）；蓝方「优雅」论被击穿：**伪造成功比失败更伤**——用户以为 AI 回了，重启后话凭空消失，信任损伤最大；修复成本 S（复用同 App 内现成的 enqueuePendingPrivateMessage 通道，community_provider.dart:2093 现成范式）；G3 高——诚实性是产品红线不是审美 | **采纳**（N49 主条：禁伪造投递成功态） |
| SC-G5 | 重连横幅常驻化+半截回复「未完成」标记 | 蓝方：snackbar 一次性提示是移动惯例；流式中断罕见 | G1 半差距（罕见≠无待遇：弱网备考场景真实存在——宿舍 WiFi 切流量）；蓝方部分成立：重连成功已有自动 reload 历史（chat_screen.dart:316-329）；改写为**横幅常驻复用现成组件**（OfflineQueueIndicator queued 态已有，把 wsConnectionState!=connected 时也点亮即可，S 级）；「未完成」标记与重新生成按钮 S-M；G3 中 | **改写采纳**（N50：复用横幅；半截回复标记制） |
| SC-G6 | 读缓存扩容 galaxy/plan/insights | 蓝方：三读域覆盖了高频面；星图离线是伪需求 | G1 半差距（真但频次存疑——星图是成就型低频面，地铁场景集中在读任务/错题，已覆盖）；G2 改写：**登记制**——N34 消费域清单登记基线，新域按需扩容不专项清洗；G3 低-中 | **改写采纳**（N50 子句：读缓存域登记基线，随需求扩容） |
| SC-G7 | 群聊重试失败补 failed 徽章 | 蓝方：数据不丢（box 里留着），静默重试可接受 | G1 真差距（静默实锤）；但数据保全成立、主聊天已有正解范式可抄（chat_bubble 四态徽章）；成本 S-M；G3 中 | **采纳**（N49 子句：投递态徽章全域统一令——群聊/私聊对齐主聊天四态待遇） |

**辩论统计**：7 条 → 采纳 2（SC-G4/SC-G7）+ 改写采纳 5（SC-G1/2/3/5/6）+ 砍 0 + 转台账 1 类（auth 三屏 guard 归 V13 D-02，SC-G3 内登记）。本轮砍单为 0：R2 已按 file:line 过滤；辩论重心在**防过度施工**——离线排队基建已达标（§2.0），三处改写（跨设备草稿、全量 restoration、54 屏 guard）都是把红方的大工程压成高收益小切口。

---

## 4. SPEC v1.8 增量条目（提案，待主会话采纳）

> 形制对齐 v1.0-v1.7：编号 + 依据 + 可验收数字；不推翻任何既有条款。编号接续 v1.7 的 N45。生效方式建议沿用两段门禁先例（文本即生效 / 守卫绑合入时点）。

**N46（§7 增补）· 单机草稿持久化令（离开即存）**
- 三个聊天输入面（主聊天 chat_screen / 私聊 private_chat_screen / 群聊 community_chat_input）composer 文本必须按 `userId+conversationId` 键持久化到本地（Hive/Isar 既有仓），**debounce ≤500ms 写入**，发送成功或用户清空时删除；重进会话/冷启动恢复草稿并恢复光标位。
- **边界（防过度施工）**：仅单机；跨设备草稿同步（Telegram F1 全量形态）不做、登记观察行；语音草稿（`_voiceDraftText`）随本条同待遇。
- 【依据：§2.1 SC-G1（chat_screen.dart:188/:1072、private_chat_screen.dart:41/:61）；§1 F1；公约③】

**N47（§7 增补）· 冷启动最后位置恢复（务实务）+ restoration 试点登记**
- **最后位置恢复**：记录 last meaningful route（path+query，写本地）；冷启动认证通过且无 pending redirect、无强制引导拦截时还原之。**白名单排除**：支付/转账中间态、计时进行中态、一次性流程（onboarding/modeling）——这些态恢复即事故，落 home 是对的。
- **restorationId 试点白名单（登记制）**：主聊天输入框 TextField + 底部 tab index 两处接入 Flutter 内建 restoration（对标 SceneStorage 最小用法，F3/F6），验收进程死亡后输入框文字与所在 tab 恢复；全量 restoration 体系**不做**（Android 1MB 上限+ShellRoute 全量 pageBuilder 回归面，辩论定论），登记观察行待 Flutter/go_router 生态成熟复核。
- 【依据：§2.1 SC-G2（app.dart:80-86、routes.dart:114-115、全库 restoration grep 0）；§1 F2/F3/F4/F6；公约①】

**N48（§7 增补）· 表单保全双档令（guard 补口 + 三案暂存）**
- **guard 真表单补口**：含 TextFormField 的表单屏必须挂 UnsavedChangesGuard（N27 既辖）；存量缺口 **10 屏**登记只降（register/login/password 三 auth 屏 V13 D-02 既辖不双立项，实际新施工 7 屏：photon_transfer / guest_upgrade / post_exam_review / schedule_preferences / seed_library_detail / forgot_password / reset_password）。**搜索/筛选输入明文豁免**。
- **自动暂存三案**：photon_transfer（金额+备注）、guest_upgrade（升级表单）、post_exam_review（复盘长文）三屏增加本地草稿暂存（键=userId+screenId，提交成功删），guard 之外补上「杀进程不丢」这条路径。
- 【依据：§2.1 SC-G3（54/10 计数、photon_transfer_screen.dart:28/:172、全库 autosave grep 0）；§1 F4/F5；公约②】

**N49（§7 增补）· 投递诚实令（禁伪造成功 + 徽章全域统一）**
- **禁伪造投递成功态**：一切发送路径失败必须呈现失败语义（入 pending 队列或失败气泡+重试），**禁止**以本地构造消息冒充服务端已收（存量靶：community_agent_provider.dart:665-680 假 Uuid+isRead:true，改造 #2 首案）；此条为舰队诚实性红线（FLEET-BRIEF §四.4）在投递链的落地面。
- **投递态徽章全域统一**：群聊/私聊消息对齐主聊天四态徽章（queued/sending/failed+重试，chat_bubble.dart:2640-2672 为正解组件）；群聊初始化重试失败禁止静默 debugPrint（community_provider.dart:1308-1309 存量靶）。
- 【依据：§2.1 SC-G4/SC-G7；§1 F1（Telegram ack 语义）；公约②】

**N50（§7 增补）· 弱网降级与读缓存域登记**
- **重连横幅常驻化**：`wsConnectionState != connected` 且存在未投递消息时点亮 OfflineQueueIndicator queued 态（组件与状态机均现成，offline_providers.dart:100-139），替代一次性 snackbar 作为唯一弱网告知面（snackbar 可并存）。
- **半截回复标记制**：流式中断产生的未完成回复必须有「未完成」视觉态+一键重新生成；75s 看门狗范式（modeling_chat_screen.dart:48-50）为主聊天的参照物。
- **读缓存域登记基线**：N34 消费域现值=task/error_book/community 三域，登记为基线；galaxy/plan/insights 扩容按需立项，不专项清洗。
- 【依据：§2.1 SC-G5/SC-G6；§1 F5（轻量恢复）；辩论 SC-G5/SC-G6 改写结论】

**N51（§10.5 台账新增行，随 v1.8 合入登记）**

| 条目 | 状态 | 剩余量 |
|---|---|---|
| N46 单机草稿持久化（三输入面） | 未开工 | 改造 #1 |
| N47 冷启动最后位置恢复+restoration 试点（白名单制） | 未开工 | 改造 #5/#8 |
| N48 guard 真表单补口（存量 10 登记）+自动暂存三案 | 未开工 | 改造 #3/#4 |
| N49 投递诚实令（吞单靶 community_agent_provider.dart:665-680）+徽章全域统一 | 未开工 | 改造 #2/#6 |
| N50 重连横幅常驻+半截回复标记+读缓存域基线（现值 3 域） | 未开工 | 改造 #6/#7 |
| 跨设备草稿同步（Telegram 全量形态） | 观察行（不做，生态成熟再议） | —— |
| 全量 Flutter restoration 接入 | 观察行（last-route 务实务先行） | —— |
| auth 三屏 guard（register/login/password） | 台账登记（V13 D-02 既辖，防双立项） | —— |

---

## 5. 改造清单（按北极星收益排序 top8，供后续卡池直接取用）

> 每条：文件/改什么/验收/量（S≤半天，M≈1 天，L≈2 天+）。排序：对「期末一周用户备考效果」直接度 > 触达频次 > 成本。**离线队列基建（主聊天/群聊/任务 outbox）不在清单内——已达标的不过度施工（§2.0/§3 定论）。**

| # | 改造 | 文件与落点 | 改什么 | 验收 | 量 |
|---|---|---|---|---|---|
| 1 | **聊天草稿持久化（N46 首案）** | chat_screen.dart `_draftController`（:188）、private_chat_screen.dart `_composerController`（:41）、community_chat_input.dart composer；新草稿仓挂 ChatCacheService 或 OfflineMessageQueueService 同层 | 按 userId+conversationId 萘 Hive 草稿，debounce 500ms，发送/清空删，重进恢复+光标复位 | 杀进程重开草稿在；发送后草稿清；widget test 三面各一 | M |
| 2 | **代写私信吞单诚实化（N49 首案）** | community_agent_provider.dart:665-680：catch 分支改走 `enqueuePendingPrivateMessage`（community_provider.dart:2093 现成通道）或气泡 failed 态 | 失败不再伪造 isRead 消息；恢复网络自动重发或用户手动重试 | 断网触发代写→失败语义可见；重启后消息不凭空消失（在队列或有失败标记） | S |
| 3 | **光子转账屏 guard+暂存（N48 首案）** | photon_transfer_screen.dart（:28/:172 金额输入）：挂 UnsavedChangesGuard（isDirty=金额非空）+金额/备注草稿暂存 | 转账半成品误返回有确认；杀进程回来金额还在 | widget test：isDirty 返回拦截+草稿恢复断言 | S |
| 4 | **guest_upgrade/post_exam_review 暂存 + 7 屏 guard 补口（N48）** | guest_upgrade_screen、post_exam_review_screen 暂存；schedule_preferences/seed_library_detail/forgot_password/reset_password/其余 1 屏挂 guard（auth 已辖 3 屏除外） | 长文与转化表单杀进程不丢；返回有确认 | guard 存量计数 10→3 只降；暂存恢复 widget test | M |
| 5 | **冷启动最后位置恢复（N47 首案）** | routes.dart redirect 链（:115 initialLocation 后、认证分支内）：新增 last-route 存取（写点=路由监听 debounce）；白名单排除支付/计时/onboarding 态 | 正常离开再回来落在原页面；深链/引导/支付场景行为不变（不还原） | 手测矩阵：冷启动还原/引导优先级/支付态落 home；redirect 单测 | M |
| 6 | **群聊/私聊投递徽章统一（N49）** | community_provider.dart 群聊/私聊消息模型补投递态字段；UI 抄 chat_bubble.dart:2640-2672 四态徽章；:1308-1309 静默 catch 补失败态 | 群聊重试失败可见、可手动重试 | 断网发群消息→failed 徽章+重试钮可见 | S-M |
| 7 | **重连横幅常驻+半截回复标记（N50）** | chat_screen.dart:306-337：wsConnectionState!=connected 时点亮 OfflineQueueIndicator；流式中断回复加「未完成」标记+重新生成钮 | 弱网状态常驻可见；半截回复有交代 | 弱网模拟（proxy 断流）走查：横幅常驻、标记渲染、重新生成可用 | S-M |
| 8 | **restorationId 试点（N47 子句）** | 主聊天 TextField 加 restorationId + MaterialApp.router/G作Router 加 restorationScopeId（最小两点）；tab index 随试点登记 | 进程死亡后输入框文字与 tab 恢复 | Android `don't keep activities` 实测恢复；登记观察行复核点 | S |

**被砍/豁免备忘（防重复立项）**：跨设备草稿同步（Telegram 全量形态）与全量 restoration 接入为**观察行**不做（N51 登记）；搜索/筛选输入**明文豁免** guard 与暂存（N48）；离线队列基建**不在施工面**（§2.0 达标项，任何「重做队列」类卡都是重复立项）；auth 三屏 guard 归 V13 D-02 线（N48 登记不施工）。

---

## 6. 下轮辩论议题清单

1. **恢复体系路线裁决**：last-route 务实务（N47 首案）跑通后，是否值得升级为全量 Flutter restoration？需数据：last-route 方案上线后「回到原处」任务完成率的残差；Flutter restoration 在 go_router StatefulShellRoute 下的回归成本实测。
2. **草稿要不要上云**：单机草稿（N46）落地后，跨设备草稿同步（Telegram F1 全量形态）对 Sparkle 的多设备用户占比是否值得后端建 draft 存储（proto 契约+网关透传）。
3. **离线写扩容边界**：任务四操作已在 outbox；错题本添加、计划创建是否入队（「地铁里录错题」是真场景吗）——需要 V13 类真人实测数据支撑，不建议拍脑袋扩。
4. **队列溢出策略的人话**：主聊天 50 条上限溢出删最旧并报错（websocket_chat_service_v2.dart:1966-1981）——删除用户排队的提问是否应该改为「禁止新增+提示清理」而不是静默删旧？痛感/实现两问。
5. **弱网流式的终极形态**：半截回复「未完成」标记之外，是否值得做断点续传（gateway/orchestrator 侧 seq 续流）——跨队协作卡（需要 C 线共同裁决，移动端单方无法闭环）。
6. **光子转账的银行级保全**：N48 三案暂存之上，转账确认是否需要金额二次确认弹窗/指纹（对标银行类 F8 推断）——涉 D 线商业化信任设计，建议 D-COMM 线合议。

---

## 7. 收工核查

- [x] 交付物仅 `v3-output/A-SPEC8A-SESSION-CONT/REPORT.md`（本文件，位于 worktree wt271-res-sesscont）；零产品代码改动（mobile/lib、backend、scripts 全程只读走查）
- [x] 主仓与其它 worktree 只读未动；无 stash/reset/clean/push；报告在 worktree 内本地 commit（不 push）
- [x] LIGHT 卡：未跑任何构建/测试/模拟器/浏览器；worktree 内无 build/.dart_tool 产生；/tmp 无驻留（全程未写）
- [x] 引用代码均为 @b9a7da3d 实测（grep/read/sed/awk 行号核实）；关键实测计数：restoration 体系全库 0 命中、草稿持久化 0 命中、autosave 0 命中、含输入屏未挂 guard 54 个（其中 TextFormField 真表单 10 个，逐文件列表在 §2.1 SC-G3）、任务 outbox 四操作（task_offline_queue.dart:19-65）、重试预算 5（offline_chat_message.dart:132）、队列上限 50（websocket_chat_service_v2.dart:1452）；无编造引用
- [x] 对标来源分级如实标注：一手官方 6 份（Apple UIKit 状态恢复 / Apple SceneStorage / Android saving-states / Flutter restore-state-android / go_router State restoration topic / Telegram core.telegram.org/api/drafts + telegram.org/blog/drafts——前五均为原文摘引，Telegram 为 API 文档+官方博客双源）；推断 4 处（Notion 离线缓冲、微信草稿标签、银行类表单保全、Things/Reminders 位置恢复），均在 §1 表内逐条标明；WebSearch 全程 429（reset 2026-09-24）已如实声明
