# 全系统审查·第一轮 · 03 引擎关键服务与贝叶斯证据融合

- 审查员：3 号（切片：引擎·关键服务与贝叶斯证据融合）
- 基线：main@90daac8a（冻结工作树 wt3，只读审查，未改任何代码）
- 范围：`backend/app/services/evidence/` 全目录、`state_aggregator/`、billing 族（billing_worker/quota/shop_service）、记忆族 15 文件、LLM 族 9 文件、推送族 13 文件、鉴权族（user_service/auth_session_service/permission_service/gateway_client）
- 方法：evidence/ 与 billing/ 逐行深读，其余重点深读 + 通读；以针对性单元测试佐证。

---

## 1. 总评

这一片是全系统数据正确性最敏感的服务群，整体工程质量**中上**：贝叶斯融合核心（Kalman 1D + unbounded_mean 投影 + 置信度折扣）数学上是自洽且收敛的，商城购买链路（行锁 + 防负余额 + 双层幂等）是全仓最扎实的事务实现，配额 Lua 的 refund 有 current 钳制防超额。但存在**一个已由测试佐证的 P1 运行时断裂**（`LLMDispatcher` 访问不存在的 `chat_model` 属性，同步推理 gRPC 路径全灭），以及一批系统性隐患：billing worker 的 at-most-once 语义 + 崩溃即退出、日配额 Lua 滑动 TTL 破坏"日"语义、LLM fallback 链对 FREE 层的"向上降级"、temperature 参数被动态路由静默吞掉、推送侧三套偏好体系互不贯通 + recall 调度绕过静默时段、会话撤销可被 touch 复活的竞态。推送/记忆侧无 P0 级跨用户泄漏（语义缓存的隔离缺口属防御缺失而非现行泄漏路径）。

---

