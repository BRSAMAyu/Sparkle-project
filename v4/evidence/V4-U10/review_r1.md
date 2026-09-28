# V4-U10 一审 receipt（R1 = wtU10R1，未参与实现）

- 审查对象：分支 `agent/v4/u10` @ `b5e04e57`（自 main@`331740ff` 开出；merge-base 已核 = 331740ff）
- 审查方式：只读审查 + 审查者自有探针亲跑（临时 pytest 文件，跑完即删、未入 commit）+ 全量复跑
- 环境：`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`（worktree 无 .env，sqlite 口径，与 run_manifest 一致）
- 卡面：高风险 · 独立审查 2 位 · 本文件为第一审

## 总裁决：APPROVE_WITH_CONDITIONS

三条卡面验收全部成立（每条经审查者亲跑正反探针），**零答案泄漏红线成立**；但存在 1 项 CHALLENGE 级发现（F-1：出题证据门未覆盖 GET 读模型与判分面，与 diff 文档「才放行出题」声明不一致且 limitations 未披露）须处置后方可销账 DONE_REVIEWED——修代码（建议）或如实改口证据+登记 limitations 二选一；另有 3 项 N 级修正（F-2/F-3/F-4）与 2 项观察（N-5/N-6）应随处置一并落。

---

## 一、红线靶（逐条亲跑，非采信实现自测）

### 靶1 零答案泄漏（最重）——成立

- **出口探针亲跑**：构造含 I07 全部 11 个答案键（answer/correct_answer/expected_answer/reference_answer/model_answer/solution/solution_steps/answer_key/explanation/correct_option/correct）与答案文本/解析文本的 guide_json（stage=example），走 `build_goal_journey` 真实装配路径，对返回视图 `json.dumps` 序列化逐键断言：11 键无一出现、答案串（"压力决定摩擦力"）、解析串（"μN"/"约掉面积"）均不在序列化输出。**通过**。
- **移动端双保险反例亲跑（复跑测试）**：`flutter test test/features/learning` 31/31——含假仓库返回带答案原始载荷 → `LearningCheckQuestion.sanitize` 检出剥除即 degraded 拒显，widget 树 `find.textContaining('压力决定摩擦力')` findsNothing；判分面塞 `answer` 键 → 允许表断言红。
- **权威单源核**：`assert_client_payload_clean` 唯一实现 = I07 `contains_independent_check_answer`（core/learning_journey.py:371），键集不复制；Dart 镜像 11 键与 Python `INDEPENDENT_CHECK_ANSWER_KEYS`（hybrid_policy.py:126-140）逐键比对一致。

### 靶2 预登记②：顶层 correct 同名不同面——三重收口成立，碰撞面实证

- 亲跑：顶层（非 independent_check 节点）`{"correct": "<答案串>"}` 服务端探针**不** raise——碰撞面真实（探针只设防嵌套标记面）；嵌套面 `{"independent_check": true, "correct": ...}` 探针设防 ✓。
- 判分路径类型面：`grade_independent_check` → `to_client_payload` 的 `correct` 只可能是 `bool | None`（dataclass 类型 + 两分支构造），服务端无写出字符串 correct 的路径。
- 移动端三重收口：允许表（`_allowedVerdictKeys`）+ `correct is bool` 校验 + `containsIndependentCheckAnswer` 嵌套探针，models 测与 widget 测各一反例钉死。**收口足够**（服务端权威门 + 移动端纵深），接受 limitations#8 如实登记；I07 键集 bump 时此命名碰撞需契约复查——与登记一致。

### 靶3 I07 检验门衔接——enter 写路径成立；GET 读模型与判分面无门（→ F-1 CHALLENGE）

- **绕过尝试应拒（成立）**：亲跑 enter_check 三连——零错题零复习、review_count=0、review_count=None 均 `check_available=False` + `HOLD.evidence_not_supported` + 不出题 + `scaffold_persisted=False` + guide_json 不变；REST 面同测钉死（`"question" not in body["view"]`）。
- **判分实测（成立）**：归一比对（strip/casefold/空白折叠）正确/错误两判分亲跑，响应零答案材料，零模型调用（纯函数，无 LLM import）。
- **缺口（亲跑实证）**：① stage=example + 零证据时 `GET /learning-journey/tasks/{id}` 的 `view.check.question` **仍返回题面**（build_goal_journey 无脚手架位置/证据条件）；② 从未 enter、stage=example 时 `POST check/submit` **仍判分**（可拿到 correct=true）——`grade_check` 无 stage 校验。移动端 UI 不渲染 `view.checkQuestion`（渲染面只消费 enter 响应经 sanitize 的题面），故用户可见行为与声明一致；但 API 契约面松于 UI 行为、与 diff 文档「用户显式选择且复习证据支持才放行出题」直接冲突，且 `LearningJourneyView.fromJson` 也解析了 checkQuestion（latent 消费面）。定性：**非泄漏红线**（题面≠答案材料；I07 自身的 chat 投影同样保留 question），是门声明 vs 实现的一致性缺口。处置建议见 F-1。

