# FINAL_V3_GATE_REPORT.md —— 骨架草案（wt804，Q-08 预备）

> **状态：SKELETON / 非终判。** 本文件是 Q-08（V3 Final Gate Audit / Commercial RC，critical/MEDIUM/双审）正式执行前的骨架卡：逐 gate 骨架 + 证据链接 + 预判槽 + 裁决槽。所有 PASS/FAIL/BLOCKED 字样均为**预判**，一律以「待 Q-08 正式裁决」为准；本骨架不做终判、不改 DoD/台账/tasks.json。
> 骨架基线：main@`054b8c9b`（2026-09-28，含轮#313 预裁① B-01Δ 入册）。撰写：wt804。
> 上游底稿：[Q-line.md §Q.4-2 证据图](../WT779-DOC-OQ/Q-line.md)（主底稿）｜[WT788 runbook 波 4](../WT788-POSTGATE/runbook.md)（四预裁决项+manifest SHA 缺口）｜gate 原文=[V3_DEFINITION_OF_DONE.md](../../v3/V3_DEFINITION_OF_DONE.md)。
> 路径约定：本报告内相对链接自本目录起算（`../`=v3-output/，`../../`=仓根）；仓根 subdir 以 `../../backend/...`、`../../scripts/...` 引用。

---

## 0. 全景与统计快照（骨架时点 main@054b8c9b）

### 0.1 107 卡全景

- **104 / 107 done**（`v3/07_tasks/tasks.json` 机器口径实测：done=104、TODO=3）。
- **余 3 卡**：
  - **O-01** 公网 Staging HTTPS/WSS 一键部署 —— TODO，卡真实用户凭据（HUMAN_INBOX H-002：阿里云 TCC 开关+ZCode 重启）；
  - **Q-07** Chaos/Recovery/Offline/Restore Storm 终验 —— TODO，HEAVY 整窗+双审，是 Q-08 唯一卡级前置（runbook §3.4；工程前置 FIX-530 已修）；
  - **Q-08** 本卡 —— TODO，双审。
- 「107 任务完成」**不得**替代产品 gate（Q-08 卡面明示；DoD 是产品级条款）。

### 0.2 统计快照

| 项 | 快照值 | 出处 |
|---|---|---|
| CI | **四绿**（run 序列 23/25/27/29；CI 30 在跑守望中，轮#312-313） | fleet state 轮#286/#312 |
| mypy | **55 零漂移**（烧减链 1095→…→55 后新基线） | fleet state 轮#290（wt755 集成注记）、轮#296 |
| 台账 | **45 行 OPEN（0 P1；P2×5：168/439/505/542/545；P3×33、P4×7）**，按表尾状态列机器口径实测 @054b8c9b；正式执行时以 `scripts/devtools/ledger_union_merge.py --verify --strict-pipes` 复测为准 | `v3/06_agent_fleet/DYNAMIC_ISSUES.md` |
| JOURNEY ns001 | **day7 终门 PASS，七日 7/7 收官**（轮#289，08:19；升栈 0-7 步全绿为基座） | fleet state 轮#288/#289 |
| E-08 复测 | 已补（wt801，104 条真模型同构全量）：intake ack 修前 p50 1.19s→修后 **0.029s**；六项 V3-8 候选 SLO **4 PASS / 2 FAIL** | [WT801-E08FINAL/report.md](../WT801-E08FINAL/report.md) |
| J-02 | **全量证据销账**（wt802：A1a 秒表 6/6 全 ≤180s=99.8-102.2s、FirstActionCard 6/6、纯 UI 注册 6/6；轮#311 收编 697e34bf） | [WT802-J02-RETEST/REPORT.md](../WT802-J02-RETEST/REPORT.md) |
| FIX-507（数据飞轮断链） | **已修**@`8e503cd8`（三写面接线：交付面+spine hook+6h beat；轮#296；引擎滚启激活与生产写入验证状态待 Q-08 复核） | fleet state 轮#296、台账 |
| FIX-530（唯一 P1） | 已修（wt793），台账零 P1 | 台账、轮#290 |

### 0.3 预裁决项状态总览（Q-08 正式执行的前置输入）

