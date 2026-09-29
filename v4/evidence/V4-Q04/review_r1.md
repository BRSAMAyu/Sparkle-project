# V4-Q04 一审 receipt（独立审查 wtQ04R1）

- 审查人：wtQ04R1（未参与实现/采样的独立会话）
- 审查时间：2026-09-29
- 被审分支：agent/v4/q04 @ 5f9a1807（基线 4622efe8；审查时工作树干净）
- 裁决：**PASS_WITH_CHALLENGES**（测量成立；7 项挑战需勘误 commit，不需重测）
- 方法：只读复算 raw 五件套 + 读工具源码 + 只读 SQL 交叉验证共享库（`docker exec sparkle_db psql` SELECT）+ 端口/凭据面复核；未写任何数据面状态，未留临时探针。

---

## 1. 统计面（首靶）——复算通过

- **raw 完整性**：5 个 raw 文件 SHA256 与 run_manifest.artifacts_sha256 逐一相符（`shasum -a 256 raw/*.jsonl`）。
- **分母对账**：raw-main 416 行 = 104×4 层，全 delivered，416 个唯一 request_id，零剔除零重试。行数与声称一致。
- **分位复算**：以线性插值法从 raw 独立重算 L0-L3 × 6 时刻全表，**与 summary-main.md / test_results.json 全部一致**（P50/P90/P99/max 逐格吻合）。n_reached 逐时刻吻合（L0 useful 101 / L1 delta 97 / L2 delta 84 / L3 delta 96）。
- **L2 首 delta P99=112.562s 异常值核——真实慢帧，非采样伪影**：L2-r2-08 / L2-r4-08 帧时间线显示 ~110s 内 9 次 ~10.0s 规则心跳 gap（status_update 间隔 10.0-13.8s），随后才出首 delta——服务端真实长阶段。四条最慢行全部是同一语料项 L2-*-08（reasoning=deep）×4 遍，恰为红项①的 3 行 + L2-r2-08（fully unmetered 行）。解释力自洽。**注意**：语料仅 26 条/层 × 4 遍，P99 实际由单项语料行为主导——解读时须带此脆弱性（limitations §1 已声明语料多样性边界）。
- **四时刻判定规则读码**（`scripts/devtools/bench_v4_q04_e2e_latency_cost.py`）：t_ack=首 ack 帧、t_first_delta=首 delta 帧、t_complete=meta 帧、t_first_useful=冻结 oracle（BOILERPLATE_TEXTS 常量 + phatic≥2/实质≥12 有效字符，与 run_manifest 描述一致）；澄清门纯 full_text 路径单列 t_first_fulltext_s，不以 delta 冒充——35 行复算吻合（L1 7 / L2 20 / L3 8，全 delivered、35-277 字符）。
- **oracle v1 已知误判的 v2 参考口径**：复算 3 行有用时刻 = 2.0264 / 1.2703 / 6.5145s，与 notes 声称精确一致；L0 useful p50 3.756→3.753（声称"不变"，实际移 3ms，可忽略）。
- **漂移切片**：run_manifest.drift 四组逐遍 p50 全部复算吻合（L0 11.1/10.0/15.4/6.6；L2 30.7/28.8/28.4/32.0；L3 34.7/39.4/40.0/42.5）。

## 2. 计费四红项复验与定性归属

以共享库只读 SQL 交叉验证（`SELECT … FROM token_usage WHERE request_id LIKE 'wtq04-%'`）：当前库内 370 行全部对账（main 252 + fastlane 104 + cancel 4 + pilot 6 + smoke 4；零重复 request_id）。**审查时点的最终态比交付时点（join 于 23:42:03）更进一步收敛**，据此逐项改判：

| 红项 | 交付声称 | 一审复验 | 定性归属 |
|---|---|---|---|
| ① no_generation 带 token | 3 行 216/216/277 tok | **成立**：L2-r1/r3/r4-08 恰 3 行 `no_generation_model_estimated`，tok/无usage帧/77-112s 首delta 全吻合 | **产品面**（计量缺陷；I10 检出桶使其可见） |
| ② 取消轮次记账 0 | 4 条取消，服务端续生成（13,320 tok 帧）但记账 0 | **成立（收窄表述）**：L2-CANCEL 帧级证据实（t=20.366s usage 帧 13,320 tok/$0.001332，早于 delta+取消；库行 no_generation_model/0tok）——服务端续生成+成本归零实锤。L0/L1/L3 库行亦 0tok，但无 usage 帧收据，"续生成"为合理推断非实证。raw 采集时仅 1/4 行可见（join 竞态），4/4 行最终均落库 | **产品面**（取消路径把真实成本记 0；收据缺失面 3/4 待补证） |
| ③ delivered 完全无计量 | main 14 + fastlane 13（快路 early-return 疑绕过 cleanup） | **部分推翻**：(a) main 14 → **12**（L3-r3-09/L3-r4-09 两行 23:05:20/25 已落库，join 晚于落库 38 分钟仍漏——join 竞态）；(b) fastlane 13 行**全部已在库**：23:42:02 恢复批（58 行/120ms 突发）中落库，标签恰为 I09 单测承诺的 `no_generation_model`/0tok（`test_deterministic_lane.py:399-430`）——I09 承诺在 live **成立 26/26**；"early-return 绕过"假设无证据：13 行缺失在时间轴上与 13 行在库行**交错分布**（23:20-23:37），符合竞争消费者竞态吞没-回亡信-恢复链，不符"系统性 early-return 漏发"。run_manifest"91 行全部为 model-lane 回退行"不实（91 = 78 model + 13 deterministic）。**遗留真红**：main 12 行至今（审查时点）无 usage 帧且无库行 | **main 12 行 = 混合面**（无收据+无行，无法区分产品漏发 vs 环境吞没，按已知队列事故环境面概率高）；**fastlane 面 = 环境延迟，非损失**（已收敛） |
| ④ 计量持久化丢失 | 152 行被坏消费者吞没；恢复 59 行 | **成立**：152 行 frame-only 至今不在库（2 行 late 归属 main-unmetered 非此桶，152 保持不变）；恢复批实测 **58 行**（23:42:00 分桶，全部 fastlane）——manifest 称 59，**差 1 未解释**。库内最新非 wtq04 行 = 2026-09-28 09:18:50.575，与"驻留栈计费停摆"声称精确吻合 | **fleet 环境面**（共享 queue:billing 双消费者 + 驻留栈凭据失效；非本卡代码） |