## 2. 发现表

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|---|---|---|---|---|---|
| E1 | **P1** | `backend/app/services/llm_dispatcher.py:520,63` | 任何经 `InferenceService.RunInference`（:50051）或 `task_service.py:1343` 的非 PREDICT_NEXT_ACTIONS 推理请求 | `_select_model` 访问 `llm_service.chat_model`，但 `llm_service.py:1519` 导出的单例是 `LLMSecurityWrapper`，**无 `chat_model`/`reason_model`/`__getattr__` 转发** → AttributeError；且 `_cache_key` 在 `run():63` 于 try 块之外调用 → gRPC 层兜底为 `PROVIDER_UNAVAILABLE`，同步推理全灭。`tests/unit/test_llm_dispatcher_quota.py` 2 用例基线失败即此因 | 见下方 diff |
| E2 | P2 | `backend/app/services/llm_service.py:592-617,836-848` | 调用方显式传 `temperature`（如 `conversational_extractor` 经 `safe_llm_json_call` 传 `temperature=0.0` 要求确定性抽取）且动态路由给出 selection | `_call_with_selection` 一律使用 `selection.config.temperature`，caller 传参被静默丢弃（chat 与 reason 两处同型） | `temperature=selection.config.temperature if temperature is None else temperature`（将 caller 值传入闭包） |
| E3 | P2 | `backend/app/services/llm/fallback.py:277-285` | FREE 层模型（`_try_llm_predict_next_actions` 首选即 `ModelTier.FREE`）或 TOP/GLM_BATCH/SPECIALIST 层失败进入 fallback | `tier_order = [MAX, PRO, PLUS, STANDARD, FAST, FREE_FAST, FREE_REASONING]` 不含 FREE/TOP/GLM_BATCH/SPECIALIST；`.index()` ValueError → `current_index=0` → 候选从 PRO/PLUS 起选，**免费层失败"降级"到昂贵层** | tier_order 补齐全部 ModelTier 并按成本降序排列；未知 tier 显式 fallback 到 FREE_FAST 而非 index 0 |
| B1 | P2 | `backend/app/services/billing_worker.py:138,189` | 宿主机/容器 TZ ≠ UTC 时（如 CST），带 `timestamp` 的账单落库 | `datetime.fromtimestamp(r["timestamp"])` 转本地时区 naive 值；无 timestamp 时回退 `_utcnow()`（UTC）→ 同表混用两种时区，日粒度计费归因可漂移 8 小时 | `datetime.fromtimestamp(ts, tz=UTC).replace(tzinfo=None)`（与 `_utcnow()` 对齐） |
| B2 | P2 | `backend/app/services/billing_worker.py:71,86-98,151-155` | DB 瞬断时批量 flush 失败且 `_retry_individually` 自身抛错（如建连失败）；或进程在 blpop 之后、flush 之前崩溃 | 记录已从 Redis `blpop` 弹出、仅存内存：`_retry_individually` 外层无兜底 → 异常传到 `start()` 的 `except Exception: raise` → **worker 进程退出且内存 batch 永久丢失**（at-most-once），需人工重启 | `start()` 内对 `_flush_to_db` 失败不 raise（退避后重试 + 未落库记录回推 Redis 或先写死信）；改用 `blpop`+处理回执（可靠队列）以获得 at-least-once |
| Q1 | P2 | `backend/app/services/lua/rate_limit.lua:17-18` + `quota.py` 调用方 | 活跃用户持续消耗日配额 | 每次成功 `incrby` 后 `expire key ttl`（86400）→ **TTL 滑动续期，key 永不过期跨日**：日配额从不重置；触及上限的用户须完全静默 24h 才能解锁（"daily"语义被破坏，方向是 fail-closed） | 固定窗口：首写时设 TTL（仅当 `ttl == redis.call('ttl', key) == -1` 时 expire），或 key 带日期后缀 |
| S1 | P2 | `backend/app/services/semantic_cache_service.py:200` | 调用方未传 `user_id` 调 `get()`（如 `get_cached_result` 默认 `user_id=None`，未来接线即触发） | `if user_id and payload.get("user_id") not in (None, user_id): continue` —— caller 为 None 时**不过滤任何用户的条目**，0.9 阈值语义命中可返回其他用户的个性化检索缓存 | 去掉 `user_id and`：`if payload.get("user_id") != user_id: continue`（严格同用户/同为匿名才可见）；或在 set 侧禁止 user_id=None 条目入语义索引 |
| P1' | P2 | `backend/app/services/push_delivery_service.py:218-225` + `user_push_opt_in_service.py:40-49` | 用户把静默时段设为非跨午夜窗口（如 12:00–14:00），或传入畸形 `HH:MM` | 公式 `current >= start or current < end` 只对跨午夜窗口正确：12:00–14:00 时并集为全天 → **静默时段配置导致永久免打扰**；`update()` 不校验格式，畸形值在投递时 `int(part)` 抛异常 | 若 `start <= end` 用 `start <= current < end`，否则用现公式；`update()` 校验 `^\d{2}:\d{2}$` 且 HH<24 |
| P2' | P2 | `backend/app/services/push_scheduler.py:155-196`；`push_service.py:381-404` | recall 队列处理（15 分钟周期） | `process_recall_queue` 直接调 `push_service._send_push`，**绕过 `process_user_push` 的静默时段/DND/频率上限/通知类型开关**；且 `_send_push` 中 `user.push_preference.last_push_time` 对无 `PushPreference` 行的用户 AttributeError → 推送静默失败（记 skipped_policy）且队列键被删 | recall 发送前复用 `_check_schedule_and_quiet_hours`/频率上限；`_send_push` 内 None 防护或沿用 `process_all_users` 的 JOIN 语义 |
| P3' | P2 | `push_service.py`（PushPreference）vs `user_push_opt_in_service.py`（UserPushOptIn）vs `notification_service.py:136-190`（NotificationPreferences） | 用户在「memory_settings/push-settings」关闭推送后仍收到 PushService 系通知，反之亦然 | 三套偏好模型互不检查：PushDeliveryService 只查 UserPushOptIn；PushService 只查 PushPreference；websocket 投递只查 NotificationPreferences。**opt-out 未贯穿所有推送路径** | 统一出口：`_send_push`/`create_and_push` 汇合点同时校验 UserPushOptIn.enabled（当前产品语义为 Aurora 推送总开关） |
| A1 | P2 | `backend/app/services/auth_session_service.py:79-100`；`app/api/deps.py:63,115` | 「登出其他设备」与目标设备在途请求并发：请求已过 `decode_token` 会话校验，随后撤销落库，再执行 touch | `upsert_session` 的 `update_fields` 含 `is_active: True, revoked_at: None` 并 `cache_service.delete(SESSION_REVOKED_PREFIX+sid)` → **已撤销会话被 touch 复活**（Redis 标记被删 + DB 标志复位）；`revoke_session` 的 Redis TTL 过期后仅剩 DB 兜底 | touch 路径不重置撤销状态：拆分 `touch`（仅更新 last_active/元数据）与 `upsert`（登录/刷新才允许复位 revoked）；删除 Redis 标记仅限显式重新激活 |
| M1 | P2 | `backend/app/services/memory_inferred_write_lane.py:80,322` | 用户触发写入限流（60s/10 条）时 | `_enqueue_degraded_candidate` 追加到类属性 `_degraded_queue`，**全仓无任何消费者** → 限流候选静默丢弃 + 进程内存无界增长 | 消费之（定时 flush 回写）或删除该队列只留 metric；至少加 maxlen |
| M2 | P2 | `backend/app/services/working_memory_consolidation_service.py:28-34,97-117` | 用户说"不对，这道题应该…"（纠正数学）等含宽泛拒绝短语的普通消息 | `REJECTION_PHRASES` 含"不对"，`handle_possible_rejection` 命中即撤回 L1 记忆，且目标取 **salience 最高**的已固化条目（`entries` 按 salience 排序）而非最近写入 → 可误撤无关重要记忆 | 拒绝判定加时间邻近约束（如最近 10 分钟内写入/提及的条目）+ 目标改取最近固化条目；"不对"需配合"记"类词共现 |
| M3 | P3 | `backend/app/services/memory_service.py:790,826` | pgvector 运行时缺失时 `create_episodic_memory` 降级 | except 仅捕 `SQLAlchemyError`；`tests/unit/test_memory_service.py` 两个向量降级用例以裸 `RuntimeError("vector.so unavailable")` 注入 → 基线失败（代码与测试对"可降级错误"的契约不一致） | 捕 `(SQLAlchemyError, RuntimeError)` 或复用 `NON_CRITICAL_SERVICE_ERRORS` 后再走 `_is_vector_runtime_error` 判定 |
| W1 | P3 | `backend/app/working_memory/service.py:220-245` | orphan 清理运行时 | 仅按 `session_id not in active_session_ids`（DB `is_active=True`）判定，**无视 `close_session` 写入的 `session_ended_at` 宽限期**；`json.loads(raw)` 无容错，坏 payload 会中断整轮 SCAN 循环 | 尊重宽限窗口；单条 payload 解析 try/except |
| L4 | P3 | `backend/app/services/evidence/fusion_engine.py:209-235` | `project_router_signals`（shadow 投影/RL trace） | `peek_variable(...) or get_variable(...)` —— `get_variable` 兜底会**创建缺失变量并写回 state**，读路径产生 mutation，默认值随后随 save_state 持久化 | 用只读兜底：`(peek or _default_variable(target))`，不落盘 |
| L5 | P3 | `backend/app/services/evidence/fusion_engine.py:477-499` | 同用户并发 `update_user_state` | load→fuse→save 无锁 RMW，Redis 单键并发写丢更新（后写覆盖前写） | Lua 小脚本内嵌融合不可行时，用 `SET NX` 短锁或 per-user 串行化队列 |
| L6 | P3 | `backend/app/services/evidence/fusion_engine.py:541-568` | bind outcome 与并发 append_trace 竞态 | `lrange` 取索引后 `lset`，期间并发 `lpush` 会使索引整体 +1 → outcome 写到错误 trace | 用 trace_id 定位（LRANGE 重读校验 trace_id 一致再 lset），或改 ZSET 按 trace_id 成员存 |
| M4 | P3 | `backend/app/services/memory_service.py:112-133` | 同用户同 pref_key 首次并发写入 | `SELECT ... FOR UPDATE` 锁不到不存在的行，两事务均得 `max_version=0` → 双 version=1 活跃记录，链断裂 | `(user_id, pref_key, version)` 唯一约束 + 冲突重试，或 advisory lock |
| M5 | P3 | `backend/app/services/ltm_release_gate.py:85-118` | 多进程/多 worker 部署下发布门控评估 | eval 分数与 job 成功率读**本进程** Prometheus 值与内存 `_JOB_HISTORY` → 门控可能因"看不到别的进程的失败"而误放行 | 指标改走中心化存储（Redis/DB 聚合）或明确单例运行约束 |
| N1 | P3 | `backend/app/services/notification_push_service.py:58-87` | 被偏好抑制的通知 | 通知先落库（未读）再做 `_should_push_notification` 抑制 → 被抑制通知仍出现在收件箱列表 | 决策先行：抑制时直接跳过落库或标记 delivered=false |
| U1 | P3 | `backend/app/services/permission_service.py:326-355` | ——（当前为死代码，无调用方） | 装饰器按 `kwargs.get('current_user', {}).get('id')` 取值，对 ORM `User` 对象必然 AttributeError；一旦被接线即 500 | 修复取值方式或删除死装饰器 |
| U2 | P3 | `backend/app/services/user_service.py:598-655` | ——（当前无调用方） | `update_user_profile` 对 updates 逐键 `setattr`，存在批量赋值面（is_active/hashed_password 等可被上游透传污染） | 字段白名单 |
| F1 | P3 | `backend/app/services/model_fallback_service.py:148` | 长驻进程单例 | `_performance_history` 只追加不修剪（`_get_recent_records` 过滤但不清存）→ 无界增长 | append 后按 performance_window 修剪 |
| F2 | P3 | `backend/app/services/semantic_cache_service.py:159,456` | invalidate 后 | `sadd(KEY_SET, ...)` 成员在 invalidate/clear 单键时不清理 → 集合含死键，`srandmember` 采样命中率被稀释 | invalidate 时 `srem(KEY_SET, cache_key)` |

