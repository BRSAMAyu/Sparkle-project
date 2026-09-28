# 最新台账片段

来源 v3/06_agent_fleet/DYNAMIC_ISSUES.md；保留原状态而不合并猜测。

原文件行 57

| V3-FIX-52 | P3 | 行为事实证据无双刃消解：历史失败痕迹把「新类型」卡点系统性带偏（A-08 记忆面反例） | CONTEXT_FACT_RULES 的 recent_failure_count≥3 → skill/difficulty 证据无时间/类型关联消解——p07（plan_drift 段失败留下 ABANDONED 痕迹后，entry 真值段被历史偏差拉向 skill → 全臂 fail；no_memory 臂无痕迹反而 primary 一次解决）：记忆净收益 +0.10 accuracy 的同时存在可证伪的个体伤害案例；「当前卡点类型≠近期失败类型」的场景记忆面是负资产 | wt393 v3-output/WT393-A08-ABLATION/REPORT.md §5-4 + raw/{full,no_memory}.jsonl（p07 对照） | T-friction-fact-decay（组员批：失败痕迹与当前 utterance/spine 证据冲突时的降权或类型关联消解；随 A-03 迭代） | OPEN [wt474分诊:可派发\|friction_diagnosis.py:1290 recent_failure_count≥阈值直给 skill/difficulty 证据、无时间/类型消解仍在场——降权或类型关联消解，随 A-03 迭代] |

原文件行 76

| V3-FIX-97 | P2 | 纠正通道以「错位行动」为唯一输入源：诚实 no_action 饿死纠正记忆回路（wt412 修 V3-FIX-50① 的结构性新发现，不剪照登） | StuckJourney 纠正入口（「不是这个原因」）产品语义是对「被提名的成因」纠正——旅程面诚实化后（B1 exact-tie 不再猜、B3 no_action），journey-first persona 的错位行动消失 → 纠正永不触发 → full/no_experience 臂的纠正记忆回路（A-08 中救回 p02/p04/p05 段的机制）在此时间线被饿死：memory 净收益由 +0.10 accuracy 翻为 −0.10（full 0.45 vs no_memory 0.55）。评估结果模型同时揭示：修前 accuracy 0.65 含平权 tie 字母序偶然蒙对的奖励（5 个 journey 幸运段），诚实化是行为正确但指标回落 | wt412 v3-output/WT412-FRICTION-FIXES/{REPORT.md §2,a08-post-fix/}（gate-only 分解与逐段归因） | T-correction-entry-without-action（组员批：无行动出口是否提供第二纠正入口（如「都不对，其实是…」自由纠正）或把 B3 的平权候选集作为「可能原因清单」低承诺出面供纠正；需产品裁决——候选集出面与 FIX-49 降噪目标存在张力） | OPEN [wt474分诊:待拍板\|产品拍板：无行动出口的第二纠正入口形态（自由纠正 vs 候选集低承诺出面），须与 FIX-49 降噪目标联合权衡] |

原文件行 394

