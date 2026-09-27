# WT631 承诺-实现差距轴 · 三遗留面终核 + DoD 对照

- 工位：wt631 ｜ 轴：未兑现承诺/愿景差距（承诺 vs 实现深核）
- 基线：main 头 `e1dbf363`（分支 `agent/node-b/wt631/promise`，backend/app/gen 已复制）
- 日期：2026-09-28 ｜ 方法：只读对码 + 调用图/分层 TTL 推演，未起栈
- 接 wt587 三面（其 findings.md「扫过无发现/未深入」§）+ DoD Gate 逐条对照 + 比赛材料数字核对
- 已避开在案编号 287–332；本文建议编号自 **V3-FIX-333** 起。已在案不重报：V3-FIX-302/303/305（wt587 F1-F4，302/305 修复在航）、**V3-FIX-304 已由 wt596 修复落地**（execution_engine.py:2474-2494 确定性 HITL 闸门已接线，本轮实码确认）、V3-FIX-306 已修（T-wt601 完成）。
- 严重度口径：P1 冒充模型结果/红线承诺失效 ｜ P2 用户可见或账本失真 ｜ P3 文档债/测试债。

---

## 一、三遗留面终核（wt587 → 本轮下结论）

### 面 1 ｜runtime probe（DoD Gate V3-0 第 3 条）—— **结论：未兑现（4/5 能力族仍凭配置宣称），wt587「未验证不算清白」解除**

**承诺原文**：`v3/V3_DEFINITION_OF_DONE.md:8`「当前模型、embedding、ASR/TTS、OCR 等能力由 runtime probe 得到，不凭配置文件宣称可用」。

**逐能力族对码**：

| 能力族 | 可用性判定实现 | 性质 |
|---|---|---|
| 当前模型（LLM） | `backend/app/core/llm_router.py:407,412`（register_model_configs 自配置注册）+ `:269` `ModelHealthState.is_healthy: bool = True` **缺省健康**；`:328-337` 冷却后 probation 探活是**真实流量驱动的被动熔断**，非主动 probe | 部分（被动健康，初始声称=配置） |
| embedding | `backend/app/services/embedding_service.py:123-146`：`provider_status()["configured"] = bool(api_key)`——键非空即宣称 | 配置宣称 |
| ASR/STT | `backend/app/services/stt_service.py:29-48,78-80`：`_init_provider` 按 `settings.STT_PROVIDER` + `_is_configured_value`（键非空）构建；`:100-125` `_should_try_backup` 是请求期**事后**错误串匹配换备 | 配置宣称 |
| TTS | `backend/app/services/tts_service.py:145-149`：`DASHSCOPE_API_KEY` 非空即构建 BailianTTSProvider | 配置宣称 |
| OCR | `backend/app/services/ocr_service.py:24-33,57`：`_provider_configured` 读 settings；`:86,139` 执行前配置检查 | 配置宣称 |

**仓内确有两处真 runtime probe（正证据，证明能力存在但未用于上述承诺面）**：
- OpenClaw 执行能力：`backend/app/adapters/openclaw/client.py:161-165,183-200` —— 真实 HTTP POST `/v1/responses` 探测，失败置 `reachable=false`；
- 可选能力表级探测：`backend/app/services/task_optional_capabilities.py:67-70`（focus/calendar 表存在性，缺席降级可观测）。

**用户可见宣称面同样来自代码/配置**：`backend/app/services/capability_registry_service.py:33` 等子系统条目 `state: "active"` 硬编码（openclaw 一项按 settings 置 configured/not_configured），经 `app/api/v1/multi_agent.py:264` body-map 端点直接对外；`get_public_agent_catalog`（agent_profiles.py:790）的 `specific_model`/`model_tier` 亦为代码注册表宣称。

**差距定级**：未兑现（承诺语义=主动 probe；实现=键存在性+被动熔断）。**修复量级 S-M**：要么启动期对 5 族能力各发一次最小连通 probe 并暴露状态端点（M），要么改 DoD 措辞为「由配置声明+流量健康熔断共同得出」（S，需 ADR 记录口径降级理由）。

---

