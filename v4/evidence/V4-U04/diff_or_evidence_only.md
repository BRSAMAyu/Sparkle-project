# V4-U04 · diff_or_evidence_only — Hybrid 入口接线与运行工作台

- 卡：`v4/04_tasks/cards/V4-U04.md`（implementation · high · 独立审查 2 位 · HEAVY=False）
- 分支：`agent/v4/u04`（base = `30b94d427422144f91983c312f52d0d31e08426d`，git worktree wtU04）
- 性质：**纯接线 + 新页面文件**（mobile-only）；backend 零 diff（`git diff --stat 30b94d42 -- backend/` 为空）；proto/迁移/生成文件零手改（`mobile/lib/gen`、`backend/app/gen` 为主检出实体复制，`git check-ignore` 确认忽略）。

## 一句话设计

把孤儿的 `HybridJourneySheet`（FIX535）挂到合法提案/运行面：新增 `/journey/workbench` 运行工作台（新页面文件，沿用 OpenClaw 路径与 Run ID 的同一 X-05/X-07 读面），入口三处——任务面提案卡旁 `HybridJourneyEntrySection`（有进行中旅程 run → 按 runId 续跑同一段 run；没有 → 打开 sheet 以任务锚定幂等键启动）、OpenClaw hub 概览「运行工作台」按钮（挂现有 OpenClaw，不建第二 Agent 中心）、跨端/冷启动深链 `run_id` 参数；human 步骤（我来做）只有用户本人 confirm/cancel 可推进（幂等键确定性推导 + 消费 `step_replay`），旅程判断/交付审批门全部留在 sheet 内既有服务端门后——入口零审批写动作。

## 验收对照（卡面三条，全部可失败）

### ① FIX535 入口真实可达且不绕审批

- **真实可达（接线级 RED/GREEN 证据）**：`hybrid_workbench_wiring_test.dart` 在**真实 app router**（`routerProvider`）上 `go('/journey/workbench')` 并断言落在工作台（`Key('hybrid_workbench_screen')`）且非 404。RED：`git stash push -- mobile/lib/app/routes.dart`（撤注册一行）复跑 → `Found 0 widgets with key [<'hybrid_workbench_screen'>]` 失败；`git stash pop` 复绿（run_manifest RED/GREEN 节）。
- **入口挂载面**（全部只增）：
  - 任务面：`task_execution_screen.dart` 在 `PendingProposalSection`（X-03 提案卡挂载点）下增挂 `HybridJourneyEntrySection(taskId: task.id)`（+4 行）；
  - OpenClaw：`openclaw_hub_screen.dart` 概览按钮区增挂「运行工作台」`TextButton.icon` → `context.push(JourneyRoutes.workbench)`（+9 行）；
  - 深链：`/journey/workbench?run_id=`（`JourneyRoutes.workbenchUri`）。
- **不绕审批**：
  - 入口区块只是导航——`hybrid_journey_entry_section_test.dart` 第 2 面证明入口唯一写动作是「打开 sheet」，零 approve/reject/complete 调用；
  - 判断门：sheet 内空选择结构性禁用提交（既有 `hybrid_journey_sheet_test.dart` 3 面保持全绿，服务端 `judgment_required` 422 不变）；
  - human_required 步骤推进门见 ②；
  - `start` 幂等键按任务锚定 `j06:start:<taskId>`（跨端同键同 run，不绕过服务端幂等/状态机）。

### ② human_required 步骤只能用户证据推进

- 工作台 run 卡逐步骤标注 ownership（我来做/带我做/交给 Sparkle，I07 三种可读选择词表 + awaiting 高亮「轮到你」）；
- generic run 的 human awaiting 步挂 X-07 统一 `AwaitingStepResumeCard`：唯一推进动作是用户点「确认，继续」→ `POST /runs/{id}/steps/{stepId}/complete`（幂等键 `x07:<runId>:<stepId>:confirm` 确定性推导）；**本页没有任何 agent 代推进控件**（`completeStep` 只以 `action='confirm'` 调用，测试断言记录在案；服务端 owner 纪律 HUMAN/HYBRID 步拒 agent-complete 兜底，`runs.py` 既有门）；
- 旅程 run 的判断/交付只能由用户在 sheet 内亲自给出（判断=真实选中 source_ref 至少一项；交付=显式 confirm）；
- 反例面：`hybrid_workbench_screen_test.dart` 证明 confirm 前零命令、`step_replay=true` 呈现「已确认过」而非报错/二次推进（X-07 命令面挂载要求 V3-FIX-379① 的消费义务在本卡落位）。

