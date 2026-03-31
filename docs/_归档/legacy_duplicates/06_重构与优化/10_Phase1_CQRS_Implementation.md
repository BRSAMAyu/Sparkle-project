# Sparkle 社群模块：CQRS 架构 Phase 1 实施报告

**日期**: 2025-12-27
**状态**: ✅ 已完成 (Implemented & Compiled)

## 1. 概述

本报告记录了 Sparkle 社群模块（Community）从传统架构向 **CQRS (命令查询职责分离)** 架构转型的第一阶段实施细节。
目标是实现**高并发读写分离**，保护核心数据库，并利用 Redis 提供毫秒级 Feed 流查询。

### 核心架构变更
*   **Write Side (Command)**: Gin API -> Postgres (Source of Truth) -> Redis Stream (Async Event).
*   **Read Side (Query)**: Gin API <- Redis (View Model).
*   **Sync Worker**: Background Goroutine -> Consumes Stream -> Updates Redis View & ZSet.

---

## 2. 实施清单

### 2.1 数据库与迁移
*   **SQL Schema**: 在 `backend/gateway/internal/db/schema.sql` 中添加了 `posts` 和 `post_likes` 表。
*   **SQL Queries**: 在 `query.sql` 中添加了 `CreatePost`, `GetPost`, `CreatePostLike` 等原子操作。
*   **Alembic Migration**: 创建了 `backend/alembic/versions/a1b2c3d4e5f6_create_community_tables.py` 以确保 Python 端/生产环境数据库同步。
*   **Code Gen**: 运行 `sqlc generate` 更新了 Go DB 模型。

### 2.2 核心组件 (Go)
| 组件 | 路径 | 职责 |
| --- | --- | --- |
| **Event Bus** | `internal/event/event_bus.go` | 封装 Redis Stream `XADD` 操作，定义统一事件格式。 |
| **Command Service** | `internal/service/community_command.go` | 处理 `CreatePost`, `LikePost`。写 DB 后立即发布事件。 |
| **Query Service** | `internal/service/community_query.go` | 仅从 Redis (`feed:global`, `post:view:*`) 读取数据。**0 SQL 查询**。 |
| **Sync Worker** | `internal/worker/community_sync.go` | 后台消费者。处理 `post_created` 事件，回查 DB (Post+User)，组装 JSON 写入 Redis。 |
| **API Handler** | `internal/api/v1/community.go` | Gin 路由处理，对接 Command/Query Service。 |

### 2.3 集成
*   **Wiring**: 在 `backend/gateway/cmd/server/main.go` 中初始化了上述所有组件。
*   **Routes**: 注册了 `/api/v1/community/posts` (POST), `/feed` (GET), `/posts/:id/like` (POST)。

---

## 3. 关键代码解析

### 3.1 异步事件发布 (Write Side)
```go
// internal/service/community_command.go
func (s *CommunityCommandService) CreatePost(...) {
    // 1. ACID Write to Postgres
    post, err := s.queries.CreatePost(...)
    
    // 2. Publish Lightweight Event
    err = s.bus.Publish(ctx, event.DomainEvent{
        Type: event.EventPostCreated,
        Payload: map[string]interface{}{
            "post_id": post.ID,
            "user_id": post.UserID,
        },
    })
}
```

### 3.2 读视图构建 (Sync Worker)
```go
// internal/worker/community_sync.go
func (w *CommunitySyncWorker) processMessage(...) {
    // 1. Re-fetch full data from DB (Post + User Profile)
    post := w.queries.GetPost(...)
    user := w.queries.GetUser(...)

    // 2. Materialize View (JSON)
    view := service.PostView{
        ID: post.ID,
        Content: post.Content,
        User: service.UserView{Username: user.Username, ...},
    }

    // 3. Write to Redis (Pipeline)
    pipe.Set("post:view:"+id, viewJSON)
    pipe.ZAdd("feed:global", Timestamp, id)
    pipe.Exec()
}
```

### 3.3 极速查询 (Read Side)
```go
// internal/service/community_query.go
func (s *CommunityQueryService) GetGlobalFeed(...) {
    // 1. Get IDs (Sorted by Time)
    ids := redis.ZRevRange("feed:global", start, stop)

    // 2. Get Data (Batch)
    jsons := redis.MGet("post:view:" + id...)

    // Return directly (No DB connection used)
    return Unmarshal(jsons)
}
```

---

## 4. 测试与验证

由于本地环境缺乏运行中的 Postgres 和 Redis 实例，已执行以下验证：

1.  **编译检查**: `go build ./...` **成功**。修复了 UUID 类型转换和 `authHandler` 初始化遗漏的问题。
2.  **代码静态分析**: 确认 `sqlc` 生成代码与 Schema 匹配。
3.  **依赖注入检查**: 确认 `main.go` 中各组件依赖关系正确（Redis -> EventBus, Queries -> CommandService 等）。

### 下一步测试计划 (需基础设施)
1.  **启动环境**: `docker-compose up -d postgres redis`
2.  **应用迁移**: `cd backend && alembic upgrade head`
3.  **运行 Gateway**: `cd backend/gateway && go run cmd/server/main.go`
4.  **端到端测试**:
    *   `POST /api/v1/community/posts` -> 确认 DB 有数据，Redis Stream 有消息。
    *   观察日志 -> 确认 Worker 消费消息。
    *   `GET /api/v1/community/feed` -> 确认返回刚才发布的帖子（带用户信息）。

---

## 5. 待办事项 (Next Steps)

1.  **Phase 2: Search Engine**: 引入 Meilisearch 或 Redis Search 替代 `feed:global` ZSet，以支持复杂过滤和全文检索。
2.  **Reliability**: 引入 `Outbox Pattern` 确保 DB 写入与事件发布的强一致性（目前是 "Best Effort"）。
3.  **Metrics**: 为 Worker 添加 Prometheus 监控（消费延迟、处理速率）。