### P1 修复建议（diff，未改代码）

**E1 — `llm_dispatcher.py` 访问不存在的 `chat_model`：**

```diff
--- a/backend/app/services/llm_dispatcher.py
+++ b/backend/app/services/llm_dispatcher.py
@@ -24,7 +24,7 @@
-from app.services.llm_service import get_configured_llm_service_for_tier, llm_service
+from app.services.llm_service import (
+    get_configured_llm_service_for_tier,
+    llm_service,
+    llm_service_impl,          # 裸 LLMService，含 chat_model/reason_model
+)
@@ -515,10 +517,10 @@
     def _select_model(self, request: inference_pb2.InferenceRequest) -> str:
         if request.task_type in (inference_pb2.HEAVY_JOB, inference_pb2.VERIFY_PLAN):
-            return llm_service.reason_model
-        return llm_service.chat_model
+            return llm_service_impl.reason_model
+        return llm_service_impl.chat_model
```

同时建议把 `run():63` 的 `self._cache_key(request)`（内部调用 `_select_model`）移入 try 块，或让 `LLMSecurityWrapper` 增加 `__getattr__` 透传路由元属性，防止此类属性再断裂。佐证：`tests/unit/test_llm_dispatcher_quota.py::test_dispatcher_refunds_*` 基线即因此 AttributeError 失败。

