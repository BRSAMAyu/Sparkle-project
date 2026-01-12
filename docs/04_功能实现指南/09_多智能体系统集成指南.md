# Enhanced Multi-Agent System - Quick Integration Guide

> **快速集成指南** - 5 分钟内将增强版多智能体系统集成到 Sparkle

---

## 📦 文件清单

### 新增文件

```
backend/app/agents/
├── enhanced_agents.py              # 增强版 Agent (StudyPlanner, ProblemSolver)
├── collaboration_workflows.py      # 协作工作流 (3种)
├── enhanced_orchestrator.py        # 增强版协调器
└── INTEGRATION_GUIDE.md           # 本文件

mobile/lib/presentation/widgets/agents/
└── collaboration_timeline.dart     # 协作时间线组件

docs/03_重构与优化报告/
└── 多智能体系统实现报告.md        # 完整文档
```

---

## 🚀 快速集成步骤

### Step 1: 更新 Orchestrator (3 分钟)

**文件**: `backend/app/orchestration/orchestrator.py`

```python
# 1. 添加导入
from app.agents.enhanced_orchestrator import create_enhanced_orchestrator

class ChatOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        # ... 其他初始化 ...

        # 2. 替换原有的 multi_agent_workflow
        # self.multi_agent_workflow = create_multi_agent_workflow()  # 旧版
        self.multi_agent_workflow = create_enhanced_orchestrator()  # 新版

    async def process_stream(
        self,
        request: ChatRequest
    ) -> AsyncGenerator[str, None]:
        # ... 现有代码保持不变 ...

        # 3. 调用多智能体工作流
        context = AgentContext(
            user_id=request.user_id,
            session_id=request.session_id,
            user_query=request.message,
            conversation_history=pruned_history
        )

        response = await self.multi_agent_workflow.process(context)

        # 4. 检查是否为协作模式，发送时间线数据
        if response.metadata and response.metadata.get("collaboration"):
            # 发送协作时间线数据
            timeline_data = {
                "type": "collaboration_timeline",
                "workflow": response.metadata["workflow"],
                "timeline": response.metadata["visualization"]["timeline"],
                "execution_time": response.metadata["execution_time"]
            }
            yield json.dumps(timeline_data) + "\n"

        # 5. 发送 Agent 响应
        yield response.response_text

        # 6. 处理工具调用（任务生成）
        if response.metadata and "tool_calls" in response.metadata:
            await self._handle_tool_calls(
                response.metadata["tool_calls"],
                request.user_id
            )

    async def _handle_tool_calls(
        self,
        tool_calls: List[Dict],
        user_id: UUID
    ):
        """处理 Agent 生成的工具调用（如创建任务）"""
        from app.services.task_service import TaskService
        from app.schemas.task import TaskCreate

        for call in tool_calls:
            if call["function"] == "create_task":
                try:
                    await TaskService.create(
                        db=self.db,
                        obj_in=TaskCreate(**call["arguments"]),
                        user_id=user_id
                    )
                    logger.info(f"Auto-created task: {call['arguments']['title']}")
                except Exception as e:
                    logger.error(f"Failed to create task: {e}")
```

---

### Step 2: 添加 Flutter 依赖 (1 分钟)

**文件**: `mobile/pubspec.yaml`

```yaml
dependencies:
  flutter:
    sdk: flutter
  # ... 其他依赖 ...
  flutter_animate: ^4.5.0  # 新增：动画库
```

**运行**:
```bash
cd mobile
flutter pub get
```

---

### Step 3: 集成 Timeline 组件 (1 分钟)

**文件**: `mobile/lib/presentation/screens/chat/chat_screen.dart`

```dart
import 'package:sparkle/presentation/widgets/agents/collaboration_timeline.dart';

class ChatMessageBubble extends StatelessWidget {
  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    // 检查是否为协作模式消息
    if (message.metadata?['collaboration'] == true) {
      final timeline = (message.metadata!['visualization']['timeline'] as List)
          .map((step) => AgentTimelineStep.fromJson(step))
          .toList();

      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
        child: AgentCollaborationTimeline(
          steps: timeline,
          workflowType: message.metadata!['workflow'],
          executionTime: message.metadata!['execution_time'] ?? 0.0,
        ),
      );
    }

    // 普通消息气泡
    return Container(
      // ... 原有消息气泡代码 ...
    );
  }
}
```

---

## ✅ 验证集成

### 测试 1: 学习计划生成

**输入**:
```
用户: "帮我准备下周的高数期末考试"
```

**预期**:
1. 后端日志显示 `[EnhancedOrchestrator] Selected workflow: task_decomposition`
2. 前端收到协作时间线数据
3. 显示 3-4 个 Agent 的协作流程
4. 自动创建任务卡片

---

### 测试 2: 深度解析

**输入**:
```
用户: "详细解释神经网络的反向传播原理"
```

**预期**:
1. 触发 `progressive_exploration` 工作流
2. 依次调用 Math → Code → Science → Writing → StudyPlanner
3. 前端显示 5 个 Agent 的时间线
4. 多角度深度解析