### 面 2 ｜可恢复 Run 端到端（DoD Gate V3-6 第 3 条）—— **结论：机制三件套齐全，但 chat 轨「同一请求重入」在生产链路上被网关去重结构性遮蔽——恢复链永不被触发（跨层 TTL 矛盾）**

**承诺原文**：`v3/V3_DEFINITION_OF_DONE.md:45`「app 关闭/重开、WebSocket 重连、worker restart 后 run 可查询并恢复」。

**机制清单（正证据，全部真实存在）**：
- Checkpoint 持久化：`backend/app/checkpoint/redis_checkpointer.py:54-105`（每节点执行前 save，`checkpoint:{session_id}`，incomplete 标记 + request_id + 24h TTL）；`:151-196` `load_interrupted`（**要求同 session_id+同 request_id**、incomplete、`checkpoint_kind=stategraph_node_pre_execute`、30 分钟 max_age）。
- 恢复接线：`backend/app/orchestration/execution_engine.py:1934` `graph.invoke(state, resume_policy="interrupted_only")` → `statechart_engine.py:237-253` 命中则从存档节点续跑（`_merge_checkpoint_state` :385-403 保新鲜请求态、滤易失键）。
- AgentRun 状态机：`backend/app/core/run_state_machine.py:65-148`（封闭词表+resume 白名单=RUNNING/EXECUTING）；`backend/app/services/agent_run_service.py:1642` `recover_stale_runs`（QUEUED 陈旧→CANCELLED；RUNNING/EXECUTING 心跳陈旧→**UNKNOWN_OUTCOME**，诚实不装恢复）；API `backend/app/api/v1/runs.py:351` POST `/{run_id}/resume`（预算闸门 :917-925 先行）。
- Hybrid 旅程有**真实恢复闭环**：`backend/app/services/hybrid_journey_service.py:679-681`（校验 awaiting judgment）→ `:686-694` complete_user_step+resume → 段3 execute/check 续跑；`:856-878` outcome 确认段同理。**这是 V3-3「Hybrid handoff 真实可恢复」的正证据**（与 wt587 G13 判断一致，WT347 G13 已证，本轮复核代码路径成立）。

**断裂点（本轮新发现，分层推演）**——chat 轨恢复链的三个互锁矛盾：

1. **网关去重 TTL(60min) > 检查点恢复窗(30min) > 响应缓存 TTL(5min)，同 id 重发永远先被弹掉**。
   - 网关：`backend/gateway/internal/service/chat_history.go:312-327` `TryAcceptRealtimeRequest`（SetNX `ws:chat:request:{user}:{req_id}`，**TTL 1 小时**）；`internal/handler/chat_orchestrator_chatflow.go:347-362` 接受前判定，重复即 `duplicate_request`（不可重试）。
   - 引擎检查点恢复窗 30 分钟（statechart_engine.py:379 `max_age_seconds=30*60`）、响应缓存 5 分钟（state_manager.py:516 `ttl=300`）。
   - 推演：同 request_id 重发落在 0–60min 内任一点 → 网关必弹（Redis 正常时）；>60min 后引擎终于可见，但 30min 恢复窗与 5min 缓存早已过期 → 全新 run。**即：网关存活时，引擎侧同请求幂等重放与检查点恢复在 WS 主链上不可达**；仅网关 Redis 故障（chatflow.go:348-349 err 分支 fail-open）或直连 gRPC 才可能触发。三层的「幂等/断点续传」注释各自成立，组合起来互斥。
2. **客户端重试刻意换新 id**：`mobile/lib/features/chat/presentation/providers/chat_provider.dart:1444-1449`——重试派生 `${runId}_r1`，注释明言为避开网关 1h 去重。新 id → `load_interrupted` 的 `request_id` 等值判据（redis_checkpointer.py:168）必失配 → **客户端唯一常态重试路径从不走进恢复链**，而是全新生成。全链重跑时上一次已执行的 side-effect 工具以新幂等键再次执行（与面 3 叠加，见 V3-FIX-336）。
3. **响应缓存写多读少（「断点续传」注释名不副实）**：`state_manager.py:517` docstring「用于幂等性和断点续传」；读侧 `get_cached_response`/`is_duplicate_request` 在 state_manager 之外**零生产调用**，唯一消费是引擎 intake 的 `_check_idempotency_response`（validation_engine.py:264-286 ← orchestrator.py:2224）——而该入口如第 1 点所述被网关去重遮蔽。写侧三处照常写入（orchestrator.py:1408,3445,3856）。

