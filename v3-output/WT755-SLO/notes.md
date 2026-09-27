# WT755-SLO notes — E-08 SLO 族首帧延迟修复（V3-FIX-439 裁决 b 移交项）

> 2026-09-28 ｜ Worker wt755 ｜ worktree `Sparkle-sysrev/wt755-slo`（分支 `agent/node-b/wt755/slo`，base `68dc7e20`）
> 台账：439 行追加进展注记（保持 OPEN，未置 FIXED）；新发现预占 **V3-FIX-491**（澄清门文案调用无预算）
> 性质声明：本卡交付**机制前移 + 服务可知点等价单测钉住**，无真模型跑（无 key 环境）；端到端 SLO 达标需有 key 环境 bench 复测（见 §6）。

---

## 1. 任务与证据基线

- 台账 V3-FIX-439（DYNAMIC_ISSUES.md）裁决 b@2026-09-27：端到端首帧延迟移交 E-08 SLO 族（E08-ISS-L2-FEEDBACK / E08-ISS-L3-ACK / E08-ISS-L0-TTFT）。
- wt372 bench（0e4087ec，104 条真模型）：首个 stage 帧（=ux_progress 帧）L2 p95=5.75s / L3 p95=7.32s / 全量仅 21/103 条 ≤500ms；L2-free 车道 12/12 全部 0.55-5.24s。
- 439 T 栏方向：intake/首 stage 帧前移——「模式判定/澄清门判定完成前即发 intake 帧 + goal_quality 门流式化或并行化」。

## 2. 归因修正（读代码 + raw.jsonl 逐帧复算，不盲从方向栏）

T 栏的机制前提**与实测不符**：

1. **澄清门/chat_mode 判定不在首帧前**。HEAD 代码（0e4087ec 同构）中 intake ack 在 `process_stream` 守卫链之后、门判定（`_check_sufficiency`→`_check_goal_quality`，orchestrator.py 3065/3095 行一带）之前发出。raw.jsonl L2-08 逐帧实录：`intake@3.0305s → goal_quality_scores@3.0314s → 模板 full_text@3.0315s`——门判定+文案+模板帧总共 9ms，紧随 ack。wt372「约 3s 门调用发生在首帧前」实为把**前段总延迟**误记到门上。
2. **真正的首帧前串行段**（约 6 个串行 await，全部 Redis/DB）：
   - `StreamChat` 前奏（agent_grpc_service.py:425-482）：`_process_aurora_correction_metadata`（通常快路径 no-op）→ `PromptBandit.select`（Redis）→ `_observe_feedback_effect`（Redis 1-3 op）→ **每请求 user bootstrap DB SELECT** → db_session_factory；
   - `process_stream` 守卫链：`_validate_request` → `_check_idempotency_response`（Redis GET）→ `_acquire_session_lock`（Redis SET NX，无自旋）→ `start_lock_renewal` → `_update_state(STATE_INIT)`（Redis HSET）→ `run_ledger.record_event(run_started)`（Redis persist）——**然后**才是 intake ack。
3. **0.33-5.24s 方差的形状**：L2-09 首帧 4.95s、L2-10 首帧 5.24s（且有两个 0.19s 的 tool_result 帧先到）、L2-08 3.03s、L2-06 0.58s——同一段代码，延迟随机分布在门轮/非门轮上都存在。5s 量级点疑与某个 5s 超时/拥塞窗吻合；主嫌疑=①上列串行链中某个 await 的 Redis 慢/超时，②前轮后台任务（bench 串行在流级，前一轮 20-100s 的深轮后台记忆/spine 写账与下一轮前段重叠）造成的**事件循环拥塞**。本机无 key 无运行栈，无法运行级定位，如实留档。

## 3. 取舍：侵入度分级与选定子集

| 级别 | 内容 | 决定 |
|---|---|---|
| L0 | **intake ack 块前移**（process_stream 内纯重排：stream_callback+RunLedger+run_started+ack+drain 移到守卫链之前） | **本次交付** |
| L1 | StreamChat 前奏前移（服务层直接发帧或 bandit/feedback-observe/bootstrap 延后/并行化） | 留登记（服务层契约面，独立卡） |
| L2 | goal_quality 门 first-content 链：`_compose_fast_interaction_copy` 无预算 LLM（真缺陷，预占 491）+ 模板零流式（wt372 §7-E）+ 门并行化（竞态面） | 491 预占+其余留登记 |
| L3 | L0 no-model 直答（E08-ISS-L0-TTFT 根因，wt372 §8 已判 FAIL 根因）；事件循环拥塞治理 | 留登记（需运行级证据） |

**选 L0 的理由**（按主会话风险指示：今晨 day7 终门，产出门后集成，优先低侵入）：
- 纯重排，**零新并发、零竞态面**；并行化按指示留登记。
- 直接命中 439 T 栏「服务可知点再前移」的字面：服务可知点从「守卫链后」钉到「请求身份锚定后」（request/session/response/trace id + spine 就绪）——这是帧能正确构造的最早点。
- 守卫链的每个 await 都是潜在秒级拥塞点（幂等 GET/锁 SET/态 HSET/run_started persist），前移后全部退出首帧路径。
- 语义代价有界且已声明：校验失败/幂等重放/锁冲突三类早退路径会先收到一个 intake ack 帧（droppable 状态帧，非终帧），随后照旧收到错误/缓存终帧。UX 上「已收到→稍后告知结果」优于秒级静默。
- `run_started` 写失败从「整轮报错」（旧行为：异常在 try 内触发 error 帧）改为**降级非致命**（对齐 stage_events.py 既有「stage 事件失败绝不阻断主链」哲学）——ledger 写故障不该杀死首帧；ack 帧此时携带空 `ledger_event_id`（与测试桩 `_RunLedgerStub` 形态一致）。
- E-03 契约保持：`test_early_ack_frame_is_ledger_correlated`（ack 带 ledger_event_id 可回查）不改即绿——run_started 仍紧邻 ack 之前记录。

