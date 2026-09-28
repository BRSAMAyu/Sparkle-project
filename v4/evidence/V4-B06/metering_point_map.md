# V4-B06 计量点地图（I10 依赖产出）

captured_at: 2026-09-28T09:18-09:23Z ｜ 活栈: Sparkle-project @ 3c4618cc（引擎 PID 77460 grpc_server.py，网关 PID 77602 :8080）
所有路径相对 `backend/`。行号为当日源码快照，集成时以 SHA 为准。

## 1. 现有计量写入点

| # | 点位 | 位置 | 计什么 | 已知缺口 |
|---|---|---|---|---|
| M1 | 根请求计量 | `app/orchestration/response_builder.py` `_cleanup` (L1619-1701) | 每次	process_stream 结束：`resolve_metering_model_key` 归因 → `token_tracker.record_usage`（tokens、estimated cost、chat_mode、tier、timing） | tokens 优先来自生成流 usage 帧；为 0 且有 final_state 时走**合成估算**（L1652-1661）——估算发生在归因判定之后，产生「no_generation_model 标签 + 估算 token>0」行（FIX545 形状） |
| M2 | 归因补全 | `app/orchestration/response_builder.py` L44-68 | `no_generation_model`（无真实用量）/`unattributed_model`（有用量无归因）显式标签 | 只解决「default 桶」；**无任何下游检出器**发现「no_generation_model 且 tokens>0」（自测 A3 NOT_FOUND） |
| M3 | TokenTracker | `app/orchestration/token_tracker.py` | Redis 日用量/分模式/分模型统计、quota 检查（默认 100k tok/日）、`estimate_cost` | `estimate_cost`（L493-524）：模型键不在 router → **静默替换 gpt-4 定价**；`no_generation_model`/`unattributed_model` 也被按 gpt-4 定价（自测 A4：42 tok → $0.00126 错价）。违反「未知价格不填 0」，且是填**错价**而非 0 |
| M4 | BillingWorker | `app/services/billing_worker.py` | 用量记录批量落库 + 重试 + dead-letter | 无 reserve/settle；无重放幂等键语义（I10 验收项） |
| M5 | Cost guard（面1） | `app/core/llm_quota.py` L570 | 每用户估算 token 扣减 | `model="gpt-4"` 硬编码标签 |
| M6 | Cost guard（面2） | `app/core/llm_security_wrapper.py` `_record_usage` (L274-280) | 各安全包装调用按输出文本估 token | 估算制；embedding 记 `model or "embedding"`（L545）；与 M1/M3 是**两本账**，无 root_request 关联 |
| M7 | 后台任务 | `app/core/celery_tasks.py` L300 | celery 内 record_usage | 同 M3 缺口 |
| M8 | 客户端用量回执 | gRPC `Usage{prompt,completion,total,cost_micro_usd}` → 网关 `usage` 帧 | 前台回执 | 探针 T1/T2：回执 `cost_micro_usd=0` 而内部账本已记 $0.000144——**两账不一致**；T3（rescue）无回执但内部记账 |

## 2. 指标标签：gRPC vs 整链（验收项 3，已满足）

- 引擎侧（gRPC 进程）：`sparkle_request_latency_seconds{module,method}`、`AI_RESPONSE_TOTAL_DURATION{chat_mode,reasoning_mode,model_tier}`、`sparkle_llm_call_duration_seconds{model,provider}`（`app/core/metrics.py`）；逐 hop `[LATENCY]` 探针（`app/orchestration/latency_probe.py`，含 trace_id）。
- 网关侧（整链）：`sparkle_ai_chat_{total,first_event,first_token,stream}_duration_seconds{chat_mode}`（`gateway/internal/metrics/ws_metrics.go` L140-165）。
- 两套序列名不重叠、标签集不同（引擎有 model_tier，网关只有 chat_mode）→ 满足「分开」；**但网关 `chat_mode` 是唯一标签，无法按模型分层看整链首 token**（记录为 I10/观测面增量项）。

## 3. 隐藏模型调用面（前台/后台预算清单）

- 前台链（root_request 的 attempt 面）：classify（`routing_engine`，rule_fast_path 或 LLM）、sufficiency（`sufficiency_checker`）、generation（含 rescue 二次调用，`standard_workflow.py` L845 `_build_mode_rescue_response` **真实再烧一次上游**）、review、reflection、tool 模型、first-touch。
- 服务层直接消费：`llm_service/LLMService` 67 个文件（清单 `hidden_llm_consumer_files.txt` 前 67 行）；embedding 面 23 个文件（后追加行）；stt/tts/ocr/translation 12 文件；tier 显式消费者 12 文件。
- 后台批处理：glm_batch 车道 provider=`BATCH_LLM_PROVIDER=minimax`（活栈实证 MiniMax-M3 注册，`minimax_m3_batch`/`qwen3_7_flash_batch`），唯一显式预算 = `MINIMAX_RPM_BUDGET=200`（Redis 60s 窗口，引擎+worker 共享）；celery beat 定时任务（learning-profile 刷新、intervention outcomes、absence scan、capsule 等约 20+ 任务）。
- 预算语义现状：**只有 RPM 限速，无 root_request 级 reserve/settle、无离线/在线分账**（LATENCY_COST_RUNTIME「完整费用」要求项全部缺口，属 I10）。

## 4. 本卡探针实证的计量缺陷（I10 输入）

1. **T3 rescue 双调用计量失真**：问候语触发生成流 400（上游 `USER is not one of ['system','assistant','user','tool','function']`）→ rescue 非流式真实调用成功 → 内部账本仅记**合成估算** 2+42=44 tok/$0.000004（标签 dashscope_fast），rescue 真实用量无回执无实账；客户端 0 usage 帧。
2. **回执 cost 恒 0**：真实生成 T1/T2 回执 `cost_micro_usd=0`，内部账本 $0.000144/$0.000132。
3. **未知/非模型键错价**：`no_generation_model` 42 tok 被按 gpt-4 价格记 $0.00126（A4）。
4. **FIX545 检出缺失**：全 app 无「no_generation_model 且 tokens>0」检出器（A3）。
5. 上一轮 S06 报告的 7 条「带 token 的 no_generation_model」在当前代码（3c4618cc）仍可复现其产生机制（M1 合成估算 + M2 判定时序），未被修复也未被检出——按「当前仓库实证 > 本包快照」如实记录为仍开放，归 I10 修。

## 5. 全链测量基线种子数据（本次 3 样本，2026-09-28 17:18-17:19 本地）

| 样本 | t_ack | t_first_visible(整链首token) | t_done | 真实模型 | usage(实账) | usage(回执) |
|---|---|---|---|---|---|---|
| t1 生成 min | 0.017s | 2.818s | 17.213s | qwen3.7-flash (fast) | 1369+72 tok，$0.000144(内部) | 1369+72，cost=0 |
| t2 生成 fast | 0.001s | 1.093s | 20.969s | qwen3.7-flash (fast) | 1245+76 tok，$0.000132(内部) | 1245+76，cost=0 |
| t3 问候(rescue) | 0.002s | 1.858s | 1.990s | 1 失败 + 1 rescue 成功 | 估算 44 tok $0.000004 | 无 usage 帧 |

p95 结论不可下（n=3 种子）；与 S05/S06 的 gRPC-only 口径不同，本表为 **Flutter→网关整链口径**（对齐网关 first_token 指标定义）。
