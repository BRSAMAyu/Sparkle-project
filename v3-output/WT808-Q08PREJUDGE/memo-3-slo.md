# 预裁③ 备忘 — Gate V3-8 SLO 修订口径草案（wt808）

> 性质：Q-08 正式执行前的**裁决口径草案**，非终判。本文不修改 DoD 原文（`v3/V3_DEFINITION_OF_DONE.md` 逐字保留）、不改台账、不改 tasks.json。
> 撰写：wt808 ｜ 2026-09-28 ｜ 分支 `agent/wt808/q08prejudge`（worktree wt808，base main@`1f62b36c`）
> 输入：[WT801-E08FINAL/report.md](../WT801-E08FINAL/report.md)（验收级复测，4 PASS/2 FAIL）＋ [WT801-E08FINAL/facts.json](../WT801-E08FINAL/facts.json) ＋ [WT406-Q06-PERF/REPORT.md](../WT406-Q06-PERF/REPORT.md)（400 样本原测）＋ [WT372-E08-BENCH/](../WT372-E08-BENCH)（修前基线引用）＋ [WT803-E08REV/receipt.md](../WT803-E08REV/receipt.md)（独立审查 APPROVE-closure）
> 标注纪律：每段标【事实】/【推断】/【建议】三档；所有数字给出可核对路径。

---

## 1. 裁决对象：DoD V3-8 原文与它的两层结构

【事实】Gate V3-8 原文（`v3/V3_DEFINITION_OF_DONE.md` §Gate V3-8，55-65 行）分两层：

- **七条候选目标**（原文自带限定语「**候选目标（必须以真实 provider 基线校准）**」）：
  1. 本地确定性交互 p95 ≤300ms；
  2. L0 no-model 路径 p95 ≤500ms；
  3. L1 fast semantic path first meaningful feedback p50 ≤2.5s / p95 ≤5s；
  4. L2 deep decision 在 500ms 内给阶段反馈，最终 p95 ≤15s；
  5. L3 Agent Run 创建/ACK ≤1s，后续异步、可恢复；
  6. 没有任何 UI 因隐藏模型调用无反馈冻结 >2s；
  7. 每个 tier 有 token/cost/latency/quality 账本。
- **修订授权与红线**（同段末，原文）：「若 qwen3.8-flash 或当期 provider 无法满足，**必须重新定真实 SLO**，并通过 fast lane/缓存/预计算/异步改善；**禁止通过隐藏等待伪造性能**。」

【推断】DoD 在写 V3-8 时就预设了「候选 → 以真实 provider 基线校准 → 必要时重定」的三步路径。因此「照原口径判 FAIL」与「产出修订 SLO」**不是二选一**——DoD 原文要求无法满足时**必须**重定，同时历史 FAIL 事实不得删除（全舰队纪律：不删断言求全绿）。预裁③真正要裁的是：**哪些项重定、按什么可证伪判据重定、终门报告如何呈现**。

---

## 2. 原始 SLO 声明 vs 实测对照表

【事实】三轮实测同构口径（同 harness `scripts/devtools/bench_ai_stack_l0_l3.py`、同 104 条语料；SLO 表达式在 harness 源码 :815-828，经 wt803 独立复算逐数吻合——[WT803-E08REV/receipt.md](../WT803-E08REV/receipt.md) §3.2）：

| # | DoD V3-8 候选条款 | 操作化 SLO | 修前 wt372（09-25，`a1418084`） | WT406（09-26，n=100/层） | **修后 wt801 终测（09-28，n=26/层）** | 现判 |
|---|---|---|---|---|---|---|
| 1 | 本地确定性交互 p95 ≤300ms | 未入 bench 操作化 | 未测 | 口径外参考（见下） | 未测（同口径外） | 参考 |
| 2 | L0 no-model p95 ≤500ms | TTFT p95 | 2033ms FAIL | 1879ms FAIL | **1781ms FAIL** | **FAIL（持续）** |
| 3 | L1 p50 ≤2.5s | TTFT p50 | 1.95s PASS | 1.58s PASS | **1.66s PASS** | PASS |
| 4 | L1 p95 ≤5s | TTFT p95 | 2.95s PASS | 2.25s PASS | **2.60s PASS** | PASS |
| 5 | L2 阶段反馈 ≤500ms | free 首事件 p95 | 4282ms FAIL | 40ms 参考（free n=38 NOT_REPORTABLE） | **42ms PASS（翻转）** | PASS |
| 6 | L2 最终 p95 ≤15s | total p95 | 49.5s FAIL | 48.25s FAIL | **65.4s FAIL（幅度上行）** | **FAIL（持续）** |
| 7 | L3 创建/ACK ≤1s | 首事件 p95 | 7.03s FAIL | 0.06s PASS | **0.054s PASS（翻转）** | PASS |

