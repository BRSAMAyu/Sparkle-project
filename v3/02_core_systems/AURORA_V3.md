# Aurora V3 — Adaptive Control + Relationship Layer

## 1. Runtime Contract
输入：`DecisionContext`
- goal state
- active action
- friction hypotheses
- current constraints
- relevant memories + provenance
- knowledge refs
- recent events/outcomes
- available tools/capabilities
- permissions
- budget / latency class
- proactive trigger (optional)

输出：`AuroraDecision`
- `intervention_type`
- `execution_mode` HUMAN|AGENT|HYBRID
- `rationale_summary`
- `evidence_refs[]`
- `uncertainties[]`
- `clarifying_question?`
- `action_proposal?`
- `tool_plan?`
- `memory_use_receipts[]`
- `policy_patch_candidate?`
- `cognition_tier`
- `no_action_reason?`

## 2. Intervention Catalog
- CLARIFY
- EXPLAIN
- RETRIEVE
- RESCOPE
- SPLIT
- SCHEDULE
- PRACTICE
- REVIEW
- DELEGATE
- EXECUTE
- CO_EXECUTE
- REFLECT
- CONNECT_PEER
- PAUSE
- REMIND
- ABSTAIN
- NO_ACTION

Catalog 是语义集合，不要求一类一个 Agent。

## 3. Decision Loop
`Observe → Check sufficiency → Build context → Select intervention → Allocate execution → Propose → Authorize → Execute/hand off → Observe outcome → Project evidence`

## 4. Bounded Plasticity
Aurora 可以保存 `PolicyPatchCandidate`：
- scope；
- intervention preference；
- evidence；
- confidence；
- expiry；
- user confirmed?；
- evaluation history。

只有白名单 policy surface 可生效；其他字段拒绝。

## 5. Relationship Experience
用户不直接看到策略引擎。他应该感受到：
- 记得该记的；
- 不乱提私事；
- 解释为什么；
- 被纠正后能变；
- 状态不好时更克制；
- 回归时恢复上下文；
- 做成事时庆祝成果而不是 streak。

## 6. Aurora UI receipts
每次重要个性化/干预可提供轻量 `Why this?`：
- “因为你今天只有 20 分钟”；
- “参考了你在这个项目里确认的偏好：先看示例”；
- “参考材料：OS.pdf …”；
并允许 `不相关 / 改一下 / 别再用这条`。

## 7. Low-stimulation mode
现有 dead-code 低刺激模式升级为 Aurora 的真实 UI policy：当用户明确开启或当前 context 满足用户已授权策略时：
- 减动画；
- 降强调色；
- 隐藏 streak/挑战性 gamification；
- 减少主动 CTA；
- 不静默推断“焦虑/心理问题”。

## 8. Evaluation
- intervention appropriateness；
- unnecessary clarification；
- no-action correctness；
- personalized rationale provenance；
- correction propagation；
- proactive precision；
- latency/cost per decision。
