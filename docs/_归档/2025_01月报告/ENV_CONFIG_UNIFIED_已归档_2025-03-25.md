# 环境配置统一规范 (Environment Configuration Standard)

## 问题诊断 (Problem Diagnosis)

当前系统存在多个环境配置不一致：

1. **backend/.env** (本地开发):
   - DATABASE_URL: `postgres:password@localhost:5432/sparkle`
   - REDIS_URL: `redis://localhost:6379/0` (无密码)

2. **docker-compose.yml** (容器环境):
   - POSTGRES_PASSWORD: `${DB_PASSWORD:-change-me}`
   - REDIS_PASSWORD: `${REDIS_PASSWORD:-change-me}`

3. **backend/.env.example**:
   - DATABASE_URL: `sparkle_user:sparkle_password@localhost:5432/sparkle_db`

4. **根目录 .env**:
   - REDIS_PASSWORD: `devpassword`

**结果**: 测试无法在不同环境间一致运行，CI 失败。

---

## 统一方案 (Unified Solution)

### 1. 标准密码配置 (Standard Credentials)

**开发环境统一密码** (适用于本地和 Docker):

```bash
# PostgreSQL
DB_USER=postgres
DB_PASSWORD=devpassword
DB_NAME=sparkle

# Redis
REDIS_PASSWORD=devpassword

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

**理由**: 使用简单、易记的密码，避免在开发环境中过度安全化（生产环境单独配置）。

---

### 2. 文件结构标准化

```
sparkle-flutter/
├── .env.example              # 根目录环境变量模板（Docker 使用）
├── .env                      # 根目录实际配置（gitignore）
├── backend/
│   ├── .env.example          # Backend 环境变量模板（本地开发）
│   └── .env                  # Backend 实际配置（gitignore）
└── docker-compose.yml        # 容器编排（使用根目录 .env）
```

---

### 3. 配置文件内容

#### 根目录 `.env.example` (Docker 环境)

```bash
# Database
DB_USER=postgres
DB_PASSWORD=devpassword
DB_NAME=sparkle

# Redis
REDIS_PASSWORD=devpassword

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# Backend
DATABASE_URL=postgresql://postgres:devpassword@sparkle_db:5432/sparkle
REDIS_URL=redis://:devpassword@sparkle_redis:6379/0
CELERY_BROKER_URL=redis://:devpassword@sparkle_redis:6379/1
CELERY_RESULT_BACKEND=redis://:devpassword@sparkle_redis:6379/2

# LLM
LLM_API_KEY=your-llm-api-key
INTERNAL_API_KEY=dev-internal-key
```

#### backend/.env.example (本地开发环境)

```bash
# Application Settings
APP_NAME=Sparkle
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production

# Database (本地 PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:devpassword@localhost:5432/sparkle

# Redis (本地 Redis)
REDIS_URL=redis://:devpassword@localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://:devpassword@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:devpassword@localhost:6379/2

# LLM Service
LLM_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your-llm-api-key
LLM_MODEL_NAME=qwen3-coder-plus
LLM_PROVIDER=qwen

# Internal API
INTERNAL_API_KEY=dev-internal-key
```

---

### 4. 快速修复步骤 (Quick Fix Steps)

```bash
# 1. 停止所有容器
cd /Users/a/code/sparkle-flutter
docker compose down -v

# 2. 清理旧配置
rm -f .env backend/.env

# 3. 复制统一配置
cp .env.example .env
cp backend/.env.example backend/.env

# 4. 编辑密码（如果需要）
# 确保所有地方都使用 devpassword

# 5. 重启容器
docker compose up -d sparkle_db redis

# 6. 等待健康检查通过
docker compose ps

# 7. 运行迁移
cd backend && alembic upgrade head

# 8. 运行测试验证
pytest tests/ -v
```

---

### 5. CI/CD 配置 (GitHub Actions)

在 `.github/workflows/test.yml` 中使用统一密码：

```yaml
env:
  DATABASE_URL: postgresql+asyncpg://postgres:devpassword@localhost:5432/sparkle
  REDIS_URL: redis://:devpassword@localhost:6379/0

services:
  postgres:
    image: pgvector/pgvector:pg16
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: devpassword
      POSTGRES_DB: sparkle

  redis:
    image: redis:7
    options: >-
      --health-cmd "redis-cli -a devpassword ping"
      --requirepass devpassword
```

---

### 6. 验证检查清单 (Verification Checklist)

- [ ] 根目录 `.env` 和 backend/.env` 密码一致
- [ ] docker-compose.yml 默认值与 .env.example 一致
- [ ] 本地可以成功运行 `pytest`
- [ ] Docker 容器可以成功启动并通过健康检查
- [ ] CI 测试可以通过
- [ ] 文档已更新（README.md）

---

### 7. 生产环境差异 (Production Differences)

⚠️ **警告**: 生产环境必须使用强密码和以下安全措施：

1. 使用 Secrets Manager（AWS Secrets Manager / Vault）
2. 启用 PostgreSQL SSL (`sslmode=require`)
3. Redis 启用 TLS
4. 使用环境变量注入，避免 .env 文件

```bash
# 生产环境示例
DATABASE_URL=postgresql+asyncpg://prod_user:$(aws secretsmanager get-secret-value --secret-id prod/db)@prod-db.rds.amazonaws.com:5432/sparkle?sslmode=require
```

---

## 下一步行动 (Next Actions)

1. **立即**: 更新 `.env.example` 文件
2. **测试**: 在干净环境中验证
3. **文档**: 更新 README.md 的"快速开始"部分
4. **团队**: 通知团队成员更新本地配置
