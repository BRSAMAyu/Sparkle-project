# Knowledge Galaxy 完整部署指南

本指南将帮助你完成知识星图系统的完整部署和测试。

## 📋 前置条件检查

### 1. Python 环境
```bash
python --version  # 应该是 Python 3.11 或更高
```

### 2. PostgreSQL 数据库
```bash
# 检查 PostgreSQL 是否安装
psql --version

# 或者使用 SQLite (开发环境)
sqlite3 --version
```

### 3. 安装 pgvector 扩展 (如果使用 PostgreSQL)
```sql
-- 在 PostgreSQL 中执行
CREATE EXTENSION IF NOT EXISTS vector;
```

## 🚀 Step-by-Step 部署流程

### Step 1: 配置环境变量

创建或更新 `backend/.env` 文件：

```env
# Application
APP_NAME=Sparkle
APP_VERSION=0.1.0
DEBUG=True
SECRET_KEY=your-super-secret-key-change-in-production

# Database - PostgreSQL (推荐)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/sparkle

# 或者 SQLite (开发环境)
# DATABASE_URL=sqlite+aiosqlite:///./sparkle.db

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256

# LLM Service (Qwen 示例)
LLM_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your_qwen_api_key
LLM_MODEL_NAME=qwen-turbo
LLM_PROVIDER=qwen

# Embedding Service
EMBEDDING_MODEL=text-embedding-v2
EMBEDDING_DIM=1536

# File Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760

# Logging
LOG_LEVEL=INFO
```

### Step 2: 安装依赖

```bash
cd backend

# 创建虚拟环境 (如果还没有)
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 确认 pgvector 已安装
pip show pgvector
```

### Step 3: 运行数据库迁移

```bash
cd backend

# 方法1: 使用 alembic (推荐)
alembic upgrade head

# 方法2: 如果 alembic 命令不可用
python -m alembic upgrade head

# 方法3: 直接使用 Python
python -c "from alembic.config import Config; from alembic import command; alembic_cfg = Config('alembic.ini'); command.upgrade(alembic_cfg, 'head')"
```

**常见问题:**

如果遇到 `pgvector` 导入错误:
```python
# 临时解决方案: 修改迁移文件
# 在 backend/alembic/versions/54e1f05154ad_add_galaxy_v2_tables.py 中
# 将 from pgvector.sqlalchemy import Vector
# 改为条件导入 (已在之前的步骤中完成)
```

### Step 4: 更新现有学科数据 (可选)

如果数据库中已经有学科数据，运行此脚本为它们添加星域字段：

```bash
cd backend
python seed_data/update_subjects.py
```

### Step 5: 加载种子数据

```bash
cd backend
python seed_data/load_seed_data.py
```

**期望输出:**
```
开始加载种子数据...

处理文件: tech.json
  创建学科: 计算机科学 (TECH)
  创建节点: Python基础
  创建节点: 数据结构
  ...

✅ 种子数据加载完成!
```

### Step 6: 启动服务器

```bash
cd backend

# 开发模式 (自动重载)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**检查启动日志:**
```
INFO:     Starting Sparkle API Server...
INFO:     ExpansionWorker started
INFO:     Scheduler started with fragmented time check and daily decay jobs
INFO:     Sparkle API Server started successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 7: 验证 API

访问 Swagger 文档: http://localhost:8000/docs

你应该看到以下新增的 Galaxy 端点:
- `GET /api/v1/galaxy/graph`
- `POST /api/v1/galaxy/node/{node_id}/spark`
- `GET /api/v1/galaxy/node/{node_id}`
- `POST /api/v1/galaxy/search`
- `GET /api/v1/galaxy/review/suggestions`
- `POST /api/v1/galaxy/node/{node_id}/decay/pause`
- `GET /api/v1/galaxy/stats`
- `GET /api/v1/galaxy/events` (SSE)

## 🧪 测试流程

### Test 1: 注册/登录用户

```bash
# 注册用户
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test123456",
    "email": "test@example.com"
  }'

# 登录获取 token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test123456"
  }'

# 保存返回的 access_token
export TOKEN="your_access_token_here"
```

### Test 2: 获取星图数据

```bash
curl -X GET "http://localhost:8000/api/v1/galaxy/graph" \
  -H "Authorization: Bearer $TOKEN"
```

**期望输出:**
```json
{
  "nodes": [
    {
      "id": "...",
      "name": "Python基础",
      "importance_level": 2,
      "sector_code": "TECH",
      "is_seed": true,
      "user_status": null,
      "position_angle": 60.0,
      "position_radius": 160.0
    },
    ...
  ],
  "relations": [],
  "user_stats": {
    "total_nodes": 13,
    "unlocked_count": 0,
    "mastered_count": 0,
    "total_study_minutes": 0,
    "sector_distribution": {},
    "streak_days": 0
  }
}
```

### Test 3: 点亮知识节点

首先获取一个节点 ID，然后：

```bash
# 替换 NODE_ID 为实际的节点 UUID
NODE_ID="..."

curl -X POST "http://localhost:8000/api/v1/galaxy/node/$NODE_ID/spark" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "study_minutes": 30,
    "trigger_expansion": true
  }'
```

