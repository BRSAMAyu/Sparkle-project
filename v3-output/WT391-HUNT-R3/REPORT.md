# WT391 · 猎缺第 3 轮（双轮审查第一轮）REPORT

- base: `d105aa57`（分支 `wt391-hunt-r3`）
- 范围：今日下半场合入的 J-06 / J-07 / J-08 / S-04 / S-05 / P-04 / P-05 / wt380 Tier 三处修复
- 纪律：只找问题 + 可证伪判据；未改任何产品代码；探针在 `/tmp/wt391-probes/`（未入库），运行于 Sparkle-project backend venv
- 结论：**13 项**（P1×2、P2×5、P3×5、SPECULATIVE 1 项并入 F13）；探针实证 3 项（A/C/D）

---

## F1 · P1 · J-06 —— start 失败/长等待后，默认幂等键把任务永久钉死在死 run（旅程不可恢复）

- **面**：J-06 hybrid journey 并发/幂等
- **文件:行**：
  - `backend/app/services/hybrid_journey_service.py:419`（默认键 `hybrid_journey:{task_id}`）
  - `hybrid_journey_service.py:463-470`（prep 失败/`NoMaterialError` 在 run 已两次提交后才抛出）
  - `backend/app/services/agent_run_service.py:561-570`（`create_run` 内部 `commit()`）、`:655`（`transition` 内部 `commit()`）
  - `agent_run_service.py:2027-2034`（`_find_by_idempotency_key` 只过滤 `deleted_at`，不过滤状态）
  - `agent_run_service.py:212`（`DEFAULT_STALE_AFTER_SECONDS = 6h`）、`:1703-1710`（AWAITING_USER 心跳陈旧 → `UNKNOWN_OUTCOME(worker_restart_orphan)`，`wait_expires_at=None` 也逃不过）
- **机制**：prep 检索零命中（新用户常态）或工具失败时，run 已按默认键创建并迁移 RUNNING（各自内部提交）；异常抛出后重试 `start` 走幂等回放——永远 resolve 到这个无产物、无 awaiting 的死 run：`GET`/重试 start 回放空壳（201），`submit_judgment` 409（无 prep artifact），`confirm` 409。journey.py 无任何 cancel/restart 路由，run 级取消也不释放幂等键。第二面：产品语义「判断可等任意久」（`await_user_step` 传 `wait_expires_at=None`，`hybrid_journey_service.py:520-530/688-697`），但 recovery sweep 把心跳 >6h 的 AWAITING_USER 判 `UNKNOWN_OUTCOME` 终态——同样被默认键永久钉死。
- **触发**：①首次启动旅程时无材料 → 422 → 补传材料重试；②判断挂起 >6h 后任何人调 `/runs/recover`（admin sweep）。
- **分级**：P1（旗舰链路在常见流程中永久楔死，无用户恢复路径）
- **可证伪判据**：sqlite fixture 上 `start`（空检索结果）→ 422 no_materials；同参重试 `start` → `created=False` 且 `run.status=RUNNING`、artifacts 空；`submit_judgment` → 409 "journey has no prep artifact"。sweep 侧：AWAITING_USER + `heartbeat_at=now-7h` → `recover_stale_runs` → status=UNKNOWN_OUTCOME。

## F2 · P1 · J-06 —— confirm_outcome 半确认孤儿：完成戳先落库，complete_task 失败后重试谎报「已确认」

- **面**：J-06 outcome confirm 竞态/幂等
- **文件:行**：
  - `backend/app/services/hybrid_journey_service.py:806-809`（重试判据 = `outcome_step.completion` 存在）
  - `:820-829`（`complete_user_step` 在 resume 事务内提交完成戳 → run 回 RUNNING）
  - `:834-852`（`TaskService.complete_task` 在完成戳**之后**执行）
  - `backend/app/services/task_service.py:725`（`_validate_transition` 可抛）、`backend/app/api/v1/journey.py:329-330`（confirm 路由只捕 `HybridJourneyStateError`，其余 500）
