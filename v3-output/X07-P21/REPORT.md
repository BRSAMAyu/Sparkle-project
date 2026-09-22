# X-07 P2-1 · 双计数统一 REPORT

- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt75`（base=8c6797fc，未 commit/push）
- 日期：2026-09-21
- 债项：X-07 验收 P2-1——`agent_runs.steps_done/steps_total`（X-05 单调计数）与 `steps` JSONB 计划的 completion 戳（X-07）双计数并存，UI 两处进度可能不同步。

## 1. 读写点清单（摸底结论）

### steps_done / steps_total 写点

| # | 位置 | 行为 | 改动 |
|---|------|------|------|
| W1 | `agent_run_service.create_run`（原 L541） | steps_total = 显式值 or len(计划) | 改：有计划时 len(计划) 必胜 |
| W2 | `agent_run_service.transition`（原 L681-684） | 参数直接赋值 | 改：赋值后经 reconcile 收口 |
| W3 | `agent_run_service.record_step`（原 L1021-1028） | 绝对序号单调推进 + 显式 total | 改：写入后经 reconcile 收口 |
| W4 | `agent_run_service.define_run_steps`（原 L1104-1105） | total 仅在本列为空时同步 | 改：经 reconcile，total=len(计划) 必胜 |
| W5 | `agent_run_service.project_execution_step`（L1553/L1574） | 经 W2/W3 传参 | 零改动（收口在 W2/W3） |
| W6 | `complete_agent_step` | **只盖完成戳，不动计数（脱节点①）** | 改：盖戳后 reconcile 推进计数 |
| W7 | `complete_user_step` | **只盖完成戳，不动计数（脱节点②）** | 改：盖戳后 reconcile 推进计数（随 resume 同事务） |
| W8 | `api/v1/runs.py`（L339/L470） | create/record 参数透传 | 零改动 |
| W9 | `run_projection_consumer.project_step_event` | 经 W5 间接 | 零改动 |
| - | `models/agent_run.py` L101-102 | 列定义 | 零改动（无迁移、无回填） |

### steps 计划完成戳推进点

仅两处，均经 `app/core/run_steps.step_completion_stamped`（纯函数）：
`complete_agent_step`（by=agent）与 `complete_user_step`（by=user）。
`await_user_step`/`define_run_steps` 只落 awaiting 戳/定义计划，不产生完成戳。

### 读面

| # | 位置 | 消费方 |
|---|------|--------|
| R1 | `models/agent_run.AgentRun.to_dict`（L174-178） | GET /runs 全族（`api/v1/runs.py` 8 处 `to_dict()`） |
| R2 | mobile `agent_run_read_service.dart` L157-158/204-205 | 「正在执行 2/4」UI（读 `steps_done`/`steps_total`） |
| R3 | mobile `chat_stream_events.dart` / `chat_provider.dart` | validation `steps_total`（**另一机制**，validation_engine 产物，与本债项无关，未动） |
| R4 | `run_projection_consumer` 日志 / 直查 SQL（test_x05b、运维） | 原始列值 |
| R5 | Go 网关 | **零引用**（纯透传），无需改动 |

## 2. 统一策略（最小侵入，与验收建议一致）

**唯一权威：steps 计划的 completion 戳**。新增纯函数 `app/core/run_steps.reconcile_step_counters`（stdlib-only，与该模块纪律一致）作为**唯一派生逻辑**，读面（`to_dict`）与服务层全部写点共用：

- **无计划**（`steps` 空）：`(int(steps_done or 0), steps_total)` 原值透传——X-05 execution 轨道（里程碑序号语义）**零改动**；
- **有计划**：
  - `steps_done = max(存储值, completed_steps_count(steps))`——计划完成戳数是进度的下界真源；
  - `steps_total = len(steps)`——计划只定义一次、长度不变（first-win + 冲突拒绝），计划长度即步骤总数真源；显式 `steps_total` 参数在有计划时被收口。

接入点（8 处调用，6 个方法 + 模型读面 + create 列构造）：

1. `reconcile_step_counters` + `completed_steps_count` 新增（`run_steps.py`，登记 `__all__`）；
2. `AgentRun.to_dict`：两字段改用派生值——**字段名与形状不变**（`steps_done: int`、`steps_total: int|null`），移动端 `agent_run_read_service.dart` 兼容面零改动；
3. 服务层写点见上表 W1/W2/W3/W4/W6/W7。

**为什么读面+写面双接入**：写面让新写入的行落库即一致（直查 SQL/运维可见）；读面派生让**统一前已落库的历史脱节行**（只盖戳、计数停 0）无需迁移/回填即在 API 一致呈现。无 Alembic 迁移（硬规则 2：列不动即无 schema 变更）。

## 3. 单调兜底说明（X-05 语义保留）

- `max(存储值, 完成戳数)` 保证派生**只升不降**：`test_reconcile_step_counters_pure_contract` 与 `test_to_dict_derivation_covers_historical_divergence`（外部 UPDATE 把 steps_done 推到 2 后，派生不拉回 1）双测钉死；
- `record_step` 的「ordinal ≤ steps_done → no-op」重放守卫**前置不变**，reconcile 在其后只可能抬高（不会被里程碑序号拉回）：`test_planless_run_counters_passthrough_unchanged` 钉死乱序迟到不回退（R2 F5）；
- `steps_total` 无单调需求（计划 immutable），`len(plan)` 恒定收敛；
- 混合轨道（同 run 既有里程碑序号又有计划）取 max——里程碑进度是真实发生的增强可见性，不因计划落后而抹掉（诚实呈现，与 X-05B「步进是增强可见性不是生命周期真源」分工一致）。

## 4. 红绿统计

红测先立：`backend/tests/unit/test_x07_p21_counter_unification.py`（新文件，8 测试）。

| 阶段 | 结果 |
|------|------|
| 红（实现前） | **7 failed, 1 passed**——脱节如实复现：agent 步完成后计数停 0；用户步同；create 显式 total=9 与计划 3 并存；define 后 total 仍 4；record_step 显式 total=5 覆盖计划 3；to_dict 读历史脱节行显 0（唯一绿是 X-05 零改动守卫基线） |
| 绿（实现后） | **8 passed** |

回归（全部串行、分批 ≤4 文件）：

| 套件 | 结果 |
|------|------|
| X-07 既有 19（hybrid_run_steps 12 + api 5 + migration_sqlite 2） | **19 passed** |
| `test_agent_run_service.py`（X-05 服务回归） | **32 passed** |
| `test_runs_api.py` + `test_run_step_projection.py` | **21 passed** |
| X-10 门禁 `tests/v3_action_eval/test_x10_action_eval_gate.py`（含 `test_inline_rerun_core_cases_all_families` 真实服务层复跑，覆盖 run_steps 族；executor `execute_run_steps` 正是驱动被改六方法的面） | **12 passed** |
| 合计 | **92 passed, 0 failed** |

基线核验：所有上述套件在改动前（base 8c6797fc）均先行跑过一遍全绿，红测仅新增文件红——无存量破坏。

## 5. 诚实申报

1. **`test_x05b_e2e_execution_projection.py` 未真实执行**（需 PG/Docker，本机单跑恒 skip，基线亦 skip）——其单元级对应 `test_run_step_projection.py`（11 passed）已覆盖 record_step 投影语义。
2. **行为变更点（有意）**：run 带 steps 计划时，显式 `steps_total` 参数被计划长度收口（create/transition/record_step/define 四处）。API 无计划路径不变；这是「两处进度不分叉」的直接推论，`test_record_step_with_plan_total_follows_plan` 钉死。
3. **`record_step` 的 no-op 重放路径（ordinal ≤ steps_done）不做写面收口**（保持纯 no-op 契约）；此类历史行的读面一致性由 `to_dict` 派生兜住。
4. **无 DB 回填**：历史行存储列值在下次写点经过时收敛；在那之前直查 SQL（R4）仍见旧值，API 面已一致。列定义零改动、无 Alembic 迁移。
5. worktree 无 `.env`：全部测试以命令行环境变量 `SECRET_KEY=...` 注入（未创建任何 .env 文件，遵守磁盘纪律）；`backend/app/gen`（gitignored proto 生成物）自主仓只读拷贝以使 API 测试可导入，收工删除。
6. 移动端 `chat_provider.dart` 的 `steps_total` 是 validation 机制（validation_engine），与 agent_runs 双计数无关，未触碰。
7. 资源纪律：全程 LIGHT（pytest 串行、单批 ≤4 文件、零模拟器零 LLM 调用）；swap 峰值约 15.3G/16.3G（>基线开工时 15.3G 持平，无恶化），load <8。

## 6. 改动清单

```
backend/app/core/run_steps.py            | +40（reconcile_step_counters + completed_steps_count）
backend/app/models/agent_run.py          | +13 -3（to_dict 派生）
backend/app/services/agent_run_service.py| +38 -3（六写点接入）
backend/tests/unit/test_x07_p21_counter_unification.py | 新增（8 测试）
v3-output/X07-P21/REPORT.md              | 新增（本文件）
```

patch：`v3-output/X07-P21/changes.patch`（`git add -N && git diff` 产物）。