**期望输出:**
```json
{
  "spark_event": {
    "node_id": "...",
    "node_name": "Python基础",
    "sector_code": "TECH",
    "old_mastery": 0.0,
    "new_mastery": 5.0,
    "is_first_unlock": true,
    "is_level_up": false,
    "particle_count": 20,
    "animation_duration_ms": 1500
  },
  "expansion_queued": false,
  "updated_status": {...}
}
```

### Test 4: 语义搜索

```bash
curl -X POST "http://localhost:8000/api/v1/galaxy/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "编程算法",
    "limit": 5,
    "threshold": 0.3
  }'
```

### Test 5: SSE 事件流 (前端测试)

使用浏览器或工具连接:
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/galaxy/events',
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

eventSource.addEventListener('nodes_expanded', (event) => {
  const data = JSON.parse(event.data);
  console.log('New nodes:', data.nodes);
});
```

### Test 6: 触发 LLM 拓展

再次点亮同一个节点 (达到 study_count = 2):

```bash
curl -X POST "http://localhost:8000/api/v1/galaxy/node/$NODE_ID/spark" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "study_minutes": 25,
    "trigger_expansion": true
  }'
```

**检查日志:**
```
INFO:     Found 1 pending expansion tasks
INFO:     Processing expansion task ... for node ...
INFO:     Expansion task ... completed: created 3 new nodes
INFO:     Sent SSE notification to user ... for 3 new nodes
```

### Test 7: 查看复习建议

```bash
curl -X GET "http://localhost:8000/api/v1/galaxy/review/suggestions?limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

### Test 8: 测试定时任务

定时任务会自动运行：
- **碎片时间检查**: 每 15 分钟
- **每日衰减**: 每天凌晨 3:00

手动触发测试（在 Python console 中）:
```python
import asyncio
from app.db.session import async_session_maker
from app.services.decay_service import DecayService

async def test_decay():
    async with async_session_maker() as db:
        service = DecayService(db)
        stats = await service.apply_daily_decay()
        print(stats)

asyncio.run(test_decay())
```

## 🐛 常见问题排查

### 问题 1: 迁移失败 - pgvector 模块未找到

**解决方案:**
```bash
pip install pgvector
# 或者使用 SQLite (自动跳过 pgvector)
```

### 问题 2: LLM API 调用失败

**检查:**
1. `.env` 中的 `LLM_API_KEY` 是否正确
2. API 配额是否充足
3. 网络连接是否正常

**临时禁用拓展:**
```python
# 在点亮节点时设置
{
  "study_minutes": 30,
  "trigger_expansion": false  # 禁用 LLM 拓展
}
```

### 问题 3: 向量搜索返回空结果

**原因:** 节点的 embedding 字段为空

**解决方案:**
重新运行种子数据加载，确保 LLM API 可用。

### 问题 4: SSE 连接断开

**检查:**
1. 前端是否正确处理连接断开和重连
2. Nginx/代理是否禁用了缓冲 (`proxy_buffering off`)
3. 防火墙是否允许长连接

## 📊 性能监控

### 检查后台任务状态

```bash
# 查看日志
tail -f backend/logs/app.log

# 检查 ExpansionWorker
grep "ExpansionWorker" backend/logs/app.log

# 检查衰减任务
grep "Daily decay" backend/logs/app.log
```

### 数据库查询

```sql
-- 查看知识节点数量
SELECT sector_code, COUNT(*)
FROM subjects s
JOIN knowledge_nodes kn ON s.id = kn.subject_id
GROUP BY sector_code;

-- 查看待处理的拓展任务
SELECT status, COUNT(*)
FROM node_expansion_queue
GROUP BY status;

-- 查看用户学习统计
SELECT
  u.username,
  COUNT(DISTINCT uns.node_id) as unlocked_nodes,
  SUM(uns.total_study_minutes) as total_minutes
FROM users u
LEFT JOIN user_node_status uns ON u.id = uns.user_id
WHERE uns.is_unlocked = true
GROUP BY u.id, u.username;
```

## 🎯 下一步: 前端集成

1. **Flutter 依赖安装**
```yaml
dependencies:
  dio: ^5.0.0
  flutter_riverpod: ^2.0.0
  go_router: ^12.0.0
  freezed_annotation: ^2.0.0
  json_annotation: ^4.8.0
  # ... 其他依赖
```

2. **连接 API**
```dart
// lib/core/network/api_endpoints.dart
class ApiEndpoints {
  static const baseUrl = 'http://localhost:8000';
  static const galaxyGraph = '/api/v1/galaxy/graph';
  static const sparkNode = '/api/v1/galaxy/node';
  static const galaxyEvents = '/api/v1/galaxy/events';
}
```

3. **实现星图渲染**
- CustomPaint for star rendering
- GestureDetector for interaction
- AnimatedBuilder for spark animations

## ✅ 完成检查清单

- [ ] 数据库迁移成功
- [ ] 种子数据加载成功
- [ ] 服务器正常启动
- [ ] API 文档可访问
- [ ] 用户注册/登录正常
- [ ] 获取星图数据成功
- [ ] 点亮节点功能正常
- [ ] LLM 拓展队列工作正常
- [ ] SSE 事件流连接成功
- [ ] 语义搜索返回结果
- [ ] 定时任务日志正常

---

**祝部署顺利！** 🎉

如有问题，请查看:
- API 文档: http://localhost:8000/docs
- 日志文件: `backend/logs/`
- 设计文档: `backend/# Sparkle 知识星图 (Knowledge Galaxy) 系统设计文档.md`