| # | 裁决项 | 状态 |
|---|---|---|
| ① | portfolio 真源（=FIX-513/533） | **已裁**：B-01 矩阵为唯一真源，B-01Δ 入册 42→43（F24 除名并入 user、F43 journey/F44 recovery 新增 CONTEXTUAL、F20/F26 重定 CONTEXTUAL）；DoD V3-0 决议注在案（`cf8d6c16`）。裁决依据 [WT786-P513MEMO/memo.md](../WT786-P513MEMO/memo.md) + [WT790-B01DELTA](../WT790-B01DELTA) |
| ② | V3-2 映射口径 | **在航**：wt806 预裁备忘派卡中（轮#313）；备忘落库前本 gate 维持「映射待裁」 |
| ③ | SLO 修订决议 | **待裁**：输入已齐（[WT801-E08FINAL](../WT801-E08FINAL/report.md) 4 PASS/2 FAIL：L0 p95 1.781s、L2 total p95 65.4s）；按 DoD V3-8 原文「必须重新定真实 SLO」产出修订决议 |
| ④ | 三端条款双口径 | **待裁**：真机段 BLOCKED（FIX-511/H-009 未采集）/ API 级+模拟器 PASS 双口径并行标注 |
| ⑤ | 「修而不复跑」三选一 | **待裁**：Q-02 全 20 GJ、Q-04 六路红队修复后均无全量重跑——补跑 / 按锁级判 / 如实 FAIL(NOT_REMEASURED) 三选一（Q-line §Q.3-5：终门必须一次性还掉或显式裁决；驱动全在库） |

---

## 1. 逐 gate 骨架（V3-0 .. V3-10）

> 每 gate 四段：原文一行｜证据链接（宁缺毋滥，未定位的显式写「未定位到证据」）｜预判（待 Q-08 正式裁决）｜裁决槽。

### Gate V3-0 — Truth

- **原文**：42 个 feature 有唯一 portfolio 五态；无用户可达半成品入口；统计数字有 lineage；mock/seed/demo 隔离；能力由 runtime probe 得到。
- **证据**：
  - 权威矩阵 [v3-output/B-01/MODULE_MATRIX.csv](../B-01/MODULE_MATRIX.csv) + [portfolio.json](../B-01/portfolio.json)（B-01Δ 后全集 43：F24/F43/F44/F20/F26 处置见 §0.3①）；独立复核 [REVIEW_RECEIPT.md](../B-01/REVIEW_RECEIPT.md)（42/42 EXACT MATCH 系初始口径，Δ 后计数待正式执行重跑 B-01 式审计或钉时点）；759 模块四态审计 [REPORT.md](../B-01/REPORT.md)。
  - DoD V3-0 决议注（[v3/V3_DEFINITION_OF_DONE.md](../../v3/V3_DEFINITION_OF_DONE.md) 内，`cf8d6c16`——保留原文 42 系初始口径）。
  - FIX-258（demo 产出 origin 标记不喂记忆推断）、FIX-333（能力宣称真实化五族状态机）——台账行 FIXED 在案。
- **预判（待 Q-08 正式裁决）**：**PASS 候选**——真源唯一+B-01Δ 入册后词表分裂已消；残差=矩阵时点 vs HEAD 的 reachability 复核（GOV-015/WS6 删 3958 行、FIX-490 摘除等变化需入册或钉时点注记）。
- **裁决槽**：预裁①已裁；余「按 HEAD 重跑 B-01 式审计 / 显式钉时点注记」二选一（Q-08 执行时点确认，零代码、约半窗 vs 零成本）。

### Gate V3-1 — First Meaningful Value

- **原文**：新用户 ≤3 分钟理解价值并完成首次 meaningful action proposal；首屏无内部名词；demo persona 不冒充用户历史；核心 onboarding/home/chat 无 P0/P1 阻断、A/B 视觉清零。
- **证据**：
  - J-02 全量证据：[WT802-J02-RETEST/REPORT.md](../WT802-J02-RETEST/REPORT.md)（macOS desktop 通道，A1a 注册→首卡 6/6 全 ≤180s：99.8-102.2s；FirstActionCard 6/6；纯 UI 注册 6/6；run_id `j02retest_macos_20260928_101701_wt802`）+ 首跑 [WT792-J02-SIM](../WT792-J02-SIM)。
  - 示例/真实区分：FIX-143 FIXED@`62241e59`（guest 种子 `is_example` 全链透传+首屏「示例」badge）。
  - 视觉 A/B=0：[WT401-Q03-VISUAL/rubric_scores.md](../WT401-Q03-VISUAL/rubric_scores.md) 核心 13 屏。
  - JOURNEY day1-7 门（ns001）七日 7/7 PASS（轮#289）。
  - 真机/三端实机段：未采集——H-009-7（[HUMAN_INBOX](../../v3/08_operations/HUMAN_INBOX.md)）。
