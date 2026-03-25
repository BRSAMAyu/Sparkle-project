# 快速修复清单 - 星火AI生产就绪

## 🔴 立即执行（5分钟）

### 1. 修复Flutter JSON序列化

```bash
# 进入mobile目录
cd /Users/a/code/sparkle-flutter/mobile

# 生成JSON序列化代码
flutter pub run build_runner build --delete-conflicting-outputs

# 修复代码风格问题
dart fix --apply
```

**预期结果**: 生成`seed_library_model.g.dart`和`transparency_settings_screen.g.dart`

### 2. 运行数据库迁移

```bash
# 进入backend目录
cd /Users/a/code/sparkle-flutter/backend

# 应用最新的数据库迁移
alembic upgrade head

# 验证迁移成功
alembic current
```

**预期结果**: 显示`ec25882a0a41 (head) (mergepoint)`

---

## 🟡 本周完成（集成工作）

### 3. 创建用户偏好服务

```bash
# 创建文件
cat > /Users/a/code/sparkle-flutter/mobile/lib/core/services/user_preferences_service.dart << 'EOF'
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class UserPreferencesService {
  final SharedPreferences _prefs;

  UserPreferencesService(this._prefs);

  Future<Map<String, dynamic>> getPreferences() async {
    final prefsJson = _prefs.getString('user_preferences') ?? '{}';
    return Map<String, dynamic>.from(json.decode(prefsJson));
  }

  Future<void> updatePreferences(Map<String, dynamic> updates) async {
    final current = await getPreferences();
    final updated = {...current, ...updates};
    await _prefs.setString('user_preferences', json.encode(updated));
  }
}

final userPreferencesServiceProvider = Provider<UserPreferencesService>((ref) {
  throw UnimplementedError('userPreferencesServiceProvider must be overridden');
});
EOF
```

### 4. 集成透明度生成器

```bash
# 编辑 orchestrator.py
# 在 app/orchestration/orchestrator.py 顶部添加导入
cd /Users/a/code/sparkle-flutter/backend
cat >> /tmp/transparency_integration.txt << 'EOF'

# 在 Orchestrator.__init__ 中添加:
from app.orchestration.transparency_data_generator import TransparencyDataGenerator

class Orchestrator:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.transparency_generator = TransparencyDataGenerator()

# 在工具执行位置添加:
async def execute_tool(self, tool_name: str, **kwargs):
    step = self.transparency_generator.create_step(
        name=f"Execute {tool_name}",
        step_type=StepType.TOOL_EXECUTION,
        agent_type="tool_executor"
    )

    self.transparency_generator.start_step(step)

    # 发送WebSocket事件
    if self.stream_callback:
        await self.stream_callback({
            "type": "delta",
            "delta": "",
            "metadata": {
                "transparency_step": self.transparency_generator.get_step_event(step)
            }
        })

    try:
        result = await tool.execute(**kwargs)
        self.transparency_generator.complete_step(step, result)

        # 发送完成事件
        if self.stream_callback:
            await self.stream_callback({
                "type": "delta",
                "delta": "",
                "metadata": {
                    "transparency_step": self.transparency_generator.get_step_event(step)
                }
            })

        return result
    except Exception as e:
        self.transparency_generator.complete_step(step, None, error=str(e))
        raise
EOF

cat /tmp/transparency_integration.txt
```

**手动操作**: 将上述代码集成到`app/orchestration/orchestrator.py`的相应位置

### 5. 集成记忆演化追踪

```bash
# 编辑 memory_service.py
# 在 app/services/memory_service.py 顶部添加导入
cat >> /tmp/memory_evolution_integration.txt << 'EOF'

# 在 MemoryService.__init__ 中添加:
from app.services.memory_evolution_service import MemoryEvolutionService

class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.evolution_service = MemoryEvolutionService(db)

# 在 update_preference 方法中添加（更新完成后）:
async def update_preference(self, user_id, preference_id, **updates):
    # ... 现有更新逻辑 ...

    # 记录演化
    await self.evolution_service.track_memory_change(
        memory_id=preference_id,
        memory_type='preference',
        old_value=old_pref.to_dict(),
        new_value=new_pref.to_dict(),
        change_reason='user_edit',
        trigger_event='preference_update',
        workflow_id=None
    )

    return new_pref
EOF

cat /tmp/memory_evolution_integration.txt
```

**手动操作**: 将上述代码集成到`app/services/memory_service.py`的相应位置

### 6. 集成自动入库机制

```bash
# 编辑 response_feedback_service.py
# 在 app/services/response_feedback_service.py 添加
cat >> /tmp/auto_seed_integration.txt << 'EOF'

# 在 ResponseFeedbackService.__init__ 中添加:
from app.services.content_quality_evaluator import ContentQualityEvaluator

class ResponseFeedbackService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.quality_evaluator = ContentQualityEvaluator(db)

# 在 process_feedback 方法中添加（保存反馈后）:
async def process_feedback(self, feedback: ResponseFeedback):
    # ... 保存反馈逻辑 ...

    # 检查质量并自动入库
    evaluation = await self.quality_evaluator.evaluate_response_quality(
        response_id=str(feedback.response_id)
    )

    if evaluation['should_seed']:
        logger.info(f"Auto-seeding response {feedback.response_id} to library")
        await self.quality_evaluator.auto_seed_to_library(
            response_id=str(feedback.response_id),
            target_library_id=None
        )

    return feedback
EOF

cat /tmp/auto_seed_integration.txt
```

