# Sparkle 项目配置指南索引

> 根据你的操作系统选择合适的配置指南

---

## 📚 选择你的操作系统

### 🍎 macOS 用户
**推荐**: 完整的 Unix 环境，开发体验最佳

📖 **阅读**: [SETUP_GUIDE.md](SETUP_GUIDE.md)

**特点**:
- ✅ 原生 Unix 环境
- ✅ Homebrew 包管理器
- ✅ 无需虚拟化层
- ✅ 最佳性能

**快速开始**:
```bash
# 1. 安装 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装 Docker
brew install --cask docker

# 3. 安装 Flutter
brew install flutter

# 4. 安装 Go
brew install go

# 5. 安装 Python
brew install python@3.11

# 6. 克隆项目并启动
git clone https://github.com/BRSAMAyu/sparkle-flutter.git
cd sparkle-flutter
make dev-all
```

---

### 🐧 Linux 用户 (Ubuntu/Debian)
**推荐**: 原生 Linux 环境，与生产环境一致

📖 **阅读**: [SETUP_GUIDE.md](SETUP_GUIDE.md) (大部分适用)

**特点**:
- ✅ 原生 Linux 环境
- ✅ 包管理器 (apt)
- ✅ 与服务器环境一致
- ✅ 完全兼容

**快速开始**:
```bash
# 1. 安装 Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 2. 安装 Flutter
sudo apt install -y curl git unzip xz-utils zip
git clone https://github.com/flutter/flutter.git -b stable ~/flutter
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.bashrc
source ~/.bashrc

# 3. 安装 Go
wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz
echo 'export PATH="$PATH:/usr/local/go/bin"' >> ~/.bashrc
source ~/.bashrc

# 4. 安装 Python
sudo apt install -y python3.11 python3-pip python3-venv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 5. 克隆项目
git clone https://github.com/BRSAMAyu/sparkle-flutter.git
cd sparkle-flutter
make dev-all
```

---

### 🪟 Windows 用户
**推荐**: 使用 WSL2 获得完整的 Linux 开发环境

📖 **阅读**: [SETUP_GUIDE_WINDOWS.md](SETUP_GUIDE_WINDOWS.md)

**特点**:
- ⚠️ 需要 WSL2 虚拟化层
- ⚠️ 需要配置 Docker Desktop
- ✅ 良好的开发体验
- ✅ 与 macOS/Linux 一致

**快速开始**:
```powershell
# 1. 启用 WSL2 (管理员 PowerShell)
wsl --install
# 重启电脑

# 2. 安装 Ubuntu 22.04 (Microsoft Store)

# 3. 在 Ubuntu 终端中安装 Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# 4. 安装开发工具 (Ubuntu 终端)
sudo apt install -y curl git unzip xz-utils zip
git clone https://github.com/flutter/flutter.git -b stable ~/flutter
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.bashrc
source ~/.bashrc

# 5. 下载并安装 Docker Desktop (Windows)
# 配置 WSL2 集成

# 6. 克隆项目
cd ~
mkdir projects
cd projects
git clone https://github.com/BRSAMAyu/sparkle-flutter.git
cd sparkle-flutter
make dev-all
```

---

## 🎯 操作系统对比表

| 特性 | macOS | Linux | Windows (WSL2) |
|------|-------|-------|----------------|
| **安装复杂度** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **开发体验** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **性能** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **兼容性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **维护成本** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 📋 通用配置步骤 (所有系统)

无论使用哪个系统，都需要完成以下步骤：

### 1. 安装核心工具
- ✅ Docker + Docker Compose
- ✅ Flutter SDK (v3.24.0+)
- ✅ Go (v1.24.0+)
- ✅ Python (v3.11+)

### 2. 克隆项目
```bash
git clone https://github.com/BRSAMAyu/sparkle-flutter.git
cd sparkle-flutter
```

### 3. 配置环境
```bash
cp .env.example .env.local
# 编辑 .env.local
```

### 4. 启动基础设施
```bash
make dev-up
```

### 5. 配置后端
```bash
# Python
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

# Go
cd backend/gateway
go mod tidy
make proto-gen
```

### 6. 配置移动端
```bash
cd mobile
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
```

### 7. 启动服务
```bash
# 终端1: Python gRPC
make grpc-server

# 终端2: Go Gateway
make gateway-dev

# 终端3: Flutter
cd mobile
flutter run
```

---

## 🔍 环境验证命令

### 跨平台验证脚本

创建 `check_setup.sh` (Linux/macOS) 或 `check_setup.ps1` (Windows):

```bash
#!/bin/bash
echo "=== Sparkle 环境检查 ==="

check_command() {
    if command -v $1 &> /dev/null; then
        echo "✅ $1: $($1 --version 2>/dev/null | head -1)"
        return 0
    else
        echo "❌ $1: 未安装"
        return 1
    fi
}

check_command docker
check_command docker-compose
check_command flutter
check_command go
check_command python3
check_command make

echo ""
echo "=== 项目文件检查 ==="
if [ -f "docker-compose.yml" ]; then
    echo "✅ docker-compose.yml"
else
    echo "❌ docker-compose.yml"
fi

if [ -f "Makefile" ]; then
    echo "✅ Makefile"
else
    echo "❌ Makefile"
fi

if [ -f ".env.example" ]; then
    echo "✅ .env.example"
else
    echo "❌ .env.example"
fi

echo ""
echo "=== 下一步 ==="
echo "1. 复制 .env.example 到 .env.local"
echo "2. 编辑 .env.local 配置你的环境"
echo "3. 运行: make dev-all"
```

---

## 🆘 寻求帮助

### 按操作系统分类

#### macOS 问题
- 搜索: "macOS Docker Desktop 问题"
- 搜索: "macOS Flutter 构建错误"
- 搜索: "macOS CC/CXX 环境变量"

#### Linux 问题
- 搜索: "Ubuntu Docker 权限问题"
- 搜索: "Linux Flutter 依赖缺失"
- 搜索: "Linux Python 包编译错误"

#### Windows 问题
- 搜索: "WSL2 Docker 集成失败"
- 搜索: "Windows Flutter Android SDK"
- 搜索: "WSL2 端口转发"

### 通用问题
- 查看 [SETUP_GUIDE.md](SETUP_GUIDE.md) 的问题解决部分
- 查看 [SETUP_GUIDE_WINDOWS.md](SETUP_GUIDE_WINDOWS.md) 的问题解决部分
- 在团队群组中提问

---

## 📖 相关文档

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - macOS/Linux 详细指南
- [SETUP_GUIDE_WINDOWS.md](SETUP_GUIDE_WINDOWS.md) - Windows 详细指南
- [PRE_COMMIT_CHECKLIST.md](PRE_COMMIT_CHECKLIST.md) - 提交前检查
- [GIT_STATUS_SUMMARY.md](GIT_STATUS_SUMMARY.md) - Git 状态总结
- [README.md](README.md) - 项目介绍

---

**选择你的操作系统，开始配置吧！** 🚀
