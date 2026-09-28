# WT801 — E-08 验收级真模型复测报告（wt372 同构全量 + Q-06 缩减切片 + keyless 探针）

> Worker wt801 ｜ 2026-09-28 10:11-11:25 (+0800) ｜ worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt801-e08final` @ `cdc547be`（branch `agent/node-b/wt801/e08final`，含 wt372 基线 `a1418084` 与 wt798 采样 `bfb17984`）
> 活栈（只消费）：引擎 gRPC :50051（PID 77460，09:55:27 启，backend 树 = 主干 `cdc547be`）+ uvicorn :8000（PID 77527）+ 网关 :8080 纯透传不进口径；三容器 healthy。采样全程 PID 未变。
> 口径：与 wt372 修前基线**同构**——同 harness（`scripts/devtools/bench_ai_stack_l0_l3.py`）、同 104 条语料、同切片、引擎直连（gRPC StreamChat + guest JWT）；测试用户为新建 bench guest（DB 亲证，见 notes §2）。硬预算 150 次真模型调用，实际 **145 次**（notes §1 逐项留痕）。

---

## 1. 结论速览

**E-08 的最后一笔测量缺口（销账四件事之④「真模型复测」）已补齐。wt755 intake-ack 前移在验收级样本量（104 条真模型全量）上成立：intake ack 修前 p50 1.19s / p95 6.07s / max 34.6s（≤500ms 仅 21/103）→ 修后 p50 29ms / p95 46ms / max 400ms（≤500ms 104/104）；同 qid 配对 102/103 改善、中位改善 ~45×。六项 Gate V3-8 候选 SLO 从 2 PASS/4 FAIL 变为 4 PASS/2 FAIL：L3-ACK（7.03s→0.054s）与 L2 阶段反馈（4.28s→0.042s）终判 PASS；L0 直答缺位（p95 1.781s）与 L2 total（p95 65.4s）终判 FAIL——后者较修前 49.5s 上行，是 tier 塌缩修复后 deep 档真实打到 plus/max 的代价，属路由修正的真实 trade-off。**

意外如实项：修前 8 条 dynamic issues 中，E08-ISS-FALLBACK 属「换标签未解决」——7 条带 token 的多代理流计量错挂原样持续（同 7 个 qid），仅标记名 `default`→`no_generation_model`，summarize 因此不再计 fallback；引用本报告 issues 计数时须注此口径。

## 2. 测量设计与执行实录

- **① wt372 同构全量**：104 条（L0/L1/L2/L3 各 26），真模型真路由，失败不重试；`raw-e08final.jsonl` + `raw-e08final.csv` + `summary.md` + `facts.json` + `dynamic_issues.json`（本目录）。10:11 起 50min 处后台进程遭 SIGKILL（exit 137），harness resume 机制续跑，L3-26 重跑成功，**无数据损坏**；被杀时在途 1 次调用留 DB 孤儿行（0 token 计量），计入预算。
- **② Q-06 缩减切片**：`q06_perf_bench.py --layers L0,L1,L2,L3 --reps 1 --limit 10` = 40 条 free 车道（预算所限；**wt406 原制 400 样本复测未执行**，见 §6）。q06 脚本经环境变量指向常驻栈 :50051（默认仍为 wt406 :50061，测量逻辑零改动）。
- **③ keyless 首帧探针**：`probe_first_frame_wt798.py` 24 样本，>2000 字符确定性拒收臂，LLM 零消耗，复核 ack 分布（§7）。
- 模板瑕疵披露：`summary.md` 头部引擎 commit/guest 名为 wt372 时代硬编码文本；实际 guest=`wt801_e08_bench`（DB token_usage 105 行全归因亲证）、栈代码=`cdc547be`。

## 3. 主对照表

### 3.1 E-08 收口核心表：intake ack（t_first_stage_s）修前 vs 修后

| 口径 | n | p50 | p95 | max | ≤500ms |
|---|---|---|---|---|---|
| 修前 wt372（`a1418084`，2026-09-25） | 103/104 | 1.190s | 6.067s | 34.562s | 21/103 (20%) |
| **修后 wt801 本次（`cdc547be` 活栈，真模型全量）** | **104/104** | **0.029s** | **0.046s** | **0.400s** | **104/104 (100%)** |
| 修后 keyless 探针（24 样本，LLM 零消耗） | 24 | 36.9ms¹ | 55.6ms¹ | — | 24/24 |

¹ 探针 summarize 的 tail 口径（mean 35.9ms）。keyless 与真模型两臂同带（~30-56ms），互证 ack 到达与后续是否走 LLM 无关。

**同 qid 配对**（103 对，修前 raw vs 修后 raw）：102 对改善，中位改善 **45.1×**；唯一变慢对 = L0-01（353ms→400ms，全新 guest 首条请求的冷启动形态，仍 <500ms，不构成回归证据）。示例：L0-02 298→35ms、L0-05 272→13ms、L0-06 526→19ms。

### 3.2 分层 percentile 对照（s；percentile 方法与 harness `_pct` 一致）

| 层 | 臂 | ack p50 | ack p95 | 首事件 p50 | 首事件 p95 | TTFT p50 | TTFT p95 | total p50 | total p95 |
|---|---|---|---|---|---|---|---|---|---|
| L0 | 修前 | 0.374 | 0.898 | 0.352 | 0.898 | 1.106 | 2.033 | 2.2 | 65.3 |
| L0 | **修后** | **0.029** | **0.045** | 0.029 | 0.045 | 1.077 | 1.781 | 2.1 | 21.2 |
| L1 | 修前 | 1.079 | 3.063 | 1.019 | 3.063 | 1.951 | 2.947 | 22.2 | 32.9 |
| L1 | **修后** | **0.031** | **0.044** | 0.031 | 0.044 | 1.656 | 2.596 | 26.6 | 30.9 |
| L2 | 修前 | 1.776 | 5.719 | 1.500 | 5.447 | 2.498 | 14.925 | 22.7 | 49.5 |
| L2 | **修后** | **0.022** | **0.042** | 0.022 | 0.042 | 1.903 | 8.327 | 29.6 | 65.4 |
| L3 | 修前 | 3.109 | 7.247 | 1.583 | 7.026 | 7.260 | 113.364 | 28.8 | 113.0 |
| L3 | **修后** | **0.030** | **0.054** | 0.030 | 0.054 | 10.936 | 113.150 | 68.5 | 126.7 |

修后四层 ack 全部塌缩到 22-54ms 恒定带、>1s 为 0 条（修前 3.1-7.2s 带）。TTFT/total 面（首内容帧之后）本修不触碰：L0/L1 同向小幅改善；L2/L3 上行见 §5 trade-off 说明。

## 4. SLO 终判（Gate V3-8 候选，口径同 wt372）

| SLO | 修前 wt372 | 修后 wt801 | 终判 |
|---|---|---|---|
| L0 no-model p95≤500ms | 2033ms FAIL | 1781ms | **FAIL（持续）** |
| L1 首个有意义反馈 p50≤2.5s | 1.95s PASS | 1.66s | **PASS** |
| L1 p95≤5s | 2.95s PASS | 2.60s | **PASS** |
| L2 500ms 内阶段反馈（free 首事件 p95） | 4282ms FAIL | **42ms** | **PASS（翻转）** |
| L2 最终 p95≤15s | 49.5s FAIL | 65.4s | **FAIL（持续，幅度上行）** |
| L3 创建/ACK p95≤1s | 7.03s FAIL | **0.054s** | **PASS（翻转）** |

**2 PASS/4 FAIL → 4 PASS/2 FAIL。**

## 5. E08-ISS 逐项终判

| Issue | 修前 | 修后实测 | 终判 |
|---|---|---|---|
| **E08-ISS-L3-ACK**（high） | L3 首帧/ACK p95=7.03s>1s | **0.054s**（n=26） | **解决（终判数字在案）**——wt798 采样判断的验收级确证 |
| **E08-ISS-L2-FEEDBACK**（high） | free 首事件 p95=4.28s>500ms | **0.042s**（n=13） | **解决（翻转）** |
| **E08-ISS-L0-TTFT / L0 直答缺位**（high） | TTFT p95=2033ms>500ms | **1781ms**（n=26） | **FAIL 持续**——L0 快答仍走完整生成链，真 TTFT p50 1.08s；是工作项（no-model 直答生效）非测量项 |
| **E08-ISS-L2-TOTAL**（medium） | total p95=49.5s>15s | **65.4s**（n=26） | **FAIL 持续且上行**——tier 修复后 deep 档真实打到 standard/plus/max（慢而深）；L3 total p50 28.8→68.5s、成本 $0.0117→$0.1269 同理。这是路由修正恢复「分层成本/质量账本」的真实 trade-off，V4 SLO 设计的起点数据 |
| **E08-ISS-TIER-COLLAPSE**（high） | 85/85 塌缩 dashscope_fast | 计量分布：fast 68 / chat(plus) 12 / max 5 / standard_thinking 1 | **解决**——wt380 三因修复 + 后续接线后分层车道真实存在 |
| **E08-ISS-FALLBACK**（high） | 19 条 default（12 零 token + 7 带 token 错挂） | 18 条 `no_generation_model`，其中 **7 条带 token（同 7 个 qid：L3-06/08/15/18/21/23/26）** | **换标签未解决**——多代理流计量错挂原样持续，`METERING_MODEL_NO_GENERATION` 显式标记（V3-FIX-80 波次）使 summarize 不再计 fallback，成本仍被低估（7 条计 $0）。同一缺陷不占新号，建议随 E-08 销账转入 dynamic issues 持续追踪 |
| **E08-ISS-ERROR**（high） | 1 条 gRPC 错误 | **0 条**（104/104 + Q-06 40/40 全成功） | **解决（本次窗口）** |
| **E08-ISS-QUALITY**（medium） | 39 条未过粗筛 | 36 条（粗筛通过 68/104） | 持平（同口径启发式粗筛；其解释需注 V3-FIX-507 个性化供给断链边界） |

## 6. Q-06 复测：缩减切片结果与 400 样本披露

**wt406 原制 400 样本（每层 50 distinct × 2 reps）复测未执行**：单该臂即需 400 次真调用，超出本卡 150 次硬预算（104 全量 + 余量）。按「超预算即停如实报告」原则执行缩减切片：

- 范围：4 层 × 前 10 distinct × 1 rep = **40 条，全 free 车道**（`--limit` 取前缀，pro 条目位于语料后段；pro 车道证据由①臂 26 条 pro 承接）。新建 guest `wt801_q06_bench_free/_pro`，request_id `wt801q06-*`，40/40 DB 归因。
- 结果（方向性读数，**n=10/层 <100，按脚本自身纪律不报 SLO 级 percentile，NOT_REPORTABLE**）：40/40 成功、0 error、0 fallback；首事件（ack）四层 p50/p95 = 27-32ms / 37-43ms，与①臂同带；raw 侧方向性 total（p50）：L0 2.1s / L1 23.1s / L2 23.8s / L3 52.8s，与①臂同形状。数据：`v3-output/WT801-Q06-RETEST/`（raw-bench.jsonl/csv、facts-bench.json）。
- **建议**：Q-06 400 样本全量复测不阻塞 E-08 销账（其承接的「100+ sample 统计」已由①臂 104 条满足）；如需重制该统计，另派预算卡。

## 7. keyless 首帧探针复核（0 调用）

24 样本（`wt801_e08_probe`，>2000 字符拒收臂）：first_frame_received 24/24，`early_ack=true` 24/24，stage=intake 24/24，t_ack mean 35.9ms / tail p50 36.9ms / p95 55.6ms；终帧 INVALID_ARGUMENT 24/24（设计内）。与 wt798（09:42 活栈）25-42ms 带一致——**wt755 集成在二次滚启后的栈上仍然生效**。数据：`evidence/ack_probe/`。

## 8. E-08 销账建议（给主会话）

销账四件事（E-line §E.2-E-08⑤）当前状态：

1. **review receipt（独立审查）**——仍开放，非本卡范围，是销账前唯一剩余硬缺口。
2. **wt755 门后集成**——✅ 已闭环（wt798）；本次复测在滚启后栈上二次确证（§3.1/§7）。
3. **E-03 残差移交笔（首帧重采）**——✅ ack 层面闭环（wt798），本次给出**验收级终判数字**：L3-ACK 0.054s、L2-FEEDBACK 0.042s，均 PASS（§4/§5）。
4. **真模型复测**——✅ **本次补齐**：wt372 同构 104 条全量 + keyless 探针复核 + Q-06 缩减切片（400 样本全量因预算未制，§6 披露，不阻塞）。

**建议 E-08 判定**：卡面验收要素（100+ queries、raw CSV/JSON+dashboard、percentiles 样本≥100、SLO 未达真实报告 + dynamic issues）全部满足；集成 bench 交付本体 + 修正波 + 集成与复测证据链完整。**可销账**，随卡注明两项遗留追踪义务：① L0 直答缺位与 L2/深档 total 上行是 V4 首帧/拥塞优化的输入数据（wt755 notes L1/L2/L3 勘察仍是现成设计）；② E08-ISS-FALLBACK 本体（7 条多代理流计量错挂）转 dynamic issues 持续追踪，勿因 issues 计数 8→3 误读为全清。

## 9. 诚实声明与边界

- 只消费活栈：零重启、零配置变更、零 Redis/DB 写入（token_usage 为引擎自身计量落账）；测试用户全部为新建 bench guest（DB 亲证），未触碰 ns001 及其 drive state。
- 真模型调用 145 次（预算 150），逐项留痕见 notes §1；约 347.8k+ tokens（①臂），计量成本 $0.1269（官方价表口径，不含隐藏辅助调用盲区）。
- 修前基线为 2026-09-25 的 wt372（引擎 `0e4087ec`），修后为 `cdc547be`——三天间隔内主干叠加了 tier 修复（wt380）、计量标记（FIX-80 波次）、507 接线等多笔变更，本对照是「叠加态 vs 叠加态」的工程对照，非单变量归因；单变量机理面由 wt798/wt755 的帧序证明与钉测承载。
- 引擎为共享 dev 实例，并行 workers 负载噪声无法完全排除；两轮同为串行 bench 形态，口径同构。
- `summary.md` 头部两行为 wt372 时代模板硬编码（引擎 commit/guest 名），事实以本报告与 notes 为准；harness 测量逻辑零改动（仅环境变量化 guest/前缀/目标，见 commit diff）。
- 后台进程 50min 处遭 SIGKILL 一次（exit 137），resume 续跑无数据损坏；在途 1 调用留 DB 孤儿行（0 token）计入预算。未登记新缺陷号（FALLBACK 为既有缺陷延续，543 仍未占用）。