| V3-FIX-507 | P2 | D-05 intervention lifecycle 写路径零生产调用方——record_exposure/record_response/record_outcome_association/associate_pending_outcomes 全仓生产面零调用，读侧三消费方（D-07 洞察卡/M-06 经验投影/North Star intervention 面）全部已接线（wt776 D/E 线 V4 交接文档深挖发现 2026-09-28，基线 main@fd4267ef；505/506 为在航 wt774/wt775 预留段、507 grep 复核空闲——主仓+两兄弟 worktree `V3-FIX-50[5-9]` 0 命中） | 全仓 grep 实录（wt776）：`record_exposure\|record_response\|record_outcome_association\|associate_pending_outcomes` 在 backend/scripts/tests_e2e 的非测试命中仅服务自身（intervention_lifecycle_service.py:146/:317/:380）；唯一外部调用方=backend/tests/{d08_flywheel,q04_personal_redteam,aurora_ablation}/engine.py 三个评测 harness+单测；InterventionEventConsumer（交付管线）不触 lifecycle。读侧接线亲证：evidence_insight_service.py:189、experience_memory_projector.py:131、north_star_wvpl_service 经 D-05 取 intervention 面。后果：friction-pattern 与 interventions-that-helped 两类洞察卡在生产部署中因「无数据不出卡」守卫整面静默缺席、M-06 经验投影恒空；D-08 飞轮闭环证明（46762b31）的 lifecycle 写入系 harness 直接驱动，不能外推为生产流量事实 | wt776 亲证链：全仓 grep（backend/scripts/tests_e2e 四域）+六服务开文件对读+intervention_lifecycle_events 表迁移 d05_20260919 在场零生产写入；v3-output/WT776-DOC-DE/D-line.md §D.2-D-05/§D.4 | T-d05-lifecycle-production-wiring：交付面（InterventionEventConsumer 标记 delivered 处/Aurora decision 执行点）调 record_exposure+record_response；D-02 ledger 增量扫描定时任务调 associate_pending_outcomes；接入后 D-07 两类卡与 M-06 经验投影即有真实数据流。属产品接线（行为面新增）非机械修，需两位 reviewer | FIXED@8e503cd8（wt797 全量接线 2026-09-28：三写面=交付面 mark_delivered/accepted/dismissed/acted→record_exposure/record_response（幂等 dedupe+内容寻址 decision_id）+spine directive 下发 hook（投影+inert 短路+signal:// 归因）+6h beat associate 扫描（37d 幂等）；韧性壳宿主永不中断；红 5→绿 5/5+9/9，触达面 1300+ 全绿，mypy 55=55 零漂移；边界如实=friction unattributed/linkage 留空无桥不伪造；详 v3-output/WT797-F507/notes.md） |

原文件行 407

| V3-FIX-535 | P3 | J-06 HybridJourneySheet+hybrid repo 全仓零生产消费者（孤儿面）：B-01Δ 定域审计顺带发现——journey feature 判 CONTEXTUAL 时核到的未接线面（wt790 发现 2026-09-28；535 号 grep 复核空闲） | FirstActionCard 挂 dashboard 自守门活，但 HybridJourneySheet 与 hybrid repository 全仓无生产 import/挂载（grep 实录）；属「就绪未激活」族 | v3-output/WT790-B01DELTA/delta_report.md F43 节 | 修法方向：V4 接线或显式豁免（同 community_context_boundary/S-02 orphan-by-design 判例——豁免移除条件=J-06 混合旅程面接入） | OPEN（wt790 发现/主会话登记 2026-09-28，门后随 J 线残差处置） |

原文件行 408

| V3-FIX-536 | P3 | J-02 R7 post-skip 落点规格-实现分歧：runbook §3 R7 规定快车道跳过建模后落 /home，而 modeling_chat_screen.dart `_finish()` 在带 post_onboarding_message 的快车道实际落 /chat（wt789 驱动编写发现 2026-09-28；worker 报告原拟 533 号——与 portfolio 全集漂移行撞号，主会话顺延 536 登记；536 号 grep 复核空闲） | 驱动已兼容两态：如实记录 `post_skip_route`，非 home 时走 shell 首页 tab 真实用户路径续 R8——不阻塞门后执行 | v3-output/WT789-J02-DRIVER/notes.md 新发现节 | 修法方向：门后集成会话裁定正解（产品意图问：快车道完成后应落哪）→回填 runbook §3 R7+驱动断言收紧 | OPEN（wt789 发现/主会话登记 2026-09-28，J-02 执行前置小裁决） |

原文件行 411