数据出处：wt372/WT406/WT801 三列数字逐项取自 [WT801-E08FINAL/report.md](../WT801-E08FINAL/report.md) §4 表＋[WT406-Q06-PERF/REPORT.md](../WT406-Q06-PERF/REPORT.md) §3 表；`facts.json` `slo_results` 字段与之一致（`"L0 no-model p95≤500ms": "FAIL", "L1 首个有意义反馈 p50≤2.5s": "PASS", ...`）。

**非 bench 化三条款的现状**（Q-08 报告需逐条带注记，不可空缺——骨架判定规则 1）：

【事实】
- **条款 1（本地确定性 300ms）**：三轮 bench 均未操作化。[WT406-Q06-PERF/REPORT.md](../WT406-Q06-PERF/REPORT.md) §3 原文：「（口径外——无独立本地交互面；ContextPackBuilder 本地构建 p50 7ms/1000 行记忆见 §5，远低于 300ms）｜参考」。旁证：网关纯透传 ≈0.02-0.35s（[WT801-E08FINAL/summary.md](../WT801-E08FINAL/summary.md)「口径与局限」节，TTFT-PROBE 已测）。
- **条款 6（UI 隐藏调用冻结 >2s）**：intake ack 修后 104/104 ≤500ms（max 400ms，`facts.json` by_layer `fb_p95` 22-54ms）；keyless 探针 24/24 ≤55.6ms（`evidence/ack_probe/`）；移动端生成期 loading 反馈 F5 6/6 PASS（[WT802-J02-RETEST/REPORT.md](../WT802-J02-RETEST/REPORT.md) delta 表）。
- **条款 7（tier 账本）**：账本存在且分层——`WT801-E08FINAL/summary.md` model 分布表（fast 68 / chat(plus) 12 / max 5 / standard_thinking 1 / no_generation_model 18）＋ lane token/cost/TTFT 表＋逐层 quality_pass 计数。【事实·缺口】7 条多代理流计量错挂计 $0（L3-06/08/15/18/21/23/26，同 qid 修前修后持续；台账 V3-FIX-545 P2 OPEN 承接），占 104 条的 6.7%，成本口径有盲区（[WT801-E08FINAL/notes.md](../WT801-E08FINAL/notes.md) §4）。

---

## 3. 两项 FAIL 的定性

### 3.1 L0 no-model p95 = 1781ms（阈值 500ms）

【事实】
- 定性锚=自动 issue 原文（`WT801-E08FINAL/dynamic_issues.json` E08-ISS-L0-TTFT）：「问候/确认/快问仍走完整生成链（对应 E-01 W-2：TRIVIAL 不跳过生成），L0 no-model 直答未生效」；wt801 报告 §5 判语：「**是工作项（no-model 直答生效）非测量项**」。
- 修前 2033ms → 修后 1781ms，13% 改善但量级不变；TTFT p50 1.08s——整条 L0 响应确实在等生成模型首 token。
- 该项四轮（E-08/wt372/WT406/wt801）全部 FAIL，方向一致、幅度同带。

【推断】定性 = **功能缺位（no-model 直答路径未实现/未生效），非环境负载，非口径过严**。环境负载论不成立：两轮间隔三天、不同时段，数值同带（2.03s/1.88s/1.78s）；口径过严论不成立：「no-model 路径 ≤500ms」的语义前提是存在一条不过生成模型的路径，路径本身没走通时谈阈值宽严无意义。500ms 阈值本身对「本地确定性交互」类目标并非苛刻（同 gate 本地条款是 300ms）。

### 3.2 L2 最终 p95 = 65.4s（阈值 15s）

