# 考试系统 P1×5 修复记录（exam-p1-fixes）

- 基线：`6b0c02db`（wt6 工作树）；来源：`docs/competition/2026-tmall-hackathon/多端实测/exam-system-eval.md` P1 清单
- 验证方式：每项单测红绿 + 引擎(:8001)/gRPC(:50052)/网关(:8081) 备端口真链路 e2e（不触碰主仓在跑服务）

## P1-E1 网关错题本 gRPC 桥 401 → 修复

- 根因：`gateway/internal/handler/error_book.go` 的 `injectAuthContext` 只透传 `authorization`；引擎侧 `error_book_grpc_service._resolve_authenticated_user_id`（SEC-3）要求网关在 JWT 校验后注入 `user-id` metadata，request.user_id 无 metadata 即 401 `missing authentication metadata`。
- 修复：`injectAuthContext` 在 token 存在时同步追加 `user-id`（取自网关 JWT 校验后的 gin context `user_id`，与 agent client `injectMetadata` 同约定）。
- 红绿：
  - 红：`TestInjectAuthContext_SetsUserIDMetadata` 断言 outgoing metadata 含 `user-id` → 修复前 `[]string(nil)` FAIL。
  - 绿：修复后 PASS（含无 user_id 时不注入的负例 `TestInjectAuthContext_NoUserID_OmitsUserIDMetadata`）。
  - e2e（经 :8081 网关）：`POST /errors` 201、`GET /errors` 200、`GET /errors/stats` 200、`GET /errors/today-review` 200（原 4 连 401 清零）。

## P1-E3 update_galaxy=true 掌握度写库静默跳过 → 修复（动态建节点 + 映射 canonical 节点）

- 根因：`exam_sprint_diagnostic_service._persist_node_mastery` 对解析不到同名 `KnowledgeNode` 的 mastery update 直接 `continue`；galaxy 无同名节点时 7 条 update 全部丢弃且响应 `node_id=null`。
- 修复（选"动态建节点/映射 canonical"路线，语义正确且复用既有机制）：
  1. 解析顺序：请求自带 node_id → 同名节点（原逻辑）→ **sprint-pack canonical 节点**（curated alias 表 `_DIAG_TOPIC_NODE_ALIASES` + 全 pack `node_id` 后缀匹配，192 个后缀实测无冲突）→ 兜底按 slug 确定性建诊断主题节点（uuid5 命名空间 `sparkle:diagnostic-topic-node`）。
  2. 新增 `GalaxyService.ensure_sprint_node()` 公共封装（复用 `_resolve_mastery_node_id(create_missing=True)` 的建节点逻辑：pack 中文 label、TECH sector、`source_type=sprint_pack`）。
  3. 解析成功的真实 node_id 回写进响应 `node_mastery_updates[*].node_id`（原来是 null）。
- 红绿：
  - 红：`test_exam_sprint_diagnostic_persists_mastery_without_matching_galaxy_nodes`（空 galaxy，无同名节点）→ 修复前 `node_id is None` FAIL。
  - 绿：修复后 UserNodeStatus 落库 + 节点真实存在 + 响应带 node_id 全 PASS。
  - e2e：网关 generate→grade（数据结构 10 题全错）后，DB 出现 11 条 `source_type=sprint_pack` 的 canonical ds.* 节点（二叉排序树/堆排序/快速排序/折半查找…）且 `user_node_status.mastery_score` 已写；`GET /galaxy/graph` 中 11 个新节点全部出现（`user_status.mastery_score` 可见，样例「折半查找 mastery: 0.0」——全错作答得 0 分正确）。

## P1-E4 grading_payload 答案泄漏 + 选项文本作答判 0 → 修复（服务端判分态 + 文本兼容）