### 靶4 预登记③：review_count>0 证据口径——放水面实测存在，登记如实

- 亲跑：review_count 0 / None / （负数语义同 0）→ HOLD；review_count=1 且 mastery_level=0.0 → **放行推进**。即「练一次即可推进检验」成立，与 limitations#3 登记一致。
- 裁决：接受为 MVP 口径——确定性、可审计、零新表；I07「用户选择且证据支持」的立法本意形式化下限。步级/投入证据增强归后续卡（登记已载）。不阻塞。

### 靶5 预登记①④：accepted_answers 张力 + 解析诚实边界——登记如实

- ①：`_extract_expected_answers` 只读 `answer` 单键；亲跑构造 `{"accepted_answers": [...]}` 判分权威 → `graded=False, correct=None`（不认发明键）；同时亲跑证明 `accepted_answers` 在 I07 键集外 → 泄漏探针对其**失明**（若未来用它存答案即成泄漏面）——登记的张力真实且方向正确（变体键必须走 I07 键集扩展同一契约变更）。仓内 `accepted_answers` 属 V3 exam_sprint 域（schemas/exam_sprint.py:361），非 I07 契约成员。**但** `grade_independent_check` docstring（core/learning_journey.py:343）误称判分权威含 `accepted_answers`，与实现、与预登记①自相矛盾——见 F-4，须修。
- ④：解析诚实红线在数据构造层（`MaterialParseOutcome.__post_init__` ValueError "no fake parse"）+ 服务面结构无 text 键 + 移动端断言三道。亲跑「failed 但部分文本可用」构造 → ValueError 拒绝；`_stored_file_parse_face("failed",...)` 返回面无 text 键。**边界裁决接受**：部分文本=伪造解析最常见来源，宁严勿假；且 pending/manual 两个合法出口（在途等真实结果、手输替代）保留了非伪造的文本通路，红线没有堵死诚实场景。

### 靶6 预登记⑤：Dart 镜像漂移——钉死测试**不是**漂移报警器；裁决：登记 F 线扫尾卡

- 实证盲区：钉死测试断言的是 Dart 集自身 == 硬编码 11 键。服务端 bump 至 12 键而 Dart 未跟时，Dart 测试仍 11==11 **绿**——它冻结本地面，但对服务端变更无警报（测试注释「必须同步跟随」是流程约定非机制）。
- 裁决建议：**登记 F 线扫尾卡补最小跨语言 parity 守卫**（不在本卡补）：解析 `hybrid_policy.py` 的 `INDEPENDENT_CHECK_ANSWER_KEYS` ↔ `learning_check_redaction.dart` 的 `kIndependentCheckAnswerKeys` 做值集 diff + kind/flag 同词校验，挂 `scripts/guards`（ENUM-PARITY 先例同款机制，单族成本小）。理由：v1 冻结 + contract-owner bump 已有审查门 + 服务端才是红化权威（移动端为纵深防御侧），不阻塞本卡；但必须挂账——本 receipt 即挂账凭证，后续键集 bump 卡若未带 parity 守卫应被审查拦下。

### 靶7 红线面——全部成立

- **五 Tab 只增不改**：routes.dart diff 仅 +import 与 +2 行挂载，且挂载点在 `StatefulShellBranch` 之外的根级 feature 路由区（与 ToolsRoutes 等同区）；`/learning/journey` 新路由核（learning_journey_routes.dart，fromLaunch 守卫在 pageBuilder 内）；router smoke 10 + deep-link 4 + shell 29 复跑全绿。
- **RF-06 冲突面零触碰**：dashboard_screen / compact_status_bar / task_execution_screen 三文件不在 diff（对 331740ff 全量核对）。
- **classic 零差量**：tasks.json 仅 U10 状态行（PENDING→in_progress/REVIEW_READY/PENDING_REVIEW）+ 文件尾换行；V3 证据目录零删除（main..HEAD 出现的 D04/F03/I04 证据「删除」是 main 前进伪影，对 331740ff 真实 diff 无任何删除）；error_book/shell 回归全绿。