| V3-FIX-539 | P2 | macOS 桌面注册提交 tap 系统性无效零反馈（O3）：wt792 J-02 实测 6/6 复现——提交 tap 后零响应零日志，只能走 API 注册+UI 登录 fallback（不计入 ≤3min 主张）（wt792 实测发现 2026-09-28；worker 原拟号 538 与 progress_narrative 钉锚行撞号顺延；539 号 grep 复核空闲） | 60 截图+12 进程日志实录；J-01 先例（wt398）同类现象无 FIX 号——系存量非回归 | v3-output/WT792-J02-SIM/REPORT.md O3 节 | 修法方向：macOS 桌面端注册按钮事件链排查（hit-test/焦点/手势层）；J-02 残留工作关联 | FIXED@583e0c8a（wt800 2026-09-28：根因=800x600 桌面几何 Privacy tile 折叠线下盲 tap 静默漏勾（warnIfMissed:false）→consent 守卫拦+唯一反馈 2.5s 瞬态 snackbar——6/6 确定性、真产品缺陷（真实用户同几何同死按钮零恢复）；假设排除表五项（装饰层/stagger 命中/按钮吞/校验/平台层）全排除探针实证；修法=Scrollable.ensureVisible 滚动到因+持久内联错误（复用 authTermsRequired 零新增 l10n）+未勾 tile 低错误色底；红先行两锚点+新 3 测+auth 面 62/62+analyze 净；确证边界=widget 面 800x600 同几何；**真机端到端已实证（wt802 补测批 6/6 纯 UI 注册一次通过零 bounce、tiles pre-submit 全勾、consentInlineError 探针就位未触发、O3 fallback 已弃用删除）**；详 v3-output/WT800-F539/notes.md+WT802-J02-RETEST/REPORT.md） |

原文件行 412

| V3-FIX-540 | P2 | 快车道 skip 后 FirstActionCard 间歇缺失：R 腿 6 跑 4 miss——goal 每次都已落库但首页卡片不浮现，直接卡 J-02 A1a ≤3min UI 秒表的全量达成（4/6 跑 R8 未测得）（wt792 实测发现 2026-09-28；540 号 grep 复核空闲） | 6 跑逐跑记录：PX3/PX5 卡片浮现（且双双 ≤3min 达标 121.7s/114.6s），其余 4 跑 goal 落库但卡片 miss | v3-output/WT792-J02-SIM/REPORT.md+evidence/j02_timings | 修法方向：FirstActionCard 浮现条件/时序排查（疑竞态或刷新触发缺失）；修复后补测即 J-02 残留工作闭环 | FIXED@b87f5f13（wt799 2026-09-28：根因=五失效面叠加——进程级缓存主根因（非 autoDispose FutureProvider 首 fetch 永久缓存 pre-goal 空态）+写链三处不 invalidate+N-4 注册表缺席+dashboard 刷新集缺席+守门吞 staleness；间歇性=落点方差耦合（soft-wall 落板=必 miss，「我的」tab=hit，与 541 分歧同源）；修法五触点最小（autoDispose 核心+三 invalidate+注册+刷新集）；红绿=stash 反向验证无修复 3/3 红（生产症状复现）恢复 3/3 绿+触达面 62+ 绿+analyze 净；真机复测已实证（**wt802 补测批：FirstActionCard 6/6 浮现+A1a 6/6 全 ≤180s（99.7-102.2s）**，对照修前 2/6+4miss）；详 v3-output/WT799-F540/notes.md+WT802-J02-RETEST/REPORT.md） |

原文件行 413

| V3-FIX-541 | P3 | guest/auto-login 落「我的」tab 非 /home：router 语义（/home 重定向）与实测落点不符（wt792 实测发现 2026-09-28，G 腿一致复现；与 FIX-536 R7 落点分歧同族——落地语义待统一裁量；541 号 grep 复核空闲） | G 腿多跑实测一致；**wt802 扩展实证：注册/upgrade 后落点 6/7 直落「我的」tab**（原行只记 guest/auto-login）| v3-output/WT792-J02-SIM/REPORT.md A2 节 | 修法方向：与 FIX-536 合并裁决「登录后落点」产品语义后一处修正 | OPEN（wt792 发现/主会话登记 2026-09-28，与 536 合并裁量） |

原文件行 414

