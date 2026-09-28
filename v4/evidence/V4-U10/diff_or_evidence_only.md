# V4-U10 · diff_or_evidence_only

执行：wtU10（分支 `agent/v4/u10`，自 main@`331740ff` 开出）· 2026-09-28 · backend + gateway + mobile，零 HEAVY，零模型调用，UI 为移动端新页面（像素族纪律：新文件，不触碰 dashboard_screen/compact_status_bar/task_execution_screen 三个高危冲突面；五 Tab 路由合同只增不改）。2026-09-28 一审（R1，APPROVE_WITH_CONDITIONS）整改随本卡落，见 §7。

## 1. 一句话

**资料→错题→练习→检验是一条带目标上下文的连续旅程，不是四个各自空开的工具页**：目标详情页新增「学习旅程」入口，起飞前经 `LearningJourneyContext.fromLaunch` 守卫（空 id/标题即 ArgumentError——「从目标跳入无上下文空页」在起飞前失败）；旅程页（`/learning/journey` 只增路由）以目标上下文头 + 「继续当前动作」为主操作，装配视图由后端 `learning_journey.v2` 冻结契约给出：资料（来源badge=真实行 id+updated_at 版本+片段锚；解析状态从 stored_files 真实行映射——failed/unsupported **无文本键**、图片 OCR 不可用走手输替代、在途 pending）、错题（知识节点链路关联，最小暴露面不含 correct_answer）、检验（I07 脚手架证据门覆盖三个面：enter 写路径=用户显式选择且复习证据支持才推进，GET 读模型=未到检验段 `view.check` 不出题面，判分面=未到检验段提交一律 HOLD 拒判——R1 F-1 收口；判分在服务端 guide_json 权威上做确定性归一比对，**响应零答案材料**；防线口径如实：服务端出口探针为权威门，移动端 sanitize 红化为运行时逻辑、判分面允许表/bool 校验为 assert（debug/test 生效），release 由「correct is bool 三元 + 契约外键无渲染路径」运行时兜底——R1 N-6）。

## 2. 语义缺口清单（现状盘点结论，base @ 331740ff）

| # | 缺口 | 现状证据 | 卡面判据 |
|---|---|---|---|
| G1 | **从目标进工具丢上下文**：goal 详情只有编辑/刷新动作；`/errors`、`/library` 等工具路由不带目标参数，落地即空态搜索页 | `grep -rn "'/errors'" mobile/lib` 命中 7 处裸跳转，无 goal 上下文载体 | 「不会从目标跳入无上下文的工具空页」 |
| G2 | **检验答案红化只有模型上下文投影面**：I07 `redact_independent_check` 只接在 chat.py 投影；无判分入口、无移动端用户可读状态门 | `grep -rn "independent_check" backend/app` 仅 hybrid_policy + chat.py | 「答案不泄漏到检验用户可读状态」 |
| G3 | **检验无推进权与判分权威消费方**：`next_scaffold_step` 全仓零生产消费（仅 I07 自测）；guide_json 策略块 independent_check 无读取/判分面 | `grep -rn "next_scaffold_step" backend/app` 零生产命中 | 「统一…为目标上下文入口」「独立检验与示例严格隔离」 |
| G4 | **材料解析失败无诚实状态面**：documents 状态在 documents.py `_document_stage`（failed/queued/done），但无「失败→手输替代、不假装已识别」的旅程呈现面 | `document_cleaning_model.dart` status 含 failed，但无手输替代流；SCREEN_FAMILIES「OCR不支持时提供手输入；不假装图片已识别」无实现 | 「真实文件/图片失败无伪造解析，来源版本正确」 |

## 3. 实现面（真实路径）

