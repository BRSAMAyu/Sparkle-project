# Round2 — 对话首字延迟优化（first-token latency）

> 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt5`（基线 commit `35b29ba5`，未 commit）
> 实测方式：题目给定的 WS 全链路复现脚本（guest 登录 → /ws/chat → 同一问候消息「你好，简单介绍下你能做什么」），DeepSeek 真实 key，每次运行使用全新 guest 用户 + 全新 session（即"新会话首条消息"这一最差真实场景）。WS 请求总数 ≤ 15。

## 1. 延迟画像（优化前，引擎日志 [LATENCY] 计时）

在 `orchestrator.process_stream` 的每个串行跳、`_route_and_classify` 的统一路由、`_plan_and_validate` 的规划器、执行图四个节点（context_builder / retrieval / router / generation）以及 `_build_user_context` 内部全部加了计时代码（`app/orchestration/latency_probe.py` + `[LATENCY]` 日志），实测三轮：

| 跳（优化前） | b1（冷） | b2 | b3 |
|---|---|---|---|
| debrief_check | 3ms | 2ms | 2ms |
| **build_full_context** | **30,342ms** | **12,874ms** | **25,198ms** |
| ├ build_user_context | 29,911ms | 12,542ms | 25,198ms |
| │ ├ prism_parallel_queries（5 路并行） | **29,289ms** | **11,744ms** | — |
| │ │ └ **learning_gaps_summary** | 占满 | **11,719ms** | 占满 |
| │ ├ personalization_llm_profile | 215ms | 747ms | — |
| │ └ context_orchestrator.get_user_context | 184ms | 191ms | — |
| spine_pipeline | 89ms | 80ms | 3ms |
| route_and_classify（统一路由） | 22ms | 26ms | 16ms |
| dual_core_routing | 78ms | 144ms | 58ms |
| plan_and_validate（规划） | 312ms | 119ms | 46ms |
| execute_graph | 9,044ms | 16,439ms | 7,740ms |
| **首字（first_text）** | **37.6s** | **26.9s** | **31.0s** |

### 定位出的三个真凶

1. **隐藏 LLM 调用在上下文构建里（最大头，10–30s）**：`_build_user_context → _build_learning_gaps_summary → SeedExtractor.get_cached_or_generate`。种子缓存 TTL 仅 5 分钟且按 user 隔离——新用户/过期后必然走 `extract_seeds`：6 个串行来源查询 + **`_refine_with_llm`（`analysis_llm.json_call` → glm-4.6 batch，实测单次 11.7–14s+）**，而这一切只为产出一条 ≤300 字符的"学习缺口摘要"。引擎日志可见回合开始处 `glm_4_6_batch` 调用吞掉 14s。
2. **会话首条消息必付一次路由 LLM**：`UnifiedIntentRouter._should_skip_llm_assist` 里 `if not conversation_history: return False`——空历史（恰好是新会话第一条）强制进入 Layer-3 LLM 意图分类（一次串行 LLM 往返）。
3. **上下文构建全串行**：personalization（~0.9s）与认知上下文（~0.6s）等逐个 await；且整份 user context 每条消息重建（热态 ~2.2s）。

规划跳本身**没有**阻塞简单消息：chat 意图 + `execution_mode=direct` 时 `plan_and_validate` 早退（46–312ms，LangGraph 规划器不执行），双核路由有「通用知识问答优先直接回答」短路（78–242ms）。执行图内部也很干净：retrieval 7ms / router 12–35ms / generation pre_prep 0ms。

**剩余无法回避的部分**：DeepSeek（reasoning 流）首个 text token 前的 provider TTFT，实测 5.6–32s 波动（含一次 glm_4_7_plus 429 降级到 qwen3.6-plus）。这是模型/供应商侧，不在编排链内，也不属于本次可动红线（换模型=产品语义变更，见 §5 建议）。

## 2. 改动清单（FT-LAT-1..5，产品语义不降级）

| # | 文件 | 改动 |
|---|---|---|
| FT-LAT-1 | `app/orchestration/context_builder.py` | `_build_learning_gaps_summary`：跳过种子 LLM refine（`allow_llm_refine=False`，启发式排序确定性产出同样 ≤300 字摘要，种子内容不变），摘要按 user 加 Redis 缓存（TTL 300s，含空值负缓存） |
| FT-LAT-2 | `app/core/unified_intent_router.py` | `_should_skip_llm_assist`：删除「空历史强制 LLM 分类」；简单消息短路（chat 意图 + 置信度 ≥0.5 + ≤120 字 + 非复杂 + 无动作词五个守卫不变）——复杂/操作类消息仍走 LLM 辅助分类 |
| FT-LAT-3 | `app/orchestration/context_builder.py` | user context 会话级缓存（进程内 per-user，TTL 120s，deepcopy 隔离读写，128 用户 LRU 淘汰）——"首条消息后复用"，后续消息 5ms 命中 |
| FT-LAT-4 | `app/orchestration/context_builder.py` | personalization 分支与认知上下文分支无依赖，`asyncio.gather` 并行（独立 DB session，只读） |
| FT-LAT-5 | `app/agents/standard_workflow.py` | 首个 text delta 立即 flush（不被 96 字符批量窗口挡住），后续 delta 保持原批处理 |
| 观测 | `app/orchestration/latency_probe.py`（新）+ orchestrator/routing_engine/execution_engine/context_builder/standard_workflow | `[LATENCY]` 全链计时日志（本次画像工具，保留为长期观测） |

单测：`backend/tests/unit/test_unified_intent_router_fast_path_first_message.py`（5 条）。核心断言 `test_route_uses_fast_path_for_simple_first_message_without_llm`：**短路路径不调用规划（Layer-3 `_llm_classify` spy 计数为 0）**，且 `execution_mode=direct`、`routing_layer=rule_fast_path`；复杂消息断言仍走 LLM 辅助；动作词守卫断言不短路。连同既有 fast-path/routing/helpers 用例共 **23 passed**。

## 3. 优化前后对比（同一脚本、同一问候消息、各 3 次全新用户/会话）

| 指标 | 优化前 b1/b2/b3 | 优化前均值 | 优化后 o1/o2/o3 | 优化后均值 | 变化 |
|---|---|---|---|---|---|
| **首字 first_text** | 37.6 / 26.9 / 31.0 s | **31.8s** | 34.9 / 13.1 / 23.0 s | **23.7s** | **−26%** |
| **编排侧首字前开销**（build_full_context + 路由/双核/规划 + 图内预处理，剔除 provider TTFT） | 30.8 / 13.2 / 25.4 s | **23.1s** | 2.76 / 1.36 / 1.71 s | **1.94s** | **−92%** |
| build_full_context | 30.3 / 12.9 / 25.2 s | 22.8s | 2.0 / 0.32 / 0.60 s | 0.97s | −96% |
| 同会话第二条消息 build_full_context | ~2.3s（全量重建） | — | **0.29s（缓存命中）** | — | −87% |
| 隐藏种子 LLM（learning_gaps） | 11.7–29.3s | — | 12–23ms | — | ~−99.9% |
| 路由 LLM（首条消息） | 1 次串行调用 | — | 0（rule_fast_path） | — | 消除 |
| provider 首 token TTFT（不可控项） | 5.6–13.4s | — | 11.7–32.1s | — | 当晚 DeepSeek/qwen 波动 + 一次 429 降级 |
| total | 40.3 / 30.1 / 33.2 s | 34.5s | 37.8 / 28.0 / 26.3 s | 30.7s | −11% |

> 注：端到端首字均值受 provider TTFT 波动影响明显（优化后测试窗口恰好赶上更慢的 provider 时段与一次 429 降级），编排侧开销（本任务可控部分）从 **23.1s → 1.9s（−92%）** 是稳定、可复现的收益；端到端数字随 provider 状态波动。

## 4. 红线核对

- 未改任何提示词内容（`prompts.py`、system prompt 拼装逻辑零改动）；
- 未砍编排功能：复杂/多步/操作类消息仍走 LLM 辅助分类 → langgraph → LangGraphPlanner 全链（守卫单测覆盖）；spine、双核、sufficiency、goal-quality、Aurora、成长卡等全部保留；
- 引擎保持运行（wt5 起的进程，:50051），网关未动。

## 5. 后续建议（超出本次红线，未实施）

- **轻量消息的生成模型分层**：当前 simple chat 也走 reasoning 流模型（首个 text 前 reasoning 阶段 5–30s，是现在首字的最大项）。`standard_workflow` 已有 `force_fast_first_touch`/ModelTier.FAST 机制，若产品允许"轻量问候走非 reasoning 快档"，首字可再降一个数量级。
- DeepSeek 429 降级链路（glm_4_7_plus → qwen3.6-plus）失败重试也计入首字，可考虑预热健康度探测。
