# Memory V3 — 从“记得”到“用得对”

## 1. Memory Record
建议最小字段：
- id / user_id
- type: FACT|CONFIRMED_PREFERENCE|OBSERVATION|HYPOTHESIS|EXPERIENCE
- canonical content / structured payload
- source_refs[]
- scope: global / goal / domain / task_type / time window
- created_at / observed_at / valid_from / expires_at
- status: candidate / confirmed / active / superseded / revoked / expired
- confidence / evidence_strength
- sensitivity / allowed_purposes
- correction_count
- supersedes_id?
- memory_epoch

## 2. Write policy
不是每轮聊天都写 Memory。
先 storage gate：
- 未来可能改变 decision 吗？
- 是稳定信息还是一次性状态？
- 其 scope 能定义吗？
- 有来源吗？
- 是否敏感？
- 是否需要用户确认？

Transient state 写 Current State/Event，不污染长期 Memory。

## 3. Retrieval pipeline
1. identity / tenant filter
2. status filter
3. purpose & permission
4. scope compatibility
5. TTL/freshness
6. conflict/supersede resolution
7. semantic retrieval / embedding
8. rerank by decision utility
9. over-personalization Self-ReCheck
10. context budget
11. emit `MemoryUseReceipt`

## 4. Over-personalization Guard
至少检查：
- IRRELEVANCE：不用也能正确回答时是否硬提历史？
- REPETITION：近期是否反复提同一偏好？
- SYCOPHANCY：偏好是否让回答无原则迎合？

允许 recall 但决定 `do_not_surface`；Memory 可以帮助内部选择而不必在文本里点名。

## 5. Experience Memory
核心 payload：
- situation signature
- intervention
- execution mode
- outcome
- user feedback
- context boundary
- repeated evidence count

不宣称因果；默认是“过去在相似情况下相关/有效”。多次一致 outcome 才提高 evidence strength。

## 6. Correct / Delete
纠正：保留 provenance，旧条目标 superseded/revoked，新条目引用 correction event。
删除：
- source of truth status revoke/delete；
- bump memory_epoch；
- invalidate semantic cache/context cache；
- retrieval 必须硬过滤；
- in-flight run 在敏感删除时重新授权/重编 context；
- derived summaries/profile 不得把已删信息复活。

## 7. User-facing control
页面不叫“Memory Engine”。
分：
- `你告诉我的`
- `我根据使用情况观察到的`
- `我还不确定的`
- `对你有效过的方法`
每条可查看来源、适用范围、修改/删除/只在此项目使用。