- **预判（待 Q-08 正式裁决）**：**PASS 候选**（simulator/desktop 秒表面+全量证据已达成，降级口径已解除）；真机走查段按三端口径注记（随预裁④）。
- **裁决槽**：无专属预裁项；「≤3 分钟」引用口径=J-01/J-02 秒表面（非统计分母口径）随报告注明。

### Gate V3-2 — Stuck → Useful Action

- **原文**：20 个代表性 friction scenario ≥18 产生与真实原因一致的 intervention；输出含 outcome/smallest step/为什么现在/完成证据/人机模式；不无限缩小任务；高风险能 clarify/abstain。
- **证据**：
  - **「20 ≥18」的直接单数证据：未定位到证据**（Q-line §Q.4-2 明示——这是本 gate 的核心缺口）。
  - 最近似锚：A-08 四臂消融 [WT393-A08-ABLATION/summary.json](../WT393-A08-ABLATION/summary.json)（四臂 full/no_memory/no_experience/fixed_policy×10 persona，journey 面 accuracy 0.45/0.55/0.45/0.30）+ [EVAL_RESULTS.md](../WT393-A08-ABLATION/EVAL_RESULTS.md)；Q-01 260 场景 journey/conflict 族 contract-simulation 判定（[backend/tests/v3_scenario_eval](../../backend/tests/v3_scenario_eval)）。
  - 机制面：A-03 摩擦诊断三轮行为修复（FIX-43/110/111/115/142 全 FIXED）；J-05「我卡住了」旗舰恢复（`f3bb620d`）；FIX-49/50/51 FIXED@`28442a5a`。
- **预判（待 Q-08 正式裁决）**：**NOT_DETERMINED→FAIL 候选/映射后 PASS 候选**——预裁②映射口径落定前无法判；如维持「必须单数证据」口径则现状=FAIL（NOT_RUN 性质）。
- **裁决槽**：**预裁②（在航，wt806）**：「20 ≥18」的 evidence link 映射口径（A-08 四臂+Q-01 simulation 判定可否作锚 / 或补一次 20-scenario 重跑）。

### Gate V3-3 — Human–AI Collaboration

- **原文**：分配离线评测 ≥90% 符合 rubric；人形成能力/判断的步骤不被 Agent 替代；高风险不可逆 autonomous execution=0；handoff 状态真实可恢复。
- **证据**：
  - X-10 77 场景：[v3-output/X-10](../X-10)（REPORT.md/results.json——allocation 100% 符合、high-risk auto=0、false success=0、real_llm_calls=0 显式）。
  - rubric 符合率统计锚：X 线章 77/77+85 场景盲评（[WT770-DOC-MX/X-line.md](../WT770-DOC-MX/X-line.md)）。
  - Hybrid 可恢复：GJ14 run 恢复 admin 门+resume PASS 面（[WT394-Q02-GOLDEN/summary.json](../WT394-Q02-GOLDEN/summary.json)）；P-04 低风险 auto-execute 五条件门 fail-closed（`cffd4034`）。
- **预判（待 Q-08 正式裁决）**：**PASS 候选**——四条款均有锚；基本齐。
- **裁决槽**：无。

### Gate V3-4 — Personalization That Helps

- **原文**：precision ≥95%；expired/revoked/wrong-user/wrong-scope 使用=0；over-personalization ≤5%；纠正改变相关决策；删除后零残留；paired +15pp（达不到必须报告真实结果而非改口径）。
- **证据**：
  - 红队 dashboard（**修前 FAIL 快照**）：[WT404-Q04-REDTEAM/dashboard.json](../WT404-Q04-REDTEAM/dashboard.json) + [REPORT.md](../WT404-Q04-REDTEAM/REPORT.md)——precision **0.0** / invalid **10**（硬门违反）/ over-personalization **41.67%** / uplift **0.0pp**。
  - 隐私与隔离四路 PASS（敏感零泄漏/删除撤回零复活/跨用户零串号/无关历史零上 prompt 面，同报告）。
  - 修复与锁：FIX-67 FIXED@`7244efb2`、FIX-68/69/70 FIXED@`12ce081b`；q04 两锁翻转+双失明锁（[backend/tests/q04_personal_redteam/test_q04_redteam_final.py](../../backend/tests/q04_personal_redteam/test_q04_redteam_final.py)，套件在 445 实跑绿内）。
  - 修复后**无六路全量重跑**（终态=修前 dashboard+锁级证据）。