- **机制**：`complete_user_step` 提交后若 `complete_task` 抛错（NotFoundError / 状态迁移校验 / DB 故障），重试 confirm 命中完成戳 → `_confirmed_replay` 返回 `receipt_type=hybrid_journey_completed`「交付已确认过（幂等回放）；不重复完成任务」——但任务从未完成、run 永停 RUNNING（永不 SUCCEEDED）、X-08 outcome 永不捕获、G-02 不点亮。客户端收到成功语义回执 = 静默数据丢失。
- **触发**：confirm 期间 `complete_task` 任意一次失败后的重试（含任务被并发软删：`db.get` 不过滤 `deleted_at`）。
- **分级**：P1（谎报成功）
- **可证伪判据**：monkeypatch `TaskService.complete` 抛一次 NotFoundError → 首次 confirm 500；再次 confirm → 200 且 `task.status != COMPLETED`、`run.status=RUNNING`、无 outcome 广播。

## F3 · P1 · Tier①（wt380 面）—— `extra_context.user_tier` 是客户端可控的 pro 车道提权通道（信号门的绕过面）

- **面**：wt380 Tier 塌缩修复①的信任边界
- **文件:行**：
  - `backend/app/services/agent_grpc_service.py:268-296`（`_resolve_request_user_tier`：`extra_context.user_tier/userTier` **覆盖**网关权威 `user_profile.is_pro`；wt380 后 camel 形态同效）
  - `backend/gateway/internal/handler/chat_orchestrator.go:56`（`chatInput.ExtraContext` 直接来自客户端 WS JSON）
  - `chat_orchestrator_chatflow.go:480-486`（网关只增量写入自己的键，不清洗客户端键）
  - `chat_orchestrator_chatflow.go:675-677`（`req.ExtraContext = structpb.NewStruct(input.ExtraContext)` 原样转发）
  - `backend/app/core/llm_router.py:453/:471`（free 钳制只看该 ContextVar）、`:120`（wt380②重排禁用也只看该 ContextVar）
- **机制**：任意登录用户在 WS chat 消息携带 `{"extra_context":{"user_tier":"pro"}}` → gRPC 层把 entitlement 权威判定覆盖为 pro → `set_request_user_tier("pro")` → free_tier_downgrade 钳制旁路 + 显式 pro 免疫自适应重排（付费模型成本与能力上限越权）。与 V3-FIX-02「权益只读独立字段」意图相悖；docstring 自述「供网关未来透传」，但网关从未清洗该键。缺陷为 wt380 之前既有（snake 形态当时已可达），wt380 修 camel 形态扩大了可达拼写。
- **触发**：单条 WS 消息字段，零工具。
- **分级**：P1（越权/成本面；任何认证用户可触发）
- **可证伪判据**：本地 gateway+engine，free 用户发送上述消息 → 引擎日志 `plan=pro`、无 free_tier_downgrade；对照不带字段 → `plan=free`。
- **探针 C（实证）**：`/tmp/wt391-probes/probe_tier_gate.py` — 门控输入仅为 ContextVar；gRPC 读取器对 snake/camel 两形态均解析出 "pro"。

## F4 · P2 · J-07 —— galaxy_graph 同族失效缺口：四处写路径只清 Redis、不宣告 shield（SHIELD-INVAL 同族扫描结论）

- **面**：J-07「同款模式还有没有」——galaxy_graph 等同族注册面
- **文件:行**：
  - `backend/app/services/node_sector_service.py:609-610`（`invalidate_user_graph_cache` 只删 Redis）
  - 调用点：`backend/app/services/galaxy_service.py:1515`、`:1540`；`backend/app/services/expansion_service.py:836`；`node_sector_service.py:454`（sector 分类/回填提交后）
  - `backend/app/services/galaxy/stats_service.py:265`（`spark_node` 学习解锁路径直接 `delete_pattern`，无 notify）
  - 对照正确实现：`backend/app/services/galaxy/outcome_absorption_service.py:641-644`（`invalidate_galaxy_graph_view_cache` Redis+shield 双层齐清）
