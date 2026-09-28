# V4-I07 · limitations（如实登记，不降验收阈值）

## 已知限制与边界

1. **目的/脚手架数据面 = `guide_json["v4_hybrid_policy"]` 版本化子键，非 X-01 契约列**。
   零迁移约束（契约/迁移归 contract-owner 单头）下的选择。代价：策略块是应用层约定，
   不像 X-01 列有 schema 导出与 SQLC 面；B05 §4 的 `action_plan.v1.1`（why_now）落地后，
   后续卡可把 `goal_purpose`/`human_required` 提升为 X-01 契约字段位（届时需版本集合成员
   判定门，B05 §4.1 同款）。本卡只在 guide_json 子键内自洽（自带 schema_version、fail-closed）。

2. **结算门当前覆盖 sprint pack 掌握写面**（`TaskService.complete → _update_sprint_pack_mastery_for_completed_task`，
   reason=sprint_task_completed）。这是今天仓库内唯一的「任务完成→人类节点掌握」直写。
   galaxy `spark_node(study_minutes)`（活动面）不在门内：agent 代执行路径
   （ExecutionIngestor `_complete_task_safely`）actual_minutes 恒 0（既有行为）且该路径本就不触发
   sprint 掌握；若未来 run 面带来新的掌握写点（如 I08 恢复层），须复用
   `settlement_for_task_row`——已留单一入口，审查者可 challenge 覆盖面完整性。

3. **错题本复习结算面未改**：`ErrorBookService.submit_review` 是用户鉴权 REST（user_id 来自
   token），无 agent 提交路径；SM-2 更新与 `apply_review_feedback` 的触发者恒为用户本人。
   「reviews」模块面的暴露点不存在，故零改动（差量举证而非为改而改）。若网关桥未来开
   agent 代复习通道，须先过 `human_mastery_settlement`（REVIEW_PERFORMANCE_IMPACT 的
   节点掌握回升同属人类掌握结算）。

4. **独立检验答案的「可检索」面覆盖了 chat 注入入口；非 chat 的 guide_json 原样读点**
   （任务详情 REST、移动端 guide 渲染）不在本卡改动内——独立检验块的生产写面目前只在本卡
   策略块约定中定义（无既有生产者），移动端渲染面归 UI 卡。风险被结构压低：答案若从未被
   写入 guide_json 以外（无独立存储），唯一模型可见入口就是 chat 注入（已门）。
   审查者可 challenge：`state_aggregator`/gRPC 面是否有 guide_json 直通（本卡核对为无，
   但全仓 guide_json 读点 22 文件，逐一接线超出本卡最小增量；已在 chat 主链路落门+探针可复用）。

5. **脚手架决策的生产写面（何时调 `next_scaffold_step` 并落盘）未接**：转移函数+持久化辅助
   已可失败测试，但「谁在对话流里推进脚手架」（I04 干预执行/聊天建议面）归下游消费卡。
   chat 上下文已携带当前态（stage/hint_level），下游建议面可直接消费。

6. **mastery 目标 + delegated 准备步的分配消解依赖调用方过 `resolve_step_purpose`**：
   若 Planner 直接以 goal 级 mastery 调 X-02，准备步也会被 G1 拦（保守方向，不漏不越）；
   per-step 消解是放宽路径，非正确性依赖。

7. **black 26 对 task_service.py 既有行存在历史漂移**：本卡增量已对齐该文件既有风格并把
   无关行的 black 重排全部手工还原（diff 仅 27 行本卡增量）；task_service.py 因此未纳入
   本卡 black --check 命令（仓内该文件在 black 26 下本就不 clean，非本卡引入）。

8. **审查与集成复验未做**（本卡交付态 REVIEW_READY）：双审（high 卡 2 位独立审查）+
   合并时 action_plan/I01/I03 面集成 SHA 复验由接力机制执行；自称完成不算完成。

## 移交（对齐 I03 模式登记）

- 对 I04（干预执行消费卡）：`task_context["scaffold"]` 投影与 `next_scaffold_step` 的
  消费建议面；脚手架推进的对话流写点。
- 对 I08（运行恢复层）：agent 路完成任务若引入新的掌握写点，必须过
  `settlement_for_task_row`（`backend/app/core/hybrid_policy.py` 单一入口）。
- 对 B06+/contract-owner：`goal_purpose`/`human_required` 的 X-01 契约字段位提升
  （含 `tasks.guide_json` 子键 → 契约列的迁移与版本集合门）。
- 对 UI 卡：`parse_policy_block`/`ScaffoldState` 的移动端渲染（「我来做/带我做/交给
  Sparkle」三种可读选择与底层词表映射）。
