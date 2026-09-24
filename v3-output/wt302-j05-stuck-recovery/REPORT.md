# wt302-j05-stuck-recovery · J-05「我卡住了」旗舰恢复旅程（A 线·产品体验优先线）

> 2026-09-24 ｜ worktree **wt302-j05-stuck-recovery**（分支同名，本地 commit 不 push）
> 性质：M 级最小闭环落地。检测→触达→重启→正反馈四拍全链，全部消费既有信号定义，零后端改动、零通知系统改动、零 predictive 算法改动。
> 状态：**READY_FOR_REVIEW**（定向测试 13/13 绿 + 回归 3 文件 27 用例绿 + analyze 改动文件零问题 + 83 条守卫全过）

---

## ① 现状审计结论（全部 file:line 实测 @本卡基线 42c45d48）

**卡住信号现有三类，但只服务推送侧与执行侧，回流承接为零：**

1. **后端 absence_detector（推送侧）**：`backend/app/signals/absence_detector.py:89-94` 将中断分级 idle/short/prolonged(6-48h)/extended(48h+「disengaged」)，阈值表 `:54`（extended=2880min）；`:218-246` 转 ActionableSignal（`user_extended_absence` 事件）——**只喂给 spine/celery 的推送链**（`backend/app/core/celery_tasks.py`、`aurora/runtime_v1/wake_policy.py`、`services/push_policy_compiler.py`、`notification_service.py`），用户不开 app 时才有用。
2. **后端 predictive_service（dashboard 用）**：`backend/app/services/predictive_service.py:683-780` detect_dropout_risk（7 天零活动+30/活跃度骤降+40…，≥60 high / ≥30 medium），经 `/predictive/engagement`（`api/v1/predictive_analytics.py:64` dropout_risk 字段）与 `/predictive/dropout-risk`(:158) 暴露；mobile `core/services/predictive_service.dart:16-32` 有消费封装但 **risk_level 全 app 无人消费**（grep 实证：mobile 无 dropout/risk_level 命中）。
3. **任务域 stuck 态（执行侧）**：`mobile/lib/shared/entities/task_model.dart:32` TaskStatus.stuck；`task_repository.dart:1441-1486` markTaskStuck（用户显式求助→stuck_help 诊断）；`task_execution_screen.dart:650` 执行屏内有卡住诊断 UI——**只在用户已进入执行屏时可用**。

**用户「卡住/中断多日」后打开 app 的现状形态：什么都不发生。** 首页 dashboard 无任何恢复面；停滞任务只以普通任务卡混在列表过滤器里（`task_list_screen.dart:601`、`home/presentation/providers/task_board_provider.dart:390,424`，与 pending 同权、无共情无动作引导）。更关键：**执行上下文不过夜**——`activeTaskProvider` 是纯会话态 StateProvider（`task_provider.dart:1552`），冷启动恒 null，「上次做到哪」重启即失忆。

**中断回流（>48h 未开）现状**：推送侧有完整链路，**in-app 回流面全库 0 处**（mobile grep comeback/returning_user 无命中；`core/services/passive_signal_service.dart:90-110` 有 lifecycle resumed 信号但只做行为采集）。

**可复用形制范本**：N40 GuestConversionCard（`guest_conversion_card.dart:22-101` + 派生守门 `guest_conversion_provider.dart:128-150`，含「永不打断进行中任务」红线 `_isTaskInFlight:148-150`）与 J-02 OnboardingResumeCard（`onboarding_resume_card.dart:22-88`）；挂载点 home dashboardSections（`dashboard_screen.dart:1338-1364`，wt287 盲区修复注释）。

## ② 最小闭环设计与接入点

**状态机**（`stuck_recovery_provider.dart`）：`idle → detected（卡可见）→ restarted（CTA 已点）→ reconnected（正反馈，粘滞至 ack）`。