- **预判（待 Q-08 正式裁决）**：**FAIL 候选**（现值口径=修前快照；锁级证据不能替代 dashboard 级复测）；已知边界必须如实带上——**uplift 0.0pp + A-08 no_memory 臂双指标反超 = 两个独立 eval 同向：当前实现下个性化净贡献未被证明为正**（DoD 原文禁止改口径）。
- **裁决槽**：**预裁⑤（三选一）**：补跑（q04 驱动在库，约半窗）/ 按锁级证据判 / 如实 FAIL(NOT_REMEASURED)。

### Gate V3-5 — Data Flywheel

- **原文**：每个 intervention 连接 context→decision→execution→outcome→evidence update；understanding_depth 五维；不显示未校准精确百分比；能答「过去什么帮助有效」并区分相关/因果。
- **证据**：
  - 飞轮闭环评估：[WT397-D08-FLYWHEEL/REPORT.md](../WT397-D08-FLYWHEEL/REPORT.md) + dashboard（双臂配对闭环 10/10 + `--verify-repro`；驱动 [scripts/devtools/d08_run_flywheel_eval.py](../../scripts/devtools/d08_run_flywheel_eval.py)）。
  - 五维 understanding_depth：D-02/D-03 面（确定性数据+校准恒等回退，`52dab3af` 链）。
  - 断链修复：**FIX-507 已修@`8e503cd8`**（D-05 intervention lifecycle 三写面生产接线：交付面+spine hook+6h beat；轮#296）——中段断链接通。
  - **运行级生产写入验证：未定位到证据**（507 接线激活需引擎滚启+一轮真链路后 `intervention_lifecycle_events` 有生产写入；轮#296 时引擎暂不滚启以保护 wt798 采样）。
- **预判（待 Q-08 正式裁决）**：**PARTIAL/FAIL 候选**——机制面齐（507 修后），运行级真实数据流证据缺；较 Q-line 撰写时点（大概率 FAIL）已改善，判定基础随 507 激活状态而定。
- **裁决槽**：507 修后判定口径（修后真实数据流已验证→可改判 / 激活未验证→如实 PARTIAL 并引 FIX-507 根因指针）——runbook §2.4 明示此项影响本 gate 判定基础。

### Gate V3-6 — Trustworthy Agent Runtime

- **原文**：100 run ≥99 正确 terminal/awaiting；false success=0、cross-user access=0、duplicate side effect=0；app 重启/WS 重连/worker restart 可恢复；cancel/timeout/retry/unknown 有语义；tool call 有 run_id/permission/idempotency/result/latency/cost。
- **证据**：
  - X-09（dual-reviewed `0c0e08ef`）：18 failure_kind 四归因分类器 162 组合×100 次零偏差、SIGKILL 真杀进程 e2e、UNKNOWN_OUTCOME 禁自动重试（=duplicate=0 机制根源）；测试在库 [backend/tests/unit/test_x09_failure_recovery.py](../../backend/tests/unit/test_x09_failure_recovery.py) + [test_failure_semantics.py](../../backend/tests/unit/test_failure_semantics.py)。
  - 耐久链：FIX-461（PEL 重放）/469（幂等闸）/487（清理接线）全 FIXED。
  - false success 面：FIX-78/79 FIXED+wt460 真引擎复验（error 帧 code=8 retryable、无模板顶替）。
  - trace 脊柱：O-02+FIX-491 审计链修复；**运行级 trace 重建证据缺一口**（`scripts/devtools/trace_timeline.py` 在库，跑真 GJ 即补）。
  - 进程韧性：FIX-530 已修（wt793）；残差 FIX-542 P2 OPEN（网关守护第二例+CWD 相对路径）。
  - 「100 run ≥99 terminal」批量统计锚：未定位到证据（需从 X-05/09 测试面提取或补跑）。
- **预判（待 Q-08 正式裁决）**：**PASS 候选**（三零硬门有机制+测试锚）；两项低成本补证（trace 重建/批量统计锚）建议正式执行时补齐后再判。
- **裁决槽**：无专属预裁项；补证项随 §2 checklist。

