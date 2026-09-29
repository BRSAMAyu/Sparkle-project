# V4-Q04｜diff_or_evidence_only

**结论：EVIDENCE_ONLY（零产品代码变更；新增 2 个 devtools 采样/恢复工具 + 本证据目录；kind=verification 重测卡）**

## 做了什么

沿真实链路 **WS 客户端（App 传输层替身）→ Go Gateway /ws/chat → gRPC AgentService.StreamChat → ChatOrchestrator** 对 L0-L3 四层各采样 104 条真实模型 query（语料原样复用 WT372-E08 的 104 条学习成长域语料 × 4 遍），四时刻分开计量（ack / 首文本 delta / 首有用内容〔冻结确定性 oracle〕/ 完整交付），成本三源对账（流内 usage 帧引擎回执 + DB token_usage 归因 + bench 侧官方价表），取消/降级/失败全部纳入分母。另做两组对照探针：取消探针（每层 2 条）与快路 flag-on L0 对照（104 条，`ENABLE_DETERMINISTIC_FAST_LANE=true`）。

### 采样面与分母（全部进入分位计算，无剔除）

| run | 分母 | delivered | cancelled | 说明 |
|---|---|---|---|---|
| main（L0/L1/L2/L3 ×104） | 416 | 416 | 0 | 主分位表 |
| cancel（2/层） | 8 | 0 | 8 | 取消探针，计层分母另报 |
| fastlane（L0 flag-on ×104） | 104 | 104 | 0 | M04 对照面 |
| pilot A/B（小样本定位） | 6 | 6 | 0 | 开工前定位问题层 |

### 四时刻分离结果（主 run，P50/P90/P99，秒）

| 层 | ack | 首 delta | 首有用内容 | 完整交付 |
|---|---|---|---|---|
| L0 | 0.013 / 0.587 / 4.598 | 3.584 / 9.354 / 11.849 | 3.756 / 9.451 / 11.850 | 10.284 / 32.971 / 45.928 |
| L1 | 0.001 / 0.323 / 1.394 | 2.072 / 4.988 / 9.167 | 2.450 / 5.551 / 9.718 | 19.822 / 30.896 / 39.667 |
| L2 | 0.028 / 0.382 / 5.017 | 3.967 / 19.258 / 112.562 | 4.272 / 12.081 / 111.523 | 29.878 / 56.179 / 112.405 |
| L3 | 0.112 / 0.770 / 1.784 | 6.414 / 11.600 / 17.017 | 6.422 / 11.651 / 17.250 | 38.714 / 57.760 / 65.365 |

（完整表含 t_first_stage/t_first_fulltext 列见 `summary-main.md`；n_reached 逐时刻单列，如 L1 首 delta n=97——澄清门纯 full_text 路径 35 行单独成立，不以 delta 冒充。）

### 对照 METRICS 目标（M04-M07）

| 指标 | 目标 | 实测 | 判 |
|---|---|---|---|
| M04 L0 快路零生成、服务 p95≤500ms | 生成调用=0；p95≤500ms | flag=off（出厂默认）时 L0 问候走全模型链：首 delta p95=10.1–10.4s、完成 p95=39.0–40.3s（raw-main 全集标准分位区间；一审 C-3 勘误：原引 11.4s/46s 疑混用 greeting 子集切面〔p95=11.147s〕，不可复现）；flag=on 时 deterministic 子集（26/104）零 token ✓ 但端到端首 delta p50=1.32s/p90=4.78s，仍 >500ms | **FAIL**（两配置均不达；且 flag=off 时生成调用≠0——勘误仅动数值，FAIL 结论不变） |
| M05 L1 首有用内容 | p50≤2s / p95≤5s | p50=2.45s / p95=6.84s | **FAIL**（p50 逼近但超；p95 超 37%） |
| M06 L2 可用提案 | p50≤4s / p95≤12s；20s 转交 | p50=4.27s / p95=34.25s（p99=111.5s） | **FAIL**（长尾显著） |
| M07 L3 控制返回 | ≤5s；深任务软90s/硬180s | 首状态帧 p50=0.282s / p95=1.227s / max=3.87s；完成 max=69.8s，0 行越软90s | **PASS**（控制返回面；完成耗时分位另报不冒充答案） |

### 计费完整性红项（验收 2，全部报红）

1. **no_generation 带 token（I10 检出桶在场）**：main run 3 行 `no_generation_model_estimated`（216/216/277 tok，L2-r1/3/4-08）——I10 的二分标签使其可见而非混桶，但「无生成却带 token」的底层计量缺陷仍在产生。→ RED。
2. **取消轮次真实成本不可见**【一审 C-5 表述收窄】：4 条 delta 后取消的探针 DB 记账全部为 `no_generation_model / 0 tok`（以审查时点**终态 4/4 库行**为准；raw 采集时点仅 1/4 行可见，join 竞态）。服务端续生成的实证面为 L2-CANCEL：客户端取消前已见 **13,320 tok / $0.001332 的 usage 帧级收据**（t=20.366s，早于取消）——取消路径把真实成本记 0 实锤；L0/L1/L3 无 usage 帧收据，「续生成」为合理推断非实证。→ RED。
3. **delivered 但完全无计量**【一审 C-1/C-2 勘误，原表述部分推翻】：main **12 行**（L1×5/L2×5/L3×2；原记 14——L3-r3-09/L3-r4-09 已于 23:05:20/25 落库，采集 join 竞态多计）有响应内容（35–1296 字符）却无 usage 帧且无 token_usage 行——遗留真红，归属**混合面**（无收据+无行，无法区分产品漏发 vs 环境吞没，按已知队列事故环境面概率高）；fastlane 13 行 deterministic 轮次**已被本卡自身恢复批（23:42:02，58 行/120ms）全部落库**，标签恰为 I09 单测承诺的 `no_generation_model`/0tok——I09 承诺 live 成立 **26/26**；缺失行与在库行时间交错（23:20-23:37），符合队列竞态回亡-恢复链，**「early-return 绕过 cleanup」根因假设撤回**。**根因=汇总 join（23:42:03）晚于自身恢复批（23:42:02）1 秒的 TOCTOU 竞态采集伪象**。→ RED（遗留 main 12 行）；fastlane 半边改判环境延迟非损失。
4. **计量持久化丢失（环境性）**：152 行的 billing 记录被共享 Redis queue:billing 上的第二个消费者（主检出驻留栈 worker，凭据失效）抢走并丢失；本卡以流内 usage 帧（同一引擎回执权威）补齐成本计量，模型归因缺失如实标注。恢复批 58 行已落库（一审 C-7 勘误：原概称 59）。→ RED（环境根因，非本卡代码）。

