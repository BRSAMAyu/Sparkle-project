# WT783-HUMANINBOX — FIX-511 真机段承诺回填中央收件箱 · 实录

- **worker**: wt783 ｜ **日期**: 2026-09-27 ｜ **分支**: `agent/node-b/wt783/huminbox`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt783-huminbox`，基线 main@e36fe444）
- **任务**: 执行 V3-FIX-511 修法方向——把散落各卡的「转 HUMAN_INBOX」真机/真人段承诺回填进中央收件箱 `v3/08_operations/HUMAN_INBOX.md`
- **硬约束遵守**: 未改 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（台账收口归主会话）；未 push；未碰运行栈/`/tmp/northstar_ns001_real_drive_state.json`/ns001 数据。纯文档卡，未跑测试（DoD=路径亲证+格式沿用+本实录）。
- **交付**: `v3/08_operations/HUMAN_INBOX.md` 纯追加 +20 行（H-009 汇总行 + 「H-009 明细」节 10 子项表 + 关联注记），历史行 H-001~008 零改写；本报告。

## 1. 路径核验实录（全部亲证，零死指针）

核验环境 = worktree 基线 main@e36fe444。命令与结果逐条实录：

### 1.1 FIX-511 已知五项

| # | 路径 | 命令 | 结果 |
|---|---|---|---|
| 1 | `v3-output/U-09/SCREENSHOT_MATRIX.md` | `test -f` | EXISTS（45 行矩阵，含采集入口+断言点+命名模板；头部 `<BUILD_SHA8>` 为设计占位符，非死链） |
| 2 | `v3-output/U-09/DIFF_REPORT.md` | `ls v3-output/U-09/` | EXISTS（diff 模板） |
| 3 | `v3-output/U-09/REPORT.md` §5/§8 | `test -f` + 读 §5/§8 | EXISTS（§5 截图矩阵交接清单、§8 DEFERRED/移交 明列「HUMAN_INBOX+主会话」） |
| 4 | `scripts/devtools/visual_baseline/visual_baseline.py` + `matrix.py` | `test -f` | 均 EXISTS（复跑命令可执行：`python3 scripts/devtools/visual_baseline/visual_baseline.py matrix --build-sha8 $(git rev-parse --short=8 HEAD)`） |
| 5 | `v3-output/WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md` | `test -f` | EXISTS（G-05 独立视觉箱：5 张截图矩阵表 + FPS 口径 + headless 已覆盖清单） |
| 6 | `v3-output/WT365-U08-A11Y/REPORT.md`（U-08） | `ls` + 读 §五 | EXISTS（§五遗留 DEFERRED：TalkBack/VoiceOver/NVDA 走查 GJ01/GJ03/GJ08 + WCAG AA 抽样取色 + 焦点序全表走查） |
| 7 | `v3/04_ux/ACCESSIBILITY.md`（U-08 补跑面） | `test -f` | EXISTS |
| 8 | `v3-output/B-04/`（REPORT.md、VISUAL_ISSUES_LEDGER.md、screenshots/、manifests/） | `ls` | 全 EXISTS（REPORT §6 表 7 项待真环境项；ENV-1/ENV-2 在案；screenshots/manifests 为 headless 批 android/macos 段） |
| 9 | `v3-output/WT358-U06-STATES/REPORT.md` + `v3-output/WT673-U06-STATES/REPORT.md`（U-06） | `ls` + grep simulator | 均 EXISTS（wt358: simulator evidence DEFERRED；wt673: 残余清单第 1 项 simulator/真机 face-check 需常驻引擎+真 LLM） |

### 1.2 补漏扫描发现的回填项

| # | 路径 | 命令 | 结果 |
|---|---|---|---|
| 10 | `v3-output/WT394-Q02-GOLDEN/HUMAN_INBOX.md` | `head -30` + 读全文 | EXISTS（波次级收件箱：A 视频/截图采集 17 项 GJ01–GJ20、B 真机/浏览器交互段 4 项、C WS 定界 2 项、D 远程 HTTPS 段 2 项） |
| 11 | `scripts/devtools/q02_run_golden_journeys.py` | `test -f` | EXISTS（WT394 D 段复跑命令真实可执行） |
| 12 | `v3-output/WT772-J02-REVIEW/receipt.md` | grep 上下文 | EXISTS（J-02 销账前置第 1 项：fresh install ≤3min+三端实机+截图视觉核） |
| 13 | `v3/01_product/FIRST_3_MINUTES.md` | `find v3 -iname '*FIRST_3*'` | EXISTS（J-02 执行清单「Automated simulator acceptance」） |
| 14 | `v3-output/WT770-DOC-MX/X-line.md` | grep 上下文 | EXISTS（X-02 行「实机 5-Persona 观感转 HUMAN_INBOX」+ §4 残差 5 全 X 线三端实机） |
| 15 | `v3-output/WT774-DOC-AJ/J-line.md` | grep 上下文 | EXISTS（GJ01 残差三项 commit 原文明列 + J-04/J-06/J-07 实机转出） |
| 16 | `v3-output/WT774-DOC-AJ/A-line.md` | grep 上下文 | EXISTS（残差②低刺激实机截图走查转 HUMAN_INBOX） |
| 17 | `v3-output/WT775-DOC-UPSG/G-line.md` | grep 上下文 | EXISTS（§G 残差 6：G-03/G-05 真机段清单就绪未采集） |
| 18 | `v3-output/WT355-HUNT-R2/REPORT.md` | grep 上下文 | EXISTS（红测要求节：真机/模拟器 chip 本地化验证放 HUMAN_INBOX） |
| 19 | `v3-output/WT686-U05/REPORT.md` | 读 §5 | EXISTS（§5：运行级 A/B 与 5 秒测试属既有 wt324 证据 + HUMAN_INBOX 段） |
| 20 | `v3/04_ux/MULTIPLATFORM.md` | `test -f` | EXISTS（允许差异登记表，多子项引用的口径真源） |

### 1.3 死指针检查结论

**零死指针**。上述 20 项路径全部在本仓亲证存在（`test -f`/`ls`/读内容三选一以上实录）。未出现 FIX-502/509 族断链。唯一注意点：`SCREENSHOT_MATRIX.md` 头部 `<BUILD_SHA8>` 是设计上的占位符（用 `git rev-parse --short=8 HEAD` 现取），已在 H-009 明细复跑命令中体现，不是断链。

## 2. 补漏扫描（`grep -rl 'HUMAN_INBOX' v3-output/`）

命中 26 个文件，逐个甄别结论：

| 文件 | 甄别 |
|---|---|
| `v3-output/U-09/REPORT.md`、`WT676_CONSISTENCY_DIFF_MATRIX.md`、`WT400-FIX53-REVERIFY/summary.json`、`WT773-O05/drill/gj03_summary.json` | 同指 U-09 45 张矩阵转出 → H-009-1（后两者为 evidence 字段证据锚，见关联注记） |
| `v3-output/WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md`、`REPORT.md`、`raw_frame_budget.md` | G-05 独立视觉箱 → H-009-2（中央索引锚已建立） |
| `v3-output/WT394-Q02-GOLDEN/HUMAN_INBOX.md`、`REPORT.md`、`raw/GJ12_local.jsonl`、`raw/GJ16_local.jsonl`、`raw/GJ18_local.jsonl`、`raw/GJ19_local.jsonl`、`summary.json` | WT394 波次收件箱及其 raw trace 数据 → H-009-6（**最大漏项**：GJ01–GJ20 采集族从未入中央箱） |
| `v3-output/B-04/VISUAL_ISSUES_LEDGER.md` | B-04 真机批权威份 → H-009-4 |
| `v3-output/WT355-HUNT-R2/REPORT.md` | H4 chip 本地化真机验证 → H-009-10 |
| `v3-output/WT576-VERIFY/verdicts.md` | F2 UTC 迁移口径确认 → 与 H-001 同源，不单列（关联注记②） |
| `v3-output/WT686-U05/REPORT.md` | U-05 运行级观感段 → H-009-10 |
| `v3-output/WT695-AUDIT/eod.md` | wt695 建箱审计本身（C 类 0 条结论、FIX-293 建议→已成 H-001），无新项 |
| `v3-output/WT770-DOC-MX/X-line.md` | X 线三端实机族 → H-009-8 |
| `v3-output/WT772-J02-REVIEW/receipt.md` | J-02 销账前置 → H-009-7 |
| `v3-output/WT774-DOC-AJ/A-line.md`、`J-line.md` | P 线低刺激实机 + J 线实机残差族 → H-009-9/H-009-10 |
| `v3-output/WT775-DOC-UPSG/U-line.md`、`G-line.md`、`P-line.md` | wt775 深挖文档（FIX-511 登记原件 + G 线交叉登记），本身是本卡输入非回填对象 |

**结论**：已知五项之外新增回填 5 组——WT394 波次收件箱全量（H-009-6，最大块）、J-02 销账前置（H-009-7）、X 线实机族（H-009-8）、J 线实机残差族（H-009-9）、零散单点（WT355-H4/WT686 U-05/P 线低刺激，H-009-10）；另 G-03 真机段并入 H-009-2。

## 3. 修改 diff 摘要

```
v3/08_operations/HUMAN_INBOX.md | 20 ++++++++++++++++++++
1 file changed, 20 insertions(+)
```

- 头部 blockquote 追加 1 条 wt783 注记（波次级收件箱与 G-05 独立视觉箱的中央索引锚关系）。
- 表格追加 H-009 汇总行（严格沿用 `| 编号 | 事项 | 需要什么 | 状态 | 来源 |` 五列格式与既有行文风）。
- 新增「H-009 明细」节：10 子项表（子项 | what | why-blocked | 清单/证据路径 | 复跑/采集入口 | 预估成本）+ 关联注记 3 条。
- H-001~008 历史行零改写（只追加原则）。
- `v3/08_operations/` 无 README 索引文件（ls 亲证：仅 DEPLOYMENT/HUMAN_INBOX/OBSERVABILITY/OPS_SURFACE/RELEASE_GATES/RUNBOOK_DEMO/SECURITY_PRIVACY），步骤 6 无操作。
- 新增本报告目录 `v3-output/WT783-HUMANINBOX/`（notes.md）。

## 4. 新缺陷核验（V3-FIX-533 号段结论：不占用）

- wt365 U-08 REPORT §五-2 登记的 `SparkleButton` Semantics 双播报缺陷：grep 台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` 零命中，但 `mobile/lib/core/design/components/atoms/sparkle_button_v2.dart:264-269` 已由 **WT373 缺陷扫雷#2** 以 `ExcludeSemantics` 修复（代码注释互引 wt365 探针 G「重试\n重试」）——**已修，不构成新发现**，wt365 报告该条为陈旧残差。
- 其余扫描未发现需占新号的未登记缺陷。`V3-FIX-533` grep 全仓零命中、保持空闲。

## 5. 遗留与移交（主会话参考，本卡不动）

1. `v3/V3-COMPLETE-STATUS-FOR-V4.md:108`「等用户解锁：H-001~008」一行在 H-009 回填后已过时——V4 文档归 wt77x/主会话维护，建议其下轮刷新为 H-001~009（本卡不越界改）。
2. `v3-output/WT774-DOC-AJ/A-line.md` 残差①（FIX-48 待产品拍板）为 B 类产品裁决、台账已在案 OPEN，非真机段，未入 H-009；主会话若认为该族应入中央箱可参照 H-006 先例补行。
3. H-009 明细表子项状态随采集进度由后续会话在明细表内注记 DONE，汇总行保持 OPEN 至全组闭环。
