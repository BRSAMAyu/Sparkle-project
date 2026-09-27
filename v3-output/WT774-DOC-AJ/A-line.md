# A 线（Aurora 8 卡）深挖章节 —— V4 交接文档素材（wt774）

> 本文是 `v3/V3-COMPLETE-STATUS-FOR-V4.md` §4「各线深度状态」A 线章节的深挖草稿。
> 证据纪律：只写三源证据（git 主干 SHA / 独立审查 receipt / 运行级实测）支撑的事实；逐条标注出处；无法定位证据的验收项显式标注「未定位到证据」。
> 撰写：wt774（2026-09-28，基线 main@5307cbb3）。方法：卡面（v3/07_tasks/cards/A-0*.md）+ `git log --grep` 逐卡定位 → 当前主干代码存在性与消费方开文件核实（policy_patch 白名单面/response_builder 收据装配/kill switch 三态逐处亲证）→ 测试文件逐个 `def test_` 计数 → v3-output REPORT/receipt 抽读 → 台账闭环逐条复核 → A-08 两轮 ablation 产物（raw jsonl/summary.json）数值级读验。**未轻信任何台账/报告结论性文字。**

---

## A.0 线级概览

A 线把「Aurora 从元数据 sidecar 升级为显式控制决策」做成八层工程：决策契约（A-01）→ 干预目录与策略引擎（A-02）→ 摩擦诊断与单问（A-03）→ Human/Agent/Hybrid 联合决策（A-04）→ 有界策略补丁（A-05）→ Why-this 收据（A-06）→ 回访/低刺激关系策略（A-07）→ 纵向/消融评估（A-08）。8/8 全部 done（tasks.json + fleet done + wt759 三源核验 report.md:35-37 逐卡 SHA 在案），交付窗口 2026-09-19～09-26，全部合入主干。

**当前主干活体面核实（本次逐一亲证）**：`backend/app/aurora/` 目录 10744 行（friction_diagnosis 1908 / joint_decision 1125 / intervention_policy 683 / intervention_catalog 443 / calibration_receipt 323 等），加上 `core/policy_patch.py` 869、`core/aurora_decision.py`、`services/policy_patch_service.py`、`services/friction_chat_wiring.py` 677、`services/aurora_receipt_service.py`、`api/v1/aurora_receipts.py`——全部有生产消费方：`friction_chat_wiring.py` 在 chat 决策环消费 A-03 引擎与 A-05 patch（WIRING-1 `7c6cb867`，FIX-33/34/43 三项 FIXED@同 commit）；`context_cache_key.py:89` 消费 PolicyPatchService（策略版本进缓存键）；`response_builder.py:273-349` 消费 `build_calibration_receipt`（A-06 数据流，见 §A.2-A-06）。**A 线不是 frozen-on-paper 契约，是活的决策基础设施。**

**审查证据形态说明（V4 必读）**：A-01/A-02（09-19 首日）有完整 receipt 文件（A-01 双 receipt+RUNTIME_MAP、A-02 单 receipt）；**A-03 起全线改为「commit message 承载签收」**——A-03/A-04 无任何 v3-output 目录，A-05 只有 REPORT.md（"dual-reviewed"/"R2 PASS"等判词逐卡在 commit message 在案），A-06/07/08 只有 REPORT。该形态已被 wt759 三源核验判为合规（WT759-RECON report.md:212「R1 卡级签收在 commit 内，52 卡」），且台账无一行证据指针指向不存在的 receipt 路径（区别于 M/X 线的 V3-FIX-502 断链）——故按 wt769 C 线先例作形态残差记录、不占 FIX 号。V4 若要求 receipt 文件化，这是要改的执行惯例。

**A 线独有的「发现→修复」密度**：A-08 一张评估卡回流 FIX-49/50/51/52 四条（wt412 修三条），A-03 引擎经历 v1→v1_1→v1_2 三轮行为修复（FIX-43/110/111/115/142 五条），A-05 归因面 FIX-67——**A 线的可靠性主要由后期红队与评估卡喂出来，而非首版交付一次到位**。

---

## A.1 意图（卡面目标与验收）

八卡共性 Forbidden 条款与 B/C 线一致（不重建权威真源/不用 mock 冒充/不静态宣称体验/不弱化安全守卫）；依赖链 A-01←B-06+C-01+X-01，A-02←A-01，A-03←A-02+C-03，A-04←A-02+X-02，A-05←A-02+M-06+D-05，A-06←A-03+M-08+U-03，A-07←A-02+U-02，A-08←A-03..07+M-09+C-08。

