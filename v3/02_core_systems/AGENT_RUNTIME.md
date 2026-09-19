# Unified Agent Runtime

## 1. Agent 不是事实来源
Agent 只能通过 Tool Registry 读取/写入，所有 authoritative state 在确定性系统中。

## 2. Run State Machine
`QUEUED → RUNNING → AWAITING_USER/AWAITING_APPROVAL → EXECUTING → SUCCEEDED`
terminal：`FAILED / CANCELLED / TIMED_OUT / PARTIAL / UNKNOWN_OUTCOME`

## 3. Run contract
- run_id
- user/tenant
- objective
- context_snapshot/version refs
- allowed_tools
- permissions
- budget: token/cost/time/tool calls
- completion_condition
- risk_class
- status
- created/updated timestamps

## 4. Tool Call
- call_id / run_id
- tool name/version
- normalized args hash
- idempotency_key for side effect
- permission decision
- start/end
- provider/tool result
- receipt
- error class
- retry policy

## 5. Recovery
客户端不是 runtime owner。App 关闭后 run 继续或停在 awaiting state；重开按 run_id 查询。worker restart 通过 persistent state 恢复；不靠内存 future。

## 6. Cancellation
取消是状态变更 + 下游 cooperative cancel；已发生 side effect 不假装回滚，显示已完成部分和可补偿动作。

## 7. Existing OpenClaw
若现有 OpenClaw 有工具/执行价值，适配为 Runtime capability；禁止成为第二套 run ledger / permission / planner。

## 8. UI
长任务显示阶段而非 chain-of-thought：
- 正在读取材料
- 正在比较方案
- 等你确认
- 正在执行 2/4
- 已完成/部分完成
用户可后台离开、回来继续。
