# WT347-VISION-GAP · 愿景 vs 实现现状差距审计（为排产提供卡池之外的活源）

> LIGHT 只读审计卡。基线 = `main@b280d38a`（2026-09-25）。权威愿景 = `/Users/brsama/code/GitHub/Sparkle-V3/Sparkle_V3_Agent_Execution_Pack_20260919/`（NORTH_STAR / MASTER_DESIGN / V3_DEFINITION_OF_DONE / 01_product / 02_core_systems，只读非 git）。实现证据 = `Sparkle-project` 代码+测试路径，**文档自述不计入**。
> 运行级证据引用两张既有实测报告（v3-output/NORTHSTAR-LOOP2、NORTHSTAR-LOOP3，2026-09-22 真栈真模型），本卡未起栈。零产品代码改动。
> 证据检索词与命中均在文中给出路径，可复核；「未命中」= 在 `backend/app`、`mobile/lib`、`scripts`、`docs` 用列明关键词 grep 为 0 命中。

## 1. 硬性承诺清单（参赛交付必须为真）

从 DoD 11 个 Gate + NORTH_STAR + 01_product 提取，按主题归组：

- **T1 Truth/诚实红线（V3-0）**：42 feature 唯一 portfolio 状态（CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE）、无用户可达半成品入口；统计数字有 lineage、mock/seed 隔离不进真实分析；模型/OCR/ASR/TTS 能力由 runtime probe 得出；不公开 CoT；不用假统计冒充真实结果。
- **T2 First 3 Minutes（V3-1）**：「把卡住变成下一步」承诺屏 → 单输入 Goal Capture → First Understanding 四条目（确认目标/不确定点/建议一步/为什么）→ Action Card（产出/时间/证据/人机分工）；≤3 分钟到首个 proposal；体验示例与「开始我的目标」严格区分、demo persona 不冒充用户历史。
- **T3 Stuck→Useful Action（V3-2）**：结构化 proposal（desired_outcome/smallest_useful_step/why_now/completion_evidence/execution_mode）；20 个代表性 friction scenario ≥18 与真实原因一致；不靠无限缩小任务制造完成感；高风险/信息不足 clarify/abstain。
- **T4 Human–AI 分工（V3-3）**：分配离线评测 ≥90%；能力型步骤不代做；高风险不可逆 autonomous execution = 0；hybrid handoff pending/awaiting_user/resumed/cancelled 真实可恢复。
- **T5 个性化（V3-4）**：memory 有效使用 precision ≥95%；expired/revoked/wrong-user/wrong-scope 使用 = 0；over-personalization ≤5%；纠正改变后续决策（无关场景不改变）；删除后 retrieval/cache/context/in-flight 均不复用；paired uplift 目标 +15pp（不达标报告真值）。
- **T6 数据飞轮（V3-5/V3-10）**：每个 intervention 连通 context→decision→execution→outcome→evidence；understanding 五维（coverage/correctness/scope_precision/freshness/utility）不合成神秘百分比；**North Star = WVPL，必须可报告**（分母/loops/类型/分工/proactive 占比）。
- **T7 Agent Runtime（V3-6）**：100 run ≥99 terminal/awaiting；false success=0、cross-user=0、duplicate side effect=0；关 app/WS 重连/worker 重启可恢复；tool call 有 run_id/permission/idempotency/receipt/latency/cost。
- **T8 体验质量（V3-7）**：12 类状态（loading/empty/error/offline/awaiting/partial…）完整；Android/Web/macOS golden journey 通过；视觉回归有基线截图与 diff。
- **T9 性能与成本（V3-8）**：L0 ≤500ms / L1 p50 ≤2.5s / L2 最终 p95 ≤15s / L3 ACK ≤1s；无 UI 因隐藏模型调用冻结 >2s；每 tier 有 token/cost 账本；达不到必须重定真实 SLO，禁止隐藏等待。
- **T10 商业工程（V3-9）**：HTTPS 远程可部署；entitlement 与 flame 解耦；quota/成本/kill switch/rollback 可观测；导出/删除有效；backup/restore 演练；一键 smoke + rollback runbook。
- **T11 产品形态（NORTH_STAR §7）**：五 Tab = 首页 Today Cockpit / **任务 Goals & Actions** / 对话 Aurora / 星图 Outcome Graph / 我的 Reflection & Control；42 feature 降为按需能力。
- **T12 演示金路径（DEMO_GOLDEN_PATH 12 步）**：goal 输入 → Today action → 「只有 20 分钟」→ TIME+ENTRY 识别 → transient scope → proposal 缩步 → Hybrid 协作 → 真实图表 artifact 入 Goal + Galaxy 新关系 → 次 session 少问一次 → why this → 纠正 → re-decision。**这一条跑不通，其它 feature 不能证明愿景**（原文）。

