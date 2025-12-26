# Sparkle Go 后端重构对齐指南 (Sparkle Go Backend Refactoring Alignment Guide)

本文档旨在详尽记录 Sparkle 项目从单体 Python 后端向 Go + Python 混合架构迁移的完整过程、设计决策及后续计划，确保开发团队对齐目标。

---

## 1. 核心目标 (Core Objectives)

本次重构旨在解决性能瓶颈并提升系统可维护性：

1.  **架构解耦 (Decoupling)**:
    -   **Go 网关**: 负责高并发 IO（WebSocket）、用户鉴权、基础数据 CRUD。
    -   **Python 代理**: 专注于 CPU 密集型任务（AI 推理）、复杂业务逻辑（Agent/RAG）。
2.  **性能提升 (High Performance)**:
    -   利用 Go 的 Goroutine 处理数千个并发 WebSocket 长连接。
    -   使用 `pgx` 驱动和 SQLC 生成的代码实现零反射、类型安全的数据库高性能读写。
3.  **契约驱动 (Contract-First)**:
    -   通过 Protobuf (`.proto`) 严格定义跨语言通信接口，杜绝隐式依赖。
4.  **数据主权 (Data Sovereignty)**:
    -   Python (SQLAlchemy/Alembic) 负责定义数据库结构（Schema Owner）。
    -   Go (SQLC) 负责消费数据（Data Consumer），通过 `pg_dump` 保持结构同步。

---

## 2. 总体架构与职责 (Architecture & Responsibilities)

### A. Go Gateway (`backend/gateway`)
作为系统的流量入口和协调者：
*   **接入层**: 基于 Gin 框架提供 HTTP API，基于 Gorilla WebSocket 提供长连接服务。
*   **鉴权**: 解析 JWT Token，维护用户会话。
*   **数据库**: 直接读写 `users` (用户), `chat_history` (聊天记录) 等基础表。
*   **AI 桥接**: 作为 gRPC 客户端，将 AI 请求转发给 Python 服务，并将流式响应通过 WebSocket 推送给前端。

### B. Python Agent Engine (`backend/app`)
作为系统的智能大脑：
*   **协议**: 提供 gRPC Server 实现 (`AgentService`)。
*   **逻辑**: 运行 LangChain/LangGraph，处理 Prompt 工程和工具调用。
*   **记忆**: 读写 `memories` 表，利用 `pgvector` 进行向量检索 (RAG)。
*   **上下文**: 读取 `chat_history` 构建短期记忆，但不负责写入基础消息（由 Go 处理）。

---

## 3. 实施进度回顾 (Implementation Progress)

### ✅ 已完成工作 (Completed)

#### 1. 协议定义 (Protocol Definition)
-   创建 `proto/agent_service.proto`，定义了系统的核心契约。
-   **特性**:
    -   `StreamChat`: 双向流式对话，支持打字机效果。
    -   `oneof`: 明确区分 文本流 (`delta`)、工具调用 (`tool_call`) 和 状态更新 (`status_update`)。
    -   `FinishReason`: 细粒度控制生成结束原因。
    -   `UserProfile` & `Struct`: 结合强类型核心字段与灵活的扩展字段。

#### 2. Go 网关框架搭建 (Go Gateway Framework)
-   建立了 `backend/gateway` 标准 Go 项目结构。
-   **基础设施**:
    -   `docker-compose.yml`: 集成 `pgvector/pgvector:pg16`。
    -   `Makefile`: 实现了 `sync-db` (同步 Schema)、`proto-gen` (生成代码)、`dev-up` (启动环境) 等工作流。
-   **核心代码**:
    -   `internal/handler/chat_orchestrator.go`: 实现了 WebSocket 读写泵 (Read/Write Pump)，支持消息聚合与异步落库。
    -   `internal/agent/client.go`: 封装 gRPC 客户端，实现了 Metadata (User-ID) 透传。
    -   `internal/db`: 配置了 SQLC，编写了 `query.sql` (Auth/Chat)。

#### 3. 环境与数据库修复 (Environment & DB Fixes)
-   **统一数据库**: 将 Python 环境从 SQLite 迁移至 PostgreSQL，确保与 Go 侧共用同一数据源。
-   **模型修复**: 修复了 `backend/app/models/user.py` 中缺失 `__tablename__` 和核心字段 (`username`, `hashed_password`) 的问题，打通了 Alembic 迁移流程。
-   **配置修正**: 统一使用 `postgres` 超级用户，解决了权限验证失败的问题。

### 🚨 遇到的挑战与解决方案 (Challenges & Solutions)

| 问题现象 | 根本原因 | 解决方案 |
| :--- | :--- | :--- |
| **Alembic 迁移报错** `InvalidRequestError` | Python 模型定义不完整，`User` 类缺少表名配置。 | 在 `user.py` 中补充 `__tablename__ = "users"` 及缺失列。 |
| **Alembic 连接 SQLite** `table users already exists` | Shell 环境变量 `DATABASE_URL` 污染，覆盖了 `.env` 文件。 | 指导 `unset DATABASE_URL` 并强制在 `.env` 中指定 Postgres URL。 |
| **Postgres 认证失败** `role "user" does not exist` | Docker 容器使用旧卷或非标准用户初始化。 | 标准化使用 `postgres` 用户，并执行 `docker compose down --volumes` 重置数据。 |

---

## 4. 接下来的计划 (Next Steps)

### Step 3: Python 后端重构 (Refactor Python Backend)
**目标**: 将现有的 FastAPI 单体应用改造为 gRPC 微服务。
1.  **依赖升级**: 引入 `grpcio`, `grpcio-tools`。
2.  **服务实现**: 编写 `AgentService` 实现类，对接现有的 `llm_service`。
3.  **入口改造**: 创建 `server.py` 启动 gRPC 服务，移除或缩减 FastAPI 路由。
4.  **RAG 适配**: 确保 Python 端能通过 `asyncpg`/`psycopg` 正确连接 Postgres 并操作向量数据。

### Step 4: Flutter 客户端适配 (Flutter Adaptation)
**目标**: 让移动端对接新的 WebSocket 网关。
1.  **网络层改造**: 将 HTTP/REST 调用替换为 WebSocket 连接 (`go_gateway_url/ws/chat`)。
2.  **协议适配**: 解析新的 JSON 消息格式 (匹配 `ChatResponse` proto 定义)。
3.  **UI 优化**: 适配流式输出 (`delta` 追加) 和状态展示 (`AgentStatus`)。

### Step 5: 联调与测试 (Integration Testing)
1.  **全链路测试**: App -> Go Gateway (WS) -> Python Agent (gRPC) -> LLM。
2.  **压力测试**: 验证 Go 网关在高并发连接下的稳定性。

---

## 5. 开发者操作速查 (Developer Cheatsheet)

### 启动开发环境
```bash
# 1. 彻底重置数据库 (慎用)
docker compose down --volumes
rm -rf postgres_data

# 2. 启动数据库
make dev-up

# 3. 运行 Python 迁移 (在 backend/ 目录下)
unset DATABASE_URL # 确保无残留变量
cd backend
alembic upgrade head

# 4. 同步 Go 代码 (在根目录下)
make sync-db    # 同步数据库结构到 Go
make proto-gen  # 生成 Protobuf 代码
cd backend/gateway && go mod tidy
```

### 运行服务
*   **Go Gateway**: `cd backend/gateway && go run cmd/server/main.go`
*   **Python Agent**: (待实现) `python server.py`
