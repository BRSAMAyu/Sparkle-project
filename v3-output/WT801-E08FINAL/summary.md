# WT372-E08 AI Stack 集成 Bench — Dashboard Summary

> 生成：2026-09-28T11:05:43+08:00 ｜ run_tag: `e08final` ｜ raw: `raw-e08final.jsonl`
> 引擎：常驻实例 127.0.0.1:50051/:8000（backend @ 0e4087ec，E-03 stage events 已含）。
> 驱动：guest JWT（user=`wt372_e08_bench`）→ gRPC StreamChat；真模型真路由，无 mock；失败不重试。

## 总量

| 指标 | 值 |
|---|---|
| 总查询 | 104 |
| 成功（无 error） | 104 |
| fallback/default 或出错 | 0 |
| quality 粗筛通过 | 68 |
| token 总量（prompt+completion） | 347796 |
| 计量成本合计（USD，官方价表） | $0.1269 |
| 单 query 均价 | $0.00122 |

## 分层（首要切片）

| 层 | n | ok | fallback | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/query | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 | 26 | 26 | 0 | 1.08 | 1.78 | 1.08 | 1.78 | 2.1 | 21.2 | 0.05 | 35820 | 0.0013 | 0.0000 | 20 |
| L1 | 26 | 26 | 0 | 1.66 | 2.60 | 1.72 | 2.83 | 26.6 | 30.9 | 0.04 | 90417 | 0.0038 | 0.0001 | 19 |
| L2 | 26 | 26 | 0 | 1.90 | 8.33 | 2.50 | 5.97 | 29.6 | 65.4 | 0.04 | 81927 | 0.0218 | 0.0008 | 18 |
| L3 | 26 | 26 | 0 | 10.94 | 113.15 | 9.19 | 112.95 | 68.5 | 126.7 | 0.05 | 139632 | 0.1000 | 0.0038 | 11 |

> TTFT=首个流式 delta；首内容=首个 delta 或 full_text（澄清门纯 full_text 路径计入）；首事件=任意帧（stage/ack）。

## lane 切片（free=免费层钳制 / pro=extra_context.user_tier=pro）

| lane | n | ok | fallback | TTFT p50 | TTFT p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|
| free | 78 | 78 | 0 | 1.48 | 8.72 | 21.0 | 60.5 | 0.05 | 251221 | 0.0106 | 54 |
| pro | 26 | 26 | 0 | 7.90 | 113.25 | 66.0 | 126.7 | 0.05 | 96575 | 0.1163 | 14 |

## observed tier/model 分布（token_usage 归因）

| model key | n | tiers | TTFT p50 | cost$ |
|---|---|---|---|---|
| dashscope_fast | 68 | ['fast'] | 1.46 | 0.0106 |
| no_generation_model | 18 | ['?'] | 110.64 | 0.0000 |
| dashscope_chat | 12 | ['plus'] | 3.33 | 0.0251 |
| qwen3_8_max | 5 | ['max'] | 64.91 | 0.0905 |
| dashscope_standard_thinking | 1 | ['standard'] | 31.62 | 0.0007 |

## intent 切片

