# Sparkle 项目 Windows 用户配置指南

> **专为 Windows 用户编写的详细配置指南**
> **系统要求**: Windows 10 (版本 2004+) 或 Windows 11

---

## 📋 目录

1. [WSL2 安装与配置](#wsl2-安装与配置)
2. [Docker Desktop 配置](#docker-desktop-配置)
3. [开发环境安装](#开发环境安装)
4. [项目配置与启动](#项目配置与启动)
5. [VSCode 集成开发](#vscode-集成开发)
6. [常见问题解决](#常见问题解决)
7. [替代方案 (不使用WSL)](#替代方案-不使用wsl)

---

## 🔧 WSL2 安装与配置

### 为什么使用 WSL2？
WSL2 (Windows Subsystem for Linux 2) 让你在 Windows 上运行完整的 Linux 环境，是开发跨平台项目的最佳选择。

### 1. 启用 WSL2 功能

#### 方法 A: 一键安装 (推荐)
```powershell
# 以管理员身份打开 PowerShell 并运行:
wsl --install

# 重启电脑
```

#### 方法 B: 手动启用
```powershell
# 1. 启用 WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 2. 启用虚拟机平台
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 3. 重启电脑

# 4. 设置 WSL2 为默认版本
wsl --set-default-version 2
```

### 2. 安装 Linux 发行版

推荐使用 **Ubuntu 22.04 LTS**:

1. 打开 Microsoft Store
2. 搜索 "Ubuntu 22.04 LTS"
3. 点击安装
4. 安装完成后，从开始菜单启动 Ubuntu
5. 首次启动会要求创建用户名和密码

### 3. 配置 Ubuntu 环境

在 Ubuntu 终端中执行：

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git build-essential

# 配置 Git (使用你在 Windows 的 Git 配置)
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"

# 配置中文支持 (可选)
sudo apt install -y language-pack-zh-hans
echo 'export LANG=zh_CN.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=zh_CN.UTF-8' >> ~/.bashrc
source ~/.bashrc
```

### 4. Windows 与 WSL 文件互访

```bash
# 在 WSL 中访问 Windows C 盘
cd /mnt/c/Users/你的用户名/

# 在 Windows 中访问 WSL 文件
# 文件资源管理器地址栏输入: \\wsl$\Ubuntu-22.04\home\你的用户名\
```

---

## 🐳 Docker Desktop 配置

### 1. 安装 Docker Desktop

1. 下载地址: https://www.docker.com/products/docker-desktop/
2. 运行安装程序
3. **重要**: 勾选 "Use WSL 2 instead of Hyper-V"

### 2. 配置 Docker 使用 WSL2

1. 打开 Docker Desktop
2. 进入 Settings (设置)
3. **General**:
   - ✅ Use the WSL 2 based engine
   - ✅ Start Docker Desktop when you log in

4. **Resources → WSL Integration**:
   - ✅ Enable integration with my default WSL distro
   - ✅ Ubuntu-22.04 (启用你的发行版)

5. 点击 Apply & Restart

### 3. 验证 Docker 安装

在 **Ubuntu WSL 终端** 中运行：

```bash
# 检查 Docker 版本
docker --version
# 应该显示: Docker version 20.x.x 或更高

# 检查 Docker Compose
docker compose version
# 应该显示: Docker Compose version v2.x.x

# 测试 Docker 是否正常工作
docker run hello-world
```

---

## 💻 开发环境安装

### 1. Flutter SDK (在 WSL2 中安装)

```bash
# 1. 安装 Flutter 依赖
sudo apt install -y curl git unzip xz-utils zip libglu1-mesa

# 2. 下载 Flutter SDK
cd ~
git clone https://github.com/flutter/flutter.git -b stable

# 3. 添加到 PATH
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.bashrc
source ~/.bashrc

# 4. 验证安装
flutter --version
# 应该显示 Flutter 3.24.x 或更高

# 5. 运行 Flutter Doctor
flutter doctor

# 6. 同意 Android 许可证 (如果提示)
flutter doctor --android-licenses
```

### 2. Go 安装 (在 WSL2 中)

```bash
# 1. 下载并安装 Go
wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz

# 2. 添加到 PATH
echo 'export PATH="$PATH:/usr/local/go/bin"' >> ~/.bashrc
echo 'export GOPATH="$HOME/go"' >> ~/.bashrc
source ~/.bashrc

# 3. 配置 Go 代理 (中国用户)
go env -w GOPROXY=https://goproxy.cn,direct

# 4. 验证安装
go version
# 应该显示: go version go1.24.0 linux/amd64
```

### 3. Python 安装 (在 WSL2 中)

```bash
# 1. 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 2. 安装 pip
sudo apt install -y python3-pip

# 3. 安装 uv (快速包管理器)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 4. 验证安装
python3 --version
# 应该显示: Python 3.11.x

pip3 --version

# 5. 安装系统依赖 (用于 Python 包编译)
sudo apt install -y libpq-dev python3-dev gcc
```

### 4. 其他工具安装

```bash
# 安装 Make
sudo apt install -y make

# 安装 Buf (Protobuf 工具)
brew install bufbuild/buf/buf
# 或者使用二进制安装:
# https://github.com/bufbuild/buf/releases

# 安装 SQLC
go install github.com/sqlc-dev/sqlc/cmd/sqlc@latest
echo 'export PATH="$PATH:$HOME/go/bin"' >> ~/.bashrc
source ~/.bashrc

# 安装 Node.js (用于某些构建工具)
sudo apt install -y nodejs npm
```

---

## 🚀 项目配置与启动

### 1. 克隆项目

```bash
# 在 WSL2 的 Ubuntu 终端中
cd ~
mkdir projects
cd projects

# 克隆项目
git clone https://github.com/BRSAMAyu/sparkle-flutter.git

# 进入项目
cd sparkle-flutter
```

### 2. 配置环境变量

```bash
# 复制环境模板
cp .env.example .env

# 编辑环境文件
nano .env
```

**在 nano 编辑器中**:
- 修改密码等敏感信息
- 按 `Ctrl + X` 退出
- 按 `Y` 确认保存
- 按 `Enter` 确认文件名

### 3. 启动基础设施

```bash
# 启动数据库、Redis、MinIO 等
make dev-up

# 检查容器状态
docker ps

# 应该看到:
# - sparkle_db (PostgreSQL)
# - sparkle_redis
# - sparkle_minio
```

### 4. 配置 Python 后端

```bash
# 创建虚拟环境
cd backend
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖 (使用 uv 加速)
uv pip install -r requirements.txt
# 或者使用 pip:
# pip install -r requirements.txt

# 应用数据库迁移
alembic upgrade head

# 检查迁移状态
alembic current
```

### 5. 配置 Go Gateway

```bash
cd backend/gateway

# 安装 Go 依赖
go mod tidy

# 生成数据库代码 (如果需要)
make sync-db

# 生成 Protobuf 代码
make proto-gen
```

快速验收：
```bash
make smoke
```

迁移异常处理（安全默认）
```bash
# 发生 revision mismatch / 多 head 时，make sync-db 会输出诊断并失败
# 明确确认后可用以下方式进行保守 stamp（无 --purge）：
FORCE_STAMP=1 make sync-db
```

OpenTelemetry（可选）
```bash
# 本地建议关闭或指向本地 collector
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### 6. 配置 Flutter 移动端

```bash
cd mobile

# 安装依赖
flutter pub get

# 生成代码
flutter pub run build_runner build --delete-conflicting-outputs

# 检查设备
flutter devices
```

---

## 🖥️ VSCode 集成开发

### 1. Windows 端安装 VSCode

1. 下载: https://code.visualstudio.com/
2. 安装时勾选 "Add to PATH"
3. 安装后打开

### 2. 安装 WSL 扩展

1. 在 VSCode 中，点击左侧扩展图标 (Ctrl+Shift+X)
2. 搜索并安装: **WSL**
3. 重启 VSCode

### 3. 连接到 WSL

**方法 A: 通过命令面板**
1. 按 `Ctrl+Shift+P`
2. 输入: `WSL: Connect to WSL`
3. 选择你的 Ubuntu 发行版

**方法 B: 通过终端**
在 WSL 终端中进入项目目录，然后运行:
```bash
code .
```
这会自动在 WSL 模式下打开 VSCode

### 4. 安装推荐的扩展

在 WSL 模式的 VSCode 中安装:

- **Flutter** (Dart Code)
- **Dart**
- **Go**
- **Python** (Microsoft)
- **Pylance**
- **Docker**
- **GitLens**
- **vscode-proto3** (Proto 文件支持)

### 5. 配置 VSCode 设置

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
    }
  },
  "[go]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "[python]": {
    "editor.formatOnSave": true,
    "editor.tabSize": 4
  },
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "go.gopath": "/home/你的用户名/go",
  "flutter.hotReloadOnSave": "all",
  "docker.composeFile": "docker-compose.yml"
}
```

---

## 🏃 启动开发环境

### 方式一: 分终端启动 (推荐)

**终端 1 - 基础设施**:
```bash
cd ~/projects/sparkle-flutter
make dev-up
```

**终端 2 - Python gRPC 服务**:
```bash
cd ~/projects/sparkle-flutter
source backend/venv/bin/activate
make grpc-server
```

**终端 3 - Go Gateway**:
```bash
cd ~/projects/sparkle-flutter
make gateway-dev
```

**终端 4 - Celery (可选)**:
```bash
cd ~/projects/sparkle-flutter
make celery-up
```

**终端 5 - Flutter 应用**:
```bash
cd ~/projects/sparkle-flutter/mobile
flutter run
```

### 方式二: 一键启动 (简化版)

```bash
# 在项目根目录
make dev-all
```

---

## 🔍 验证安装

### 1. 检查所有服务

```bash
# 检查 Docker 容器
docker ps

# 应该看到:
# - sparkle_db
# - sparkle_redis
# - sparkle_minio
# - sparkle_backend (如果启动了)
# - sparkle_gateway (如果启动了)
```

### 2. 测试 API

```bash
# 测试 Go Gateway 健康检查
curl http://localhost:8080/health

# 应该返回: {"status":"healthy"}
```

### 3. 测试 Flutter

```bash
cd mobile
flutter analyze

# 如果没有错误，说明配置正确
```

---

## 🐛 常见问题解决

### 问题 1: WSL2 网络连接问题

**症状**: 无法访问互联网或下载慢

**解决**:
```bash
# 检查 DNS
cat /etc/resolv.conf

# 如果 DNS 不正确，手动设置
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf
```

### 问题 2: Docker Desktop 无法启动

**症状**: Docker Desktop 卡在启动画面

**解决**:
1. 以管理员身份打开 PowerShell
2. 运行: `wsl --shutdown`
3. 等待 10 秒
4. 重新启动 Docker Desktop

### 问题 3: Flutter 无法检测到设备

**症状**: `flutter devices` 显示无设备

**解决**:
```bash
# 检查 ADB (Android Debug Bridge)
# 需要在 Windows 中安装 Android Studio 并配置 ADB

# 在 Windows PowerShell 中:
adb devices

# 在 WSL 中配置 ADB 路径
echo 'export PATH="$PATH:/mnt/c/Users/你的用户名/AppData/Local/Android/Sdk/platform-tools"' >> ~/.bashrc
source ~/.bashrc
```

### 问题 4: Python 包编译失败

**症状**: 安装依赖时出现 gcc 错误

**解决**:
```bash
# 安装完整的构建工具
sudo apt install -y build-essential libpq-dev python3-dev

# 如果使用 pip，尝试:
pip install --upgrade pip setuptools wheel
```

### 问题 5: 端口冲突

**症状**: 服务启动失败，端口已被占用

**解决**:
```bash
# 检查端口占用
sudo netstat -tulpn | grep :8080
sudo netstat -tulpn | grep :8000

# 杀掉占用进程
sudo kill -9 <PID>

# 或者修改端口映射
# 在 docker-compose.yml 中修改端口
```

### 问题 6: WSL2 磁盘空间不足

**症状**: Docker 容器无法启动

**解决**:
```bash
# 在 Windows PowerShell 中清理 WSL
wsl --shutdown
wsl --unregister Ubuntu-22.04

# 重新安装并设置更大的磁盘限制
# 编辑 C:\Users\你的用户名\.wslconfig
# 添加:
# [wsl2]
# diskSize=100GB
```

### 问题 7: 文件权限问题

**症状**: 在 WSL 中无法修改 Windows 文件

**解决**:
```bash
# 将项目克隆到 WSL 文件系统中，而不是 /mnt/c
cd ~
mkdir projects
cd projects
git clone ...
```

### 问题 8: Flutter Doctor 显示问题

**症状**: `flutter doctor` 显示各种警告

**常见警告及解决**:

```bash
# Android Toolchain 问题
# 需要在 Windows 中安装 Android Studio
# 然后在 WSL 中配置:
echo 'export ANDROID_HOME="/mnt/c/Users/你的用户名/AppData/Local/Android/Sdk"' >> ~/.bashrc
echo 'export PATH="$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools"' >> ~/.bashrc
source ~/.bashrc

# Chrome 问题 (Web 开发)
sudo apt install -y chromium-browser
```

---

## 🔄 替代方案 (不使用 WSL)

如果你不想使用 WSL，也可以在 Windows 原生环境中配置，但会遇到更多兼容性问题。

### 1. 安装工具 (Windows 原生)

#### Git
- 下载: https://git-scm.com/
- 安装时选择: "Use Git from the Windows Command Prompt"

#### Docker Desktop
- 同上，但不需要 WSL2 集成

#### Flutter
- 下载: https://flutter.dev/docs/get-started/install/windows
- 解压到 `C:\src\flutter`
- 添加到 PATH: `C:\src\flutter\bin`

#### Go
- 下载: https://go.dev/dl/
- 安装到 `C:\Go`
- 配置环境变量:
  - `GOROOT`: `C:\Go`
  - `GOPATH`: `C:\Users\你的用户名\go`
  - 添加到 PATH: `%GOROOT%\bin;%GOPATH%\bin`

#### Python
- 下载: https://www.python.org/downloads/
- 安装时勾选: "Add Python to PATH"
- 重启终端

### 2. Windows 终端配置

使用 **PowerShell** 或 **Windows Terminal**:

```powershell
# 配置 Go 代理
go env -w GOPROXY=https://goproxy.cn,direct

# 安装项目依赖
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 启动服务 (注意路径分隔符)
cd backend
python grpc_server.py

# 另一个终端
cd backend/gateway
go run cmd/server/main.go
```

### 3. Windows 原生的问题

⚠️ **警告**: 原生 Windows 配置可能遇到以下问题:

1. **路径分隔符**: Windows 使用 `\`，Linux 使用 `/`
2. **Shell 差异**: PowerShell vs Bash
3. **Docker 性能**: Windows 上 Docker 文件系统性能较差
4. **某些包不支持**: 某些 Python 包在 Windows 上编译困难
5. **Flutter 构建**: Android 构建在 Windows 上可能更慢

**建议**: 除非必须，否则推荐使用 WSL2

---

## 📝 Windows 专属提示

### 1. 快速访问 WSL 文件

在 Windows 文件资源管理器中:
```
\\wsl$\Ubuntu-22.04\home\你的用户名\projects\sparkle-flutter
```

### 2. Windows Terminal 配置

安装 **Windows Terminal** (Microsoft Store):
- 打开设置 (Ctrl+,)
- 添加 Ubuntu 配置文件
- 设置默认终端为 Ubuntu

### 3. 环境变量持久化

在 WSL 中，环境变量添加到 `~/.bashrc`:
```bash
echo 'export PATH="$PATH:$HOME/flutter/bin"' >> ~/.bashrc
source ~/.bashrc
```

在 Windows 中，环境变量添加到:
- 控制面板 → 系统 → 高级系统设置 → 环境变量

### 4. 端口转发 (如果需要外部访问)

在 Windows PowerShell 中:
```powershell
# 将 WSL 端口转发到 Windows
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=127.0.0.1
```

---

## 🎯 Windows 配置总结

### 推荐配置流程

1. **安装 WSL2 + Ubuntu** (必须)
2. **安装 Docker Desktop** (配置 WSL2 集成)
3. **在 WSL 中安装开发工具** (Flutter/Go/Python)
4. **克隆项目到 WSL 文件系统**
5. **使用 VSCode + WSL 扩展开发**
6. **在 WSL 终端中运行所有命令**

### 优势
- ✅ 完整的 Linux 环境
- ✅ 与生产环境一致
- ✅ 更好的性能
- ✅ 避免路径和兼容性问题

### 需要避免
- ❌ 在 `/mnt/c` 中开发 (性能差)
- ❌ 混合使用 Windows 和 WSL 命令
- ❌ 在 Windows 和 WSL 之间频繁切换文件

---

## 🆘 Windows 专属支持

如果遇到 Windows 特定问题:

1. **检查 WSL 状态**: `wsl -l -v`
2. **重启 WSL**: `wsl --shutdown`
3. **查看 Docker 日志**: Docker Desktop → Troubleshoot → Get support
4. **Windows 事件查看器**: 搜索 Docker 或 WSL 相关错误

**祝你的 Windows 开发环境配置顺利！** 🚀
