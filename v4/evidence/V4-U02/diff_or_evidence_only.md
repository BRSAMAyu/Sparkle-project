# V4-U02 · diff_or_evidence_only

执行：wtU02（分支 `agent/v4/u02`，自 main@`a592159f` 开出；`f99254c4` 为其祖先）· 2026-09-29 · mobile 单域增量，零 HEAVY、零产品级模型调用、零 backend/gateway/proto/迁移/生成文件手改触碰。**RF-06 三个组员冲突面（dashboard_screen / compact_status_bar / task_execution_screen）零 diff**；五 Tab 路由合同零触碰；classic 面视觉零改动（校准区消费既有 core/design 令牌与 F02 状态徽章族，零新颜色字面量、零像素通道改动）。

## 设计（一句话）

recovery sheet（三宿主同一入口 `showStuckJourneySheet`，J-05 已统一）在旅程载荷区之后**恒渲染**一块 V4 校准区（新组件 `RecoveryCalibrationSection` + 状态机控制器 `RecoveryCalibrationController`）：纠正输入**恒可达**（abstain/旅程错误态照常在场）；纠正原话提交后进入**约束/偏好分离选择**——「仅本次」走 X-03 统一 command path 生成 `task.update_fields` 提案（服务端权威 diff：预计时长 40 → 15 可读对照），「保存为偏好」走既有 M-08 理解纠正写面（`POST /experience/understanding-snapshot/corrections`，routing_policy 域）——两写路径互斥且结构上互不触及；确认调整后**回执门**生效：approve 返回 COMMITTED 且回执本体在场才进成功相（F02 `PixelSuccessBadge` 唯一成功面孔 + 回执号），409 版本冲突/回执缺席的 unknown 均给可恢复出口（按最新重调 = 显式取消过期提案 / 重看权威投影），取消与关闭 sheet 全程零写（原行动不变）。

## 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **三宿主统一已部分满足**：J-05 已让 home/goal/action 三面走同一 `showStuckJourneySheet`（today_cockpit_card / goal_detail_screen / task_execution_screen 既有调用零改动）。本卡差量 = 该 sheet 载荷区之后的校准区垂直面（此前「卡住→纠正」止步于 friction 反馈环 + 文案确认，无约束/偏好分离、无行动 diff、无回执门）。
- **不造第二权威（6 处既有面复用）**：提案生成/确认/取消全走 X-03 统一 command path（diff 由服务端 `prepare()` 权威计算，客户端只渲染 changed 字段前后值）；偏好写面复用 U03 同款 M-08 理解纠正端点（`ApiEndpoints.understandingSnapshotCorrections` 既有常量）；旅程读面复用既有 `StuckJourneyRepository`（零改动）；幂等键复用既有 `proposalActionIdempotencyKey`；状态徽章复用 F02 `PixelStateBadge` 族；任务基线读面复用既有 `taskListProvider`（零新端点、零新表、零本地持久化新增）。
- **I04 契约消费**：abstain 是可纠正状态不是终审——校准区不依赖旅程判定结果恒渲染；「今天只有十五分钟」走「仅本次」会话内生效（随提案 summary 进审计），不写永久偏好；偏好保存显式独立且明示「不改动当前任务」。客户端零 friction 分类（不复制 I04 词牌引擎，free text 不在端上做语义判定）。

## 交付物（语义命名）

