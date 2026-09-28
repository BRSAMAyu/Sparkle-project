# V4-U10 · diff_or_evidence_only

执行：wtU10（分支 `agent/v4/u10`，自 main@`331740ff` 开出）· 2026-09-28 · backend + gateway + mobile，零 HEAVY，零模型调用，UI 为移动端新页面（像素族纪律：新文件，不触碰 dashboard_screen/compact_status_bar/task_execution_screen 三个高危冲突面；五 Tab 路由合同只增不改）。

## 1. 一句话

**资料→错题→练习→检验是一条带目标上下文的连续旅程，不是四个各自空开的工具页**：目标详情页新增「学习旅程」入口，起飞前经 `LearningJourneyContext.fromLaunch` 守卫（空 id/标题即 ArgumentError——「从目标跳入无上下文空页」在起飞前失败）；旅程页（`/learning/journey` 只增路由）以目标上下文头 + 「继续当前动作」为主操作，装配视图由后端 `learning_journey.v1` 冻结契约给出：资料（来源badge=真实行 id+updated_at 版本+片段锚；解析状态从 stored_files 真实行映射——failed/unsupported **无文本键**、图片 OCR 不可用走手输替代、在途 pending）、错题（知识节点链路关联，最小暴露面不含 correct_answer）、检验（I07 脚手架证据门：用户显式选择且复习证据支持才放行出题；判分在服务端 guide_json 权威上做确定性归一比对，**响应零答案材料**，出口探针 + 移动端红化门/允许表双保险）。

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
| `backend/app/core/learning_journey.py` | **冻结契约**（`learning_journey.v1`）：旅程段封闭词表（materials/errors/practice/independent_check，后段与 I07 脚手架链 import 期断言对齐）；`MaterialParseOutcome` 解析诚实构造不变量（failed/unsupported 带 text 即 ValueError「no fake parse」；pending 在途不宣称；manual=用户手输）；`JourneySourceRef` 来源引用（id+版本+片段锚，空版本拒绝构造）+ `ensure_source_version_current` 版本新鲜门（陈旧声明 SourceVersionMismatchError）；`request_independent_check`（消费 I07 `next_scaffold_step` 单点转移）；`grade_independent_check`（确定性归一判分，只认 I07 键集覆盖的 `answer` 键——不发明等价答案新键）；`assert_client_payload_clean`（出口探针，唯一实现=I07 `contains_independent_check_answer`） |
| `backend/app/services/learning_journey_service.py` | **服务面**：`build_goal_journey`（task 权威行→I07 策略块解析（降级回 example/full+警示）→materials=task_documents→stored_files（解析状态面**无 text 键**；图片 mime OCR 不可用→unsupported+手输）→errors=知识节点链路关联（简报无 correct_answer/user_answer/latest_analysis）→evidence_supported=关联错题 SM-2 review_count>0→check 只抽 question 字段→`redact_for_client`+出口探针）；`enter_check`（唯一写路径：I07 `apply_scaffold_decision` 写回 guide_json 策略块脚手架子键，零迁移）；`grade_check`（零写，判分权威原地留在服务端）；跨用户=404 语义 reason（episode_resume house 先例） |
| `backend/app/api/v1/learning_journey.py` | REST 入口：`GET /learning-journey/tasks/{task_id}` + `POST .../check/enter` + `POST .../check/submit`（pydantic 校验、404 不泄露存在性） |
| `backend/app/api/v1/router.py` | +2 行：路由注册（只增） |
| `backend/gateway/internal/handler/proxy_routes.go` | +10 行：`/learning-journey` authed 组 registerREST（I01 episode-resume 同款直通） |
| `backend/gateway/internal/handler/proxy_routes_learning_journey_test.go` | 网关守卫：直通注册钉死 + 未认证请求不达后端 |
| `scripts/guards/check_rule_ba_routes_parity.py` | +1 行：GATEWAY_ONLY ledger 登记 learning-journey bare-group（episode-resume 同款先例，非绕门） |
| `mobile/lib/features/learning/`（新 feature，10 文件） | `data/learning_check_redaction.dart`（I07 键集 Dart 消费侧镜像，冻结 11 键钉死测试）；`data/learning_journey_models.dart`（载荷解析：解析诚实/来源可见断言、`LearningCheckQuestion.sanitize` 红化门检出即降级拒显、判分面允许表校验）；`data/learning_journey_repository.dart`（Dio 仓库，判分面零本地缓存）；`presentation/`（旅程页/上下文头/来源badge/材料卡含手输替代/检验卡含判分呈现；provider 可注入假仓库）；`learning_journey_routes.dart`（`/learning/journey` 只增路由，fromLaunch 守卫） |
| `mobile/lib/app/routes.dart` / `goal_detail_screen.dart` | +路由挂载（只增）；+目标详情「学习旅程」入口按钮（上下文起飞前校验） |
| `mobile/lib/l10n/app_en.arb` / `app_zh.arb` + 生成产物 | +31 键（旅程文案；gen-l10n 重生成） |
| `mobile/test/features/learning/`（3 文件） | 红化门键集钉死 + 模型断言 + 旅程页 widget 一正一反 + 证据采集（截图/语义按需落盘） |
| `v4/evidence/V4-U10/` | 五件套 + 2 张顶层截图 + 语义枚举 |

