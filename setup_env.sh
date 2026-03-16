#!/usr/bin/env bash
#
# Sparkle 项目环境配置脚本
#
# 用法:
#   bash setup_env.sh [--skip-flutter] [--skip-docker]
#
# 选项:
#   --skip-flutter    跳过 Flutter 安装（较大，可选）
#   --skip-docker     跳过 Docker/colima 启动
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_ROOT/backend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 解析参数
SKIP_FLUTTER=false
SKIP_DOCKER=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-flutter) SKIP_FLUTTER=true; shift ;;
        --skip-docker) SKIP_DOCKER=true; shift ;;
        *) log_error "未知参数: $1"; exit 1 ;;
    esac
done

log_info "🚀 开始配置 Sparkle 项目环境..."
log_info "项目根目录: $PROJECT_ROOT"
echo ""

# ========================================
# 1. 检查系统环境
# ========================================
log_info "=== 检查系统环境 ==="

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_success "Python: $PYTHON_VERSION"
else
    log_error "Python3 未安装"
    exit 1
fi

# uv
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version)
    log_success "uv: $UV_VERSION"
else
    log_warn "uv 未安装，使用 pip 替代"
fi

# Go
if command -v go &> /dev/null; then
    GO_VERSION=$(go version | awk '{print $3}')
    log_success "Go: $GO_VERSION"
else
    log_error "Go 未安装"
    exit 1
fi

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    log_success "Docker: $DOCKER_VERSION"
else
    if [ "$SKIP_DOCKER" = false ]; then
        log_warn "Docker 未运行，尝试启动 colima..."
    fi
fi

echo ""

# ========================================
# 2. 启动 Docker/colima
# ========================================
if [ "$SKIP_DOCKER" = false ]; then
    log_info "=== 启动 Docker 环境 ==="

    if ! docker ps &> /dev/null; then
        if command -v colima &> /dev/null; then
            log_info "启动 colima..."
            colima start --cpu 2 --memory 4 --vm-type qemu --mount-type virtiofs 2>&1 || {
                log_error "colima 启动失败"
                exit 1
            }
            log_success "colima 已启动"
        else
            log_error "Docker 不可用且未安装 colima"
            exit 1
        fi
    else
        log_success "Docker 已运行"
    fi
else
    log_warn "跳过 Docker 启动 (--skip-docker)"
fi

echo ""

# ========================================
# 3. 配置后端环境
# ========================================
log_info "=== 配置 Python 后端环境 ==="

# 创建虚拟环境
VENV_DIR="$PROJECT_ROOT/venvs/sparkle"
if [ ! -d "$VENV_DIR" ]; then
    log_info "创建虚拟环境: $VENV_DIR"
    if command -v uv &> /dev/null; then
        uv venv "$VENV_DIR" --python 3.11
    else
        python3 -m venv "$VENV_DIR"
    fi
    log_success "虚拟环境创建成功"
else
    log_success "虚拟环境已存在: $VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 升级 pip
log_info "升级 pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1

# 安装依赖
log_info "安装 Python 依赖..."
if command -v uv &> /dev/null; then
    uv pip install -r "$BACKEND_DIR/requirements.txt"
else
    pip install -r "$BACKEND_DIR/requirements.txt"
fi

log_success "Python 依赖安装完成"
echo ""

# ========================================
# 4. 配置 .env 文件
# ========================================
log_info "=== 配置环境变量 ==="

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_info "创建 .env 文件（从 .env.example 复制）"
    cp "$BACKEND_DIR/.env.example" "$PROJECT_ROOT/.env"
    log_success ".env 文件已创建"
    log_warn "⚠️  请编辑 .env 文件，配置以下 API Keys："
    log_warn "   - DASHSCOPE_API_KEY (通义千问)"
    log_warn "   - DEEPSEEK_API_KEY (DeepSeek)"
    log_warn "   - XUNFEI_API_KEY, XUNFEI_API_SECRET (讯飞 STT)"
    log_warn "   - SILICONFLOW_API_KEY (SiliconFlow)"