### Gate V3-7 — Experience Quality

- **原文**：L2–L5 审查完成：核心旅程 A/B=0、长尾 A=0；九类状态完整；Android/Web/macOS 核心 golden journey 均通过；视觉回归有基线截图与 diff。
- **证据**：
  - Q-03：[WT401-Q03-VISUAL/rubric_scores.md](../WT401-Q03-VISUAL/rubric_scores.md)——107 屏真渲染逐屏程序化探针零异常；**核心 13 屏 A/B=0**、long-tail 85 屏 A=0（遗留 C 级带坐标证据）；before/after 6 组成对。
  - Q-02：[WT394-Q02-GOLDEN/REPORT.md](../WT394-Q02-GOLDEN/REPORT.md) 首轮 13 PASS/6 FAIL/1 RESTRICTED 0 waive + 修复链 + [WT400-FIX53-REVERIFY/summary.json](../WT400-FIX53-REVERIFY/summary.json) 局部复验（GJ08 5/6 轮间波动在档）；**修后无全 20 GJ 重跑**。
  - 状态完整面：U 线 L2 双审 APPROVE（U-06 九态、U-07/U-08 面）。
  - 视觉回归基线：U-09 matrix 设施为就绪清单非已建基线（FIX-376/395 换锚链在案）。
  - **三端实机段：未采集**——FIX-511/H-009（中央箱零覆盖：U-09 45 张矩阵、G-05 真机批、U-08 走查、WT394 HUMAN_INBOX 17 项）。
- **预判（待 Q-08 正式裁决）**：**双口径**——API 级+模拟器渲染口径 **PASS 候选**；「Android/Web/macOS 核心 GJ 均通过」真机口径 **BLOCKED**（设备/浏览器权限，H-009）。
- **裁决槽**：**预裁④**：三端条款双口径并行标注（已列入 §0.3）；Q-02 重跑口径随预裁⑤。

### Gate V3-8 — Performance & Cost

- **原文**：L0-L3 分层 SLO 候选（本地 p95≤300ms/L0≤500ms/L1 p50≤2.5s p95≤5s/L2 阶段反馈 500ms+终态≤15s/L3 ACK≤1s）；无 UI 因隐藏调用冻结>2s；每 tier 账本；不达必须重新定真实 SLO，禁止隐藏等待伪造。
- **证据**：
  - Q-06 400 真样本：[WT406-Q06-PERF/facts-bench.json](../WT406-Q06-PERF/facts-bench.json) + [raw-bench.jsonl](../WT406-Q06-PERF/raw-bench.jsonl)——L1 双达标、L3 ACK 0.06s、L0 1879ms 与 L2 total 48.25s FAIL；tier 账本四车道复活（fast263/plus67/max25/standard2）；成本 $0.7288（$0.0018/query）；增长标度无 O(n²)。
  - **E-08 验收级复测（wt801，104 条真模型同构全量）**：[WT801-E08FINAL/report.md](../WT801-E08FINAL/report.md)——intake ack 修前 p50 1.19s/p95 6.07s → 修后 p50 **0.029s**/p95 0.046s（≤500ms 104/104）；六项 V3-8 候选 SLO **4 PASS/2 FAIL**（L3-ACK 0.054s PASS、L2 阶段反馈 0.042s PASS；**L0 p95 1.781s FAIL、L2 total p95 65.4s FAIL**——后者为 deep 档真实打到 plus/max 的路由修正代价，如实报告）；FALLBACK 计量错挂口径注记（FIX-545 P2 OPEN）。
  - 供应商波动：七场景注入+wt460 真引擎复验（全断/过载面修复后 11/12 error 帧 retryable、cap=20 下 30/0 全 ≤15.1s）。
  - E-08 销账四笔：receipt/wt755 集成（`0b063c7c`）/移交笔/复测④已补——销账判定待主会话（wt801 报告已给判定材料）。
- **预判（待 Q-08 正式裁决）**：**FAIL（2 项）+SLO 修订决议待产出**——按 DoD 原文「必须重新定真实 SLO」：终门产出修订决议而非沉默 FAIL；改善项（L3-ACK/L2 阶段反馈/首帧）如实入册。
- **裁决槽**：**预裁③**：SLO 修订决议（输入=WT801 复测数字；L0 no-model 直答缺位与 L2 total 预算重定/或派修后复测）。

