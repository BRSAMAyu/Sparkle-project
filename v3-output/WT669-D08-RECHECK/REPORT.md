# WT669 · 卡 D-08 增量复证 REPORT — 数据飞轮纵向证明 @ 集成 HEAD

**Status: READY_FOR_REVIEW（增量复证；不重做首轮）**
**本证 base SHA:** `0495e085`（main HEAD 2026-09-27，worktree `wt669-d08`，零产品代码改动）
**首轮 dual 证物:** wt397 单提交 `46762b31` + 树内产物 `v3-output/WT397-D08-FLYWHEEL/`（其 dashboard `git_sha=2d2336ea`，历史产物照登不重写）
**本证产物:** `v3-output/WT669-D08-RECHECK/{dashboard.json, DASHBOARD.md, REPORT.md, raw/{flywheel,no_feedback}.jsonl}`（全部由 HEAD 真实服务面全量双跑产出，`--verify-repro` exit 0）
**模型 judge 使用声明：0 次**（沿首轮协议：Stage20 确定性 judge + 确定性指标程序复算）。

## 1. 结论（先说判定，漂移逐条归因在 §4，不粉饰）

**D-08 卡面两项验收在集成 HEAD 复跑后仍成立：10/10 persona 各自 ≥1 条可解释 adaptation 因果链（事件→读侧证据→与对照臂行为差分三段齐备）；无效/无效力个性化 5 条照登不筛（首轮 25 条历史产物原样保留）。但五面数字相对首轮发生实质漂移，全部归因到首轮之后落地的已登记产品修复（V3-FIX-50①/51 wiring 门与 B3 诚实化、V3-FIX-67 patch 归因 scope 谓词、V3-FIX-70 deny 安静窗）与已登记 OPEN 的 V3-FIX-97 饿死机制——零新发现不诚实面，不新开 FIX 号。** 旅程纠正腿在零事实 persona 上被诚实 no_action 饿死（16/20 纠正事件 skipped，established+changed 链 14→4），验收改由记忆安静腿（memory_quieter 10/10，且 Day3 已提前变安静）承载——这是 V3-FIX-97 预言的纵向面同构实证。

## 2. 双证判定（git log + 树内亲证，增量不重做）

| 证 | 内容 | 判定 |
|---|---|---|
| 证 1（git log） | `46762b31` feat(eval) wt397 卡 D-08：10/10 persona、25 条无效照登、Day0/3/7 双臂配对、`--verify-repro` 双跑一致 | 在案 |
| 证 2（树内产物） | `v3-output/WT397-D08-FLYWHEEL/` 全套在树（raw×2 + dashboard.json + DASHBOARD.md + REPORT.md READY_FOR_REVIEW）；engine/metrics/protocol/契约测试在树 | 在案 |
| 复算证 | HEAD 上 `--summarize-only` 从首轮 raw 复算 dashboard：**除 `generated_at`/`git_sha` 两字段外逐字节一致**（指标代码在 +1149 提交后确定性未变） | 吻合 |
| 独立审查回执 | 未检得（v3-output 内无 D-08 review 件；协调分支 state.json 本机不可达） | **缺**——卡面 Required evidence 的 review receipt 仍欠 |

依赖项三项全部已落地，无需等待：D-06（`c90641c0` + wt653 补证 `8a0a868f`）、D-07（wt369 `667001e6`；wt666 今日 insights 面在途与本证零交叠）、A-08（wt393 `2d2336ea`）。

## 3. HEAD 复跑验证件套（本证全部真实执行）