else
    log_success ".env 文件已存在"
fi

echo ""

# ========================================
# 5. 启动基础设施
# ========================================
if [ "$SKIP_DOCKER" = false ]; then
    log_info "=== 启动基础设施 ==="

    cd "$PROJECT_ROOT"

    log_info "启动数据库和 Redis..."
    docker compose up -d sparkle_db redis minio

    log_info "等待数据库启动..."
    sleep 5

    log_info "运行数据库迁移..."
    cd "$BACKEND_DIR" && alembic upgrade head

    log_success "基础设施启动完成"
else
    log_warn "跳过基础设施启动 (--skip-docker)"
fi

echo ""

# ========================================
# 6. Go Gateway 配置
# ========================================
log_info "=== 配置 Go Gateway ==="

cd "$BACKEND_DIR/gateway"

log_info "下载 Go 依赖..."
go mod download > /dev/null 2>&1

log_success "Go Gateway 配置完成"
echo ""

# ========================================
# 7. Flutter 配置（可选）
# ========================================
if [ "$SKIP_FLUTTER" = false ]; then
    log_info "=== 配置 Flutter ==="

    if ! command -v flutter &> /dev/null; then
        log_warn "Flutter 未安装"
        log_warn "请访问 https://docs.flutter.dev/get-started/install 安装"
        log_warn "安装后运行: cd mobile && flutter pub get"
    else
        FLUTTER_VERSION=$(flutter --version | head -1)
        log_success "Flutter: $FLUTTER_VERSION"

        cd "$PROJECT_ROOT/mobile"
        log_info "下载 Flutter 依赖..."
        flutter pub get > /dev/null 2>&1
        log_success "Flutter 依赖安装完成"
    fi
else
    log_warn "跳过 Flutter 配置 (--skip-flutter)"
fi

echo ""

# ========================================
# 8. 生成 Protobuf 代码
# ========================================
log_info "=== 生成 Protobuf 代码 ==="

cd "$PROJECT_ROOT"

if command -v buf &> /dev/null; then
    log_info "使用 buf 生成..."
    buf generate > /dev/null 2>&1
    log_success "Protobuf 代码生成成功 (buf)"
else
    log_warn "buf 未安装，跳过 Protobuf 生成"
    log_info "安装 buf: brew install bufbuild/buf/buf"
fi

echo ""

# ========================================
# 9. 验证配置
# ========================================
log_info "=== 验证配置 ==="

cd "$PROJECT_ROOT"

if [ "$SKIP_DOCKER" = false ]; then
    log_info "检查数据库连接..."
    if docker ps | grep -q sparkle_db; then
        log_success "数据库容器运行中"
    else
        log_error "数据库容器未运行"
    fi
fi

log_info "检查 Python 环境..."
source "$VENV_DIR/bin/activate" && python -c "import fastapi, langgraph, grpcio" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log_success "Python 依赖验证通过"
else
    log_error "Python 依赖验证失败"
fi

echo ""

# ========================================
# 完成提示
# ========================================
log_success "🎉 环境配置完成！"
echo ""
log_info "📋 后续步骤："
echo ""
echo "1. 配置 API Keys:"
echo "   nano $PROJECT_ROOT/.env"
echo ""
echo "2. 启动服务（分终端运行）："
echo "   终端1 - Python gRPC 服务:"
echo "     cd $PROJECT_ROOT && source venvs/sparkle/bin/activate"
echo "     cd backend && python grpc_server.py"
echo ""
echo "   终端2 - Go Gateway:"
echo "     cd $PROJECT_ROOT/backend/gateway && go run cmd/server/main.go"
echo ""
echo "   终端3 - Flutter 应用（如已安装）:"
echo "     cd $PROJECT_ROOT/mobile && flutter run"
echo ""
echo "3. 健康检查:"
echo "   cd $PROJECT_ROOT && make smoke"
echo ""
echo "4. 停止基础设施:"
echo "   cd $PROJECT_ROOT && docker compose down"
echo ""