【事实】
- 上行的时间线与 tier 塌缩修复强相关：修前 deep 档 85/85 塌缩 `dashscope_fast`（E08-ISS-TIER-COLLAPSE），L2 total p95 49.5s；wt380 三因修复＋接线后计量分布恢复四车道（fast 68/chat 12/max 5/standard 1），L2 total p95 65.4s、L3 total p50 28.8→68.5s、计量成本 $0.0117→$0.1269（[WT801-E08FINAL/report.md](../WT801-E08FINAL/report.md) §5＋notes §4）。
- wt801 notes §4 原文：「deep/pro 臂真实打到 max/plus……『分层成本/质量账本』恢复的同时深档延迟上行，**是路由修正的真实 trade-off，不是退化事故**」。
- 慢的主体是 provider 推理本身：`qwen3_8_max` 车道 TTFT p50 64.91s（summary.md model 表）；`deep_analysis` intent 8 条 TTFT p50 91.16s。
- 环境边界（report §9 原文）：「引擎为共享 dev 实例，并行 workers 负载噪声无法完全排除；两轮同为串行 bench 形态，口径同构」；且「本对照是『叠加态 vs 叠加态』的工程对照，非单变量归因」。

【推断】定性 = **主因：原口径相对当期 provider 真实能力过严**（15s 预算在写 DoD 时未校准 max 档真实首 token 时延；DoD 自称「候选目标（必须以真实 provider 基线校准）」，校准义务本来就在）；**次因：环境负载噪声（不可定量剥离）；非代码退化**（L0/L1 TTFT 同向改善、ack 面塌缩至 22-54ms，若为系统性退化不可能出现此形态）。【事实】此定性已获独立审查背书：wt803 APPROVE-closure 且轮#307 销账时「L0/L2-total 深档 trade-off 入 V4 输入」落账。

---

## 4. Q-08 对 SLO gate 的三种处置选项

### 选项 A — 照实判 FAIL（维持原口径，不产修订决议）

- **依据**：判定纪律最保守形态；「自称完成不算完成」，FAIL 无需任何补充论证；与骨架判定规则 2（任一 gate FAIL→FINAL FAIL）兼容。
- **风险**：①与 DoD 原文「无法满足**必须重新定真实 SLO**」相抵触——不产出修订决议本身就是未完成 DoD 内嵌义务；②把 L2 total 的「路由修正真实 trade-off」记成无定性的质量事故，会误导 V4 优先级（把已正确的分层路由当性能缺陷回滚的激励）；③终门报告失去「修订后的可证伪新口径」，V4 没有验收线可依。
- 【推断】该选项事实上不是「更严格」而是「少交一项 DoD 要求的产物」。

### 选项 B — 按修订口径判（产出修订 SLO 决议，按新口径判）

- **依据**：DoD V3-8 内嵌授权＋义务（见 §1）；WT801/WT406 两轮真实 provider 基线数据恰好就是 DoD 要求的「真实 provider 基线校准」输入。
- **风险**：①修订若过宽＝变相放水——DoD 同段红线「禁止通过隐藏等待伪造性能」，改口径正是该红线防的软性形态之一；②若修订不附旧口径 FAIL 事实，事后无法审计「当时到底差多少」；③修订阈值若无判据（n、percentile、重校准触发条件），V4 无法证伪。
- 【推断】风险可控的形态是「**事实层保留原口径 FAIL 记录 ＋ 决议层产出可证伪修订口径**」的复合，见 §5 推荐。

### 选项 C — 标注环境因素后判（维持原口径 FAIL 判定＋环境/trade-off 注记）

- **依据**：report §9 边界声明（共享 dev 实例、叠加态对照）＋ trade-off 机理链（tier 塌缩修复时间线）。
- **风险**：①环境注记无法升级为豁免——「非单变量归因」的限制是双向的：既不能证明退化，也不能干净地证明「全是环境」；②FAIL 计数照旧（不改善 FINAL 状态），注记若被读作「找借口」反而损耗报告公信力；③L0 项套「环境因素」注记不成立（见 §3.1 定性），混用会连累 L2 项定性的可信度。
- 【推断】选项 C 的合理残余用途是**给 L2 项的 FAIL 判定附定性注记**（「口径过严＋真实 trade-off」），而非作为独立处置路线。

---

## 5. 推荐口径（可证伪判据）

