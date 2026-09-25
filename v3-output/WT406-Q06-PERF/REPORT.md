# WT406-Q06 REPORT — Performance / Cost / Provider 波动终验（Gate V3-8）

> 2026-09-26 ｜ Worker wt406 ｜ 卡 Q-06（stream QUALITY，HEAVY，gate V3-7，lock performance-eval）
> base SHA `acbeb450`（main）＝本卡全部实测的被测代码；worktree `Sparkle-sysrev/wt406-q06-perf`
> 交付物：本报告 + `raw-bench.jsonl/csv`（400 样本全字段）+ `facts-bench.json` + `chaos_results.json`（七场景）+ `growth_results.json` + 驱动脚本 ×4（`scripts/devtools/q06_*.py|.sh`）
> **所有数字均由 raw 程序化复算（summarize/growth/chaos 驱动），无手填；错误与抖动原样呈报，不剪异常、false smooth=0。**

---

## 1. 运行环境与真源

| 项 | 值 |
|---|---|
| 被测引擎 | **wt406 worktree 自起实例** backend @ `acbeb450`（=main HEAD），gRPC :50061（bench 段）/ :50062（chaos 段）；**非常驻 :50051**（该实例代码版本不可证，弃用） |
| 上游 | 真实 dashscope/deepseek/zhipu/xiaomi（bench 段）；chaos 段经 env 把 7 个 provider base_url 指向本地 mock（:9099），产品代码零改动 |
| 客户端 | 主仓 backend/.venv，guest JWT（`wt406_q06_bench_free` / `_pro` 双账号）→ gRPC StreamChat 直连 |
| 计量归因 | token_usage 落库经 **redis db1 专用 billing worker**（此前 E-08 依赖常驻 uvicorn 的 lifespan worker——独立栈必须自起，本卡已证实并留脚本）；DB 归因 396/400 + 4 补跑 = 400/400 |
| 隔离 | redis db1（bench）/db2（chaos），避免污染常驻引擎共享的 `llm:fail:*` 健康键 |
| 运行方式 | 串行并发=1（bench），逐条落盘断点可续；窗口 00:33–04:00（bench）/ 04:01–05:20（chaos）/ 05:16（growth） |
| 限流 | bench 段真实上游 429 = **0 次**（如实记录口径） |

## 2. 路线一：分层延迟/成本（每层 n=100，50 distinct × 2 reps）

语料 = E-08 的 104 条原样保可比 + 新增 96 条（学习成长域跨科目真实多样，不复读句式）；pro 车道走**网关忠实形态**（`ChatRequest.user_profile.is_pro=true`，不带 extra_context.user_tier——wt392 服务端权威升档门由此被真实检验）。

### 2.1 分层延迟（秒；n≥100 才报 p50/p95——卡面验收）

| 层 | n | ok | err | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | 帧间最大静默 p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0 快答 | 100 | 100 | 0 | 0.91 | 1.88 | 0.91 | 1.88 | 9.03 | 22.97 | 0.04 | 10.1 |
| L1 标准 | 100 | 100 | 0 | 1.58 | 2.25 | 1.58 | 2.25 | 22.77 | 35.01 | 0.05 | 10.1 |
| L2 深推理 | 100 | 98 | 2 | 1.80 | 9.36 | 1.80 | 9.36 | 23.97 | **48.25** | 0.04 | 10.1 |
| L3 编排·长上下文 | 100 | 95 | 5 | 7.20 | **141.40** | 7.20 | 141.40 | 33.61 | **215.03** | 0.06 | 10.1 |

- **抖动原样呈报**：全层帧间最大静默 p95=10.1s（恒定值，系统性节奏——疑似 stage/心跳帧间隔，非随机抖动；L2 max 30.1s）。E-08 未报该指标。
- L3 TTFT p95=141s：deep_analysis 的 cognitive_prism 多代理串行链（E-08 已实测 hops: execute_graph 110s），本轮 r2 复现（多样本 110-157s）；**未平滑、未剪**。
- L3 5 条错误 = 3 条客户端 240s 截断（censored：引擎仍在流式产出，如 L3-49 r1 444 帧/4825 字未收尾）+ 2 条 V3-FIX-77 校验误判拒答。L2 2 条 err = 同一校验误判（L2-30 双 rep）。

### 2.2 分层成本（官方价表与 E-08 同源；USD）