- **契约测试**：`backend/tests/unit/test_d08_flywheel_contract.py` **7/7 绿**（HEAD `0495e085`，sqlite 隔离口径）。
- **全量复跑**：`d08_run_flywheel_eval.py --out-dir v3-output/WT669-D08-RECHECK --verify-repro` → **exit 0**，per-persona canonicalized 双跑逐字节一致；评估不变量双臂各 30 探针全过。
- **复算链**：dashboard 全部数字由 raw 程序化复算（`d08_flywheel_metrics.v1` 未 bump，指标代码对 raw 的映射零改动——漂移全部来自被评估产品面的真实行为变化，非口径改动）。
- **环境项**：worktree 缺 gitignored `backend/app/gen`、`mobile/lib/gen` 按先例自主仓 `cp -RL` 补齐；`backend/.venv` 符号链接自主仓（未入库）。pytest 无 `.env` 落 sqlite（隔离 worktree 守卫口径）。
- **ruff/mypy**：本证零 Python/产品代码改动（新增仅 v3-output 产物与本报告），触达文件零、零新增。

## 4. 首轮（base 2d2336ea）→ HEAD（0495e085）漂移对照（逐条归因）

| 面 | 首轮 | HEAD 复跑 | 归因（引入提交/台账号） | 判定 |
|---|---|---|---|---|
| 旅程纠正链（established+changed） | 14 | **4**（p02/p03/p04 三 persona + 基线对齐项；filed 4 / skipped 16，skip 原因 `diagnosis_matches_truth_or_not_act`） | wt412 `28442a5a` V3-FIX-50①（B1 exact-tie→B3 诚实 no_action）→ 零事实 persona 旅程不再到达 act 出口 → 协议纠正入口饿死 = **已登记 OPEN V3-FIX-97 的纵向同构实证** | 已知结构性代价，非新缺陷 |
| memory_not_quieter 台账 | 10 | **0**（Day3 旧偏好即不再注入；Day7 维持 0/10 vs 对照 10/10） | wt404 `b79e6a27` V3-FIX-70① deny 72h 安静窗（对齐 D-08 PROBE_DAYS） | 真实产品改进：首轮如实入账的无效个性化已被修复 |
| ineffective_patch 台账 | 11 | **5**（保留不筛；established 链 11→5、未 established 9→5） | wt404 `7c164542` V3-FIX-67 applied_patch_ids 收敛到 situation_patches 同 scope 谓词 → 跨 scope patch 不再虚计「已应用」 | 台账前提随源变诚实（FIX-67 决议既定口径） |
| harmful_correction_differential | 4 | **0** | 同行 1 同根：纠正饿死后「纠正让类型更对但行动更差」的有害差分随之消失——代价与收益同源消失，非独立改进 | 与 FIX-97 同账 |
| utility 五维 | unknown→ok(0.667)×10 | **unknown→unknown ×10**（`unknown_reason: decisive feedback 2 < 3`） | FIX-70 安静窗 + wt412 wiring 门：Day3/Day7 旧偏好不再注入、对照话轮侵入 6/6→0/0 → 窗内 decisive 记忆反馈 6→2，跌破 3 样本下限 → D-03 unknown 语义**如实**报「数据不足」而非给假值 | 评估信号变稀的诚实呈现，非缺陷 |
| 对照臂侵入（fly/no_fb） | 6/6 | **0/0** | wt412 wiring v2 词牌门（与 A-08 post-fix「对照侵入 84-100%→0」同源） | 真实产品改进 |
| 被跟随决策匹配分均值 D0→D7 | 0.6→0.45 | **0.6→0.7** | 有害纠正差分消失 + 剩余纠正只落在事实充足 persona（纠正在能纠的地方生效） | 飞轮正向信号变强 |
| 理解五维迁移 | coverage/scope/freshness unknown→ok ×10、correctness ok→ok ×10 | 同左（coverage 0.33、scope 1.0、freshness/correctness 同构） | — | 保持 |
| outcome 面 | 20 关联/臂 | 20 关联/臂（admit 证据门全过） | — | 保持 |
| flywheel 臂事件行 | 180（memory_reference_outcome 60） | 170（**50**：Day4 二次 deny 因安静窗无注入可否认而消失） | FIX-70 下游 | 协议内解释 |

