# M 线（Memory，10 卡）深挖章 —— V3-COMPLETE-STATUS-FOR-V4 §4 素材

> 作者：wt770（文档深挖）｜基线：main@ce9846a3（2026-09-28）｜方法：卡面 + `git log --grep` 逐卡定位 → 读现势代码核实 → 目标测试在 worktree 实跑 → REPORT/REVIEW_RECEIPT/FIX 台账抽读。
> **本章事实判据**：所有 SHA 均已在 main 可达（`git show` 亲验）；运行级证据 = 本 worktree 实跑（见 §2.0）；推断/待验证项显式标注「推测」。
> 本轮新登记：**V3-FIX-502**（M/X 线卡级 receipt 断链）、**V3-FIX-503**（M-09 真模型复验承诺未兑现），见 §5。

## 0. 逐卡验证口径（本章通用）

- **实跑验证（2026-09-28，worktree wt770-docmx = main HEAD）**：M 线核心测试 273 用例全绿——
  `test_memory_epistemic_contract + test_memory_invalidation_pipeline + test_memory_storage_gate + test_memory_retrieval_prefilter + test_memory_use_selfcheck` = 183 passed；
  `tests/memory_eval/test_memory_eval_gate + test_memory_provenance_api + test_experience_memory_contract + test_experience_memory_projector` = 90 passed（18.9s，sqlite in-memory，零 LLM）。
- **评审证据形态**：M-01..M-07、M-10 有入库 receipt/REPORT；**M-06/M-08/M-09 的 receipt 原件未入库**（评审结论在 commit message 内，经 wt759 三源核验）→ 已登记 V3-FIX-502。
- tasks.json 20 张卡 status=done（wt759 核正 8d4291aa 落库），fleet done 名单 20/20 在册。

## 1. 意图（卡面提炼）

M 线 10 卡（MEMORY stream，V3-2~V3-4 门）要回答一个问题：**系统对用户的「理解」如何做到正确、可纠正、可删除、可信任**。设计骨架（MEMORY_V3.md / USER_WORLD_MODEL.md）：

1. **认识论分型**：每条记忆可归入 FACT / CONFIRMED_PREFERENCE / OBSERVATION / HYPOTHESIS / EXPERIENCE 五型之一，且可指出 source/scope/status（M-01）；**推断永远不能覆盖用户陈述的事实**（M-01 红线）。
2. **该不该记**：写入前用规则+快速语义门判定 store/current_state/event/ignore/confirm，瞬态（「今天下午3点有课」）不得默认长期化（M-02）。
3. **该不该用**：检索在 LLM 之前用确定性规则预筛（wrong-user/revoked/expired 在语义检索前为 0，M-03）；合法召回后再判断「该不该说出来」（over-personalization ≤5% 目标，M-05）。
4. **冲突仲裁**：多来源/多时间证据显式仲裁，explicit correction 胜过旧 inference，scope 不同可共存，高增益不确定时出澄清而非静默选（M-04）。
5. **经验投影**：从真实 intervention→outcome 投影「何种帮助曾有效」，无 outcome 不标 effective，失败同样保留（M-06）。
6. **纠正/删除终局**：删除/纠正贯穿派生状态、缓存、后续检索——删除后新请求 0 使用、旧 derived summary 不复活、重复删除幂等（M-07，risk=critical）。
7. **用户主权 API**：list/detail/source/scope/update/revoke/why-this，UI 不读内部 ORM，跨用户零泄露，source 不存在诚实 unknown（M-08）。
8. **回归门禁**：≥80 multi-session cases × 10 Persona、paired 无历史基线、关键 case 真模型 ×5，失败不被平均掩盖（M-09）。
9. **全链到 UI**：用户无需知道 Memory 内部结构即可查看来源、纠正、删除，且删除后当前/未来个性化正确变化（M-10）。

**Forbidden（全卡共性，执行中逐卡核验）**：不重建既有权威真源（不建第二记忆库）；不用 mock/seed 冒充真实行为；不以静态代码阅读宣称用户体验通过；不弱化既有安全/幂等/隔离/审计守卫。

## 2. 实际交付逐卡表