- **机制**：`galaxy.py:78` 注释自述的失效模式「只清 Redis 层时 shield 仍回写前旧值（读面最长 10s 不更新）」——主会话修了 aurora comeback 的前缀缺陷，但 galaxy 同族仍有 4 个写面单层失效。aurora.py 的 comeback 修复本身（裸 user_id 前缀）核对无误；galaxy_graph 钩子前缀 `f"{user_id}:"` 与键格式 `f"{user_id}:{sector}:{locked}:{zoom}"` 匹配，无前缀缺陷。
- **触发**：sector 回填/expansion/spark_node 提交后 10s 内拉 `/galaxy/graph`（shield 命中旧缓存）。
- **分级**：P2
- **可证伪判据**：填充 shield 缓存 → 调 `NodeSectorService.invalidate_user_graph_cache` → `notify_read_view_invalidated("galaxy_graph", uid)` 返回 0，而 shield `_cache` 条目仍在、TTL 内读回旧值。

## F5 · P2 · J-08 —— 里程碑↔任务按位置对齐：中间任务缺失即错位归属（探针实证）

- **面**：J-08 goal_trajectory milestones 环
- **文件:行**：
  - `backend/app/services/goal_trajectory_service.py:237-241`（`milestone_tasks[index]` 位置配对，无 id 关联）
  - `backend/app/api/v1/goals.py:222-252`（里程碑任务创建失败 `except Exception: pass` 吞掉 → 天然制造缺位；`GoalMilestonePayload.id` 未持久化到任务侧）
- **机制**：wizard 里程碑列表按 `created_at` 序的任务行做**位置 join**。任一里程碑任务创建失败/被删除/重排，后续全部错位一位：达成状态归属错误。
- **触发**：建目标时任一任务创建失败（被设计吞掉）、用户删除里程碑任务、replan 重建任务。
- **分级**：P2（成长叙事面呈现错误事实）
- **可证伪判据 / 探针 A（实证）**：`/tmp/wt391-probes/probe_milestones.py` — 3 里程碑、第 2 个任务缺失 → 输出 `m2 reached=True`（实为 m3 任务完成）、`m3 reached=False`，断言全过。

## F6 · P2 · S-05 —— leave/kick 实时关闭无补偿：kick publish 失败 = 非成员连接永久收群广播

- **面**：S-05 修复后的 WS 关闭竞态（广播与 kick 的顺序窗口的**实质问题**）
- **文件:行**：
  - `backend/app/api/v1/community.py:2063-2090`（leave：commit → broadcast → kick 顺序；`:2172-2176` kick 同构）
  - `backend/app/core/websocket.py:299-315`（`kick_user_from_group` 依赖单次 Redis `publish`；`:324-334` `_broadcast_local` 不复检成员行）
  - `community.py:1795-1804`（群 WS 端点仅 connect 时校验成员资格，收包循环零复检）
  - `backend/app/services/community_service.py:925`（`leave_group` 幂等挡死重试：非成员 → ValueError → 400）
- **机制**：成员行删除提交后，唯一关闭手段是 kick_group publish（广播与 kick 同 channel，Redis 保序，正常路径无乱序）。但 publish 失败（Redis 瞬断）→ 500（成员行已提交）→ 事后重试 leave/kick 一律 400「不是群组成员」→ 已退成员的存活 WS 永久挂在 active_connections 持续接收群广播——正是 S-05 要堵的隐私缺口，且无对账/无广播前复检/无补偿重试。
- **触发**：leave/kick 请求瞬间 Redis 不可达。
- **分级**：P2
- **可证伪判据**：monkeypatch `redis.publish` 抛 ConnectionError → leave 500；二次 leave 400；该 WS 仍收到后续群广播帧。