| V3-FIX-542 | P2 | 网关进程守护缺位第二例（FIX-530 家族）+启动 CWD 相对路径：09:29 引擎滚动重启（kill :50051/:8000）时网关 workers 收 context canceled 优雅退出（gateway_day7.log 09:29:09 实录）且无守护不自愈——缺席 ~8 分钟被 wt798 开工核查披露；重启时从错误 CWD 拉起二度失败（minio 主机名/locales 相对路径解析失败，gateway_day7c.log 实录），从 backend/gateway 目录拉起即成（主会话处置+登记 2026-09-28；542 号 grep 复核空闲） | 09:29:09 优雅退出日志+09:36:11 CWD 误启日志+09:37 正确目录 10s 上线三段实录 | /tmp/gateway_day7{,b,c}.log | 修法方向：①守护统一（launchd/supervisord 罩网关+引擎+gRPC 三进程，与 530 的 ops 提案合并）；②启动路径自锚定（可执行文件定位资源/env 或启动脚本显式 cd）；③网关对上游丢失的退出行为若系设计（后端死不服务）则守护必配 | OPEN（ops 家族；530/542 与 launchd 提案合并处置） |

原文件行 415

| V3-FIX-543 | P3 | J-02 register 截图证据失真：wt792 驱动 shot() 取首个 RepaintBoundary=栈底路由——全部 register 时点截图实为登录屏（wt800 修 539 时探针发现 2026-09-28；543 号 grep 复核空闲——542 已被 wt798 占用后本号顺延确认） | J-02 E3 的核心数字系 timing/DB 探针面不受影响；截图面需重采集 | v3-output/WT800-F539/notes.md 附带发现① | 修法方向：驱动 shot() 锚定目标路由 RepaintBoundary；FIX-540 修复后的 J-02 补测一并重采集 | FIXED@697e34bf（wt802 补测批 2026-09-28：shot() v2 锚定=栈顶路由双条件（全视口≥90%+子树含可见文本取 DFS 末者）——v1 纯几何被 persona 屏背景层绕过（首跑同 md5 纯背景实测）迭代修复；02-register=真实注册屏/05-persona=完整画像引导目检实证；18 名族截图重采集） |

原文件行 417

| V3-FIX-545 | P2 | E-08 FALLBACK 计量错挂（wt803 审查 C1 条件显式落账）：7 个 qid（L3-06/08/15/18/21/23/26=wt372 修前 metered-default 同集）多代理流被错挂 `no_generation_model` 标签——harness `_fallback` 判据对新标签失明→自动 issues 8→3 中 1 项系换标签非解决；成本低估（错挂流未计 deep 档）；修后任何自动 dynamic_issues.json 不再出现该缺陷仅存报告散文（wt801 披露+wt803 证实） | raw 程序化复算：7 条带 token 的 no_gen 与修前同 qid 集逐条吻合 | v3-output/WT801-E08FINAL/report.md 披露节；v3-output/WT803-E08REV/receipt.md 可证伪探针节 | 修法方向：harness 补 `no_generation_model`-with-tokens 检出+标签语义二分（真无模型 vs 降级计量）；V4 排期；Q-06 400 样本修后重制另派预算卡 | OPEN（E-08 销账 C1 义务，V4 追踪） |

原文件行 419