### 2.1 总表

| 卡 | 主干 SHA（评审签收） | 关键交付 | 用户可见行为一句话 | 验证证据 | 残差 |
|---|---|---|---|---|---|
| M-01 | `7ef808ee`（dual-review+rework） | 契约模块 `memory_epistemic_contract.py`（362L）+ 迁移 `m01a` + 写路守卫 | 推断值不再顶替用户显式偏好；导出/面板可见每条记忆的类型/状态/范围 | 红 7F/3P→绿 10/10 守卫；R2 返修后 23 passed；并发 bump 测试 {2,3,4} | FIX-10 F2-F7 → M-04 已收口@`fa4e5837` |
| M-02 | `10fde918`（ACCEPT）+ FIX-41@`1ae6a9e1` | `memory_storage_gate.py`（1038L）规则门 + 默认关的语义层 | 「明早8点考试」落短窗事件而非终身事实；敏感推断不直接入库需确认 | 64 场景规则层 P/R=1.0/类（EVAL_RESULTS）；13 对抗负例钉单测 | FIX-15/FIX-44 词表残留 OPEN |
| M-03 | `1ea854c9`（dual-review+2 rework） | `memory_retrieval_prefilter.py`（716L）+ context_builder/context_pack 接线 | 已删除/过期/他人记忆在进入 LLM 前为 0 | 1165L 测试；红态实漏实证（superseded 行穿越 SQL） | 守卫测试曾因 worktree 缺 app.gen 静默不可收集（FIX-35 成因之一，流程教训） |
| M-04 | `fa4e5837`（R2 dual-pass+Leader verify） | `conflict_resolver_service.py` +855L 仲裁接线 | 用户纠正胜过旧推断；冲突可出澄清；每条裁决带 resolution record | 1391L 类目测试；M-01 遗留 F2/F4/F6/F7 同卡收口 | aurora_calibration_receipt lane 红线经 FIX-06 迁移写入点@`a28a5b8c` |
| M-05 | `b9a48bdb`（single deep review） | `memory_use_selfcheck.py`（735L）+ OP-Bench 46 case | 无关记忆可召回但不再每轮刷屏；谄媚性附和被拦 | 规则层盲跑过度个性化 0.0%（0/21，目标≤5%）；1066L 测试 | FIX-35 第二失败模式（irrelevant_to_query 降档链头）已随 `3c2ca32c` 收口 |
| M-06 | `e56be400`（R2-reviewed, P2-1 fixed） | `experience_memory.py`（735L）+ projector（346L） | 「上次这样帮你有效/无效」进上下文（WIRING-1 后） | 1290L 契约+服务测试；无 outcome 不标 effective 有契约钉 | **交付时未接 chat（FIX-33）**，`7c6cb867` 补接线；生产降档率 66.67%（selfcheck 收紧，设计内） |
| M-07 | `0ea1e198`（dual-review+rework+delta） | `memory_invalidation_pipeline.py`（477L）统一失效管线 | 用户删除一条偏好，所有个性化面（含缓存）立即不再使用它 | 红 13F/4P→绿 17/17（863L 测试）；live 键复活主通道红→绿 | semantic_cache/state_aggregator 豁免经源码核对登记（不含记忆内容） |
| M-08 | `cbd7e44d`（dual-reviewed, rev2） | `/memory/provenance/*` API（277L）+ service（1186L）+ m08 迁移 | U-03 理解面的每条来源可查、可改、可删、可问「为什么当时用它」 | 1171L API 测试（21 定向测+变异 A/B/C） | FIX-39 OPEN：revoke 端点旗标组合 500 面 + m08 迁移无回填（迁移头已披露） |
| M-09 | `7d1eedd3`（R2-reviewed） | `tests/memory_eval/` 评测套件：82 case×10 Persona + 真模型 25 次预算探针 | （对内）记忆正确性成为可重复门禁 | 门禁在库且现绿（REGISTERED_BUG_CASE_IDS 已清空）；真模型报告 5case×5 入库 | FIX-38 OPEN（to_row 丢 detail、fail-open 语义门未声明、.env 绝对路径、21 case 同构） |
| M-10 | `90cda638`（wt354）+ 债兑现 `bff5a816` | mobile 15 文件：chat 回执「为什么有这条」深链 + 五面失效级联 + 黑话清除 | 用户在聊天里点「不对」可直达来源并真删；删除后各面板同步重算 | 4 测试文件 analyze 0 错；DEFERRED 债由 CI 首跑兑现（7/7 绿@`bff5a816`） | **GJ08/GJ09 三端实机走查未做**（headless 口径，wt759 标 ⚠）；UnderstandingSnapshotCard「可信度 X%」文案残留（报告 §8.4 自登记） |

