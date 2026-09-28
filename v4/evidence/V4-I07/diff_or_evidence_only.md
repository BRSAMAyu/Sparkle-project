# V4-I07 · diff_or_evidence_only —— 学习/交付目标的人机权限与脚手架

卡：`v4/04_tasks/cards/V4-I07.md`（implementation · risk high · 双审）｜锁：hybrid-policy
分支：`agent/v4/i07` @ wtI07，base `1063abb3`（main，含 I03/I06/D02 合并）
规格：`v4/03_intelligence/EXPERIENCE_AND_LEARNING.md` §Human/Hybrid/Agent 的学习目标 + MASTER_DESIGN §5「人机合作不偷走学习」/§6「示例→自己做→检查」

## 一句话设计

在**现有** Human/Agent/Hybrid 步骤语义（X-01 `ExecutionMode`/`CognitiveOwnership`、X-02 allocation policy）上加**目的维度**（mastery/deliverable/mixed）与 **human_required 约束**：`backend/app/core/hybrid_policy.py` 纯函数策略层提供目的解析、人类掌握结算门、脚手架链（示例→尝试→独立检验 + 提示渐隐）与独立检验答案红化，并接三处真实消费面（X-02 分配、TaskService.complete 结算、chat.py 上下文注入）——不另起第二权限真源，零迁移零新列。

## 与既有权威的关系（不重建、只增量）

| 既有权威 | 本卡关系 |
|---|---|
| X-01 `action_plan.v1` 契约列（execution_mode/cognitive_ownership） | **不动**。目的/human_required 落 `tasks.guide_json["v4_hybrid_policy"]` 版本化子键（既有 JSONB，零迁移）。提升进 X-01 契约列 = contract-owner 的 `action_plan.v1.x` 变更，本卡不做（登记见 limitations） |
| X-02 `action_allocation_policy.py`（hybrid-policy 锁真源） | **增量消费**：`AllocationFactors` +goal_purpose/+human_required 因子（词表 `GOAL_PURPOSES` import 不复制）；`_learning_guard_active` 三分支（mastery 显式生效 / deliverable 解除 task_type 启发式但 user_core·learning_goal·human_required 仍守 / 未知走既有启发式）；+G5 `human_required_step_no_agent` 硬规则；v1.1→v1.2 按冻结协议重冻结（+1 reason code、sha256、版本） |
| D-02 outcome 账本 / galaxy 节点掌握 | **结算门只拦掌握写面**（`_update_sprint_pack_mastery_for_completed_task` → `update_node_mastery`）；任务完成、outcome 广播、行动账本照常——「完成任务≠能力掌握」的账本分离 |
| B05 回执契约 | unknown/降级语义同款（脏块 fail-closed → None+原因，不半真解析）；答案面纪律与 §9 反例「模型自评已完成」同源 |
| I01 `episode_resume_view` | 零改动（`pending_human_step` 词表冻结归 B05/I01 owner）；本模块可被未来 v1.x bump import |
| I03 选择器 | 零改动；封闭词表纪律同款（词表冻结测试 + 精确集断言） |
| I08 深任务运行恢复 | 零交集：本卡是权限判定层（谁完成能否结算），I08 是运行恢复层（agent-runtime 锁面未触碰） |

## 三个可失败验收面的实现

### 验收① 学会目标中 Agent 代答不能结算人类掌握

- 纯函数：`human_mastery_settlement(goal_purpose, human_required, completed_by)` → `SettlementVerdict`。规则：用户完成→结算；agent 完成 × human_required→`BLOCK.agent_completed_human_required_mastery`；agent × mastery 目标→`BLOCK.agent_completed_mastery_step`。
- legacy 行（无策略块）：`derive_goal_purpose` 按 X-02 `LEARNING_TASK_TYPES` **同集**推导（防漂移测试钉死：LEARNING/TRAINING/REFLECTION → mastery；delegated → deliverable；其余 mixed）。
- 真实接线：`TaskService.complete` 在 sprint 掌握结算（galaxy `update_node_mastery`，reason=sprint_task_completed）前置门；BLOCKED 时 WARN 留痕（task_id/reason/purpose/human_required/completed_by），完成与 outcome 照常。
- 可失败证据：stash 回退接线复跑 → `test_complete_by_agent_does_not_settle_sprint_mastery` 红（旧代码 agent 完成照常 +25 节点掌握）；复原后绿。

### 验收② 交付目标允许合法代办，不强迫用户手工重复

- 声明块 `goal_purpose=deliverable`（或 legacy delegated/PLANNING/SOCIAL/OCR 推导）+ agent 完成 → `OK.deliverable_delegation_settlement`，照常结算——完成不被要求用户手工重做一遍。
- 分配面：X-02 对 deliverable 目的解除 task_type 启发式（`LEARNING` 类型 + 声明交付 + 委托意图 → `mode=agent` 可行，G1 不触发）；步骤自身显式学习信号（user_core/learning_goal/human_required）仍守。
- 反例守卫：交付目标里声明 human_required 的门，agent 代完成仍 BLOCK（G5 + 结算面双落）。

### 验收③ 独立检验答案不出现在可见/可检索上下文

- `redact_independent_check(payload)`：`kind=="independent_check"` 节点或 `independent_check: true` 旗标节点的整棵子树内，封闭答案键集（answer/correct_answer/expected_answer/reference_answer/model_answer/solution/answer_key）剥除；返回 (干净深拷贝, 移除路径)。非标记节点同名字段不动（用户自有错题材料不属此门）。
- 真实接线：`api/v1/chat.py` task_context 的 `guide_json` 注入改走 `task_guide_context_projection`（答案先剥除；脚手架态 stage/hint_level/goal_purpose 单独投影——答案面之外）；剥除留 INFO 观测日志。
- 判分权威原地保留：答案本体留服务端 guide_json（红化是投影面门，不是数据删除）；泄漏探针 `contains_independent_check_answer` 供测试/守卫。

### 脚手架链（示例→尝试→独立检验 + 提示渐隐）

`next_scaffold_step` 冻结转移表：推进须 `user_chose ∧ evidence_supported`（缺一原地，两种 HOLD 码）；示例段证据支持而用户未推进 → 提示渐隐一档（full→reduced→none）；尝试失败 → 提示档**回升**一档（局部支持），阶段永不回退（不把用户降级）；independent_check 终态。`apply_scaffold_decision` 把决策写回策略块（guide_json 版本化子键，零迁移）。chat 上下文投影携带当前态供建议面消费。

## 差量清单

- 新增 `backend/app/core/hybrid_policy.py`（纯函数策略层，~460 行，零 IO）
- 改 `backend/app/services/action_allocation_policy.py`（X-02 v1.2，因子+G5+守卫分支+from_task 策略块投影）
- 改 `backend/app/services/task_service.py`（complete() 结算门前置，+1 import，diff 27 行全为本卡）
- 改 `backend/app/api/v1/chat.py`（guide_json 注入红化门+脚手架面）
- 冻结测试刻意更新 ×4（`test_action_allocation_policy.py`：精确集+G5、sha256 `c4fc…→e4c3…`、v1.1→v1.2 ×2 处）
- 新增 `backend/tests/unit/test_hybrid_policy.py`（29 测试）
- `v4/04_tasks/tasks.json`（I07 状态推进）+ 本证据五件套

## 自证边界

- 无 UI 交付（卡面无截图要求；移动端消费面归 UI 卡）
- 无真实模型调用（纯规则层，零 LLM）
- 零迁移、零新列、零 proto 改动（`guide_json` 版本化子键路径）
