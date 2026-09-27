# WT634 · Round-2 独立复验裁决（V3-FIX-333/334/335/336）

- 工位：wt634 ｜ 轴：round-2 独立验证（对 wt631 round-1 四条发现逐条亲证，不信任其 file:line）
- 基线：main 头 `b03fb358`（分支 `agent/node-b/wt634/verify2` worktree）
- 日期：2026-09-27 ｜ 方法：只读对码 + 全仓 grep + sqlite in-memory 运行级红测（未起栈、未改任何产品代码）
- 裁决汇总：**333 CONFIRMED ｜ 334 CONFIRMED ｜ 335 CONFIRMED ｜ 336 CONFIRMED（含运行级实证）**
- round-1 行号锚点抽验：绝大多数精确命中（269/379/516/41/123/57/264 全对）；三处小偏移已在本文明示（不影响任何语义结论）。

---

## 1 ｜ V3-FIX-333（runtime probe 未兑现）—— 裁决：**CONFIRMED**

逐处亲证（本次打开的行号即当前 HEAD 的行号）：

| 处 | 亲证证据 | 结论 |
|---|---|---|
| LLM | `backend/app/core/llm_router.py:269` `is_healthy: bool = True`（精确命中）。三相滞回（healthy/unhealthy/probation）状态只能经 `record_failure`/`record_success`/`check_recovery` 变更——三者全部由真实流量的成败回调驱动；`check_recovery`（unhealthy→probation）仅判冷却时间流逝，**不发出任何探测流量**；probation 相内 `is_healthy=True` 只是重新放行真实流量。全文件无启动期/定时 probe（grep probe/ping/health_check 无主动探测命中） | 缺省健康 + 纯被动熔断，属实 |
| embedding | `backend/app/services/embedding_service.py:123` `def provider_status`，`:131`/`:137` `"configured": bool(self.dashscope_api_key)` / `bool(self.siliconflow_api_key)`；`:152` `is_configured() = any(...)` | 键非空即宣称，属实 |
| STT | `backend/app/services/stt_service.py:50-84` `_build_provider`：bailian `:55`、zhipu `:62`、xunfei `:69-77` 均只做 `_is_configured_value`（`:86-87`＝非空字符串）判定，通过即构建 provider；`_should_try_backup` `:96-115` 是请求期事后错误串匹配换备 | 键非空即宣称 + 事后换备，属实（round-1 锚点 `:78` 是 xunfei 的 return 行，语义成立、锚点偏松） |
| TTS | `backend/app/services/tts_service.py:149` `if settings.DASHSCOPE_API_KEY and settings.DASHSCOPE_API_KEY.strip(): self.provider = BailianTTSProvider()` | 键非空即宣称，属实 |
| OCR | `backend/app/services/ocr_service.py:57-61` `_provider_configured`＝`bool(self.api_key)`/`bool(self.siliconflow_api_key)`，执行前配置检查 | 键非空即宣称，属实 |
| body-map | `backend/app/services/capability_registry_service.py`：`"state": "active"` 硬编码在 `:32/:54/:65/:76/:87/:98/:109`（round-1 记 `:33`，实为 `:32`，差一行）；仅 openclaw `:43` 按 settings 置 configured/not_configured。`backend/app/api/v1/multi_agent.py:259-264` GET `/body-map` → `build_registry()`（`capability_registry_service.py:162`）将 `subsystems` 原样对外 | 硬编码 active 对外，属实 |
| 正证据 | 真探活确在别处：`backend/app/adapters/openclaw/client.py:183-200` `_probe_http_execution_capability` 真实 HTTP POST `/v1/responses`、失败置 reachable=false；`backend/app/services/task_optional_capabilities.py:46` 表级探测 | 承诺面（5 族能力）确未使用真 probe |

**裁决**：五能力族（当前模型/embedding/STT/TTS/OCR）的可用性判定全部为「配置存在性 + 被动流量熔断」，无主动 probe；registry 对外宣称硬编码。round-1 发现成立。量级评估（S-M：补 probe 或 ADR 降级口径）同样成立。

---

## 2 ｜ V3-FIX-334（可恢复 Run chat 轨 TTL 互斥断裂）—— 裁决：**CONFIRMED**

### 2.1 三个 TTL 真实数字（本次亲证）

