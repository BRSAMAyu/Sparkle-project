# WT372-E08 REPORT — AI Stack 集成 Bench（Quality × TTFT × Cost × Context，L0-L3）

> 2026-09-25 ｜ Worker wt372 ｜ worktree `Sparkle-sysrev/wt372-e08-bench`（base `0e4087ec`，本提交为唯一交付提交）
> 交付物：`REPORT.md`（本文）+ `raw.jsonl`（104 条全字段原始记录）+ `raw.csv` + `summary.md`（dashboard）+ `facts.json` + `dynamic_issues.json`（8 条）
> 复跑脚本：`scripts/devtools/bench_ai_stack_l0_l3.py`（`run` / `summarize` 子命令，`--help` 可用）
> **所有数字均由 raw.jsonl 经 summarize 程序计算（facts.json / summary.md），无手填。**

---

## 1. 运行环境与真源

| 项 | 值 |
|---|---|
| 被测引擎 | 常驻实例 127.0.0.1:50051（gRPC）/ :8000（FastAPI），backend @ `0e4087ec`（main，E-03 stage events 已含），PID uvicorn 5426 / grpc 39370 |
| 客户端 | 主仓 backend/.venv，guest JWT（专用账号 `wt372_e08_bench`，guest seeding 真实数据）→ gRPC StreamChat 直连（网关 :8080 纯透传 ≈0.02-0.35s 不在口径内，TTFT-PROBE 已测） |
| DB 归因 | `docker exec sparkle_db psql` 查 `token_usage`（model/model_tier/ai_reasoning_mode/tokens/cost），104/104 归因成功 |
| 运行方式 | 串行（并发=1），逐条落盘，失败不重试；运行窗口 12:08:00–12:53:19（引擎日志首末请求；流式时长合计 2635.9s≈44min），对照探针 16:43 |
| 限流 | 429/RESOURCE_EXHAUSTED 出现 **0 次**（如实记录口径，非掩盖） |

## 2. 语料与分层配比（每层 26，共 104）

| 层 | 设计意图 | 驱动方式 | n |
|---|---|---|---|
| L0 快答 | 问候/确认/致谢/快问快答/记忆写入指令 | reasoning_mode=fast, chat_mode=standard | 26 |
| L1 标准 | 单概念解释/方法/how-to（≤120字） | reasoning_mode=fast, chat_mode=standard | 26 |
| L2 深推理 | 对比/诊断/推导/代码审查/论证审查 | reasoning_mode=deep（free 13 / pro 13），error_diagnosis 1 条 | 26 |
| L3 编排·长上下文 | 学习计划编排 10 + 长材料 QA 8 + deep_analysis 8 | chat_mode=study_plan/deep_analysis；长材料 800-2500 字（free 13 / pro 13） | 26 |

语料为学习成长域真实多样中文/英文/中英混合（考研、雅思、高数、单词、笔记法、动机、编程），persona 六类（beginner/college_student/exam_candidate/professional/researcher/self_learner），intent 30 类。会话 3 turn 轮换（33 sessions），session_turn 入 raw。

**如实声明（跑前未知、跑后证实）**：`extra_context.user_tier=pro` 覆盖因 `MessageToDict` camelCase 转换（`agent_grpc_service.py:282` 读 `user_tier`，实际键为 `userTier`）为死代码——本 bench 的 pro 车道实际未被引擎识别为 pro；补充的 `user_profile.is_pro=true` 控制探针证实即使真 pro 信号也被塌缩（见 §7-A）。

## 3. 总量与成功率

| 指标 | 值 |
|---|---|
| 总查询 | 104 |
| 成功（无 error） | 103（99.0%） |
| 错误 | 1：L0-21（“嗯，继续吧”）`DEADLINE_EXCEEDED`@90s——流式已出 281 字后被引擎 90s 超时切断，未重试 |
| token_usage.model='default' | 19（归因见 §6） |
| 429/RESOURCE_EXHAUSTED | 0 |
| 计量生成模型分布 | dashscope_fast 85（85/85 带token生成行）+ default 19（12 条 0 token + 7 条带 token 错挂） |

## 4. 分层延迟（TTFT=首流式 delta；首内容=首 delta 或 full_text；首事件=任意帧）

| 层 | ok | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | quality粗筛通过 |
|---|---|---|---|---|---|---|---|---|---|
| L0 | 25/26 | 1.11s | 2.03s | 1.11s | 2.03s | 2.19s | **65.27s** | 0.90s | 20/26 |
| L1 | 26/26 | 1.95s | 2.95s | 1.99s | 3.38s | 22.19s | 32.92s | 3.06s | 19/26 |
| L2 | 26/26 | 2.50s | 14.93s | 2.97s | 10.96s | 22.68s | **49.46s** | 5.45s | 18/26 |
| L3 | 26/26 | 7.26s | **113.36s** | 6.79s | **112.84s** | 28.81s | **113.03s** | 7.03s | 8/26 |