## 2. 差距表

等级：无=零证据｜弱=有骨架无闭环/无真实证据｜半=机制在但报告面或运行级缺｜全=机制+测试双证。
槽型：A=产品体验、C=真缺陷、E=评测/证据、O=运维/外部、D=文档/治理。HEAVY/LIGHT 按舰队内存纪律。

| # | 承诺 | 现状（证据路径） | 等级 | 补齐建议（一卡粒度） | 槽型 |
|---|---|---|---|---|---|
| G1 | T2 首屏承诺+Goal Capture+First Understanding | mobile 无「把卡住变成下一步」（grep 0 命中）；onboarding 仍是旧 feature 导览（`mobile/lib/features/onboarding/presentation/screens/interactive_onboarding_screen.dart`：galaxy/personalization/reminders 介绍页），无单输入 goal→首个 action 直达链 | **无** | 新建 Promise 屏（两 CTA）+Goal 单输入+四条目 First Understanding，接既有 `/goals` + friction_diagnosis 链；旧导览降级为可选 | A/HEAVY |
| G2 | T12/T8 GJ20 竞赛演示全链真栈跑通 | golden journeys 只有冻结清单+参考桩：`backend/tests/v3_scenario_eval/harnesses.py:687-724`（GJ01..GJ20，surrogate 自述「真 UI/真栈全由 grading 判 unsupported」）；LOOP3 实测过 7 项定向非全链 | **弱** | GJ20 冷启动真栈演练卡：起栈+真模型走 12 步，逐步截图/JSON 存档，断点立 C 卡 | E+O/HEAVY |
| G3 | T3 20 friction scenario ≥18 真实一致 | 场景库 260 条已枚举+判卷门在（`backend/tests/v3_scenario_eval/test_v3_scenario_eval_gate.py:85`），但 harness 是确定性参考桩；friction 分类器本身强（`backend/app/aurora/friction_diagnosis.py` 15 类+One Best Question，1616 行） | **弱** | 取 20 代表场景跑真模型 batch（有 MiniMax key），产出 ≥18/20 判定报告；缺口场景立修复卡 | E/HEAVY |
| G4 | T9 延迟 SLO | 分层预算表在 surrogate 里（`harnesses.py:598-604`）；LOOP3 实测完整回合 51–87s、TTFT ~30s 簇（NORTHSTAR-LOOP3 §1.7），对照 L2 最终 p95 ≤15s 目标差 3–6 倍，且无重定 SLO 记录 | **弱** | 两张卡：(a) 诚实重定 SLO 并记录 ADR；(b) 演示链 fast-lane（澄清快交互已 19.4s→再压） | C+E/HEAVY |
| G5 | T10 HTTPS 远程部署 | `deploy/`+`k8s/`+`nginx/` 配置在仓；阿里云 ECS 已购但**卡凭据**（v3/HANDOVER-20260925.md §2.7，AskUserQuestion 多次未答） | **无**（外部阻塞） | 用户给凭据后一张部署卡（IP 直连先通，ICP 后补）；无凭据则持续 BLOCKED 证据 | O/EXTERNAL |
| G6 | T2 体验示例隔离形态 | 半成品形态在：后端 DEMO_MODE mock 响应（`backend/app/services/llm_service.py:127-137`）+移动端 DemoDataService（`mobile/lib/main.dart:126-129` dart-define/guest pref；banner `app_localizations_zh.dart:28479`）+`backend/app/services/guest_seed_service.py`；但非愿景的「顶部持续标识示例体验+一键用我的目标开始+demo 不写真实画像」三件套，第三件无测试 | **半** | Example Mode 卡：示例/真实双态切换+常驻标识+「demo seed 零写入真实画像」回归测试 | A+T/MEDIUM |
| G7 | T6 WVPL 可报告 | 事实口径+golden 冻结+每日 worker 全在：`backend/app/core/north_star_wvpl.py`、`backend/tests/golden/test_north_star_wvpl_golden.py`（sha256 钉死）、`backend/app/workers/cost_wvpl_worker.py`；但 **api/v1 全目录 grep wvpl=0 命中**——分母/loops/分工分布无法被评审查询 | **半** | 一张卡：只读端点（如 `GET /admin/wvpl-fact`）吐 canonical JSON+契约测试，复用 frozen schema | C/LIGHT |
| G8 | T5 删除后 in-flight/cache 不复用（GJ09） | 删除 API+status 机在（`backend/app/services/memory_retrieval_prefilter.py:440,469` M-01 revoked/expired；36 个 test_memory* 文件）；但「in-flight continuation 不复用」无专项测试（grep no_reuse/not_reused 0 命中） | **弱** | GJ09 定向测试链：删除→进行中 chat 回合→断言旧信息不再出现于续写/context pack | C/LIGHT |
| G9 | T8 三平台 golden journey 真渲染 | 六平台目录在（`mobile/{android,ios,web,macos,windows,linux}/`）；视觉基线有一角（`mobile/test/goldens/*.png`）；但 GJ 真渲染判 unsupported（同 G2 证据），Linux 像素差曾被判「错标准门」（HANDOVER §2.4） | **弱** | Android 真机/模拟器 GJ03+GJ07 定向跑分+截图存档；Web/macOS 至少 smoke 一条；容差规则成文 | A/HEAVY(设备) |
| G10 | T1 42 feature portfolio 状态 | grep `portfolio_status\|FEATURE_PORTFOLIO\|CORE.*CONTEXTUAL.*LABS` 于 backend/mobile/scripts/docs = 0 命中；半成品入口清查无登记 | **无** | 治理卡：建 feature portfolio 清单（CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE 五态）+mobile 入口对照+守卫脚本（rule_guard 可挂） | D/MEDIUM |
| G11 | T5 precision ≥95% + uplift +15pp | 评测门在：`backend/tests/memory_eval/gate.py:31`（VALID_USE_PRECISION_MIN=0.95，uplift 目标 +15pp 注释）+`real_model_stability_report.json`；但达标与否取决于真模型 run，评审可见的报告未成文 | **半** | 出一页 eval 报告（真值不达标照写，符合 DoD「报告真实结果而非改口径」） | E/LIGHT-HEAVY |
| G12 | T4 分配 ≥90% + 高风险 autonomous=0 | `backend/tests/unit/test_action_allocation_eval.py:69-74`（accuracy≥0.90、high-risk auto-agent=0、学习类 agent=0）+`backend/app/services/action_allocation_policy.py`+`backend/app/aurora/proactive/autoexec.py`（allowlist 封闭词表+fail-closed+TOCTOU 二次校验） | **全** | 无需补卡；评审材料引用即可 | — |
| G13 | T4 hybrid handoff 可恢复 | `backend/tests/unit/test_hybrid_run_steps.py`（12 tests）+`test_hybrid_run_steps_api.py`（app kill/reopen、step_replay、run.user_resumed 事件、cold reopen 派生 awaiting） | **全** | 无需补卡 | — |
| G14 | T7 run 状态机/幂等/false success | `backend/app/core/run_state_machine.py`（QUEUED→…→FAILED/CANCELLED/TIMED_OUT/PARTIAL/UNKNOWN_OUTCOME）+`failure_semantics.py`+`idempotency.py`+`backend/app/api/v1/runs.py`+chaos 目录；100-run 批量统计未跑（同 G2 surrogate 问题） | **全(机制)/半(统计)** | 并入 G2 演练卡顺带产出 100-run 记录 | — |
| G15 | T6 understanding 五维 | `backend/app/core/understanding_dimensions.py`（467 行：五维公式冻结+缺数据=unknown+不合成百分比）+`backend/tests/golden/understanding_dimensions_golden.json`+校准服务；mobile 端消费档位的证据弱 | **全(后端)/半(UI)** | 小卡：核对 mobile 理解度展示走 summarize 档位而非百分比 | A/LIGHT |
| G16 | T6 intervention→outcome 闭环 | `backend/app/core/outcome_ledger.py`+`backend/app/core/event_registry.py:89,251`（OUTCOME 事实+D-02 关联窗口）+`backend/app/services/outcome_capture_service.py`+test_outcome_ledger_contract/promotion_governor | **全** | 无需补卡 | — |
| G17 | T11 五 Tab：任务=Goals & Actions | 实际五 tab = Home/Galaxy/Chat/**Community**/Profile（`mobile/lib/app/routes.dart:228-382`）；goal 无一级入口（`mobile/lib/features/goal/presentation/screens/`仅 wizard+detail） | **半（形态偏离）** | 决策卡：改 tab 或改愿景口径（Community 是强功能，二选一要用户拍板）；审计不动代码 | 治理/LIGHT |
| G18 | T10 entitlement 解耦/kiquota/kill switch/导出 | `backend/app/core/entitlement.py`+`test_o04_entitlement_flame_decouple.py`（四层+迁移重放）；`kill_switch.py`+readiness tests；`data_export.py`+memory_export/episodic governance tests | **全** | 无需补卡 | — |
| G19 | T10 backup/restore 演练+smoke | `docs/ops/disaster_recovery_runbook.md`+`scripts/journey_smoke.sh`（unit+integration 级，非真栈）+`scripts/run_e2e_smoke.sh`；演练成功记录未见 | **半** | 并入 G5 部署卡：部署后跑一次 restore 演练+journey smoke 真栈存档 | O/MEDIUM |
| G20 | T1 runtime probe 能力 | llm_router 有健康熔断（`backend/app/core/llm_router.py:235-294` healthy/probation/unhealthy），但 OCR/ASR/TTS provider 仍读 settings 配置（`llm_router.py:545-546`），无主动 probe | **弱** | 小卡：启动期 capability probe（列可用模型/OCR 连通）+状态端点；或降级为文档声明「health-based」 | C/LIGHT |

