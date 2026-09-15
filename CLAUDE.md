# CLAUDE.md — Sparkle（星火）

> 2026-09 新阶段版。规范入口：`AGENTS.md` ｜ 深度导览：[docs/00_项目概览/05_编码代理深度指南.md](docs/00_项目概览/05_编码代理深度指南.md)

## 项目概览

Sparkle 是面向大学生的 AI 学习成长系统（双核协作：执行核推进目标，认知核理解用户）。三层架构：Flutter（Riverpod/GoRouter）+ Go 网关（鉴权/WS/限流）+ Python 引擎（自研 StateGraph 聊天编排 + LangGraph 规划）。基础设施：PostgreSQL 16（pgvector+AGE）、Redis、MinIO、Celery。

## 认知协议

| 级别 | 特征 | 协议 |
|------|------|------|
| L1 原子 | 单文件 <50 行 | 直接执行 |
| L2 局部 | 2-5 文件同语言同特性 | 简述意图后执行 |
| **L3 跨边界** | proto/Go↔Python↔Flutter/DB | **必须先出计划** |
| L4 架构级 | 新子系统/大重构 | **必须深度分析** |

L3+ 在动手前输出：影响面 / 风险 / 依赖链 / 执行步骤。

## 硬规则

```
NEVER 手改生成代码（*/gen/、SQLC 产物）——源头在 proto / Alembic / query.sql
NEVER 改 proto 后跳过 make proto-gen
NEVER Go 网关写 AI 推理/业务逻辑；handler 必须走 service 层
NEVER Python 引擎做用户鉴权
NEVER 密钥入库；提交前跑 bash scripts/run_all_rule_guards.sh
NEVER 在仓库根散落一次性脚本/会话产物（见 docs/engineering/REPOSITORY_STANDARDS.md）
```

## 主链路（聊天）

```
Flutter websocket_chat_service_v2.dart → Go chat_orchestrator*.go → agent/client.go
→ Python agent_grpc_service.py → orchestrator.py → agents/standard_workflow.py → llm_service.py
```

## 命令与排障

```bash
make dev-up / sync-db / proto-gen / grpc-server / gateway-dev / smoke
cd backend && pytest ; cd backend/gateway && go test ./... ; cd mobile && flutter test
# 本地验证 Go：CGO_ENABLED=0 go build ./...（绕过本机 cgo/Xcode license 问题）
docker compose logs -f gateway / grpc-server
grpcurl -plaintext localhost:50051 list
```

| 症状 | 排查 |
|------|------|
| WS 连不上 | `curl localhost:8080/api/v1/health` |
| gRPC 超时 | `grpcurl -plaintext localhost:50051 list` |
| 字段找不到 | proto 不同步 → `make proto-gen` |
| DB 查询失败 | `alembic current` vs `alembic heads` |

## 提交前检查单

```
□ 编译/测试通过（受影响区域）
□ 生成代码已从源头重新生成
□ 无密钥/调试残留
□ 规则守卫通过（bash scripts/run_all_rule_guards.sh）
□ 新文件符合仓库整洁规范
```