| 卡 | Risk/Reviewers | 卡面目标（一句话） | 卡面关键验收 |
|---|---|---|---|
| A-01 AuroraDecision 契约与 Runtime 映射 | high/2 | 从 sidecar 升级为显式控制决策但复用现有 20+ 组件；intervention/mode/rationale refs/uncertainty/tier/no_action | 现有聊天不因 shadow Aurora 退化；shadow/live 可对比；契约可追踪 source refs；新能力三态 kill switch |
| A-02 Intervention Catalog + Policy Engine V1 | medium/1 | 17 类干预做成可评测选择空间：规则先过滤非法，LLM 只在合法集合选/参数化 | 每 item 有 capability/permission/expected outcome，无「字符串自由动作」；≥30 基础 scenario 输出合法决策 |
| A-03 Friction Diagnosis + One Best Question | medium/1 | 准确区分卡点并减少问卷式追问；UNKNOWN 时不假诊断 | 20 canonical stuck scenarios ≥18 合理；同一句「做不下去」不同 Context 不同处理 |
| A-04 Human/Agent/Hybrid 联合决策 | high/2 | intervention 与 execution allocation 联合而非两系统各猜；用户 explicit delegation 优先 | paired cases 不出现「intervention 合理但执行权错误」；high-risk auto=0 |
| A-05 Bounded Policy Patches | high/2 | Aurora 从 outcome 更新白名单策略，而非改系统 Prompt/代码；candidate→evidence→confirm→active→expire/revoke | 非法 patch field 被拒绝；用户纠正可撤销；同 scope 历史有效 intervention 可改变 ranking 且有 evidence refs |
| A-06 Why-this / Calibration Receipt | high/2（HEAVY） | 让用户感知理解与可纠正性；receipt 支持 not relevant/wrong/change scope/delete | GJ08 用户可从建议直接纠偏；receipt 与真实 Context 一致；不泄露 hidden CoT |
| A-07 Comeback + Low-stimulation Policies | medium/1 | 回来恢复目标状态而非模板问候；低刺激控制 UI/主动/游戏化，不能心理诊断 | 3/7/14-day test clock 回归合理、不显示陈旧任务为当前；用户 explicit setting 最高优先 |
| A-08 Longitudinal/Ablation Evaluation | medium/1 | 证明 Aurora 比固定模板/无历史基线更好并找到失败边界；10 Persona multi-session 四臂 | 输出 raw+summary；目标指标达到或诚实未达；不把模型 judge 单独作为结论 |

---

## A.2 实际交付逐卡

### A-01 · AuroraDecision 契约与 Runtime 映射

**交付**：合入 `873ba1a4`（ACCEPT merge，dual-review + rework，2026-09-19）。`backend/app/core/aurora_decision.py`（488 行，aurora_decision.v1）——3 个 frozen dataclass + 7 个封闭词表（17 干预名与 AURORA_V3 逐字核对）；ref schemes 从 X-01 结构性派生（growth 自动 surface）；**shadow/live 共享同一 decision_id**（内容寻址）= 对比锚点；44 组件 runtime map（25 决策点 + 23 kill switch，RUNTIME_MAP.md，P3-5 勘误 22→23）——kill switch 全部基于 `app/core/kill_switch.py` 三态原语（off/shadow/live），settings.py:334-348 逐项在案（AURORA_STAGE18/19/21_*_MODE 族）。测试：契约 30 测试（test_aurora_decision_contract.py）+ L2 接线 15 测试（test_a01_aurora_decision_l2_wiring.py），交付时 70 targeted + 177 suite 绿（双 hashseed）。

**shadow/live 对比验收的诚实边界（本次亲证，V4 重点）**：机制在库——`migration.py` shadow cohort 治理链 + `record_shadow_divergence` 计数器（`sparkle_aurora_shadow_divergence_total`，observability/metrics.py:51）+ decision_id 对比锚；但 **fleet state notes 全文 0 次 shadow divergence 运行记录**——V3 期间没有做过一次真实 shadow/live 对比运行。「现有聊天不因 shadow Aurora 退化」以「shadow 分段 kill switch 默认不改变现役路径」的构造性方式保证，而非实测对比。V4 若做 Aurora 灰度/迁移，这套机制是现成的，但需要真正跑起来。

**残差**：① 23 个 kill switch 三态面之外，wt765（O-06 扫雷）发现 `AURORA_DEFAULT_MODE`「总默认」声明零读者（**V3-FIX-500 OPEN**）与 5 个 metacognition proxy 绕开 kill switch 核心（**V3-FIX-501 OPEN**）——A-01 的三态治理面存在两处声明与行为脱节，登记在案待修；② FIX-30 的 P3-2/P3-4/P3-5 follow-ups 备忘型未深查（台账行在案）。

**一句话用户可见行为**：无直接可见行为（契约+治理层）；它让后续所有 A 线卡共享同一决策词汇与 decision_id 追踪锚。

### A-02 · Intervention Catalog + Policy Engine V1