| 文件 | 性质 | 说明 |
|---|---|---|
| `mobile/lib/features/recovery/presentation/providers/recovery_calibration_provider.dart` | 新（状态机面） | 十相封闭状态机（input/scopeChoice/adjusting/diffReview/confirming/committed/conflict/unknown/preferenceSaved/preferenceFailed）；`RecoveryProposalView` fail-closed 投影解析（proposal_id 缺失→null 不渲染半份；COMMITTED 无回执本体→unknown 不给成功）；回执门/冲突恢复/幂等重试语义（头注即铁律清单） |
| `mobile/lib/features/recovery/presentation/widgets/recovery_calibration_section.dart` | 新（呈现面） | 恒渲染校准区：输入/分离选择卡/结构化 stepper/可读 diff 表/回执成功面/冲突与 unknown 恢复面/偏好中性 ack；白名单字段名→用户语言映射（词表外原文回落）；全令牌消费 |
| `mobile/lib/features/recovery/presentation/widgets/stuck_journey_sheet.dart` | 改 | 载荷区之后恒挂校准区（loading/error/ready 皆在场）；基线分钟从任务列表投影解析（无锚点=区内如实说明）；零宿主特化分支 |
| `mobile/lib/features/task/data/repositories/action_proposal_repository.dart` | 改 +59 | additive 两方法：`createAdjustmentProposal`（X-03 统一入口，source=recovery_sheet；返回原始投影含权威 receipt 本体）、`getProposal`（冲突恢复重看面）；既有 list/approve/cancel/reject 零改动 |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + 生成 dart ×3 | 改 | 45 新键纯增量（校准区全文案 + diff 字段标签），`flutter gen-l10n` 官方通道再生 |
| `mobile/test/features/recovery/recovery_calibration_test.dart` | 新（测试） | 18 测：三宿主同语义 3 + abstain 反例钉 2 + 分离选择 1 + 偏好≠任务正反 4 + 仅本次 payload 钉 1 + 取消零写 1 + 回执门正反 5 + 409 恢复 1 + 网络失败 1 + 控制器单元 2（含畸形载荷 fail-closed） |
| `mobile/test/features/recovery/recovery_calibration_evidence_test.dart` | 新（证据） | 2 测：常规跑真实渲染断言；设 `U02_EVIDENCE_DIR` 落盘 5 态截图 + 语义树 |
| `mobile/test/.../action_proposal_dual_mount_test.dart`、`test/unit/chat_provider_test.dart` | 改 | 既有 `implements ActionProposalRepository` 夹具补齐两个新方法 override（throw UnimplementedError——夹具不消费），行为零变更 |
| `v4/evidence/V4-U02/` | 新（证据） | 五件套 + 5 态截图/语义树（本目录） |

## 与验收逐条对照（全部可失败；详见 test_results.json 映射）

1. **「三宿主同语义，abstain仍可输入纠正」**——三宿主各一正测钉同一组件/同标题/同输入键；反例钉两枚：abstain 载荷与旅程错误态下纠正输入在场（校准区若被挂回「有 intervention 才渲染」即红）。
2. **「保存偏好≠改任务；取消不改变原行动」**——偏好路径恰一次理解纠正 POST + proposal repo 三调用全空断言 + 成功徽章类型缺席（结构性：该方法体无任何 proposal 调用）；仅本次路径 payload 钉死且偏好端点零调用；取消零写两拍（先都不用 / 不调了）。
3. **「unknown/版本冲突可恢复，回执之后才成功反馈」**——时序反例钉：approve 在途（Completer 挂起）零成功文案/零成功徽章/零 SnackBar，回执 complete 后成功面孔才出现；COMMITTED 无回执→unknown（fail-closed）；409 冲突面 + 按最新重调（显式取消过期提案留痕）+ 重看权威投影（真相赢零重复写）；网络失败≠unknown（不臆断结果）。

## 红线自证（diff 逐面）

- `git diff a592159f -- mobile/lib/features/home/presentation/screens/dashboard_screen.dart mobile/lib/core/design/widgets/compact_status_bar* mobile/lib/features/task/presentation/screens/task_execution_screen.dart` 为空——RF-06 三冲突面零触碰。
- 五 Tab 路由：`mobile/lib/app/routes.dart` 零 diff；既有三宿主调用点零 diff（sheet 内部增量，签名未变）。
- backend/gateway/proto/迁移：零 diff → OpenAPI + BA-ROUTES 机械门与 mypy 门不触发。
- 生成物：`mobile/lib/gen`、`backend/app/gen`、`backend/gateway/gen` 均为 gitignored 实体复制（新 worktree 环境就位用），永不入库；l10n 生成物经 `flutter gen-l10n` 官方通道再生（arb 为源，纯增量 45 键）。
- 无权限语义进入校准面（写资格由 X-03 服务端裁定，客户端不推导）；无 Mock 冒充模型结果；零产品级 LLM 调用。

## 成功呈现纪律（CH-R1/F03 反面教训终结声明）

本卡改动面全文件 **零 `AppFeedback.success` 调用**：成功呈现 = 回执驱动的状态相（committed 相内 F02 `PixelSuccessBadge` + 回执号行），不是动作驱动的 toast；偏好保存成功是中性行（无成功徽章类型）；失败/冲突/unknown 走 F02 状态徽章族（conflict/unknown/failed 语义与全产品同源，零庆祝视觉）。时序反例测试钉死「在途相零成功反馈」。
