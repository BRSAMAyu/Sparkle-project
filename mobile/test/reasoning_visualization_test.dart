import 'package:flutter/material.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/reasoning_step_model.dart';
import 'package:sparkle/presentation/widgets/chat/agent_reasoning_bubble_v2.dart';

/// Mock Data Test for Chain of Thought Visualization
///
/// This file demonstrates how the reasoning visualization works
/// without needing a live backend connection.

void main() {
  runApp(const TestApp());
}

class TestApp extends StatelessWidget {
  const TestApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
      title: 'Chain of Thought Visualization Test',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        brightness: Brightness.dark,
      ),
      home: const ReasoningVisualizationDemo(),
    );
}

class ReasoningVisualizationDemo extends StatefulWidget {
  const ReasoningVisualizationDemo({super.key});

  @override
  State<ReasoningVisualizationDemo> createState() => _ReasoningVisualizationDemoState();
}

class _ReasoningVisualizationDemoState extends State<ReasoningVisualizationDemo> {
  bool _showRealTime = false;
  final bool _showCompleted = false;

  // Mock: Real-time reasoning steps (streaming in)
  final List<ReasoningStep> _realTimeSteps = [
    ReasoningStep(
      id: 'step_1',
      description: '正在规划解题路径...',
      agent: AgentType.orchestrator,
      status: StepStatus.completed,
      createdAt: DateTime.now().subtract(const Duration(seconds: 5)),
      completedAt: DateTime.now().subtract(const Duration(seconds: 4)),
    ),
    ReasoningStep(
      id: 'step_2',
      description: '解析微积分公式结构',
      agent: AgentType.math,
      status: StepStatus.completed,
      createdAt: DateTime.now().subtract(const Duration(seconds: 4)),
      completedAt: DateTime.now().subtract(const Duration(seconds: 3)),
    ),
    ReasoningStep(
      id: 'step_3',
      description: '正在生成 Python 代码...',
      agent: AgentType.code,
      status: StepStatus.inProgress,
      toolOutput: '```python\nimport numpy as np\n\ndef derivative(f, x, h=1e-5):\n    """计算函数f在x处的导数"""\n    return (f(x + h) - f(x - h)) / (2 * h)\n```',
      createdAt: DateTime.now().subtract(const Duration(seconds: 3)),
    ),
  ];

  // Mock: Completed reasoning steps
  final List<ReasoningStep> _completedSteps = [
    ReasoningStep(
      id: 'step_1',
      description: '分析用户查询意图',
      agent: AgentType.orchestrator,
      status: StepStatus.completed,
      createdAt: DateTime.now().subtract(const Duration(seconds: 8)),
      completedAt: DateTime.now().subtract(const Duration(seconds: 7)),
    ),
    ReasoningStep(
      id: 'step_2',
      description: '检索微积分基本定理相关知识',
      agent: AgentType.knowledge,
      status: StepStatus.completed,
      citations: ['Calc-101', 'Derivative-Concepts'],
      createdAt: DateTime.now().subtract(const Duration(seconds: 7)),
      completedAt: DateTime.now().subtract(const Duration(seconds: 5)),
    ),
    ReasoningStep(
      id: 'step_3',
      description: '计算导数公式',
      agent: AgentType.math,
      status: StepStatus.completed,
      toolOutput: 'Result: d/dx(x²) = 2x',
      createdAt: DateTime.now().subtract(const Duration(seconds: 5)),
      completedAt: DateTime.now().subtract(const Duration(seconds: 3)),
    ),
    ReasoningStep(
      id: 'step_4',
      description: '生成 Python 实现代码',
      agent: AgentType.code,
      status: StepStatus.completed,
      toolOutput: '```python\ndef power_derivative(x, n=2):\n    return n * x**(n-1)\n```',
      createdAt: DateTime.now().subtract(const Duration(seconds: 3)),
      completedAt: DateTime.now().subtract(const Duration(seconds: 1)),
    ),
  ];

