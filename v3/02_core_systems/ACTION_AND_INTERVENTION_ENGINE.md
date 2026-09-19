# Action & Intervention Engine

## 1. Action Proposal
必须结构化：
- goal_id / action_id
- desired_outcome
- smallest_useful_step
- why_now
- friction addressed
- estimated_minutes
- completion_evidence
- execution_mode
- cognitive_ownership
- dependencies
- source_refs
- risk / reversibility
- fallback
- expiry/version

## 2. Smallest Useful Step
一个 step 只有满足至少一项才算 useful：
- 产生 artifact；
- 消除关键 uncertainty；
- 形成可验证能力；
- 解锁依赖；
- 完成真实决策；
- 使 goal state 实质前进。
“打开 IDE”“看 10 分钟”不是默认成功。

## 3. Authorization
Proposal 不等于执行。用户已授予的低风险自动权限才允许 auto-execute。其它写操作：proposal → confirmation → deterministic validation → execute → receipt。

## 4. Outcome
Action complete 必须尽量连接 evidence：文件、代码、答题结果、用户确认、自报结果、系统事件。区分 actual/self-reported/estimated/unknown。

## 5. Intervention selection
不要只优化 completion rate。一个把所有任务缩小到无意义的系统会高完成但低价值。评分至少包含：goal progress, feasibility, cognitive ownership, user preference, risk, time, expected information gain。