**定性**：worker restart 场景的 DoD 承诺实际由 `recover_stale_runs` 以 UNKNOWN_OUTCOME「诚实终止」满足（不伪装恢复，符合 false success=0 精神），但「可恢复」半句在 chat 轨不成立；hybrid/AgentRun 轨成立。**修复量级 M**：裁决一项即可解——(a) 网关去重命中时不弹错，改返回该 request_id 的最终结果/状态（查 run_ledger+响应缓存，把响应缓存 TTL 提到 ≥1h），或 (b) 去重键与恢复键解耦（恢复专用通道带原 request_id 白名单）。任一需跨 gateway/engine 两侧联改+契约测试，建议先出裁决卡。

---

### 面 3 ｜per-tool-call 幂等键（DoD Gate V3-6 第 5 条）—— **结论：wt587「倾向 DoD 缺口」翻案——执行器层幂等真实存在且严密；真实缺口收敛为「键的跨尝试稳定性」（意图片重跑无结构性防重）**

**wt587 猜测**：`core/idempotency.py` 只有请求级与 plan_review action 级接线，「倾向算 DoD 缺口」。

**本轮对码（正证据）**：per-tool-call 幂等在 **X-06 工具执行账本**完整落地：
- 强制闸门：`backend/app/orchestration/executor.py:473`（docstring）+ `:515-524`——side-effect（`ToolEffect.WRITE`，`app/tools/metadata.py:124-126`）工具**无键即拒**（`IdempotencyKeyRequired`，fail-closed）；`:526-560` 同键查账本命中即**重放已记录结果不重复执行**，args_hash 不符拒（`IdempotencyArgsMismatch`），账本不可读拒（`LedgerUnavailable`）。
- 并发窗口封闭：`executor.py:644-660` 捕获唯一索引 `uq_agent_tool_calls_idem`（`app/models/agent_tool_call.py:74-81`，(user_id, tool_name, idempotency_key) 部分唯一索引）撞键 fail-closed。
- 重试语义有界且诚实：`executor.py:1635-1648`（docstring）——仅 `side_effect_state=none`（账本随事务回滚=确证无事发生）才以派生键 `{spec.id}:retry:{n}` 重试；unknown 族不重试；`interrupted` 态同键重放仍拒（`agent_tool_call.py:31-46` 词表注释，「重试必须换新幂等键（显式决策，非自动）」）。
- 写工具覆盖面：app/tools/ 下约 18 个 `effect = "write"` 工具（task_tools/plan_tools/companion_tools/growth_strategy_tools/intervention_tools/error_tools/theater_tool/report_tool/task_query_tool）全部过此闸门。
- DoD 第 5 条字段清单对账（`tool call 有 run_id、permission decision、idempotency key、result/receipt、latency/cost`）：`agent_tool_call.py:51-72` run_id✓（chat 轨未挂 run 时可空）、permission_decision✓、idempotency_key✓、result✓、execution_time_ms✓；**cost 仅 run 维度**（record_run_usage 聚合），调用级 cost 列不存在——第 5 条按字面为部分兑现。

**真实缺口（新发现，V3-FIX-336）**：键源全是**单次尝试唯一**值，非**意图稳定**值：
- chat 轨直执行：`app/agents/standard_workflow.py:2774` `tool_call_id=tc.tool_call_id or str(uuid.uuid4())`（模型 id 本轮唯一/uuid 每次全新）；bridge 轨 `execution_engine.py:252` `bridge_{tool}_{uuid4().hex[:12]}` 每次全新。
- DAG 计划轨：`executor.py:1655` `tool_call_id=spec.id`（LLM 生成计划内的节点 id）。
- 组合效应（与面 2 缺口 2 叠加）：客户端换新 request_id 全链重跑 → LLM 重新生成 → 新 spec.id/新 call id → 上次已提交的写操作（如 create_task）**再次执行**，账本因键不同无法识别同一意图。**DoD「duplicate side effect = 0」仅在单次执行尝试内结构性成立**；跨尝试（重连重发、进程崩溃后人工重发）依赖「上次根本没执行成功」的运气而非机制。
- **修复量级 M**：为写工具引入意图稳定键，如 `(session_id, 规范化用户意图/plan 输入哈希, tool_name, canonical_args_hash)` 派生键（args_hash 基建已在，`app/tools/metadata.py` canonical_args_hash；账本已有 args_hash 列可做二级判据），或恢复链把原 plan 的 spec.id 随 checkpoint 持久化（`executable_plan` 现列于 `KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS`，redis_checkpointer.py:41——恢复后按需重建即换键，注释自认）。

