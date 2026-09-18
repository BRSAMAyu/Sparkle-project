# 08 跨层契约·安全横切 修复报告（round2 / G8 修复波）

- 修复员：G8 切片（R2-08-01 / 02 / 07 + 死路由处置 + 残留）
- 基线：`main@ca86bda8`（冻结，无 commit；全部改动在工作树）
- 日期：2026-09-18
- 对应复审报告：`round2/08-r2-contracts-security.md`
- 修复补丁：`round2/08-r2-fixes.patch`（`git add -A && git diff --cached` 产物）

## 0. 修复总览

| ID | 严重度 | 结论 | 证明方式 |
|---|---|---|---|
| R2-08-01 release_approvals 组越权 | P1 | 基线已含修复（复审误报）+ 回归测试固化 | 红(5 failed)→绿(10 passed) |
| R2-08-02 wrapper 转发旁路 | P1 | 已修复（接手前任半成品完成 fail-closed 收敛） | 红(12 failed)→绿(18 passed) |
| R2-08-07 achievementtype 枚举漂移 | P1 | 已修复（新迁移 r20807_20260918 收敛到引擎小写契约） | fresh 库 RED→GREEN + 可逆性 |
| R2-08-05 REST chat 三连死路由 | P2 | 已修复（引擎去双前缀，对齐网关注册） | 契约测试 3 passed |
| R2-08-10 event-bus/observability 死组 | P3 | 已删除（指向真身注释） | go build 通过，测试无新增失败（§7） |
| R2-08-03/04 plans+recommendations 簇 | P2 | 已修复（网关补 18+6 条注册，删 2 条死路由） | go build 通过，测试无新增失败（§7） |
| R2-08-06(a) dev 库 alembic 桩 | P2 | 已修复（t32_community_rooms→真头，alembic current 正常） | 直接 SQL 实证 |
| R2-08-06(b) sync-db 导出源 | P2 | 已修复（db-dump 改从一次性 fresh 迁移库导出） | 实测一次通过，schema.sql 收敛 |
| R2-08-08 sqlc 产物陈旧 | P3 | 已修复（重生成 + 2 个消费点随新产物机械更新，sqlc diff 归零） | go build/test 通过 |
| R2-08-09/11/12 及 90 条长尾 | P3 | 分类归档（§5，只修明确该修的） | — |

## 1. R2-08-01（P1）/release_approvals 组越权 —— 基线已修复，复审误报

真相：复审称"引擎四个 GET 端点无 superuser 依赖"。实测基线 ca86bda8 的
`backend/app/api/v1/release_approvals.py:22-26` APIRouter 构造已带路由级依赖
`dependencies=[Depends(get_current_active_superuser)]`，对全部端点（含 4 个只读 GET、PATCH、DELETE）统一
生效——reviewer 只核对了端点级参数，漏看了 router 级闸门。该文件自 initial commit（1722e6dc，含 F8 修复
squash）从未改动。网关侧仅 authMiddleware 无需加固——引擎侧 superuser 闸门即报告建议方案中更强的那个。
C-04 脉络改写：F8 的修复真实存在，F8 的 false-positive 判定反而正确；R2 对 C-04 的再翻转不成立。

红绿证明（`backend/tests/api/test_release_approvals_authz.py`，10 用例，前任起步遗留、本轮验证跑通）：
- RED：临时摘除 router 级依赖 → 普通用户直达 4 读端点+详情 → 5 failed（文件已还原，diff 为空）
- GREEN：恢复 → 10 passed（读端点普通用户 403；superuser 列表/摘要/页签 200、未命中详情 404）

## 2. R2-08-02（P1）LLMSecurityWrapper 转发旁路 —— 已修复

前任被击杀前完成 fail-closed 重写主体（362+/334-），本轮接手收尾：
1. 审查确认：安全面（chat/chat_with_tools/stream_chat）管线保留；六个显式审计旁路（reason/reason_json/
   chat_json/continue_with_tool_results/chat_stream_with_tools/generate_push_content）为真实方法，统一走
   _run_audited（配额[可识别身份时]+监控+用量记账）；豁免论证登记于模块 docstring（旁路输入为前序安全调用
   产物或系统内部推理，深度筛查由内层 LLMService 自有 hygiene 层承担，避免双重改写）。
2. 修复前任遗漏的行为回归：`app/orchestration/persistence_layer.py:40` 的
   getattr(llm_service,"default_model",None)（ChatMessage.model_name 元数据）会被 fail-closed 静默降级
   None → 将 default_model（内层只读 property）补入 _FORWARDABLE_META_ATTRS。