### Gate V3-9 — Commercial Launch Engineering

- **原文**：HTTPS 远程可部署；移动/Web 可配远端 endpoint；密钥只在服务端；flame 与 entitlement 解耦；quota/成本/降级/kill switch/rollback 可观测；导出/删除/Memory 控制有效；backup/restore 演练成功；RC 有一键 smoke+rollback runbook。
- **证据**：
  - 解耦：O-04 双侧判官（flame/gameification 与 entitlement 解耦）。
  - 操作面：O-06 [backend/app/api/internal/ops_release.py](../../backend/app/api/internal/ops_release.py)（`GET /release-manifest`：model/config/migration 清单；release 五旗冻结键集+64 能力快照）；O-07 预算/背压/超预算 UX。
  - 导出/删除：data_export/memory export/ai-usage export 端点在库；M-07 删除级联红→绿。
  - 备份链：O-05 [scripts/backup_prod_data.sh](../../scripts/backup_prod_data.sh)+[restore_prod_data.sh](../../scripts/restore_prod_data.sh)+INV 校验器（WT773 演练；FIX-505 P2 OPEN=redis-stack 持久化错位残差；FIX-532 P3 OPEN=O-05 残余四项）。
  - **O-01 整款 BLOCKED**：HTTPS 远程部署/远端 endpoint 配置/密钥服务端验证全未执行（卡用户凭据，H-002）。
  - **「RC 一键 smoke+rollback runbook」未在远端行使**（ops_rollback_smoke 真栈面仅本机一次）；RUNBOOK_DEMO.md 与 docs/05_部署与运维/RUNBOOK_LLM_HEALTH_RESET.md 先例在库。
  - release-manifest **git SHA 缺口**：O-06 设计决定运行时不可靠自证——Q-08 按 runbook §4.3 选 (b) 带外记录集成 SHA+manifest 注记（(a) build-time 注入属 O-01 部署面）。
- **预判（待 Q-08 正式裁决）**：**双口径**——本地/机制面条款 **PASS 候选**（解耦/观测/导出删除/备份链脚本面）；远程部署段 **BLOCKED**（O-01，H-002）；manifest deploy 段=BLOCKED/本地 compose 形态注记。
- **裁决槽**：无专属预裁项；BLOCKED 项全部挂 HUMAN_INBOX 指针（H-002）；SHA 带外记录随正式执行执行。

### Gate V3-10 — North Star Measurement

- **原文**：North Star=WVPL（7 天内 ≥1 次 goal-linked action→observable outcome→state update 闭环）；必须同时报告 active users 分母/WVPL users/loops/user/outcome 类型/H-A-H/是否 proactive 启动；不得把 chat/send/task-click 当闭环。
- **证据**：
  - 定义→实现全链：[backend/app/core/north_star_wvpl.py](../../backend/app/core/north_star_wvpl.py)（词表判据，排除 chat/send/task-click）+ [cost_wvpl_metrics.py](../../backend/app/core/cost_wvpl_metrics.py) + cost_wvpl_worker（O-07 cost_per_wvpl；loops=0 不伪造）。
  - **JOURNEY ns001 七日驱动 7/7 PASS**（轮#289：day7 终门 08:19 PASS，升栈当日代码后 M1d6-M4d6 全 200；证据 `/tmp/ns001_journey_out/evidence/steps/` + `/tmp/day7_gate_run.log` + 备份 `Sparkle-sysrev/.journey_ns001_state_backup.json`——**/tmp 证据非库内，正式执行时应收编入库**）。
  - 生产分母=ns001 单用户七日；「active users 分母」在无公网部署下只有演示语义。
- **预判（待 Q-08 正式裁决）**：**PASS 候选（本地演示形态口径）**——全链在库+七日闭环实证；分母/口径如实标注（单用户演示，非统计显著口径）；报告时注明 day7 证据收编状态。
- **裁决槽**：无专属预裁项；演示形态口径标注随报告（可与预裁④同批确认）。

---

## 2. Q-08 正式执行 checklist（骨架交付物）

### 2.1 前置核验