**交付**：合入 `0c56a96f`（ACCEPT merge，single deep review，2026-09-19）。`backend/app/aurora/intervention_catalog.py`（443 行）——catalog 从 `AURORA_INTERVENTION_TYPES` 结构性派生（零拷贝、漂移即 fail-fast；卡面拼写地雷 R0 拒绝）；`intervention_policy.py`（674 行→现 683）——10 个纯函数守卫 + 16 个封闭 reason codes（sha256 双钉）；**feasible-set-then-LLM**（合法集先过滤、LLM 只在集合内选——与 X-02 同构）；spine 34 条策略字符串全投影（双向契约）；no_action 确定性出口；P3-8 缺失/脏 allocation mode → 确定性拒绝。场景面：`backend/tests/aurora/fixtures/intervention_policy_scenarios.json` **45 场景**（卡面要求 ≥30，超额兑现，本次读文件亲证 `_count: 45`）。测试：目录契约 13 + 策略引擎 24；交付时 106 targeted + 349 回归绿。

**残差**：catalog 的「每个 item 有 capability/permission/expected outcome」以结构字段兑现；LLM 真模型上的选择质量属 A-08 评估域（见该卡——四臂驱动为确定性服务面+模型 judge 0 次，真模型干预选择质量未独立测量）。

**一句话用户可见行为**：AI 的干预动作不再「字符串自由发挥」——所有出面都是目录内词表项且带守卫。

### A-03 · Friction Diagnosis + Sufficiency / One Best Question

**交付（v1 三轮演进，全部主干在案）**：

| 版本 | 主干 SHA | 内容 |
|---|---|---|
| v1 | `fd2d4a45`（reviewed，2026-09-20） | `friction_diagnosis.py`（1588 行）aurora_friction_diagnosis.v1：15 类摩擦分类→充分性判定→One Best Question→追问预算，纯函数零 IO never-raises；决策敏感封闭形式 `_flip_changes_primary`；负信息增益保留（认识论诚实）；答案种子零先验吸收+证据量均摊（冷启动两问收敛）；hard_family：同句「做不下去」三 Context 三处理（问/问一次对/直出 pause）。20 canonical 场景 + hard_family 6（fixture 本次读文件亲证，含 rubric 注释）；73 targeted + 6 变异必红。R2 PASS（1 P2→FIX-43 P1 接线条目 + 6 P3）。**无 v3-output 目录，签收在 commit message** |
| v1_1 | `7c6cb867`（WIRING-1） | 负向分支遮蔽根修（最长词牌算法）+指纹 bump |
| v1_2 | `28442a5a`（wt412） | B1 exact-tie 降级 B3.budget_exhausted_tie_no_action（宽分支零事实平权不再按字母序偶然型行动；TIE_DISCRIMINATION_EPSILON=1e-9 入指纹+子进程换 seed 测试锁死）——修复 A-08 实锤的 FIX-50 |

**生产接线（本次开文件亲证）**：`friction_chat_wiring.py`（677 行）在 chat 决策环消费引擎；FIX-49 出口词牌门（ask/act 出面必须携带 utterance_matches 正向词牌否则静默 no_action）、FIX-110 否定感知、FIX-111 answer_replay 置信门、FIX-115 卡住族词表补齐——四条摩擦门语义缺陷族 FIXED@`8541ddde`（wt428）；FIX-142 出口载荷剔除 input_snapshot（用户原话不进 response metadata）FIXED@`4e8b226b`。旅程面消费：J-05 stuck_journey_service 全部选问/主干预交冻结 A-03 引擎（LLM 0 次）。A-03 冻结面现值 112 测试（FIX-142 行注记「A-03 冻结面 112/112」）+ test_a03_friction_diagnosis.py 77 函数 + wiring 45 函数（本次逐文件计数）。

**卡面验收兑现**：20 场景 ≥18 合理=fixture rubric+变异实证；「同一句不同 Context 不同处理」=hard_family 6 例契约锁；「UNKNOWN 时不假诊断」=缺事实保持 None 不猜（J-05 集成实录再证）。

**残差**：FIX-52 **OPEN**——行为事实证据无双刃消解（历史失败痕迹把新类型卡点系统性带偏，A-08 记忆面反例 p07 的机制成因），随 A-03 迭代处理；FIX-97 **OPEN 待产品拍板**——诚实化后 journey-first persona 的错位行动消失→「不是这个原因」纠正通道饿死（见 §A.4-4）。

**一句话用户可见行为**：用户说「做不下去」时，AI 只在证据够时问一个高价值问题、在零证据时诚实 no_action（不再问卷式追问、不再凭空猜原因）。

### A-04 · Aurora Human/Agent/Hybrid 联合决策