---

## 3. 验证良好清单（重点核对过、未发现问题）

**evidence 贝叶斯融合（数学正确性）**
- `belief_state.update_from_evidence`：confidence 钳位 [0.01,0.99]、观测方差 `(1-c)^2` 钳位到 `[variance_floor, MAX_VARIANCE]`、Kalman 增益分母恒正、方差收缩 `(1-K)*prior` 上下界完整；`unbounded_mean` 保留内部高斯后验、投影不回写，更新代数自洽（projection_diagnostics 可观测）。
- 时间衰减：half-life 语义正确（`1-0.5^(t/12h)`），方差上界 MAX_VARIANCE 收敛、均值向中性锚回缩，不会发散；past timestamp（elapsed<=0）跳过衰减。
- 同源相关折扣：同轮同源第 2+ 条证据置信度 `*0.85^group_index` + 方差下限 0.08，方向正确缓解序列更新独立性假设违背；`from_raw` 对 strength/confidence<=0 拒收，无 0/1 概率直塞、无 log 域下溢路径（实现完全在概率/方差域，未用 log）。
- `reward_model`：完成/放弃奖励钳位 [-2,5]/[-2,0]，难度加权、时长超限成本分量分离，weak_heuristic 标签不进训练（`training_eligible=False`）——防 reward 泄漏的 trace 绑定设计到位。

**billing / 配额**
- `shop_service.purchase_item`：`with_for_update` 行锁防超卖、`_update_balance` 防负余额、`IdempotencyKey` 表级幂等（PG/SQLite on_conflict_do_nothing + fingerprint 冲突 409）+ API 层强制 `Idempotency-Key` 头 + `TokenUsage.request_id` unique 兜底，购买/账本幂等闭环完整（除退款外的幂等面未发现新洞）。
- `rate_limit_refund.lua`：refund 钳制 `min(amount, current)`、current<=0 直接 no-op —— **双退款/跨日退款不会使配额超额**；`check_and_decr` Redis 故障 fail-open 是显式可用性取舍（已记录为风险而非 bug）。
- `billing_worker` 死信队列 + request_id 去重跳过 + 逐条重试，批量失败不阻塞合法记录（除 B2 的进程级缺口外）。