【建议】**A+B 复合，逐项分治**——原口径事实全部保留入册（不删 FAIL），L2 项产出修订决议，L0 项不修订、判 FAIL 并派 V4 工作项；修订决议随 FINAL_V3_GATE_REPORT 同批产出、引用本备忘为依据。具体：

1. **L0 no-model ≤500ms：不修订，终判 FAIL**，定性注记「功能缺位（TRIVIAL 不跳过生成链），非环境/非口径」；V4 工作项=E-01 W-2 no-model 直答生效后按同 harness 复测。
   - **可证伪复验判据 R2**：真模型窗 n≥26、`scripts/devtools/bench_ai_stack_l0_l3.py` 同构口径下 L0 TTFT p95 ≤500ms。现值 1781ms（`WT801-E08FINAL/facts.json` `by_layer.L0.ttft_p95=1.7812`）。
2. **L2 最终 ≤15s：原口径 FAIL 事实保留；产出修订口径 R1 并按 R1 判**——
   - **修订 SLO R1（L2 deep 档最终回复总时长）**：当期 provider 基线下 **L2 total p95 ≤75s**（=wt801 实测 65.356s × 1.15 余量；数据源 `facts.json by_layer.L2.total_p95=65.356375`，n=26）。
   - **重校准触发条件**：provider 价表/主力模型切换、或路由 tier 策略变更（任一发生则 R1 作废须重校准）——锚定 DoD「必须以真实 provider 基线校准」原文。
   - **硬伴随门（不可随 R1 放宽）**：L2 阶段反馈首事件 p95 ≤500ms（现 42ms PASS）；UI 隐藏调用冻结 >2s = 0 条（现 ack max 400ms 达成）。这两条守住 DoD 红线——允许深档「慢而深」，不允许「无反馈地慢」。
   - **修订依据注记（必须随决议入册）**：tier 塌缩修复时间线＋`qwen3_8_max` TTFT p50 64.91s＋L0/L1 同向改善排除系统性退化＋「叠加态对照、非单变量归因」边界（全部引自 WT801 report/notes，见 §3.2）。
3. **tier 账本（条款 7）：判「存在但有计量盲区」**——账本存在性 PASS（四车道分布表在档）；账本可信度注记 FAIL 倾向：
   - **可证伪判据 R3**：计量错挂行（`no_generation_model` 带 token）占比 ≤5% 为可信阈值；当前 7/104 = 6.7% 超标（`WT801-E08FINAL/notes.md` §4 qid 集），由 V3-FIX-545（P2 OPEN）承接，不阻塞 V3-8 判定但必须随报告注记。
4. **本地确定性 300ms（条款 1）：维持「口径外参考」注记，不本轮修订**。无独立测面是事实（WT406 §3 原文）；【建议】V4 若要操作化，候选测面=网关纯透传延迟（已有 TTFT-PROBE 先例 0.02-0.35s）＋ ContextPackBuilder 本地构建（p50 7ms/1000 行），两项旁证均远低于 300ms，届时正式化成本低。
5. **UI 冻结（条款 6）：按现有证据判 PASS**——判据 R4：新会话首事件（任意帧）p95 ≤500ms 且无 >2s 无反馈窗。现证据：ack 104/104 ≤500ms（max 400ms）＋ keyless 24/24 ＋ J-02 F5 6/6。此条建议在 Q-08 报告中作为「wt755/wt798 修正波的改善项」如实入册（骨架 V3-8 预判已有此意）。

【推断·风险声明】R1 的 75s 是「实测×1.15」的工程口径而非服务水平承诺；若 Q-08 双审认为余量应更紧（如 ×1.0=65.4s 硬贴实测）或更宽，争议点只剩这一个参数，判据结构不受影响——这正是把它写成可证伪形式的意义。

---

## 6. 与其他预裁项的边界

- 本备忘只裁 V3-8 的 SLO 口径，不触碰 Q-06 400 样本是否补制（WT801 §6 已给「不阻塞」建议，属执行资源裁决）。
- 「修而不复跑」的通用三选一是预裁⑤（Q-02/Q-04 面），本备忘的 L0「V4 复测」判据仅是 V4 工作项定义，不是 V3 终门内的复跑义务。
- 修订决议的落库渠道＝协调方（与预裁①同形态：DoD 加决议注、原文保留）；本备忘无权直接改 DoD。
