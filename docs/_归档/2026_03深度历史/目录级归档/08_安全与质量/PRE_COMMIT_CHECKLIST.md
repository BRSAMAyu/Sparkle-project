# Git 提交前检查清单

> **目的**: 确保代码提交后，组员可以直接拉取并运行项目，无需额外配置

---

## 📋 Git 配置检查

### 1. 远程仓库配置
```bash
# 检查远程仓库
git remote -v

# 应该显示:
# origin  https://github.com/BRSAMAyu/sparkle-flutter.git (fetch)
# origin  https://github.com/BRSAMAyu/sparkle-flutter.git (push)
```

### 2. 分支状态
```bash
# 查看当前分支
git branch

# 确保在正确的功能分支上
# 推荐命名: feature/xxx, fix/xxx, refactor/xxx

# 查看未提交的更改
git status
```

### 3. 确保忽略敏感文件
检查 `.gitignore` 确保包含:
```
.env
.env
.env.*.local
*.db
*.sqlite
postgres_data/
redis_data/
minio_data/
backend/gateway/bin/
backend/app/__pycache__/
mobile/build/
mobile/.dart_tool/
```

---

## 🔧 环境文件检查

### 1. 确保环境模板存在
```bash
# 检查 .env.example 是否存在且完整
ls -la .env.example

# 检查 backend 环境模板
ls -la backend/.env.example
```

### 2. 验证环境变量模板内容
`.env.example` 应该包含:
```env
# 数据库
DB_USER=postgres
DB_PASSWORD=change-me
DB_NAME=sparkle

# Redis
REDIS_PASSWORD=change-me

# 安全
JWT_SECRET=change-me-in-production

# LLM (可选)
LLM_API_BASE_URL=
LLM_API_KEY=

# MinIO (可选)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# 内部API密钥
INTERNAL_API_KEY=
```

---

## 📦 依赖文件检查

### 1. Python 依赖
```bash
# 检查 requirements.txt 存在
ls -la backend/requirements.txt

# 验证没有绝对路径
grep -v "^/" backend/requirements.txt | head -20
```

### 2. Go 依赖
```bash
# 检查 go.mod 和 go.sum
ls -la backend/gateway/go.mod
ls -la backend/gateway/go.sum

# 验证模块路径正确
head -5 backend/gateway/go.mod
```

### 3. Flutter 依赖
```bash
# 检查 pubspec.yaml
ls -la mobile/pubspec.yaml

# 验证没有本地路径依赖
grep "path:" mobile/pubspec.yaml || echo "✅ 无本地路径依赖"
```

---

## 🔐 生成代码检查

### 1. Protobuf 生成代码
```bash
# 检查 Go 生成代码
ls -la backend/gateway/gen/agent/v1/
ls -la backend/gateway/gen/galaxy/v1/

# 检查 Python 生成代码
ls -la backend/app/gen/agent/v1/
ls -la backend/app/gen/galaxy/v1/
```

### 2. SQLC 生成代码 (Go)
```bash
# 检查生成的数据库代码
ls -la backend/gateway/internal/db/models.go
ls -la backend/gateway/internal/db/query.sql.go

# 检查 schema.sql
ls -la backend/gateway/internal/db/schema.sql
```

### 3. Flutter 生成代码
```bash
# 检查关键的生成文件
ls -la mobile/lib/core/services/chat_service.g.dart 2>/dev/null || echo "需要运行 build_runner"
ls -la mobile/lib/presentation/providers/*.g.dart 2>/dev/null | head -5 || echo "需要运行 build_runner"
```

---

## 🗄️ 数据库迁移检查

### 1. Alembic 迁移文件
```bash
# 检查迁移目录
ls -la backend/alembic/versions/ | head -10

# 验证迁移文件存在
count=$(ls backend/alembic/versions/*.py 2>/dev/null | wc -l)
echo "迁移文件数量: $count"
```

### 2. 迁移状态
```bash
# 如果有本地数据库，检查迁移状态
cd backend
alembic current 2>/dev/null || echo "数据库未启动"
```

---

## 📄 文档检查

### 1. 必需文档
```bash
# 检查关键文档
ls -la README.md
ls -la SETUP_GUIDE.md
ls -la CLAUDE.md
```

### 2. 文档链接检查
```bash
# 验证文档中链接的有效性 (可选)
grep -r "docs/" README.md | head -5
```

---

## 🚫 排除项检查