| V3-FIX-513 | P3 | 42 feature portfolio 状态双真源词表分裂：`v3/V3_DEFINITION_OF_DONE.md` Gate V3-0 要求「42 个 feature 有唯一 portfolio 状态：CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE」；`v3/00_context/MODULE_PORTFOLIO.md`（初始 pack 导入 0c7fa4c5，自述 desired role）用扩展词表 CORE 15/CONTEXTUAL 15/LABS 5/SECONDARY 3/CORE_OPTIONAL 1/HIDDEN 1/INTERNAL 2 且 RETIRE=0；B-01 交付的 `v3-output/B-01/MODULE_MATRIX.csv`+portfolio.json 才是 DoD 五态口径（RECEIPT 独立复核 CORE 15/CONTEXTUAL 18/LABS 5/HIDDEN 4/RETIRE 0，42/42 EXACT MATCH）（wt779 O/Q 线 V4 交接文档深挖发现 2026-09-28，基线 main@c0306be1；513 号 grep 复核空闲——台账+全仓 v3/ v3-output/ 0 命中，512 同批被本线占用） | ①「唯一 portfolio 状态」文档层不可直接满足——两真源同 feature 值不同（achievement：CSV=CONTEXTUAL vs PORTFOLIO=SECONDARY）；②B-01 矩阵基线 a2d8a10c 距 HEAD 9+ 天未复核——GOV-015/WS6 删除（~3,958 行）、FIX-490 LearningModeScreen 摘除等 reachability 变化未入册，终门按旧矩阵判 V3-0 会过判 | wt779 逐行解析实录（portfolio 42 行词表分布/B-01 CSV 状态列/RECEIPT:14）；v3-output/B-01/{MODULE_MATRIX.csv,REVIEW_RECEIPT.md}；v3/00_context/MODULE_PORTFOLIO.md；v3-output/WT779-DOC-OQ/Q-line.md §Q.2-Q-08/§Q.5 | 修法方向：Q-08 终门前裁决唯一真源（建议 B-01 矩阵为准、MODULE_PORTFOLIO.md 降级 desired-role 参考并加注）+按 HEAD 重跑 B-01 式审计或显式钉矩阵时点注记；词表映射表（SECONDARY/CORE_OPTIONAL/INTERNAL→五态）随裁决产出 | OPEN（裁决+加注已落@ca41d7cf 2026-09-28——B-01 唯一真源、双 desired 源降级参考层；余 B-01Δ 五项审计在航 wt790，落地后刷新 B-01 册再闭） |

原文件行 422

| V3-FIX-498 | P3 | 澄清门快交互文案 _compose_fast_interaction_copy 无预算辅助 LLM 调用串行在门短路 first-content 之前（wt755 2026-09-28，E-08 SLO 首帧卡顺审发现；预分配号 491 grep 复核空闲——台账全文+wt756 notes 复核记录 0 占用，备用 492 未动） | validation_engine.py:775 门判 fail 后 `await self._compose_fast_interaction_copy(...)`（:74-117）经 FAST 车道 llm.chat 生成用户文案，自身无 asyncio.timeout——仅靠 llm_service.py:791 内层 120s 兜底；对照同门族 goal_quality 评估器已有 GOAL_QUALITY_LLM_BUDGET_SECONDS=5.0（goal_quality_evaluator.py:19，TTFT-CFG 先例——探针实测该门单次 LLM 曾 15.7-35.8s 串行在首事件前才加预算）；门短路轮 first-content 最坏被文案调用阻塞至 120s（评估器 ≤5s+文案 ≤120s 串行）；wt372 12 条澄清门轮实录两组形态：双辅助调用快速失败走模板（L2-08 判定+文案+full_text 共 10ms）与 ~3s 迟缓形态（§6 fallback 表） | 代码审读级（validation_engine.py:74-117/:775-780 与 goal_quality_evaluator.py:19/:78 预算对照、llm_service.py:791 内层 120s 亲读；未运行级挂起复现，如实标注） | 修法方向：文案调用加 asyncio.timeout（与门预算同量级 3-5s，超时落 fallback_text 既有兜底）；或门短路先发模板流式 delta 再终帧（一并解 wt372 §7-E 模板零流式）；并入下一个触达 validation_engine 的批次 | FIXED@0b063c7c（wt755 登记 2026-09-28；重编号注：原号 491 系分支基点期预占、主干 491 已属 wt761——轮#254 裁决改 498；wt795 翻格 2026-09-28；wt755 分支 938e845c READY→wt785 预审 APPROVE-for-integration：红绿为真（对 merge-base 68dc7e20 新钉测 FAILED 而交付树绿）+mypy/ruff delta 0+受影响面 1419 过（1 既有 flaky 单跑绿）；集成即纠指 2026-09-28，合并态 208 过+mypy 55 零漂移；receipt v3-output/WT785-WT755REV/receipt.md） |
