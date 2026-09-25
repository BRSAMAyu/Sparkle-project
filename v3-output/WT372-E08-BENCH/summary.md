# WT372-E08 AI Stack 集成 Bench — Dashboard Summary

> 生成：2026-09-25T16:46:56+08:00 ｜ run_tag: `run` ｜ raw: `raw.jsonl`
> 引擎：常驻实例 127.0.0.1:50051/:8000（backend @ 0e4087ec，E-03 stage events 已含）。
> 驱动：guest JWT（user=`wt372_e08_bench`）→ gRPC StreamChat；真模型真路由，无 mock；失败不重试。

## 总量

| 指标 | 值 |
|---|---|
| 总查询 | 104 |
| 成功（无 error） | 103 |
| fallback/default 或出错 | 19 |
| quality 粗筛通过 | 65 |
| token 总量（prompt+completion） | 294768 |
| 计量成本合计（USD，官方价表） | $0.0117 |
| 单 query 均价 | $0.00011 |

## 分层（首要切片）

| 层 | n | ok | fallback | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/query | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 26 | 25 | 1 | 1.11 | 2.03 | 1.11 | 2.03 | 2.2 | 65.3 | 0.90 | 34791 | 0.0012 | 0.0000 | 20 |
| L1 | 26 | 26 | 2 | 1.95 | 2.95 | 1.99 | 3.38 | 22.2 | 32.9 | 3.06 | 97465 | 0.0039 | 0.0001 | 19 |
| L2 | 26 | 26 | 7 | 2.50 | 14.93 | 2.97 | 10.96 | 22.7 | 49.5 | 5.45 | 70979 | 0.0031 | 0.0001 | 18 |
| L3 | 26 | 26 | 9 | 7.26 | 113.36 | 6.79 | 112.84 | 28.8 | 113.0 | 7.03 | 91533 | 0.0035 | 0.0001 | 8 |

> TTFT=首个流式 delta；首内容=首个 delta 或 full_text（澄清门纯 full_text 路径计入）；首事件=任意帧（stage/ack）。

## lane 切片（free=免费层钳制 / pro=extra_context.user_tier=pro）

| lane | n | ok | fallback | TTFT p50 | TTFT p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|
| free | 78 | 77 | 11 | 1.89 | 10.53 | 18.8 | 60.8 | 5.01 | 225647 | 0.0089 | 51 |
| pro | 26 | 26 | 8 | 6.14 | 113.63 | 28.0 | 113.0 | 7.63 | 69121 | 0.0028 | 14 |

## observed tier/model 分布（token_usage 归因）

| model key | n | tiers | TTFT p50 | cost$ |
|---|---|---|---|---|
| dashscope_fast | 85 | ['fast'] | 2.03 | 0.0117 |
| default | 19 | ['?'] | 107.04 | 0.0000 |

## intent 切片

