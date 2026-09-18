# 03-fixes（重建占位）

> 原件（F3 修复明细：E1 属性转发、S1 缓存隔离、B1/B2 计费、Q1 Lua、A1 会话、E3 fallback、M1/M2、E2、P1'-P3'）随修复工作树清洗丢失（当时未被 git 跟踪）。
> 修复内容以集成提交 `f813c3f0` 与 9 个新测试文件为准（test_llm_dispatcher_quota、test_auth_session_touch、test_billing_worker、test_llm_tier_fallback_order、test_memory_inferred_write_lane_queue、test_push_quiet_hours、test_rate_limit_lua、test_working_memory_rejection_guard、test_llm_explicit_temperature、test_push_recall_policy_guards）。
> 独立复核结论见 round2/03-r2-critical-services.md（Apex：14/14 验证落地）。