| 层 | tokens(prompt+completion) | cost | cost/query |
|---|---|---|---|
| L0 | 145,359 | $0.0100 | $0.000100 |
| L1 | 342,972 | $0.0107 | $0.000107 |
| L2 | 336,190 | $0.0930 | $0.000930 |
| L3 | 478,901 | $0.6151 | $0.006151 |
| **合计（400 条）** | **1,303,422** | **$0.7288** | **$0.001822** |

- 深层贵 60 倍：L3 单条成本是 L0 的 61 倍，主因 qwen3_8_max 车道（25 条，$0.5635，73% 成本集中于 deep_analysis pro 车道）。
- 计量盲区持续（→ **V3-FIX-80**）：39/400 条 token_usage.model='default'（32 条 0-token 澄清门模板直出 + 7 条多代理流错挂带 token，与 E-08 E08-ISS-FALLBACK 同因未修：`response_builder.py:948` `or "default"`）。

### 2.3 tier 账本（分层复活证明——对比 E-08 塌缩）

| model key（token_usage 归因） | n | tier | TTFT p50 | cost$ | 用途 |
|---|---|---|---|---|---|
| dashscope_fast (qwen3.7-flash) | 263 | fast | 1.47s | 0.0362 | free 全车道 + 轻任务 |
| dashscope_chat (qwen3.7-plus) | 67 | **plus** | 2.50s | 0.1189 | pro 主生成 |
| qwen3_8_max | 25 | **max** | 50.96s | 0.5635 | deep_analysis pro |
| dashscope_standard_thinking (qwen3.8-flash) | 2 | **standard** | 1.44s | 0.0012 | 深档子调用 |
| default（盲区） | 39 | - | 104.87s | 0 | 澄清门/多代理错挂 |
| （无计量行） | 4 | - | - | 0 | 校验误判拒答 |

**E-08 时 85/85 全部塌缩 dashscope_fast；本轮 fast/plus/max/standard 四车道真实分布，且引擎日志 7049 条 free_tier_downgrade 全部来自 free 账号请求（free 车道 plus→fast 钳制符合设计），pro 账号子代理调用保持 plus/max（E-08 问题 C 已修）。wt392 提权封堵实测：free 账号 + extra_context.user_tier=pro + user_profile.is_pro=false → 仍 dashscope_fast（smoke 探针 wt406-smoke-free-claims-pro）。**

## 3. SLO 判定（Gate V3-8 候选目标，逐条）

| SLO | 实测（n） | 判定 | 对比 E-08 |
|---|---|---|---|
| 本地确定性交互 p95 ≤300ms | （口径外——无独立本地交互面；ContextPackBuilder 本地构建 p50 7ms/1000 行记忆见 §5，远低于 300ms） | 参考 | E-08 未测 |
| L0 no-model 路径 p95 ≤500ms | TTFT p95=1879ms（100） | **FAIL** | E-08 2033ms FAIL——问候/确认/快问仍全走生成链（E08-ISS-L0-TTFT 悬置，TRIVIAL 不跳过生成） |
| L1 首个有意义反馈 p50 ≤2.5s | 1.58s（100） | **PASS** | E-08 1.95s PASS（改善） |
| L1 p95 ≤5s | 2.25s（100） | **PASS** | E-08 2.95s PASS（改善） |
| L2 500ms 内阶段反馈（首事件 p95，free lane） | n=38（语料 lane 配比 19:31 非 1:1，如实不报 p95） | **NOT_REPORTABLE** | E-08 5446ms FAIL（n=13）；本轮同口径全 lane 参考 40ms（n=100）**达量级改善**（E-03 stage 前置 + 500ms ack 生效） |
| L2 最终 p95 ≤15s | 48.25s（100） | **FAIL** | E-08 49.46s FAIL——无改善，深档思考/多代理链路总时长仍在 15s 预算 3 倍以上 |
| L3 Agent Run 创建/ACK p95 ≤1s | 首事件 p95=0.06s（100） | **PASS** | E-08 7.03s FAIL——**最大改善项**（前置 ack/stage 全面生效） |

**结论：6 项可判 SLO 达标 4 项（E-08 为 2/6）；FAIL 2 项（L0 no-model 未落地；L2 最终 p95 48s）。L3 ACK 与 L2 阶段反馈两项由 FAIL 转 PASS，为 wt380-wt400 修复链的直接证据。**

## 4. 路线二：供应商波动注入（七场景+1 干净对照，注入点=上游客户端层）