尾部证据：L0 total p95=65.27s 由 L0-22（“谢谢你，很有帮助”被拉入 planning/processing 多阶段链，TTFT 59.1s）+ L0-21（90s DEADLINE）构成；L3 TTFT p95≈113s 为 deep_analysis 的 cognitive_prism 多代理循环（L3-26 latency hops 实测：`check_sufficiency=876ms → plan_validate=4226ms → execute_graph=110858ms`，graph 内 error_analyst/deep_analyst/math_agent 等每代理约 10s 串行）。

## 5. 成本（官方单价表，脚本硬编码并注明来源日期；CNY→USD 按 7.15）

| 层 | tokens(prompt+completion) | cost | cost/query |
|---|---|---|---|
| L0 | 34,791 | $0.0012 | $0.000046 |
| L1 | 97,465 | $0.0039 | $0.000150 |
| L2 | 70,979 | $0.0031 | $0.000119 |
| L3 | 91,533 | $0.0035 | $0.000135 |
| **合计** | **294,768** | **$0.011688** | **$0.000112** |

- 单价表（主要项，全表见 summary.md）：qwen3.7-flash ¥0.225/¥0.974 per M（Aliyun 文档 2026-09-10）；qwen3.8-flash ¥0.8/¥2.7（百炼调价 2026-08-27）；glm-5.3-flash ¥0.8/¥2.8（BigModel 2026-08 列表价）；deepseek-v4-pro $0.435/$0.87（api-docs 2026-08-17）；qwen3.8-max $2/$6（llmpricing.dev 2026-09-12，官方页未直接抓取，已标注）。
- **成本为下界**：①7 条多代理流的 token 错挂 `default` 按价表计 0；②隐藏辅助调用（Layer3 分类/sufficiency/HyDE/goal_quality/各代理间调度）不在 token_usage 计量内（E-01 C5 观测缺口），仅主生成计量。

## 6. fallback/失败分布（不剪异常）

| 类别 | n | 明细 |
|---|---|---|
| 澄清门模板直出（0 token，无流式 delta） | 12 | goal_quality 门触发 `requires_goal_clarification` → 模板 full_text（约 3s），生成模型从未运行：L0-21, L1-03, L1-17, L2-08~11, L2-20/21/25, L3-04, L3-09 |
| 多代理流计量错挂 default（带 token） | 7 | cognitive_prism/study_plan 流未写 `generation_model_key`（`response_builder.py:948` 落 `or "default"`）：L3-06/08/15/18/21/23/26，token 40~1479，费用无法按模型定价（计 0） |
| gRPC 错误 | 1 | L0-21 DEADLINE_EXCEEDED@90s（与上一行同源：前置链 + 生成未完成） |
| provider 429/限流 | 0 | — |

## 7. 机制发现（引擎日志佐证，非推测）

- **A. Tier 塌缩（本 bench 最重要的 V3 决策输入）**：104 条中 85/85 条带 token 的生成行全部为 `dashscope_fast`（qwen3.7-flash，tier=fast）——pro 车道、deep 档、study_plan/deep_analysis 无一到达 standard/plus/max。控制探针 `wt372-e08-probe-ispro-84715b`（`user_profile.is_pro=true` + deep）仍被重排：
  `app.core.adaptive_routing:reorder_candidates:228 - [AdaptiveRouting] reorder head dashscope_standard_thinking -> dashscope_fast (samples>=8)`（bench 窗口内该日志 90 次）。
  持久化贝叶斯自适应路由（samples>=8 置信）把链头稳定翻到 fast，**L1/L2/L3 的 tier 差异在当前构建中不存在**——Gate V3-8 的“每 tier 成本/延迟/质量账本”被这个机制整体失效化；深档请求的质量上限被 fast 车道封顶。
- **B. pro 覆盖死键**：`agent_grpc_service.py:282` `MessageToDict(request.extra_context)` 产出 camelCase（`userTier`），而 `_resolve_request_user_tier` 读 `user_tier`——extra_context.user_tier 覆盖永不生效（本 bench 26 条 pro 车道全部按 free 处理的直接原因）。
- **C. 多代理 fan-out 丢失 pro 信号**：同一请求内主生成选中 standard（log：`Agent策略路由: generation -> dashscope_standard_thinking [tier=standard]`），随后子代理全部 `free_tier_downgrade: pro -> fast (agent=deep_analyst, task=deep_reasoning)`——contextvar 的 tier 信号未跨代理任务边界传播（或代理线程池新 context 默认 free），与 A 叠加使深档彻底不可达。
- **D. E-03 stage 前置的覆盖边界**：L0/L1 首事件 p95 0.90s/3.06s 部分受益于 500ms 前置 ack；但 L2 免费层 deep 首事件 p95=5.45s（>500ms）、L3 ACK p95=7.03s（>1s）——编排/深档轮的首个用户可见反馈仍秒级，S18“有反馈无进度”在深档仍存在。
- **E. 澄清门不流式**：12 条澄清门回答全部无 delta（full_text 一次直出）。反馈出现快（~3s）但打字机流式为零，且这些 turn 的辅助 LLM 成本（goal_quality 调用）不在计量内。

