# 已知代码债务台账（Known Code Debt Ledger）

> **文档定位**：2026-09-08 全仓只读审计产出的**当前有效**债务清单，供后续清理战役排期。与 [technical_debt_register_2026-03-22](./technical_debt_register_2026-03-22.md)（三月登记册）互补：该册为历史基线，本台账为现行状态。
> **维护规则**：处理掉一项就划掉/移除并注明日期；新发现的显著债务登记进来。排序 = 建议处理优先级。

---

## ✅ 已处理

| 日期 | 项目 | 处置 |
|---|---|---|
| 2026-09-08 | 网关死代码：`internal/api/v1/community.go` + `community_test.go`（自述未接线的 HTTP 处理器，仅自测引用） | 已删除 |
| 2026-09-08 | 网关死代码：`internal/service/community_command.go` + `community_query.go` 的**服务部分**（CommunityCommand/QueryService，仅被上一条引用且自带 Deprecated 注记）。注意：同文件中的 `PostView`/`UserView` 是活跃读模型，已提取至 `internal/service/community_views.go` 保留 | 服务已删，视图类型保留 |
| 2026-09-08 | 网关死代码：`internal/event/event_bus.go`（`internal/event` 包零外部导入，与活跃的 `internal/cqrs/event` 是两套） | 已删除 |
| 2026-09-08 | 仓库根空目录/孤儿：`integration_test/`、`test_driver/`、`tests/`（根级空占位，真实测试在 `mobile/integration_test`、`backend/tests`、`tests_e2e`） | 已删除 |
| 2026-09-08 | 根目录孤儿 gitlink `flutter/`（无 .gitmodules 的悬空子模块指针） | 已移除 |
| 2026-09-25 | C-01：`plan_context ↔ prompts` 循环 import（含 `context_pack` 本体，三入口干净进程全炸；2026-09-19 R2-F5 复核升格 H3） | **CLOSED WITH EVIDENCE**（wt364 卡 R2-B）：prompts.py 对 `merge_plan_context` 改函数内延迟导入，打断环中唯一模块级边 prompts→plan_context；函数行为/签名零变更。证据 = `backend/tests/unit/test_wt364_r2b_import_cycles_smoke.py` 三入口 subprocess 干净进程 import 全绿（修复前同测 3/3 红，可证伪）+ 相关面回归全绿 + 冷 mypy ≤ 基线 |
| 2026-09-26 | mypy 类型债存量批一烧减（scripts/ci/mypy_ratchet.sh 口径） | **棘轮下移 1095 → 1041（-54）**（wt504）：29 文件纯类型注解修正，零 `# type: ignore` 新增、零测试迁就、零行为变更。修法分类：①Optional 参数默认值补注解（`T = None` → `T \| None = None`）39 处/21 文件；②容器字面量补类型注解（var-annotated）6 处/6 文件（circuit_breaker `_result_window`/migration `execution_constraints`/collaboration_workflows `categorization`/enhanced_orchestrator `active_tasks`+`active_plans`/orchestrator `dual_core_context`）；③级联收益 9 处——上游 Optional 化后下游误报消失（cache truthy-function 1、HybridExplorationRouter 调用点 1、CacheService.set ttl 调用点 1、`_record_feedback` metadata 调用点 1、ToolSuccessRateView last_used_at 调用点 1、`_broadcast_local` exclude_user_id 调用点 1 等）。error_handler.py 两处 `user_id: str = None` 有意不修（None 会流入 `execute_tool_call` 身份参数，转登记 **V3-FIX-217**，按 AGENTS 身份面红线不并入注解批）；另登记 **V3-FIX-218**（age_client `add_vertex` 声明 `-> str` 实返 None）与 **V3-FIX-219**（celery `_purge_redis_keys` UUID 形参收 str 实参）。触达测试 424 绿（orchestration 全目录 230+galaxy/ab_test/learners 73+auth/contract/celery/event_bus/circuit_breaker 121）；auth_flow_integration 1 failed+15 errors 为 base 既有 sqlite no-table 假红（stash 对照同红）。门禁：`mypy_ratchet.sh` 1041=1041 exit 0；ruff 触达 29 文件全过；black 触达面 23/29 文件 base 既有漂移（stash 对照同数），新增行零 flag。批二候选面：FastAPI 路由参数 Optional 化（auth/plans/tasks/capsules/profile_transparency 7 处，需评估依赖注入行为）、`Missing named argument`（TypedDict 构造 31 处）、`Incompatible return value`（67 处）、bert_intent_classifier 8 处（假红族解禁后再动） |

