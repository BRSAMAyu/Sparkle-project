# V4-B03 · 独立一审 receipt（review_r1）

- 审查会话：**wtB03R**（独立审查，未参与 B03 实现）
- 日期：2026-09-28
- 受审对象：分支 `agent/v4/b03` commit `44938c4c`（base `3c4618cc`），worktree `/Users/brsama/code/GitHub/wtB03`
- 卡：`v4/04_tasks/cards/V4-B03.md`（verification · normal · 独立审查 1 位）
- **总裁决：APPROVE**（零实质 CHALLENGED；2 条轻微备注见 §5，不阻塞）

## 1. 复跑探针（卡验收第 1 条）——PASS

实跑 `python3 v4/evidence/V4-B03/recompute_baselines.py`（仓库根，未带 `--write`，不落盘）：

- **exit 0**，`all_ok=true`，六探针全部 ok：a08_postfix / a08_prefix_historical / fix545_metering_blindspot / e08_slo_2f / q04_dashboard_not_remeasured / utility_freeze
- 复跑 `repo_head=44938c4cd2b4…`；交付内 `test_results.json` 记录的 `repo_head=3c4618cc1d23…` 系实现会话在提交前自测时点，属预期时序差，探针内容逐项一致
- 脚本纯 stdlib（argparse/hashlib/json/sys/pathlib + 仅 `git rev-parse` 子进程），无网络、无引擎启动——零模型调用主张与 run_manifest 一致

## 2. 重点核数字出处（防口径混写）——PASS，未发现混写

负结果 #2（`V3-NEG-A08-POSTFIX-NOMEMORY-BEATS-FULL`）声称「修后 no_memory 11/20=0.55 反超 full 9/20=0.45（utility −9.2 vs 0.0）」。逐一打开源产物核对：

| 口径 | 源产物 | 内部 git_sha | full | no_memory | utility(full/nm) | NEG 行 |
|---|---|---|---|---|---|---|
| **修前** | `v3-output/WT393-A08-ABLATION/summary.json`（2026-09-25T14:29） | b9bc60ae | **13/20=0.65** | 11/20=0.55 | −16.2 / −21.4 | #1 `HISTORICAL_PRE_FIX` |
| **修后** | `v3-output/WT412-FRICTION-FIXES/a08-post-fix/summary.json`（2026-09-25T19:29） | b5e8dedd（=NEG#2 `summary_git_sha`） | **9/20=0.45** | 11/20=0.55 | −9.2 / 0.0 | #2 `OPEN_AS_V4_BASELINE` |

- 两组数字来自**不同产物**、sha256 钉扎互不相同（修前 `d57e9f3a…`，修后 `e5908bc0…`）——**不是同一产物混写**
- 审查会话**独立复数 raw**（不经实现方脚本）：`full` episode_end=9/fail=11、`no_memory` 11/9、`no_experience` 9/11、`fixed_policy` 6/14，与 summary.json、EVAL_RESULTS.md、NEG#2 frozen_numbers 逐数一致；uplift −10pp（0.45−0.55）算术成立
- 防混用机制在案且生效：NEG#1 `reuse_rule` 明示「仅作历史对照锚点；最新基线=修后数字」；`frozen_utility.json baseline_rule.latest_baseline=修后 9/20 与 11/20`、`forbidden=拿 pre-fix 0.65 作最新基线`；CLAIMS_LEDGER 第 8 行「自适应优于不用记忆｜不能引用修前0.65或单一基线」在库
- 修前 full 0.65>no_memory 0.55（WT393）与修后反转（WT412）方向各自行内正确，无跨行串数

## 3. sha256 钉扎抽验——PASS（超额：5 行全部 18 个钉扎逐一实算，非抽 3）

`shasum -a 256` 对 NEG#1–#5 全部 `source_sha256`（16 个唯一源产物）实算比对：**18/18 全部一致**（含 WT393 2、WT412 6、WT404 3、WT801 3、DYNAMIC_ISSUES 1、WT803 receipt 1）。另核对 `paired_baseline.jsonl` 逐行 `scenario_source_sha256=4bf2ae4c…` 与 `v4/06_evaluation/scenarios.jsonl` 实算一致、run_manifest 所引 `EVALUATION_PROTOCOL.md=369ee58e…` 一致。