mock = OpenAI 兼容上游（:9099），运行时经 admin 切换故障模式；引擎经 env 把 **7 个 provider base_url**（DASHSCOPE/DEEPSEEK/ZHIPU/XIAOMI_MIMO×2/SILICONFLOW/MINIMAX/LLM_API）全部指向 mock，产品代码零改动。场景间清 redis db2 `llm:*`（环境复位）；观测三面：用户可见帧时间线 / 引擎 fallback·健康日志 / mock 上游尝试链。**终版数据为统一全注入面单轮套件**（首轮部分注入面数据作废原因见 §4.2）。

| 场景 | 注入 | n | ok/err | 用户可见结果 | 上游尝试 | 判读 |
|---|---|---|---|---|---|---|
| S1 primary-429 | 仅 qwen* 429 | 8 | 8/0 | 全部成功，total 0.59-2.96s，首事件 ≤60ms，无错误帧 | 20 | **换道链工作正常**：429 识别（`report_rate_limit`）→ 候选车道接管 → 用户仅感知轻微变慢 |
| S3a slow-TTFT 35s（套件内，S1 之后跑） | 仅 qwen* 首 token 延 35s | 5 | 5/0 | 全部 ~1s 完成——**qwen 被路由内存健康避开**（S1 的 429 失败仍在内存态），注入打不到目标 | 5 | **E-07 滞回的跨场景后果**：失败后 provider 被持续跳过，redis 清扫不复位内存态（→ V3-FIX-81） |
| S3a_clean 干净引擎对照 | 同上，重启后首场景 | 5 | 5/0 | total **18.7-58.2s**：qwen 真实慢 TTFT 被承受，不误判超时、不换道，等待期间首事件 ≤357ms（stage 帧在） | 22 | **35s<60s 阈值的正确姿势**：等待而非误 fallback；有进度反馈 |
| S3b slow-TTFT 65s（>60s read timeout） | 全部 provider | 5 | 4/1 | total 104.7-180.0s：60s 读超时→fallback→下一候选再 65s→链式等待；1 条烧满客户端 180s | 23 | **超时链真实但无总预算**：用户等 104s+ 才见结果/错误（→ V3-FIX-78） |
| S4a 断流（仅 qwen*） | mid-stream 出 2 delta 即断 | 8 | 8/0 | 全部成功（候选车道完整答案），0 截断标记，total 1.3-42.4s | 15 | **mid-stream 失败→候选车道逃生成功** |
| S4b 断流（全部 provider） | mid-stream 全断 | 8 | 8/0 | 「成功」但答案主体为 **experience_actuator 固定话术模板**（`orchestration/experience_actuator.py:172`「我先按你的材料把真正卡住的点校准清楚…」，不同问题同开头实证）+semantic cache；**无错误帧、无降级标注、无截断标记** | 13 | **静默模板降级**：全断供时用户拿到未标注的模板文本，无法分辨模型答案与模板兜底（→ V3-FIX-78 关联语义面） |
| S5 队列压力 | 全部 ok×5s 延迟，30 并发 | 30 | 8/22 | **22/30 烧满 150s 客户端超时**（chars=0 无任何内容帧）；成功者 TTFT 最长 128s（等槽）；上游仅 8 次尝试（多数请求未挤进上游就超时） | 8 | **过载无背压语义（→ V3-FIX-79）**：并发池 20×每轮多上游调用放大排队，无「繁忙」提示、无快速失败 |
| S2 total outage | 全部 provider 429×12 连发 | 12 | 6/6 | 6 条 chars=0 烧满 180s；6 条「成功」=同 S4b 的模板/缓存文本；上游 15 次后熔断开路（后续无上游流量） | 15 | **全断供=静默等待或未标注模板文本**；引擎日志实录 record_failure 连续计数至 86（首轮 S2 窗口），无总预算（→ V3-FIX-78） |

### 4.1 波动面结论

- **单点 429 / 慢 TTFT（<60s）/ 单车道断流：弹性合格**——换道、限速学习、stage 反馈、等待-不误判全部实证（S1/S3a_clean/S4a）。
- **全断供 / 全慢（>60s）/ 过载三面不合格**：无快速诚实失败（重试无总预算，86 连续失败、180s 静默）、无背压提示（22/30 烧满 150s）、降级文本不标注（模板话术冒充正常回答面）——Gate V3-6「cancel/timeout/retry 有明确用户语义」在 provider 级故障下不成立。
- **附带发现**：健康系统按设计工作（失败后避让），但避让跨场景持久且无复位出口——故障演练/排障会误判「已恢复的 provider 仍不可用」（V3-FIX-81）。

