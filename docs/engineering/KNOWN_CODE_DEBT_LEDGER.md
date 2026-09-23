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

## ⚠️ 本地测试环境已知阻塞（非代码债务）

- `internal/handler` 的 `TestChatOrchestrator_QuotaIntegration` 在本地沙箱失败（测试内真实 localhost WS 拨号得到 nil 连接后 panic；0.00s 即失败，与代码改动无关——2026-09-08 验证 handler 零改动、零被删符号引用，service/cqrs/middleware 等包全部通过）
- 本机 Xcode license 未接受导致 cgo 不可用，`runtime/cgo` 编译失败会**掩盖**真实编译错误；本地验证 Go 请用 `CGO_ENABLED=0 go build/test ./...`（CI 不受影响）
- Flutter 全量测试在本地被 IsarCore 失败阻塞（见 MEMORY.md 2026-05-03 条目）

## 🔴 P1 — 功能性债务（影响真实用户）

| # | 位置 | 现状 | 建议处置 |
|---|---|---|---|
| 1 | `mobile/lib/core/statistics/presentation/providers/agent_statistics_provider.dart:98-165`、`capsule_statistics_provider.dart`、`focus_statistics_provider.dart:119-141` | 三个统计仓库的 `fetchFromApi` 返回硬编码 mock（固定 successRate 0.95、engagement 4.2 等）；后端已有 `backend/app/api/v1/` 统计路由可接 | 接真实 API 或下线该模块 |
| 2 | `mobile/lib/core/statistics/data/repositories/hybrid_statistics_repository.dart` | **mock 数据被写进 Isar 暖缓存并作为"过期兜底"长期供给 UI**（假数据比会话存活更久）；`watchStatistics` 自述占位实现（L271） | 与 #1 一并修：mock 不许进缓存 |
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
- **CARD-DUAL-WRITE 规则停用**：守卫 import 的 `app.services.card_protocol.consistency_validator` 自初始提交即不存在于仓库；card_protocol 接线时须一并补齐该模块并恢复规则。
- **守卫产物再生脚本**：`scripts/stage27/render_jitai_templates.py`、`scripts/stage30/render_stage30_templates.py`；其余 stage22/23/24 产物用各自 --write/bootstrap 脚本再生。产物均已入库，勿再依赖未跟踪状态。


## 2026-09-19 B-06 复核补充登记（O1）

- **engine 侧 is_pro=flame_level>=3 派生**：`backend/app/services/user_service.py:208` 与网关 `user_context.go:129` 同源同病（D17 拆除对象），游客种子 flame=15 导致 166/166 游客以 pro 进 LLM tier（B-02 双路实锤）。处置随 V3-FIX-02（entitlement 独立字段）一并拆网关+引擎两处。


## 2026-09-19 C-01 复核补充登记（R2-F5）

- **plan_context ↔ prompts 循环 import（含 context_pack 本体）**：环 = plan_context:27 → models.__init__:103 → aurora runtime → chat_adapter:20 → prompts:44 → 回 plan_context；单独 import `app.core.plan_context` / `app.orchestration.prompts` / `app.core.context_pack` 皆炸（双 worktree 复现）。正常入口（conftest/main 先载 app.models）不触发；但 C-01 把 context_pack 变成会被直接 import 的契约模块后，新脚本/Celery 入口/健康检查首 import 即炸的概率上升。处置：接线卡前做一次 import 拓扑整理（把 prompts 对 models 的传递依赖打断或延迟导入）。