### 靶8 复跑（全部亲跑）

| 套件 | 声称 | 实测 | 判 |
|---|---|---|---|
| 后端合并单命令（29 新 + I07 31 + I08 24 + D02 38） | 122 passed | **122 passed**（67.95s） | ✓（分项 18+8+3=29、31/24/38 逐一 collect 核实） |
| go test（LearningJourney -run + ./... 全量） | 2 测 + 全绿 | **ok + 全包 ok** | ✓ |
| flutter test test/features/learning | 31 | **31** | ✓ |
| 移动回归 router smoke+deep-link + shell + error_book | **75**（18+57） | **71**（10+4+29+28；57 对，18 实为 14） | ✗ 见 F-2 |
| flutter analyze（4 目标） | No issues | **No issues found** | ✓ |
| 治理守卫 | 88 rules 全过 | **all rule guards passed (88 rules)**；BA-ROUTES 单跑 `OK: 621 ↔ 1015, 169 ledgered`（+1 行生效） | ✓ |

### 靶9 limitations 9 条如实性——9/9 与实现一致，无伪造；1 项缺漏

逐条核：#1 单键判分（实现属实，但 docstring 反证见 F-4）、#2 揭示面未做（判分反馈确为封闭短语，payload 仅 graded/correct/reason/feedback）、#3 证据口径（探针证实）、#4 端到端真机未做（gateway bare-group 登记属实；NOT_RUN 口径如实、未伪造联调）、#5 知识节点链路（代码属实）、#6 badge 跳转呈现面（onOpenFragment 未接深链属实）、#7 宿主渲染非真机（U02TestFonts 先例属实）、#8 correct 双语义（探针证实）、#9 V3 未触碰（diff 属实）。
**缺漏**：F-1 的「GET 视图无门带题 + 判分无位置门」未在 limitations 披露，而 diff 文档作了强于实现的无 Qualification 声明——这是唯一需要补披露/修正的点。

---

## 二、发现清单

### F-1（CHALLENGE，处置后可销账）出题证据门未覆盖 GET 读模型与判分面
- 实证：探针（见靶3）——GET 视图任意阶段带 `check.question`；submit 无 enter/无 stage 校验即判分。
- 处置二选一：
  - **(a) 建议**：`build_goal_journey` 的 `check_view` 挂脚手架位置门（非 independent_check 段 → `None`，UI 已有证据提示面不受影响，移动端不消费 `view.checkQuestion`，预计零 UI 回归）；`grade_check` 加 `scaffold.stage == independent_check` 校验（否则 `HOLD.scaffold_not_at_check`——该 reason 本就在封闭集且语义正合此用）。补两反例测试钉死。
  - (b) 若坚持现行为：limitations 增补 + diff 文档「才放行出题」改写为「门覆盖 enter 写路径与 enter 响应；GET 视图预告题面、submit 不设位置门」，并移除 `LearningJourneyView.fromJson` 对 checkQuestion 的解析（消灭 latent 面）。
- 复核要求：属高风险卡面改动，(a) 之修正 delta 需复审确认（可为本 R1 复核，轻量）。

### F-2（N，必修）移动回归计数失实
- run_manifest.json / test_results.json / review_receipt.json 三处声称「75 passed（路由 18 + 57）」；实测 **71**（smoke 10 + deep-link 4 + shell 29 + error_book 28）。57 部分准确，18 实为 14。全绿是真的，数字必须修成 71 并注因。

### F-3（N，必修）diff 规模声明失实
- diff_or_evidence_only.md §4「tracked 改动 10 文件 520+/92-」；实际对 331740ff：含测试 22 文件 +3195，生产面 17 文件 +2281（另有 l10n 生成产物与 evidence）。不影响结论，证据口径须修。

### F-4（N，必修）`grade_independent_check` docstring 漂移
- core/learning_journey.py:343 声称判分权威含 `accepted_answers`——实现只读 `answer`，且与预登记①「不发明键」直接矛盾。一行修正。

### N-5（observation）HOLD/verdict reason 口径漂移三处
- (a) `enter_check` 无判分权威时 `HOLD.check_authority_missing` 不在 `CHECK_VERDICT_REASONS` 封闭集（服务层词表外造 reason）；(b) `grade_check` 无判分权威复用 `HOLD.scaffold_not_at_check`（缺权威≠位置不对，语义错位；若按 F-1(a) 加位置门，此分支应改词表内新 reason 或并入封闭集 bump）；(c) ungradeable 判分 reason 落 `OK.check_graded_incorrect`（`graded=False` 却挂 OK.* 判分语义，封闭集缺 ungradeable 成员）。不影响安全性，建议随 F-1 一并词表收口。