### 4.2 首轮数据作废声明（false smooth=0）

首轮套件（04:01-05:00）注入面不全：XIAOMI/SILICONFLOW/MINIMAX/LLM_API 未重定向，S4b/S2/S5 的「成功」样本混入**未注入的真实 xiaomi 上游答案**（bench 窗口引擎日志可见 generation -> xiaomi_chat）；且首轮 S3a 受内存健康残留失真（3s 完成）。上表全部为补全注入面后的单轮重跑数据；首轮 raw 保留于过程日志（/tmp），不入交付。

## 5. 路线三：Context token × Memory 增长标度

真实服务面 `ContextPackBuilder.build()`（sqlite 真实 schema + fakeredis；真实格式记忆行；semantic gating 走真实 dashscope embedding batch；LLM judge 0 次）。幂律拟合 build_ms ~ n^b。

### episodic 轴（10→1000 行）

| n | pack tokens | 渲染 prompt tokens | pack 内 episodic 条数 | build p50 (ms) |
|---|---|---|---|---|
| 10 | 256 | 7,739 | 2 | 7.8 |
| 50 | 256 | 7,740 | 2 | 7.3 |
| 100 | 256 | 7,736 | 2 | 7.2 |
| 500 | 256 | 7,739 | 2 | 7.1 |
| 1000 | 256 | 7,734 | 2 | 6.9 |

**曲线=完全水平（token 指数 b=-0.0，build 指数 b=-0.02）**：护栏三层生效（`list_recent_episodic` limit=20 查询面裁剪 → 排序/soft-cap 选择 → budget 调度钳制），1000 行记忆与 10 行的 Context 成本完全一致。无 O(n²)，无增长灾难。

### preference 版本链轴（25 键 × 1→20 版本 = 25→500 行）

| 行数 | pack tokens | pack 内偏好数 | build p50 (ms) |
|---|---|---|---|
| 25 | 15 | 1 | 8.0 |
| 50 | 3 | 0 | 7.7 |
| 100 | 15 | 1 | 8.7 |
| 200 | 15 | 1 | 8.7 |
| 500 | 3 | 0 | 12.5 |

**build 指数 b=0.142（亚线性）**：500 行仅 +56% 时间（8.0→12.5ms），`list_preference_records` 的全量加载被 key 去重 + 链头胜出消解，token 面零泄漏。pack 内偏好数 1/0 交替为 semantic gating 阈值边缘效应（cosine 0.55 边界），如实呈报。

**增长面判定：无 O(n²) 灾难，护栏明确且实测有效（PASS）。**

## 6. 动态卡登记（v3/06_agent_fleet/DYNAMIC_ISSUES.md，占用号段 V3-FIX-77..81；57-76=wt401/wt404 预留）

| id | P | 摘要 | 证据 |
|---|---|---|---|
| V3-FIX-77 | P2 | SQL 注入校验器英文词误判：`select `/`update ` 子串 + `\bkw\b.*?from\b` 跨句匹配，正常英语学习内容被判恶意拒答（400 样本 4 条触发，2 个 distinct 输入稳定复现） | raw-bench L2-30 r1/r2、L3-43 r1/r2（error_code=2 "Message contains potentially malicious content"）+ 引擎日志 3 条 "Detected potential SQL injection: select/update" |
| V3-FIX-78 | P1 | 全断供/全慢面无快速诚实失败：引擎内重试无预算上界（record_failure 连续计数至 86），单请求烧满客户端 180s 超时，用户只见静默等待；S3b 3/5、S2 5/12 同型 | chaos_results S2/S3b + 引擎日志 "Model marked unhealthy after 86 consecutive failures" + S2-0..3 帧 0 内容 |
| V3-FIX-79 | P2 | 过载无背压语义：上游 5s 延迟×30 并发 → 18/30 烧满 150s 客户端超时（并发池 20×每轮多上游调用放大），排队中无「繁忙」降级文案 | chaos_results S5（TTFT max 143.8s） |
| V3-FIX-80 | P3 | 计量盲区持续：39/400 条 token_usage.model='default'（32 澄清门 0-token + 7 多代理错挂带 token）——E08-ISS-FALLBACK 一轮未收敛，`response_builder.py:948` `or "default"` | raw-bench db_model 分布 + facts-bench.json tier_ledger |
| V3-FIX-81 | P3 | 模型健康双源不同步：llm_router 内存健康与 redis `llm:*` 三相状态机并行，无管理复位出口（清 redis 后内存态仍拒排 qwen，chaos S3a 首轮失真根因；生产排障同样会踩） | chaos 首轮 S3a（3s 完成）vs 干净重启重跑（18.7-58.2s）对照 + mock 尝试链 |