| 文件 | 角色 |
|---|---|
| `backend/app/core/learning_journey.py` | **冻结契约**（`learning_journey.v2`，v1→v2 = R1 N-5 词表收口随冻结集更新流程 bump，v1 未外发）：旅程段封闭词表（materials/errors/practice/independent_check，后段与 I07 脚手架链 import 期断言对齐）；检验裁决 reason 封闭集 `CHECK_VERDICT_REASONS`（OK.check_graded_correct / OK.check_graded_incorrect / HOLD.evidence_not_supported / HOLD.scaffold_not_at_check / HOLD.check_authority_missing / HOLD.check_ungradeable，词表冻结钉死测试锚定）；`MaterialParseOutcome` 解析诚实构造不变量（failed/unsupported 带 text 即 ValueError「no fake parse」；pending 在途不宣称；manual=用户手输）；`JourneySourceRef` 来源引用（id+版本+片段锚，空版本拒绝构造）+ `ensure_source_version_current` 版本新鲜门（陈旧声明 SourceVersionMismatchError）；`request_independent_check`（消费 I07 `next_scaffold_step` 单点转移）；`grade_independent_check`（确定性归一判分，只认 I07 键集覆盖的 `answer` 单键——不发明等价答案新键；`accepted_answers` 属 V3 exam_sprint 域非本卡权威；权威不完整 → HOLD.check_ungradeable）；`assert_client_payload_clean`（出口探针，唯一实现=I07 `contains_independent_check_answer`） |
| `backend/app/services/learning_journey_service.py` | **服务面**：`build_goal_journey`（task 权威行→I07 策略块解析（降级回 example/full+警示）→materials=task_documents→stored_files（解析状态面**无 text 键**；图片 mime OCR 不可用→unsupported+手输）→errors=知识节点链路关联（简报无 correct_answer/user_answer/latest_analysis）→evidence_supported=关联错题 SM-2 review_count>0→check 面挂脚手架位置门：仅检验段携带 question，未到段不出题不误报警示→`redact_for_client`+出口探针）；`enter_check`（唯一写路径：I07 `apply_scaffold_decision` 写回 guide_json 策略块脚手架子键，零迁移；缺判分权威 → 词表内 HOLD.check_authority_missing）；`grade_check`（零写；挂 stage 位置门——未到检验段提交一律 HOLD.scaffold_not_at_check 拒判，缺权威 → HOLD.check_authority_missing）；跨用户=404 语义 reason（episode_resume house 先例） |
| `backend/app/api/v1/learning_journey.py` | REST 入口：`GET /learning-journey/tasks/{task_id}` + `POST .../check/enter` + `POST .../check/submit`（pydantic 校验、404 不泄露存在性） |
| `backend/app/api/v1/router.py` | +2 行：路由注册（只增） |
| `backend/gateway/internal/handler/proxy_routes.go` | +10 行：`/learning-journey` authed 组 registerREST（I01 episode-resume 同款直通） |
| `backend/gateway/internal/handler/proxy_routes_learning_journey_test.go` | 网关守卫：直通注册钉死 + 未认证请求不达后端 |
| `scripts/guards/check_rule_ba_routes_parity.py` | +1 行：GATEWAY_ONLY ledger 登记 learning-journey bare-group（episode-resume 同款先例，非绕门） |
| `mobile/lib/features/learning/`（新 feature，10 文件） | `data/learning_check_redaction.dart`（I07 键集 Dart 消费侧镜像，冻结 11 键钉死测试）；`data/learning_journey_models.dart`（载荷解析：解析诚实/来源可见断言、`LearningCheckQuestion.sanitize` 红化门检出即降级拒显——运行时逻辑；判分面允许表 + `correct is bool` 校验为 **assert（debug/test 生效，release 跳过）**，release 真实防线=服务端出口探针（权威）+ 运行时兜底（`correct is bool ? correct : null` 三元、契约外键无渲染路径），注释口径如实 R1 N-6）；`data/learning_journey_repository.dart`（Dio 仓库，判分面零本地缓存）；`presentation/`（旅程页/上下文头/来源badge/材料卡含手输替代/检验卡含判分呈现；provider 可注入假仓库；UI 只消费 enter 响应经 sanitize 的题面，不渲染 GET `view.checkQuestion`）；`learning_journey_routes.dart`（`/learning/journey` 只增路由，fromLaunch 守卫） |
| `mobile/lib/app/routes.dart` / `goal_detail_screen.dart` | +路由挂载（只增）；+目标详情「学习旅程」入口按钮（上下文起飞前校验） |
| `mobile/lib/l10n/app_en.arb` / `app_zh.arb` + 生成产物 | +31 键（旅程文案；gen-l10n 重生成） |
| `mobile/test/features/learning/`（3 文件） | 红化门键集钉死 + 模型断言 + 旅程页 widget 一正一反 + 证据采集（截图/语义按需落盘） |
| `v4/evidence/V4-U10/` | 五件套 + 2 张顶层截图 + 语义枚举 |

零迁移、零 proto 改动、零新表（判分权威复用 tasks.guide_json 策略块；来源版本复用既有行 updated_at；脚手架推进复用 I07 apply_scaffold_decision 既有子键）。