| 层 | 锚点 | 数字 |
|---|---|---|
| 网关去重 | `backend/gateway/internal/service/chat_history.go:316`（`ttl <= 0 → time.Hour` 兜底）+ 调用点 `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:347` **显式传 `time.Hour`** | 60 min |
| 检查点恢复窗 | `backend/app/orchestration/statechart_engine.py:379` `max_age_seconds=30 * 60` | 30 min |
| 响应缓存 | `backend/app/orchestration/state_manager.py:516` `ttl: int = 300`（全仓所有写侧调用均走默认值：`session_state_mixin.py:926-930` 包装器、`execution_engine.py:285/539/588/1591`、`orchestrator.py:1408/3445/3856`，无一处覆写） | 5 min |

排序 1h > 30min > 5min 确认。

### 2.2 「同 request_id 重发先被网关弹掉」控制流（亲证调用链）

WS 入口（legacy `chat_orchestrator.go:586`、envelope `:631`/`:664`、protocol `chat_orchestrator_protocol.go:645`）→ `handleChatMessage`（`chat_orchestrator_chatflow.go:293`）→ **去重检查 `:347-367` 在先**：`TryAcceptRealtimeRequest` SetNX `ws:chat:request:{user}:{req_id}`；未接受 → 先 `sendChatAccepted` 再三路 responder 发 `duplicate_request`（retryable=false，`:358-364`）并 `return false`；**Redis 读写出错 → 仅打日志继续放行（fail-open，`:349-351`）** → 通过后才到 gRPC 桥 `StreamChatWithFallback`（`:723`）。`req.RequestId = reqID`（`:679`）——request_id 原样传引擎，引擎侧等值判据本可命中，但请求根本到不了引擎。**结论：Redis 正常时，60 分钟内同 id 重发永不及引擎；确认。**

### 2.3 客户端换新 id（亲证）

`mobile/lib/features/chat/presentation/providers/chat_provider.dart:1442` `final attemptRequestId = isRetryAttempt ? '${runId}_r1' : runId;`（round-1 记 1444-1449，实际 1442；`:1425-1440` 注释块明言「gateway dedups exact (user, request_id) pairs for 1h…a literal same-id resend would bounce」——换 id 是**刻意设计**）。新 id → `redis_checkpointer.py:168` `data.get("request_id") != request_id → None` 等值判据必失配 → 客户端唯一常态重试路径**从不走进恢复链**。确认。

### 2.4 响应缓存读侧死路（全仓 grep 亲证）

`get_cached_response`/`is_duplicate_request` 生产读调用**仅一条链**：`session_state_mixin.py:905 _check_idempotency` ← `validation_engine.py:271 _check_idempotency_response` ← `orchestrator.py:2224`（引擎 intake）。`is_duplicate_request` 生产调用为零（仅 `tests/orchestration/test_fsm_state_real.py:167-170`）。写侧照常写入（7 处，多于 round-1 所列 3 处——**写多读少的结论不变、读侧死路结论不变**）。

### 2.5 修复裁决草案（去重命中改返结果/状态而非弹错）

**推荐方案（a）：去重命中 → 网关向引擎查此前尝试的结果/状态，可回放则回放，不可回放才落 duplicate_request。**

触面清单（文件 + 函数）：

1. **契约**：`proto/agent_service.proto` 新增一元 RPC，建议 `rpc GetRequestResult(GetRequestResultRequest) returns (GetRequestResultResponse)`（入参 user_id/session_id/request_id；出参 status: running|completed|unknown + 完整响应体）；随后 `make proto-gen`（硬规则 1，两侧 gen 同步）。
2. **引擎侧**（新 handler，挂 AgentService gRPC 实现）：
   - 结果读取两条既有通道二选一或并用：响应缓存 `state_manager.get_cached_response(session_id, request_id)`（`state_manager.py:538`，需先做 2.4 的 TTL 提升）；run ledger 按 session 索引解析 `RunLedgerStore.session_key(session_id)` → `load_summary`（`run_ledger.py:134`）→ `summary["request_id"]`（`:73`）等值校验 → status/最终文本（`:248` completed 判定已在）。
