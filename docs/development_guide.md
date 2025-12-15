# Sparkle 开发指南

## 环境准备

### 后端开发环境

**必需软件**:
- Python 3.11+ (tested with 3.14)
- PostgreSQL 14+ (或 SQLite 用于开发)
- Git

**推荐工具**:
- VSCode / PyCharm
- Postman / Insomnia (API 测试)
- DBeaver / pgAdmin (数据库管理)

### 前端开发环境

**必需软件**:
- Flutter SDK 3.0+
- Dart SDK
- Android Studio / Xcode
- Git

**推荐工具**:
- VSCode with Flutter extension
- Android Emulator / iOS Simulator

## 项目设置

### 1. 克隆项目

```bash
git clone <repository-url>
cd sparkle
```

### 2. 后端设置

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置数据库和 API 密钥
# 使用你喜欢的编辑器打开 .env

# 初始化数据库
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 3. 前端设置

```bash
cd mobile

# 获取依赖
flutter pub get

# 运行代码生成（如果需要）
flutter pub run build_runner build

# 检查设备
flutter devices

# 运行应用
flutter run

# 或指定设备
flutter run -d <device_id>
```

## 开发规范

### Git 工作流

```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 提交代码
git add .
git commit -m "feat: 添加某某功能"

# 推送到远程
git push origin feature/your-feature-name

# 创建 Pull Request
```

**提交信息规范** (Conventional Commits):
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 添加测试
- `chore`: 构建/工具配置

### 代码规范

#### Python 后端

```python
# 使用 Type Hints
def create_user(username: str, email: str) -> User:
    """
    创建新用户

    Args:
        username: 用户名
        email: 邮箱

    Returns:
        User: 创建的用户对象

    Raises:
        ValueError: 用户名已存在
    """
    pass

# 使用 async/await
async def get_user_by_id(user_id: str) -> Optional[User]:
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

**格式化工具**:
```bash
# 格式化代码
black app/

# 检查代码风格
flake8 app/

# 类型检查
mypy app/
```

#### Flutter 前端

```dart
// 使用 const 构造函数
const Text('Hello World')

// Widget 命名使用 PascalCase
class CustomButton extends StatelessWidget {
  const CustomButton({super.key});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: () {},
      child: const Text('Click Me'),
    );
  }
}

// 使用 final 声明不变变量
final String userName = 'Alice';

// 私有变量使用下划线前缀
String _privateField = 'secret';
```

**格式化工具**:
```bash
# 格式化代码
flutter format lib/

# 分析代码
flutter analyze
```

## 常见任务

### 添加新的 API 端点

1. 在 `backend/app/models/` 创建数据模型
2. 在 `backend/app/schemas/` 创建 Pydantic 模式
3. 在 `backend/app/services/` 实现业务逻辑
4. 在 `backend/app/api/v1/` 创建路由
5. 在 `backend/app/api/v1/router.py` 注册路由
6. 创建数据库迁移: `alembic revision --autogenerate -m "添加 XX 表"`
7. 应用迁移: `alembic upgrade head`

### 添加新的 Flutter 页面

1. 在 `mobile/lib/presentation/screens/` 创建页面文件
2. 在 `mobile/lib/app/routes.dart` 添加路由
3. 在 `mobile/lib/data/models/` 创建数据模型
4. 在 `mobile/lib/data/repositories/` 实现数据获取
5. 在 `mobile/lib/presentation/providers/` 创建状态管理

### 测试

#### 后端测试

```bash
cd backend

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api/test_auth.py

# 查看覆盖率
pytest --cov=app tests/
```

#### 前端测试

```bash
cd mobile

# 运行单元测试
flutter test

# 运行集成测试
flutter test integration_test/
```

## 调试技巧

### 后端调试

在代码中添加断点：
```python
import pdb; pdb.set_trace()
```

或使用 VSCode 调试配置。

### 前端调试

使用 Flutter DevTools:
```bash
flutter run --observatory-port=9200
```

在 VSCode 中使用断点调试。

## 部署

### 后端部署 (示例)

```bash
# 使用 Docker
docker build -t sparkle-backend .
docker run -p 8000:8000 sparkle-backend

# 或使用 Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 前端部署

```bash
# Android
flutter build apk --release

# iOS
flutter build ios --release
```

## 常见问题

### 1. 数据库连接失败

检查 `.env` 文件中的 `DATABASE_URL` 配置是否正确。

### 2. Flutter 依赖冲突

```bash
flutter pub cache clean
flutter pub get
```

### 3. 后端导入错误

确保虚拟环境已激活，并重新安装依赖：
```bash
pip install -r requirements.txt
```

## 资源链接

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Flutter 文档](https://flutter.dev/docs)
- [Riverpod 文档](https://riverpod.dev/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)

## 团队协作

- **代码审查**: 所有 PR 需要至少一位团队成员审查
- **每日站会**: 每天简短同步进度和问题
- **文档更新**: 添加新功能时同步更新文档
- **问题跟踪**: 使用 GitHub Issues 追踪 bug 和功能需求

---

**祝开发顺利！** 🚀