## 8. SLO 对照（Gate V3-8 候选目标 → 结论）

| SLO | 实测（n） | 结论 |
|---|---|---|
| L0 no-model 路径 p95 ≤500ms | TTFT p95=2033ms（26） | **FAIL**——问候/确认/快问全走生成链（E-01 W-2 未修，无 no-model 直答） |
| L1 首个有意义反馈 p50 ≤2.5s | 1.95s（26） | **PASS** |
| L1 p95 ≤5s | 2.95s（26） | **PASS** |
| L2 500ms 内阶段反馈（首事件 p95） | 5446ms（free 车道 13） | **FAIL** |
| L2 最终 p95 ≤15s | 49.46s（26） | **FAIL** |
| L3 Agent Run 创建/ACK p95 ≤1s | 7.03s（26） | **FAIL** |

**结论：6 项 SLO 达标 2 项（均为 L1）；L0/L2/L3 全部未达。** 且在 Tier 塌缩（§7-A）下，“达标”的 L1 与“未达”的 L2/L3 实际共用同一模型车道——当前主要矛盾是路由/编排/自适应机制，而非模型品牌。

## 9. Dynamic Issues（dynamic_issues.json，8 条，自动生成）

| id | severity | 摘要 |
|---|---|---|
| E08-ISS-TIER-COLLAPSE | high | 全部计量生成塌缩 dashscope_fast；is_pro 控制探针仍被 adaptive reorder；tier 账本失效 |
| E08-ISS-L0-TTFT | high | L0 TTFT p95=2033ms > 500ms；TRIVIAL 不跳过生成 |
| E08-ISS-L2-FEEDBACK | high | L2 免费层首反馈 p95=5446ms > 500ms |
| E08-ISS-L2-TOTAL | medium | L2 最终 p95=49.46s > 15s |
| E08-ISS-L3-ACK | high | L3 ACK p95=7.03s > 1s |
| E08-ISS-FALLBACK | high | 19 条 default 计量盲区（12 澄清门 0-token + 7 多代理错挂） |
| E08-ISS-QUALITY | medium | 39 条未过启发式粗筛（12 条为澄清门短答，其余低词面相关；粗筛口径见 §10） |
| E08-ISS-ERROR | high | 1 条 DEADLINE_EXCEEDED（90s），未重试掩盖 |

## 10. quality 口径声明

quality 为**确定性启发式粗筛**（非模型评审）：非空（≥10 字）∧ 非弃答 ∧ 语言匹配（zh 需 CJK≥10%；en 需 CJK≤30%）∧ 词面相关（zh bigram + en word，≥0.34）。定位是**筛异常**（空答/弃答/跑题/语言错），不是质量结论；澄清门模板短答天然落筛。39 条 fail 中 12 条为澄清门、其余多为长问句 bigram 相关阈值偏严——修复优先级低于 §7 机制问题。

## 11. 复跑

```bash
# 常驻引擎（127.0.0.1:50051/:8000）+ sparkle_db 容器在位时：
cd <worktree> && /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python \
  scripts/devtools/bench_ai_stack_l0_l3.py run            # 全量 104 条，断点可续（跳过已存在 qid）
  # 可选 --limit N / --layers L0,L1 / --tag NAME
... bench_ai_stack_l0_l3.py summarize [--tag NAME]        # 重算 raw.csv / summary.md / facts / issues
```

## 12. 改动文件清单（本提交，单提交交付）

| 文件 | 性质 |
|---|---|
| `scripts/devtools/bench_ai_stack_l0_l3.py` | 新增：bench 复跑脚本（104 语料 + 单价表 + run/summarize + --help） |
| `scripts/devtools/README.md` | 登记：devtools 目录表新增一行 |
| `v3-output/WT372-E08-BENCH/REPORT.md` | 新增：本报告 |
| `v3-output/WT372-E08-BENCH/raw.jsonl` | 新增：104 条全字段原始记录（含逐帧时间线，DB 归因 104/104） |
| `v3-output/WT372-E08-BENCH/raw.csv` | 新增：raw 扁平表 |
| `v3-output/WT372-E08-BENCH/summary.md` | 新增：dashboard summary |
| `v3-output/WT372-E08-BENCH/facts.json` | 新增：程序计算的关键数字 |
| `v3-output/WT372-E08-BENCH/dynamic_issues.json` | 新增：8 条 dynamic issues |

未触碰 mobile；无 Java/双库/第二身份系统；未重建路由真源（纯外部观察）；无 mock/seed 冒充（全部真模型）；守卫与 mypy 对照不在本卡范围（脚本不进包，backend 代码零改动）。
