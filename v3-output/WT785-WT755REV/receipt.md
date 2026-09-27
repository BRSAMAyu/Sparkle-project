# WT785-WT755REV — wt755 分支（E-08 SLO L0 首帧前移）独立审查 receipt

> 2026-09-28 ｜ 审查员 wt785 ｜ worktree `Sparkle-sysrev/wt785-wt755rev`
> 审查对象：commit `938e845c`（分支 `agent/node-b/wt755/slo`，base=merge-base `68dc7e20`）
> 环境：主仓只读；自有 detach worktree @938e845c + `cp -RL` 主仓 `backend/app/gen` + `.venv` 符号链接指主仓。

## Verdict：APPROVE-for-integration（附重编号映射）

**重编号映射（门后集成时执行）**：wt755 台账新增行 `V3-FIX-491`（澄清门快交互文案无预算 LLM）→ **`V3-FIX-498`**。

- 依据：主干现行 `V3-FIX-491` 已被占用（wt754 登记 auto_degrade 审计 publish 错位，修复集成于 wt761 `1e3b6ebf`；主干台账 :379 行）；497 亦已被 wt761 占用（:383 行）。
- **498 号是 fleet 协调方轮 #254 预先改道分配给 wt755 的**（state commit `aa7fe96c`：「wt755 挂起项撞号改道：其 491→498（497 已被 wt761 占用）」），且主干现行台账 grep `V3-FIX-498` = **0 命中**（复核于本审查时点 main=e36fe444）。优先用 498，而非泛取 533（533 亦空闲、在册最高 532，若 498 届时被占可作回退）。
- 重编号需同步改的引用（均在 wt755 新增文本内）：①新行行首 ID；②该行「预分配号 491 grep 复核空闲…备用 492 未动」出处格改写为重编号注记（按「集成即纠指针」先例注集成 SHA）；③439 行进展注记内「预占 V3-FIX-491」→ 498。`v3-output/WT755-SLO/notes.md` 为冻结产物不改，台账行为准。
- 其余 6 文件 merge 干净（`git merge-tree` 实证唯一冲突文件 = `v3/06_agent_fleet/DYNAMIC_ISSUES.md`，冲突点=表尾 append 撞行；439 行进展注记 hunk 所在行主干与 merge-base 逐字节相同，可干净落位）。

## 1. 交付本体复跑（sqlite 内存环境）

命令：`cd backend && DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v ./.venv/bin/python -m pytest <paths> -q`（路径均 find 实证存在）

| 面 | 结果 |
|---|---|
| commit 触达 4 测试文件（orchestration/test_orchestrator_process_stream_integration + unit/test_stage_events_e03 + test_phase2_core + test_phase2_integration） | **42 passed** |
| 新钉 `test_intake_ack_beats_slow_prologue_guards`（三守卫 0.2s 慢桩+事件序+首帧<500ms） | 绿（42 内含） |
| **红验证**：新钉测试 × merge-base orchestrator（`git show 68dc7e20:...orchestrator.py` 覆盖后单跑） | **FAILED**（真红→绿，非恒真钉） |
| notes 声称受影响面合集（tests/orchestration + tests/unit/orchestrator + done_tail/observability/signal_spine/trace_spine/event_*reliability/context_source/f821 + agent_grpc_service×3 + integration/phase5） | **1419 passed, 1 failed, 1 skipped**（88s） |
| 唯一 failed = `test_signal_spine.py::test_version_conflict_result_has_diff_fields` | **即 notes 预报的既有 flaky（批量偶红单跑绿）**——单跑复验 passed；`tests/orchestration/test_statechart_engine.py::TestParallelExecution` 单跑亦 passed（5/5） |

数字口径注记：notes 称「orchestration 1229」，我实测 `tests/orchestration` 收集 208；其「合计约 1340」与我的合集收集 1420 同量级（我面略宽）。总数自洽、分量数「1229」无法按该文件路径复现，判为分量口径误标，非绿态造假（绿态已独立复现）。

## 2. 静态面（delta 口径，对 merge-base 68dc7e20 两侧独立冷跑）

| 项 | 分支 938e845c | merge-base 68dc7e20 | delta |
|---|---|---|---|
| ruff：`app/orchestration/orchestrator.py` | 0 error | 0 error | **0** |
| ruff：`tests/unit/test_stage_events_e03.py`（新文件） | 0 error | —（不存在） | **0** |
| ruff：`tests/orchestration/test_orchestrator_process_stream_integration.py` | 0 | 0 | **0** |
| ruff：`test_phase2_core.py` / `test_phase2_integration.py` | 49 / 51（全 W293/I001/F401 族既有） | 49 / 51 | **0**（既有噪声两侧同分布） |
| mypy（MYPY_CACHE_DIR 独立冷跑 `mypy app/orchestration/orchestrator.py`） | **66 errors in 59 files** | **66 errors in 59 files** | **0**（归一化错误集 `diff` 逐行相同；带行号唯一差异=orchestrator.py 既有 arg-type `CheckpointDebriefService` 2400→2415 平移，与 notes 声明逐字一致） |
| black `--check orchestrator.py` | 19 hunks | （notes 称 base 同判） | 零新增（与 notes 一致） |

