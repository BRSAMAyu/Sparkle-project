# WT689 · U-04 增量独立审查（V3-FIX-378 复验 + V3-FIX-379 评估）

- 审查人：wt689（独立会话，未参与 wt687 实现）
- 审查对象：main `f00c44d6`（fix(chat): wt687 卡 U-04 续做——V3-FIX-378 chat 挂载 proposal 命令分发收口）+ 台账 `0c68f28e` 中 V3-FIX-379 登记
- 工作分支：`agent/node-b/wt689/review`（worktree，未 push；本目录唯一 commit，产品代码零改动）
- 验证环境：worktree `cp -RL` 主仓 `mobile/lib/gen` 后，Flutter 3.41.3 stable

## 裁决：APPROVE

V3-FIX-378 修法属实、接线正确、幂等语义未被重建、测试真测非恒真。379 三项独立核验全部属实（其中 ① 实际比台账登记更严重一点，见评估表），维持 OPEN/待裁决判断与排期建议合理。无阻断条件，无新不诚实面（不需要动用 V3-FIX-380/381）。

---

## 1. 断链实证（任务 1）

**修前形态（`f00c44d6^` 的 chat_notifier_actions.dart）**：`handleWidgetAction` switch 从 `intervention_feedback` case 直接落到

```dart
default:
  debugPrint('ℹ️ Unsupported widget action: $actionType');
```

三命令 `action_proposal_approve/reject/cancel` 在修前代码中零命中——断链描述属实，不是 worker 幻觉。

**修后形态（当前 main）**：`mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart`

- :291-295 三 case 在位，统一转发 `_runActionProposalCommand(actionType, payload)` 后 `return`，不再落 default；
- :309-334 `_runActionProposalCommand` 经 `_ref.read(actionProposalRepositoryProvider)` 转发 X-03 统一 command path；
- 发射点闭合确认：`action_card.dart:241/248/255`（chat 挂载 ActionProposalCard 包装）是全仓唯一发射点，`grep action_proposal_approve mobile/lib` 发射点与消费点一一对应；
- 接线端到端闭合：`chat_screen.dart:1984` `onWidgetAction` → `chatProvider.notifier.handleWidgetAction`，真实挂载路径（非测试假注入）有人接。

## 2. 幂等键语义（任务 2）

**透传链（键未重建）**：

1. 卡内推导：`proposal_card_models.dart:230` `proposalActionIdempotencyKey = 'u04:$proposalId:$action'`；`idempotencyKeyFor` 优先服务端显式携带键，缺省才本地推导——重建/重进得到同一个键（X-09 语义对齐）；
2. 卡片防抖：`ProposalActionGuard.run` 在途重入复用同一 Future，双击只透传一次；
3. chat 挂载包装：`action_card.dart` spread `widget.action.data` 后显式写 `proposal_id`/`idempotency_key`（显式键在 spread 之后，覆盖 stale 数据键，正确）；
4. 仓库转发：`action_proposal_repository.dart:86-103` `_mutate` 把 `idempotencyKey` 原样放进 POST body `{'idempotency_key': ...}`，**无任何重建/改写**。

**缺键双保险（fail-closed）**：`chat_notifier_actions.dart:313-317`

```dart
final proposalId = _actionString(payload, 'proposal_id');
final idempotencyKey = _actionString(payload, 'idempotency_key');
if (proposalId.isEmpty || idempotencyKey.isEmpty) {
  return;
}
```

任一键缺失即不下发、不臆造键。正确。

**失败语义**：`on Exception` → `lastActionStatus: 'failed'` + 既有 lexicon 键 `operationFailed`（零 arb 新键），不伪装成功。`DioException` 是 `Exception` 子类，网络失败被覆盖；`on Exception` 不接 `Error` 与本文件其他 handler 惯例一致，不构成问题。成功路径不写 chat 级状态、由卡内 9 态转换承载（approve→unknown 诚实态），与 docstring 声明一致，属设计而非遗漏。

## 3. 测试真测（任务 3）

| 套件 | 结果 |
|---|---|
| `test/unit/chat_provider_test.dart`（含 3 新测） | 12/12 绿 |
| `test/shared/widgets/action_proposal/` + `first_action_card_test.dart` | 34/34 绿 |
| `action_card_ux/task_list/chat_action_card_navigation/mirofish_wiring_finish` | 10/10 绿 |
| `test/features/chat/` 全族 | 246/246 绿（与 worker 声明逐字一致） |
| `flutter analyze` | No issues found! |

3 新测内容核验（chat_provider_test.dart:241/279/305）：