3. 调用面全量核对（grep 全仓 llm_service.<attr>）：chat×17、chat_json×6、continue_with_tool_results×5、
   chat_model×5、reason_json×4、chat_with_tools×4、reason×3、generate_push_content×2、
   chat_stream_with_tools×2、stream_chat×1、reason_model×1、model_key×1、default_model×1——全部在定义面。
   三个可疑命中均非调用面：plan_matching_service.py:290 .complete() 是注入 None 的死分支（构造点
   PlanMatchingService(active_db) 不传 llm_service）；weekly_synthesis_service.py:141,144 是注释；
   llm_router.py:1186 是 docstring。前任删除的 generate_embeddings 包装全仓零调用点。
4. 契约测试（tests/unit/test_llm_security_wrapper_forwarding.py，18 用例）：
   - RED（基线无界转发版 wrapper）：12 failed（旁路无配额预检/无超限阻断/未知属性不拦截）
   - GREEN：18 passed（fail-closed 拦截、4 元属性透传、5 旁路配额+记账、流式主路径开始前预检+完成后按产出
     记账、超限抛 QuotaExceededError 不记账、无身份旁路跳过配额正常透传）
   - 既有 tests/unit/test_llm_security_wrapper.py 2 用例保持绿。

## 3. R2-08-07（P1）achievementtype 枚举漂移 —— 已修复（新迁移）

方向取舍（PG 无法删枚举值，只能整型重建）：DB 收敛到引擎 11 值小写契约：
1. 引擎/API payload/achievement_seeds 全链按小写产消（dev 47 行存量全小写实测佐证），改大写会破坏移动端
   API 契约；2. 大写 10 值从未被引擎成功写入（fresh 写入即炸），无真实消费者；3. 同表 rarity 走 SQLAlchemy
   默认 member NAME（本模型成员名即大写），type 带 values_callable 显式产出小写——DB 大写是漏配
   values_callable 时代的化石。

新迁移 backend/alembic/versions/r20807_achievementtype_lowercase_20260918.py（down=0150e391736a，含
Migration Contract 头，可逆）：upgrade 建 11 值小写 achievementtype_new → USING lower(type::text) 转换
（假想大写存量行收敛、小写行 no-op）→ DROP 旧 TYPE → RENAME；downgrade 先收敛 planning 行到 milestone
→ 重建 10 值大写枚举 → upper() 转回。

fresh scratch 库红绿验证（独立建库/销毁，PG16）：
- RED（sr8_g8_red @ 旧头 0150e391736a）：引擎 SQLAlchemy 模型逐写 11 枚举值 → 11/11 FAIL
  （invalid input value for enum achievementtype）；sync_achievement_definitions FAIL；pg_enum=10 大写。
- GREEN（upgrade head）：11/11 OK；sync OK（created=39 skins=6 elements=37）；pg_enum=11 小写。
- 可逆性：downgrade -1 → 10 大写+planning 行收敛 MILESTONE；再 upgrade head → 11 小写。通过。
- 两个 scratch 库均已 DROP。

## 4. 死路由处置

### 4.1 REST chat 三连（R2-08-05，P2）—— 引擎去双前缀
真相：chat.py 路由内层再带 /chat，经 router.py:176 prefix="/chat" 叠成 /api/v1/chat/chat*；网关注册
/api/v1/chat|/chat/stream|/chat/confirm（/chat/task/:task_id 本就对齐）。全仓无 /api/v1/chat/chat 消费者，
产品主链路是 /ws/chat。修复：chat.py 三条路由改挂 ""、/stream、/confirm；更新
tests/contract/test_api_router_openapi_contract.py（断言新三路径存在、/api/v1/chat/chat 不存在）→ 3 passed。