注：绝对数 66 与主干现行 mypy 55 不可比（基点不同），按指示只报 delta=0。

## 3. 证据核验（notes.md → wt372 在案交付物逐点回查）

- `v3-output/WT755-SLO/` 仅 notes.md（本卡无 bench 产物，其性质声明=机制前移+单测钉住，**无真模型跑**，与交付一致——分层标注：规则层/机制层证据，非模型层）。
- wt372 raw.jsonl 程序化复算（本 worktree 内 `v3-output/WT372-E08-BENCH/raw.jsonl`）：104 行、103 条含 `t_first_stage_s`、**恰 21 条 ≤0.5s** → 与 439 行/notes 引的「全量仅 21/103 ≤500ms」吻合；`L2-08 t_first_stage_s=3.0305` 与 notes「intake@3.0305s」吻合；REPORT.md :94「L2 首事件 p95=5446ms FAIL」与 notes「基线 5446ms」吻合。
- 归因修正声明（T 栏「门判定在首帧前」与实测不符、真凶=守卫链+StreamChat 前奏串行段）：与 diff 实态一致——旧代码 ack 确在守卫链后、`_check_goal_quality` 前，raw.jsonl 时间线（门判定紧随 ack 9ms）支持其读法。属诚实勘误而非翻案。
- 「修前实录首帧 0.605s」未逐值复测（我只复现红 FAILED 本身），量级可信。
- 台账守卫：`ledger_union_merge.py --verify --strict-pipes`（用主仓 venv）→ **verify 通过**：326 行 V3-FIX 行全 8 裸管形态、零冲突标记、ID 无重号、状态枚举合法。

## 4. 交付本体 diff 审读（backend/app/orchestration/orchestrator.py 唯一生产码）

- 实质=E-03 ack 块（queue/stream_callback/RunLedgerRecorder/run_started/intake ack/drain + chat_mode/user_message 提取）自「守卫链后、Step 3 态更新后」整块前移至「Step 1 校验/幂等之前」（请求身份锚定后）；纯重排零新并发。
- 行为面新增一处（已声明+已测）：`run_started` persist 加 try/except 降级非致命（旧行为=异常入外层 try 触发 error 帧）；失败时 ack 带空 `ledger_event_id`。
- 早退路径语义变化（已声明+3 处契约测试同步）：校验失败/幂等重放/锁冲突现先收到 1 帧 intake ack（droppable status 帧）再收错误/缓存终帧——42 绿含此三面。
- `EARLY_ACK_PROGRESS_ENABLED=False` 语义不变：新旧两版 run_started/queue 建立均不受该开关门控，开关仅门 `_emit_early_ack_progress`，parity 成立。
- 未触 proto/OpenAPI/gateway schema/DB：commit 7 文件中零 proto、零 openapi 快照、零生成物——**契约面无快照/生成物更新需求**（主干快照重冻结不受影响）。

## 5. 集成面预判（供主会话门后集成）

- 冲突文件清单（`git diff --name-only 68dc7e20 938e845c` ∩ 同左→main，并 `git merge-tree --write-tree` 实证）：**仅 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`**。其余 6 文件零冲突。
- 冲突机理：wt755 在表尾（481 行后）append 新行 491；主干同位已追加 490/491/…/532 多行 → 表尾 add/add 撞。439 行注记 hunk 本身可干净落（该行主干与 mb 相同）。
- 集成操作建议：按上方重编号映射（491→498 及两处文内引用）手工落 439 注记+新行（改 ID 后置于表尾现行最高行后），重跑 `ledger_union_merge.py --verify --strict-pipes`；439 行保持 OPEN（其进展注记明确「保持 OPEN 不置 FIXED——端到端 SLO 达标需有 key 环境真模型 bench 复测」）。
- 498 行若集成时已被在途分支占用：回退 533（当前空闲、在册最高 532）。

## 6. 残差与不移交事项（原卡已自登记，审查确认成立）

- StreamChat 前奏前移（L1）、门 first-content 流式化、门并行化、L0 no-model 直答（L3）、事件循环拥塞——均留登记，notes §3 分级表与 439 注记③一致；本审查无补充新增缺陷登记。
- 无 Mock 冒充、无运行栈触碰、未碰 ns001 数据、未 push、主仓只读——本审查全程合规。

---
审查命令与输出实录见上文各表；复核入口：worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt785-wt755rev`（分支 `agent/node-b/wt785/wt755rev`）。
