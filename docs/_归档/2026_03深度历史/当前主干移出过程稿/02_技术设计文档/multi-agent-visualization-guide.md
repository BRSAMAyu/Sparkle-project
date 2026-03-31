# Multi-Agent 协作可视化系统使用指南

## 概述

本系统实现了一个完整的Multi-Agent协作可视化方案，让用户能够直观地看到不同的AI"专家"在接力工作。

## 核心设计

### Agent 角色定义

| Agent | 职责 | 图标 | 主题色 | 动画隐喻 |
|-------|------|------|--------|----------|
| **Orchestrator** | 主脑/指挥官 - 理解意图、拆解任务、汇总结果 | 🧠 `Icons.psychology` | 紫色 `#9C27B0` | 呼吸脉冲 (思考中) |
| **KnowledgeAgent** | 图书管理员 - GraphRAG检索、查阅文档 | ✨ `Icons.auto_awesome` | 蓝色 `#2196F3` | 旋转扫描 (检索中) |
| **MathAgent** | 计算专家 - 数值计算、公式推导 | 🔢 `Icons.calculate` | 琥珀色 `#FFC107` | 数字跳动 (计算中) |
| **CodeAgent** | 工程师 - 生成代码、调试、运行 | 💻 `Icons.terminal` | 绿色 `#4CAF50` | 光标闪烁 (编码中) |

## 技术实现路径

### 1. 协议层 (Protocol Layer)

**文件**: `proto/agent_service.proto`

添加了 `AgentType` 枚举和 `active_agent` 字段到 `AgentStatus` 消息中：

```protobuf
enum AgentType {
    AGENT_UNKNOWN = 0;
    ORCHESTRATOR = 1;
    KNOWLEDGE = 2;
    MATH = 3;
    CODE = 4;
}

message AgentStatus {
    State state = 1;
    string details = 2;
    string current_agent_name = 3;  // Legacy
    AgentType active_agent = 4;     // 🆕 类型安全的agent标识
}
```

### 2. 后端调度逻辑 (Backend Layer)

**文件**: `backend/app/orchestration/orchestrator.py`

#### 核心改动

1. **工具到Agent的映射函数**:
```python
def get_agent_type_for_tool(tool_name: str) -> int:
    """根据工具名称返回对应的AgentType"""
    if any(keyword in tool_name for keyword in ['knowledge', 'query', 'search']):
        return agent_service_pb2.KNOWLEDGE
    if any(keyword in tool_name for keyword in ['math', 'calculate', 'wolfram']):
        return agent_service_pb2.MATH
    if any(keyword in tool_name for keyword in ['code', 'execute', 'system']):
        return agent_service_pb2.CODE
    if any(keyword in tool_name for keyword in ['task', 'plan', 'create']):
        return agent_service_pb2.ORCHESTRATOR
    return agent_service_pb2.ORCHESTRATOR
```

2. **发送Agent状态时携带类型**:
```python
yield agent_service_pb2.ChatResponse(
    status_update=agent_service_pb2.AgentStatus(
        state=agent_service_pb2.AgentStatus.EXECUTING_TOOL,
        details=f"Executing {tool_name}...",
        active_agent=get_agent_type_for_tool(tool_name)  # 🆕
    )
)
```

### 3. 前端视觉引擎 (Flutter Layer)

**核心组件**: `mobile/lib/presentation/widgets/chat/agent_avatar_switcher.dart`

#### 关键Widget

##### 1. `AgentAvatarSwitcher` - Agent头像切换器

支持平滑的角色切换动画：

```dart
AgentAvatarSwitcher(
  agentType: AgentType.knowledge,  // 当前活跃的Agent
  size: 32,
  showPulseAnimation: true,  // 是否显示脉冲动画
)
```

**动画特性**:
- 使用 `AnimatedSwitcher` 实现无缝溶解切换
- 组合动画：旋转 + 缩放 + 淡入淡出
- 自动根据AgentType显示对应的图标和颜色

##### 2. `AgentStatusIndicator` - Agent状态指示器

完整的状态显示组件：

```dart
AgentStatusIndicator(
  agentType: AgentType.math,
  statusText: "MathAgent 正在解微分方程...",
  isThinking: true,
)
```

**视觉效果**:
- 带边框的圆角容器
- 动态背景色（基于Agent主题色）
- 可选的loading指示器