### 2.2 逐卡要点与证据细节

**M-01（7ef808ee）**——交付四层：
1. `EpistemicClass` 五型；CONFIRMED_PREFERENCE 由表成员资格承载（memory_preferences/memory_goals 即该型），不加列——「不建第二库」的具体落法。
2. `derive_status` 七态状态机（revoked>superseded>retracted>archived>expired>resolved>active），全部从既有列派生，零新增存储（episodic 仅加 `epistemic_class`/`superseded_by_id` 两列）。
3. **红→绿守卫（真 bug 实证）**：`upsert_preference` 原实现无条件建新版并压链头——推断写（ai_inferred）会把用户显式偏好 supersede 掉；修后 inferred→explicit 拒写（指标 `MEMORY_WRITE_TOTAL{status="blocked_inferred_over_fact"}`）。报告 §1.1 有完整代码链。
4. R2 返修两点（有 dev 库只读证据）：F1 回填写收——184 direct_capture 行仅 1 行（user_registered）是用户陈述，机器行（chat_turn=164 等）落 OBSERVATION 不冒领 FACT；F3 epoch bump 原子化（单条 `UPDATE..RETURNING`），并发探针旧算法 [2,2]→2 丢增量复现、新算法 {2,3,4} 稳定。
残差处理：F2/F4/F5-F7 经主会话裁决登记 FIX-10 作 M-04 前置，随 `fa4e5837` 全部收口（wt474 扫陈确认 + 逐 F 项 file:line）。

**M-02（10fde918 + 1ae6a9e1）**——规则层 R1-R10+B2/B3 决策五出口（store/current_state/event/ignore/confirm）；R4 敏感推断→confirm、R5 一次性约束→event+bounded_scope（decay 压 7d）。评测：64 场景人工标注（store15/event12/current_state11/ignore14/confirm12），规则层独跑五类 P/R 全 1.0（阈值守卫固化进 `test_memory_storage_gate_eval.py`）。**语义层存在但 settings 默认 `SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED=False`**（本 worktree settings.py:1019 亲验）——生产决策面=规则层。FIX-41（P1）：E-04 审查发现 R10 对 inferred lane 是 fail-open STORE（敏感内容无确认直接入库）→ 改 net fail-closed + 四处词漏补 + marker 计数化。残留 FIX-15/FIX-44（OPEN，备忘型）：「每天/每周」不在稳定性词表、「见底/确诊」独立网词过宽（保守方向）。

**M-03（1ea854c9）**——预筛器挂 context_builder/context_pack/context_manager/context_sources 四处（本 worktree grep 亲验）；报告 §1 勘察出**真漏**：`list_recent_episodic` SQL 过滤漏 superseded 行、`due_at+7d` 过期承诺无消费者、wrong-user/revoked 候选无级守卫——修后「wrong-user/revoked/expired 在语义检索前为 0」有 1165L 单测覆盖（scope lattice + today-only 专项）。FIX-35 复盘披露：本卡守卫测试曾因 worktree 缺 app.gen 而不可收集、静默上线——后被 M-09 评测兜住，属流程教训非活性缺陷。