**四红项归属小结**：①②=产品面缺陷（报红正确且必要）；④=fleet 环境面事故（另派卡处置）；③交付表述失实（fastlane 半边被自身恢复批收敛、main 少 2 行、根因假设无据），遗留真红为 main 12 行无计量（归属待定）+ 审计 trail 延迟面。

## 3. I06 补迁移合规性——通过

- 迁移文件 `backend/alembic/versions/i06_20260928_add_context_selection_receipts.py` 在基线 4622efe8 已存在（I06 卡合并产物），revises=wt598_20260927 链正确；幂等守卫（has_table 即返）；只增无改（create_table+3 索引）；**有真 downgrade**（drop 全套）→ 可回退留证成立（`alembic downgrade -1`）。
- `backend/gateway/internal/db/schema.sql` 在基线已含 context_selection_receipts（20 处）→ **sync-db 链已随 I06 卡在上游刷新，本卡无 schema.sql/SQLC 快照欠账**。
- 经 Alembic 唯一入口对共享数据面 `upgrade head` = 硬规则 2 的正道执行；limitations §2 已自曝"超出只读字面"并给回退路径——处置合规。

## 4. 凭据纪律——通过

- `backend/.env`、`backend/gateway/.env` 均为 symlink 指向主检出（只读引用）；worktree 无凭据文件新增（`git status` 干净、commit 5f9a1807 diff 仅工具+证据+tasks.json）。
- 证据/工具全文 grep 无明文密钥（仅占位符与"零回显"声明）。"git 史初始凭据进程注入"声称与零落盘痕迹自洽。
- 凭据漂移环境声称获得**独立佐证**：审查中以容器 env 密码连 sparkle_redis 亦 WRONGPASS（与"跨仓凭据漂移"同类）；sparkle_db host 侧损坏声称与"token_usage 最新非 wtq04 行停在 09-28 09:18:50"精确吻合。

## 5. SLO 裁决校准——通过（一处数值勘误）

对照 `v4/06_evaluation/METRICS.json`：M04"生成调用=0；服务处理 p95≤500ms"、M05"p50≤2s/p95≤5s"、M06"p50≤4s/p95≤12s；20s 转交"、M07"≤5s；软90s/硬180s；单报最终耗时不把 ack 算答案"。

- **M05 FAIL**：p50=2.450/p95=6.844 复算精确 → FAIL 正确。
- **M06 FAIL**：p50=4.272/p95=34.250/p99=111.523 复算精确（p95 亦越 20s 转交线）→ FAIL 正确。
- **M07 PASS**：首状态帧 p50=0.282/p95=1.227/max=3.872 复算精确；完成 max=69.823、0 行越软 90s，完成面单列不冒充 → PASS 口径符合 caveat，成立。
- **M04 FAIL**：flag-on deterministic 子集 26 行 **0 token 实证**（db 0 + usage 0）——"生成调用=0"在该子集实际达标；"服务处理 p95≤500ms"未直接测（端到端代理 p50=1.32s），FAIL 判定偏保守可接受（flag=off 生成调用≠0 单独足以 FAIL）。**但引用数值 11.4s/46s 不可复现**：raw-main 全集任何标准分位法给出 delta p95 10.15-10.41s、complete p95 38.98-40.32s（greeting 子集 p95=11.147 为最接近来源，疑混用切面）——FAIL 结论不受影响（目标 500ms，实测超 20 倍+），数值须勘误。
- 任务 value 标注：tasks.json 置 in_progress/REVIEW_READY，evidence_verdict 预置 PASS_WITH_CHALLENGES 且 self_note 声明"以独立审查为准"——程序上可接受，value 以本 receipt 为准。

## 6. 成本面——对账通过

