# V4-U07 · diff_or_evidence_only

**一句话设计**：在既有 chat 流式栈上落四个可失败增量——快慢反馈语义接 I09（消费帧 metadata 的 `chat_lane`/`deterministic_lane_kind`：快路模板应答带「即时回复·形态」诚实标记、快路轮不进检索→思考→生成三段假进度胶囊）、滚动主权锚（上滑阅读后到达性滚动不再自动拉回，仅发送等显式用户动作恢复跟随）、引用诚实差量举证（真来源可点真实导航；未知引用保持禁用态不造超链接）、200% 长中文/代码/公式不横向破屏差量举证——零新权威、零后端改动、零契约变更。

## 性质判定：implementation（移动端 chat 呈现面最小增量；锁 ui-chat）

基线 commit `e50107fe`（开卡时 main）；分支 `agent/v4/u07`（worktree wtU07，未 push）。

## 差量明细（产品码 7 文件 +252/-7 行，全部 additive 或门内扩展；一审 C-1 勘误：原记 6 文件 +201 系聚合口径不精确，numstat 实测为准）

| 文件 | 变更 | 内容 |
|---|---|---|
| `mobile/lib/features/chat/data/models/chat_message_model.dart` | 新 +44 | `ChatLaneValues`（I09 词表移动端消费门：封闭集 `{deterministic, model}`，集合外/缺键→null=既有行为）+ 消息级判据 `chatLane`/`deterministicLaneKind`/`isDeterministicLaneReply`（读终帧 rawMetadata，不生产 lane 值） |
| `mobile/lib/features/chat/presentation/providers/chat_state.dart` | 新 +27 | `chatLane`/`deterministicLaneKind` 字段 + `copyWith(clearChatLane:)` + `isDeterministicLane` + `shouldShowPhaseCapsule`（S18 胶囊门收进状态：快路轮不进三段胶囊） |
| `mobile/lib/features/chat/presentation/providers/chat_provider.dart` | 新 +25 | `_captureChatLaneFromMetadata`：StatusUpdateEvent/TextEvent/FullTextEvent 三帧捕获点（同轮后到覆盖先到）；`_beginRun`/`finalizeRun`/`_invalidateActiveStreamState` 清轮级标记；终帧消息 rawMetadata 经既有 `accumulatedRawMetadata` 零改动收口 |
| `mobile/lib/features/chat/presentation/providers/chat_scroll_anchor.dart` | 新文件 | `ChatScrollAnchor`：reversed 列表滚动主权锚（纯阈值判定：pixels ≤ 240 = 贴底跟随；离开即解除；`forceFollow` 供显式用户动作） |
| `mobile/lib/features/chat/presentation/screens/chat_screen.dart` | 改 +44/-12 | `_scrollToBottom({force})` 门（到达性滚动仅跟随态执行）；`_handleScroll` 每帧更新锚；messages 监听区分「用户消息追加=显式动作 force」vs「助手消息/组件到达=到达性」；回横幅继续/定位回退=force；两处胶囊分支改用 `chatState.shouldShowPhaseCapsule` |
| `mobile/lib/features/chat/presentation/widgets/assistant_lane_marker.dart` | 新文件 | 「即时回复」诚实标记（icon+caption；形态词只在 I09 冻结词表内翻译 greeting/acknowledgment/farewell，未知 kind 不臆造标签） |
| `mobile/lib/features/chat/presentation/widgets/chat_bubble.dart` | 改 +12 | 中断标记同款位形挂载 `AssistantLaneMarker`（判据=`isDeterministicLaneReply`，只读 metadata 事实） |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + gen×3 | 新 +4×2/+48 | `chatInstantReply`/`chatLaneKindGreeting`/`chatLaneKindAcknowledgment`/`chatLaneKindFarewell`（arb 改动 + `flutter gen-l10n` 再生，非手改 gen） |

l10n 再生判例遵循 F06 wt729 同款（arb+gen×3 同步再生成）。

## 卡验收逐条对照（每面一正一反，全部可失败）

### 1. 200% 长中文/代码/公式不横向破屏 —— 差量举证（既有栈已满足，测试钉死）

- **正**：`sparkle_markdown_200_scale_test.dart` 四例（长中文无空格段落/长 Python 代码块/长公式含 LaTeX 源文与无空格长 token/表格+列表混排）在 `TextScaler.linear(2.0)` × 360 逻辑宽下 `takeException()` 为 null；更紧约束面（气泡真实内容宽 288 = min(屏宽×0.8,内容列×0.9)−内边距）长 SQL/长公式同样零溢出。
- **反（对照/判别力）**：同款断言下必然溢出的无约束 Row 被抓到（`isNotNull`）——证明「isNull」断言有牙。
- **溢出消化路径在场断言**：代码块内部横向 `SingleChildScrollView` 在场（代码保真不折行、容器不破）。
- 实现事实：正文走 Flutter 逐字换行；代码卡自带横向滚动（`sparkle_markdown.dart` 既有）；本卡未改 sparkle_markdown（无需改——红了才会改）。

### 2. reference 点击真来源，未知引用不造超链接 —— 差量举证（既有链路已满足，测试钉死）