---

## 二、DoD Gate 逐条对照表

口径：✅已兑现=有代码+测试/实测双证或本轮实码确认；🟡部分=机制在、缺一环；❌未兑现；❓=需真栈/真模型证据，本轮只读无法判定（引用既有审计）。已修复的在案项标注编号。

| Gate | 条目 | 现状 | 证据 |
|---|---|---|---|
| **V3-0 Truth** | 42 feature 唯一 portfolio 状态、无半成品入口 | ✅（矩阵在案） | v3-output/B-01/（42/42 定级+独立复核收据，基线 a2d8a10c）；孤儿路由/空 shop 缺口已在报告 §3 登记 |
| | 统计数字 lineage、mock/seed 隔离 | 🟡 | persistence_layer origin=DEMO 单点保证（wt587 复核通过）；反例：agent-stats 零写入（在案 FIX-330）、weekly_synthesis 残轨（FIX-331） |
| | 能力由 runtime probe 得到 | ❌ | **本轮面 1（V3-FIX-333）**：模型/embedding/ASR/TTS/OCR 五族均配置宣称 |
| **V3-1 First Value** | ≤3 分钟首个 meaningful proposal；承诺屏/First Understanding | ❌（壳缺失，机制在） | WT347 G1：mobile 无「把卡住变成下一步」、onboarding 仍旧导览（其证据路径在案，本轮未推翻）；friction/proposal 组件全在 |
| | 体验示例与「开始我的目标」严格区分、demo 不冒充历史 | 🟡 | DemoDataService+DEMO_MODE+guest_seed 在（WT347 G6）；三件套之「demo seed 零写真实画像」无专项测试 |
| **V3-2 Stuck→Action** | 20 friction 场景 ≥18 一致 | ❓（评测未跑） | WT347 G3：260 场景库+判卷门在（test_v3_scenario_eval_gate.py:85），harness 为确定性参考桩，无真模型批量报告 |
| | proposal 五要素结构 | ✅（机制） | friction_diagnosis.py 15 类+One Best Question（WT347 G3 同条证据，1616 行） |
| **V3-3 Human–AI** | 分配离线评测 ≥90% | ✅ | test_action_allocation_eval.py:69-74（accuracy≥0.90 断言）+action_allocation_policy（WT347 G12） |
| | 高风险不可逆 autonomous=0 | ✅（本轮确认修复落地） | **wt596/V3-FIX-304 已修**：execution_engine.py:2474-2494 确定性 requires_hitl/requires_confirmation 闸门置于 LLM 审查之前，降级链不可绕过；standard_workflow.py:2731-2753 对照 enforcing 原本就有。余留：PONR_TOOLS 五件套不在 38 工具注册表（在案 FIX-304 行内注记，不重报） |
| | Hybrid handoff pending/awaiting/resumed/cancelled 真实可恢复 | ✅ | hybrid_journey_service.py:679-694,856-878 awaiting→resume→续跑真实闭环（本轮实码路径核对+WT347 G13 测试清单） |
| **V3-4 Personalization** | precision ≥95% / uplift +15pp | ❓ | 评测门+阈值在（tests/memory_eval/gate.py:31），真模型 run 报告未成文（WT347 G11） |
| | 删除后 retrieval/cache/context/in-flight 不复用 | 🟡 | memory_retrieval_prefilter M-01 revoked/expired 在；in-flight 不复用无专项测试（WT347 G8） |
| **V3-5 Flywheel** | intervention→outcome 闭环 | ✅ | outcome_ledger+event_registry OUTCOME+capture_service（WT347 G16） |
| | understanding 五维、不合成神秘百分比 | ✅（后端）/🟡（UI 消费） | core/understanding_dimensions.py 467 行+golden 冻结（WT347 G15）；mobile 档位消费待小卡核对 |
| **V3-6 Runtime** | 100 run ≥99 正确 terminal/awaiting | ❓（统计未产出） | 状态机+chaos 复跑在（WT460-CHAOS-REVERIFY：typed error 真引擎级 12 样本×8 敏感性点）；100-run 批量统计无 |
| | false success=0 | ✅（机制+实测） | wt460 chaos 终版：全断供 11/12 用户可见 error 帧 code=8、无模板/缓存文本冒充（chaos_results.json 程序化复算） |
| | 关闭/重连/重启后可恢复 | ❌（chat 轨）/✅（hybrid/AgentRun 轨） | **本轮面 2（V3-FIX-334）**：三层 TTL 互斥遮蔽；recover_stale_runs 诚实 UNKNOWN_OUTCOME |
| | duplicate side effect=0 | 🟡 | **本轮面 3（V3-FIX-336）**：单次尝试内结构性成立（账本+唯一索引+fail-closed）；跨意图级重试无防护 |
| | tool call 五件套字段 | 🟡 | agent_tool_call.py 全字段在，唯调用级 cost 缺（run 维度聚合代偿） |
| **V3-7 Experience** | 核心旅程 A/B=0、三平台 golden journey | ❓ | u02_rubric 截图+rubric 判定表在案（android 列）；GJ 真渲染判 unsupported（WT347 G9） |
| | 视觉回归基线截图+diff | ✅（一角） | mobile/test/goldens + U-09 45 行矩阵 + U-02 真字形出图（v3/09_evidence/u02_rubric/） |
| **V3-8 Perf & Cost** | L0≤500ms/L1≤2.5s/L2≤15s/L3 ACK≤1s | ❌（未达标且未重定 SLO） | LOOP3 实测完整回合 51-87s、TTFT ~30s 簇 vs L2 p95≤15s 差 3-6 倍、无重定 SLO ADR（WT347 G4；docs/adr/ 最新止于 0008，无 SLO ADR） |
| | 每 tier token/cost/latency 账本 | 🟡 | run_ledger usage/response 段在（run_ledger.py:75-84）；模型级归因失真在案 FIX-303 |
| **V3-9 Commercial** | HTTPS 远程部署 | ❌（外部阻塞） | 阿里云 ECS 已购卡凭据（WT347 G5，HANDOVER §2.7；本轮无新凭据证据） |
| | entitlement 解耦/quota/kill switch/导出 | ✅ | entitlement 四层+迁移重放、kill_switch、data_export 测试（WT347 G18） |
| | backup/restore 演练成功 | ❌ | runbook+脚本在，演练成功记录未见（WT347 G19） |
| | 一键 smoke + rollback runbook | 🟡 | journey_smoke.sh/run_e2e_smoke.sh 为 unit/integration 级非真栈（WT347 G19） |
| **V3-10 North Star** | WVPL 可报告（分母/loops/分工/proactive） | ✅（本轮确认 G7 已修） | **WT347 后已落地**：backend/app/api/v1/north_star_wvpl.py（D-06，frozen schema `north_star.wvpl.fact.v1`，superuser 只读，router.py:89,263 挂载）+golden+worker 全链 |
| | 不得把 chat/send/task-click 当成果闭环 | ✅（口径冻结） | core/north_star_wvpl.py 事实口径+golden sha256 钉死（WT347 G7 原证据，端点现补齐） |

