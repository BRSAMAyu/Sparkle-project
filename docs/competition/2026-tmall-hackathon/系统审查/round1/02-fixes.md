# 02-fixes（重建占位）

> 原件（F2 修复明细：P1-1 /complete 400 映射、P1-2 applier 幂等、P2-1..8）随修复工作树清洗丢失（当时未被 git 跟踪）。
> 修复内容以集成提交 `c519bba4` 与新增测试为准：tests/api/test_task_complete_and_update_api.py、tests/unit/test_execution_ingestor_confirm_reject.py、tests/unit/test_plan_state_service_jsonb.py、test_plan_adjustment_applier.py、test_adaptive_replanner_stage34.py 扩充。
> 独立复核结论见 round2/02-r2-engine-planning.md。