- **正**：`assistant_citation_honesty_test.dart` 例1：引用带可解析深链（`/tasks/task-123`）→ chip 打开定位 sheet（摘录/章节定位在场）→「前往文档」可点（`onPressed != null`）→ 真实导航到 `TASK-DETAIL:task-123`（GoRouter 真路由）。
- **反**：例2 外部 url-only 引用（`DeepLinkService.resolveRoute` 不可解析）→「前往文档」禁用（`onPressed == null`），摘录仍如实展示（不装死不造链接）；例3 无目标引用与伪造 `sparkle://not-a-real-type/xyz` → 同样禁用。
- 实现事实：`AssistantCitationStrip` 既有 `navigationTarget→resolveRoute→null=禁用` 链路即本验收的诚实语义；本卡零改动、以可失败测试冻结（防回归）。

### 3. 首个有用内容与 ack 区分，慢任务不循环假思考 —— 本卡新行为（接 I09 快慢路）

- **正（provider 级）**：`chat_notifier_lane_capture_test.dart` 例1：快路轮状态帧（I09 WT373 拆帧契约：status 携带 lane 标记先行）→ `state.chatLane=deterministic` + 等待期 `shouldShowPhaseCapsule=false`（不展示检索/思考假阶段）；模板 delta 到达后终帧消息 `isDeterministicLaneReply=true` + 形态词收口；run 终态轮级标记清零。
- **正（呈现层）**：`assistant_lane_marker_test.dart`：已知形态「即时回复 · 问候/应答/告别」如实呈现。
- **反（provider 级）**：例2 集合外 lane 值（`warp_speed`）不捕获、等待面保持既有三段胶囊（旧后端零变化）；终帧 `chat_lane=model` 不误标即时回复。例3 全程无键 → 零 lane 标记（I09 开关关闭=既有行为）。
- **反（呈现层）**：缺形态词/未知形态词只显示「即时回复」本体，集合外语不透传成用户可见标签。
- **慢任务不循环假思考**：三段胶囊门 `shouldShowPhaseCapsule` 钉死——零模型快路轮（检索/思考阶段不存在）永不进胶囊；慢路胶囊继续走 S18 既有语义（真实后端状态帧驱动 + 真实已等待时长 + 可取消，非客户端合成循环）。聊天屏第二胶囊分支同样被门（快路轮空白槽直落消息渲染路径）。

## objective 逐项落点（回复分段流式/来源定位/工具阶段折叠/上滑不拉回/保留中断内容）

| objective 项 | 落点 | 性质 |
|---|---|---|
| 回复分段流式 | 既有 50ms 流式防抖批 + `SparkleMarkdown.isStreaming` 部分语法补全（首流前 S18 胶囊承接）——「首个有用内容与 ack 区分」补齐其快路面 | 差量举证（既有）+ 快路语义新增 |
| 来源定位 | 引用 strip 真来源导航 + 未知引用不造链接（验收 2） | 差量举证 |
| 工具阶段折叠 | 工具阶段收在状态行/胶囊（S18 既有）；快路轮不进假阶段（验收 3 门） | 差量举证 + 门新增 |
| 上滑后不自动拉回 | `ChatScrollAnchor` + chat_screen 四处接线（本卡核心新增） | 新行为 |
| 保留中断内容 | M6-09「流式取消=中断保留」既有（`_preservePartialReplyAsInterrupted` + `isInterrupted` 尾标记）+ 本卡滚动锚保证中断处阅读位置不被拉走 | 差量举证 + 阅读位保持新增 |

## 红线自证

- **五 Tab 只增不改**：diff 不含 `mobile/lib/app/routes.dart`（无新路由；引用导航走既有 DeepLinkService/GoRouter 既有路由表）。
- **RF-06 冲突面零触碰**：diff 不含 dashboard_screen / compact_status_bar / task_execution_screen；`git diff e50107fe -- mobile/lib/features/` 仅 chat 域 6 文件。
- **classic 零差量**：`chat_lane` 键缺省（旧后端/I09 开关关）时全部新行为零触发——state 字段为 null、`shouldShowPhaseCapsule` 与旧表达式 `hasActiveRun && streamingContent.isEmpty` 逐值等价（`!isDeterministicLane` 恒真）、marker 不挂载、滚动锚阈值内恒跟随（贴底初始态行为同旧）。测试钉：`chat_notifier_lane_capture_test` 例3 + `chat_lane_semantics_test` 胶囊门正例。
- **不碰 .env/proto/迁移/生成代码**：diff 无 backend 文件、无 proto、无 `*/gen/` 手改（l10n gen 由 `flutter gen-l10n` 生成）。
- **I09 契约复用不复制**：lane 词表消费端封闭集与引擎帧 metadata 键名一一对应（`backend/app/agents/standard_workflow.py:1668`、`response_builder.py:1035`）；无第二真源。

## 交付物索引

`run_manifest.json`（命令/exit code/版本/环境声明）、`test_results.json`（36 新测试 + 595 受影响面回归（一审 C-1 勘误：Δ+2=证据采集 2 个恒执行测试，原 593 为补文件前口径） + I09 49 / I03 77 锚明细）、`review_receipt.json`（PENDING，待独立会话在集成 SHA 复验）、`limitations.md`、`ui/`（顶页截图×2 + 语义 dump×2，Ahem 测试字体块形制同 F02 判例，真实文案由语义 txt 承载）。