3. **网关侧**：`chat_orchestrator_chatflow.go handleChatMessage` `:354-366` 的 `!accepted` 分支——发 duplicate_request 之前先调新 RPC：completed → 以原 request_id 回放最终响应帧；running → 发 ack/状态帧（客户端继续等）；unknown/引擎不可达 → 保留现 duplicate_request 兜底（`legacyStreamErrorPayload` 帮助函数与既有错误帧格式不动）。
4. **TTL 对齐**：`state_manager.py:516` 默认 ttl 300 → ≥3600（与去重窗等长），或在 `session_state_mixin.py:926 _cache_response` 显式传参；checkpoint 恢复窗 30min 是否同步拉长为独立裁决（非本卡阻塞项）。
5. **mobile（增量 1 可不动）**：`chat_provider.dart:1442` 的 `${runId}_r1` 派生是针对「守卫超时后首发可能已死」的救援语义，可保留；网关能回放后，「断线重连同 id 重发」成为可行路径，属增量 2。

**测试影响评估**：
- Go：`chat_history_contract_test.go:20`（service 层 SetNX 语义）不受影响；`chat_stream_error_test.go:85` 只测 `legacyStreamErrorPayload` 纯函数，兜底路径保留则不红；需新增回放路径的 handler 契约测试（completed 回放/running ack/unknown 兜底三态）。
- Python：新增 RPC handler 需新测试；`tests/orchestration/test_fsm_state_real.py:167-170` 断言与 TTL 数值无关（写后立即读回），TTL 改动不碰红。
- 契约：proto 变更走 `make proto-gen` + 契约检查（验证与夜间执行节）。
- 备选方案（b，弱）：网关 TTL 1h → ≤30min 对齐恢复窗，仅恢复「恢复链可达」，不能回放已完成结果，不推荐单做。

---

## 3 ｜ V3-FIX-335（executable_plan 不入 checkpoint）—— 裁决：**CONFIRMED**

- `backend/app/checkpoint/redis_checkpointer.py:41`：`"executable_plan"` 在 `KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS`（精确命中）；`save()` `:70-73` 对清单内 key 直接 `continue` → 计划对象**结构性不入 checkpoint**。文件头注释 `:20-25` 自认「恢复面安全：全部消费点……按需重建计划」。
- 恢复后重建换键路径：`statechart_engine.py:371-390` `_load_interrupted_checkpoint` 合并存档态（无计划）→ `standard_workflow.py:1508-1515` `generation_node` 判 `executable_plan` 缺失 → 重跑 LLM 规划 → 新 `plan_id`/新 `spec.id`（执行器键源，见 §4.2）→ 中断前已执行写工具在恢复后持新键再次执行。
- 与 336/334 的组合（334 断重入通道、336 键尝试唯一、335 计划不入档）叠加路径完整成立。

**裁决**：CONFIRMED（静态证据链完整；其实害通道已由 §4.3 运行级红测实证——凡产生新键的重入即复现）。

---

## 4 ｜ V3-FIX-336（幂等键尝试唯一非意图稳定）—— 裁决：**CONFIRMED（含运行级实证）**

### 4.1 执行器幂等机制本身严密（round-1 翻案正确，亲证无缺口）

- 强制闸门：`backend/app/orchestration/executor.py:515-524`——effect=write 无 key（显式 `idempotency_key` 或 `tool_call_id`）即 `IdempotencyKeyRequired`（`:521`，fail-closed）。
- 同键语义：`:556` args_hash 不符 → `IdempotencyArgsMismatch`；`:564` 前次 in_progress → `IdempotencyConflict`；`:576` 前次 interrupted → `IdempotencyInterrupted`（同键重放恒拒，注释明言「重试必须换新幂等键——那是显式决策」）；succeeded/failed → `replay_result` 重放不重执行；账本不可读 → `LedgerUnavailable`（`:546`）。
- 并发窗口：`:644-663` 捕 IntegrityError，按 Postgres 约束名 `uq_agent_tool_calls_idem` 或 SQLite 列三元组判定撞唯一索引 → fail-closed `IdempotencyConflict`。唯一索引在 `backend/app/models/agent_tool_call.py:77-85`（部分唯一索引，PostgreSQL/SQLite 双 variant）。
- 有界重试：`executor.py:1635-1648` docstring + `:1696` 派生键 `{spec.id}:retry:{attempt}`，仅 side_effect_state=none 进入；`agent_tool_call.py:43` 封闭状态词表。
- DoD 五件套对账：`agent_tool_call.py:53-66` run_id/tool_call_id/idempotency_key/args_hash/permission_decision/result/execution_time_ms 全在；**调用级 cost 列不存在**（run 维度聚合代偿）——按字面部分兑现，与 round-1 一致。