  // Mock: Multi-agent collaboration
  final List<AgentContribution> _collaborationContributions = [
    AgentContribution(
      agentName: 'MathExpert',
      agentType: AgentType.math,
      reasoning: '根据微积分基本定理，导数是函数变化率的瞬时值',
      responseText: '导数公式: d/dx(x²) = 2x',
      confidence: 0.95,
      citations: ['Calc-101'],
    ),
    AgentContribution(
      agentName: 'CodeExpert',
      agentType: AgentType.code,
      reasoning: '将数学公式转换为Python函数实现',
      responseText: '使用幂函数直接计算，时间复杂度O(1)',
      confidence: 0.98,
      citations: ['Python-Best-Practices'],
    ),
    AgentContribution(
      agentName: 'KnowledgeGraph',
      agentType: AgentType.knowledge,
      reasoning: '检索相关知识点：导数定义、幂函数性质',
      responseText: '链接: Derivative-Concepts → Power-Rule',
      confidence: 0.92,
      citations: ['Derivative-Concepts', 'Power-Rule'],
    ),
  ];

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(
        title: const Text('Chain of Thought Visualization'),
        backgroundColor: Colors.deepPurple,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const SizedBox(height: 24),
            _buildSection(
              '1. 实时推理过程 (Real-time)',
              '模拟AI正在思考时的流式更新',
              _buildRealTimeDemo(),
            ),
            const SizedBox(height: 16),
            _buildSection(
              '2. 已完成的推理 (Completed)',
              '展示完整的思考过程',
              _buildCompletedDemo(),
            ),
            const SizedBox(height: 16),
            _buildSection(
              '3. 多智能体协作 (Multi-Agent)',
              '多个专家共同解决问题',
              _buildCollaborationDemo(),
            ),
            const SizedBox(height: 16),
            _buildSection(
              '4. 持久化消息 (Persisted)',
              '在历史消息中展示推理过程',
              _buildPersistedMessageDemo(),
            ),
          ],
        ),
      ),
    );

  Widget _buildHeader() => Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.deepPurple.shade700, Colors.blue.shade700],
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '🧠 Chain of Thought Visualization',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          SizedBox(height: 8),
          Text(
            'This demo shows the new reasoning visualization system for Sparkle.',
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
        ],
      ),
    );

  Widget _buildSection(String title, String subtitle, Widget content) => Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade900,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade700),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          Text(
            subtitle,
            style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
          ),
          const SizedBox(height: 12),
          content,
        ],
      ),
    );

  Widget _buildRealTimeDemo() => Column(
      children: [
        AgentReasoningBubble(
          steps: _realTimeSteps,
          isThinking: true,
          totalDurationMs: 2100,
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            ElevatedButton.icon(
              onPressed: () {
                setState(() {
                  _showRealTime = !_showRealTime;
                  if (_showRealTime) {
                    // Simulate adding a new step
                    _realTimeSteps.add(
                      ReasoningStep(
                        id: 'step_4',
                        description: '验证代码正确性',
                        agent: AgentType.code,
                        status: StepStatus.completed,
                        createdAt: DateTime.now(),
                        completedAt: DateTime.now().add(const Duration(milliseconds: 500)),
                      ),
                    );
                  }
                });
              },
              icon: const Icon(Icons.play_arrow),
              label: Text(_showRealTime ? '重置' : '模拟下一步'),
            ),
          ],
        ),
      ],
    );

  Widget _buildCompletedDemo() => AgentReasoningBubble(
      steps: _completedSteps,
      totalDurationMs: 7000,
    );

  Widget _buildCollaborationDemo() => MultiAgentCollaborationBubble(
      contributions: _collaborationContributions,
      summary: '综合三位专家的分析，推荐使用幂函数直接计算导数，时间复杂度O(1)，代码简洁高效。',
      isComplete: true,
    );

  Widget _buildPersistedMessageDemo() {
    final message = ChatMessageModel(
      id: 'demo_msg_1',
      conversationId: 'demo_conv',
      role: MessageRole.assistant,
      content: '根据您的要求，我已经完成了微积分公式的Python实现。\n\n**导数公式**: d/dx(x²) = 2x\n\n**Python代码**:\n```python\ndef power_derivative(x, n=2):\n    return n * x**(n-1)\n```\n\n这个实现使用了幂函数的导数规则，效率为O(1)。',
      createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
      reasoningSteps: _completedSteps,
      reasoningSummary: '完成于 7.0s，4个步骤',
      isReasoningComplete: true,
      aiStatus: 'EXECUTING_TOOL',
    );

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '模拟消息结构:',
            style: TextStyle(color: Colors.white70, fontSize: 12),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.grey.shade900,
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              message.toJson().toString(),
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 10,
                color: Colors.greenAccent,
                height: 1.4,
              ),
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            '在ChatBubble中显示效果:',
            style: TextStyle(color: Colors.white70, fontSize: 12),
          ),
          const SizedBox(height: 8),
          // Simulate ChatBubble rendering
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey.shade800,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade600),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (message.aiStatus != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.amber.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '🔧 ${message.aiStatus}',
                      style: const TextStyle(color: Colors.amber, fontSize: 11),
                    ),
                  ),
                if (message.reasoningSteps != null) ...[
                  const SizedBox(height: 8),
                  AgentReasoningBubble(
                    steps: message.reasoningSteps!,
                    totalDurationMs: 7000,
                  ),
                ],
                const SizedBox(height: 8),
                Text(
                  message.content,
                  style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.5),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
