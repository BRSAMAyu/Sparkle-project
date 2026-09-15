# Enum 序列化规范

> **重要**: 本项目所有跨语言通信的 Enum 必须遵循本规范，避免序列化错误。

---

## 📋 核心原则

### 1. **统一使用 UPPERCASE 值**
所有跨平台传输的 Enum 值必须使用**大写字母** + **下划线**格式。

**正确示例**:
```python
# Python Backend
class TaskType(str, enum.Enum):
    LEARNING = "LEARNING"
    TRAINING = "TRAINING"
    ERROR_FIX = "ERROR_FIX"
```

```dart
// Flutter Frontend
enum TaskType {
  @JsonValue('LEARNING')  // ✅ 大写 + 下划线
  learning,
  @JsonValue('TRAINING')
  training,
  @JsonValue('ERROR_FIX')
  errorFix,
}
```

**错误示例**:
```dart
// ❌ 小写 - 会导致后端验证失败
enum TaskType {
  @JsonValue('learning')  // 错误！
  learning,
}
```

---

## 🔧 实现规范

### Python Backend (SQLAlchemy + Pydantic)

```python
# 1. 模型定义 - app/models/task.py
class TaskType(str, enum.Enum):
    """Enum 值必须与 JsonValue 完全一致 (UPPERCASE)"""
    LEARNING = "LEARNING"
    TRAINING = "TRAINING"
    ERROR_FIX = "ERROR_FIX"
    REFLECTION = "REFLECTION"
    SOCIAL = "SOCIAL"
    PLANNING = "PLANNING"
    OCR = "OCR"

# 2. Schema 验证 - app/schemas/task.py
class TaskCreate(BaseModel):
    type: TaskType = Field(validation_alias=AliasChoices("type", "task_type"))

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_task_type(cls, value):
        """标准化输入：支持小写别名，但内部统一为大写"""
        if isinstance(value, TaskType):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            alias_map = {
                "learning": "LEARNING",
                "training": "TRAINING",
                "errorfix": "ERROR_FIX",
                "error_fix": "ERROR_FIX",
                "reflection": "REFLECTION",
                "social": "SOCIAL",
                "planning": "PLANNING",
                "ocr": "OCR",
            }
            mapped = alias_map.get(lowered, value.upper())
            try:
                return TaskType(mapped)
            except Exception:
                return value
        return value
```

### Flutter Frontend (json_annotation)

```dart
// shared/entities/task_model.dart
import 'package:json_annotation/json_annotation.dart';

part 'task_model.g.dart';

enum TaskType {
  @JsonValue('LEARNING')  // ✅ 必须与后端完全一致
  learning,
  @JsonValue('TRAINING')
  training,
  @JsonValue('ERROR_FIX')
  errorFix,
  @JsonValue('REFLECTION')
  reflection,
  @JsonValue('SOCIAL')
  social,
  @JsonValue('PLANNING')
  planning,
  @JsonValue('OCR')
  ocr,
}

enum TaskStatus {
  @JsonValue('PENDING')
  pending,
  @JsonValue('IN_PROGRESS')
  inProgress,
  @JsonValue('COMPLETED')
  completed,
  @JsonValue('ABANDONED')
  abandoned,
}

// ✅ 使用 JsonSerializable 自动生成序列化代码
@JsonSerializable()
class TaskCreate {
  final String title;
  final TaskType type;  // 序列化时会自动使用 @JsonValue 定义的值
  final int estimatedMinutes;

  Map<String, dynamic> toJson() => _$TaskCreateToJson(this);
}
```

---

## 📊 常见错误与解决方案

### 错误 1: Flutter 发送中文显示名称
```json
// ❌ 错误请求
{
  "type": "学习"  // 这是显示文本，不是枚举值！
}

// ✅ 正确请求
{
  "type": "LEARNING"  // 使用 @JsonValue 定义的值
}
```

**解决方案**: 确保 UI 使用 `TaskType.learning` (enum 实例)，而不是 `_getTypeLabel(TaskType.learning)` (显示文本)。

### 错误 2: 大小写不一致
```
Backend: LEARNING (UPPERCASE)
Frontend: @JsonValue('learning') (lowercase)
```

**错误消息**:
```
Invalid argument(s): learning is not one of the supported values: LEARNING, TRAINING, ERROR_FIX...
```

**解决方案**: 统一使用 UPPERCASE 值。

### 错误 3: Protobuf Oneof 字段冲突
```python
# ❌ 错误：同时设置 oneof 字段
yield ChatResponse(
    delta=chunk,
    status_update=AgentStatus(...)  # 会覆盖 delta！
)

# ✅ 正确：分开发送
yield ChatResponse(status_update=AgentStatus(...))
yield ChatResponse(delta=chunk)
```

---

## ✅ 检查清单

添加新 Enum 时，必须完成以下步骤：

### Backend
- [ ] 在 `app/models/` 定义 Enum，值使用 UPPERCASE
- [ ] 在 `app/schemas/` 添加 Pydantic 验证
- [ ] 在 Schema 的 field_validator 中添加 alias_map 支持小写输入
- [ ] 运行 `alembic revision --autogenerate -m "add enum"`
- [ ] 运行 `alembic upgrade head`

### Frontend
- [ ] 在 `shared/entities/` 定义 Enum，使用 `@JsonValue('UPPERCASE')`
- [ ] 运行 `flutter pub run build_runner build --delete-conflicting-outputs`
- [ ] 在 `core/design/tokens/` 添加颜色/图标映射（如需要）
- [ ] 在所有 switch 语句中添加新 case

### 测试
- [ ] 测试创建资源时 Enum 序列化
- [ ] 测试更新资源时 Enum 反序列化
- [ ] 测试前端显示时 Enum 到文本的转换

---

## 📚 参考示例

### 完整工作流：添加新任务类型 "QUICK"

#### 1. Backend (Python)
```python
# app/models/task.py
class TaskType(str, enum.Enum):
    # ... existing types ...
    QUICK = "QUICK"  # 新增

# app/schemas/task.py
alias_map = {
    # ... existing mappings ...
    "quick": "QUICK",  # 新增
}
```

#### 2. Frontend (Flutter)
```dart
// shared/entities/task_model.dart
enum TaskType {
  // ... existing values ...
  @JsonValue('QUICK')  // 新增
  quick,
}

// features/task/presentation/screens/task_create_screen.dart
String _getTypeLabel(TaskType type) {
  switch (type) {
    // ... existing cases ...
    case TaskType.quick:  // 新增
      return '快速';
  }
}

// core/design/tokens/task_colors.dart
class _RawTaskColors {
  // ... existing colors ...
  static const Color quick = Color(0xFF00BCD4);  // 新增
}
```

#### 3. 重新生成代码
```bash
# Backend
cd backend && alembic revision -m "add quick task type"

# Frontend
cd mobile && flutter pub run build_runner build --delete-conflicting-outputs
```

---

## 🔍 调试技巧

### 查看 Flutter 发送的 JSON
在 `api_interceptor.dart` 的 LoggingInterceptor 中启用详细日志：

```dart
@override
void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
  if (kDebugMode) {
    _logger.d('Request Body: ${options.data}');  // 查看实际发送的值
  }
  super.onRequest(options, handler);
}
```

### 查看 Python 接收的值
在 Pydantic Schema 中添加日志：

```python
@field_validator("type", mode="before")
@classmethod
def _normalize_task_type(cls, value):
    logger.info(f"Received type: {value}, type: {type(value)}")  # 调试日志
    # ... validation logic
```

---

**文档版本**: 1.0.0
**最后更新**: 2026-02-01
**维护者**: Sparkle 开发团队
