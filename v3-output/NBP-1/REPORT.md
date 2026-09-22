# NBP-1 · WS 主链路记忆写账断裂 — 修复报告

- 卡号：NBP-1（NORTHSTAR-LOOP2 最高优先 P0）
- worktree：wt115（基于 main@d5cce684，分支 wt115-v3）
- 产物：`v3-output/NBP-1/changes.patch`（6 文件，5 源码 + 1 测试）+ 本报告
- 纪律：未 commit / 未 push；未触碰 wt116（experience/goal_router）与 wt117（gateway setup.go/timeout.go）域

---

## ① 断点定位（file:line 与机制）

**一句话机制**：WS/gRPC 主链路的对话轮收尾没有任何一条**确定可达且携带用户原文**的 declared-fact 捕获触发器——REST 面（`api/v1/chat.py` `save_chat_message` 尾部直调 `MemoryInferredWriteLaneService.enqueue_from_chat_turn`，chat.py:1131）的三个 WS 等价触发点全部失效：

1. **快交互短路轮零触发器（B1 实锤直接断点）**
   `backend/app/orchestration/validation_engine.py:87` `_emit_fast_interaction` 只发协议帧即返回——不持久化、不建 finalize 任务、不碰记忆面。sufficiency 澄清/确认（validation_engine.py:356/374）、phase-A 规划前置门（:626）、goal-quality 澄清（:756）四类短路出口全部经它发出**最终回复**后 process_stream 直接 return（orchestrator.py:3042/3062）。B1 的 Day0 消息（「请帮我建立目标并给我冲刺计划」信息不足 → 澄清门反问目标分数）正是这类轮——**明示事实最密集的轮恰好全灭**。

2. **主路径旧 fallback 被双重架空**
   `backend/app/orchestration/orchestrator.py:1183`（`_write_turn_end_episodic_memory` summary 为空分支的 `enqueue_from_chat_turn` 兜底）：(a) 仅主路径 Step14 `final_state is not None` 时创建的 `_finalize_turn_after_done`（orchestrator.py:3782）可达，一切短路轮到不了；(b) 摘要非空即跳过。LOOP2 中它对 B1 形态轮从未执行。

3. **persist 收尾触发器赌异步落库竞态**
   全部 persist 路径的触发器 `_persist_assistant_message` → `enqueue_from_session(user_message=None)`（persistence_layer.py:52 旧行号）不带用户原文，靠 `process_chat_turn` 内 `_load_latest_user_turn` 从 Postgres 回捞 user 行（memory_inferred_write_lane.py:553）。但 WS 链路的 user 行由**网关 Redis persister 异步落库**（gateway `chat_history.go` `SaveMessage` → `queue:persist:history` → `chat_history_persister.go`，且受 `ChatPersisterEnabled` 门控），一次性 fire-and-forget 后台任务稳输该竞态 → `missing_user_turn` → return None，**无重试、永久丢失**。引擎侧 WS 路径从不及持久化 USER 行（全引擎仅 persistence_layer.py 持久化 ASSISTANT 行）。

实证闭环：LOOP2 `probe-rest-memory-write.json` REST 臂 3 条（due_at 正确）/ WS 臂 0 条（即时+10 分钟均 0）；Day1 快照中唯一的 episodic 行来自 `direct_capture` lane（task_completed 摘要非空分支）——证明 finalize 路径本身可达，唯 declared 面触发器缺位。

## ② 修复面（单一事实源，非复制逻辑）

全部改动直调与 REST 同一个捕获函数 `MemoryInferredWriteLaneService.enqueue_from_chat_turn`（抽取/去重/门禁/冲突裁决/写入全在其内，零逻辑复制）：

| 文件 | 改动 |
|---|---|
| `backend/app/orchestration/persistence_layer.py` | `_persist_assistant_message` 新增 `user_message: str \| None = None` 入参：调用方在手原文时改调 `enqueue_from_chat_turn`（evidence_token=assistant 行真实 id）；未传时**保持 `enqueue_from_session` 原行为零变化** |
| `backend/app/orchestration/validation_engine.py` | `_emit_fast_interaction` 新增 `turn_capture` 参数，发出 STOP 帧后触发同一捕获面（request_id 作 evidence_token；非法上下文静默跳过绝不影响回复）；新增模块级 `_ws_turn_capture` 构造器（缺关键字段返回 None）；四处短路出口全部接线；`_check_goal_quality` 增补可选 `session_id`/`request_id` 参数（向后兼容默认 None） |
| `backend/app/orchestration/orchestrator.py` | **移除**被架空的旧 fallback（:1177-1193）——它同时构成与 persist 钩子并发的 semantic_key check-then-insert 双写竞争（`EpisodicMemory.semantic_key` 无唯一约束，models/memory.py:108）；`_check_goal_quality` 调用点传入 session_id/request_id；fast-track（:806）/debrief（:2331）/aurora runtime（:1376）三处 persist 调用补传 user_message |
| `backend/app/orchestration/response_builder.py` | 主路径 `_build_final_response` 持久化时携带 `latest_user_message`（与 ux_envelope 同源抽取，:1295 原有函数） |
| `backend/app/orchestration/execution_engine.py` | bridge 短路/openclaw 控制×2/multi-agent 四处 persist 调用补传 user_message（`_continue_after_tool_result` 的 :1455 不接——tool-result 轮的原文已在上一轮捕获，避免无原文可传的形参） |
| `backend/tests/unit/test_nbp1_ws_turn_memory_capture.py` | 新增红→绿锁定测试（9 例，见③） |

