# Sparkle 环境配置指南

> 📝 生成时间: 2026-02-10
> 📦 项目路径: `/Users/brsama/code/GitHub/Sparkle-project`

---

## 📋 环境需求清单

### 必需环境
- **Python:** 3.11+（当前系统: 3.9.6，建议升级）
- **Go:** 1.20+（已安装: go1.25.7）✅
- **Docker:** 已安装（需要启动 colima）✅
- **uv:** 已安装 v0.10.0 ✅

### 可选环境
- **Flutter:** 用于移动端开发（较大，可选）

### 外部服务（需要 API Keys）
- **通义千问 (DashScope):** LLM 服务
- **DeepSeek:** LLM 推理服务
- **讯飞 STT (XunFei):** 语音转文字
- **SiliconFlow:** 嵌入与重排服务

---

## 🚀 快速开始

### 方式 1: 自动配置（推荐）

```bash
cd ~/code/GitHub/Sparkle-project
bash setup_env.sh
```

**选项：**
- `--skip-flutter` - 跳过 Flutter 安装
- `--skip-docker` - 跳过 Docker 启动

**示例：**
```bash
bash setup_env.sh --skip-flutter  # 不安装 Flutter
```

---

### 方式 2: 手动配置

#### 步骤 1: 启动 Docker

```bash
# 启动 colima（如果 Docker 未运行）
colima start --cpu 2 --memory 4

# 或使用项目脚本
bash ~/ops/amadeus_setup_20260210/scripts/start_colima.sh
```

#### 步骤 2: 创建 Python 虚拟环境

```bash
cd ~/code/GitHub/Sparkle-project
uv venv venvs/sparkle --python 3.11
source venvs/sparkle/bin/activate
```

#### 步骤 3: 安装 Python 依赖

```bash
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
```

#### 步骤 4: 配置环境变量

```bash
# 复制示例配置
cp backend/.env.example .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

**必需配置的 API Keys：**

```env
# 通义千问（必需）
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# DeepSeek（推荐）
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 讯飞 STT（如需语音功能）
XUNFEI_API_KEY=your_xunfei_key
XUNFEI_API_SECRET=your_xunfei_secret

# SiliconFlow（推荐，用于嵌入）
SILICONFLOW_API_KEY=your_siliconflow_api_key_here
```

#### 步骤 5: 启动基础设施

```bash
cd ~/code/GitHub/Sparkle-project
docker compose up -d sparkle_db redis minio
```

#### 步骤 6: 运行数据库迁移

```bash
cd backend
alembic upgrade head
```

#### 步骤 7: 配置 Go Gateway

```bash
cd backend/gateway
go mod download
```

#### 步骤 8: 生成 Protobuf 代码（可选）

```bash
cd ~/code/GitHub/Sparkle-project
make proto-gen
```

---

## 🎯 启动服务

### 分终端启动（开发模式）

**终端 1: Python gRPC 服务**
```bash
cd ~/code/GitHub/Sparkle-project
source venvs/sparkle/bin/activate
cd backend
python grpc_server.py
```

**终端 2: Go Gateway**
```bash
cd ~/code/GitHub/Sparkle-project/backend/gateway
go run cmd/server/main.go
```

**终端 3: Flutter 应用（可选）**
```bash
cd ~/code/GitHub/Sparkle-project/mobile
flutter run
```

### 使用 Makefile

```bash
cd ~/code/GitHub/Sparkle-project

# 启动基础设施
make dev-up

# 启动 Python gRPC 服务
make grpc-server

# 启动 Go Gateway
make gateway-dev

# 健康检查
make smoke
```

---

## 🔍 验证配置

### 健康检查

```bash
cd ~/code/GitHub/Sparkle-project
make smoke
```

预期输出：
```
🔎 Running config self-check...
🔎 Checking backend health...
🔎 Checking gateway health...
✅ Smoke checks passed.
```

### 手动验证

```bash
# 检查数据库
docker ps | grep sparkle_db

# 检查 Python 环境
source venvs/sparkle/bin/activate
python -c "import fastapi, langgraph, grpcio; print('OK')"

# 检查 Go 依赖
cd backend/gateway && go version
```

---

## 📦 依赖说明

### Python 后端依赖

| 分类 | 主要包 |
|------|--------|
| **Web 框架** | fastapi, uvicorn |
| **数据库** | sqlalchemy, asyncpg, pgvector, redis |
| **LLM & AI** | openai, dashscope, langgraph, langchain |
| **gRPC** | grpcio, grpcio-tools |
| **任务队列** | celery |
| **测试** | pytest, pytest-asyncio |

### Go Gateway 依赖

- **框架:** Gin
- **数据库:** sqlx
- **gRPC:** google.golang.org/grpc
- **认证:** jwt-go

### Flutter 依赖

- **状态管理:** Riverpod
- **网络:** dio
- **gRPC:** grpc

---

## 🛠️ 常用命令

```bash
# === 数据库 ===
make db-migrate        # 运行迁移
make db-dump           # 导出 Schema
make db-sqlc           # 生成 Go 代码

# === Protobuf ===
make proto-gen        # 生成所有语言代码
make proto-lint        # 检查协议定义
make proto-breaking    # 检查破坏性变更

# === 测试 ===
cd backend && pytest               # Python 测试
cd backend/gateway && go test ./...  # Go 测试

# === Celery ===
make celery-up        # 启动 Celery
make celery-logs      # 查看日志
make celery-flush     # 清空队列

# === 清理 ===
docker compose down   # 停止基础设施
make db-reset         # 重置数据库
```

---

## ⚠️ 常见问题

### 1. Python 版本过低

**问题:** 系统自带 Python 3.9.6，项目需要 3.11+

**解决:**
```bash
# 使用 pyenv 安装 Python 3.11
brew install pyenv
pyenv install 3.11.14
pyenv global 3.11.14
```

### 2. Docker 不可用

**问题:** `docker: command not found`

**解决:**
```bash
# 启动 colima
colima start --cpu 2 --memory 4

# 或使用项目脚本
bash ~/ops/amadeus_setup_20260210/scripts/start_colima.sh
```

### 3. 数据库迁移失败

**问题:** `alembic upgrade head` 失败

**解决:**
```bash
# 检查容器状态
docker ps | grep sparkle_db

# 强制 stamp
FORCE_STAMP=1 make db-migrate
```

### 4. LLM API 调用失败

**问题:** 无法调用通义千问/DeepSeek

**解决:**
- 检查 `.env` 中的 API Keys 是否正确
- 验证网络连接：`curl https://dashscope.aliyuncs.com`

---

## 📚 参考资料

- **项目 README:** [README.md](README.md)
- **Claude Code 开发指南:** [CLAUDE.md](CLAUDE.md)
- **认知引擎设计:** [docs/09_Cognitive_Nexus/](docs/09_Cognitive_Nexus/)
- **深度技术讲解:** [docs/深度技术讲解教案_完整版.md](docs/深度技术讲解教案_完整版.md)

---

## 🆘 获取帮助

```bash
# 查看所有可用命令
make help

# 环境配置检查
make env-check

# 查看日志
docker logs -f sparkle_db
docker logs -f sparkle_redis
```

---

*最后更新: 2026-02-10*