**交付**：合入 `e943e08b`（dual-reviewed，2026-09-20）。`backend/app/aurora/joint_decision.py`（1078 行→现 1125）——纯函数两步联合（policy×allocation→结构性约束→A-01 契约），D1-D4/X1 确定性裁决序+对抗归因，**high-risk auto=0**，交叉边界 8×3×2 穷举；`joint_factor_projection.py`（300 行）——严格 bool 因子装配投影器（闭合 A-02 验收 N3 缺口）；L2 生产决策点完整链接线（投影→联合→契约 P3-8 ref→`spine:aurora_decisions` 真落键，`signals/spine_orchestrator.py` +152）；语义通道三重隔离默认关+shadow read 门；12 canonical scenarios 冻结（真实引擎实跑）。测试：契约 10 + 联合 40 + 投影 27 + spine 接线 7（本次计数）；交付时 139 targeted/558 回归绿（双 hash 种子）。R2 ACCEPT（零 P1/P2）+ R1 PASS；follow-ups→FIX-30。**无 v3-output 目录，签收在 commit message。**

**验收的下游再证**：「high-risk auto=0」后来被 X-10 的 77 场景 eval 以 allocation 100%、high-risk auto=0、false success=0 再证（详 X 线章 §X.2-X-10）；J-04 的学习守卫（LLM 建议 agent 被分配策略拦回 human/hybrid）是本引擎 decide_allocation 的生产路径实证（`02b82cd2` 5-Persona 断言）。

**残差**：FIX-30 三条 P3 备忘（decide_joint 步绑定提名陷阱/AllocationDecision.to_dict 缺 annotations/7 个待落投影点）——「均不阻塞」自登记，与执行面投影点接线同批处理，V4 做执行面深化时应先读该行。

**一句话用户可见行为**：用户在学习类任务上永远不会被 AI 自动代执行高风险步骤；AI 建议的执行权分配可从 decision log 溯源。

### A-05 · Bounded Policy Patches / Adaptive Preferences

**交付**：合入 `64678a2b`（dual-reviewed，2026-09-20）。四件套：`backend/app/core/policy_patch.py`（869 行纯契约层）+ `models/policy_patch.py`（59 行）+ `services/policy_patch_service.py`（889 行）+ 迁移 a05_20260919。R2 CHANGES→返修（scope 三面+审计 append-only+FOR UPDATE）→delta PASS+R1 PASS；**REPORT.md 入库但两份 review receipt 未入库**（见 §A.0 形态说明）。

**「边界」实际由什么保证（卡面灵魂，本次逐条开文件亲证）——五层硬约束面**：

1. **六面白名单封闭**（`POLICY_PATCH_SURFACES`，冻结）：granularity/clarification/explanation/intervention_preference/proactive_cadence/allocation_preference **恰好六面**，精确集+sha256 被契约测试双钉；surface 不在集合→`V1.surface_not_whitelisted` 拒绝（fail-closed）。「改 prompt/改代码/改模型参数」没有合法 surface 名，**走不到任何写路径**（模块 docstring 原文：「提示词边界不是边界……本模块把可塑性面也做成代码边界」；变异守卫：放开白名单必红）。
2. **payload 封闭**：每面独立键集+值域（`SURFACE_PAYLOAD_SCHEMAS` 冻结）——未知键 `V2.payload_field_unknown`、词表外值 `V3.payload_value_out_of_vocabulary`，无静默修正。
3. **patch 是决策输入不是代码**：六面消费契约全部是确定性投影——3 面进 A-02 提名重排、allocation_preference 进 X-02 因子（`AllocationFactors.user_preference` 既有入参，不绕过 A-04 联合约束层）、proactive_cadence 进主动门因子、explanation 进解释参数化。
4. **生命周期状态机封闭**：candidate→evidenced→active→expired/revoked（+rejected 终态），非法迁移 `T6.illegal_transition` 拒绝；revoked 即时生效+版本立即 bump，复活需新 patch（M-01 supersede 哲学）。
5. **证据门只认真源**：evidence_refs 封闭 scheme `memory://experience/<id>`（M-06）与 `decision://aurora_<32hex>`（A-01/D-05）；方向敏感（prefer 需正向共同出现证据、demote 需负向）；档位真源=D-05 `association_evidence_tier`，消费 M-06 `completeness_adjusted_strength` 保守值；single_observation 需用户 confirm，≥repeated 才可自动激活。

**策略版本与缓存正确性（卡面 Work 3）**：`compute_policy_patch_version` 内容寻址 `polpatch_<sha256[:16]>`，active 集任一变化版本必变；`context_cache_key.py:89` 亲证消费 PolicyPatchService——策略版本进缓存键，bump 即失效。归因：`applied_patch_ids` 走与 situation_patches 同一 `scope_matches` 谓词（FIX-67 修，FIXED@`7244efb2`——修前归因面曾用全量 effective patches 过报）。

