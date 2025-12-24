# Sparkle 开发指南

## 概述

本文档为 Sparkle 项目的开发者提供完整的开发环境搭建、代码规范、开发流程和部署指南。

## 环境要求

### 系统要求
- **操作系统**: macOS 10.15+, Ubuntu 20.04+, Windows 10+ (WSL2)
- **内存**: 8GB+ (推荐16GB+)
- **存储**: 10GB+ 可用空间

### 软件依赖
- **Python**: 3.11+ (推荐3.11.4)
- **Flutter**: 3.16+ (推荐最新稳定版)
- **Docker**: 20.10+ (用于数据库和缓存)
- **Node.js**: 18+ (用于开发工具)
- **Git**: 2.30+

## 开发环境搭建

### 后端环境搭建

1. **克隆项目**
```bash
git clone https://github.com/your-username/sparkle-flutter.git
cd sparkle-flutter/backend
```

2. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接、API密钥等
```

5. **数据库设置**
```bash
# 启动PostgreSQL (推荐使用Docker)
docker run --name sparkle-db -e POSTGRES_DB=sparkle -e POSTGRES_USER=sparkle -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15

# 或使用SQLite (开发模式)
# 在 .env 中设置 DATABASE_URL=sqlite:///./sparkle.db
```

6. **运行数据库迁移**
```bash
alembic upgrade head
```

7. **启动后端服务**
```bash
uvicorn app.main:app --reload
```

### 移动端环境搭建

1. **安装Flutter**
```bash
# 根据官方指南安装Flutter SDK
# https://docs.flutter.dev/get-started/install
```

2. **检查环境**
```bash
flutter doctor
```

3. **获取依赖**
```bash
cd mobile
flutter pub get
```

4. **运行应用**
```bash
flutter run
```

## 项目结构

### 后端结构
```
backend/
├── app/                    # 应用主目录
│   ├── main.py            # 应用入口
│   ├── config.py          # 配置管理
│   ├── api/               # API路由
│   │   └── v1/            # API版本
│   ├── services/          # 业务逻辑服务
│   ├── models/            # 数据模型
│   ├── schemas/           # Pydantic模型
│   ├── workers/           # 后台任务
│   └── core/              # 核心功能
├── alembic/               # 数据库迁移
├── seed_data/             # 种子数据
├── tests/                 # 测试文件
├── requirements.txt       # Python依赖
└── .env.example          # 环境变量示例
```

### 移动端结构
```
mobile/
├── lib/                   # Dart源代码
│   ├── main.dart          # 应用入口
│   ├── app/               # 应用配置
│   ├── presentation/      # UI层
│   │   ├── screens/       # 页面
│   │   ├── widgets/       # 组件
│   │   └── providers/     # 状态管理
│   ├── data/              # 数据层
│   │   ├── models/        # 数据模型
│   │   ├── repositories/  # 数据仓库
│   │   └── datasources/   # 数据源
│   └── core/              # 核心功能
├── pubspec.yaml           # 项目配置
└── android/ios/macos/     # 平台特定代码
```

## 开发规范

### Python代码规范
- **代码风格**: 遵循 PEP 8 标准
- **类型提示**: 所有函数和方法必须包含类型提示
- **文档字符串**: 使用 Google 风格的文档字符串
- **命名规范**: 使用 snake_case 命名变量和函数

### Dart代码规范
- **代码风格**: 遵循 Effective Dart 指南
- **命名规范**: 使用 camelCase 命名变量和函数
- **注释**: 使用 Dartdoc 风格的文档注释
- **组件设计**: 遵循 Flutter 最佳实践

### Git工作流
- **分支策略**: Git Flow 或 GitHub Flow
- **提交规范**: 遵循 conventional commits 规范
- **代码审查**: 所有代码必须经过PR审查

## 数据库设计

### 核心表结构

#### 用户表 (users)
- 存储用户基本信息和个性化设置
- 包含火焰等级、偏好设置等学习相关字段

#### 任务表 (tasks)
- 存储用户的学习任务
- 支持多种任务类型和状态管理

#### 知识节点表 (knowledge_nodes)
- 存储知识点信息
- 支持向量嵌入用于语义搜索

#### 用户节点状态表 (user_node_status)
- 存储用户对知识点的掌握情况
- 包含遗忘曲线相关字段

### 数据库迁移
```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## API设计

### RESTful设计原则
- 使用标准HTTP方法
- 使用嵌套路径表示资源关系
- 统一错误响应格式
- 版本控制

### 认证机制
- 使用JWT进行身份验证
- 支持令牌自动刷新
- 实现权限控制中间件

## 测试策略

### 后端测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api/

# 生成覆盖率报告
pytest --cov=app
```

### 移动端测试
```bash
# 运行单元测试
flutter test

# 运行集成测试
flutter test integration_test/
```

## 部署指南

### 后端部署

#### Docker部署
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 环境变量配置
```bash
# 生产环境推荐配置
APP_NAME=sparkle
APP_VERSION=1.0.0
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:password@host:port/dbname
LLM_API_KEY=your-llm-api-key
LLM_MODEL_NAME=qwen-max
```

### 移动端部署

#### Android
```bash
flutter build apk --release
# 或构建分发版
flutter build appbundle --release
```

#### iOS
```bash
flutter build ios --release
```

## 性能优化

### 后端优化
- 使用异步数据库操作
- 实现API响应缓存
- 优化数据库查询
- 使用连接池

### 前端优化
- 实现组件懒加载
- 优化图片和资源加载
- 使用Riverpod进行状态管理
- 实现分页加载

## 监控与日志

### 日志配置
- 使用 loguru 进行日志记录
- 实现结构化日志输出
- 配置日志级别和格式

### 监控指标
- API响应时间
- 数据库查询性能
- 内存使用情况
- 错误率统计

## 社群功能开发

### 数据模型
- 好友关系表 (friendships)
- 群组表 (groups)
- 群成员表 (group_members)
- 群消息表 (group_messages)

### 实时通信
- 使用WebSocket或SSE实现消息推送
- 实现群组消息的实时同步
- 支持消息历史记录

### 火堆系统
- 实现火苗贡献值计算
- 设计火堆动画效果
- 支持群组排名和成就系统

## 扩展开发

### 新功能开发流程
1. 需求分析和设计
2. 数据库模型设计
3. API接口设计
4. 后端开发
5. 前端开发
6. 测试和部署

### 模块化设计
- 保持模块间的低耦合
- 使用接口抽象依赖关系
- 实现插件化功能扩展

## 故障排除

### 常见问题
- 数据库连接问题
- API认证失败
- 前端构建错误
- 性能问题

### 调试技巧
- 使用日志进行问题定位
- 使用Postman测试API
- 使用Flutter DevTools
- 数据库查询优化

## 最佳实践

### 代码质量
- 编写单元测试
- 进行代码审查
- 使用静态分析工具
- 保持代码简洁

### 安全考虑
- 输入验证和清理
- SQL注入防护
- XSS防护
- 数据加密

### 用户体验
- 响应式设计
- 加载状态处理
- 错误处理和提示
- 离线功能支持