- 根因：generate 响应携带 grading_payload（含 correct_choice_index/accepted_answers）供无状态判分回传 → 直连消费者可自改答案作弊；`_score_choice_answer` 只认 a/b/c/d 与 0/1-based 数字，选项文本一律 0 分。
- 修复：
  1. `DiagnosticGenerateResponse` 移除 `grading_payload` 字段（结构性杜绝泄漏）；判分态改存服务端 `_DiagnosticSessionStore`（key=`exam_sprint:diagnostic:grading_session:<diagnostic_id>`，TTL 24h，redis 优先 + 进程内兜底）。
  2. `DiagnosticGradeRequest` 新增 `diagnostic_id`；grade 时服务端 session 权威（覆盖 days_left/pass_score/knowledge_nodes），客户端 grading_payload 仅作 legacy 兜底。
  3. `DiagnosticQuestionGrader` 新增 `choices`；`_score_choice_answer` 支持选项文本精确（归一化）匹配，命中错误选项显式 0 分，字母/索引契约不变。
- 红绿：
  - 红：`test_diagnose_generate_does_not_leak_answers_and_grade_uses_server_session` → 修复前响应含 grading_payload FAIL。
  - 绿：响应无任何答案键 + 全部选项文本作答经 diagnostic_id 判 100.0 PASS。
  - 既有 2 个测试（service happy path、API round-trip）迁移到新契约；API 层断言 `"grading_payload" not in generate_payload`。
  - e2e：经网关 generate 响应零答案键；同 session 下 `choices[1]` 文本作答 =60.0 与字母 `b` =60.0 完全一致（错项文本=0.0）。注：数字 `"2"`=70.0 属保留的 0/1-based 双读 legacy 契约（与文本无关）。

## P1-E2 种子场景「数据结构」422 → 修复（新增数据结构模板集）

- 根因：`_select_templates` 白名单 `_contains_network_subject` 仅放行计网；种子场景科目「数据结构」直接 422（覆盖领域不足）。
- 修复：
  1. 新增 `_DS_TEMPLATES`（13 题：8 单选 + 1 短答 + 概念/计算/过程追踪原型，7 领域：线性表/栈与队列/树与二叉树/图/查找与哈希/排序/复杂度分析；答案内容人工核验，正确项位置分散）+ `_DS_DEFAULT_NODES`（slug 与 `data_structures_algorithms` pack 节点后缀一致，galaxy 映射天然对齐）。
  2. 科目解析 `_resolve_subject_pack_key`：复用 `SprintPackRegistry.match_subject` + 别名前缀匹配（「数据结构期中」→ data_structures_algorithms）+ 计网旧白名单兜底；未支持科目给出明确 422 文案（当前支持：计算机网络、数据结构）。
  3. `_resolve_nodes`/`_select_templates`/archetypes 全部按 `_SUBJECT_TEMPLATE_SETS` 科目化。
- 红绿：
  - 红：`test_exam_sprint_diagnostic_supports_data_structures_subject` → 修复前 `ValueError: 知识节点覆盖不足…`（即实测 422 根因）FAIL。
  - 绿：数据结构 generate 10 题/7 领域/含短答、「数据结构期中」变体同过、grade 落库 canonical ds.* 节点全 PASS。e2e 经网关 generate=200（原 422）。

## P1-E5 移动端无诊断入口 → 修复（最小入口闭环落地）

- 修复（页面原先不存在，按任务要求建最小闭环）：
  1. `api_endpoints.dart`：`examSprintDiagnoseGenerate/Grade` 两条端点。
  2. `exam_sprint_models.dart`：`DiagnosticQuestion/GenerateResult/AnswerInput/BottleneckResult/GradeResult`（响应模型与服务端新契约一致，天然不含答案键）。
  3. `exam_sprint_repository.dart`：`generateDiagnostic/gradeDiagnostic`（grade 走 diagnostic_id，客户端只交作答文本 + confidence）。
  4. 新屏 `diagnostic_quiz_screen.dart`：加载→作答（单选 RadioGroup / 简答输入 + 把握三档）→交卷→结果页（估分/过考概率/补强策略/薄弱环节）→再测；UI 全部走 `mobile/lib/core/design` 令牌（DS.*、typo、SparklePageScaffold）。
  5. 路由 `PlanRoutes.examSprintDiagnose = '/exam-sprint/diagnose'`（subject query 参数）。
  6. 入口：`ExamSprintDashboardCard` 新增「开始诊断小测」按钮（`onStartDiagnostic`），`dashboard_screen` 两处调用点接线；l10n 新增 18 键（arb zh/en + `flutter gen-l10n` 再生成）。