**生产接线实证**：WIRING-1 `7c6cb867`——patched_decision_inputs 真实进决策环，**prefer-patch 翻转 practice→explain e2e 实录**（FIX-34 FIXED@同 commit）；测试现值契约 30 + 服务 39 + 迁移 sqlite 3 = 72 函数。下游消费：A-08 评估 harness 以 A-05 patch 证据门为四臂驱动面之一；D-08 数据飞轮（`46762b31`）复用同门实证「反馈→未来行为真实变化」14 条链。

**残差**：FIX-31 P3 子项（inputs 缓存 120s TTL 陈旧/进程级缓存单进程契约/is_effective 边界）已随 D-05 增量批收口（FIXED@49d81fb2 复验口径）；patch 面的用户直接可见管理 UI 未见交付（V3 的 patch 由引擎证据门驱动，用户面只有「纠正可撤销」语义——V4 若做个性化设置面板，这里是现成后端+缺前端）。

**一句话用户可见行为**：用户的纠正与结果反馈能在**白名单六面**内改变后续 AI 行为（如解释详略、主动频率），且撤销立即生效；AI 永远不能借 patch 改系统提示词或代码。

### A-06 · Aurora "Why this?" / Calibration Receipt

**交付（两波）**：

| 波次 | 主干 SHA | 内容 |
|---|---|---|
| wt311 机制面 | `d8a89bec`（2026-09-24） | `aurora/calibration_receipt.py`（323 行，pure frozen-v1）：4 动作封闭词表+authority-delegation map+uncertainty 标签覆盖 AURORA_UNCERTAINTY_KINDS+呈现门 hidden/ambient/surfaced+3/day 预算；**降档只降强度、绝不吞纠正**。`api/v1/aurora_receipts.py`（111 行，POST /aurora/receipts/respond）+`services/aurora_receipt_service.py`（146 行）——**四动作全部委托既有权威**：not_relevant→M-06 denied 飞轮、wrong(带内容)→M-01 supersede、wrong(无内容)→降置信、change_scope→scope pause、delete→M-07 撤销链；**零新写路径零新表零新迁移**。response_builder 接线（rationale 组成摘要+GraphRAG 真实 refs+uncertainties，Redis 日计数 fail-open）。mobile：独立 AuroraReceiptApiService+aurora_receipt_chip（235 行）+CoT 红线 STRUCTURAL（decision-ring 代码不可进入模块数据流，测试双钉 JSON 无内部码）。32 backend+7 widget 绿 |
| wt388 旅程级验收锁 | `b9bc60ae`（2026-09-2x） | test_a06_gj08_calibration_journey.py（16 个测试函数，交付注记 17 用例）：①**receipt↔真实 Context 一致正测**（经 ResponseBuilderMixin 真实装配路径，refs⊆该用户 Context 行且内容一致）；②**编造 ref 必败负测**（随机 UUID 四动作必败+HTTP 404 与越权同形态无存在性泄漏）；③GJ08 四路纠偏→下一轮适配链（change_scope/delete→召回真源排除；supersede→旧内容不再召回新内容可引用；not_relevant/wrong→降噪 0.65→0.55→下轮回执升格 uncertain——**被纠正后能变**）；④按需展开三态（未自然引用→hidden 无回执；全高置信→ambient；不确定→surfaced）；⑤CoT 硬红线负测（reasoning 脏字段经 gRPC 同款编码零泄露）。**变异实验 5 组全部拦截**（摘除召回排除→红/阈值改动→红/去 user_id→越权红） |

**数据流真实性核验（本次亲证代码链）**：`response_builder.py:273` 从检索面取 `retrieval["context_receipt"]["used_names"]`（真实 GraphRAG 检索的引用记录）→ `:300` `_build_memory_reference_receipt` → `:345` `build_calibration_receipt`（纯模块装配 rationale 摘要+refs+uncertainties，呈现门+日预算）→ chat 响应 metadata 附带 receipt → 用户点四动作 → `/aurora/receipts/respond`（404 无存在性泄漏/409 非 ACTIVE/422 词表外）→ 委托权威真源生效 → wt388 钉死的「下一轮适配」链可观测。**结论：A-06 的数据流是真实检索驱动的，不是模板回显**；「receipt 与真实 Context 一致」有变异实验级测试锁。

**验证证据**：test_a06_calibration_receipt 23 + test_a06_receipt_respond 13 + GJ08 旅程 16 = **52 测试函数**（本次逐文件计数）；HTTP 入口面 200/404/422/409 全谱；v3-output/WT311-A06/REPORT.md 在库（receipt 文件缺，形态说明见 §A.0）。

**残差**：wt388 DEFERRED「定向 widget 真跑」（free swap 837M<1.2G 门，补跑命令在 REPORT）——widget 测试文件已入库，现由 CI flutter 面覆盖；卡片「避免每条回复都强制展示历史」以 3/day 预算+hidden/ambient 三态兑现，但收据在真实对话中的自然出现率（用户实际多久能看到一次 why-this）无运行级统计（unknown）。