## ⚠️ 本地测试环境已知阻塞（非代码债务）

- `internal/handler` 的 `TestChatOrchestrator_QuotaIntegration` 在本地沙箱失败（测试内真实 localhost WS 拨号得到 nil 连接后 panic；0.00s 即失败，与代码改动无关——2026-09-08 验证 handler 零改动、零被删符号引用，service/cqrs/middleware 等包全部通过）
- 本机 Xcode license 未接受导致 cgo 不可用，`runtime/cgo` 编译失败会**掩盖**真实编译错误；本地验证 Go 请用 `CGO_ENABLED=0 go build/test ./...`（CI 不受影响）
- Flutter 全量测试在本地被 IsarCore 失败阻塞（见 MEMORY.md 2026-05-03 条目）

## 🔴 P1 — 功能性债务（影响真实用户）

| # | 位置 | 现状 | 建议处置 |
|---|---|---|---|
| 1 | `mobile/lib/core/statistics/presentation/providers/agent_statistics_provider.dart:98-165`、`capsule_statistics_provider.dart`、`focus_statistics_provider.dart:119-141` | 三个统计仓库的 `fetchFromApi` 返回硬编码 mock（固定 successRate 0.95、engagement 4.2 等）；后端已有 `backend/app/api/v1/` 统计路由可接 | 接真实 API 或下线该模块。**已销账（D-04/5ed3d20d 双审，wt479 核验 2026-09-26）**：三统计仓库已接真实端点，本行描述为销账前状态——保留原文防审计断链 |
| 2 | `mobile/lib/core/statistics/data/repositories/hybrid_statistics_repository.dart` | **mock 数据被写进 Isar 暖缓存并作为"过期兜底"长期供给 UI**（假数据比会话存活更久）；`watchStatistics` 自述占位实现（L271） | 与 #1 一并修：mock 不许进缓存。**已销账（同上）**：mock Isar 暖缓存已一次性 purge；残余=watchStatistics 占位+诚实空态（低风险） |
| 3 | `mobile/lib/features/leaderboard/`（约 1,143 行：screen/provider/repo） | **已裁决销账（D-COMM-1，2026-09）**：产品决策 = 全站综合榜**保持 D17 隐藏不路由**（v3-output/D-COMMUNITY/DESIGN.md §2.2/§3.2——大池/异质水平/静态综合分命中「打击中尾生」全部反面模式）；唯一路由产品面改为**自我 7 日锚视图**（后端 `GET /api/v1/leaderboards/self-anchor` 已落地：sprint 账本完成度 + study_records 掌握度增量按日序列，复用既有面零新聚合；网关经 leaderboards wildcard 代理可达）。守卫 `COMM-LB`（`scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py`）固化：routes.dart 不挂 LeaderboardScreen + 网关 leaderboards 组 wildcard-only | 移动端尾巴**已销账（LEADERBOARD-DEBT，D-COMM-4 收官，2026-09）**：D-COMM-4 小队详情榜落地后经能力对比裁决——widget 层无可复用增量（小队榜已覆盖并列名次/无账本态/<3 人降级/完成度口径全部诚实面，死链的 XP/连胜口径反命中反刷分红线；podium/我的排名横幅属被裁决禁入的「大池比较」视觉）→ 三件套 screen/provider/repo 共 1,143 行整链删除，连带 `ApiEndpoints.leaderboards*` 6 个死常量（保留 `leaderboardsSelfAnchor`）、l10n `leaderboard*` 11 个死键（保留 `leaderboardSelfAnchor*` 12 键）、session_refresh_service 两处 provider 登记；COMM-LB 守卫绿（routes.dart 自我锚接线行按守卫自带 escape hatch 注 ignore） |