- 三命令同键透传断言：`_RecordingProposalRepository.calls` 记录 `approve:prop-9:u04:prop-9:approve` 等精确串；
- 失败人话反馈：`throwOnCall=true` 断言 `lastActionStatus='failed'` + `hasLength(1)`（命令确实发出过）；
- 缺键零下发：缺 `idempotency_key` 断言 `repository.calls` 为空。

**恒真性思想实验（变异实测，非纸面推演）**：在 worktree 删除三 case（落入 default）后重跑——12 测中**恰好 2 红**（透传断言红：期望 3 条 calls 得 0；失败反馈红：期望 `hasLength(1)` 得 0），与 worker「修前 stash 变异 2 红」声明逐字一致。缺键零下发测试在变异下保持绿属预期（两种形态下均为零下发，它是负向守卫不背断链检测）。变异已 `git checkout` 还原，worktree 干净，未提交。结论：**测试真测分发接线，非恒真**。

## 4. V3-FIX-379 三项独立核验（任务 4，不实施）

| # | 台账断言 | 独立核验 | 属实性 | 修复成本 | 排期建议 |
|---|---|---|---|---|---|
| ① | `step_replay` 后端已产出、命令服务文档承诺「UI 据此提示已经确认过了」、`AwaitingStepResumeCard.onConfirm` 丢弃投影、全移动端零 consumer | 后端 `runs.py:596` `step_replay=not result.applied` 在树；`agent_run_command_service.dart:23-24` 承诺在树；`grep step_replay mobile` 全仓仅该文档注释；`awaiting_step_resume_card.dart:43` `onConfirm` 签名 `Future<void> Function(String)` 结构性丢投影 | **属实，且比登记更重**：`AgentRunCommandService.completeStep` 本体在 lib+test **零调用点**（hybrid sheet 实际走 `journeyHybridOutcomeConfirm` 独立端点，不经 completeStep）——文档承诺的方法整个无人调用 | 小（S）：onConfirm 签名改带投影 + hybrid_journey_sheet `_confirmOutcome` 消费点接线 + 1 个 l10n 新键；但新键受 wt685 arb 冻结让渡约束，需与键面卡协调 | arb 解冻后随手承接；或并入 U-04 尾巴合流卡。10/4 前非必须（重放场景 UI 显示普通成功，不诚实性问题不成立） |
| ② | chat 挂载 conflict「再看一遍」（action_proposal_review）/unknown「刷新结果」（action_proposal_refresh）仍落 default 静默分支 | `action_card.dart:262/266` 两发射点在树；`grep action_proposal_review\|action_proposal_refresh mobile/lib mobile/test` 仅此 2 命中，`handleWidgetAction` 无对应 case（378 修后复验确认）——V3-FIX-378 同根未收部分属实 | 属实 | 中-大（M/L）：需 GET 单 proposal 读面 + 消息内 widget payload 更新机制（消息状态手术），属新交互流设计 | 同意 wt687 判断：按 10/4 红线只入计划不实施；主路径 receipt 消息可达，此为兜底 affordance |
| ③ | `AgentRunReadService`/`agentRunViewProvider`/`activeAgentRunsProvider` 全套 X-05 持久 run 读面零 UI 消费 | `grep agentRunViewProvider\|activeAgentRunsProvider mobile/lib` 仅命中 `agent_run_read_service.dart` 自身（定义+注册），全仓零消费点；chat 相位条确为流式轮级面（非此投影）；恢复入口现仅 hybrid journey sheet（J-06 覆盖面） | 属实 | 中-大（M/L）：通知 deep link / 冷启动重开渲染入口，涉及路由+新交互流设计 | 同意：按 10/4 红线入计划，post-launch 节奏承接；服务面本体可保留（零消费≠死代码，是待挂载的恢复锚点能力层） |

379 三项台账描述与代码事实逐项吻合，无夸大无缩水，登记质量合格。

## 5. 新发现

无新增不诚实面。两条非阻断观察（不立新号）：

1. `completeStep` 零调用点（379① 的加重情节）已并入上表 ①，承接卡落地时顺带决定该方法的去留（挂上 vs 撤面），避免承诺-调用双悬空固化；
2. `_runActionProposalCommand` 的 `on Exception` 不接 `Error`——与本文件既有 handler 惯例一致，记录备查，不要求改动。

## 6. 纪律声明

- 产品代码零改动：worktree 内唯一动过的产品文件是变异实验（已还原），提交面仅 `v3-output/WT689-REVIEW/review.md`；
- 未 push 远端；未触碰 `/tmp` 运行态与 `.env`；
- 台账零改动（V3-FIX-380/381 经 grep 复核为空闲且本卡无需动用）；
- 本审查证据全部来自本次会话实跑（测试/analyze/grep/git 历史对照），无转引 worker 断言为据。