**手动操作**: 将上述代码集成到`app/services/response_feedback_service.py`的相应位置

### 7. 注册Go Gateway A/B中间件

```bash
# 编辑 gateway/internal/router/router.go
cat >> /tmp/go_ab_integration.txt << 'EOF'

// 在文件顶部添加导入
import "gateway/internal/middleware"

// 在 SetupRouter 函数中添加:
func SetupRouter(engine *gin.Engine, config *Config) {
    // 创建A/B测试中间件
    abConfig := &middleware.ABTestConfig{
        BackendURL:            config.PythonBackendURL,
        ExperimentServiceAddr: config.ExperimentServiceURL,
        Timeout:              5 * time.Second,
        Enabled:              true,
    }
    abMiddleware := middleware.NewABTestMiddleware(abConfig)

    // 应用到API路由
    apiGroup := engine.Group("/api/v1")
    apiGroup.Use(abMiddleware.AssignVariant())
    apiGroup.Use(abMiddleware.RecordMetric())

    // ... 现有路由注册 ...
}
EOF

cat /tmp/go_ab_integration.txt
```

**手动操作**: 将上述代码集成到`gateway/internal/router/router.go`的相应位置

---

## 🟢 可选优化（测试和文档）

### 8. 添加单元测试

```bash
cd /Users/a/code/sparkle-flutter/backend

# A/B测试框架测试
cat > tests/unit/test_ab_test_framework.py << 'EOF'
import pytest
from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced

@pytest.mark.asyncio
async def test_create_experiment(db_session):
    framework = ABTestFrameworkEnhanced(db_session, config)

    experiment = await framework.create_experiment(
        name="Test Experiment",
        description="Test",
        hypothesis="Test hypothesis",
        variants=[
            {"name": "control", "weight": 0.5},
            {"name": "treatment", "weight": 0.5}
        ],
        metrics=["success"]
    )

    assert experiment.status == "created"
    assert experiment.name == "Test Experiment"
EOF

# 运行测试
pytest tests/unit/test_ab_test_framework.py -v
```

### 9. 验证API端点

```bash
cd /Users/a/code/sparkle-flutter/backend

# 启动服务器（如果未运行）
make grpc-server

# 在另一个终端测试API
curl -X GET http://localhost:8000/api/v1/experiments
curl -X GET http://localhost:8000/api/v1/user/persona/batch-edit-suggestions
```

---

## ✅ 验证检查清单

完成修复后，逐项验证：

### 后端验证

- [ ] 数据库迁移成功: `alembic current` 显示 `ec25882a0a41`
- [ ] 所有Python文件语法正确: `python -m py_compile app/...`
- [ ] 模块导入成功: 运行上面的导入测试
- [ ] API端点可访问: `curl http://localhost:8000/api/v1/experiments`
- [ ] 透明度生成器可导入: `from app.orchestration.transparency_data_generator import TransparencyDataGenerator`
- [ ] 记忆演化服务可导入: `from app.services.memory_evolution_service import MemoryEvolutionService`

### Flutter验证

- [ ] JSON序列化代码已生成: `ls mobile/lib/features/seed_library/data/models/*g.dart`
- [ ] 代码风格问题已修复: `flutter analyze` 无错误
- [ ] 用户偏好服务已创建: `ls mobile/lib/core/services/user_preferences_service.dart`
- [ ] 应用可编译: `flutter build apk --debug`

### Go验证

- [ ] A/B中间件已注册: 检查`router.go`包含`abMiddleware`
- [ ] Go代码可编译: `cd gateway && go build`

---

## 🚀 部署顺序

1. **准备阶段** (今天)
   - ✅ 运行Flutter build_runner
   - ✅ 运行数据库迁移
   - ✅ 创建用户偏好服务

2. **集成阶段** (本周)
   - ✅ 集成透明度生成器
   - ✅ 集成记忆演化追踪
   - ✅ 集成自动入库机制
   - ✅ 注册Go A/B中间件

3. **测试阶段** (下周)
   - ✅ 单元测试
   - ✅ 集成测试
   - ✅ 端到端测试

4. **部署阶段** (生产环境)
   - ✅ 数据库迁移
   - ✅ 后端服务重启
   - ✅ Go Gateway重启
   - ✅ Flutter应用发布

---

## 📞 遇到问题？

### Flutter生成失败
```bash
# 清理并重试
cd mobile
flutter clean
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
```

### 数据库迁移冲突
```bash
# 检查当前状态
alembic current

# 查看未应用的迁移
alembic heads

# 强制到特定版本（谨慎使用）
alembic upgrade ec25882a0a41
```

### Python导入错误
```bash
# 激活虚拟环境
source .venv/bin/activate

# 重新安装依赖
pip install -e .

# 验证安装
python -c "from app.models.experiment import ABExperiment; print('OK')"
```

---

**总预计时间**:
- 快速修复: 5分钟
- 集成工作: 2-3小时
- 测试验证: 1-2天
- 总计: 2-3天完成所有集成和测试

**优先级**: 🔴 立即执行第1-2项 → 🟡 本周完成第3-7项 → 🟢 可选执行第8-9项