交叉抽验第三方事实（不经实现方脚本）：WT404 `dashboard.json`（precision 0/10、invalid 10 全 `patch_attribution_cross_scope`、50/120=0.4167、uplift 0.0pp、20 blind pairs、acceptance FAIL、failed_cases_preserved=true）；WT801 `report.md`（4 PASS/2 FAIL、L0 1781ms、L2 total 65.4s 较修前 49.5s 上行、intake ack 104/104 p50 29ms/p95 46ms）；DYNAMIC_ISSUES.md L417 FIX-545 行（7 qid L3-06/08/15/18/21/23/26、issues 8→3 中 1 项换标签、OPEN）——三处与 NEG#3/#4/#5 frozen_numbers 逐数吻合。

## 4. 诚实性——PASS

- **NOT_RUN 全量标注**：`paired_baseline.jsonl` 20/20 行 `execution_status=NOT_RUN`；case 数据与 scenarios.jsonl 原文逐字一致（20 case 全部存在，family/oracle/variant 逐字段比对无差异）；runability 如实两分：V3 臂执行器 IN_REPO（三脚本实存于 `scripts/devtools/`）、V4 C/D 臂 MISSING（依赖 V4-I02/I06/I04/U02/U03/I09/I10 全 PENDING/NOT_STARTED）
- **review_receipt NOT_SIGNED**：`review_receipt.json` verdict=NOT_SIGNED/PENDING_INDEPENDENT_REVIEW，`reviews: []`；tasks.json `status=IN_PROGRESS`、`implementation_state=REVIEW_READY`、`review_status=PENDING_INDEPENDENT_REVIEW`——无 DONE 宣称
- **零模型调用**：attestation（model_calls=0）与脚本实际行为、test_results.json `kind=RECOMPUTE_ONLY_ZERO_MODEL_CALLS`、limitations.md 边界声明一致；E-08 的 145 次历史调用明确记为 V3 在案证据非本卡支出
- **产品码零改动**：`git diff 3c4618cc..44938c4c` 仅触及 `v4/evidence/V4-B03/*`（10 文件）+ `v4/04_tasks/tasks.json`
- `dev_holdout_template.json` 确为 TEMPLATE_ONLY_NOT_GENERATED，无伪造 episode 数据；防泄漏规则（holdout 不给实现 Agent、臂标签不进 AUT、盲评分房）成文（验收第 2 条以「数据未生成故无从泄漏」+ 规则冻结方式满足）
- 卡验收第 3 条：`frozen_utility.json denominator_policy` 0 分母=N/A、未解决/缺失计入不得排除，探针⑥断言在案

## 5. 轻微备注（不阻塞，均非实质）

1. **M1·文档与登记表字段不符**：`diff_or_evidence_only.md` §3 称 `evidence_verdict=RECOMPUTE_PASS_PENDING_REVIEW`，但 tasks.json 实际值为 `NOT_RUN`（且为全库 58 卡唯一在用枚举值）。登记表口径更保守、无夸大，属文档笔误；建议后续以文档改齐为主（如需引入新枚举值应由 tasks.json 单一 owner 决定）。
2. **M2·V3 侧产物标题遗留（非 B03 缺陷，登记防将来误读）**：`v3-output/WT412-FRICTION-FIXES/a08-post-fix/EVAL_RESULTS.md` 标题仍为「WT393 · A-08 …」（程序化生成复用 spec 名）。B03 按路径+sha256+内部 git_sha（b5e8dedd）钉扎，证据链不受影响；后续引用请以目录与 git_sha 区分修前/修后，勿以该标题区分。

## 6. 审查动作留痕

| 动作 | 结果 |
|---|---|
| `python3 v4/evidence/V4-B03/recompute_baselines.py` | exit 0，all_ok=true（六探针） |
| `shasum -a 256`（18 钉扎 + scenarios + protocol） | 全部一致 |
| raw 独立复数（4 臂 episode_end/fail） | 与冻结数逐数一致 |
| WT404 dashboard / WT801 report / DYNAMIC_ISSUES 交叉抽验 | 逐数吻合 |
| `git diff 3c4618cc..44938c4c --name-only` | 仅 v4/ 证据 + tasks.json |
| paired 20 行 vs scenarios.jsonl 逐字段比对 | 无差异，20/20 NOT_RUN |

本 receipt 由 wtB03R 独立产出并 commit 至 `agent/v4/b03`（不 push）。本卡 DONE 仍需按验收模型完成集成 SHA 复验；`review_receipt.json` 的 `reviews[]` 签署按舰队流程另行落账。
