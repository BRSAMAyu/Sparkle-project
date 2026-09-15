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
| 3 | `mobile/lib/features/leaderboard/`（约 1,143 行：screen/provider/repo） | 完整实现但**未挂路由**（`app/routes.dart` 聚合处无条目，全仓无 `LeaderboardScreen` 引用）；后端 `api/v1/leaderboards.py`、`api_endpoints.dart:575-579` 5 个端点常量、20 条 l10n 均已就绪 | 产品决策：要么挂路由上线，要么整链删除（含端点常量与 l10n 键） |

## 🟡 P2 — 迁移中的集群（删除前必须核对状态）

| # | 位置 | 现状 | 建议处置 |
|---|---|---|---|
| 4 | `backend/app/services/card_protocol/`（legacy_adapter.py 39 处、card_operations_service.py 35 处、phase_service.py 26 处等标记） | 卡协议遗留迁移**mid-flight**，文件自述"shadow 验证通过后才退役 legacy" | 先查 shadow 验证状态再行动；这是最大单体清理目标 |
| 5 | `backend/app/orchestration/routing_engine.py`（26 处 legacy 标记）、`services/galaxy_service.py`（21 处）、`aurora/migration.py`（16 处） | 带退役计划的过渡代码 | 跟随各自迁移计划处置 |
| 6 | Python 全仓 101 文件含 deprecated/legacy/to-be-deleted 标记（services 36、card_protocol 13、orchestration 11、api/v1 10） | 密度图 | 按目录分批清理 |

## 🟢 P3 — 记录性质（当前不动作）

| # | 位置 | 现状 | 说明 |
|---|---|---|---|
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