### 4.2 键源全部尝试唯一（亲证）

- chat 轨直执行：`backend/app/agents/standard_workflow.py:2774` `tool_call_id=tc.tool_call_id or str(uuid.uuid4())`——模型 call id 本轮唯一、uuid 每次全新。
- bridge 轨：`backend/app/orchestration/execution_engine.py:252` `bridge_{tool}_{uuid4().hex[:12]}`——每次全新。
- DAG 计划轨：`executor.py:1666`（重试 `:1696`）`tool_call_id=spec.id`——LLM 生成计划内节点 id，重规划即换。

### 4.3 运行级红测（round-1 草图落地，本机实证）

环境：sqlite in-memory（`sqlite+aiosqlite:///:memory:` + StaticPool，镜像 `tests/unit/test_x06_tool_call_safety.py` 的 `guard_db` fixture 与桩写工具）。脚本为一次性会话产物（/tmp，不入库）。同文本（同 args_hash 意图）两次执行、仅换尝试唯一键：

```text
attempt1: success=True execute_count=1 error=None
attempt2: success=True execute_count=2 error=None          ← 同意图第二次执行成功
ledger rows=2 keys=[call_aaa_11111111, call_bbb_22222222] statuses=[succeeded, succeeded]
control(same-key replay): success=True data_attempt=1 execute_count=2  ← 同键重放被正确拦下
RED CONFIRMED: same intent, two attempt-unique keys -> write side effect executed TWICE
```

- 断言一（实害通道）：两次尝试键不同 → 写副作用执行 2 次、账本 2 行均 succeeded、互不可见 → **跨尝试 duplicate side effect 通道实证为真**（等价于 tasks 表 +2）。
- 断言二（护栏完好）：同键重放 → 返回首次结果、不重执行 → 单次尝试内幂等恰一次，X-06 守卫零弱化。
- 基线回归：`pytest tests/unit/test_x06_tool_call_safety.py tests/unit/test_v3_fix223_ledger_gate_attribution.py -q` → **43 passed**（executor 幂等既有绿面未被我方理解偏差污染）。

**裁决**：CONFIRMED——机制严密性与键策略缺陷同时成立；「DoD duplicate side effect=0 仅单次执行尝试内结构性成立」的表述准确。335/336 修复方向（意图稳定键或 plan 骨架入 checkpoint）维持 round-1 建议。

---

## 5 ｜ DoD 对照表「已兑现」抽核（防 round-1 误放行）

抽 3 条 ✅ 判定 + 1 条佐证，全部复核通过，未发现误放行：

1. **V3-3「高风险不可逆 autonomous=0」（wt596/V3-FIX-304 已修）**：`backend/app/orchestration/execution_engine.py:2474-2494` 确定性 HITL 闸门实码在——`requires_confirmation or requires_hitl` 任一为真即 `_stream_hitl_plan_confirmation` + return，置于 validate_plan 消费之后、LLM plan review 之前；注释明言「降级链/合成回退自动批准也无法绕过」。✅ 维持。
2. **V3-3「Hybrid handoff 真实可恢复」**：`backend/app/services/hybrid_journey_service.py:675-700` judgment 步 awaiting 校验 → `complete_user_step` → resume 续跑；`:850-880` outcome 确认段（幂等重放终态 + awaiting 校验）实码路径成立。✅ 维持。
3. **V3-10「WVPL 可报告（本轮确认 G7 已修）」**：`backend/app/api/v1/north_star_wvpl.py` 在（frozen schema `north_star.wvpl.fact.v1`、`get_current_active_superuser` 依赖 `:42`）；挂载于 `router.py:89`（import）与 `:263`（include_router）。✅ 维持。
4. 佐证（V3-0 第一行的证据引用）：`v3-output/B-01/REPORT.md:19`「42/42 全定级，无 UNKNOWN 残留」+ `REVIEW_RECEIPT.md:13` 独立复核收据在档。✅ 证据引用有效。

---

## 6 ｜ 结论

四条发现全部 **CONFIRMED**；round-1 的行号锚点精度高（三处 ±1~3 行偏移已在各节标明，无语义影响）；334 的修复裁决草案见 §2.5；335/336 的实害通道已由 sqlite in-memory 运行级红测实证（执行 2 次/账本 2 行 + 同键对照回放），不再是纯静态推演。DoD 抽核未发现 round-1 误放行。