## 5. 卡面验收逐条对照（HEAD 口径）

- [x] **每个 Persona 至少一条 correction 或 plan change 后产生可解释 future adaptation** — 10/10 PASS：每 persona ≥1 条 established 且 behavior_changed 链（memory_quieter 10/10：deny×1+retract 后 Day3/Day7 旧偏好 0 注入 vs 对照臂同位注入；journey_correction p02/p03/p04 额外成立）。逐条链带事件引用、读侧证据（applied/applied_correction_ids/deny 标记/quieted 标记）、与对照臂差分。注：验收承载腿从「旅程 14 + 记忆 10」变为「记忆 10 + 旅程 4」，原因 §4 行 1（FIX-97 饿死，已登记，非本轮新发现）。
- [x] **错误/无效个性化保留在结果，不筛掉** — HEAD 复跑 5 条照登（ineffective_patch×5，p01×2/p04/p08×2，逐条 probe_day 在案）；首轮 25 条历史产物原样保留不重写。台账判据五类（ineffective_patch/patch_never_applied/memory_not_quieter/harmful_correction_differential/correction_not_read）在 metrics 中全部保留。

Required evidence 对照：base/final SHA ✅（§头部）；targeted tests ✅（7/7 + 邻域由 FIX-67/70 收口轮次覆盖：272/264 绿在案）；integration/simulator evidence ✅（本证全量双跑）；**review receipt ❌ 未检得**——首轮状态 READY_FOR_REVIEW，按验收模型需独立未参与会话审查签收后方可升 DONE。

## 6. V3-FIX-97 确认证据（不新开号）

本证为已登记 OPEN 的 V3-FIX-97（纠正通道以「错位行动」为唯一输入源，诚实 no_action 饿死纠正记忆回路；wt474 分诊待产品拍板）追加纵向面实证：D-08 协议下 20 次旅程纠正机会 16 次 skipped（`diagnosis_matches_truth_or_not_act`——诊断≠真值但无 act 出口）、仅事实充足 persona 4 次 filed 且全部生效（p02/p03/p04 established+changed）。证据路径 `v3-output/WT669-D08-RECHECK/raw/flywheel.jsonl`（event_type=journey_correction 行）+ 本报告 §4。**不改台账行**（避免与并行会话撞文件），由台账 owner 择机并入。

## 7. 诚实声明

1. persona 决策为 seeded 显式模型（沿首轮声明）：纠正倾向全员开启；量化结论是该模型与真实服务行为的联合结果，效应方向可审计、量级不可外推为真人 RCT。
2. judge 解析面由 harness 固定喂入（生产为模型解析面）；UserStateV1 为简化投影（沿首轮声明）。
3. 旅程面「纠正→垫后」机制在产品代码层完好（`2d2336ea..HEAD` 该服务仅增 FIX-51 delivery 契约注记）：p02/p03/p04 的纠正链在 HEAD 真实生效可复现；零事实 persona 的饿死入口在协议层（无 act 出口即无纠正时机），修复属 V3-FIX-97 产品裁决（第二纠正入口形态），非本卡工程范围。
4. worktree 环境项（gen×2、.venv 链接）未入库；合并后建议在 integration HEAD 复跑 `--verify-repro`（gen 面齐备环境）。

## 8. 运行级待验清单（移交）

1. D-08 独立审查回执（首轮与本证合并审查即可：审查者独立执行 `--verify-repro` + 抽任一 persona 链对 raw 行核三段证据）。
2. Q-08 终局 gate 引用口径：引用本目录 dashboard.json（`git_sha=0495e085`）为 HEAD 现状证据；引用 WT397 目录为首轮 base 证据；两者数字差异以本报告 §4 归因表为唯一定论口径。
3. V3-FIX-97 拍板后（第二纠正入口形态落地），D-08 旅程腿数字预期回升——届时按本协议复跑即可，协议参数零改动。