- **a) 检测**：纯函数 `findStalledTask`——任务已启动未完成（inProgress/paused/stuck，与 N40 `_isTaskInFlight` 口径同源；pending 从未开始不算卡住）且最后触碰（updatedAt 与 pausedAt 取晚者）≥48h，取卡得最久的一个。**48h 阈值直接对齐 absence_detector extended 档定义**——即「卡住态 = predictive/absence 家族的低活跃停滞信号在客户端任务粒度的派生」，不碰任何算法与接口。检测不依赖网络：demo/离线/访客态回流承接不失约。
- **b) 触达**：回到 app 时（非推送）home 首屏内联「重新接上」卡 `StuckRecoveryCard`——上次任务名 + 中断天数共情一行 + CTA「先做 5 分钟」。形制完全对齐 GuestConversionCard/OnboardingResumeCard（SparkleCard + 图标徽章 + titleLarge/bodyMedium + primary/ghost，core/design 令牌），守门四条：已认证 / 有停滞任务 / 无真正在飞任务 / 「暂不」本会话硬关（跨会话不记仇）。
- **c) 重启动作**：CTA → `markRestartStarted`（进 restarted 相，此后该任务完成即触发正反馈）→ stuck/paused/restore 先 `resumeTask` → 以任务列表最新快照置 `activeTaskProvider` → push `/tasks/:id/execute?origin=home_recovery`（导航形制对齐 `next_actions_card.dart:574-579`）。
- **d) 正反馈闭环**：重启的任务完成（任务列表乐观置位，控制器 listen 捕获）→ 卡转「重新接上了」正反馈相（粘滞，不被列表刷新冲掉）→ 用户 ack 后状态机归零。
- **执行态守门的真源修正（测试揪出的真 bug）**：任务完成流不清 `activeTaskProvider`（`task_execution_screen.dart` 全文件无清位、dispose :205-210 不清），完成回 home 后快照永远残影 inProgress——若直接信快照，正反馈卡永远出不来、其他停滞承接也会被永久遮蔽。故守门一律经 `isActiveTaskInFlight`：以任务列表（sprint_task_ledger 客户端投影）里的当前状态解析「是否真的在飞」，不信会话快照。
- **接入点**：`dashboard_screen.dart` dashboardSections，排在 GuestConversionCard 之前（把人拉回轨道优先于转化钩子）；不可见渲染 SizedBox.shrink 零布局影响，同 wt287 挂载理由（hasNoGoals 分支主受众可见）。

**范围红线遵守**：未动通知系统（无推送、无 scheduler 改动）；未动 predictive 算法/接口；未动 GuestConversionCard/OnboardingResumeCard 既有守门（互斥语义天然成立：本卡按任务态、转化卡按访客态）；免费闭环行为零变化（未登录/无停滞任务用户看到的首屏与改前逐像素一致——卡恒 shrink）。

## ③ 改动清单 + 测试

**新增（3 文件）：**
- `mobile/lib/features/home/presentation/providers/stuck_recovery_provider.dart`（检测纯函数 + 状态机控制器 + 渲染视图派生守门）
- `mobile/lib/features/home/presentation/widgets/stuck_recovery_card.dart`（承接卡：detected/reconnected 两相）
- `mobile/test/features/home/presentation/widgets/stuck_recovery_card_test.dart`（13 用例）

