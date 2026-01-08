# Sparkle 项目组员配置指南

> **项目名称**: Sparkle (星火) AI 学习助手
> **项目版本**: MVP v0.3.0
> **最后更新**: 2026-01-08

---

## 📋 目录

1. [项目架构概览](#项目架构概览)
2. [前置环境要求](#前置环境要求)
3. [Git克隆与初始配置](#git克隆与初始配置)
4. [环境变量配置](#环境变量配置)
5. [后端服务配置](#后端服务配置)
6. [移动端配置](#移动端配置)
7. [VSCode插件推荐](#vscode插件推荐)
8. [开发工作流](#开发工作流)
9. [常见问题解决](#常见问题解决)
10. [验证安装](#验证安装)

---

## 🏗 项目架构概览

本项目采用**三层架构**设计：

```
┌─────────────────────────────────────────────────────────────┐
│  FLUTTER (移动端)  →  用户界面, 本地状态管理, WebSocket客户端  │
├─────────────────────────────────────────────────────────────┤
│  GO GATEWAY (网关)  →  认证, 路由, 缓存, 实时通信, 文件处理    │
├─────────────────────────────────────────────────────────────┤
│  PYTHON ENGINE (引擎)  →  AI逻辑, RAG, 工具调用, LLM集成      │
└─────────────────────────────────────────────────────────────┘
         ↕ PostgreSQL + pgvector    ↕ Redis    ↕ MinIO
```

**核心组件**:
- **Flutter Mobile**: 跨平台移动应用 (iOS/Android)
- **Go Gateway**: 高性能API网关和WebSocket服务器
- **Python Backend**: AI引擎和业务逻辑
- **PostgreSQL + pgvector**: 向量数据库
- **Redis**: 缓存和任务队列
- **MinIO**: 对象存储
- **Celery**: 异步任务队列
- **Observability**: Prometheus + Grafana + Tempo

---

## 🔧 前置环境要求

### 1. 操作系统支持
- ✅ **macOS** (推荐, 本指南主要针对macOS)
- ✅ **Linux** (Ubuntu/Debian/CentOS)
- ⚠️ **Windows** (需要WSL2)

### 2. 必需工具安装

#### Docker Desktop
```bash
# macOS 使用Homebrew安装
brew install --cask docker

# 验证安装
docker --version
docker compose version
```

#### Flutter SDK (v3.24.0+)
```bash
# macOS
brew install flutter

# 或手动下载
# 访问 https://flutter.dev/docs/get-started/install

# 验证安装
flutter --version

# 配置环境变量 (如果使用Homebrew)
echo 'export PATH="$PATH:/opt/homebrew/bin"' >> ~/.zshrc
source ~/.zshrc
```

#### Go (v1.24.0+)
```bash
# macOS
brew install go

# 验证安装
go version

# 配置GOPROXY (中国用户)
go env -w GOPROXY=https://goproxy.cn,direct
```

#### Python (v3.11+)
```bash
# macOS
brew install python@3.11

# 验证安装
python3 --version
pip3 --version

# 安装uv (快速包管理器)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 其他工具
```bash
# Node.js (用于某些构建工具)
brew install node

# Make (通常已预装)
make --version

# Git (通常已预装)
git --version
```

---

## 📥 Git克隆与初始配置

### 1. 克隆仓库
```bash
# 克隆项目
git clone https://github.com/BRSAMAyu/sparkle-flutter.git

# 进入项目目录
cd sparkle-flutter

# 检查远程仓库
git remote -v
# 应该显示:
# origin  https://github.com/BRSAMAyu/sparkle-flutter.git (fetch)
# origin  https://github.com/BRSAMAyu/sparkle-flutter.git (push)
```

### 2. 分支管理
```bash
# 查看所有分支
git branch -a

# 切换到主分支 (如果需要)
git checkout main

# 创建你的开发分支
git checkout -b feature/your-feature-name

# 或者切换到现有分支
git checkout 分支名
```

### 3. 拉取最新代码
```bash
# 更新主分支
git checkout main
git pull origin main

# 合并到你的分支 (如果需要)
git checkout your-branch
git merge main
```

---

## 🔐 环境变量配置

### 1. 创建环境文件
```bash
# 复制示例文件
cp .env.example .env.local

# 编辑环境变量
nano .env.local
```

### 2. 配置内容 (.env.local)
```env
# ==================== 数据库配置 ====================
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
DB_NAME=sparkle

# ==================== Redis配置 ====================
REDIS_PASSWORD=your_redis_password_here

# ==================== 安全配置 ====================
JWT_SECRET=your_jwt_secret_key_here_change_in_production

# ==================== LLM配置 (可选) ====================
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-key

# ==================== MinIO配置 (可选) ====================
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin_password

# ==================== 内部API密钥 ====================
INTERNAL_API_KEY=your_internal_api_key
```

### 3. 确保环境文件被忽略
检查 `.gitignore` 文件包含:
```
.env
.env.local
.env.*.local
```

---

## 🖥 后端服务配置

### 1. 启动基础设施 (数据库 + Redis + MinIO)
```bash
# 启动所有基础设施服务
make dev-up

# 检查容器状态
docker ps

# 查看日志
docker compose logs -f
```

### 2. 配置Python后端

#### 安装Python依赖
```bash
# 方法1: 使用uv (推荐,更快)
cd backend
uv pip install -r requirements.txt

# 方法2: 使用pip
cd backend
pip install -r requirements.txt
```

#### 数据库迁移
```bash
# 在backend目录下
cd backend

# 应用所有迁移
alembic upgrade head

# 查看迁移状态
alembic current
alembic heads
```

#### 启动Python gRPC服务器
```bash
# 在项目根目录
make grpc-server

# 或手动启动
cd backend
python grpc_server.py
```

### 3. 配置Go Gateway

#### 安装Go依赖
```bash
cd backend/gateway
go mod tidy
```

#### 生成数据库代码 (如果需要)
```bash
# 在项目根目录
make sync-db

# 这会:
# 1. 运行Python迁移
# 2. 导出PostgreSQL schema
# 3. 使用SQLC生成Go代码
```

#### 生成Protobuf代码
```bash
# 安装buf (如果未安装)
brew install bufbuild/buf/buf

# 生成代码
make proto-gen

# 或使用传统方式
make proto-gen-legacy
```

#### 启动Go Gateway
```bash
# 方法1: 使用Makefile
make gateway-run

# 方法2: 开发模式(自动重载)
make gateway-dev

# 方法3: 手动构建并运行
cd backend/gateway
go build -o bin/gateway ./cmd/server
./bin/gateway
```

### 4. 启动Celery任务队列
```bash
# 在项目根目录
make celery-up

# 查看状态
make celery-status

# 查看日志
make celery-logs-worker
```

---

## 📱 移动端配置

### 1. Flutter环境检查
```bash
# 检查Flutter环境
flutter doctor

# 修复常见问题
flutter doctor --android-licenses  # Android许可证
flutter doctor --ios               # iOS环境检查
```

### 2. 安装依赖
```bash
cd mobile

# 安装pub依赖
flutter pub get

# 生成代码 (Riverpod, Retrofit, JSON序列化等)
flutter pub run build_runner build --delete-conflicting-outputs

# 或使用热重载开发
flutter pub run build_runner watch
```

### 3. 配置iOS (如果需要)
```bash
cd mobile/ios
pod install --repo-update
```

### 4. 运行应用
```bash
# 列出可用设备
flutter devices

# 运行在模拟器/设备
flutter run

# 指定设备
flutter run -d "iPhone 15"

# 运行在Web
flutter run -d chrome

# Release模式构建
flutter build apk --release
flutter build ios --release
```

### 5. macOS特定问题解决
如果遇到CC/CXX环境变量冲突:
```bash
# 临时解决
unset CC CXX
flutter run

# 永久解决 (添加到 ~/.zshrc)
echo 'unset CC CXX' >> ~/.zshrc
source ~/.zshrc
```

---

## 💻 VSCode插件推荐

### 必需插件

#### Flutter/Dart开发
- **Flutter** (Dart Code) - 官方Flutter扩展
- **Dart** - Dart语言支持
- **Riverpod** - Riverpod状态管理语法高亮

#### Go开发
- **Go** (官方) - Go语言支持
- **Go Nightly** - 预览版特性

#### Python开发
- **Python** (Microsoft) - Python支持
- **Pylance** - 类型检查和智能提示
- **Ruff** - 快速Linting

#### Docker/容器
- **Docker** - 容器管理

#### Git
- **GitLens** - Git增强工具
- **Git Graph** - Git分支可视化

#### 代码质量
- **Code Spell Checker** - 拼写检查
- **Error Lens** - 错误内联显示
- **Prettier** - 代码格式化

#### Protobuf
- **vscode-proto3** - Proto文件语法支持

### 推荐VSCode设置

在项目根目录创建 `.vscode/settings.json`:

```json
{
  "files.associations": {
    "*.proto": "proto3"
  },
  "[dart]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    },
    "editor.rulers": [80, 120]
  },
  "[go]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    },
    "editor.tabSize": 4
  },
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    },
    "editor.tabSize": 4
  },
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "go.gopath": "~/go",
  "go.toolsManagement.checkForUpdates": "local",
  "flutter.closingLabels": true,
  "flutter.hotReloadOnSave": "all",
  "flutter.previewFlutterUiGuides": true,
  "flutter.allowAnalytics": false,
  "ruff.importStrategy": "fromEnvironment",
  "ruff.fixAll": true,
  "ruff.lintOnSave": true
}
```

---

## 🚀 开发工作流

### 日常开发流程

#### 1. 启动开发环境
```bash
# 终端1: 启动基础设施
make dev-up

# 终端2: 启动Celery
make celery-up

# 终端3: 启动Python gRPC服务器
make grpc-server

# 终端4: 启动Go Gateway
make gateway-dev

# 终端5: 运行Flutter应用
cd mobile
flutter run
```

#### 2. 代码修改与测试
```bash
# Flutter代码修改后会自动热重载
# Python代码修改后需要重启grpc-server
# Go代码修改后会自动重编译 (gateway-dev模式)
# Proto修改后需要重新生成:
make proto-gen

# DB Schema修改后:
make sync-db
```

#### 3. 提交代码前检查
```bash
# Flutter分析
cd mobile
flutter analyze

# Python linting
cd backend
ruff check .
mypy . --ignore-missing-imports

# Go linting
cd backend/gateway
go vet ./...
```

### 关键命令速查

| 命令 | 作用 | 使用场景 |
|------|------|----------|
| `make dev-up` | 启动基础设施 | 开始开发前 |
| `make dev-all` | 启动所有服务 | 全栈开发 |
| `make grpc-server` | Python gRPC服务 | 后端开发 |
| `make gateway-dev` | Go网关开发模式 | 网关开发 |
| `make proto-gen` | 生成Proto代码 | API修改后 |
| `make sync-db` | 同步数据库 | DB修改后 |
| `make celery-up` | 启动任务队列 | 异步任务开发 |
| `flutter pub run build_runner build` | 生成Dart代码 | Flutter代码生成 |
| `flutter analyze` | 静态分析 | 代码质量检查 |

---

## 🐛 常见问题解决

### 1. Flutter构建问题

#### CC/CXX环境变量冲突
```bash
# 临时解决
unset CC CXX
flutter run

# 永久解决
echo 'unset CC CXX' >> ~/.zshrc
source ~/.zshrc
```

#### 依赖版本冲突
```bash
cd mobile
flutter clean
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
```

### 2. Docker问题

#### 容器启动失败
```bash
# 查看日志
docker compose logs <service_name>

# 重启特定服务
docker compose restart <service_name>

# 完全清理重启
docker compose down -v
docker compose up -d
```

#### 端口冲突
```bash
# 查看端口占用
lsof -i :8080  # Go Gateway
lsof -i :8000  # Python Backend
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# 杀掉占用进程
kill -9 <PID>
```

### 3. Python依赖问题

#### pip安装失败
```bash
# 使用uv加速
cd backend
uv pip install -r requirements.txt

# 或使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### Alembic迁移问题
```bash
# 查看当前状态
alembic current

# 查看历史
alembic history

# 降级到指定版本
alembic downgrade <revision_id>

# 重新生成迁移
alembic revision --autogenerate -m "描述"
```

### 4. Go模块问题

```bash
cd backend/gateway
go mod tidy
go mod download

# 清理缓存
go clean -modcache
```

### 5. 数据库连接问题

```bash
# 检查PostgreSQL是否运行
docker ps | grep sparkle_db

# 连接数据库测试
docker exec -it sparkle_db psql -U postgres -d sparkle

# 查看数据库日志
docker logs sparkle_db
```

### 6. Redis连接问题

```bash
# 测试Redis连接
docker exec -it sparkle_redis redis-cli ping

# 查看Redis日志
docker logs sparkle_redis
```

---

## ✅ 验证安装

### 1. 验证基础设施
```bash
# 检查所有容器
docker ps

# 应该看到:
# - sparkle_db (PostgreSQL + pgvector)
# - sparkle_redis
# - sparkle_minio
```

### 2. 验证Python后端
```bash
# 测试gRPC服务
cd backend
python test_grpc_simple.py

# 检查端口
lsof -i :50051
```

### 3. 验证Go Gateway
```bash
# 测试健康检查
curl http://localhost:8080/health

# 应该返回: {"status":"healthy"}
```

### 4. 验证Flutter应用
```bash
cd mobile
flutter analyze

# 如果没有错误，说明配置正确
# 运行应用测试连接
flutter run
```

### 5. 端到端测试
```bash
# 启动所有服务后
make integration-test
```

---

## 📚 项目文档

### 重要文档位置
- **技术架构**: `docs/00_项目概览/02_技术架构.md`
- **API参考**: `docs/02_技术设计文档/03_API参考.md`
- **知识星图设计**: `docs/02_技术设计文档/02_知识星图系统设计_v3.0.md`
- **完整技术文档**: `docs/深度技术讲解教案_完整版.md`

### Git工作流参考
- **主分支**: `main` (稳定版本)
- **开发分支**: `develop` (最新开发)
- **功能分支**: `feature/feature-name`
- **修复分支**: `fix/bug-description`

---

## 🎯 下一步

配置完成后，你可以:

1. **运行完整开发环境**:
   ```bash
   make dev-all
   ```

2. **查看监控面板**:
   - Flower (Celery): http://localhost:5555
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090

3. **开始开发**:
   - 阅读现有代码了解架构
   - 查看TODO列表或issues
   - 创建你的第一个功能分支

---

## 🆘 寻求帮助

如果遇到问题:

1. **检查日志**: `docker compose logs -f <service>`
2. **查看文档**: 项目内docs目录
3. **询问团队**: 在团队群组中提问
4. **提交Issue**: 在GitHub上创建issue

---

**祝你开发愉快！🚀**

*本文档由项目维护者编写，如有疑问请联系项目负责人。*