| intent | n | ok | fb | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/q | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ack | 6 | 6 | 0 | 1.06 | 1.29 | 1.06 | 1.29 | 2.0 | 19.6 | 0.49 | 8097 | 0.0003 | 0.0000 | 4 |
| attribution | 1 | 1 | 1 | - | - | 3.57 | 3.57 | 3.6 | 3.6 | 3.57 | 0 | 0.0000 | 0.0000 | 0 |
| code_review | 2 | 2 | 0 | 3.93 | 5.06 | 3.93 | 5.06 | 45.3 | 56.9 | 3.50 | 5896 | 0.0004 | 0.0002 | 2 |
| comparison | 3 | 3 | 1 | 2.61 | 3.00 | 3.04 | 4.76 | 18.3 | 25.7 | 4.66 | 6208 | 0.0003 | 0.0001 | 3 |
| concept_def | 16 | 16 | 1 | 1.91 | 2.66 | 1.93 | 3.79 | 22.2 | 31.1 | 2.36 | 62725 | 0.0024 | 0.0001 | 11 |
| continuation | 2 | 1 | 1 | 1.09 | 1.13 | 1.09 | 1.13 | 45.7 | 85.6 | 0.34 | 1346 | 0.0000 | 0.0000 | 2 |
| deep_analysis | 8 | 8 | 3 | 7.68 | 114.94 | 7.68 | 114.94 | 28.0 | 115.2 | 6.54 | 10093 | 0.0003 | 0.0000 | 2 |
| diagnose | 3 | 3 | 0 | 6.14 | 11.91 | 6.14 | 11.91 | 22.8 | 25.3 | 4.43 | 17088 | 0.0006 | 0.0002 | 1 |
| error_diagnosis | 1 | 1 | 0 | 2.50 | 2.50 | 2.50 | 2.50 | 14.3 | 14.3 | 1.55 | 2942 | 0.0001 | 0.0001 | 1 |
| experiment_design | 1 | 1 | 0 | 6.21 | 6.21 | 6.21 | 6.21 | 34.0 | 34.0 | 5.61 | 3216 | 0.0002 | 0.0002 | 1 |
| goal_check | 1 | 1 | 0 | 1.20 | 1.20 | 1.20 | 1.20 | 16.8 | 16.8 | 0.50 | 1563 | 0.0001 | 0.0001 | 0 |
| goal_eval | 1 | 1 | 0 | 1.71 | 1.71 | 1.71 | 1.71 | 8.9 | 8.9 | 0.88 | 3084 | 0.0001 | 0.0001 | 1 |
| greeting | 7 | 7 | 0 | 1.02 | 1.38 | 1.02 | 1.38 | 2.1 | 14.7 | 0.56 | 9597 | 0.0003 | 0.0000 | 5 |
| howto | 7 | 7 | 0 | 2.04 | 2.19 | 2.04 | 2.19 | 22.4 | 34.7 | 1.24 | 30374 | 0.0013 | 0.0002 | 6 |
| logic_check | 1 | 1 | 0 | 1.03 | 1.03 | 1.03 | 1.03 | 27.0 | 27.0 | 0.48 | 1830 | 0.0001 | 0.0001 | 1 |
| long_context_qa | 8 | 8 | 2 | 7.46 | 94.00 | 7.46 | 94.00 | 32.3 | 94.2 | 6.89 | 44137 | 0.0016 | 0.0002 | 4 |
| math_derive | 1 | 1 | 1 | - | - | 3.03 | 3.03 | 3.0 | 3.0 | 3.03 | 0 | 0.0000 | 0.0000 | 0 |
| memory_write | 4 | 4 | 0 | 1.34 | 1.50 | 1.34 | 1.50 | 1.9 | 28.9 | 0.75 | 5141 | 0.0002 | 0.0000 | 3 |
| persona_fact | 1 | 1 | 0 | 2.09 | 2.09 | 2.09 | 2.09 | 16.6 | 16.6 | 0.51 | 1382 | 0.0000 | 0.0000 | 1 |
| plan_eval | 1 | 1 | 1 | - | - | 5.24 | 5.24 | 5.2 | 5.2 | 0.19 | 0 | 0.0000 | 0.0000 | 0 |
| planning | 10 | 10 | 4 | 6.74 | 107.29 | 5.05 | 107.12 | 31.4 | 107.4 | 6.10 | 37303 | 0.0015 | 0.0002 | 2 |
| quick_fact | 4 | 4 | 0 | 1.63 | 1.85 | 1.63 | 1.85 | 2.1 | 14.6 | 1.07 | 6483 | 0.0002 | 0.0001 | 3 |
| quiz_gen | 1 | 1 | 1 | - | - | 3.42 | 3.42 | 3.4 | 3.4 | 3.42 | 0 | 0.0000 | 0.0000 | 1 |
| system_design | 1 | 1 | 1 | - | - | 3.32 | 3.32 | 3.3 | 3.3 | 3.31 | 0 | 0.0000 | 0.0000 | 0 |
| thanks | 2 | 2 | 0 | 30.06 | 56.24 | 30.06 | 56.24 | 38.6 | 72.1 | 0.61 | 2745 | 0.0001 | 0.0000 | 2 |
| theory_apply | 8 | 8 | 1 | 2.12 | 3.45 | 2.15 | 5.03 | 22.9 | 31.0 | 1.70 | 30329 | 0.0013 | 0.0002 | 7 |
| tradeoff | 2 | 2 | 1 | 36.33 | 36.33 | 19.05 | 34.60 | 28.2 | 52.0 | 28.98 | 1572 | 0.0001 | 0.0000 | 1 |
| writing_feedback | 1 | 1 | 0 | 1.29 | 1.29 | 1.29 | 1.29 | 22.7 | 22.7 | 0.33 | 1617 | 0.0001 | 0.0001 | 1 |

## persona 切片