---

### 测试 3: 错题诊断

**输入**:
```
用户: "这道极限题我总是做错"
```

**预期**:
1. 触发 `error_diagnosis` 工作流
2. ProblemSolver 分析错误模式（苏格拉底式提问）
3. StudyPlanner 生成复习计划
4. 自动创建错题复习任务

---

## 🔧 配置选项

### 启用/禁用协作工作流

如果你暂时只想使用单个 Agent，可以在 `enhanced_orchestrator.py` 中修改：

```python
async def _select_workflow_type(self, query: str) -> str:
    # 强制降级为单 Agent 模式
    return "default"

    # 或者只启用特定工作流
    if "计划" in query or "复习" in query:
        return "task_decomposition"
    else:
        return "default"
```

---

### 调整 LLM 模型

每个 Agent 使用不同的模型，可在 `enhanced_agents.py` 和 `specialist_agents.py` 中修改：

```python
# StudyPlannerAgent
response_text = await llm_service.chat(
    messages=[...],
    model="qwen-plus",  # 改为其他模型：deepseek-chat, gpt-4, etc.
    temperature=0.7
)
```

---

## 🐛 常见问题

### Q1: 后端报错 "No module named 'app.agents.enhanced_agents'"

**原因**: Python 模块未被识别

**解决**:
```bash
cd backend
python -c "from app.agents.enhanced_agents import StudyPlannerAgent; print('OK')"
```

如果报错，检查 `backend/app/agents/__init__.py` 是否存在。

---

### Q2: 前端报错 "Target of URI doesn't exist: flutter_animate"

**原因**: 依赖未安装

**解决**:
```bash
cd mobile
flutter pub get
flutter pub upgrade
```

---

### Q3: 协作时间线不显示

**原因**: 后端未发送正确的元数据格式

**调试**:
```python
# 在 orchestrator.py 中添加日志
if response.metadata and response.metadata.get("collaboration"):
    logger.info(f"[DEBUG] Collaboration metadata: {response.metadata}")
    # 检查是否包含 'visualization' 和 'timeline' 字段
```

---

### Q4: 任务未自动创建

**原因**: `_handle_tool_calls` 未被调用

**调试**:
```python
# 检查 response.metadata 中是否包含 tool_calls
logger.info(f"[DEBUG] Response metadata: {response.metadata}")

if response.metadata and "tool_calls" in response.metadata:
    logger.info(f"[DEBUG] Tool calls: {response.metadata['tool_calls']}")
    await self._handle_tool_calls(...)
```

---

## 📊 性能优化建议

### 1. 知识星图数据预加载

在用户登录时预加载知识星图数据，避免每次请求都查询数据库：

```python
# backend/app/api/v1/auth.py

@router.post("/login")
async def login(request: LoginRequest):
    # ... 登录逻辑 ...

    # 预加载知识星图数据到 Redis
    galaxy_service = GalaxyService(db)
    galaxy_data = await galaxy_service.get_galaxy_graph(user_id)
    await cache_service.set(
        f"galaxy:{user_id}",
        galaxy_data,
        ttl=600  # 10分钟
    )
```

---

### 2. 并行调用优化

在 `collaboration_workflows.py` 中，确保所有可以并行的 Agent 调用都使用 `asyncio.gather`：

```python
# 已优化示例
parallel_tasks = [
    ("MathExpert", MathAgent().process(math_context)),
    ("CodeExpert", CodeAgent().process(code_context)),
    ("WritingExpert", WritingAgent().process(writing_context)),
]

results = await asyncio.gather(
    *[task for _, task in parallel_tasks],
    return_exceptions=True
)
```

---

### 3. LLM 响应流式返回

修改 `enhanced_agents.py` 中的 LLM 调用，使用流式 API：

```python
async def _generate_study_plan(...):
    # 替换为流式调用
    async for chunk in llm_service.stream_chat(
        messages=[...],
        model="qwen-plus"
    ):
        yield chunk  # 逐字返回给前端
```

---

## 📚 下一步

1. **[ ] 真实数据集成**
   - 替换 `_build_enhanced_context` 中的模拟数据
   - 调用真实的 GalaxyService、DecayService、TaskService

2. **[ ] 单元测试**
   - `tests/agents/test_enhanced_agents.py`
   - `tests/agents/test_collaboration_workflows.py`

3. **[ ] 性能监控**
   - Grafana Dashboard（查看协作工作流耗时）
   - Prometheus Metrics（Agent 调用成功率）

---

## 🎉 完成！

现在你的 Sparkle 已经拥有了一套**教育导向的多智能体协作系统**！

**快速验证**:
```bash
# 后端
cd backend
python -c "from app.agents.enhanced_orchestrator import create_enhanced_orchestrator; print('✅ Backend OK')"

# 前端
cd mobile
flutter analyze | grep collaboration_timeline.dart
# 应该显示没有严重错误
```

---

**如有问题，请参考**: `docs/03_重构与优化报告/多智能体系统实现报告.md`