### 4.2 event-bus/observability 整组死代理（R2-08-10，P3）—— 删除
引擎真身：/api/v1/admin/event-bus/*（event_bus_health.py，prefix=/admin）与 /api/v1/admin/observability/*
（observability.py），均被网关 /admin catch-all（RequireAdmin 双闸）覆盖。proxy_routes.go 删除
/api/v1/observability/* 组与 Missing-Proxy-Loop 的 {"/event-bus"} 项，留注释指向真身。Go 测试、mobile、
scripts 零依赖。

### 4.3 plans 簇（R2-08-03，P2）—— 网关补注册 18 条
GET /active（移动端 home_growth_provider 在调）、POST /phases/:phaseCardId/{complete,design-tasks,feedback,
feedback-gate/start,schedule/regenerate}（complete/feedback/schedule-regenerate 为移动端 api_endpoints.dart
既有常量）、POST /phases/feedback-gate/:sessionId/respond、POST /discovery/{start,:sessionId/turn,
:sessionId/finalize}、POST /compass/:artifactId/approve、GET /:id/compass/review、
POST /:id/phase-sketch/generate、POST /:id/phase-sketch/:artifactId/materialize、POST /:id/advance-phase、
GET /:id/planning-context、POST /:id/today、POST /:id/phases。（复审计 16，按引擎导出表重核 18，差异为
GET /active 与 POST /:id/phases 两条漏计。）

### 4.4 recommendations 簇（R2-08-04，P2）—— 双向错位纠正
删两条引擎不存在的死代理（bare GET /recommendations、POST /feedback，全仓零消费者；移动端
recommendationsFeedback* 常量实为 /community/recommendations/... 异路径），注册引擎真实 6 条
（collaborative/similar-users/similar-items/my-interactions/record-interaction/stats），与移动端
api_endpoints.dart 六常量一一对应。

网关验证：CGO_ENABLED=0 go build ./... 通过；wt8 树 go test ./... 除 1 个基线预存失败外全绿（基线复现
证明与逐包结果见 §7；此前报告 §4.5 所称"全绿"系误在主仓树上运行，本轮已在 wt8 树复验并更正）。

### 4.5 处置统计
| 类别 | 复审计数 | 本轮处置 |
|---|---|---|
| 整组死代理 | 2 组 | 2 删除 |
| 死网关代理路由（报告§2.2） | 22 | 修复 3（chat 三连）+删 2（recommendations 死路由）；其余 17 归档 §5 |
| 不可达引擎路由（报告§2.3） | 90（重核 92） | 恢复 24（plans 18+recommendations 6）；其余 66 归档 §5 |
| 引擎双前缀副本（R2-08-09） | 4 处 | chat/chat 已消除；health/health、achievements/achievements、ws/ws 归档 |

## 5. 残余不可达路由分类清单（66 条+死网关路由 17 条，P3 归档，本轮不改代码）

| 簇 | 条数 | 定性 | 建议 |
|---|---|---|---|
| /health/health/* | 11 | 引擎双前缀死副本；网关健康检查为 Go 原生 | 引擎去重复 include（R2-08-09）+守卫化 |
| /ws/*（devices×3、online、ws/ws/ack） | 5 | 引擎直连 WS 面，网关链路不需要 | by design（R1 C-06 同族） |
| /achievements/achievements/* 副本 | 3 | 双前缀副本 | 引擎去重 |
| /exam-sprint（dashboard、sprint-summary、diagnose×2） | 4 | 功能面缺口 | 产品确认后补注册 |
| /marketplace admin 面 | 4 | admin 面未开，保守姿态 | 维持或并入 /admin catch-all |
| /seed-libraries admin/items 面 | 5 | 功能面缺口 | 产品确认 |
| /galaxy 长尾 | 3 | P3 | 守卫化后批量清 |
| /community 长尾 | 20 | P3（aggregates/strategy-outcomes/knowledge-base 等） | 守卫化后批量清 |
| 单条散布（files/process、client-telemetry、calendar restore、background-tasks SSE、push/interaction、tasks subtasks 等） | 9 | catch-all 差一个形状 | 守卫化后批量清 |
| 死网关路由 17 条（报告§2.2 #4-7,10-22） | 17 | cards bare/PATCH/PUT 方法面、tasks reopen、cqrs/dlq/stats、community 私信×3+posts PATCH+groups 冗余×2、share adopt 旧别名、exam-sprint completion 405、galaxy nodes 405 | 删死路由/补注册/改方法三类归档；守卫化（网关↔引擎前缀自动比对扩进 BA guard） |

R2-08-12（迁移守卫对未提交改动失效）为 scripts/check_migration_contracts.py 加固项，按报告三层方案实施；
本轮新迁移已按现行 contract 头要求书写。

## 6. 残留任务：dev 库桩与 sync-db —— 已修复（含一处待办注记）

### 6.1 dev 库（sparkle）桩 —— 已修复
实测：桩 t32_community_rooms + 21 值污染枚举 + 47 行全小写成就数据。修复：
UPDATE alembic_version SET version_num='0150e391736a'（桩指向基线外 revision，alembic stamp 自身会先解析
当前版本而失败，故直接 SQL 修正）→ alembic upgrade head 真实执行 R2-08-07 迁移。
结果：alembic current = r20807_20260918 (head)；枚举 21→11 小写；47 行完好。

### 6.2 make sync-db 导出源 —— 已修复（Makefile，已实测闭环）
db-dump 不再从 dev 库 pg_dump（防污染枚举写回快照扩散到 sqlc）。新流程：建一次性库 sparkle_syncdb_fresh
→ alembic upgrade head → 导出 → 删库；升级失败不触碰 schema.sql（防半途覆盖）。新增 DB_DUMP_SCRATCH、
ALEMBIC_ABS（绝对路径覆盖兼容，修复原 ../$(ALEMBIC) 拼接对 `make db-dump ALEMBIC=...` 的破坏）。
实测（Docker 恢复后）：流程一次通过；重生成 diff 显示 tracked 快照除枚举 10 大写→11 小写外仅 pg_dump
版本头注释变化——快照自此成为迁移链的忠实派生物。
附带发现：R2-08-08 比复审认定的更陈旧——重生成后的 query.sql.go 还把 getChatHistory 的列展开补上了
chat_messages.metadata、CreateUser/CreateSocialUser 的 RETURNING 列序与新库对齐（旧产物脱胎于 dev 库
时代 schema）。sqlc 新签名影响 2 个消费点（GetPost 由 GetPostParams{} 改为直接传 pgtype.UUID，语义不变）：
internal/cqrs/projection/handlers.go、internal/worker/community_sync.go，已随工具产物机械更新。
`sqlc diff` 归零；`CGO_ENABLED=0 go build ./...` 通过。
（过程注记：会话中途宿主机 ENOSPC——外部并发进程拉取大镜像——曾致 Docker Desktop 崩溃，重启后完成本节与
§7 复验；遗留 scratch 库 sparkle_syncdb_fresh 已 DROP。）

## 7. 测试执行记录（资源纪律：pytest 按文件、Go 一次全量、DB 全 scratch 且清理）

| 命令 | 结果 |
|---|---|
| pytest tests/api/test_release_approvals_authz.py | 10 passed（红证时 5 failed，文件已还原） |
| pytest tests/unit/test_llm_security_wrapper.py | 2 passed |
| pytest tests/unit/test_llm_security_wrapper_forwarding.py | 18 passed（红证时 12 failed，已还原） |
| pytest tests/contract/test_api_router_openapi_contract.py | 3 passed |
| alembic heads（含新迁移） | 单头 r20807_20260918 |
| fresh RED（旧头+11 值探针+sync 重放） | 11/11 FAIL，sync FAIL，枚举 10 大写 |
| fresh GREEN（head+同探针） | 11/11 OK，sync created=39，枚举 11 小写 |
| 可逆性 downgrade -1 → upgrade head | 双向收敛正确 |
| dev 库修复后 current/枚举/行数 | r20807_20260918 / 11 小写 / 47 行 |
| CGO_ENABLED=0 go build ./... && go vet（wt8 树） | 通过 |
| CGO_ENABLED=0 go test ./...（wt8 树，JWT_SECRET 就绪） | 全部包 ok，唯 handler 包 FAIL=TestChatOrchestrator_QuotaIntegration——已用 git stash 在基线原树复现同一 panic（WS dial bad handshake 后 nil WriteJSON），系基线预存问题非本轮引入；config 包需 JWT_SECRET 环境变量（缺省时 FAIL，属环境项） |
| sqlc diff（重生成后） | 零漂移 |
| 环境事件 | 会话中途宿主 ENOSPC（外部并发进程拉大镜像）致 docker daemon 崩溃：2 个 scratch 库崩溃前已清、sparkle_syncdb_fresh 遗留（新流程首步幂等清理） |

## 8. 改动文件清单

backend/app/core/llm_security_wrapper.py                      R2-08-02 fail-closed 重写（前任主体+default_model 白名单）
backend/tests/unit/test_llm_security_wrapper_forwarding.py    R2-08-02 契约测试（新增）
backend/tests/api/test_release_approvals_authz.py             R2-08-01 回归证明（前任新增，本轮验证保留）
backend/app/api/v1/chat.py                                    R2-08-05 三条路由去内层 /chat
backend/tests/contract/test_api_router_openapi_contract.py    R2-08-05 契约断言更新
backend/gateway/internal/handler/proxy_routes.go              R2-08-10 两组删除 + R2-08-03/04 注册修复
backend/alembic/versions/r20807_achievementtype_lowercase_20260918.py  R2-08-07 新迁移（新增）
backend/gateway/internal/db/schema.sql                        R2-08-06/07/08 经新 db-dump 流程重生成（11 小写枚举）
backend/gateway/internal/db/models.go                         R2-08-08 db-sqlc 重生成（陈旧 PLANNING 常量消除，planning 落位）
backend/gateway/internal/db/query.sql.go                      db-sqlc 重生成（getChatHistory 补 metadata 列展开、列序对齐、GetPost 直参签名）
backend/gateway/internal/cqrs/projection/handlers.go          GetPost 新签名机械适配（语义不变）
backend/gateway/internal/worker/community_sync.go             GetPost 新签名机械适配（语义不变）
Makefile                                                      R2-08-06(b) db-dump 改 fresh 迁移库导出源
（backend/gateway/gen/ 为 gitignored 本地生成物，由主仓同 proto 契约复制用于构建验证，不入补丁）
docs/competition/2026-tmall-hackathon/系统审查/round2/08-r2-fixes.md    本报告
docs/competition/2026-tmall-hackathon/系统审查/round2/08-r2-fixes.patch 补丁
