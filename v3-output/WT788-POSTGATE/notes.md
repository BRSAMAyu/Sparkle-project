# wt788 素材读取实录（notes）

> 2026-09-28 ｜ worker wt788 ｜ worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt788-postgate`（分支 `agent/node-b/wt788/postgate`，自 main@`cb122a22`）
> 任务：汇编门后总执行手册。纯读取+规划，未改台账/未改任何 FIX 行/未碰运行栈与 ns001 状态文件/未 push。

## 1. 基线与环境实录

- `git log --oneline -5`（main@cb122a22）：`cb122a22` state(fleet) 轮#275 wt785 预审收口+补位 wt788 ← `ac4e872c` docs(rev) wt785 审查 wt755@938e845c APPROVE（即「review(O-05)/wt785 receipt」基线确认）← `16ac17b4` 轮#274 ← `6a289d6a` v4-handoff v0.6 ← `08f00268` wt783 HUMAN_INBOX。
- worktree 创建：`git worktree add .../wt788-postgate -b agent/node-b/wt788/postgate cb122a22`。
- **撰写中途 main 前进** `cb122a22 → 5833639a`：新增 `88ff9e45`（wt784 J-02PREP 包并入 main）+ `5833639a`（state 轮#276）。`git diff --stat cb122a22 5833639a -- v3/06_agent_fleet/DYNAMIC_ISSUES.md v3/07_tasks/tasks.json` **为空**（台账与 tasks.json 两时点逐字节未变，runbook 编号口径不受影响）。
- **wt784 worktree 被舰队回收**：首次探查时 `Sparkle-sysrev/wt784-j02prep` 在册（branch `agent/node-b/wt784/j02prep`@e36fe444），读取其 runbook 前 40 行后分支与 worktree 被删——随后确认内容已以 `88ff9e45` 并入 main，改从 main 路径读取全文。教训已在 runbook §4.4 记录：引用素材一律用 main 路径。

## 2. 素材逐个实录

### 素材1：`v3/06_agent_fleet/DYNAMIC_ISSUES.md`（407 行，363 处 V3-FIX 提及）

- 解析方法：`awk -F'|'` 取末二列状态格，凡以 `OPEN` 起头者列出；**剔除「OPEN 补记FIXED@…」「OPEN→FIXED@…」两类实际已修仅状态格未翻/已带的行**（09/10/23/61/62/199?/417/418/427/455 等——其中 199 经第二次标题抽取确认为真 OPEN）。
- **真 OPEN 共 44 行**（含 439）。重点行全行文本逐条提取（495/505/507/513/514/528/529/530/532），其余 33 行提取 ID+P+标题前 110 字。
- 关键确认：
  - **FIX-53 状态格已是 `FIXED@10d3d7e8`**（wt779 依补记翻格，V3-FIX-512 当场收口 2026-09-28）——任务清单里「FIX-53 外历史 OPEN」按现行台账已不成立，runbook §5 如实注记防误报。
  - **FIX-508 已收口**（状态格 `FIXED@补闭即修复`，主会话 2026-09-28：491/492/493 三行重写 FIXED@1e3b6ebf）——不在派卡清单。
  - FIX-530 是唯一 OPEN P1；FIX-439 OPEN 且 wt785 receipt 明示集成后**保持 OPEN**（端到端复测前置）。
  - FIX-532 含 wt782 审查纠偏：prod compose 已有 `--dir /data`（docker-compose.prod.yml:618），错位真实面=**dev docker-compose.yml**；新残差=prod AOF on 而 backup/restore 仅 RDB。
  - 在航登记分支（勿重复派卡）：495→wt760/s01、500/501→wt765/o06、504→wt769/docbc、510→wt775/upsg、524→wt777/p499、507/509→wt776/docde（登记会话）、529→wt778/mypy11（发现者，行为变更超其授权面）。

### 素材2：`v3-output/WT785-WT755REV/receipt.md`（72 行，全文读）

- Verdict：**APPROVE-for-integration（附重编号映射）**。对象 `938e845c`（分支 agent/node-b/wt755/slo，base=merge-base 68dc7e20）。
- 重编号：wt755 新增行 V3-FIX-491→**498**（主干 491 已被 wt754/wt761 占用，497 被 wt761 占用；498=轮#254 预先改道分配且主干 0 命中；回退 533）。
- 三处引用同步：①新行行首 ID ②出处格「预分配号 491…」改写为重编号注记 ③439 行进展注记「预占 V3-FIX-491」→498。
- 唯一冲突文件=`DYNAMIC_ISSUES.md`（表尾 append 撞行；439 注记 hunk 可干净落位，merge-tree 实证）。
- 复跑数据：触达 4 测试文件 42 绿；红验证 FAILED（真红）；受影响面合集 1419 passed/1 failed（唯一红=notes 预报既有 flaky `test_signal_spine`，单跑绿）；ruff/mypy delta 双 0（mypy 66=66 仅 arg-type 2400→2415 平移）。
- 证据回查：wt372 raw.jsonl 104 行/103 含 t_first_stage_s/**恰 21 条 ≤0.5s**；L2-08 intake@3.0305s；REPORT p95 5446ms 全吻合。
- 集成建议：落位后重跑 `ledger_union_merge.py --verify --strict-pipes`；**439 保持 OPEN**。
- 残差不移交：L1 前奏前移/L2 门并行化/L3 拥塞等留 wt755 notes §3 分级表。

### 素材3：`v3-output/WT779-DOC-OQ/Q-line.md`（195 行，全文读）

- Q 线 6/8 done；Q-07/Q-08 TODO 未启动。
- **Q-07**：前置 X-09✓ O-05（现 tasks.json 已 done，本手册复核）U-06✓；**FIX-530 P1 是 Work 1（Redis issue）直接前置，建议先修再验**；执行计划三层资产复用（q06_provider_chaos.py + O-05 restore_consistency_check INV-1..7 + X-09 failure semantics）；判据 false success=0/duplicate=0/历史 SLO 不大幅退化；估 HEAVY 一整窗。
- **Q-08**：唯一缺的卡级前置=Q-07；卡面 Work 三条准备度（Work1 就绪=证据图即索引草案；Work2 纪律已示范；Work3 大半就绪+三缺口：**①release-manifest 缺 git SHA**（build-time 注入或带外记录）②deploy=O-01 未启动 ③runbook 先例在库）。
- **DoD V3-0..V3-10 逐 gate 证据图**（§Q.4-2 表）：11 gate 各有「已天然满足证据面 / 需补需裁决」两列——本手册波 4 直接引用；四个裁决项=portfolio 词表(=FIX-513)/V3-2 friction 映射/SLO 修订(L0 1879ms+L2 48.25s)/三端条款双口径，**建议终门前由协调方预先拍板**。
- 终门执行建议（成本从低到高）：①零成本 manifest 抓取+索引 ②低成本补证（trace_timeline.py 真 GJ+Q-02/Q-04 全量重跑各半窗）③裁决项随 FINAL 报告 NOT_RUN/FAIL/BLOCKED 标注产出。
- 其他：Q-02/Q-04「修而不复跑」三清单（含 FIX-57 GJ08/GJ15 DEFERRED）；V3-4 负面结论（Q-04 uplift 0.0pp+A-08 no_memory 反超）必须如实进终门与 V4；FIX-512/513 登记实录；号占用核验段。

### 素材4：`v3-output/WT784-J02PREP/`（先经兄弟 worktree 读 40 行，后从 main@88ff9e45 读全文 210 行 + checklist/notes 文件在册）

- 已存在**完整 J-02 执行 runbook**：通道选择（主=macOS desktop，备选 iOS Simulator/Android 同一 dart 驱动换 `-d`）；fresh install 三通道 wipe 语义；构建命令；**前置缺口如实声明：`integration_test/j02_fastpath_journey_test.dart` 不存在，执行会话第一件事编写该驱动**（红→绿，产品代码零改动）；Leg R 注册端 10 步（R8 秒表 ≤180s 主判据）+Leg G 游客端（G4 只读 DB 探针双 0 行）+Leg U 升级端；5 persona 差异化判据；秒表打点 J02_MARK/J02_SUMMARY 形制；失败留证规则（新缺陷自 V3-FIX-533 起、只写 notes 不编辑台账）；§7 判据↔acceptance 映射表；§8 产物命名模板（`v3-output/WT784-J02-SIM/`）；验收=独立会话审+wt772 receipt `7bbaf092` 销账前置。
- runbook 据此在 §3.1 引用为照单执行项，未复制全文（避免双真源），只提要点+指针。
- 交叉核对 `v3/01_product/FIRST_3_MINUTES.md`（50 行全文）：Automated simulator acceptance 七条清单与 wt784 runbook F1-F7 一一对应。

### 素材5：`v3-output/WT776-DOC-DE/E-line.md`（214 行，全文读）

- §E.2-E-08「AI Stack 集成 Bench——当前状态盘点」完整性能图景：
  - **修前**：wt372 `a1418084` 104 真模型 query（L0 TTFT p50 1.11s/p95 2.03s；L2 total p95 49.5s；L3 ACK 7.03s；tier 塌缩 dashscope_fast 85/85；成本 $0.0117）；dynamic issues 五项（E08-ISS-L0-TTFT/L2-FEEDBACK/L2-TOTAL/L3-ACK/FALLBACK 计量盲区）。
  - **已修**：tier 塌缩→wt380 `b42e279d`（修后未重采 104 条）；计量盲区→FIX-80@a1587328；L3-ACK→Q-06 `12e89303` 400 样本复测 0.06s 转准；首帧前段→wt755 `938e845c`（intake ack 前移+归因修正：门路径仅 9ms，真凶=StreamChat 前奏+守卫链 6 串行 await）。
  - **未修**：L0 no-model 直答缺位；L2 total ~48s 超预算；免费层前置静默；wt755 L1/L2/L3 勘察未实施。
  - **复测路径**：wt372 驱动在库；Q-06 bench 五件在 scripts/devtools@`12e89303`；**最小集=Q-06 同构 400 样本+wt755 集成后首帧重采**。
  - **销账缺口四笔**：①review receipt ②wt755 集成 ③E-03 Leader 裁决残差移交笔 ④真模型复测——「107 卡里销账成本最低的一张」。
- wt372 bench 实物核实：`v3-output/WT372-E08-BENCH/`（REPORT.md/dynamic_issues.json/facts.json/raw.csv/raw.jsonl/summary.md）`ls` 在库。
- 附带收获：§E.5 FIX-507 对 E 线含义（E-08 quality 粗筛解释边界）；FIX-508（491/492/493 台账未闭——后已被主会话收口，见素材1）；E-01 G 缺口清单（G-2/G-4/G-5 开放）归长尾池背景。

### 素材6：`v3/07_tasks/tasks.json` 卡面条目（python json 逐条提取）

- **J-02**：TODO；depends J-01,U-01；lock mobile-onboarding；HEAVY；1 reviewer；gate V3-1；acceptance=fresh user ≤3min useful action+seed 不进真实 Memory+三端 session 稳定；required_evidence 含 integration/simulator evidence+review receipt。
- **E-08**：TODO；depends E-03,E-04,E-07,C-08；lock ai-eval；HEAVY；1 reviewer；gate V3-7；acceptance=raw CSV/JSON+dashboard、percentiles n≥100、SLO 未达真实报告+dynamic issues。
- **Q-07**：TODO；depends X-09,O-05,U-06；critical/HEAVY/**2 reviewers**；lock chaos-eval；work 六项与 acceptance（false success=0/duplicate=0/SLO 不大幅退化）。
- **Q-08**：TODO；depends Q-02..Q-06,Q-07,D-08,P-05,G-05；critical/MEDIUM/**2 reviewers**；lock release；acceptance 三条（evidence link 逐条/不得用 107 任务替代 gate/FINAL_V3_GATE_REPORT.md）。
- 附加复核：O-05=**done**（wt782 审查回账）、O-01=TODO、X-09=done、U-06=done、E-03=done、J-01=done——Q-07 任务级依赖全满足。

## 3. 编排决定记录（本 worker 的判断范围）

- **波次划分**：按「机械集成 / 需派卡修复 / 需钥匙设备真栈 / Q-08 收口」四波；Q-07 归波 3（真栈整窗+双审）而非波 2，因其性质是终验执行非修复，且 FIX-530 修完才能开工。
- **合并裁决**：528+532 合并卡A（同为测试/脚本卫生）；504+510+514+222(+502/509 注记) 合并卡B（账面卫生，集成会话专属）；507/530 独立卡（双审）；529 独立微卡；495/513 裁决前置。
- **53 的处理**：任务清单列为 OPEN，但现行台账已 FIXED——按「源码/账面以实际为准」原则如实注记不派工。
- **533 号段冲突预判**：wt785 回退号(533) 与 wt784 执行会话新缺陷起始号(533) 潜在撞——runbook §3.1/§4.2 已写让位规则（wt755 回退占 533 则 J-02 从 534 起）。
- 全部 44 行 OPEN 均有去向（§5 表），无遗漏、无重复派卡（在航分支单列）。

## 4. 合规自查

- 未改 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`、未改任何 FIX 行、未改 tasks.json；worktree 内仅新增 `v3-output/WT788-POSTGATE/{runbook.md,notes.md}`。
- 未触碰运行栈、未碰 `/tmp/northstar_ns001_real_drive_state.json`、未 push。
- 对主仓只读（worktree 独立检出；台账/卡面均经 git 只读命令与文件读取）。