## 4. 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **未重建 V3**：错题档案/复习/文档清洗/词汇工具全部原样（旅程只做目标上下文装配与呈现，不改 V3 服务行为）；`_document_stage` 状态机未复制（服务面按同一真实行重新映射到本卡封闭词表，测试钉死映射关系）。
- **复用既有权威 7 处**：答案红化=I07 `redact_independent_check`/`contains_independent_check_answer`（不复制键集）；脚手架推进=I07 `next_scaffold_step`/`apply_scaffold_decision`（阶段永不回退）；判分权威=I07 策略块 independent_check 子结构（服务端 guide_json 原地）；脚手架状态解析=I07 `parse_policy_block`（降级语义不臆测）；REST 直通=I01 registerREST 模式；跨用户 404 语义=episode_resume/runs.py house 先例；宿主字体截图=U02TestFonts 先例。
- **新增仅 3 个后端文件 + 1 个网关组 + 1 个移动端 feature**。
- **diff 规模（R1 F-3 勘误）**：原记录「tracked 改动 10 文件 520+/92-」失实。R1 复核（对 `b5e04e57`）：22 文件 +3195、生产面 17 文件 +2281（注：该 22 文件口径 = 生产面 + 网关测试 + 移动测试，未含后端测试 3 文件 +657；全口径 25 文件 +3852）。本卡整改后对 `331740ff` 的终态全口径（`git diff 331740ff --numstat` 逐类可复核）：
  - 生产面 **17 文件 +2329**（backend app 4 + gateway proxy_routes.go + BA-ROUTES ledger 注释 + 移动 lib 11 含 l10n 外全部）；
  - 测试面 **8 文件 +1727**（后端 3 + 网关 1 + 移动 4）；
  - l10n **5 文件 +483**（arb 2 + 生成产物 3）；
  - 证据 **7 文本文件 +578** + 2 张截图（二进制）；tasks.json +4/-4（仅 U10 状态行）；
  - 合计 tracked 38 文本文件 + 2 二进制，**+5121/-96**。

## 5. 与验收逐条对照（可失败 = 每条一正一反）

1. **不会从目标跳入无上下文的工具空页**
   - 正：`test_build_journey_carries_goal_context_and_segments`（装配带 goal 上下文，attempt 段主操作=practice）；widget 测「目标头+继续动作+三段全渲染」；`test_get_journey_check_face_gated_by_scaffold_position` 正面（检验段 GET 照常带题面）+ API `test_check_face_and_grading_gated_until_check_stage` 正面（到段后 GET/submit 照常）。
   - 反：`test_enter_check_without_evidence_holds_and_persists_nothing`（无复习证据 → HOLD + 脚手架不推进 + 不出题）；`journey_segment_for_scaffold("garbage")=practice`（脏态绝不映射检验段）；`fromLaunch('')` 抛 ArgumentError（起飞前失败，落地即无上下文空页不可能发生）；出题证据门读模型/判分面（R1 F-1 反例钉死）：`test_get_journey_check_face_gated_by_scaffold_position`（example 段 GET `view.check` 为 None、不误报警示）、`test_submit_check_before_check_stage_rejected_without_verdict`（从未 enter 提交正确答案也拿不到 correct 裁决）、API `test_check_face_and_grading_gated_until_check_stage`（REST 面 GET 无 check + submit HOLD.scaffold_not_at_check）、`test_submit_check_missing_authority_at_check_stage_uses_authority_reason`（缺权威 → HOLD.check_authority_missing）。
2. **答案不泄漏到检验用户可读状态**
   - 正：`test_submit_check_grades_without_leaking_answer`（判分响应全文不含答案/解析文本，无 `answer` 键，出口探针过）；widget 测作答→判分→树中 `find.textContaining('压力决定摩擦力')` 为空。
   - 反：`assert_client_payload_clean` 对带答案节点载荷 raise（core）；`LearningCheckQuestion.sanitize` 检出剥除即 degraded 拒显 + widget 测「服务端泄漏载荷→降级文案，题面不可读」；判分面契约外字段（如顶层 `answer`）断言失败（assert=debug/test 生效，release 由运行时兜底+服务端探针承担，R1 N-6 口径）。
3. **真实文件/图片失败无伪造解析，来源版本正确**
   - 正：`test_materials_reflect_real_parse_status_and_source_version`（processed→parsed + 版本=updated_at ISO；failed 无文本+手输标记；图片→unsupported `ocr_unavailable_for_image`）；`MaterialParseOutcome(failed, text=...)` 构造即 ValueError；widget 测手输替代入口可见、保存后明示「不声称自动识别」。
   - 反：`ensure_source_version_current` 陈旧声明 → `SourceVersionMismatchError`；移动端状态面携带 `text` 键 → 断言失败；来源badge缺版本 → 构造断言失败。

## 6. UI 证据（顶层截图 + 语义 + 真实操作）