零迁移、零 proto 改动、零新表（判分权威复用 tasks.guide_json 策略块；来源版本复用既有行 updated_at；脚手架推进复用 I07 apply_scaffold_decision 既有子键）。

## 4. 差量判定（卡「当前仓库已满足本卡行为时做差量举证，不重写」）

- **未重建 V3**：错题档案/复习/文档清洗/词汇工具全部原样（旅程只做目标上下文装配与呈现，不改 V3 服务行为）；`_document_stage` 状态机未复制（服务面按同一真实行重新映射到本卡封闭词表，测试钉死映射关系）。
- **复用既有权威 7 处**：答案红化=I07 `redact_independent_check`/`contains_independent_check_answer`（不复制键集）；脚手架推进=I07 `next_scaffold_step`/`apply_scaffold_decision`（阶段永不回退）；判分权威=I07 策略块 independent_check 子结构（服务端 guide_json 原地）；脚手架状态解析=I07 `parse_policy_block`（降级语义不臆测）；REST 直通=I01 registerREST 模式；跨用户 404 语义=episode_resume/runs.py house 先例；宿主字体截图=U02TestFonts 先例。
- **新增仅 3 个后端文件 + 1 个网关组 + 1 个移动端 feature**（tracked 改动 10 文件 520+/92-，其中 l10n 生成产物占大头）。

## 5. 与验收逐条对照（可失败 = 每条一正一反）

1. **不会从目标跳入无上下文的工具空页**
   - 正：`test_build_journey_carries_goal_context_and_segments`（装配带 goal 上下文，attempt 段主操作=practice）；widget 测「目标头+继续动作+三段全渲染」。
   - 反：`test_enter_check_without_evidence_holds_and_persists_nothing`（无复习证据 → HOLD + 脚手架不推进 + 不出题）；`journey_segment_for_scaffold("garbage")=practice`（脏态绝不映射检验段）；`fromLaunch('')` 抛 ArgumentError（起飞前失败，落地即无上下文空页不可能发生）。
2. **答案不泄漏到检验用户可读状态**
   - 正：`test_submit_check_grades_without_leaking_answer`（判分响应全文不含答案/解析文本，无 `answer` 键，出口探针过）；widget 测作答→判分→树中 `find.textContaining('压力决定摩擦力')` 为空。
   - 反：`assert_client_payload_clean` 对带答案节点载荷 raise（core）；`LearningCheckQuestion.sanitize` 检出剥除即 degraded 拒显 + widget 测「服务端泄漏载荷→降级文案，题面不可读」；判分面契约外字段（如顶层 `answer`）断言失败。
3. **真实文件/图片失败无伪造解析，来源版本正确**
   - 正：`test_materials_reflect_real_parse_status_and_source_version`（processed→parsed + 版本=updated_at ISO；failed 无文本+手输标记；图片→unsupported `ocr_unavailable_for_image`）；`MaterialParseOutcome(failed, text=...)` 构造即 ValueError；widget 测手输替代入口可见、保存后明示「不声称自动识别」。
   - 反：`ensure_source_version_current` 陈旧声明 → `SourceVersionMismatchError`；移动端状态面携带 `text` 键 → 断言失败；来源badge缺版本 → 构造断言失败。

## 6. UI 证据（顶层截图 + 语义 + 真实操作）

- `learning_journey_hub.png`：旅程页顶层（目标上下文头「力学单元巩固」+ 段徽标「练习」+ 「继续当前动作：先练习」；资料段=已解析 PDF（来源badge file-abc + 版本 2026-09-28T10:00:00）与图片「不支持」+ OCR 手输替代入口；错题段=关联错题（已复习 2 次 + 来源badge）；检验段=证据提示）。真实操作：点「继续当前动作」→ 服务端证据门放行 → 题面渲染。
- `learning_journey_check.png`：检验题面顶层（「独立解释：为什么滑动摩擦力与接触面积无关？」+ 「用自己的话作答」输入 + 提交答案）；判分只呈现对/错与泛化反馈，答案材料不在任何可读面。
- `learning_journey_semantics.txt`：Semantics/Tooltip 枚举（`当前目标：力学单元巩固`、来源badge tooltip 带真实版本等）。
- 采集方式：`LEARNING_JOURNEY_EVIDENCE_DIR=... flutter test test/features/learning/learning_journey_evidence_test.dart`（dpr=2、宿主 Hiragino 字体真实渲染、RepaintBoundary 顶层截图；常规跑不落盘、断言照常执行）。无模型调用，无价格面。