## F7 · P2 · P-05 —— 评估 runner 事件侧通道未隔离：sqlite 真源隔离成立，但 event bus 指向真实 dev Redis（DLQ 还指真 Postgres）

- **面**：P-05 backdate 时钟手法对生产路径的污染风险
- **文件:行**：
  - `backend/tests/proactive_longitudinal/engine.py:313-329`（只重定向 `AsyncSessionLocal`；apply_clock 的回写全部落隔离 sqlite，DB 面隔离成立）
  - `scripts/devtools/p05_run_proactive_longitudinal_eval.py:31-33`（仅设 `SECRET_KEY`/`EVENT_BUS_MAX_RETRIES`，不动 REDIS_URL、不 stub event_bus）
  - `backend/app/core/event_bus.py:972-980`（`_publish_once` redis 为 None 时**自动 connect `settings.REDIS_URL` 并 XADD `sparkle_events`**）
  - `event_bus.py:1126`（publish 失败 DLQ 落库走真实 DB 工厂）
- **机制**：`TaskService.complete → capture_task_outcome → emit_outcome_recorded` 等真实链路在 runner 进程内向真总线 publish：本机 make dev-up（Redis 可达）时评估事件（伪 user uuid、回拨时间线）写进真实 dev Redis stream；本地 consumer 在跑则继续进 dev Postgres 读模型（galaxy 点亮/账本/投影）。Redis 不可达时 DLQ 路径改指真 Postgres。backdate 本身不污染，污染面在事件通道，runner 零隔离零断言。
- **触发**：在配置了可达 REDIS_URL 的机器上无人值守跑 P-05 runner。
- **分级**：P2
- **可证伪判据 / 探针 D（实证）**：`/tmp/wt391-probes/probe_bus_escape.py` — stub connect 后 `_publish_once` 确以 `settings.REDIS_URL = redis://127.0.0.1:6379/0` 发起连接；失败回退日志实证 DLQ 尝试写真实 Postgres（auth failed，未写成）。XRANGE 前后对照可终验。

## F8 · P3 · J-06 —— LLM 失败重试后判断产物行丢失（审计链洞）+ 重试可换 refs 而持久化判断记录仍是首次选择

- **文件:行**：`hybrid_journey_service.py:617-644`（`complete_user_step` 内部 commit 先于 `db.add(judgment artifact)+flush`）；`backend/app/db/session.py:126-129`（get_db 异常回滚已 flush 未提交行）；`:610-611`+`:648`（replay 时 `chosen` 取自本次请求 refs）
- **机制**：check/生成失败 → 503 → 回滚：判断**步戳**已提交而 judgment **产物行**丢失；重试 `replay=True` 不补写产物 → prep→judgment 产物链缺环。且重试可提交不同 `selected_refs`/`focus_note`，草稿按新选择起草，而持久化判断戳/产物仍是首次提交——审计记录与实际交付可分叉。
- **触发**：首次 `submit_judgment` 遇 JourneyGenerationError/JourneyCheckError 后重试（换选集）。
- **分级**：P3
- **可证伪判据**：fixture 中 llm_chat 首次抛错 → 503 → 查库 judgment 产物行缺失；二次以不同 refs 提交 → 200，且 execute_check 产物 citations ≠ judgment 步戳 artifact_refs。

## F9 · P3 · S-04 —— 并发 adopt/give 竞态 → 500（幂等仅串行成立）+ retract/adopt 交错留下「已撤回资源上的 adopted 证据」

