# HUMAN_INBOX — 真实人/外部事实阻塞项登记

> 登记规则（对齐执行包 HUMAN_INBOX 口径）：需要真实用户动作、真实凭据、外部平台事实或产品拍板的事项在此登记；工程侧不被这些事项阻塞。解决后把状态列改为 DONE 并注日期。v3 舰队轮记与台账只追加不改写历史行。
>
> 2026-09-27 由 wt695 日终盘点建议创建（此前仅 WT394/WT395 两份波次级收件箱，无中央登记）。
>
> 2026-09-27 wt783 补 H-009（台账 V3-FIX-511）：回填早于本箱创建、散落各卡的「转 HUMAN_INBOX」真机/真人段承诺；波次级收件箱 `v3-output/WT394-Q02-GOLDEN/HUMAN_INBOX.md` 与 `v3-output/WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md`（G-05 独立视觉箱）自 H-009 起以本表为中央索引锚。

| 编号 | 事项 | 需要什么 | 状态 | 来源 |
|---|---|---|---|---|
| H-001 | 生产库连胜 UTC 日行回填（V3-FIX-293 尾注）：冻结钟双场景造成的历史日行错位需在生产库按量化 SQL 回填修正 | 真实生产库凭据/用户在场执行（SQL 量化已随 FIX-293 行在案） | OPEN | 台账 V3-FIX-293；wt695 审计 |
| H-002 | 云端部署解锁：阿里云 TCC 开关确认 + ZCode 重启（浏览器取凭据卡的前置） | 用户在 TCC 操作并重启 ZCode | OPEN | 轮记 #17x 起 |
| H-003 | Dependabot #111-113 三条依赖升级 PR 处置 | 用户拍板合并/关闭 | OPEN | GitHub PR |
| H-004 | T36 B/D 两项（sparkle-cosmos 仓） | 用户拍板 | OPEN | 接力日志 T36 |
| H-005 | l10n 49 冻结键的最终文案裁决（FIX-182 后续） | 用户/文案拍板 | OPEN | 台账 V3-FIX-182 |
| H-006 | FIX-97 第二纠正入口形态（B 类产品裁决族） | 产品/用户拍板（wt695 B 类 13 条清单在 v3-output/WT695-AUDIT/eod.md） | OPEN | 台账 V3-FIX-97 |
| H-007 | FIX-290 处置 | 用户拍板 | OPEN | 台账 V3-FIX-290 |
| H-008 | V3-FIX-189 部署前盘查：仓外显式 legacy-only=false 的存量部署，stage19 三态门收编后 extractor 会从「关」翻「开」——上线前核生产 env 该 binding 值 | 真实生产 env 核查（.env.prod 盘查） | OPEN | 台账 V3-FIX-189 闭账注记；wt707 风险披露 |
| H-009 | 三端实机/真机段交接承诺汇总回填（V3-FIX-511）：U-09 45 张三端截图矩阵、G-03/G-05 真机截图/FPS 批、U-08 辅助技术走查、B-04 L2-L5 真机批、U-06 simulator 段、WT394 波次收件箱 GJ01-GJ20 采集族、J-02 simulator 实测、X/J/A 线三端实机走查族等「转 HUMAN_INBOX」承诺均早于本箱创建（09-27 wt695 建箱 H-001~008）从未回填——逐项 what/阻塞原因/清单路径/复跑命令/预估成本见下方「H-009 明细」节 | 设备/浏览器权限批：android 真机 + web 双宽 + macOS 桌面、屏幕阅读器（TalkBack/VoiceOver/NVDA）、常驻引擎真 LLM 窗口、远程 HTTPS 端点；成本在采集执行而非代码，V4 初期建议安排一次集中采集批次（多子项可同批搭车） | OPEN | 台账 V3-FIX-511（wt775 登记）；wt783 回填 2026-09-27 |

## H-009 明细（2026-09-27 wt783 回填；引用路径全部在本仓 main@e36fe444 亲证存在，无死指针）