**一句话用户可见行为**：AI 推荐旁边有「为什么是这条」收据；用户可以就任意一条记忆引用直接「不相关/说错了/改范围/删掉」，且被纠正后下一轮对话真实改变。

### A-07 · Comeback + Low-stimulation Relationship Policies

**交付**：合入 `9ce23e55`（wt362，2026-09-25）+ mypy 收口 `fe947483` + 交付物入库 `16d7583d`。三块：①**回来恢复目标状态而非模板问候**——comeback payload 新增 goal_state 读侧真源投影（Goal 标题/status/诚实进度 completed/total 含冻结 0，零写库）+ComebackBanner 目标状态行；②**陈旧任务守卫 3/7/14-day clock**——plan_expired/next_task_overdue_days/stale_focus 入 payload，checkpoint_debrief 与 personalized_return 文案诚实化（计划窗口已结束不再宣称「还来得及/收尾窗口」，改如实呈报+指向重新校准 replan 端点）；3 天阈值触发+焦点逾期≥3 天标记 stale，**红测=goal_state 缺失/陈旧伪装当前即红+变异实验实证拦截力**；③**low-stimulation 关系策略**——`aurora_stimulation_mode`（auto/low/standard）显式偏好入 AuroraUserPreferencesService+PUT /aurora/preferences，`stimulation_policy` 模块（explicit low→主动 nudge 不推送仅入通知中心+重复抑制 24h→72h+标题去敦促化；explicit standard→行为零变化；**绝不心理诊断**）；移动端三选档经 EmotionStateNotifier.setMode 同步引擎。测试：引擎定向 23（comeback 13+stimulation 7+nudge 3，本次计数一致）；flutter 定向交付时 DEFERRED（swap 门三次实测）——测试文件全部入库，现由 CI flutter 面覆盖。

**下游协同（亲证）**：P-06（`05cc6328`）统一通知设置以 `aurora_stimulation_mode` 为真源之一做低刺激交集语义（quiet 窗两端外扩 60min+cap 3→2）；U-02（`22f99776`）低刺激视觉/动效档与 A-07 引擎档分属两层（**解锁 A-07→A-08 全线的卡**）；J-07（wt385）复用本卡 payload 三块并补齐 ComebackContextResponse 模型（见 J 线章）。

**残差**：①**FIX-48 OPEN（待产品拍板）**——P-05 纵向评估反例：A-07 的 stale 诚实文案生效但过期计划（非完成）的建议投放不停（最坏 persona 14 天收 14 条、dismiss 4 次仍每日一条，唯一有效停运杆是 mute）——「低刺激」与「主动面打扰」的权衡缺产品裁决；②「低刺激截图/interaction 通过」验收以 U-02 的 9 widget 两档真实差异测试+CI 覆盖兑现，实机截图走查转 HUMAN_INBOX。

**一句话用户可见行为**：离开几天回来，看到的是自己目标的真实进度和「计划窗口已结束、重新校准」的诚实建议，而不是「还来得及！」的敦促模板；开了低刺激档后主动推送安静下来。

### A-08 · Aurora Longitudinal / Ablation Evaluation

**交付（主卡 + 行为修复组 + 飞轮复用，三轮主干在案）**：

