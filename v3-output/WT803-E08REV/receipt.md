# WT803 — E-08 销账独立审查 receipt（verdict: APPROVE-closure）

> 审查人 wt803（独立会话，未参与 E-08 任一交付段）｜ 2026-09-28 ｜ worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt803-e08rev` @ `a78b0818`（main HEAD，含 WT801-Q06-RETEST 产物；branch `agent/node-b/wt803/e08rev`）
> 审查对象：wt801 建议的 E-08（AI Stack 集成 Bench）销账裁决，证据链四段——①wt372 修前基线（`v3-output/WT372-E08-BENCH/`）②修正波（tier 塌缩 wt380 + 计量盲区 FIX-80 + L3-ACK；`v3-output/WT776-DOC-DE/E-line.md` §E.2-E-08）③wt798 首帧重采（`v3-output/WT798-E08SAMPLE/`）④wt801 验收级复测（`v3-output/WT801-E08FINAL/` + `v3-output/WT801-Q06-RETEST/`）。
> 方法：纯数据审计。全部结论出自对 raw jsonl/csv 的程序化复算（python3 stdlib，零后端代码执行、零栈接触、零 DB/Redis 访问）；harness `scripts/devtools/bench_ai_stack_l0_l3.py` 的 `_pct`/`stats`/SLO 表达式按源码逐条比对。gen 产物（`backend/sparkle/*_pb2*.py`）为已提交内容、worktree 内在位，按先例无需重生成。

---

## 1. VERDICT：APPROVE-closure（附条件见 §6）

wt801 的销账建议**成立**。四段证据链完整、口径贯穿一致、核心数字经全量程序化复算**逐数吻合**（不是抽中文档数字，是从 raw 重算后对表）；两项可证伪探针均未找到反例；未达 SLO 项（L0 直答、L2 total）与 FALLBACK 换标签缺陷的披露如实且充分。两项追踪义务方向正确，但**转台账落账是销账生效的前提条件**（§6-C1）。

---

## 2. 审查命令与结果实录

```bash
# 1) worktree（主仓只读，HEAD=a78b0818）
git worktree add --detach /Users/brsama/code/GitHub/Sparkle-sysrev/wt803-e08rev HEAD
#    → HEAD is now at a78b0818 state(fleet): 轮#306 …（8935 files）

# 2) 数字复算（脚本存 /tmp/wt803_recompute.py 等 4 件，stdlib 实现 harness 同款
#    _pct 线性插值；对 raw 逐行重算，与 report/facts 对表）
python3 /tmp/wt803_recompute.py    # §3 主对照全表 + SLO + FALLBACK + 配对 + Q-06
python3 /tmp/wt803_probes2.py      # 中位改善 + wt798 分层变体归因 + wt372 facts 对表
python3 /tmp/wt803_probes3.py      # 成本口径 + 预算前缀 + L2-09 缺行定位
python3 /tmp/wt803_median.py       # 45.1× 口径复算
python3 /tmp/wt803_probes5.py      # wt372 FALLBACK 7 qid 集
# 3) wt798 keyless 证据重算（36 样本合并）
# 4) tasks.json E-08 条目提取与逐项映射（§5）
```

---

## 3. 抽验数字表（raw 重算 vs 报告值）

### 3.1 wt801 分层 percentile（`raw-e08final.jsonl` 104 行全量复算，s）

| 层 | ack p50（报告） | ack p95（报告） | TTFT p50/p95（报告） | total p50/p95（报告） | 判 |
|---|---|---|---|---|---|
| L0 | 0.0290（0.029） | 0.0451（0.045） | 1.0767/1.7812（1.077/1.781） | 2.1147/21.1619（2.1/21.2） | ✅ 全符 |
| L1 | 0.0309（0.031） | 0.0436（0.044） | 1.6565/2.5962（1.656/2.596） | 26.6298/30.9264（26.6/30.9） | ✅ 全符 |
| L2 | 0.0219（0.022） | 0.0424（0.042） | 1.9026/8.3271（1.903/8.327） | 29.5649/65.3564（29.6/65.4） | ✅ 全符 |
| L3 | 0.0304（0.030） | 0.0541（0.054） | 10.9362/113.1504（10.936/113.150） | 68.4858/126.7048（68.5/126.7） | ✅ 全符 |

全量 ack：p50 0.0289 / p95 0.0461 / max 0.3999，≤500ms **104/104**（报告 0.029/0.046/0.400/104）✅。`t_first_event_s == t_first_stage_s` 104/104（本臂 ack 即首事件，表内两列同源成立）。

### 3.2 SLO 判定（表达式按 harness 源码 ：815-828 复算）

| SLO | 阈值 | 重算 | 判定（报告） | 判 |
|---|---|---|---|---|
| L0 no-model TTFT p95 | ≤500ms | 1781ms | FAIL（1781ms FAIL） | ✅ |
| L1 TTFT p50 | ≤2.5s | 1.656s | PASS（1.66s） | ✅ |
| L1 TTFT p95 | ≤5s | 2.596s | PASS（2.60s） | ✅ |
| L2 free 首事件 p95（n=13） | ≤500ms | 42ms | PASS（42ms） | ✅ |
| L2 total p95 | ≤15s | 65.356s | FAIL（65.4s） | ✅ |
| L3 ACK p95 | ≤1s | 0.054s | PASS（0.054s） | ✅ |

**2 PASS/4 FAIL → 4 PASS/2 FAIL 成立。**（facts.json `slo_results` 六键与 summary 表同源，:935 由表回填。）

### 3.3 同 qid 配对（wt372 raw vs wt801 raw，t_first_stage_s）

- 配对 **103 对**（唯一缺对 = **L2-09**，wt372 raw 该行无 t_first_stage_s——与报告「修前 103/104」口径自洽；修前 error 行 L0-21 反有 ack=0.34s 在对内）；改善 **102**、变慢 **1** = L0-01 **353.1→399.9ms** ✅（报告 353→400）。
- 中位改善 **45.08× ≈ 45.1×** ✅ ——精确复现条件：103 对**含变慢对**的全集中位数（含 0.88× 一项）；若只取 102 个改善对则为 46.87×。报告未注明口径，属表述粒度问题（见 F2），数字本身无错。
- 抽样 5 条逐数核对：L0-01 353.1→399.9 / L0-02 298.0→34.9（报告 298→35）/ L0-05 271.6→12.7（272→13）/ L0-06 526.0→18.6（526→19）/ L3-26（SIGKILL-resume 行）4612.7→72.4ms ✅ 全符。

### 3.4 计量与成本

| 项 | 重算 | 报告/facts | 判 |
|---|---|---|---|
| db_model 分布 | fast 68 / no_generation_model 18 / chat(plus) 12 / max 5 / standard_thinking 1 | 同（facts `models`） | ✅ |
| no_generation_model 带 token | 7 条 = L3-06/08/15/18/21/23/26 | 同 7 qid | ✅ |
| 与 wt372 修前 metered-default 集 | 完全同集（wt372 dynamic_issues `request_ids_metered` 7 条同 qid） | 「同 7 个 qid」 | ✅ |
| quality_pass / error | 68/104、0 error | 68、0 | ✅ |
| tokens / cost | 347796、**$0.126854**（CSV `cost_usd`=harness 官方价表列求和） | 347796、$0.1269 | ✅ |
| fallback_flag | 0（修前 19） | 0 | ✅ |

### 3.5 预算与 Q-06、keyless

- 预算留痕：①臂 raw 104 行、request_id 全 `wt801-e08-*` 且 104 个全 distinct；Q-06 40 行全 `wt801q06-*`；keyless 24 样本零调用；**104+40+1（SIGKILL 孤儿，仅 DB 留痕，仓库内不可独立复核，与 L3-26 resume 重跑行自洽）= 145/150** ✅。
- Q-06 切片重算：40 行、0 error、首事件 p50 27-32ms / p95 37-43ms、total p50 2.1/23.1/23.8/52.8s ✅ 与报告逐数符；`facts-bench.json` 各层 `_reportable:false`（NOT_REPORTABLE 纪律编码在产物内）。
- keyless（wt801）：raw 24 样本重算 mean 35.9ms ✅；表内 p50 36.9/p95 55.6 为 **tail 口径**（summary.json `t_tail_p50/p95`=0.0369/0.0556；t_ack 口径为 36.4/54.6ms）——报告脚注¹已如实注明 ✅。
- keyless（wt798）合并 36 样本重算：p50 28.4ms ✅、max 37.9ms ✅、36/36 ≤100ms ✅；p95 重算 34.1ms vs 报告 33.2ms（tail/线性口径差，量级不变）。早前帧序证据（`wt798_ordering_check.json`、钉测名）在库可查。

### 3.6 wt372 修前基线复算与跨段一致性

- 全量 ack：1.190s / 6.067s / max 34.56s / ≤500ms 21/103 —— 与 wt801 §3.1、wt798 §3.1 引用**逐数一致** ✅。
- 分层（wt801 §3.2 修前列）：L0 0.374/0.898、L1 1.079/3.063、L2 1.776/5.719、L3 3.109/7.247 —— 重算**全符** ✅；首事件列（0.352/0.898、1.019/3.063、1.500/5.447、1.583/7.026）全符 ✅。
- wt372 facts by_layer 与 E-line §E.2-E-08① 表（TTFT/首事件/total）逐数符；SLO 修前 2 PASS（L1×2）/4 FAIL 符；tier 塌缩 85/85 fast + default 19（12 零 token + 7 带 token）符；L2-free 首事件 p95 4282ms 符。
- **例外（F1）**：wt798 §3.1 的修前分层 5 行（0.355/0.934、1.066/3.416、1.776/5.746、2.622/7.324）与 wt372 raw 重算不符——归因定位：wt798 用了**不同 percentile 实现**（p50=floor 取整、p95=round 取整；逐数复现：floor_p50 四层全中、round_p95 四层全中），而 harness `_pct` 是线性插值。方向保守（把修前压得更差），不改结论量级；wt801 终判报告用的是 harness 一致口径。详见 F1。

---

## 4. 可证伪探针结果

| 探针 | 结果 |
|---|---|
| 任一臂 ack>500ms 反例（报告称 104/104 过） | **未找到反例**：104 行 max=399.9ms（L0-01），>500ms 集为空，>1s 集为空 |
| SLO 判定表达式与数字吻合 | 六项全部按 harness 源码表达式重算吻合，含 L2-FEEDBACK 的 free-lane n=13 口径 |
| FALLBACK 换标签是否「同一缺陷」 | 证实：修后 7 条带 token 的 no_generation_model 与修前 7 条带 token default **同 qid 集**；harness `_fallback` 判据（`db_model=="default" or error`）对新标签**失明**，故 n_fallback=0、FALLBACK issue 不再自动生成——wt801「换标签未解决、summarize 不再计 fallback」的披露机理成立 |
| issues 8→3 成分 | 修前 8 项、修后 3 项 ✅；真实解决 4（L2-FEEDBACK/L3-ACK/ERROR/TIER-COLLAPSE，各有终判数字）+ 换标签 1（FALLBACK）= 8-5=3，与 notes §4 披露逐项一致 |

---

## 5. 口径审查与验收映射

**口径贯穿性**：引擎直连（gRPC StreamChat + guest JWT，网关 :8080 不进口径）在四段中披露一致——wt372 REPORT :15、wt798 头注（含 09:29 网关滚启期间离线对本口径零影响的披露）、wt801 头注/notes §头、E-line §E.2-E-08①。成本口径自洽：报告数字 = harness 官方价表（重算 $0.126854 精确），engine 内部记账列（engine_cost_usd_db 合 0.2740）为另一口径未混用。FALLBACK 8→3 的口径成分已在 wt801 §1/notes §4 双处如实标注（含「引用 issues 计数时须注此口径」）。

**tasks.json E-08 验收逐项映射**（卡面 acceptance + required_evidence）：

| 验收字段 | 覆盖证据 | 判 |
|---|---|---|
| raw CSV/JSON | WT372 raw.csv/jsonl（段①）+ WT801 raw-e08final.csv/jsonl（段④）+ Q-06 raw-bench（段④附） | ✅ |
| dashboard summary | 两代 summary.md（harness 生成）+ REPORT.md/report.md；wt801 summary 头部模板瑕疵已自曝（F4） | ✅ |
| percentiles 样本量≥100 | bench 级 n=104 满足（卡面 work item「100+ queries across L0-L3」同读法）；分层 n=26 与 Q-06 缩减切片 n=10/层不满足「每 percentile ≥100」的严格读法——分层 ≥100 统计的修后重制仍缺（见 F6，wt801 已披露并建议不阻塞） | ✅*（按 bench 级读法） |
| SLO 未达真实报告 + dynamic issues | 2 FAIL（L0 1781ms、L2 total 65.4s）如实报告 + dynamic_issues.json 3 项 + FALLBACK 追踪义务 | ✅ |
| base/final SHA | a1418084（wt372）/ bfb17984（wt798）/ 3fc5de77（wt801）均 main 可达；栈 cdc547be | ✅ |
| targeted tests / integration evidence | harness 在库可复跑；wt798 帧序钉测 + 36/36 early_ack 运行级证明；wt801 验收级复测 | ✅ |
| review receipt | **本 receipt**（销账四件事之①，此前唯一硬缺口） | ✅（本件补齐） |

---

## 6. 发现清单与 VERDICT 条件

**非阻塞发现**：

- **F1（引用卫生）** wt798 §3.1 修前分层表用了 floor/round 取整 percentile（非 harness 线性插值），8 个数字与 raw 重算有毫秒-秒级偏差（最大：L1 p95 3.416 vs 3.063）；方向保守、总口径行一致、不影响任何判定。V4 引用修前分层分布时以 wt801 §3.2 修前列（本 receipt §3.6 复算符）为准。
- **F2（表述粒度）** 「中位改善 45.1×」为含变慢对的 103 对全集中位数（改善对子集为 46.87×），报告未注明；数字无误。
- **F3（产物瑕疵，既有）** E08-ISS-QUALITY 的 evidence 只列 36 条中前 20 条 request_id（harness `[:20]` 截断），计数正确。
- **F4（产物瑕疵，已自曝）** wt801 summary.md 头部为 wt372 模板残留（"WT372-E08"、backend @ 0e4087ec、旧 guest 名）；实测栈为 cdc547be、guest wt801_e08_bench，wt801 notes §2 已如实披露，本审查核实。
- **F5（读法注记）** 「所有 percentiles 样本量≥100」按 bench 级（n=104）读法满足；严格分层读法下修后分层 n=26、Q-06 切片 n=10/层（NOT_REPORTABLE）不足，wt406 的分层 100 样本统计仍是修后栈上的缺口径。wt801 已披露、建议不阻塞——本审查**认可该读法与不阻塞判断**。
- **F6（预算复核边界）** 145 = 104+40+1 孤儿中，孤儿行仅 DB 留痕、仓库内不可独立复核；与 L3-26 resume 重跑成功行自洽，采信。

**阻塞级条件（销账生效前提）**：

- **C1（追踪义务落账）** wt801 两项追踪义务方向正确且充分性成立——① L0 直答缺位 + L2/深档 total 上行（65.4s/126.7s）作为 V4 首帧/拥塞与 SLO 设计输入；② E08-ISS-FALLBACK 本体（7 qid 多代理流计量错挂、成本低估、修复后 harness 对其失明）转持续追踪。但 FALLBACK 缺陷在修后**任何自动 dynamic_issues.json 中都不再出现**（换标签使判据失明），只存在于报告散文中——**销账落笔时必须把两项义务显式写进台账/销账条目**（含 7 个 qid 与 harness 失明机理），否则 8→3 会变成静默丢失。另建议（不阻塞）给 harness 补一条 `no_generation_model`-with-tokens 的 fallback-like 检出，防同类盲区逃过未来 bench；Q-06 400 样本修后重制维持 wt801 建议：另派预算卡、不随 E-08。

**VERDICT：APPROVE-closure** —— 卡面验收要素按 §5 映射全部满足（percentiles 一项按 bench 级读法并注记 F5）；集成 bench 交付本体 + 修正波 + wt798/wt801 集成与复测证据链完整、数字可信、披露诚实。销账在满足 C1 后生效。

---

## 7. 审查边界

主仓只读（仅 worktree add 与本分支 commit）；未重启/未触碰运行栈、未访问 DB/Redis、未触碰 ns001、未改台账/tasks.json/主文档、未 push。全部复算脚本为临时件（/tmp），审计仅消费入库产物；未验证 DB token_usage 归因（wt801 的 105 行/104/40 亲证属 DB 面，本审查采信其留痕自洽性）。