**汇总：✅ 12 ｜ 🟡 9 ｜ ❌ 6 ｜ ❓ 5**（按表内条目计；❓=有机制无运行级证据）。

---

## 三、比赛材料一致性（docs/competition 抽核）

本仓 docs/competition/2026-tmall-hackathon/ 现存材料为**审计型**（系统审查/多端实测/接力日志），**未发现「2 秒」「59 项全绿」类无源宣传数字**——历史红线项在这批材料中不存在，材料本身可信度高（负向声明也是正证据）。抽核三项可验证数字：

1. **「恢复风暴 P50 45s→68ms」（V3规划输入-项目全景.md:17,233,254）**：修复机制在码——`backend/app/api/v1/galaxy.py:233`「恢复风暴防护：single-flight 合并同 user 并发拉取 + 10s TTL 缓存 + 并发钳制」✅ 相符。
2. **「编排侧首 token 开销 23.1s→1.94s（-92%）」（:254）**：机制在码——`force_fast_first_touch`（standard_workflow.py:284,1617,1895）✅ 相符；同文档 ：326 诚实标注「现在端到端首 token 约 24s，残余是 DeepSeek reasoning 思考时间」——口径分层清楚，无冒充。
3. **「治理守卫 71 条全绿」（:17）**：现 `scripts/rule_guard_manifest.tsv` 活规则 **86 条**。非失真（守卫数随时间增长），但**复用该全景文做提交/答辩材料时须重新计数**，否则与仓内现状即时不一致（文档过期级，S）。
4. **「V2 任务卡 100% 完成」（:17）**与「两轮 8-agent 审查 44+30 项、P0/P1 100% 闭环」：有系统审查 round1/round2 目录与接力日志佐证过程存在；「100% 闭环」无法只读复核到每项，按材料自有引用口径视为可溯源声明，不列为差距。
5. 记忆/RAG「8/9 剩余 1 项（mr4 qwen3.8-flash 间歇性不引用）」：`scripts/devtools/acceptance_memory_revival.py` 在码 ✅；剩余项表述诚实。