| intent | n | ok | fb | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/q | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ack | 6 | 6 | 0 | 0.99 | 1.19 | 0.99 | 1.19 | 1.8 | 13.6 | 0.03 | 8194 | 0.0003 | 0.0000 | 5 |
| attribution | 1 | 1 | 0 | - | - | 3.21 | 3.21 | 3.2 | 3.2 | 0.02 | 0 | 0.0000 | 0.0000 | 0 |
| code_review | 2 | 2 | 0 | 3.34 | 5.01 | 3.34 | 5.01 | 52.7 | 67.8 | 0.03 | 6506 | 0.0020 | 0.0010 | 2 |
| comparison | 3 | 3 | 0 | 1.71 | 1.76 | 1.77 | 4.03 | 27.6 | 32.6 | 0.03 | 6212 | 0.0003 | 0.0001 | 3 |
| concept_def | 16 | 16 | 0 | 1.60 | 2.23 | 1.66 | 2.67 | 25.2 | 30.4 | 0.04 | 42905 | 0.0019 | 0.0001 | 11 |
| continuation | 2 | 2 | 0 | 0.97 | 1.12 | 0.97 | 1.12 | 6.3 | 10.7 | 0.03 | 2546 | 0.0001 | 0.0000 | 2 |
| deep_analysis | 8 | 8 | 0 | 91.16 | 115.61 | 91.16 | 115.61 | 114.4 | 146.2 | 0.06 | 25090 | 0.0905 | 0.0113 | 1 |
| diagnose | 3 | 3 | 0 | 2.21 | 4.40 | 2.21 | 4.40 | 28.4 | 57.9 | 0.04 | 7137 | 0.0019 | 0.0006 | 1 |
| error_diagnosis | 1 | 1 | 0 | 1.89 | 1.89 | 1.89 | 1.89 | 16.4 | 16.4 | 0.01 | 2819 | 0.0001 | 0.0001 | 1 |
| experiment_design | 1 | 1 | 0 | 4.14 | 4.14 | 4.14 | 4.14 | 55.4 | 55.4 | 0.02 | 16032 | 0.0047 | 0.0047 | 0 |
| goal_check | 1 | 1 | 0 | 0.94 | 0.94 | 0.94 | 0.94 | 30.9 | 30.9 | 0.04 | 1915 | 0.0001 | 0.0001 | 0 |
| goal_eval | 1 | 1 | 0 | 1.97 | 1.97 | 1.97 | 1.97 | 13.2 | 13.2 | 0.01 | 3363 | 0.0015 | 0.0015 | 1 |
| greeting | 7 | 7 | 0 | 1.07 | 2.46 | 1.07 | 2.46 | 3.8 | 12.3 | 0.29 | 9302 | 0.0003 | 0.0000 | 5 |
| howto | 7 | 7 | 0 | 1.80 | 2.50 | 1.80 | 2.50 | 27.2 | 32.5 | 0.04 | 42669 | 0.0017 | 0.0002 | 6 |
| logic_check | 1 | 1 | 0 | 1.82 | 1.82 | 1.82 | 1.82 | 53.3 | 53.3 | 0.01 | 2454 | 0.0010 | 0.0010 | 1 |
| long_context_qa | 8 | 8 | 0 | 8.35 | 104.52 | 8.35 | 104.52 | 53.1 | 104.7 | 0.05 | 33777 | 0.0060 | 0.0007 | 5 |
| math_derive | 1 | 1 | 0 | - | - | 3.72 | 3.72 | 3.7 | 3.7 | 0.03 | 0 | 0.0000 | 0.0000 | 1 |
| memory_write | 4 | 4 | 0 | 1.19 | 1.23 | 1.19 | 1.23 | 12.0 | 43.6 | 0.03 | 5278 | 0.0002 | 0.0000 | 3 |
| persona_fact | 1 | 1 | 0 | 1.18 | 1.18 | 1.18 | 1.18 | 16.4 | 16.4 | 0.01 | 1369 | 0.0000 | 0.0000 | 1 |
| plan_eval | 1 | 1 | 0 | - | - | 4.72 | 4.72 | 4.7 | 4.7 | 0.02 | 0 | 0.0000 | 0.0000 | 0 |
| planning | 10 | 10 | 0 | 4.06 | 108.36 | 2.87 | 107.70 | 56.2 | 107.9 | 0.04 | 80765 | 0.0035 | 0.0004 | 5 |
| quick_fact | 4 | 4 | 0 | 1.00 | 1.66 | 1.00 | 1.66 | 2.0 | 16.5 | 0.03 | 6686 | 0.0002 | 0.0001 | 2 |
| quiz_gen | 1 | 1 | 0 | - | - | 4.98 | 4.98 | 5.0 | 5.0 | 0.04 | 0 | 0.0000 | 0.0000 | 1 |
| system_design | 1 | 1 | 0 | - | - | 3.18 | 3.18 | 3.2 | 3.2 | 0.03 | 0 | 0.0000 | 0.0000 | 0 |
| thanks | 2 | 2 | 0 | 1.00 | 1.07 | 1.00 | 1.07 | 2.1 | 2.1 | 0.05 | 2445 | 0.0001 | 0.0000 | 2 |
| theory_apply | 8 | 8 | 0 | 1.90 | 4.82 | 2.11 | 5.94 | 41.9 | 64.6 | 0.04 | 34897 | 0.0096 | 0.0012 | 7 |
| tradeoff | 2 | 2 | 0 | 31.62 | 31.62 | 17.31 | 30.18 | 24.7 | 44.1 | 0.01 | 3828 | 0.0007 | 0.0004 | 1 |
| writing_feedback | 1 | 1 | 0 | 1.07 | 1.07 | 1.07 | 1.07 | 30.0 | 30.0 | 0.01 | 1607 | 0.0001 | 0.0001 | 1 |

## persona 切片

| persona | n | ok | fb | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/q | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| beginner | 15 | 15 | 0 | 1.47 | 2.40 | 1.72 | 3.45 | 17.4 | 35.5 | 0.04 | 42884 | 0.0031 | 0.0002 | 14 |
| college_student | 23 | 23 | 0 | 1.74 | 104.14 | 1.75 | 94.52 | 23.9 | 107.4 | 0.05 | 68616 | 0.0330 | 0.0014 | 16 |
| exam_candidate | 19 | 19 | 0 | 1.87 | 33.30 | 2.07 | 32.29 | 29.4 | 81.5 | 0.05 | 70106 | 0.0285 | 0.0015 | 12 |
| professional | 16 | 16 | 0 | 1.48 | 108.63 | 1.63 | 107.89 | 26.6 | 108.1 | 0.04 | 50077 | 0.0036 | 0.0002 | 8 |
| researcher | 9 | 9 | 0 | 8.79 | 96.92 | 6.05 | 92.35 | 52.0 | 113.4 | 0.03 | 45918 | 0.0296 | 0.0033 | 6 |
| self_learner | 22 | 22 | 0 | 1.86 | 104.11 | 1.90 | 103.99 | 24.8 | 116.3 | 0.07 | 70195 | 0.0290 | 0.0013 | 12 |

## SLO 对照（Gate V3-8 候选目标）

| SLO | 实测 | 结论 |
|---|---|---|
| L0 no-model p95≤500ms | 1781ms (n=26) | FAIL |
| L1 首个有意义反馈 p50≤2.5s | 1.66s (n=26) | PASS |
| L1 p95≤5s | 2.60s (n=26) | PASS |
| L2 500ms 内阶段反馈（首事件 p95） | 42ms (n=13, free lane) | PASS |
| L2 最终 p95≤15s | 65.4s (n=26) | FAIL |
| L3 创建/ACK p95≤1s | 0.05s (n=26) | PASS |

## Dynamic Issues（自动生成，不剪异常）

- **E08-ISS-L0-TTFT** [high] L0 快答路径 TTFT p95=1781ms > 目标 500ms（Gate V3-8）。问候/确认/快问仍走完整生成链（对应 E-01 W-2：TRIVIAL 不跳过生成），L0 no-model 直答未生效。
- **E08-ISS-L2-TOTAL** [medium] L2 最终回复 p95=65.4s > 目标 15s（思考档总时长超预算）。
- **E08-ISS-QUALITY** [medium] 36 条未过启发式 quality 粗筛（空答/弃答/语言不符/低相关；粗筛口径声明于报告）：

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
