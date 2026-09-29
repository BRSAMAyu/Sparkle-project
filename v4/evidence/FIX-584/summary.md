# FIX-584 summary — G5 校准投影缺口修复（FIXED，本地待独立审查）

**定性**（Q01 揭案 → 代码链实查）：向导直达面（wizard-direct）`baselineMinutes=null` 的缺口 = **向导创建分支独有的任务列表投影填充缺失**。`_createGoal` 服务端建 goal+plan+tasks 后，`onStartFirstTask` CTA 直接 `router.go('/tasks/<id>/execute')`，全链零 `taskListProvider` 填充调用；恢复校准区时长锚点（`stuck_journey_sheet._resolveBaselineMinutes`）只读该投影 → 解析不到新任务 → hasAnchor 门如实不出「调整这次行动」入口。pilot 种子面无此缺口（任务先于 TaskNotifier 构造存在，构造期 loadTasks 即含锚点），故「曾全通回执机制」。Q01 姊妹会话「投影按 today 过滤」猜想**证伪**（后端 GET /tasks 全量分页无 today 过滤，r5 console 实证任务可读回）；r5 水化绕道仍 null 的真因 = driver 拖拽未触发 onRefresh（绕道期间零 GET /tasks 请求，时间线实证），绕道从未生效。

**修法**（收敛单一填充函数，不复制粘贴）：`goal_creation_wizard_screen._createGoal()` 创建成功分支补一次 `unawaited(ref.read(taskListProvider.notifier).refreshTasks())`——与任务列表下拉刷新同源的唯一填充函数，onCreated/dialog 两分支共覆盖。`unawaited` 而非 `await` 的裁决：await 使成功弹窗被网络时延卡住（最坏 10s connect timeout）且打破既有 `goal_creation_wizard_screen_test` 契约（邻域实证红）；锚点消费侧是 watch 型自愈，慢网下最多晚一拍，不假缺席。

**回归 + mutation**：
- 新增 `goal_creation_wizard_projection_fill_test.dart` 2 例：①填充钉（创建后投影含新任务）；②锚点钉（G5 面端到端：「调整这次行动」在场 + 无锚点文案不在场）。
- Mutation 亲跑双向：修前形态 `0 passed/2 failed` exit **1**（投影空 + 入口缺失双红，reason 命中缺口语义）→ 还原 `+2 passed` exit **0**。
- 邻域全绿：recovery 5 文件 + goal 4 文件 + f569 语义接线 `+64 passed` exit **0**；`dart analyze` 两变更文件零问题。
- 一次真实返修入档：await→unawaited（见 verification §3.3），不以删断言换绿。

**遗留**：真端复测归 Q01 复测轨（真机点出回执帧不在本卡证据）；`unawaited` 一拍延迟窗口与测试文案锚定见 limitations。

**交付**：`agent/v4/f584` 本地提交（不 push）；证据四件套 + raw 关键行在本目录。与 FIX-583 零文件交集（本卡 mobile/lib/features/goal + mobile/test，backend 零改动）。