### N-6（observation）移动端「双保险」的 release 口径
- `LearningCheckVerdict` 允许表/bool 校验为 `assert`（debug/test 生效，release 跳过）；运行时安全仍由 `correct is bool ? correct : null` 三元与「契约外键无渲染路径」兜底，`sanitize` 降级为真实运行时逻辑。即 release 下生效门 = 服务端出口探针（权威）+ 移动端运行时兜底，建议证据文案如实区分。

### N-7（observation）入口空标题的失败形态
- `fromLaunch` 在 pageBuilder 内抛 ArgumentError（设计即「起飞前失败」）；若存在空标题目标将得路由构建错误屏而非友好拒绝。当前 goal 创建面标题必填，风险低，记录备查。

---

## 三、预登记 7 条逐判（对应 review_receipt.json review_focus_suggestions）

| # | 预登记 | 逐判 |
|---|---|---|
| 1 | 判分单键 vs 教学变体张力（limitations#1） | **接受**。探针证实 accepted_answers 不被认、探针对其失明（张力真实、登记方向正确）；变体键必须与 I07 键集扩展同一契约变更走审——维持。但 F-4 docstring 反称权威含该键，须修，否则登记不如实。 |
| 2 | 顶层 correct 同名不同面三重收口（limitations#8） | **收口足够**。探针：判分路径类型面只出 bool/None；嵌套面探针设防；顶层碰撞面服务端探针失明但无写出路径，移动端允许表+bool+嵌套探针收口。键集 bump 需契约复查——登记如实，维持。 |
| 3 | review_count>0 证据口径（limitations#3） | **接受为 MVP 口径**。放水面实测（≥1 次即放行，不问 mastery/新鲜度）真实但已登记；确定性可审计；步级证据归后续卡。不阻塞。 |
| 4 | 解析诚实红线位置 | **位置正确，接受**。构造期不变量强于渲染层隐藏；「部分文本可用」场景确被挡（探针证实），pending/manual 两个诚实通路保留，宁严勿假裁决成立。 |
| 5 | 跨用户/所有权语义复用 episode_resume 先例 | **核实通过**。`_load_task` 与 episode_resume_service.py:137-149 逐点一致（同 deleted_at 过滤、同 object_not_found/cross_object_access 词、同 warning log），API 404 面同款且未删 TaskService/下游归属校验；enter/submit 两入口跨用户 404 亲跑成立。 |
| 6 | Dart 镜像漂移：钉死测试 vs parity 守卫 | **裁决：登记 F 线扫尾卡补最小 parity 守卫，不在本卡补**。钉死测试对服务端 bump 无警报（盲区实证）；ENUM-PARITY 先例机制现成、单族成本低；不阻塞理由见靶6。本 receipt 为挂账凭证。 |
| 7 | BA-ROUTES +1 行 + enter_check 唯一写路径回滚 | **均接受**。ledger 行与 episode-resume/inventory 同款 registerREST bare-group 口径，guard OK；写路径零迁移、写回 I07 权威子键（无新数据格式，向后兼容），回滚=独立 commit（满足卡面；无新开关可加——未引入新基础设施，「既有开关」要求在此退化为主commit回滚，判定满足）。 |

## 四、integration SHA 复验注记

分支自 main@`331740ff` 开出（merge-base 已核）；审查时点 main 已前进至 `f9729cc5`（D04 销账）。本 receipt 以 331740ff 基线 + b5e04e57 出具；集成时须对最新集成 SHA 重跑合并面（后端 122 合并 + 移动 71/31 + 守卫 88）后再销账。

## 五、裁决汇总

- 卡面三验收：**全部成立**（亲跑正反探针）。
- 红线（零答案泄漏）：**成立**。
- F-1 处置前不得销账 DONE_REVIEWED；F-2/F-3/F-4 随处置一并修正。
- 预登记 7 条：5 接受维持、1 收口成立维持（②）、1 裁决登记 F 线卡（⑤）；跨用户先例核实通过。
- 复跑：后端/网关/移动新测/analyze/守卫全绿；移动回归数字 71（修正后仍全绿）。

—— wtU10R1 · 2026-09-28
