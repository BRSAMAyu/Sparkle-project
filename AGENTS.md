# AGENTS.md — Sparkle 项目 Agent 规范

> 2026-09 新阶段版。本仓库是 **Sparkle 星火** 的参赛工程项目：一个面向大学生的 AI 学习成长系统。
> 深入了解代码库：[docs/00_项目概览/05_编码代理深度指南.md](docs/00_项目概览/05_编码代理深度指南.md)

## 项目一句话

三层架构的 AI 学习成长系统：`Flutter Mobile + Go Gateway + Python AI Engine`，由 PostgreSQL 16（pgvector + Apache AGE）、Redis、MinIO、Celery 支撑。核心链路：`Flutter → /ws/chat → Go Gateway → AgentService.StreamChat(gRPC) → ChatOrchestrator`。

## 项目结构

- `backend/app/` — Python AI 引擎（gRPC :50051 + FastAPI :8000）：`orchestration/`（编排、双核路由、提示词）、`agents/`（聊天 StateGraph）、`services/`（服务层）、`state_aggregator/`、`services/evidence/`（贝叶斯证据融合）
- `backend/gateway/` — Go 网关（:8080）：WebSocket/HTTP、鉴权、限流、gRPC 桥、CQRS
- `mobile/` — Flutter 应用（Riverpod + GoRouter）；`third_party_plugins/` 为 vendored fork（见其 README）
- `proto/` — gRPC 契约单一事实来源（buf 管理）
- `docs/` — 精简后的工程文档（入口 `docs/README.md`）；`docs/competition/` 为参赛材料
- `scripts/` — 治理守卫（`rule_guard_manifest.tsv`）、部署、一次性脚本（`scripts/devtools/`）
- `tests_e2e/` — 跨层 E2E

## 常用命令

```bash
make dev-up               # PostgreSQL(16+AGE+pgvector)/Redis/MinIO
make sync-db              # Alembic 迁移 → schema 导出 → SQLC 生成
make proto-gen            # buf 重新生成 gRPC 代码
make grpc-server          # Python 引擎 :50051
make gateway-dev          # Go 网关 :8080
cd mobile && flutter run

cd backend && pytest && cd ../backend/gateway && go test ./...   # 测试
cd mobile && flutter test
bash scripts/run_all_rule_guards.sh      # 治理守卫（提交前）
```

## 硬规则

1. **proto → 生成代码**：改 `proto/*.proto` 后 `make proto-gen`；永不手改 `*/gen/` 与 SQLC 产物
2. **DB schema**：唯一入口是 Alembic 迁移；网关 `schema.sql` 是自动导出快照，手改无效
3. **分层边界**：Go 网关禁 AI 推理与业务逻辑；Python 引擎不做用户鉴权；handler 走 service 层
4. **本地验证 Go 请用 `CGO_ENABLED=0`**（本机 Xcode license 问题会让 cgo 报错并掩盖真实错误）
5. **仓库整洁**：遵循 `docs/engineering/REPOSITORY_STANDARDS.md`——一次性脚本进 `scripts/devtools/`，会话产物/运行时数据永不入库，新文档登记进所在目录 README
6. **已知债务**：动统计模块、排行榜、`card_protocol/` 前先看 `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md`
7. **磁盘与工作区纪律（强制，2026-09-19 磁盘事故后立规）**——见下方专节，每个 agent 开工前必读

## 磁盘与工作区纪律（强制）

> 背景：2026-09-19 磁盘被耗尽到 1G，导致 Docker daemon 崩溃、数据库容器 exit 133，所有在跑任务险些全损。事后清出 17G+，其中 14G 是无人清理的 77 个废弃 worktree。

**每个子 agent 的义务（开工前读，收工前做）**：

1. **专属空间边界**：一切修改只在自己的 worktree 内进行；主仓（Sparkle-project）与主仓进程对子 agent 是**只读**的；严禁在仓库根、家目录、共享目录创建任何文件（尤其 `.env` 副本——曾因此覆盖生产配置导致网关瘫痪）。
2. **临时产物只放两处**：worktree 内（随 worktree 生命周期回收）或 `/tmp`（收工自清）。构建产物（`build/`、`.dart_tool/`、venv、node_modules）不入库、不落主仓。
3. **收工必清理清单**（每轮任务结束前执行）：
   - 删：worktree 内 `mobile/build`、`.dart_tool`、独立端口的进程（杀净）、`/tmp` 下自己产生的日志/探针数据、起过的模拟器（Android 实测员收工必须关模拟器）
   - 留：`docs/` 下的报告与 `.patch`（规范目录登记）、正式代码改动
4. **持久产物只有两类**：进 git 的代码/文档，和归档在 `docs/competition/` 的实测报告。其余皆可删。
5. **主会话职责**：合入 patch 后立即 `git worktree remove` 已完成的 worktree；每轮唤醒巡检 `df`（<6G 触发清理：go-build 缓存、/tmp 大日志、已完成 worktree 的构建产物）；发现不明大文件立即溯源。

**红线**：C 档（聊天记录等应用数据、正在运行的 Docker 卷、在用模拟器镜像）与 D 档（主仓、在用 worktree、SDK 平台工具）永不清理；删除任何 1G 以上内容前必须获项目方明确确认。

## 代码风格

Python：类型注解 + black(120)/ruff ｜ Go：gofmt + golangci-lint ｜ Dart：Effective Dart + flutter_lints，屏幕 `_screen.dart` 结尾，UI 消费 `mobile/lib/core/design/` 令牌