## 3. Top 10 派发候选（按 评审价值 × 补齐成本 排序）

1. **G1 First 3 Minutes 重构**（A/HEAVY）——评委第一眼就是它，现状与愿景相反；组件（friction/proposal/cockpit）全在，缺的是这层壳，投入产出比最高。
2. **G2 GJ20 演示全链真栈演练**（E+O/HEAVY）——直接回答「说得出来但跑不通」；演练断点自动产出 C 卡活源（LOOP3 一轮就产出 2 个真缺陷+3 观察，本轮修了 NBP-3b 与 CP-01）。
3. **G4 延迟 SLO 处置**（C+E/HEAVY）——TTFT ~30s 是演示当场翻车最大单点；先诚实重定 SLO（一行 ADR），再 fast-lane。**不处理则任何演示脚本都在赌**。
4. **G3 真模型 scenario eval（20 场景 ≥18）**（E/HEAVY）——DoD 硬数字，260 场景+判卷门已就绪，只差真模型 run 与报告。
5. **G5 云端 HTTPS 部署**（O/EXTERNAL）——评委要远程可访问；唯一阻塞是用户凭据，应持续升格提醒而非等唤醒。
6. **G6 Example Mode 三件套**（A+T/MEDIUM）——V3-1 诚实红线（demo 不冒充用户历史）；现有 DemoMode 是地基，补形态与隔离测试。
7. **G7 WVPL 暴露端点**（C/LIGHT）——北极星必须可答；frozen schema 直接复用，半天级。
8. **G8 删除后 in-flight 不复用测试链**（C/LIGHT）——隐私红线「=0」承诺的最后一公里。
9. **G9 三平台 golden journey 证据**（A/HEAVY·设备）——V3-7 明确要求；Android 优先，无设备则按纪律出阻塞证据。
10. **G10 42 feature portfolio 清单**（D/MEDIUM）——Truth gate 第一条；文档+守卫卡，防止评委随手点进半成品。

（次优先：G11 eval 报告成文、G15 mobile 档位核对、G17 五 Tab 形态裁决、G20 capability probe。）

## 4. 结论

- 后端引擎层与愿景的**语义对齐度出乎意料地高**：friction 15 类、五维 understanding、outcome ledger、allocation ≥90%、hybrid resume、autoexec fail-closed、WVPL golden 均有代码+测试双证（G12-G16、G18）。
- 差距集中在**两端**：体验壳（First 3 Minutes/Example Mode/tab 形态）与**真实证据**（真栈 GJ、真模型 eval、延迟实测、部署）。前者是 A 线活源，后者是 E/O 线活源。
- 「说得出来但跑不通」最高危单点：**演示链延迟（G4）**与**GJ20 无全链证据（G2）**。LOOP3 已证明演练卡能持续产真缺陷，建议常态化。
- 本卡为审计：未改任何产品代码；发现的既有缺口全部以表内证据路径呈现，未现场修。