| 子项 | 事项（what） | 阻塞原因（why-blocked） | 清单/证据路径 | 复跑/采集入口 | 预估成本 |
|---|---|---|---|---|---|
| H-009-1 | U-09 三端截图矩阵 45 张采集（9 canonical surfaces×3 平台×viewport）+ DIFF_REPORT 填写 | 无浏览器/AVD/真机权限（wt390/wt676 两轮如实转出不伪造） | `v3-output/U-09/SCREENSHOT_MATRIX.md`（45 行含采集入口+断言点+命名模板）、`v3-output/U-09/DIFF_REPORT.md`（模板）、`v3-output/U-09/REPORT.md` §5/§8（交接清单）、`v3-output/U-09/WT676_CONSISTENCY_DIFF_MATRIX.md` §1 | `python3 scripts/devtools/visual_baseline/visual_baseline.py matrix --build-sha8 $(git rev-parse --short=8 HEAD)`；采集后走 manifest/verify/diff 链（harness 在 `scripts/devtools/visual_baseline/`） | 三端环境就绪后约 0.5–1 天 |
| H-009-2 | G-05 galaxy 真机截图 5 张（U-09 galaxy 行）+ FPS/latency 三端（50/500 节点拖拽/捏合，目标 ≥55fps 交互档；5000 档 large 走 LOD）+ 断网重连验证；G-03 跨端缩放/点击稳定同批 | 无真机/模拟器 + DevTools Performance 人工采集 | `v3-output/WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md`（**G-05 独立视觉箱，本行即其中央索引锚**）、`v3-output/WT395-G05-GALAXY/REPORT.md`、`v3-output/WT395-G05-GALAXY/raw_frame_budget.md`（headless 段 p50/p95）；G-03 残差见 `v3-output/WT775-DOC-UPSG/G-line.md` §G 残差 6 | DevTools Performance 页逐项采集；headless 段可复跑 `flutter test test/features/galaxy/performance/g05_galaxy_frame_budget_test.dart` | 约 2–3 小时 |
| H-009-3 | U-08 辅助技术实机走查：TalkBack/VoiceOver/NVDA 过 GJ01/GJ03/GJ08 + WCAG AA 抽样取色 + 焦点序（traversal order）全表系统性走查 | 无设备/浏览器（wt365 以 headless 语义树断言替代并如实标注） | `v3-output/WT365-U08-A11Y/REPORT.md` §五；补跑面 `v3/04_ux/ACCESSIBILITY.md` 全清单 | 按 ACCESSIBILITY.md 清单人工走查并存证入 v3-output | 约 0.5 天 |
| H-009-4 | B-04 L2–L5 真机批走查（§6 表 7 项中 1–6 为真环境项：真机 45 行矩阵复核、goal 详情真后端采集、chat 引用块真数据复核、galaxy 节点标签交互级审查、macOS 真桌面文字级权威份、探针逻辑尺寸参数化 harness 增量） | 无真机/macOS 桌面 app/真后端活栈（flutter_tester macos 批有 ENV-1 字形伪影，文字审查权威=真机批） | `v3-output/B-04/REPORT.md` §3/§6、`v3-output/B-04/VISUAL_ISSUES_LEDGER.md`（B-04-ENV-1/ENV-2、B-04-L-06）、headless 批已在库：`v3-output/B-04/screenshots/` + `v3-output/B-04/manifests/` | 采集入口按 `scripts/devtools/visual_baseline/states.py`；goal 行按 `/plans` 入口（REPORT §3-1 注记，矩阵清单不改） | 0.5–1 天（与 H-009-1 同批搭车） |
| H-009-5 | U-06 simulator/真机 face-check：cognitive 三面分阶等待升格观感（500ms/2600ms 节奏推进）与错误 toast 人话复核 | 需常驻引擎+真 LLM 窗口+模拟器（wt358/wt673 两轮 simulator 证据 DEFERRED，widget 渲染树行为测试为行为证据） | `v3-output/WT358-U06-STATES/REPORT.md`（DEFERRED 注记）、`v3-output/WT673-U06-STATES/REPORT.md`（残余①②与 face-check 清单） | 起真实栈后 simulator 三面走查 | 约 1–2 小时 |
| H-009-6 | WT394 Q-02 波次收件箱全量收编：A 视频/截图采集 17 项（GJ01–GJ20，三端录屏+断言点）、B 真机/真实浏览器交互段 4 项（含 U-09 矩阵引用+iOS 滑返+10.0.2.2 宿主别名+触觉音频降级确认）、C WS 主路径定界 2 项、D 远程 HTTPS 段 2 项 | 无 AVD/真机/浏览器自动化权限、无远程 HTTPS 部署（GJ19 RESTRICTED）；C 段部分依赖的 V3-FIX-53/54 已实质收口可采 | `v3-output/WT394-Q02-GOLDEN/HUMAN_INBOX.md`（波次级原件，本行补中央索引）；API 级 trace 已在 `v3-output/WT394-Q02-GOLDEN/raw/*.jsonl` | 远程段解除后：`python scripts/devtools/q02_run_golden_journeys.py --env remote --remote-url https://<host>`；其余逐项人工采集 | 最大块：约 1–2 天 |
| H-009-7 | J-02 销账前置：fresh install ≤3min 到 Action 秒表核 + 三端实机走查 + 截图视觉核（卡面 Required evidence，审查方无权豁免；或由 fleet owner 显式裁决豁免并转 HUMAN_INBOX 首飞清单，豁免须记账） | 无设备/simulator | `v3-output/WT772-J02-REVIEW/receipt.md` 前置表第 1 项；执行清单 `v3/01_product/FIRST_3_MINUTES.md`「Automated simulator acceptance」 | 按 FIRST_3_MINUTES 清单在 integration HEAD 执行并存证（截图+秒表）入 v3-output | 约 1 小时 |
| H-009-8 | X 线三端实机走查族：X-02 实机 5-Persona 观感、X-04 三端实机、GJ07 等全 X 线实机走查（headless+widget 口径已交付，X-10 journey 族为服务层重放非真机） | 无设备 | `v3-output/WT770-DOC-MX/X-line.md` §3 X-02 行 + §4 残差 5 | 与 H-009-1/H-009-6 同批采集 | 搭车 +0.5 天 |
| H-009-9 | J 线三端实机残差：GJ01 三端视觉与会话一致性、真模型（非脚本 LLM）5-Persona 实机首帧差异化观感、503 诚实错误实机重试体验（commit 原文三项）、J-04 三端实机+persona 观感、J-06 实机端到端、J-07 真实用户回访行为学验证 | 设备 + 独立真模型运行 + 真实用户（行为学为长期面） | `v3-output/WT774-DOC-AJ/J-line.md`（GJ01/J-04/J-06/J-07 残差段） | 设备项随 H-009-1 同批；行为学需真实用户另行安排 | 搭车 0.5 天 + 行为学另行 |
| H-009-10 | 零散单点验证项：WT355-H4 真机/模拟器「我还有什么任务」chip 本地化文案显示验证、U-05 运行级 Persona A/B 观感与 5 秒测试（wt324 模拟器证据之外的 HUMAN_INBOX 段）、P 线低刺激模式实机截图走查 | 设备/模拟器 | `v3-output/WT355-HUNT-R2/REPORT.md`（红测要求节）、`v3-output/WT686-U05/REPORT.md` §5、`v3-output/WT774-DOC-AJ/A-line.md` 残差② | 随 H-009-1 同批 | 合计 <2 小时 |

> 关联注记：①`v3-output/WT400-FIX53-REVERIFY/summary.json` 与 `v3-output/WT773-O05/drill/gj03_summary.json` 的 visual_evidence 字段均引用 U-09 矩阵转出——同为 H-009-1 证据锚；②`v3-output/WT576-VERIFY/verdicts.md` F2（user_streak_days UTC 迁移口径需 HUMAN_INBOX 或架构确认）与 H-001 同源，不单列；③B-04 §6 第 7 项（独立 review receipt）属工程验收非真机段，不在本组。