### 1. 确保不提交的内容
```bash
# 检查是否有大文件
find . -size +100M -not -path "*/\.*" 2>/dev/null

# 检查是否有临时文件
find . -name "*.tmp" -o -name "*.temp" -o -name "*.bak" 2>/dev/null

# 检查是否有敏感信息
grep -r "password.*=" .env 2>/dev/null || echo "✅ 无敏感信息"
```

### 2. 检查生成的二进制文件
```bash
# 确保没有提交二进制
git ls-files | grep -E "\.(exe|bin|so|dylib|a)$" || echo "✅ 无二进制文件"

# 检查是否有构建产物
git ls-files | grep "^mobile/build/" || echo "✅ 无构建产物"
```

---

## 🧪 功能完整性检查

### 1. 核心配置文件存在性
```bash
# 项目结构检查清单
required_files=(
    "docker-compose.yml"
    "Makefile"
    ".env.example"
    "backend/requirements.txt"
    "backend/alembic.ini"
    "backend/gateway/go.mod"
    "backend/gateway/sqlc.yaml"
    "mobile/pubspec.yaml"
    "proto/agent_service.proto"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file 缺失"
    fi
done
```

### 2. 关键目录结构
```bash
# 检查目录完整性
required_dirs=(
    "backend/app"
    "backend/gateway"
    "backend/alembic/versions"
    "mobile/lib"
    "proto"
    "docs"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir/"
    else
        echo "❌ $dir/ 缺失"
    fi
done
```

---

## 📝 提交前最终检查

### 1. 代码质量检查
```bash
# Flutter 静态分析
cd mobile
flutter analyze --no-fatal-infos

# Python linting (如果安装了工具)
cd backend
ruff check . 2>/dev/null || echo "ruff 未安装，跳过"

# Go vet (如果安装了Go)
cd backend/gateway
go vet ./... 2>/dev/null || echo "go 未安装，跳过"
```

### 2. 生成文件完整性
```bash
# 确保所有生成文件都是最新的
echo "如果以下文件缺失，需要运行:"
echo "  - Flutter: flutter pub run build_runner build --delete-conflicting-outputs"
echo "  - Protobuf: make proto-gen"
echo "  - SQLC: make sync-db"
```

### 3. 提交信息规范
```bash
# 推荐的提交信息格式
# 类型(范围): 简短描述
#
# 详细描述 (可选)
#
# 例如:
# feat(auth): 添加JWT自动刷新机制
#
# - 实现token过期检测
# - 自动刷新逻辑
# - 错误处理
```

---

## 🎯 组员拉取后快速验证

### 1. 组员执行的命令序列
```bash
# 1. 克隆项目
git clone https://github.com/BRSAMAyu/sparkle-flutter.git
cd sparkle-flutter

# 2. 创建环境文件
cp .env.example .env
# 编辑 .env 填入实际配置

# 3. 启动基础设施
make dev-up

# 4. 启动后端服务 (3个终端)
make grpc-server    # 终端1
make gateway-dev    # 终端2
make celery-up      # 终端3

# 5. 启动移动端 (终端4)
cd mobile
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
flutter run
```

### 2. 验证命令
```bash
# 检查服务状态
docker ps

# 测试Go Gateway
curl http://localhost:8080/health

# 检查Celery
make celery-status
```

---

## ✅ 提交确认清单

在执行 `git commit` 前，请确认:

- [ ] `.env` 文件未被跟踪 (已在 `.gitignore`)
- [ ] 所有生成代码已提交 (proto, sqlc, flutter build_runner)
- [ ] 数据库迁移文件已包含
- [ ] 依赖文件完整且无绝对路径
- [ ] 文档已更新
- [ ] 测试通过 (可选但推荐)
- [ ] 提交信息清晰明确
- [ ] 没有敏感信息泄露
- [ ] 没有大文件或构建产物

---

## 🚀 提交命令

```bash
# 添加文件
git add .

# 查看将要提交的内容
git status

# 提交
git commit -m "feat: 你的描述"

# 推送
git push origin 你的分支名
```

---

## 🆘 如果组员遇到问题

### 常见问题快速解决

1. **缺少生成代码**:
   ```bash
   make proto-gen
   make sync-db
   cd mobile && flutter pub run build_runner build --delete-conflicting-outputs
   ```

2. **数据库连接失败**:
   ```bash
   make dev-up
   docker ps  # 确认容器运行
   ```

3. **Flutter依赖问题**:
   ```bash
   cd mobile
   flutter clean
   flutter pub get
   flutter pub run build_runner build --delete-conflicting-outputs
   ```

4. **Go模块问题**:
   ```bash
   cd backend/gateway
   go mod tidy
   go mod download
   ```

---

**记住**: 提交前运行此检查清单，可以避免90%的团队协作问题！