**记忆族**
- `mentioned_entity_hash = HMAC(key=user_id, name)`：人名实体哈希按用户加盐，Rule Z 无跨用户 join 边界守住了；`_is_duplicate` 按 evidence_token + semantic_key 双通道去重。
- `LtmRolloutService`：sha256 稳定分桶 + allowlist + cohort 三层，百分比钳位 [0,100]。
- `MemoryPolicyEvaluator`：无设置记录 → 默认允许（记忆产品默认开）、存在记录则按用户开关拒绝；`_ALIAS_MAP`/`_signal` 后缀双向展开覆盖推断键。
- 工作记忆条目键含 user_id+session_id，清理按 meta payload 的 user/session 删除，无跨用户误删路径（W1 是宽限期问题非越权问题）。

**LLM 分发**
- `llm_dispatcher._cache_key` 含 user_id + task_type + messages 全量 + model + schema → 精确缓存无跨用户泄漏；语义缓存主链路 `hybrid_search` 恒传 user_id（S1 为防御缺口）。
- quota 预扣/退款路径覆盖 CB 熔断、InferenceException、RpcError、未知异常四类（refund 有 current 钳制，最多少记不超扣）；`_try_llm_predict_next_actions` FREE→FREE_FAST 双层超时预算（1.5s/2.5s）+ wait_for 包裹 + rules 兜底候选，链路完整。
- `embedding_service`/`rerank_service` 双供应商切换 + 熔断器 + 失败回退原始顺序；DashScope batch≤10 分片。

**推送**
- `UserPushOptIn` 默认 `enabled=False`（默认不推，隐私默认值正确）；PushDeliveryService 投递前依次校验 kill switch、opt-in、分类开关、24h 频控、静默时段（P1' 为公式边界缺陷）。
- `push_sender_service` 对 UNREGISTERED/INVALID token 自动清理，防止死 token 重试堆积；FCM data 全字符串化。

**鉴权**
- `decode_token` 检查顺序正确：jti 黑名单 → 用户级 revoked_before（含 DB 回落）→ sid 撤销检查，先于 deps 的 touch（正常请求路径无复活；A1 为并发竞态）；token 黑名单查询失败在 prod fail-closed。
- `permission_service` 权限判定默认拒绝（非成员 False）；`can_mute_user`/`can_kick_user` 层级约束（不可禁言群主、admin 互不操作）正确。
- `gateway_client`：5s 超时、失败仅告警返回 False、无自动重试（无重试风暴风险）。

---

## 4. 测试执行记录

```bash
cd /Users/brsama/code/GitHub/Sparkle-sysrev/wt3/backend
export SECRET_KEY=<取自主检出 backend/.env>
/opt/homebrew/bin/pytest tests/unit -k "evidence or aggregator or billing or memory or llm or notification or push or user or permission" -q
# 结果：15 failed, 705 passed, 237 errors（206s）
```

- **237 个 ERROR 全部为 fixture 环境**：sqlite 测试库不支持 `accountability_partnership` 的 `Least/Greatest` 部分索引（`tests/unit/test_working_memory_consolidation.py` 等建表即炸），非产品缺陷。
- **与切片直接相关的真实失败（复跑确认，非环境）**：
  - `test_llm_dispatcher_quota.py::test_dispatcher_refunds_reserved_quota_on_provider_failure` / `test_dispatcher_refunds_unused_success_reservation` → `AttributeError: 'LLMSecurityWrapper' object has no attribute 'chat_model'`（= E1，P1）。
  - `test_memory_service.py::test_create_episodic_memory_falls_back_when_vector_runtime_unavailable` / `..._retries_without_embedding_...` → 裸 RuntimeError 未被 `except SQLAlchemyError` 捕获（= M3，代码/测试契约分歧）。
  - `spine/test_notification.py` 3 例 → `NameError: DomainPackMarketplace`（测试引用未定义符号，基线既有）；`stage37_llm_safety_kill_switch` 2 例 → 注入过滤行为期望分歧（kill switch 环境态）；其余失败（context_builder/spine_orchestrator/idiographic 等）与本切片核心链路无直接因果。
- 环境备注：冻结工作树缺 `app/gen`（gitignore 产物），先执行 `bash scripts/proto_toolchain.sh gen`（宿主 toolchain 回退；`make proto-gen` 被本机 Xcode license 阻断）后测试方可收集；未修改任何被 git 跟踪的文件。