- [ ] **Q-07 done**（唯一卡级前置；若窗口不够则 Q-08 按 Q-07=NOT_RUN 如实标注，不得用「历史 X-09 面已验」替代——runbook §4.4）。
- [ ] **预裁②③④⑤ 全部落定**（①已裁@`cf8d6c16`；②wt806 备忘在航；③输入已齐待拍板；④⑤待拍板）——避免审计会话变成裁决会话。
- [ ] 动工前重读台账现行态（本骨架 45 OPEN/0 P1 为 @054b8c9b 快照）+ `ledger_union_merge.py --verify --strict-pipes`。
- [ ] 锁 `release`；双 reviewer 名单（卡面 Reviewers: 2）。

### 2.2 零成本索引（正式执行第 1 步）

- [ ] 抓取 `GET /api/internal/ops/release-manifest`（model/config/migration 段）+ **git SHA 带外记录并 manifest 注记**（runbook §4.3 (b)）；deploy 段注记 BLOCKED/本地 compose。
- [ ] 本报告 §1 逐 gate 证据链接程序化复核（路径存在性+关键数字抽验）；「未定位到证据」项逐条处置（补证或维持）。

### 2.3 低成本补证（按预裁⑤结果裁剪）

- [ ] `scripts/devtools/trace_timeline.py` 跑真 GJ 重建 O-02 运行级 trace 证据（V3-6）。
- [ ] 「100 run ≥99 terminal」批量统计锚从 X-05/09 测试面提取或补跑（V3-6）。
- [ ] Q-02 全 20 GJ 修复后重跑一次（[scripts/devtools/q02_run_golden_journeys.py](../../scripts/devtools/q02_run_golden_journeys.py)，wt400 真栈形制，约半窗）——若预裁⑤选「补跑」。
- [ ] Q-04 六路红队修复后重跑一次（q04 驱动在库，约半窗）——若预裁⑤选「补跑」。
- [ ] ns001 day7 证据从 /tmp 收编入库（V3-10）。
- [ ] V3-0：按 HEAD 重跑 B-01 式审计或钉时点注记（裁决槽余项）。

### 2.4 FINAL 判定规则（报告本体落定时的机器纪律）

1. **DoD V3-0..V3-10 每条**必须有 evidence link + PASS / FAIL / BLOCKED / NOT_RUN 四值之一；不得空缺。
2. **任一 gate 判 FAIL → FINAL_V3 = FAIL**（如实交付，Q 线先例：诚实 FAIL 合法且优于假 PASS）。
3. **BLOCKED 单列**：逐项附 HUMAN_INBOX 指针（H-001~H-009）与解锁条件；BLOCKED 不并入 FAIL 计数，但 FINAL 总状态标注 BLOCKED 分量。
4. NOT_RUN 仅用于「未执行的必做项」（如 Q-07 未跑时的 chaos 面）；不得用 NOT_RUN 掩盖 FAIL。
5. 「107 任务完成」不得替代产品 gate；不得以 Mock/人工改库冒充模型结果；不删断言求全绿。
6. RC 入册四件：manifest（含带外 SHA）/config/model/flags + deploy 形态注记 + runbook 引用。
7. 报告入库后**双 reviewer 独立签收**（critical 卡面 2；独立=未参与本卡与被审 gate 交付的会话）；签收前 FINAL 状态一律为 DRAFT。

### 2.5 产出与验收

- [ ] 报告本体落 `v3-output/`（正式执行会话目录），本骨架作底稿归档。
- [ ] 双审 receipt 各一份；所有 BLOCKED 项有 HUMAN_INBOX 指针。
- [ ] 不改 DoD/台账/tasks.json（裁决产出走协调方渠道；报告只引用现行账面）。

---

## 附：骨架证据覆盖自检（wt804 实测 @054b8c9b）

- 11 gate 全部有骨架；**有定位证据的 gate：11/11**（每 gate ≥1 条可点路径）；**含「未定位到证据」缺口的 gate：4**（V3-2 单数证据、V3-5 运行级生产写入、V3-6 批量统计锚、V3-7 三端实机段）。
- 裁决槽共 6 类：①portfolio 真源（已裁）/②V3-2 映射（在航）/③SLO 修订（待裁）/④三端双口径（待裁）/⑤修而不复跑三选一（待裁）/⑥V3-5 507 修后判定口径（待裁）。
- 全部证据路径经 wt804 `ls`/开文件亲证存在；关键数字（秒表 6/6、SLO 4/2、mypy 55、45 OPEN、day7 7/7）逐一溯源 fleet state 或产物文件，非转引。