| persona | n | ok | fb | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/q | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| beginner | 15 | 15 | 1 | 1.81 | 23.50 | 1.91 | 21.21 | 18.0 | 58.2 | 2.99 | 42825 | 0.0018 | 0.0001 | 13 |
| college_student | 23 | 23 | 3 | 2.12 | 8.63 | 2.12 | 8.45 | 19.4 | 41.5 | 2.27 | 49546 | 0.0021 | 0.0001 | 16 |
| exam_candidate | 19 | 19 | 3 | 2.65 | 14.93 | 3.25 | 10.65 | 22.4 | 36.1 | 8.56 | 43184 | 0.0018 | 0.0001 | 8 |
| professional | 16 | 16 | 4 | 2.01 | 103.47 | 1.87 | 102.63 | 22.6 | 102.8 | 4.71 | 49819 | 0.0019 | 0.0001 | 8 |
| researcher | 9 | 9 | 3 | 6.06 | 77.04 | 5.75 | 67.32 | 27.9 | 78.2 | 6.89 | 38077 | 0.0015 | 0.0002 | 6 |
| self_learner | 22 | 21 | 5 | 1.95 | 107.90 | 1.99 | 106.59 | 19.6 | 107.3 | 4.60 | 71317 | 0.0026 | 0.0001 | 14 |

## SLO 对照（Gate V3-8 候选目标）

| SLO | 实测 | 结论 |
|---|---|---|
| L0 no-model p95≤500ms | 2033ms (n=26) | FAIL |
| L1 首个有意义反馈 p50≤2.5s | 1.95s (n=26) | PASS |
| L1 p95≤5s | 2.95s (n=26) | PASS |
| L2 500ms 内阶段反馈（首事件 p95） | 4282ms (n=13, free lane) | FAIL |
| L2 最终 p95≤15s | 49.5s (n=26) | FAIL |
| L3 创建/ACK p95≤1s | 7.03s (n=26) | FAIL |

## Dynamic Issues（自动生成，不剪异常）

- **E08-ISS-L0-TTFT** [high] L0 快答路径 TTFT p95=2033ms > 目标 500ms（Gate V3-8）。问候/确认/快问仍走完整生成链（对应 E-01 W-2：TRIVIAL 不跳过生成），L0 no-model 直答未生效。
- **E08-ISS-L2-FEEDBACK** [high] L2 免费层首反馈 p95=4282ms > 目标 500ms（Gate V3-8 阶段反馈）。E-03 stage 前置已生效部分场景，但免费层 deep 档仍存在前置静默。
- **E08-ISS-L2-TOTAL** [medium] L2 最终回复 p95=49.5s > 目标 15s（思考档总时长超预算）。
- **E08-ISS-L3-ACK** [high] L3 Agent Run 首帧/ACK p95=7.03s > 目标 1s（Gate V3-8 创建/ACK）。编排轮首个用户可见反馈仍有秒级前置。
- **E08-ISS-FALLBACK** [high] 19 条 token_usage.model='default'（生成模型 key 未写入 response_builder/response_builder.py:948）：12 条 0 token=前置链澄清门/模板直出未进生成（无流式 delta，成本盲区）；7 条带 token=多代理（cognitive_prism）流的计量错挂 default，费用无法按模型定价（计 0，成本被低估）：
- **E08-ISS-ERROR** [high] 1 条查询出错（gRPC/引擎错误，全部如实记录，未重试掩盖）：
- **E08-ISS-TIER-COLLAPSE** [high] 全部计量生成塌缩到单一模型车道 ['dashscope_fast']——85/85 条带 token 的生成行均为该模型，pro 车道与 deep 档无一到达 standard/plus/max。控制探针（user_profile.is_pro=true+deep，request_id 见 evidence）仍被 adaptive_routing_engine.reorder_candidates 重排：[AdaptiveRouting] reorder head dashscope_standard_thinking -> dashscope_fast (samples>=8)（bench 窗口内该日志 90 次）。当前构建中 L1/L2/L3 的 tier 差异不存在，Gate V3-8 的分层成本/质量账本失效——深档请求实际按 fast 车道计延迟/成本/质量。
- **E08-ISS-QUALITY** [medium] 39 条未过启发式 quality 粗筛（空答/弃答/语言不符/低相关；粗筛口径声明于报告）：

## 口径与局限（如实声明）