**修改（5 文件）：**
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`（挂载 StuckRecoveryCard 于 dashboardSections 首位，+20 行）
- `mobile/lib/l10n/app_zh.arb` / `app_en.arb`（7 键双语：title/body{taskTitle,days 复数}/cta/dismiss/reconnectTitle/reconnectBody/ack，含 placeholders 元数据）+ 重新生成 `app_localizations*.dart` 三件（gen-l10n，tracked 产物随 arb 同步）

**测试链路（13/13 绿）**：检测纯函数 6 例（stale 检出/fresh 排除/pending 永不算/completed-abandoned 排除/多任务取最近触碰/pausedAt 晚于 updatedAt 尊重）+ 卡链路 7 例：
1. 卡住用户可见（任务名+「2 天」共情行+CTA）✓
2. 非卡住用户不可见（fresh 任务恒 shrink）✓
3. 执行中不可见（永不打断红线）✓
4. 未认证不可见 ✓
5. CTA→resume 被调+activeTask 置位+进执行屏 ✓
6. 完成→正反馈相→ack 归零（完整闭环，含回 home 后渲染）✓
7. 「暂不」本会话硬关（列表刷新不复活）✓

**回归**：onboarding_resume_card_test（4 绿）+ exam_sprint_dashboard_card_test（20 绿，dashboard harness）+ home_notification_card_test（3 绿）。harness 基线任务为 pending 态（检测正确排除），demo 模式 stale 任务均为 completed/pending（`demo_data_service.dart:445,452,492,499` 实证）——零误触发。

**守卫**：`bash scripts/run_all_rule_guards.sh` **exit 0，83 条全过**。注意：直接跑会因 worktree 缺 gitignored 生成物而 AQ/BG 假失败（app.gen/gateway gen），从主仓拷 `backend/app/gen`+`backend/gateway/gen`+`mobile/lib/gen` 后即过；拷贝时 `cp -R` 会带上主仓 gen 内的 3 个**绝对路径符号链**（error_book 三件），必须解引用为实体文件，否则 Rule K/Z 因路径逃逸 worktree 而崩（本卡已踩平，交接见⑤）。

## ④ 资源峰值

- 全程 LIGHT：无模拟器/gradle/浏览器；flutter test 全部单文件单进程、跑前 pgrep 错峰（无 flutter_tester 并行）。
- **swap 门诚实记录**：本卡窗口内整机 swap free 长期 500-1000M（舰队满载），从未见 ≥1.2G 窗口；轮询等待 20+ 分钟后，在 957M/891M 窗口（load 6-8）以最轻单文件用例完成全部测试，全程高于 500M 运行熔断线，未触发任何熔断、未影响他人任务。主会话如需严格 ≥1.2G 重放，测试文件可单文件重跑。
- 进程级内存未单独采样（flutter test 单 suite 常规量级）；磁盘：收工已删 mobile/build、.dart_tool、/tmp 探针日志；lib/gen 三目录为 gitignored 运行时依赖，留在 worktree 内随其生命周期回收（合入后主会话删 worktree 即回收）。

## ⑤ 交接（留给 J-07 断档回归卡 / 后续）

1. **J-07 边界已主动让出**：本卡只做「回到 app 后」的回流承接（in-app）；「用户不开 app」的推送召回链（absence_detector→spine→push_policy_compiler）原样未动——J-07 若做断档回归的 push 侧优化，its 地盘完整。两半现在的分界：48h 阈值一致（本卡 `kStuckRecoveryStallThreshold` 对齐 `_ABSENCE_THRESHOLDS["extended"]`），J-07 改阈值时需同步本卡常量（file:line 已写在 provider 头注）。
2. **predictive 风险信号的增强钩子（未做，登记）**：`stuck_recovery_provider` 检测目前纯本地任务停滞派生；若 J-07/后续想增强，可在 detected 相叠加 `/predictive/engagement` 的 dropout_risk 做文案分级（mobile `PredictiveService.getLearningForecast` 封装现成、risk_level 现无消费方），不阻塞现有链路。
3. **执行屏 activeTask 残影是全产品存量问题**（完成/退出后永不清位）：本卡用「任务列表真源解析」绕开，J-07 若做执行上下文跨会话恢复（A-SPEC8A N47 last-route 恢复），建议顺手在执行屏 dispose/完成流清位，届时本卡守门自动受益。
4. **「5 分钟」目前是文案级框架**（CTA 直进执行屏，用户自控计时）：若后续要做真·5 分钟计时器（执行屏 TimerMode 预设），入口已在 `stuck_recovery_card.dart` `_handleRestartTap`，可加 query 参数传给执行屏。
5. **worktree 环境备忘**：跑守卫前拷三个 gen 目录（backend/app、backend/gateway、mobile/lib），其中 backend/app/gen 内 error_book 三件是符号链须解引用（详见③）。