- `learning_journey_hub.png`：旅程页顶层（目标上下文头「力学单元巩固」+ 段徽标「练习」+ 「继续当前动作：先练习」；资料段=已解析 PDF（来源badge file-abc + 版本 2026-09-28T10:00:00）与图片「不支持」+ OCR 手输替代入口；错题段=关联错题（已复习 2 次 + 来源badge）；检验段=证据提示）。真实操作：点「继续当前动作」→ 服务端证据门放行 → 题面渲染。
- `learning_journey_check.png`：检验题面顶层（「独立解释：为什么滑动摩擦力与接触面积无关？」+ 「用自己的话作答」输入 + 提交答案）；判分只呈现对/错与泛化反馈，答案材料不在任何可读面。
- `learning_journey_semantics.txt`：Semantics/Tooltip 枚举（`当前目标：力学单元巩固`、来源badge tooltip 带真实版本等）。
- 采集方式：`LEARNING_JOURNEY_EVIDENCE_DIR=... flutter test test/features/learning/learning_journey_evidence_test.dart`（dpr=2、宿主 Hiragino 字体真实渲染、RepaintBoundary 顶层截图；常规跑不落盘、断言照常执行）。无模型调用，无价格面。

## 7. 一审整改记录（R1 = review_r1.md，APPROVE_WITH_CONDITIONS · 2026-09-28）

| # | 处置 | 落点 |
|---|---|---|
| F-1（唯一阻塞，采 a 案） | 出题证据门补齐三面：`build_goal_journey` 的 `check_view` 挂脚手架位置门（非 `independent_check` 段 → `view.check=None`，不出题不误报警示；到段后照常带题面）；`grade_check` 挂 stage 位置门（未到检验段提交一律 `HOLD.scaffold_not_at_check` 拒判，correct 裁决不可得）。移动端零消费 `view.checkQuestion`（UI 只渲染 enter 响应经 sanitize 的题面），零 UI 回归（31 新测 + 71 回归复跑全绿）。正反钉死：service `test_get_journey_check_face_gated_by_scaffold_position` / `test_submit_check_before_check_stage_rejected_without_verdict` + API `test_check_face_and_grading_gated_until_check_stage` | core 不改（门在服务层）；service +gate×2；tests +3 |
| F-2 | 移动回归计数勘误 75→71（router smoke 10 + deep-link 4 + shell 29 + error_book 28；原「18+57」中 18 实为 14），run_manifest/test_results/review_receipt 三处同步修正并注因 | 证据三件套 |
| F-3 | diff 规模勘误：原「10 文件 520+/92-」失实 → R1 复核 22 文件 +3195（生产面 17 +2281），本卡整改后终态全口径 38 文本 +2 二进制 +5121/-96（逐类分解见 §4） | diff doc §4 |
| F-4 | `grade_independent_check` docstring 修正：判分权威 = `answer` 单键（I07 键集成员）；`accepted_answers` 属 V3 exam_sprint 域（`schemas/exam_sprint.py`）非 I07 契约/本卡权威——与实现、与预登记①一致 | core docstring |
| N-5 | HOLD reason 词表收口（三处归拢 + 冻结集更新流程）：`HOLD.check_authority_missing` 入 `CHECK_VERDICT_REASONS`（原词表外字面量，enter_check 与 grade_check 缺权威分支共用，不再误用位置 reason）；ungradeable 落新成员 `HOLD.check_ungradeable`（原误挂 `OK.check_graded_incorrect` 判分语义）。词表 4→6 成员，按模块冻结纪律 bump `LEARNING_JOURNEY_SCHEMA_VERSION` v1→v2（v1 未外发；本 bump 即 R1 N-5 预授权的冻结集更新流程），词表冻结钉死测试锚定 | core 词表 + service reason + tests |
| N-6 | 判分面口径如实化：允许表/`correct is bool` 校验为 **assert（debug/test 生效，release 跳过）**；release 真实防线 = 服务端出口探针（权威）+ 运行时兜底（三元 + 契约外键无渲染路径）。Dart 注释、diff doc §1/§3、limitations#8 同步 | models.dart + 证据 |
| N-7 | 入口空标题失败形态：按 R1 裁决记录备查不改（goal 创建面标题必填，风险低） | 无代码改动 |

整改复跑（`SECRET_KEY=ci-test-key DATABASE_URL=sqlite://`）：后端本卡 34（core 19 + service 11 + api 4，+5 新测全一正一反）+ 合并回归 127（34 + I07 31 + I08 24 + D02 38）；网关 LearningJourney 2 + `go test ./...` 全绿；移动 learning 31 + 回归 71；守卫 88 rules 全绿；ruff/black/mypy（本卡 3 生产文件 0 error）/flutter analyze 零新增。