## 🟡 P2 — 迁移中的集群（删除前必须核对状态）

| # | 位置 | 现状 | 建议处置 |
|---|---|---|---|
| 4 | `backend/app/services/card_protocol/`（legacy_adapter.py 39 处、card_operations_service.py 35 处、phase_service.py 26 处等标记） | 卡协议遗留迁移**mid-flight**，文件自述"shadow 验证通过后才退役 legacy" | 先查 shadow 验证状态再行动；这是最大单体清理目标 |
| 5 | `backend/app/orchestration/routing_engine.py`（26 处 legacy 标记）、`services/galaxy_service.py`（21 处）、`aurora/migration.py`（16 处） | 带退役计划的过渡代码 | 跟随各自迁移计划处置 |
| 6 | Python 全仓 101 文件含 deprecated/legacy/to-be-deleted 标记（services 36、card_protocol 13、orchestration 11、api/v1 10） | 密度图 | 按目录分批清理 |

## 🟢 P3 — 记录性质（当前不动作）

| # | 位置 | 现状 | 说明 |
|---|---|---|---|
| 0 | `backend/gateway/`（2026-09-16 lint 基线债务） | CI 首次真正执行 lint 后记录的 **185 项**遗留发现：errorlint 34、bodyclose 26、revive 22、noctx 20、errcheck 20、gosec 19、unused 12、staticcheck 11、gosimple 7、unparam 6、unconvert 4、ineffassign 2。基线钉在 `e6256a3`（`.golangci.yml` 的 `new-from-rev`），基线前不挡 CI、基线后全量检查 | 按安全价值排序逐步清偿：先 gosec/errcheck/staticcheck（真 bug 类），后 noctx/bodyclose（资源与超时类），清偿后推进基线 |
| 7 | `mobile/lib/features/community/data/repositories/mock_community_repository.dart` | demo 模式回退数据源（`community_repository.dart:11-16` 有意接线） | 有意设计，非债务；已注释说明 |
| 8 | `mobile/third_party_plugins/` 7 个 fork | vendored 原因多为 Apple Silicon/ARM 兼容；具体上游 commit 未登记 | 已补 README 记录；后续可对照上游校验差异 |
| 9 | 网关 `internal/cqrs/outbox/repository.go:420,427`、`internal/worker/community_sync.go:319,328` 弃用构造函数仍可调用 | Deprecated 注记完备 | 小型清理，随手可做 |
| 10 | 根 `CHANGELOG.md` 冻结在 1.0.0（2026-03-22） | 项目已演进至 5 月 | 决定：要么恢复维护，要么明示冻结 |
| 11 | `mobile/lib/features/photon/presentation/screens/photon_transfer_screen.dart`（466 行，2026-09-22 登记，PHOTON 卡 #10 / A-SPEC2 PH-G3） | **幽灵面遗存屏**：`/photon/transfer` 路由已撤除（P2P 转账触反刷敏感区——`transfer_in` 已被排除出可兑换基数，未审计面不应对深链开放；深链现落路由 errorBuilder 兜底），全仓零 push 引用，屏文件按裁决保留未删。屏本体为旧栈实现（`Theme.of` 直取、`ActionChip` backgroundColor 直填、`DS.xl` 裸 padding），`pt*` l10n 键为其保留 | 未来真做 P2P 转账需先过 D 线价值评估 + 反刷审计，再按现行 SPEC 重写并重挂路由；否则届时整文件连同 `pt*` l10n 死键一并删除 |
| 12 | `mobile/lib/features/notification_center/presentation/screens/notification_analytics_screen.dart` + `notification_analytics_provider.dart`（约 0.5k 行） | **孤儿面（NAV-IA P-3，2026-09-22 摘除路由挂载）**：`/notification-analytics` 从 `NotificationCenterRoutes.routes` 摘除（0 入边、纯运营分析面，挂在路由表即可被任意深链触达）；屏与 provider 文件保留未删，barrel `notification_center.dart` 导出未动 | 重新挂载需产品裁决（候选：admin-operations 下）；长期不用则连屏带 provider 删除（屏留 git 历史） |