### 红项归属总表（一审 wtQ04R1 裁定；勘误后权威口径）

| 红项 | 一审归属 | 处置去向 |
|---|---|---|
| ① no_generation 带 token（3 行 216/216/277 tok，L2-*-08） | **产品面**（计量缺陷；I10 检出桶使其可见） | 转实现卡处置 |
| ② 取消轮次真实成本归零（L2 13,320 tok 帧级收据实锤；L0/L1/L3 无收据为推断；终态 4/4 库行 0tok） | **产品面**（取消路径把真实成本记 0） | 转实现卡处置 |
| ③ delivered 无计量——fastlane 13 行：交付时「无账面行/early-return 疑绕过」为 **TOCTOU 采集伪象**（汇总 join 23:42:03 晚于自身恢复批 23:42:02〔58 行/120ms 突发〕1 秒，未读及恢复批落库；I09 承诺 26/26 达标）；遗留 main 12 行：**混合面**（无收据+无行，环境面概率高） | ③fastlane=采集伪象（勘误结案）；③main 12=混合面 | main 12 行与④同源，转 fleet 环境卡 |
| ④ 计量持久化丢失 152 行（恢复批 58 行已落库） | **fleet 环境面**（共享 queue:billing 双消费者 + 驻留栈凭据失效） | **FIX-571** fleet 卡（共享 DB 鉴权修复 + queue:billing 单消费者化） |

### 成本三源合计（main run）

- DB 归因 250 行 / 1,022,536 tok / **$0.102185**（引擎账，模型/tier 归因完整）
- 流内回执 152 行 / 545,200 tok / **$0.054525**（engine receipt cost_micro_usd，同源权威；模型归因丢失）
- 完全无计量 12 行（见红项 3；一审 C-2 勘误：原记 14，L3-r3-09/L3-r4-09 已落库）
- **合计 ≈ $0.156710**；另 fastlane 探针 $0.010334（91 行 = 78 model-lane 回退行 + 13 deterministic no_generation_model/0tok——一审 C-1 勘误：原记「全部为 model-lane 回退行」不实）、pilot ≈$0.003。**本卡全程真实模型支出 ≈ $0.17**，远低于既有 E08 系列同规模基准先例（$0.127/104q × 本卡 528q 规模折算 ≈ $0.65），无预算超限。
- 价表来源：`bench_ai_stack_l0_l3.py` 内嵌官方价表（Aliyun/BigModel/DeepSeek 2026-08~09 价，逐项注明来源日期），本 run 归因子集 100% `dashscope_fast`（¥0.225/¥0.974 per M tok，2026-09-10 价）。

### 观测面重要副产物（供后续卡消费）

1. **tier 全塌缩复现**：main 归因子集 250 行全部 `dashscope_fast`——pro lane / deep reasoning_mode 的 L2/L3 行也无 STANDARD/MAX 归因（E08 已记录同类现象；I09/I10/I08/U07 合并未改变路由分层行为）。
2. **主检出驻留栈不可用作验证目标**：驻留 gRPC 引擎进程启动于依赖合并前（I09/I10/I08/U07 之前），且共享 Postgres 自 2026-09-28 容器重启起 host 侧 scram 鉴权全坏（role hash 与现行 .env 不匹配，驻留栈 guest auth 同样失败，token_usage 最新行停留在 09-28 09:18）。本卡自建 wtQ04 栈（gate 8081/engine 50052/8001）并用 cosmos 仓 git 历史中的初始有效凭据（只读引用，未回显未落盘）。
3. **共享数据面已补 I06 迁移**：本卡经 Alembic 唯一入口 `upgrade head` 补齐 `wt598_20260927 → i06_20260928`（主库此前缺表导致新代码事务中毒、计费行不落库）。
4. **时间漂移**：bench guest 用户状态随采样累积，后遍 p50 系统性劣化（如 L1 useful r1=1.41s → r3=3.71s）——分位表含该真实漂移；逐遍切片见 run_manifest.drift。

## 交付物

- `scripts/devtools/bench_v4_q04_e2e_latency_cost.py`（四时刻 WS 采样工具，语料/价表复用 E08 脚本单一来源）
- `scripts/devtools/recover_q04_billing_deadletter.py`（死信恢复：复用 BillingWorker 同一列映射直插，恢复产品自身已产出计量，非造数）
- `v4/evidence/V4-Q04/raw/*.jsonl`（5 个 run 全量原始样本，含帧级时间线）
- `v4/evidence/V4-Q04/summary-*.md`、`cost_rollup-*.json`（分位表/成本三源/红项清单）
- `run_manifest.json`、`test_results.json`、`limitations.md`、`review_receipt.json`