**M-04（fa4e5837）**——lane 档位唯一真源仍在 `ConflictResolverService.KNOWN_SOURCE_LANES/PRIORITY_BY_TIER`（M-01 契约只做认识论语义、不重复定义档位，测试钉两侧一致）；TEMPORAL/SCOPE/SOURCE/INFERENCE 四类仲裁 + resolution record + provenance；高信息增益且不确定→clarification（与 C-05 注入同源）。同卡收口 M-01 遗留：F2 生命周期过滤+重放幂等（apply_live_decision）、F4 第 5 破坏性入口（arbitrate_unresolved_conflict）补 epoch bump、F6 explicit 判据显式化（EXPLICIT_PREFERENCE_SOURCE_TYPES）、F7 守卫跳过计数指标。后续：FIX-06（P1）校准回执写入点从保留未登记 lane 迁至 working_memory lane（`a28a5b8c`），保留位作为 unknown-tier 红线 fixture 文档化。

**M-05（b9a48bdb）**——四检查固定求值序 relevance→necessity→repetition→sycophancy、首失败独占归因；**tighten-only**（只能降档不能复活）；`use_for_internal_decision` 与 `surface_to_user` 分面。OP-Bench 46 case（must_block 21/must_surface 24/known_limitation 1）规则层盲跑：过度个性化 0.0%（目标≤5%）。WIRING-1（`7c6cb867`）后生产逐轮可读降档率 **66.67%**——即经验/记忆 claims 三分之二被 selfcheck 收紧，这是设计内保守行为，但 V4 应知道「合法个性化的实际通过率」由这条闸主导。

**M-06（e56be400）**——投影契约：situation signature/intervention/mode/outcome/feedback/evidence count；单次结果低权、重复证据提升 strength、失败同样保留；**无 outcome 的 intervention 不标 effective**（契约测试钉）。**关键取舍（FIX-33，P2）**：交付时 `retrieve_context` 已建成并过 M-03/M-05 门测试，但未接任何 chat 路径——台账原话「F1 落地前经验记忆对用户零可见；记忆流宣告口径=机制闭环非用户可感知闭环」。WIRING-1（`7c6cb867`）补齐：stage34 单点注入 + context_sources 三 key golden + 降档率生产可读。上游 D-05 lifecycle 管线（11af43cd）供数，其 P3 批后清（`49d81fb2`）。

**M-07（0ea1e198，critical）**——统一管线 `apply_in_txn`：correction/revoke/supersede/bulk_revoke（+working_memory_forget）四动作全部「状态变更+审计行+epoch bump+`memory.invalidated` 事件」**同事务原子**（关闭 M-01 best-effort 缺口），提交后异步 DEL 派生缓存。勘察出的**复活主通道（真 bug）**：面板删偏好只撤 memory_preferences 链，而提示词装配真源是 live 表 user_preferences——删后每次编译永久复活；修法=链头删除同事务摘 live 键+version+1。读侧双 epoch 门（profile_context 缓存 + inline snapshot，缺 epoch/不一致/读失败一律 fail-closed）使「DEL 失败只剩 TTL 有界陈旧且被门拒绝」。幂等：FOR UPDATE + derive_status!=active 复查，重复删除收敛恰一次 bump/审计/事件。事件词表 33→34 登记 `memory.invalidated`（payload 零内容：只有 ids/action/epoch/reason_code）。实现中还抓到并修掉一个真实生产 bug：DEL 协程从未被 await（FakeRedis 暴露 RuntimeWarning）。本 worktree 亲验：管线在 memory_service 4 入口在场、profile_context_service epoch 门在场（:149/:421-441）。Q-05 红队（`4671173e`）后来用 43 场景对抗复测「轨迹 revoked 复活/错误本记忆复活」两类缺陷并当场修——失效承诺经受了独立对抗复核。

**M-08（cbd7e44d）**——路由面（本 worktree 亲验）：`GET /memory/provenance/items`、`/items/{kind}/{id}`、`/source`、`/scope`、`POST /update`（=supersede）、`POST /revoke`、`POST /why-this`（按 M-05 memory_use_receipt 结构查「为什么当时用这条」）。跨用户隔离与「source 不存在诚实 unknown」由 1171L API 测试承载（含变异 A/B/C 必红）。m08 迁移给 memory_goals 补 source_type（无回填，迁移头披露——FIX-39 OBS-2）。A-06（`d8a89bec`）的 Aurora 四动作回执把「拒绝 flywheel/M-01 supersede/scope pause/M-07 revoke」全部委托给本卡权威面，零新写路径——M-08 是 UI 治理动作的唯一后端权威。