## 明确不是债务（防止误删）

- `internal/cqrs`、`internal/chaos`（`cmd/server/setup.go` 引用，活跃）
- `internal/worker/community_sync.go` 等三个投影消费者（活跃社群路径本体）
- `data/dictionaries/`（compose 挂载 + settings 引用）
- `tool/ui_lint.sh`（CI `ui-lint.yml` path filter 引用，**不可移动**）
- `README_CN.md`（5 行别名指针，历史决定保留）

---

**审计方法**：三路并行只读探索（网关导入图验证、移动端路由/引用 grep、Python 标记密度扫描）+ 全量引用交叉核对；2026-09-08 执行。

---

## 2026-09-18 守卫体系自足性（登记于全量首绿之后）

- **BD 规则停用**：`stage40_sgw_dogfood_report.md` 为 v1 未跟踪产物已丢失；规则要求 `PHASE_I_EXIT_READY: YES` 的实测证据，不可凭空重建。恢复条件：真实重跑 Stage40 SGW dogfood（Phase A/B/C，/tmp/stage40_{off,shadow,rl}.db 三库）。
- **CARD-DUAL-WRITE 规则停用**（已处置 2026-09-27，V3-FIX-274）：守卫 import 的 `app.services.card_protocol.consistency_validator` 自初始提交即不存在于仓库；V3-FIX-274 已补齐该模块、复活规则进 manifest 活跃行（守卫自足化：默认环境内存 SQLite 种子自测，真库下跑真实双写校验；`card_protocol/__init__.py` 改惰性导出解除对未跟踪 `app.gen` 的 import 依赖）。遗留尾巴：校验器的生产面接线（API/ops 暴露）随 card_protocol 双写期收口落地。
- **守卫产物再生脚本**：`scripts/stage27/render_jitai_templates.py`、`scripts/stage30/render_stage30_templates.py`；其余 stage22/23/24 产物用各自 --write/bootstrap 脚本再生。产物均已入库，勿再依赖未跟踪状态。


## 2026-09-19 B-06 复核补充登记（O1）

- **engine 侧 is_pro=flame_level>=3 派生**：`backend/app/services/user_service.py:208` 与网关 `user_context.go:129` 同源同病（D17 拆除对象），游客种子 flame=15 导致 166/166 游客以 pro 进 LLM tier（B-02 双路实锤）。处置随 V3-FIX-02（entitlement 独立字段）一并拆网关+引擎两处。


## 2026-09-19 C-01 复核补充登记（R2-F5）

- **plan_context ↔ prompts 循环 import（含 context_pack 本体）**：环 = plan_context:27 → models.__init__:103 → aurora runtime → chat_adapter:20 → prompts:44 → 回 plan_context；单独 import `app.core.plan_context` / `app.orchestration.prompts` / `app.core.context_pack` 皆炸（双 worktree 复现）。正常入口（conftest/main 先载 app.models）不触发；但 C-01 把 context_pack 变成会被直接 import 的契约模块后，新脚本/Celery 入口/健康检查首 import 即炸的概率上升。处置：接线卡前做一次 import 拓扑整理（把 prompts 对 models 的传递依赖打断或延迟导入）。
- **✅ 已闭合（CLOSED WITH EVIDENCE，2026-09-25，wt364 卡 R2-B）**：prompts.py 的 `from app.core.plan_context import merge_plan_context` 下沉为 `build_system_prompt` 内延迟导入（唯一调用点，环中唯一模块级边），打破上述环；无 try/except 掩盖、无 API 签名变更。冒烟判据 `backend/tests/unit/test_wt364_r2b_import_cycles_smoke.py`（三入口 subprocess 干净进程 import，修复前 3/3 红、修复后 3/3 绿）。