### ③ 中断/跨端恢复保持同 run，不重复生成工件

- 恢复唯一锚点是 runId：工作台列表来自 `GET /runs?active=true`（客户端非 runtime owner，零本地持久化）；点「继续旅程」→ `showHybridJourneySheet(runId:)` → `GET /journey/hybrid/{runId}` 幂等回放（`fetchStateRunIds == [runId]`、`startCalls == 0` 断言）；
- 重建/重开（新 screen 实例 + 新 provider 容器）后同一步骤幂等键逐字一致（`x07:run-g1:step-2:confirm`）；
- 深链 `run_id` 冷启动直达同一段 run（不 start 新 run）；
- 后端同 run 语义由既有测试钉住（`tests/unit/test_j06_hybrid_journey.py` 5 passed；I08 恢复对抗 24 passed）。

## 变更清单（+579/-2，全部 mobile）

新增：
- `mobile/lib/features/journey/journey_routes.dart`（只增路由 `/journey/workbench`）
- `mobile/lib/features/journey/presentation/screens/hybrid_workbench_screen.dart`（运行工作台，新页面文件——RF-06 冲突面零触碰）
- `mobile/lib/features/journey/presentation/widgets/hybrid_journey_entry_section.dart`（任务面入口区块）
- `mobile/test/features/journey/hybrid_workbench_screen_test.dart`（8 面）
- `mobile/test/features/journey/hybrid_journey_entry_section_test.dart`（4 面）
- `mobile/test/features/journey/hybrid_workbench_wiring_test.dart`（真实 router 接线面，RED 可失败）
- `mobile/test/features/journey/hybrid_workbench_evidence_capture_test.dart`（证据采集，默认断言执行、落盘 env 门控）

修改（只增，逐文件）：
- `mobile/lib/app/routes.dart`：+1 import、+1 行 `...JourneyRoutes.routes`（五 Tab 分支结构零改动）
- `mobile/lib/core/services/agent_run_read_service.dart`：`AgentRunView.traceId` additive 只读解析（`trace_id` wire 值）
- `mobile/lib/features/journey/data/models/hybrid_journey_models.dart`：`kHybridJourneyTraceId` 常量（识别面，非第二权威）
- `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`：+import、+`HybridJourneyEntrySection` 挂载（4 行）
- `mobile/lib/features/home/presentation/screens/openclaw_hub_screen.dart`：+import、+1 个入口按钮（9 行）
- `mobile/lib/l10n/app_zh.arb` / `app_en.arb` + 再生成本地化：31 个新键（workbench/journeyEntry/openclawHubButtonWorkbench；zh 模板 + en 双面并集，arb 为 gen-l10n 生成流）
- `mobile/test/features/journey/hybrid_journey_copy_test.dart`：新键纳入零 guilt 红线扫描（zh+en 31 键逐词）

## 复用声明（不重建）

- 旅程四段链/审批门：既有 `hybrid_journey_service.py` + `/journey/hybrid/*`（J-06，零后端改动）
- run 脊柱/幂等 resume/owner 纪律：X-05/X-07 `AgentRunService` + `runs.py`（I08，零改动）
- human mastery/目的词表：`hybrid_policy.py`（I07，零改动；ownership 文案「我来做/带我做/交给 Sparkle」对其三种可读选择）
- awaiting-step 卡/防抖/幂等键推导：`AwaitingStepResumeCard`/`ProposalActionGuard`/`runStepActionIdempotencyKey`（U-04/X-07 既有组件，零改动）
- 成功视觉唯一经既有 Badge 体系（F03 词表/呈现适配器未触碰）