- 红绿：新增 `diagnostic_quiz_screen_test.dart` 2 用例（加载→作答→交卷→结果断言 + 失败重试态）PASS；`exam_sprint_dashboard_card_test.dart`、`exam_sprint_closed_loop_test.dart` 15/15 PASS。
- 门禁：改动文件 `flutter analyze` 0 新增（新文件 0 issue；既有文件逐条与基线 diff，仅 l10n 生成文件格式化漂移）；`check_ui_design_tokens_ratchet.py` PASS（color=275/275, fontSize=727/727）。

## P2-Q1 sprint-summary 首日「用了 16 天」→ 顺带修复

- 根因：`days_used = (target_date - created_at) + 1` 把计划总长当已用天数。
- 修复：抽 `_compute_days_used`（已用=自创建日起含当天，封顶计划长度；无 target_date 退化为纯已用天数）。
- 红绿：`test_days_used_counts_elapsed_days_not_plan_length` / `..._without_target_date...` 红（AttributeError）→绿（1/5/封顶 15 全对）。

## e2e 环境与分域

- 自起实例：引擎 FastAPI :8001、gRPC :50052（`GRPC_PORT=50052`）、网关 :8081（`BACKEND_URL=127.0.0.1:8001 AGENT_ADDRESS=127.0.0.1:50052` + 主仓 backend/.env 导出、gateway/.env 拷贝、MinIO 凭证以 `docker exec sparkle_minio env` 实测值为准）；未 kill 主仓任何在跑进程。

## 新发现（记录不修，超出本波范围）

1. **错题复习端点在基线即回归（被 P1-E1 的 401 掩盖，桥修通后暴露）**：`POST /errors/{id}/review`（网关 gRPC 桥）500 `MissingGreenlet`；引擎直连 HTTP 同样 500（response 校验失败：`latest_analysis` 局部 JSONB 缺 `error_type` 等 6 必填）。两路径均调 `ErrorBookService.submit_review`，与本波 diff 无交集（diff 未触碰 error_book 引擎侧），基线 6b0c02db 复现。实测在 164a1cd6 运行进程上曾是 200，属该点之后的回归。建议单独开修复单（涉及响应模型容错 + gRPC 会话内懒加载排查）。
2. **mobile l10n 生成文件格式化漂移**：本机 Flutter 3.41.3 `flutter gen-l10n` 对既有生成文件做了一次性格式化（参数换行风格），diff 噪声 ~400 行，属一次性迁移，后续生成将稳定。
3. **游客 dashboard `active=false`（P1-E2 的另一半）**：种子计划缺 `source_metadata.exam_sprint_intake`，本波只修了 422 白名单侧；dashboard 激活判定维持现状（见 eval P1-E2 证据），建议后续接 intake 元数据。

## 测试汇总

- 后端：`pytest tests/unit/test_exam_sprint_diagnostic_service.py tests/unit/test_exam_sprint_diagnose_api.py tests/unit/test_exam_sprint_review_service.py` → 15 passed / 1 failed（`test_completed_sprint_auto_archives_without_post_exam_review`，基线即红，与本波无关）；galaxy 相关 26 passed。
- 网关：`go test ./internal/handler/ -run TestInjectAuthContext` → ok；`go build ./...`（CGO_ENABLED=0）ok。
- 移动：3 个定向测试文件 15/15 PASS；`flutter analyze` 0 新增；UI-TOKENS 守卫 PASS。