#### 核心工具函数

**protobuf值到AgentType的映射**:
```dart
AgentType agentTypeFromProto(int protoValue) {
  switch (protoValue) {
    case 1: return AgentType.orchestrator;
    case 2: return AgentType.knowledge;
    case 3: return AgentType.math;
    case 4: return AgentType.code;
    default: return AgentType.orchestrator;
  }
}
```

## 演示效果剧本

### 场景：用户提问 "请帮我计算这个物理抛物线公式的极值，并用 Python 绘制图像"

#### Phase 1: 指挥阶段
- **图标**: 🧠 紫色 (Orchestrator)
- **文字**: "Orchestrator 正在拆解任务：1.数学计算 -> 2.代码绘制"
- **动画**: 呼吸脉冲效果

#### Phase 2: 数学计算
- **切换动画**: 紫色大脑旋转消失 → 琥珀色计算器弹跳出现
- **图标**: 🔢 琥珀色 (MathAgent)
- **文字**: "MathAgent 正在推导极值点..."
- **视觉**: 气泡边框隐约闪烁琥珀色光芒

#### Phase 3: 代码生成
- **切换动画**: 计算器淡出 → 绿色终端滑入
- **图标**: 💻 绿色 (CodeAgent)
- **文字**: "CodeAgent 正在生成 Matplotlib 绘图代码..."

#### Phase 4: 完成
- **图标**: ✅ 绿色勾选
- **文字**: "任务完成"
- **结果**: 展示最终输出

## 集成指南

### 在聊天界面中使用

1. **监听WebSocket的AgentStatus消息**:
```dart
// 在处理gRPC响应时
if (response.hasStatusUpdate()) {
  final status = response.statusUpdate;
  final agentType = agentTypeFromProto(status.activeAgent);

  // 更新UI显示当前活跃的Agent
  setState(() {
    _currentAgent = agentType;
    _statusText = status.details;
  });
}
```

2. **在推理气泡中显示**:
```dart
AgentReasoningBubble(
  steps: reasoningSteps,
  isThinking: true,
  // AgentReasoningBubble内部已集成AgentAvatarSwitcher
)
```

### 自定义Agent配置

如果需要添加新的Agent类型：

1. 在 `proto/agent_service.proto` 中添加枚举值
2. 运行 `make proto-gen` 重新生成代码
3. 在 `agentTypeFromProto()` 中添加映射
4. 在 `AgentConfig.forType()` 中添加视觉配置

## 技术特性

### 性能优化
- ✅ 使用 `AnimatedSwitcher` 的内置动画优化
- ✅ Widget复用（通过 `ValueKey` 识别变化）
- ✅ 避免不必要的重建

### 可访问性
- ✅ 清晰的颜色对比度
- ✅ 描述性的状态文本
- ✅ 图标 + 文字的双重指示

### 可维护性
- ✅ 集中式的Agent配置管理
- ✅ 类型安全的枚举使用
- ✅ 清晰的职责分离

## 故障排查

### 常见问题

**Q: Agent图标没有切换动画？**
A: 确保每个AgentAvatarSwitcher的child都有唯一的 `ValueKey`。

**Q: 从后端收到的agent类型无法识别？**
A: 检查protobuf值是否正确映射，查看 `agentTypeFromProto()` 函数。

**Q: 动画卡顿？**
A: 检查是否在build方法中创建了AnimationController，应该在initState中创建。

## 下一步计划

- [ ] 添加更多Agent类型（如 DataAnalysisAgent, TranslationAgent）
- [ ] 支持Agent之间的交接动画（流线效果）
- [ ] 添加音效反馈
- [ ] 支持自定义主题色

## 相关文件

### 协议定义
- `proto/agent_service.proto` - gRPC协议定义

### 后端
- `backend/app/orchestration/orchestrator.py` - 主orchestrator
- `backend/app/gen/agent/v1/` - 生成的Python protobuf代码

### 前端
- `mobile/lib/presentation/widgets/chat/agent_avatar_switcher.dart` - Agent头像组件
- `mobile/lib/presentation/widgets/chat/agent_reasoning_bubble_v2.dart` - 推理气泡
- `mobile/lib/data/models/reasoning_step_model.dart` - 数据模型

## 贡献者

Claude Code & User - 2025-12-27
