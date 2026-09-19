# Entity Map — Expected Contract, Not Repository Truth

> B-06 负责在当前 HEAD 生成最终实体映射。本文件只告诉 Agent 要找什么，避免新建同名系统。

| V3 concept | 优先寻找现有区域 | 规则 |
|---|---|---|
| Current State | models / state_aggregator / task/plan/goal | DB/业务服务为真值 |
| Memory | working_memory / evidence / personalization / learning | 先复用五层模型 |
| Knowledge | RAG / documents / pgvector / galaxy | 与 User Memory 隔离 |
| Events | CQRS outbox/event store / logs | telemetry 不是业务真值 |
| Aurora | backend/app/aurora | extend，不另造 Controller 服务 |
| Context | orchestration/context_builder/UserStateV1 | 单一 ContextPack contract |
| Action/Task | card_protocol/task services | 保留可信写入协议 |
| Agent Run | agents/openclaw/attempt/receipts | 收敛成唯一 run truth |
| Outcome | evidence/task/artifact | D-02 选定唯一 ledger |
| Entitlement | 查当前 account/subscription/profile | 必须脱离 flame_level |

找不到并不自动意味着“创建新表”；先证明为什么现有对象不能扩展。
