# Enhanced Multi-Agent System v2.0

> **教育导向的 AI 导师团队** - 基于知识星图和遗忘曲线的个性化学习支持

---

## 🎯 核心特性

### 1. 新增教育导向 Agent

| Agent | 角色 | 核心能力 |
|-------|------|----------|
| **StudyPlannerAgent** | 学习规划师 | 基于遗忘曲线安排科学复习<br>识别薄弱知识点<br>自动生成任务卡片 |
| **ProblemSolverAgent** | 问题解决导师 | 苏格拉底式教学法<br>知识点关联教学<br>错题模式识别 |

### 2. 三大协作工作流

- **TaskDecompositionWorkflow** (任务分解协作)
  - 适用场景：考试准备、学习计划制定
  - Agent 组合：StudyPlanner → [Math, Code, Writing] → Orchestrator

- **ProgressiveExplorationWorkflow** (渐进式深度探索)
  - 适用场景：概念深度解析
  - Agent 组合：Math → Code → Science → Writing → StudyPlanner

- **ErrorDiagnosisWorkflow** (错题诊断循环)
  - 适用场景：错题分析、薄弱点强化
  - Agent 组合：ProblemSolver → StudyPlanner → [Math/Code] → Tasks

### 3. 数据集成

- ✅ **知识星图** (GalaxyService): 掌握度、节点关系
- ✅ **遗忘曲线** (DecayService): 记忆衰减预测
- ✅ **任务系统** (TaskService): 自动任务生成
- ✅ **OpenTelemetry**: 分布式追踪

---

## 📁 文件结构

```
backend/app/agents/
├── __init__.py                      # 包导出
├── base_agent.py                    # Agent 基类
├── specialist_agents.py             # 原有专家 (Math, Code, Writing, Science)
├── orchestrator_agent.py            # 原有协调器
├── enhanced_agents.py               # 🆕 增强版 Agent (StudyPlanner, ProblemSolver)
├── enhanced_orchestrator.py         # 🆕 增强版协调器
├── collaboration_workflows.py       # 🆕 协作工作流
├── INTEGRATION_GUIDE.md            # 🆕 快速集成指南
└── README.md                        # 🆕 本文件

mobile/lib/presentation/widgets/agents/
└── collaboration_timeline.dart      # 🆕 协作时间线组件

docs/03_重构与优化报告/
└── 多智能体系统实现报告.md          # 🆕 完整文档
```

---

## 🚀 快速开始

### 1. 导入增强版 Orchestrator

```python
from app.agents import create_enhanced_orchestrator

# 创建协调器
orchestrator = create_enhanced_orchestrator()

# 处理用户请求
response = await orchestrator.process(context)
```

### 2. 检查协作模式

```python
if response.metadata and response.metadata.get("collaboration"):
    # 协作模式：包含时间线数据
    workflow_type = response.metadata["workflow"]
    timeline = response.metadata["visualization"]["timeline"]
    participants = response.metadata["participants"]
```

### 3. 处理任务生成

```python
if response.metadata and "tool_calls" in response.metadata:
    for call in response.metadata["tool_calls"]:
        if call["function"] == "create_task":
            # 调用 TaskService 创建任务
            await TaskService.create(db, TaskCreate(**call["arguments"]), user_id)
```

---

## 📊 示例用法

### 场景 1: 学习计划生成

```python
from app.agents import EnhancedOrchestratorAgent, AgentContext

orchestrator = EnhancedOrchestratorAgent()

context = AgentContext(
    user_id=user_id,
    session_id=session_id,
    user_query="帮我准备下周的高数期末考试",
    conversation_history=[]
)

response = await orchestrator.process(context)

# 输出示例：
# workflow_type: "task_decomposition"
# participants: ["StudyPlanner", "MathExpert", "WritingExpert"]
# 自动创建 3-5 个任务卡片
```

### 场景 2: 错题诊断

```python
context = AgentContext(
    user_id=user_id,
    session_id=session_id,
    user_query="这道极限题我总是做错：lim(x→0) sin(x)/x",
    conversation_history=[]
)

response = await orchestrator.process(context)

# 输出示例：
# workflow_type: "error_diagnosis"
# participants: ["ProblemSolver", "StudyPlanner", "MathExpert"]
# 苏格拉底式引导 + 复习计划 + 练习题
```

---

## 🔧 配置

### 环境变量

```bash
# .env
LLM_PROVIDER=qwen  # 或 deepseek, openai
LLM_API_KEY=your_api_key
LLM_MODEL_NAME=qwen-plus  # 或 deepseek-chat
```

### 启用/禁用协作工作流

在 `enhanced_orchestrator.py` 中修改：

```python
async def _select_workflow_type(self, query: str) -> str:
    # 强制使用单 Agent 模式
    return "default"

    # 或者只启用特定工作流
    if "计划" in query:
        return "task_decomposition"
    return "default"
```

---

## 🧪 测试

### 运行单元测试

```bash
cd backend
pytest tests/agents/test_enhanced_orchestrator.py -v
```

### 测试覆盖率

```bash
pytest tests/agents/ --cov=app.agents --cov-report=html
```

---

## 📚 文档

- **完整文档**: `docs/03_重构与优化报告/多智能体系统实现报告.md`
- **集成指南**: `INTEGRATION_GUIDE.md`
- **API 文档**: 每个类和方法都有详细的 docstring

---

## 🎉 特色亮点

1. **深度个性化**
   - 基于知识星图的薄弱点识别
   - 遗忘曲线驱动的复习安排
   - 学习行为模式分析

2. **苏格拉底式教学**
   - 不直接给答案，引导学生思考
   - 关联已掌握的知识点
   - 提醒常见错误

3. **自动任务生成**
   - Agent 自动调用 `create_task` 工具
   - 优先级智能排序
   - 与学习计划无缝集成

4. **生产级架构**
   - OpenTelemetry 分布式追踪
   - 多层降级策略
   - 并行执行优化

---

## 🛠️ 下一步开发

### 高优先级
- [ ] 真实数据集成（GalaxyService, DecayService）
- [ ] 单元测试覆盖率 > 80%
- [ ] LLM 响应流式返回

### 中优先级
- [ ] 思维导图生成器
- [ ] 学习进度可视化面板
- [ ] 学习模式识别

### 低优先级
- [ ] 动态难度调节
- [ ] 多轮对话优化

---

## 🤝 贡献

欢迎提交 PR 和 Issue！请参考：
- 代码规范：遵循 PEP 8
- 提交信息：使用 Conventional Commits 格式
- 测试：新功能必须包含单元测试

---

## 📄 License

MIT License - 详见项目根目录的 LICENSE 文件

---

**Built with ❤️ for Sparkle AI Learning Assistant**