**M-09（7d1eedd3）**——套件形态：82 case×10 Persona（每 persona 五维度全数覆盖、全 multi-session）、paired 无历史对照臂、三指标（invalid use/overpersonalization/valid-use precision+uplift）、**per-case 门禁不被平均掩盖**、变异自证非空洞。真模型探针（硬预算 25 次，qwen3.8-flash dashscope 真实 API，`has_key: true`）：5 关键 case×5 重复，**4/5 稳定 5/5 通过；P01-D1-evening_plan 0/5 失败**——根因=生产渲染器 format_user_context 不渲染偏好值（正确值在 M-01..M-07 全链正确，但最终 prompt 不可见）→ 登记 FIX-36（P1）。82 case 门禁合入时 RED（20 失败=FIX-35 supersede 反杀链签名）→ `3c2ca32c` 双修后 **82/82 全绿、REGISTERED_BUG_CASE_IDS 永久清空**（台账亲证+本 worktree 门禁实跑绿）。**残差（V3-FIX-503，本轮登记）**：FIX-36 注记「真模型复验由 E-05 下窗口补」至今未兑现——库内 stability report 仍是修前快照。

**M-10（90cda638 + bff5a816）**——接缝缺口盘点（报告 §0）五项全处置：G1 chat 回执无深链→`memory://<kind>/<id>` 开 U-03 why-this sheet（真实 API+真实纠正环）；G2 无入口→home/chat「查看完整理解」；G3 **诚实性红线**——U-03 删改同步链只失效 1 面，dashboard 理解快照/persona/透明档案/推断偏好 4 面删改后继续展示旧个性化→扩为五面级联失效；G4 置信百分比黑话两处清除（阈值与后端 `_confidence_label` 同口径 0.75/0.45）；G5 网关 `/memory` 纯代理零缓存（声明）。DEFERRED 的 6 测试用例（swap 门）由 CI 首跑兑现并暴露 1 个测试 fake 类型 bug（`bff5a816` 修后 7/7 绿）。**未做**：GJ08/GJ09 三端实机走查（无设备，headless 断言已尽；wt759 结论 ⚠「待人工裁」）；UnderstandingSnapshotCard「可信度 X%」文案残留（§8.4 自登记，features/experience 锁外）。

## 3. 设计决定与取舍（考古）

1. **派生而非复制**：五型/七态/scope 全部从既有列派生，唯一新列是 `epistemic_class`/`superseded_by_id`/epoch 三列——「不建第二库」落在 schema 层。CONFIRMED_PREFERENCE 甚至不加列（表成员资格即类型）。代价：状态是读时计算（O(列) 无聚合），收益：零回填漂移、迁移最小（m01a 全加法可逆，sqlite 重放验证）。
2. **保守分类学**：NULL epistemic_class 按 lane 保守派生（未知→HYPOTHESIS）；机器写行落 OBSERVATION 不冒领 FACT（R2 以 dev 库 184 行构成实证收紧）。 extending USER_STATEMENT_SOURCE_TYPES 被显式声明为产品决策。
3. **epoch = 廉价单调计数器 + 读侧 fail-closed 门**（E-05 version-key 先例）：DEL 是加速、门是保证。这个「双保险分层」是 M-07 最重要的架构决定——失效链不再依赖任何单点（DEL/事件/缓存版本）全中。
4. **评测先行抓真 bug**：M-09 不是「补测试」而是产品缺陷发现器——合入时 RED 20 case 直指 FIX-35（P1）、真模型探针 0/5 直指 FIX-36（P1）。两个 P1 都在 demo 前修掉（`3c2ca32c`）。V4 值得沿用「评测套件=门禁+缺陷猎场」双职能。
5. **语义层默认关**（M-02 gate / M-05 fast-model 降档 / X-02 allocation 同款哲学）：规则层是可复现、可审计的生产决策面；LLM 只在规则层标记的灰区残差上生效，且只能在可行集内选、带熔断/限频/超时。代价：生产语义兜底缺位（FIX-41 修复前 R10 fail-open 曾靠语义层当借口的假设不成立）；收益：CI 无 key 环境可复现全部判定。
6. **lane 注册表单一真源 + 保留位红线**：aurora_calibration_receipt 刻意不注册（FIX-06 裁决迁移写入点），作为「新写方必须先登记档位」的文档化 fixture，并有注册完备性守卫测试（test_all_app_source_lane_literals_are_registered）。
7. **快捷旗标与权威纠正环并存**：chat 快捷「不对」（lower_confidence）不 bump epoch 是 epistemic contract 有意设计（置信微调≠破坏性变更）；M-10 不改契约，改为让权威环（supersede/revoke）从深链可达。取舍记录在 M-10 报告 §8.2，V4 若要改须动 test_memory_epistemic_contract 钉。