- **文件:行**：`backend/app/services/community_feedback_service.py:251-259`（adopt 幂等 = 读 `adopted_at` 后无锁无 CAS）、`:117-124`（give upsert 同型）；`backend/app/models/community.py:601`（`uq_sr_feedback_resource_user`）、`:630`（evidence `feedback_id` 唯一）；retract 交错：`community_feedback_service.py:371-396`（retract 读集与 adopt 写集无锁交错）
- **机制**：双击/双设备并发采纳：双双通过 `adopted_at is None` 检查 → 证据 INSERT 撞唯一锚 → 后者 IntegrityError 500 整事务回滚（outbox 序列号被消费 → 序号空洞）；give_feedback 并发同构 500。另一窗口：adopt 通过 retracted 检查后 retract 提交 → adopt 再提交 → feedback 已 retracted 而 evidence 行停留 adopted（retract 的 evidence 更新查询先于该行插入执行）。
- **触发**：并发双击采纳/反馈；撤回与采纳毫秒级交错。
- **分级**：P3（约束兜底无脏数据，但幂等承诺在并发面破形态、可产生状态分叉）
- **可证伪判据**：两线程同 feedback 并发 `adopt_feedback` → 恰一成功、另一 IntegrityError 500；retract-adopt 交错后查 `CommunityOutcomeEvidence.status='adopted'` 且所属 SharedResource.deleted_at 非空。

## F10 · P3 · J-07 —— plans.py 双写路径失效宣告完整性清单（问句回答：还有哪些写路径没宣告）

- **已宣告**：`plans.py:1398`（replan）、`:1272`（update_plan 仅 target_date 变化时）。
- **未宣告但 comeback 读面消费**（`aurora/runtime_v1/service.py:414+` 读 `Plan.is_active`/`target_date`/未完成任务/逾期）：
  1. `plans.py:1229` `phases/{id}/schedule/regenerate`（时间窗=deadline 写）
  2. `plans.py:1246+` update_plan 的 `is_active`（`schemas/plan.py:39`）——停用/启用计划不宣告
  3. `plans.py:924` advance-phase、`:1412` generate-tasks、`:1524` archive、`:1661` restore、`:1471` delete
  4. 任务级全谱：完成/改期/删除（tasks API 与 `TaskService.complete`；J-06 `confirm_outcome` 完成任务同样不宣告）
- **后果封顶**：comeback shield ttl=8s 陈旧窗口，危害有限；但同一失效域内「replan/target_date 宣告、其余不宣告」的双标本身是债。另：`aurora_status.py` control_surface（ttl=8s）、`predictive_analytics.py` realtime-next-step、`aurora.py` core_session 三个 shield 完全无失效钩子（TTL-only 既有设计，登记为观察）。
- **分级**：P3
- **可证伪判据**：archive 计划后立即拉 comeback-context → 8s 内返回旧 plan 建议且 `notify` 计数无变化。

## F11 · P3 · P-04 —— 五条件门三处边界

- **a) 判定/重入不重验 `auto_eligible`**：`action_authorization.py:73+` 判定只用存储 grant+当前风险标志；grant 后 handler 部署翻转 `auto_eligible=False`（reversible 不变）→ 既有 grant 继续直通 auto。「授权后命令 schema 变更」问句的答案：资格只在 grant 入口校验（`action_permission_service.py:84`），判定面不复验。判据：grant 后改 handler 资格位 → `create_proposal` 仍 mode=auto。
- **b) 首次 inline 执行无 revoke 复核**：`action_command_service.py:161`（判定）→ `:236`（approve 直通）复用同请求早前判定值；`_resume_or_replay:684` 有复核但只覆盖重入。窗口=同请求内毫秒级。判据：判定读真源与 approve 之间并发 revoke → auto 仍执行。
- **c) `explicit` JSONB 整文档读-改-写无锁无 CAS**：`action_permission_service.py:214-236`（`increment_version` 只加不查）→ 并发 grant/revoke、或与 P-03 mute 同行键并发写 = 丢更新（last-writer-wins 整文档）；危险方向为并发 revoke 被再授予覆盖。判据：两个交错 session grant(A)/revoke(B) → 终态只保留其一。
- **分级**：P3（b、c 有实际并发面；a 需部署动作）

