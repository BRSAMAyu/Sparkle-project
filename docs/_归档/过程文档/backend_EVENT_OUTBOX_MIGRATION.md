# Event Outbox 迁移记录

## 概述

本文档记录 `event_outbox` 和 `event_sequence_counters` 表的迁移过程，确保事件发布链路在所有环境中稳定可用。

## 迁移详情

### 迁移文件
- **文件**: `backend/alembic/versions/5f2b9b3c0e6f_create_event_outbox_tables.py`
- **版本**: `5f2b9b3c0e6f`
- **依赖**: `4f6c3b8e1d2a` (create_user_tool_history_table)

### 迁移内容

#### 1. event_outbox 表

```sql
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    payload jsonb NOT NULL,
    metadata jsonb,
    sequence_number BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- 索引
CREATE INDEX idx_outbox_aggregate ON event_outbox (aggregate_type, aggregate_id, sequence_number);
CREATE INDEX idx_outbox_unpublished ON event_outbox (created_at) WHERE published_at IS NULL;
```

#### 2. event_sequence_counters 表

```sql
CREATE TABLE event_sequence_counters (
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    next_sequence BIGINT NOT NULL DEFAULT 1,
    PRIMARY KEY (aggregate_type, aggregate_id)
);
```

### 迁移特性

该迁移是**幂等且安全的**，包含以下修复逻辑：

1. **表不存在时创建**: 使用 `inspector.has_table()` 检查并创建
2. **类型修复**: 自动将手动创建的 `BYTEA` 列转换为 `jsonb`
3. **默认值补齐**: 为 `id` 列添加 `gen_random_uuid()` 默认值
4. **索引安全创建**: 使用 `CREATE INDEX IF NOT EXISTS`
5. **主键修复**: 确保 `event_sequence_counters` 有正确的主键

### 手动建表导致的漂移修复

如果之前手动创建了 `event_outbox` 表，迁移会自动修复以下问题：

| 问题 | 修复 |
|------|------|
| `payload` 列类型为 `BYTEA` | 转换为 `jsonb` |
| `metadata` 列类型为 `BYTEA` | 转换为 `jsonb` |
| `id` 列无默认值 | 添加 `gen_random_uuid()` |
| 缺少索引 | 创建 `idx_outbox_aggregate` 和 `idx_outbox_unpublished` |

### 降级策略

```python
def downgrade() -> None:
    # Intentionally a no-op: avoid destructive drops for core outbox tables.
    pass
```

迁移的降级函数是**有意设计的 no-op**，避免误删核心表。

## 应用迁移

### 开发环境

```bash
# 应用迁移
docker exec sparkle_api alembic upgrade head

# 验证版本
docker exec sparkle_api alembic current
# 应输出: 5f2b9b3c0e6f (head)

# 验证表结构
docker exec sparkle_db psql -U postgres -d sparkle -c "\d event_outbox"
docker exec sparkle_db psql -U postgres -d sparkle -c "\d event_sequence_counters"
```

### 生产环境

```bash
# 1. 备份数据库
pg_dump -U sparkle -d sparkle > backup_before_outbox_$(date +%Y%m%d).sql

# 2. 应用迁移
alembic upgrade head

# 3. 验证
psql -U sparkle -d sparkle -c "SELECT COUNT(*) FROM event_outbox;"
psql -U sparkle -d sparkle -c "SELECT * FROM alembic_version;"
```

## 验证检查清单

- [ ] Alembic 版本为 `5f2b9b3c0e6f`
- [ ] `event_outbox` 表存在，列类型为 `jsonb`
- [ ] `event_sequence_counters` 表存在，有主键
- [ ] 索引 `idx_outbox_aggregate` 和 `idx_outbox_unpublished` 存在
- [ ] 网关日志无 `relation does not exist` 错误
- [ ] 网关日志无 `cached plan must not change result type` 错误

## 相关文件

- **迁移文件**: `backend/alembic/versions/5f2b9b3c0e6f_create_event_outbox_tables.py`
- **Gateway Outbox Publisher**: `backend/gateway/internal/cqrs/outbox/publisher.go`
- **Outbox Repository**: `backend/gateway/internal/cqrs/outbox/repository.go`
- **Schema 定义**: `backend/gateway/internal/db/schema.sql`

## 故障排除

### 问题 1: "cached plan must not change result type"

**原因**: 列类型在迁移后发生变化，但 PostgreSQL 的 prepared statements 缓存了旧计划

**解决方案**: 重启网关服务
```bash
docker compose restart sparkle_gateway
```

### 问题 2: "relation event_outbox does not exist"

**原因**: 迁移未正确应用

**解决方案**: 手动应用迁移
```bash
docker exec sparkle_api alembic upgrade 5f2b9b3c0e6f
```

### 问题 3: Alembic 版本未更新

**原因**: 迁移运行成功但版本未记录（罕见）

**解决方案**: 手动更新版本表
```sql
UPDATE alembic_version SET version_num = '5f2b9b3c0e6f';
```

## 维护

### 清理策略

参考 `docs/OUTBOX_GROWTH_STRATEGY.md` 了解如何管理 outbox 表的增长：

- 已发布的事件保留 7 天
- 使用 Celery Beat 定期清理
- 批量删除避免长时间锁表

### 监控指标

```sql
-- 待发布事件数量
SELECT COUNT(*) FROM event_outbox WHERE published_at IS NULL;

-- 最旧的未发布事件
SELECT MIN(created_at) FROM event_outbox WHERE published_at IS NULL;

-- 今日已发布事件
SELECT COUNT(*) FROM event_outbox 
WHERE published_at >= CURRENT_DATE;
```

## 更新历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-01-30 | 5f2b9b3c0e6f | 初始版本，创建表并修复手动建表漂移 |
