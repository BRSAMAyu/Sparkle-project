# Rule AB

Stage 29.5 起，Rule AB 的权威解释升级为两层约束：

1. `backend/app/state_aggregator/` 仍然必须保持只读派生层，禁止任何写库、写缓存、原始 SQL 写入或副作用型持久化调用。
2. Router 读取 Aggregator 字段时，命中必须提前登记在 [rule_ab_router_whitelist.md](/Users/brsama/code/GitHub/Sparkle-project/docs/aurora/rule_ab_router_whitelist.md)；未登记字段一律视为红线。

永久边界：

- `task_sufficiency_summary` 仅允许用于 Stage 20 follow-up question 分流。
- `context_sufficiency_summary` 仅允许生成 prompt caveat，永不作为 Router 分支条件。
- `active_skills_summary` 仅允许进入 Stage 21 skill 选择输入，禁止外扩为通用画像路由信号。

自动化：

- `scripts/check_rule_ab_aggregator_integrity.py`
- `scripts/run_all_rule_guards.sh --rule AB`