## 4. 残差与 V4 注意点

**活性残差（有台账号的）**：
- FIX-15/44（M-02 词表打磨，OPEN 备忘）：「每天/每周」不稳、网词过宽——保守方向，随评测迭代。
- FIX-38（M-09 harness 打磨，OPEN 备忘）：to_row 丢 detail（eval_results 与报告口径差）、harness 语义门 fail-open 未显式钉死、.env 绝对路径硬编码、21/82 case 同构双写 supersede（偏好路径信号密度低）。
- FIX-39（M-08，OPEN 备忘）：revoke 端点旗标组合面 500（默认配置不可达）；m08 迁移无历史回填。
- V3-FIX-502/501（本轮登记，见 §5）。

**结构性事实（V4 设计输入）**：
1. **生产决策面=规则层**。存储门/使用自检/分配策略的语义层全部默认关；真模型证据集中在三处：M-09 探针（25 次）、E-04 五面探针（memory.gate/memory.extract 含注入对抗，收敛轮 15/15）、JOURNEY 真实驱动。**没有常态化的真模型记忆回归**（CI 无 key）——V4 若把语义层开进生产，需先建带 key 环境的常驻评测位。
2. **合法个性化的实际通过率由 M-05 主导**：生产逐轮降档率 66.67%（WIRING-1 起 metric 可读）。V4 调「个性化感知强度」时先看这条曲线，不要再造第二套过滤。
3. **失效链三层保证**（同事务 bump+事件 / 后置 DEL / 读侧 epoch 门）是 V4 可直接继承的范式；任何新派生面（新缓存/新快照）接入时必须：写侧钉 epoch、读侧 fail-closed。
4. **真源地图**：偏好链=memory_preferences（版本+replaced_by_id）；陈述=episodic_memories（lane+epistemic_class+superseded_by_id）；瞬态=working_memory（Redis 即真源）；live 提示词真源=user_preferences（删链头必须摘 live 键）。V4 新增任何「对用户的理解」面，先回答落在哪一格，禁止第四真源。
5. **M-10 之后的 UX 债**：三端实机走查（GJ08/GJ09）+ UnderstandingSnapshotCard「可信度 X%」残留。V4 做理解面时以 U-03/M-10 已建立的语言为准（定性层级词、零百分比黑话），并把两处残留一并清。

## 5. 本轮发现问题登记（号段复核后占用）

| 号 | 定性 | 一句话 | 证据硬点 |
|---|---|---|---|
| **V3-FIX-502** | 实现漂移（证据面） | M-06/M-08/M-09 与 X-03..X-09 卡级 REPORT/REVIEW_RECEIPT 从未入库，台账 FIX-33/38/39/28/29/32/40/42 引用死路径 | `git log --all --diff-filter=A` 0 命中；v3-output/ 现存目录清单亲验；wt759 以 commit message 签收核验故结论不受影响 |
| **V3-FIX-503** | 承诺未兑现 | FIX-36 修法注记「真模型复验由 E-05 下窗口补」，至今无复验产物；库内 stability report 仍是修前失败快照，会误导 V4 读者以为渲染缺口仍存活 | real_model_stability_report.json@HEAD P01-D1 0/5 在册；E-05 产物与 fleet notes 全扫无复验记录；代码面修复有 8 单测钉（风险低） |

（号段复核：500/501 在册 0 占用，仅 FIX-499 行内「备用号 500 未用」提及。）