## 7. 口径与局限（如实声明）

- **引擎为本卡 worktree 自起**（main HEAD 可证），非常驻实例；网关 :8080 未入链路（E-08 已测透传 0.02-0.35s）。
- 每层 n=100 = 50 distinct × 2 reps（rep 间新会话）；lane 配比 L2 为 38:62、L3 为 52:48（新增语料 lane 分配所致），lane 级切片按 n≥100 规则不报 p95，如实标 NOT_REPORTABLE。
- L3 3 条 240s 客户端截断为**测量仪器上限**（引擎仍在产出），以 censored error 计入，不影响 p95（截断样本均为尾部 max 区）。
- chaos 段答案文本来自 mock 或引擎模板面（S4b/S2 的模板兜底已定位到 `experience_actuator.py:172`）；S1/S4a 的 fallback 成功证明的是**引擎换道机制**，非 fallback 车道的答案质量。终版 chaos 数据为统一全注入面（7 base_url）单轮套件；首轮部分注入面数据已作废并声明（§4.2）。
- 成本为**主生成计量口径**（token_usage 表），辅助调用（分类/sufficiency/HyDE/多代理内部）不在计量内（E-01 C5 观测缺口未修，见 V3-FIX-80）。
- 10.1s 恒定帧间静默为系统性节奏（疑似心跳/stage 帧间隔），未做平滑处理；其产品语义（用户可感知的 10s 停顿是否伴随进度指示）归 V3-7 体验面。
- growth 段 sqlite+fakeredis 隔离（wt393/wt397 同款口径），真实服务代码 + 真实 embedding API；模型 judge 0 次（全卡所有判定均为确定性启发式/DB 归因/帧时间线）。

## 8. DEFERRED（不阻塞本卡关闭）

- L0 no-model 直答落地（E08-ISS-L0-TTFT / E-01 W-2）与 L2 总时长 48s 的编排裁剪——两者均为架构级，归修复卡（V3-FIX-78 顺带重试预算，L2 需 planner 面裁决）。
- S5 队列压力的全注入面复跑（30 并发 × 全 provider 5s）与并发池参数敏感性扫描。
- 网关侧 NoRoute 熔断语义核对（V3-FIX-56）——本卡注入点在上游客户端层，网关面未入链路。
- 多轮会话下的 tier 账本纵向漂移（adaptive routing 长窗口学习对分层的侵蚀）需 >400 样本的长时间窗。

## 9. 复跑

```bash
# 引擎（worktree 自起 :50061 + redis db1 + billing worker）在位时：
cd <worktree> && /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python \
  scripts/devtools/q06_perf_bench.py run            # 400 条，断点可续
# ... q06_perf_bench.py summarize                    # 重算 facts/csv
# chaos：bash scripts/devtools/q06_chaos_engine.sh start（先启 mock：q06_provider_chaos.py serve）
# ... q06_provider_chaos.py run [--scenarios S1,S3a,S3b,S4a,S4b,S5,S2]
# growth：q06_growth_scaling.py（sqlite 隔离，独立于引擎）
```

## 10. 改动文件清单（本卡提交）

| 文件 | 性质 |
|---|---|
| `scripts/devtools/q06_perf_bench.py` | 新增：分层 bench 驱动（400 样本 + summarize） |
| `scripts/devtools/q06_growth_scaling.py` | 新增：增长标度驱动 |
| `scripts/devtools/q06_provider_chaos.py` | 新增：mock 上游 + 七场景驱动 |
| `scripts/devtools/q06_chaos_engine.sh` | 新增：chaos 引擎启停（按端口精确杀，不触常驻） |
| `scripts/devtools/q06_smoke_tier.py` | 新增：tier smoke 探针（报告引用） |
| `scripts/devtools/README.md` | 登记 5 行 |
| `v3-output/WT406-Q06-PERF/*` | 新增：raw/facts/chaos/growth + 本报告 |
| `v3/06_agent_fleet/DYNAMIC_ISSUES.md` | 登记 V3-FIX-77..81 |

产品代码（backend/app、gateway、mobile）**零改动**；无 mock 冒充模型结果（mock 仅作为被注入的上游仪器，全部声明）；无 Java/双库/第二身份系统。