| 轮次 | 主干 SHA | 内容 |
|---|---|---|
| wt393 主卡 | `2d2336ea`（2026-09-25） | 消融 harness 四文件（engine 701/metrics 378/persona 419/world 363，`backend/tests/aurora_ablation/`）+ 契约锁 13 测试 + runner `scripts/devtools/a08_run_aurora_ablation_eval.py`（187 行）；产物 `v3-output/WT393-A08-ABLATION/`（REPORT+EVAL_RESULTS+raw/*.jsonl 四臂 348 行+summary.json 3186 行，全部入库）。**10 persona×14 模拟日×20 卡点段+25 对照会话**；驱动面=真实 Aurora 服务面（StuckJourneyService+FrictionChatWiringService+D-05 lifecycle+A-05 patch 证据门+StateRegister），sqlite 隔离+fakeredis+backdate 可控时钟，**产品代码零改动**；确定性判据为主、模型 judge 0 次；summary 全由 raw 程序化复算（--verify-repro 双跑一致 exit 0）；反例照登回流 V3-FIX-49..52 |
| wt412 行为修复组 | `28442a5a`（2026-09-26） | 修 A-08 实锤的 FIX-49/50/51（词牌门/B3 tie 降级/delivery=recommendation 契约）+FIX-59；**A-08 全人口四臂复跑不回退证明**，产物 `v3-output/WT412-FRICTION-FIXES/a08-post-fix/`（EVAL_RESULTS+summary.json+raw 入库） |
| D-08 复用 | `46762b31`（wt397） | A-08 人口/harness 零重建复用做数据飞轮纵向证明：Day0/3/7 双臂配对证实「反馈→未来行为真实变化」14+10 条链，25 条无效个性化照登（含 4 条有害适应），A-05 证据门为被评面之一 |

**方法论与数字可信度（本次产物数值级读验）**：
- **可信面**：①驱动全部走真实服务面（非脚本重放）；②判据确定性（resolution_requires_match/budget_respected 不变量每臂报告，fixed_arm_zero_engine_calls=true 钉死对照臂零引擎调用）；③效用权重冻结并印在产物头；④summary 由 raw 程序化复算且 --verify-repro 双跑一致——**数字是可复现的**；⑤模型 judge 0 次（卡面「不把模型 judge 单独作为结论」超额兑现）。
- **边界面**：人口是 10 个合成 persona（静态时间线，DEFERRED 明示「外推力有限」）；判据是引擎自身冻结契约（评的是「机制按设计收敛」，非真实用户价值）；**无真实 LLM 参与**（hermetic 是刻意设计——CI 可跑可复算），「Aurora 比固定模板好」的结论适用于机制层，不构成真模型效用证明。
- **头条数字的时点（V4 必读）**：v0.3 文档引用的「0.65 vs 0.30」是 wt393 修前值。**wt412 行为修复后，入库终态（gate+B3）为 accuracy 0.45/0.55/0.45/0.30（full/no_memory/no_experience/fixed_policy）**（a08-post-fix/summary.json 本次读验）；full 效用 -16.2→-9.2（提交信息的 -3.6 是「去除侵入罚项」的 gate-only 分解值，REPORT.md 分解表在案，非终值）；对照侵入率 84%→0。accuracy 0.65→0.45 的回落全部归因为 B3 移除平权偶然蒙对（5 个 journey 幸运段逐一入档）——**full 仍稳定优于 fixed（0.45 vs 0.30），但修后复跑中 no_memory 臂 accuracy 0.55、效用 0.0，双指标高于 full（0.45/-9.2）**：在这套模拟人口上，记忆面的净贡献在行为修复后是负向的（与 wt393 原始记录「记忆面净收益 +0.10/+5.2 但含个体伤害反例」方向相反）。这是 V4 设计个性化记忆面时最应直视的一组数字。

**残差**：①FIX-52 OPEN（历史失败痕迹带偏新类型卡点——no_memory 反超 full 的机制成因之一）；②FIX-97 OPEN 待产品拍板（纠正通道饿死）；③「经验面收益未证」（chat-first+错型+同 tag 历史交集未覆盖——DEFERRED 原文），D-08 已部分补证飞轮行为链但效用因果联动仍 reserved；④卡片 Work 1 的「A/B no-memory/no-experience/fixed-policy/full」以四臂兑现 ✅，但「multi-session」的纵向面由 D-08 承接而非本卡独立完成（分工而非缺口）。

**一句话用户可见行为**：无直接可见行为（评估卡）；它产生了 V3 最重要的自我否定证据（侵入门缺失/B1 平权 tie/记忆双刃），并直接塑造了 A-03 v1_2 与 wiring v2 的现行行为。

---

## A.3 设计决定与取舍（从提交/审查考古）

1. **白名单即代码边界（A-05）**：卡面「而非改系统 Prompt/代码」没有落在提示词纪律上，而是落在「六面精确集 sha256 双钉+变异必红」——设计立场是「提示词边界不是边界」。代价是个性化表达力被压到六面；收益是「AI 能自己改什么」变成可机器断言的封闭问题。
2. **feasible-set-then-LLM（A-02）**：规则先定合法集、LLM 只在集合内选——与 X-02 同构。V3 从不信任 LLM 的动作空间，只信任它的排序与参数化；V4 扩干预目录时这条次序应保持。
3. **契约先行+shadow 锚（A-01）**：shadow/live 共享内容寻址 decision_id，把「对比」从 ad-hoc 观测变成键级锚。取舍：V3 期间一次真实 shadow 对比都没跑（机制在库、运行未发生）——契约的完备性跑在了运维采用前面。
4. **确定性优先（A-03/A-04/A-08 一致）**：摩擦诊断纯函数零 IO never-raises、联合决策 D1-D4/X1 确定性裁决序、A-08 模型 judge 0 次+程序化复算——A 线的「智能」面全部做成可复现的规则层，LLM 只在授权的推导/起草点（J-04/J-06）出场。「不把模型 judge 单独作为结论」不是口号是结构。
5. **反例照登+回流修（A-08 教义）**：评估卡交付时同时登记 FIX-49..52 四条自家缺陷（含「无门全量触发 100% 侵入」这种丢脸数字），随后 wt412 修复并复跑不回退证明——**V3 的评估卡的价值标准是「找出自己的边界」而非「证明自己好」**。V4 的 eval 卡应沿用此验收形态。
6. **证据门消费真源而非自报（A-05）**：patch 激活的证据只认 M-06 投影行与 D-05 关联行，方向敏感（prefer/demote 分向）、档位保守（截断降档后取值）——「Aurora 从 outcome 学习」的每一步都可溯源到真实记录。
7. **呈现预算与降档不吞纠正（A-06）**：3/day 预算+hidden/ambient/surfaced 三态解决「理解收据」的打扰问题；「降档只降强度、绝不吞纠正」保证可纠正性不被省电策略牺牲。
8. **诚实性取舍**：A-07 宁可把「还来得及」全删改成如实呈报（被打扰问题转到 FIX-48 待拍板），A-03 宁可 no_action 饿死纠正通道（FIX-97 待拍板）也不回退到猜测——两处 OPEN 都是「诚实与体验的权衡被显式留给产品」，V4 应作为设计议题接手而非当 bug 修。

---

## A.4 残差与 V4 注意点（汇总）

1. **A-08 终态数字与文档口径**：引用消融结论时以 a08-post-fix/summary.json 终态为准（full 0.45/-9.2 vs fixed 0.30/-24.8，no_memory 0.55/0.0 反超 full）；v0.3 文档的「0.65 vs 0.30」是 wt412 修前值。在模拟人口上「记忆面净贡献为负」是现行最硬的自我认知，V4 做记忆/个性化设计时应从这里出发（结合 M 线 M-09 缺陷发现器叙事）。
2. **两个 OPEN 的产品裁决**：FIX-97（无行动出口的第二纠正入口形态——诚实 no_action 让「不是这个原因」纠正通道饿死）与 FIX-48（低刺激与主动打扰的权衡、过期计划建议衰减）——都是「诚实边界与体验的冲突」，需产品拍板而非机械修。
3. **两个 OPEN 的三态治理缺口**：FIX-500（AURORA_DEFAULT_MODE 零读者）/FIX-501（5 个 metacog proxy 绕开 kill switch 核心）——A-01 的治理面有两处声明与行为脱节，wt765 已登记待修。
4. **shadow/live 对比从未真实运行**：机制齐备（decision_id 锚+divergence 计数器+cohort 治理链），运行记录为零。V4 若做 Aurora 灰度/迁移，第一张卡应是「真跑一次 shadow 对比」。
5. **真模型效用层整体缺位**：A-08 四臂是确定性服务面模拟（hermetic 刻意设计）；「Aurora 干预在真实 LLM 用户上的效用」与 A-02「LLM 在合法集内的选择质量」都没有真模型数据。V4 若要证明个性化价值，A-08 harness 换真模型驱动是现成起点（同 C-08 context_eval 的复用逻辑）。
6. **A 线核心测试面**：本次逐文件计数 16 个 A 线主测试文件 355 个测试函数，加 friction_chat_wiring 45 与 A-06 收据 52，A 线轨道合计约 452 个测试函数（不含迁移/邻域）。
7. **审查 receipt 文件化缺口（形态残差）**：A-03 起 receipt 以 commit message 承载（wt759 判合规、台账无断链指针）；追溯成本高，V4 若要求文件化按 FIX-502 三选一同构处理。

---

## A.5 本次审查登记

- **零新登记**。本次深挖复核过的候选发现均判定不构成台账级新账：①A-03/A-04 无 v3-output 目录、A-05 双审 receipt 未入库——属 wt759 已裁决合规的「commit 内签收」形态且台账零断链指针（区别于 M/X 线 FIX-502 的指针腐烂），按 wt769 C 线先例作形态残差记录；②「0.65 vs 0.30」时点漂移——两轮数字均诚实入库（a08-post-fix 产物在主干），属文档引用口径问题，本文件 §A.4-1 已给终态口径，随章并入 v0.4 即修正；③J-01 机会图未处置项归 J 线章（见 J-line.md §J.4-2）。
- 号占用核验：505 起空闲——`grep -rn "V3-FIX-50[5-9]|V3-FIX-5[1-9][0-9]" v3/ v3-output/ docs/ backend/` 零命中（499=wt767、500/501=wt765、502/503=wt770、504=wt769 均已占用）。
- A 线相关 FIX 全链状态复核：FIX-30 备忘在案｜FIX-31 FIXED@49d81fb2｜FIX-33/34/43 FIXED@7c6cb867｜FIX-49/50/51/59 FIXED@28442a5a｜FIX-52 OPEN｜FIX-67 FIXED@7244efb2｜FIX-97 OPEN 待拍板｜FIX-110/111/115 FIXED@8541ddde｜FIX-142 FIXED@4e8b226b｜FIX-48 OPEN 待拍板｜FIX-500/501 OPEN（wt765 登记）。