- main：DB 归因 250 行/1,022,536 tok/$0.102185 + 流内回执 152 行/545,200 tok/$0.054525 + 无计量 14 行 = **$0.156710，从 raw 逐行重加精确复现**；共享库现值 252 行/tok/成本三数与声称**分毫不差**。加 fastlane $0.010334 + smoke/pilot ≈ **$0.17 真实支出成立**。
- 价表绑定：`bench_ai_stack_l0_l3.py:63-68` dashscope_fast ¥0.225/¥0.974 per M tok，来源逐项注明（Aliyun 2026-09-10）。
- **tier 塌缩 100% dashscope_fast 复现**：归因 model 行 225/225 全为 dashscope_fast/fast，尽管 reasoning_mode_sent 分布 fast 208 / deep 156 / balanced 52——E08 先例复现成立。

## 7. 工具与可复现——通过

- 2 个 devtools 工具均登记（`scripts/devtools/README.md` +1 行）；recover 脚本前缀过滤 wtq04-、复用 `BillingWorker._to_stmt_data` 同列映射、dup 跳过——恢复产品自身计量，非造数。
- 自起栈用完即关亲验：8081/50052/8001 **无监听**；驻留栈已复原（50051/8080/8000 在听）——pkill 误杀披露与现状吻合。
- 复算命令（审查者可重放）：
  - `shasum -a 256 raw/*.jsonl`
  - `python3`（对 raw-main.jsonl 按层线性插值分位，见 §1 全表吻合）
  - `docker exec sparkle_db psql -U postgres -d sparkle -Atc "SELECT count(*),sum(total_tokens),round(sum(cost)::numeric,6) FROM token_usage WHERE request_id LIKE 'wtq04-main-%'"` → `252|1022536|0.102185`

---

## 挑战清单（C-1..C-7，需勘误 commit；不重测）

- **C-1（红项③fastlane 半边失实）**："13 行无账面行 / I09 承诺该面 0 行 / early-return 疑绕过 cleanup"被推翻：13 行已全部落库且恰为 I09 承诺的 no_generation_model/0tok（26/26 达标）；缺失模式为时间交错（竞态消费者），非系统性漏发。run_manifest"91 行全部为 model-lane 回退行"改为"78 model + 13 deterministic"；根因假设撤回，改报"恢复前审计 trail 延迟（最长 ~5min）+ 队列竞态"。
- **C-2（红项③main 计数）**：14 → 12（L3-r3-09 / L3-r4-09 已落库）。遗留红 = main 12 行无 usage 帧且无库行。
- **C-3（M04 数值不可复现）**：11.4s/46s 改为实测 10.1-10.4s / 39.0-40.3s（注明口径与切面），FAIL 结论不变。
- **C-4（manifest 模型分布错）**：dashscope_fast 219 + no_generation 24 + estimated 3（=246≠250）改为 225 + 22 + 3（=250）。
- **C-5（红项②表述）**："服务端继续生成"限定为"L2 有 13,320 tok 帧级收据；L0/L1/L3 无收据为推断"；"DB 记账全部 0tok"注明"以审查时点终态为准，raw 采集时点仅 1/4 可见"。
- **C-6（悬空引用）**：三个 summary 引用 `run_manifest.attempt_reconciliation` 但该键不存在——辅助调用计量对账从未落地。补该节或删引用；"漏辅助计费"验收面目前仅以 NOT_MEASURED 兜底（limitations §3），应明示为红项边界。
- **C-7（恢复计数差 1）**：声称 59，库内恢复批实测 58；差额来源补记。

## 非阻断备注（N-1..N-5）

- N-1 oracle"采样前冻结"为过程性声称（工具与证据同 commit 提交，git 无法独立证明时序）；oracle v1 对短直答的误判已如实披露且 v2 口径复算吻合。
- N-2 cache-hit 声称 0/528，按不同分母口径实测 0/526-534——均为 0，无影响。
- N-3 L2 P99 尾部由单项语料（L2-*-08）主导，26 语料 ×4 遍下 P99 对单项行为敏感——消费该数字的下游卡须知。
- N-4 M04"服务处理 p95"未直接测（端到端代理）；FAIL 保守不算错，但后续实现卡应补服务侧口径。
- N-5 评审 receipt（review_receipt.json）reviewer/status 空置符合"自称完成不算完成"模型；本 receipt 即其回填对象。

## 裁决理由

测量方法面（四时刻分离、分母纪律、成本三源、报红义务、环境偏离披露+回退路径）全部独立复算成立；核心数字（分位、成本、红项①④、M05/M06/M07）精确可复现，共享库交叉验证分毫不差；无任何伪造或美化迹象。挑战集中于报告层：红项③的定量与根因表述被终态数据部分推翻（工具 join 与自身恢复批的 TOCTOU 竞态）、M04 两处数值与 manifest 一处分布不可复现、一处悬空引用——均为勘误级，不动摇测量与裁决方向。故 **PASS_WITH_CHALLENGES**：完成 C-1..C-7 勘误 commit 后本卡可落 DONE_REVIEWED；红项①②（产品面）转实现卡处置，红项④与遗留 main-12 行无计量转 fleet 环境卡（共享 DB 鉴权修复 + queue:billing 单消费者化）。
