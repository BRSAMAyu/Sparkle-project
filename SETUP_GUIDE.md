# Sparkle (星火) 开发者环境配置指南

> **版本**: 1.0.0
> **架构**: 混合微服务 (Flutter + Go Gateway + Python Engine)
> **更新日期**: 2026-01-10

本文档旨在帮助开发者快速搭建 Sparkle 项目的开发环境。项目采用三层混合架构，需要分别配置基础设施、后端服务和移动端环境。

---

## 📚 目录

1. [架构与技术栈](#1-架构与技术栈)
2. [环境准备](#2-环境准备)
3. [快速启动 (Quick Start)](#3-快速启动-quick-start)
4. [详细配置指南](#4-详细配置指南)
    - [基础设施 (Infrastructure)](#41-基础设施-infrastructure)
    - [后端: Python AI Engine](#42-后端-python-ai-engine)
    - [后端: Go Gateway](#43-后端-go-gateway)
    - [移动端: Flutter](#44-移动端-flutter)
5. [验证与测试](#5-验证与测试)
6. [常见问题 (Troubleshooting)](#6-常见问题-troubleshooting)

---

## 1. 架构与技术栈

| 层级 | 语言/框架 | 关键组件 |
| :--- | :--- | :--- |
| **移动端 (Mobile)** | Dart / Flutter 3.24+ | Riverpod, Hive, WebSocket Client |
| **网关层 (Gateway)** | Go 1.24+ / Gin | Gorilla WebSocket, JWT, SQLC |
| **智能层 (AI Engine)** | Python 3.11+ / FastAPI | gRPC, LangChain, Celery |
| **基础设施 (Infra)** | Docker | PostgreSQL (pgvector), Redis, MinIO |

---

## 2. 环境准备

### 2.1 必需工具
请确保安装以下工具：

- **Git**: 版本控制
- **Docker & Docker Compose**: 运行数据库和中间件
- **Make**: 自动化脚本执行

### 2.2 语言环境

#### 🐍 Python (AI Engine)
- **版本**: 3.11+
- **包管理**: `pip` 或 `uv` (推荐)
- **安装**:
  ```bash
  brew install python@3.11
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

#### 🐹 Go (Gateway)
- **版本**: 1.24+
- **安装**:
  ```bash
  brew install go
  go env -w GOPROXY=https://goproxy.cn,direct
  ```
- **工具**: 安装 `buf` 用于 Protobuf 生成
  ```bash
  brew install bufbuild/buf/buf
  ```

#### 📱 Flutter (Mobile)
- **版本**: 3.24.0+
- **安装**: [Flutter 官网指南](https://flutter.dev/docs/get-started/install)
- **检查**: `flutter doctor`

---

## 3. 快速启动 (Quick Start)

我们使用 `Makefile` 来简化日常开发操作。

### 第一步：启动基础设施
启动 PostgreSQL, Redis, MinIO 等容器服务。
```bash
make dev-up
```

### 第二步：配置环境变量
复制示例配置文件并根据需要修改。
```bash
cp .env.example .env.local
```

### 第三步：启动所有服务 (三终端模式)

**终端 1 (AI Engine)**:
```bash
make grpc-server
```

**终端 2 (Gateway)**:
```bash
make gateway-dev
```

**终端 3 (Mobile)**:
```bash
cd mobile
flutter run
```

---

## 4. 详细配置指南

### 4.1 基础设施 (Infrastructure)

核心数据存储和中间件通过 Docker Compose 运行。

- **PostgreSQL**: 端口 `5432`，数据库 `sparkle`，用户 `postgres`。
- **Redis**: 端口 `6379`。
- **MinIO**: 控制台端口 `9001`，API 端口 `9000`。
- **Observability**: Prometheus, Grafana, Tempo (详见 `monitoring/` 目录)。

### 4.2 后端: Python AI Engine

位于 `backend/` 目录。

1.  **创建虚拟环境**:
    ```bash
    cd backend
    python3.11 -m venv .venv
    source .venv/bin/activate
    ```
2.  **安装依赖**:
    ```bash
    uv pip install -r requirements.txt
    ```
3.  **数据库迁移**:
    ```bash
    alembic upgrade head
    ```

### 4.3 后端: Go Gateway

位于 `backend/gateway/` 目录。

1.  **同步数据库 Schema**:
    如果 Python 层修改了模型，需要同步到 Go 层。
    ```bash
    # 在项目根目录
    make sync-db
    ```
2.  **生成 gRPC 代码**:
    如果修改了 `.proto` 文件：
    ```bash
    make proto-gen
    ```
3.  **运行**:
    ```bash
    make gateway-dev
    ```

### 4.4 移动端: Flutter

位于 `mobile/` 目录。

1.  **安装依赖**:
    ```bash
    cd mobile
    flutter pub get
    ```
2.  **代码生成**:
    使用了 `freezed` 和 `riverpod`，修改模型后需运行：
    ```bash
    flutter pub run build_runner build --delete-conflicting-outputs
    ```
3.  **运行**:
    连接真机或模拟器。
    ```bash
    flutter run
    ```

---

## 5. 验证与测试

### 验证各层连通性

1.  **Gateway 健康检查**:
    访问 `http://localhost:8080/health`，应返回 `{"status":"healthy"}`。

2.  **gRPC 服务测试**:
    ```bash
    make grpc-test
    ```

3.  **集成测试 (WebSocket)**:
    ```bash
    make integration-test
    ```

---

## 6. 常见问题 (Troubleshooting)

### macOS 编译 Flutter 失败
**现象**: 报错 `ld: symbol(s) not found for architecture arm64` 或与 GCC 相关错误。
**原因**: 环境变量 `CC` 或 `CXX` 指向了 Homebrew 的 GCC，与 Xcode Clang 冲突。
**解决**:
```bash
unset CC CXX
flutter run
```

### 数据库连接失败
**检查**:
1. `docker ps` 确认 `sparkle_db` 正在运行。
2. 检查 `.env.local` 中的密码是否与 `docker-compose.yml` 一致。

### gRPC 代码不一致
**现象**: Go 或 Python 报错找不到方法。
**解决**: 重新生成代码。
```bash
make proto-gen
```

### 端口被占用
- **8080**: Go Gateway
- **8000**: Python Service
- **50051**: Python gRPC
- **5432**: PostgreSQL
- **6379**: Redis

使用 `lsof -i :<port>` 查找占用进程并 `kill`。