## F12 · P3 · J-08 —— 轨迹读面：账本 200 条扫描上限 + Galaxy 环 N+1 + 无 shield 暴露于恢复风暴族

- **文件:行**：`goal_trajectory_service.py:55-56`（`_LEDGER_SCAN_LIMIT=200`；`_ledger_task_index` 只取最前 200 条 task_completion）→ 历史完成 >200 条的用户，老目标 outcome 恒 `ledger_verified=False`、`outcomes_formed` 少计；`:457-466`（每节点 2 次 point SELECT，最多 20 节点=40 查询/请求）；`/journey/trajectory` 无 EndpointShield/缓存（移动端 Goal 页拉取面）。
- **触发**：长期用户 >200 完成项后查看早期目标轨迹；恢复风暴并发拉 Goal 页。
- **分级**：P3
- **可证伪判据**：>200 条账本条目的用户，早期任务 outcome `ledger_verified=false` 而账本直查命中。

## F13 · P3（SPECULATIVE）· J-06 —— ABANDONED 任务仍可确认交付：正向 outcome 记到已放弃任务

- **文件:行**：`hybrid_journey_service.py:837`（`not in (COMPLETED, ABANDONED)` 才完成；ABANDONED 分支继续走 run SUCCEEDED + `build_run_receipt_outcome` 正极性 outcome）。
- **机制**：任务锚被放弃后，用户确认交付 → 交付回执照发、positive outcome 落账。若产品语义是「确认交付=该任务真实完成」，ABANDONED 不应放行。
- **触发**：旅程进行中任务在别处被放弃，随后 confirm。
- **分级**：P3 / SPECULATIVE（产品意图可能允许「交付即复活」，需产品判读）
- **可证伪判据**：任务置 ABANDONED → confirm_outcome 200 → outcome ledger 出现该任务正极性条目。

---

## 已排除的怀疑（查证后不成立，防二轮重复劳动）

- galaxy_graph 钩子前缀 `f"{user_id}:"` 与 run 键格式匹配（`galaxy.py:84` vs `:237`）——前缀无缺陷，缺的是**其他写面的 notify 缺失**（F4）。
- `confirm_outcome` 的 outcome artifact 悬空怀疑不成立：`transition(SUCCEEDED)` 内部 commit 会把已 flush 的产物一并落库；`emit_outcome_recorded` 内部全捕获（`outcome_capture_service.py:191-195`）。
- `_adaptive_reorder_allowed` 的 deep/pro 判定本身逻辑正确（探针 C）；问题在输入源可信度（F3）。
- J-08 权限面：goal/plan/task/artifact/reflection/galaxy 各环查询均带 user 归属过滤，**未发现跨用户读轨迹通道**（`_reflections_face` 无 user_id 但 task_ids 已归属约束）。
- wt380 task_manager ContextVar 修复语义正确（`copy_context` + `create_task(context=)`）；`agent_grpc_service.py:517` 在 finally 复位 token，无泄漏。celery worker 侧 ContextVar 不跨进程传播属设计（任务显式传参），未发现依赖隐式传播的读面。
- journey.py 四路由错误映射完备；`MissingIdempotencyKeyError` 在 confirm/judgment 由 Pydantic `min_length=1` 前置拦截，不可达。

## 探针清单

| 探针 | 位置 | 结论 |
|---|---|---|
| A 里程碑位置对齐 | `/tmp/wt391-probes/probe_milestones.py` | CONFIRMED（m2 错误 reached=True） |
| C tier 信号门 | `/tmp/wt391-probes/probe_tier_gate.py` | CONFIRMED（门控=ContextVar；双形态解析） |
| D event bus 侧通道 | `/tmp/wt391-probes/probe_bus_escape.py` | CONFIRMED（自动连 dev Redis；DLQ 指真 Postgres） |

探针未入库（会话产物不入库纪律）；复跑命令见各文件头注释（需 `SECRET_KEY` 环境变量）。