## 4. 实现面（commit 内 5 个文件）

| 文件 | 变更 |
|---|---|
| `backend/app/orchestration/orchestrator.py` | 唯一生产码变更：`process_stream` 内 ack 块（queue/stream_callback/RunLedgerRecorder/run_started/intake ack/drain + chat_mode/user_message 提取）从「锁+会话态之后」移到「Step 1 校验/幂等之前」；`run_started` 加 try/except 降级；`_emit_early_ack_progress` docstring 同步新服务可知点定义；Step 3 注释同步。零签名/零协议/零 proto 变更 |
| `backend/tests/unit/test_stage_events_e03.py` | 新增 `test_intake_ack_beats_slow_prologue_guards`（红→绿主钉，见 §5） |
| `backend/tests/orchestration/test_orchestrator_process_stream_integration.py` | 锁冲突契约更新：`len==1`→`len==2`（ack 帧先于冲突错误，错误仍唯一终帧且 retryable） |
| `backend/tests/test_phase2_core.py` | 同上（锁冲突 smoke） |
| `backend/tests/test_phase2_integration.py` | 幂等重放契约更新：`len==1`→`len==2`（ack 先于缓存 full_text，缓存 STOP 仍唯一终帧） |

## 5. 红→绿与验证

- **红**：`test_intake_ack_beats_slow_prologue_guards`——三守卫（校验/幂等/锁）各 0.2s 慢桩 + 事件序记录；修前实录首帧 **0.605s**（守卫链后）FAIL（断言 <0.5s + first_frame 事件序先于三守卫）；修后绿（首帧 ~ms 级，事件序 first_frame→validated→idempotency→lock）。
- **绿**：受影响面 pytest 全绿——tests/orchestration 全量 1229、test_stage_events_e03 12、phase2 core/integration、process_stream 驱动面（done_tail/observability/signal_spine/trace_spine/event_*reliability/context_source/f821/spine pipeline）、gRPC 服务面（test_agent_grpc_service×2）、tests/unit/orchestrator 128、integration/phase5 27——合计约 **1340 passed**。
- **既有 flaky 2 例与本改无关**（如实记录）：`test_statechart_engine.py::TestParallelExecution::test_parallel_branch_execution`（并行计时断言 <0.10s，stash 后 base 上同红）；`test_signal_spine.py::test_version_conflict_result_has_diff_fields`（批量跑偶红，单跑绿）。
- **mypy**：触达文件 `app/orchestration/orchestrator.py` 错误清单与基线 **NO-DIFF**（唯一 1 条既有 arg-type 仅行号 2400→2415 平移；follow-import 全景 66 errors 与改前同集）。
- **lint**：ruff check 过；black（120）在本机版本下该文件本就 Would reformat（19 hunks 全在未触达区域，stash 对照 base 同判），本改零新增漂移。
- **台账守卫**：`ledger_union_merge.py --verify --strict-pipes` 零 FAIL（曾修一次：进展注记误成独立列 9 裸管，已收回 OPEN 单元格内）。

## 6. 复测建议（给有 key 环境的同事）

1. 复跑 wt372 bench（引擎 @ 本分支集成 SHA）：
   ```bash
   cd <集成 worktree> && backend/.venv/bin/python scripts/devtools/bench_ai_stack_l0_l3.py run --tag wt755
   backend/.venv/bin/python scripts/devtools/bench_ai_stack_l0_l3.py summarize --tag wt755
   ```
2. 对照指标（与 raw.jsonl 基线 0e4087ec 同口径）：
   - `t_first_stage_s` 分布：**本改吃掉的是守卫链段**——期望下界与方差收窄（守卫链慢 await 不再挡首帧）；但 **StreamChat 前奏（bandit/feedback-observe/bootstrap SELECT）仍在首帧前**，0.33s 量级的地板与事件循环拥塞项不因本改消失。
   - L2-free `t_first_stage_s` 12/12 与 L2 首事件 p95（基线 5446ms）：若 p95 仍 >1s，剩余归因按 §2.3 指向 StreamChat 前奏/拥塞，**L1/L3 才是下一刀**，不要回滚本改。
   - 澄清门 12 条的 `t_first_stage_s` 与 full_text 时点：门路径 9ms 形态（L2-08）说明门调用非首帧阻塞者；模板零流式与文案预算是 491 的面。
3. 若需直证守卫链耗时：`latency_probe` 已有 `debrief_check`/`build_full_context` 等点位，建议在守卫链四 await 各补 mark（独立卡，本卡不改观测面）。

## 7. 边界与不声明

- 本机无 LLM key/docker：未做真模型 bench、未跑引擎级联调；「首帧 <500ms」的端到端结论**不下**，只交付机制+单测等价钉住（先例：E-03 的服务可知后 1.8ms 单测）。
- 未触碰：mobile、gateway、proto、DB schema、docker/运行栈/.env/状态文件、adaptive_routing/双核路由本体。
- `EARLY_ACK_PROGRESS_ENABLED` 开关语义不变（False 时旧行为完全保留）。
- 无 Mock 冒充模型结果；bench 数字全部引自 wt372 在案交付物并逐帧复算。
