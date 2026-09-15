# GEMINI.md — Sparkle（星火）

> 2026-09 新阶段版。规范入口：`AGENTS.md` ｜ 深度导览：[docs/00_项目概览/05_编码代理深度指南.md](docs/00_项目概览/05_编码代理深度指南.md)

Sparkle 是面向大学生的 AI 学习成长系统，三层架构：

- **前端** Flutter（Riverpod + GoRouter，42 个 feature 模块）
- **接入** Go 网关 1.24（鉴权、WebSocket、限流、gRPC 桥、CQRS）
- **引擎** Python 3.11（自研 StateGraph 聊天编排 + LangGraph 规划、FastAPI + gRPC）
- **设施** PostgreSQL 16（pgvector + Apache AGE）、Redis、MinIO、Celery

## 强制规则

1. **源头层级**：API 契约源头是 `proto/*.proto`（`make proto-gen` 生成 Go/Dart，Python 走 `scripts/generate_python_protos.sh`）；DB 源头是 Alembic 迁移（网关 `schema.sql` 是导出快照，手改无效）。**永不手改生成文件。**
2. **分层**：Go 网关只做接入与转发（禁 AI 推理，handler 走 service 层）；Python 引擎禁用户鉴权。
3. **验证**：`pytest`（backend）、`go test ./...`（gateway）、`flutter test`（mobile）；本地验证 Go 用 `CGO_ENABLED=0`。
4. **整洁**：遵循 `docs/engineering/REPOSITORY_STANDARDS.md`；已知债务见 `docs/engineering/KNOWN_CODE_DEBT_LEDGER.md`。
5. L3+ 跨边界任务（proto/DB/三层联动）先输出影响面分析（认知协议见 CLAUDE.md）。

## 关键目录

`proto/`（契约）、`backend/app/orchestration/orchestrator.py`（AI 大脑）、`backend/app/agents/standard_workflow.py`（聊天图）、`backend/gateway/internal/handler/chat_orchestrator*.go`（实时枢纽）、`mobile/lib/features/`（功能模块）、`docs/competition/`（参赛材料）。

## 常用命令

`make dev-up` / `make sync-db` / `make proto-gen` / `make grpc-server` / `make gateway-dev` / `bash scripts/run_all_rule_guards.sh`
