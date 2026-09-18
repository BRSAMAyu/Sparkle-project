# 测试债第三波清理（testdebt-wave3）

基线：`d9210935`（= efb1567a + d9210935 memory tz 修复；worktree wt6）。
挂账 6 红（原 4 + 追加 2）全部修复，定向邻域 85 例全绿。**生产代码仅改 1 处**（context_pack 预算计量），其余 5 例为测试漂移。

## 逐例台账

### R1 error_replan FSM 红（断言过时）

- 测试：`tests/unit/test_error_replan_bridge.py::test_error_replan_bridge_inserts_next_day_first_repair_task_and_completion_lifts_mastery`
- 症状：`ValueError: Invalid state transition: PENDING -> COMPLETED`（`app/services/task_service.py:66`）
- 根因：**测试断言过时**。R1A4-P2-2 任务 FSM 明确 `PENDING→COMPLETED` 非法（完成前置 `IN_PROGRESS`），兄弟测试 `tests/test_plan_task_service_production.py` 已带注释按新契约编写，本测试创建的 bridge 修复任务为 PENDING，直接调 `TaskService.complete`。
- 修法：测试内补生产路径 `TaskService.start(db_session, repair_task)` 后再 `complete`（start 的 event_bus/srl 副作用已在测试既有 patch 集内）。生产代码零改动。
- 证据：单文件 + stage34 文件 11 passed。

### R2+R3 aurora self_model 契约漂移 2 红（断言过时）

- 测试：`tests/unit/test_aurora_runtime_self_model.py::test_plan_turn_bootstraps_self_model_in_redis_with_ttl_and_readout_summary`、`::test_task_timeouts_reduce_strategy_confidence_and_trigger_recalibration`
- 症状：读出层 `strategy_confidence` 得 0.62，断言期望 `DEFAULT_STRATEGY_CONFIDENCE`(0.7)
- 根因：**测试断言过时（契约漂移）**。生产 `SparkleSelfModelService.get_readout_summary` 末尾经 `_attach_bayesian_policy_calibration` 将存储态置信度与贝叶斯校准值按 `0.4*存储 + 0.6*校准` 折算；冷启动校准值 = `(2/3)*0.85 = 0.5667` → `0.4*0.7 + 0.6*0.5667 = 0.62`（精确）。存储态仍是 0.7（测试里 Redis 存储断言通过即为证）。新契约已由**通过的** `test_aurora_bayesian_learner.py::test_self_model_uses_bayesian_uncertainty_to_calibrate_strategy_confidence` 钉死（`strategy_confidence == bayesian_policy.applied_strategy_confidence` 且 `!= 0.7`），两处旧断言与之矛盾。
- 修法：读出断言改为新契约（等于 `bayesian_policy.applied_strategy_confidence` 且低于默认值），超时测试另加 `最终 < 初始` 强化"超时降置信度"语义。生产代码零改动。
- 证据：self_model + bayesian_learner 13 passed。

### R4 exam sprint 完结自动归档红（断言过时）

- 测试：`tests/unit/test_exam_sprint_review_service.py::test_completed_sprint_auto_archives_without_post_exam_review`
- 症状：同 R1，`PENDING -> COMPLETED` FSM ValueError
- 根因：**测试断言过时**，与 R1 同根因。失败点在 `TaskService.complete` 入口校验，先于 `ensure_sprint_node`/`_persist_node_mastery` 新路径执行 —— **与 781c0280 的 galaxy/exam 改动无关**（已排除任务书提示的嫌疑）。
- 修法：测试夹具 `final_task` 创建态 `PENDING` → `IN_PROGRESS`（对齐兄弟测试惯例并注释 FSM 依据）。生产代码零改动。
- 证据：exam_sprint 邻域（review/diagnostic/diagnose_api/sprint_galaxy_mastery/plan_task_service_production）75 passed。

### R5+R6 memory lane prompt 读路径 2 红（生产真缺陷）

- 测试：`tests/unit/test_memory_inferred_write_lane.py::test_two_consecutive_sessions_prompt_includes_inferred_memory`、`::test_memory_inferred_revoke_hides_from_prompt_read_path`
- 症状：写路径健康（candidate 落库），但 prompt 完全没有 `## 跨会话记忆 [L2 引导]` 段；stderr 出现 `Context pack trimmed episodic: usage=582 budget=200`
- 根因：**生产真缺陷 —— 预算计量把永进不了 prompt 的客户端元数据计入 prompt 预算**。`ContextPackBuilder` 对 episodic/goal payload 按**全量序列化**计量 trim（含 `rank_factors`/`correction_actions`/`claim_status` 等纯客户端修正 UI 元数据）；单条 inferred episodic 信封实测 582 token，而**生产默认预算** chat=500 / learning=560 / planning=380 全部放不下一条 → trim 全丢 → `pack.episodic_memories=[]` → 读路径对所有意图死路。prompt 侧模板（`prompts.py` `_format_past_session_memory_section`，标题 `## 跨会话记忆 [L2 引导]`）存在且只渲染 `summary/subject_type/source_type/source_lane/occurred_at/tags/confidence/user_confirmed` —— 即被计量的 ~350 token 元数据从不进 prompt。ceb059f5（memory revival）的提交信息声称"baseline 红由此转绿"，但该测试在 ceb059f5 提交树上实测仍红（临时 worktree 实证），元数据 payload 富化早于/独立于该修复，验收路径实际未通。
- 修法（`backend/app/core/context_pack.py`，最小侵入）：新增 `_budget_view(payload, section)` 把 payload 投影到 prompt 实际渲染字段，`_trim_list`/`_trim_ranked_list` 及 `original_usage`/`token_usage` 按 section 用投影计量。上下文包内 payload 全量字段保持不变（客户端修正 UI 契约不动），仅预算语义回归"prompt token"本义。
- 证据：memory lane 7 passed；context pack 全家族（pack/ranking/personalized_ranking/conflicts/focusing/budget_scheduler/rollout/feedback）+ LTM e2e 全绿；最终定向合集 85 passed。

## 邻域涟漪核验（最终树，串行定向）

85 passed：error_replan_bridge + stage34 + g14、aurora self_model + bayesian_learner、exam_sprint review/diagnostic/diagnose_api + sprint_galaxy_mastery、memory_inferred_write_lane、context pack 全家族。

## 新发现的既存红（不在本波挂账，未动，待挂账）

`tests/unit/test_error_mastery_loop.py` 2 红：`GalaxyService.update_mastery_from_error` 不存在 —— `galaxy_service.py:161` 有 `# --- REMOVED: handle_error_created / update_mastery_from_error ---` 注释，方法在 clean-slate 重置前已删，测试仍调旧 API。d9210935 干净树上同样红（已实证非本次改动引入）。修法需按现行掌握度更新路径（`_persist_node_mastery`/`_error_mastery_delta`）重写测试或确认废弃，属产品语义决策，建议入下一波台账。

## 产物

- 本文档 + `testdebt-wave3.patch`（`git add -A && git diff --cached` 生成，未 commit）
- 变更面：`backend/app/core/context_pack.py`（1 处生产修复）+ 4 个测试文件