**比赛材料结论**：无红线级失真；一处需刷新的时效数字（守卫 71→86）；建议 10/4 交付前把 :17 顶栏数字与当时 manifests/计数对齐一次（S，纯文档）。

---

## 四、建议编号汇总

| 建议编号 | 主题 | 级别 | 量级 |
|---|---|---|---|
| V3-FIX-333 | DoD V3-0 runtime probe 未兑现：五能力族配置宣称 + body-map 硬编码 active 对外 | P3（承诺-实现缺口，用户面宣称与实际可用性可漂移） | S-M（probe 补齐或 ADR 降级口径） |
| V3-FIX-334 | 可恢复 Run 端到端断裂：网关去重 1h > 恢复窗 30min > 响应缓存 5min 互斥 + 客户端重试换 id + 响应缓存读侧死路 | P2（DoD V3-6「可恢复」承诺 chat 轨失效；中断后用户消息静默无回音面） | M（跨 gateway/engine 裁决+联改） |
| V3-FIX-335 | `executable_plan` 不入 checkpoint → 恢复后重建计划换幂等键 → 中断前已执行写工具在恢复后重复执行的结构性通道 | P2（与 334/336 叠加成 duplicate side effect 实害路径） | M（持久化 plan 骨架（plan_id+spec.id+args_hash）或意图派生键） |
| V3-FIX-336 | per-tool-call 幂等键为尝试唯一非意图稳定：跨逻辑重试无防重，DoD「duplicate side effect=0」仅单尝试内成立；另 DoD 五件套缺调用级 cost | P2 | M（意图派生键/二级 args_hash 判据） |

> 334/335/336 是同一断裂面的三个可独立修复的切面：334 修「重入通道」，335/336 修「重入后不重复作恶」。任一单独落地都有独立价值；三项齐了 V3-6「重连可恢复+duplicate side effect=0」才同时为真。

## 复核提示（给下一轮）

1. V3-FIX-334 的实测确认路径：网关起栈+Redis 正常，同 request_id 二次发送观察 30s 内（缓存窗内）响应——预期收 duplicate_request 而非缓存重放；随后停引擎、杀 Redis 去重键、同 id 重发观察是否命中检查点恢复（fail-open 通道）。两项行为各一帧日志即可定案。
2. V3-FIX-335/336 的红测草图：构造写工具（create_task）→ mock 图执行完成该工具后进程中断 → 以新 request_id 重发同文本 → 断言 tasks 表行数。当前实现预期 +2（重复创建）。
3. 守卫计数如被引用，以 `grep -cv '^#\|^$' scripts/rule_guard_manifest.tsv` 现算为准，勿抄文档常数。