双触发互斥性：快交互短路轮与 persist 路径单轮互斥（短路即 return，不进 persist）；主路径单触发点（persist 钩子），重复声明由捕获面内 semantic_key 去重兜底。

## ③ 红→绿 与 回归统计

**红测试（新增 `test_nbp1_ws_turn_memory_capture.py`，9 例）**：覆盖 B1 原句的三条链路形状——快交互短路轮捕获、persist 钩子捕获、以及「捕获调用形状 → 同一捕获面 `process_chat_turn` 真实入库」的链路级断言（≥3 条 declared facts + exam `due_at=2026-09-28T18:00` 与 REST 臂一致）。

- **红**：`git clone wt115 → /tmp/nbp1-baseline`（天然 HEAD 基线，未碰原树）+ 同一测试文件 → **6 failed**（四类新行为断言全红；3 例红线守卫通过属预期）。
- **绿**：wt115 修复后 → **9 passed**。

**回归（pytest，SQLite 内存库 + fakeredis，SECRET_KEY 走进程环境变量，未落任何 .env）**：

| 批次 | 结果 |
|---|---|
| memory 家族（declared_fact 18 + write_lane×2 + write_guard + chinese_commitment + selfcheck×3） | **145 passed** |
| correction 7（BP-3B 纠正优先级）+ resilience（sufficiency preflight + spine）+ 四个 mixin 既有测试 + done 尾延迟 | **78 passed** |
| gRPC agent 服务（unit + chat_modes）+ gRPC 流式集成 + 降级/熔断（spine_degradation/llm_fallback×2/circuit_breaker）+ r2 fixes | **37 passed, 16 skipped** |
| 红线面：citations（markers 16 + rag_cite_chain/context_funnel 33）+ O-07 budget + RuleY gate/guard | **121 passed** |
| 广域扫描（-k "memory/declared/persist/sufficiency/goal_quality/orchestrator"） | **903 passed** |
| 全量 `tests/orchestration` + `tests/unit/orchestrator` | **284 passed / 35 failed**（对照基线 283/36，见下） |

**预存失败（基线逐一对照复现，非本次引入）**：
- O-07 dispatch choke/backpressure 15 例（celery 桩契约漂移）；
- `_GraphStub.invoke(resume_policy=...)` 桩不匹配 6 例 + `orchestrator_real_engine`/`working_memory_api` 6 例 + 22 个 collection/fixture error（缺 `grpcio-reflection` 等环境依赖）；
- 唯一差异方向为**向好**：基线失败的 `test_r2_04_orchestration_source_has_no_exc_info`（orchestration 源码 exc_info 扫描）随旧 fallback 删除在 wt115 转绿（35 vs 36）。

## ④ 红线面四组核查

1. **REST 路径零变化**：`api/v1/chat.py` 零改动；`save_chat_message` 仍直调 `enqueue_from_chat_turn`（正是被统一的单一事实源）；memory 家族 145 例含 MEM-AMNESIA 18 例全绿。
2. **WS 流式协议/事件形状不变**：全部改动在帧发**之后**或帧发参数之外的旁路；`_emit_fast_interaction` 两帧形状（status_update THINKING + full_text/STOP）有专项断言；gateway 零改动（未碰 wt117 的 SSE 域）；citations 家族 49 例全绿（V13 citations 面）。
3. **BP-3B 纠正优先级 / ORCH-DEBT 降级**：correction 7 例、降级/熔断批次 37 例全绿；`has_correction_signal` 判定序未触碰。
4. **FIX-49/O-07/RuleY 限流与预算面不绕过**：事实抽取为既有捕获面内零 LLM 正则（快交互轮此前从未到达该面，现在到达的也是 REST 轮一直走的同一面）；lane 内建 10/min/user 限流、RuleYAdapter 校验、O-07 预算面全部原样生效；RuleY gate/guard 测试绿。O-07 的 15 例失败为预存桩漂移（基线一致），与预算语义无关。

## ⑤ 收工核查

- [x] 未 commit/push；patch 可在干净基线 `git apply --check` 通过
- [x] 无 .env 创建（SECRET_KEY 走进程环境变量）；无仓库根/家目录/共享目录文件
- [x] /tmp 自清：`nbp1-baseline` 克隆、uv 日志、uv.lock 备份已删
- [x] worktree 内产物仅 gitignored 的 `backend/.venv`、`backend/app/gen`（随 worktree 生命周期回收，供 LOOP3 复测复用）
- [x] uv.lock 已还原（diff 不含依赖变更）；`git status` 仅 5 源码文件 M + 2 新增产物目录
- [x] 未触碰 wt116/wt117 域；真栈验证未做（留给主会话 LOOP3：本卡+wt116 合入后统一重启验证）

**LOOP3 验证建议**：同句 B1 走 WS `/ws/chat` 两种形态各一发（直答轮 + 触发澄清门轮），判卷后 30s 查 `/memory/episodic` 应 ≥3 条 declared facts（exam commitment 带 due_at），与 REST 探针臂对齐。