- TTFT = 首个 text delta；首事件 = 任意帧（含 stage/status）；ACK 口径取 t_first_event。
- usage：优先 DB token_usage（含 model/tier/reasoning），缺行用流内 usage 帧；均缺记 none（见 issues）。
- cost = usage × 官方价表（下表）；引擎自身估算列于 raw（engine_cost_usd_db）作对照。
- 隐藏辅助调用（Layer3 分类/sufficiency/HyDE/planning）不在 token_usage 计量内——成本口径为「主生成计量成本」，辅助面成本为盲区（E-01 C5 已登记）。
- quality 为确定性启发式粗筛（非空/弃答/语言匹配/词面相关≥0.20），非模型评审；定位是筛异常，不是质量结论。
- 429/限流未重试；出现的错误全部保留在 raw.error 字段。
- 客户端为 gRPC 直连引擎（网关 :8080 纯透传 ≈0.02-0.35s，TTFT-PROBE 已测，未含入本口径）。
- 引擎为共享 dev 实例，并行 workers 的负载噪声无法完全排除；运行窗口见 raw 各条时间戳。

## 单价表（硬编码来源，USD per 1M tokens；CNY→USD 按 7.15）

| key | provider | provider model | in$ | out$ | source |
|---|---|---|---|---|---|
| dashscope_fast | dashscope | qwen3.7-flash | 0.0315 | 0.1362 | Aliyun help.aliyun.com qwen3.7-flash 模型价格页 2026-09-10（¥0.225/¥0.974 per M） |
| dashscope_chat | dashscope | qwen3.7-plus | 0.2797 | 1.1189 | Aliyun 百炼 qwen3.7-plus 列表价 2026-09 检索（¥2/¥8 per M，未计 8 折活动） |
| dashscope_standard_thinking | dashscope | qwen3.8-flash | 0.1119 | 0.3776 | Aliyun 百炼调价公告 2026-08-27 生效（¥0.8/¥2.7 per M） |
| dashscope_reason | dashscope | qwen3.8-flash | 0.1119 | 0.3776 | DASHSCOPE_REASON_MODEL 运行时解析（.env LLM_REASON_MODEL_NAME=qwen3.8-flash）；单价同 qwen3.8-flash 2026-08-27 价 |
| qwen3_8_max | dashscope | qwen3.8-max | 2.0000 | 6.0000 | Qwen3.8-Max 参考价 $2/$6 per M（llmpricing.dev 2026-09-12；官方 Model Studio 页未直接抓取，报告中标注） |
| qwen3_8_max_top | dashscope | qwen3.8-max | 2.0000 | 6.0000 | 同 qwen3_8_max（TOP 层同旗舰模型） |
| glm_4_7_flash_no_thinking | zhipu | glm-5.3-flash | 0.1119 | 0.3916 | BigModel 开放平台 glm-5.3-flash 列表价 2026-08 检索（¥0.8/¥2.8 per M，未计限时 5 折） |
| glm_4_7_flash_thinking | zhipu | glm-5.3-flash | 0.1119 | 0.3916 | 同 glm_4_7_flash_no_thinking |
| glm_4_7_pro | zhipu | glm-5.3-flash | 0.1119 | 0.3916 | glm_4_7_pro 运行时解析 ZHIPU_TOOLS_MODEL=.env glm-5.3-flash；单价同 glm-5.3-flash |
| deepseek_chat | deepseek | deepseek-flash(v4-flash 系) | 0.1399 | 0.2797 | DeepSeek V4-flash 系最低档 2026-04 检索（约 ¥1/¥2 per M）——近似值，已标记 approx |
| deepseek_reason | deepseek | deepseek-v4-pro | 0.4350 | 0.8700 | DeepSeek 官方 api-docs 2026-08-17 正式版价（$0.435/$0.87 per M） |
| default | none | no-generation(metered as default) | 0.0000 | 0.0000 | token_usage.model='default' = 生成模型 key 未写入（前置链模板/澄清门 0 token；或多代理流 metering 错挂）；计 0 并计 fallback（见 REPORT 归因） |

## 复跑

```bash
# 引擎常驻时（127.0.0.1:50051/:8000）
/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python \
  scripts/devtools/bench_ai_stack_l0_l3.py run --tag rerun1
# 汇总（重算 CSV/summary/issues）
... bench_ai_stack_l0_l3.py summarize --tag rerun1
```
