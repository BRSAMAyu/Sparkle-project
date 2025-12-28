import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 竞赛演示模式 - Week 8
///
/// 专为软件竞赛设计的自动演示模式
/// 展示 Sparkle 的核心功能和特色
///
/// 演示流程（8分钟）：
/// 1. 开场 - 项目介绍 (1min)
/// 2. 必杀技 A - GraphRAG 可视化 (1.5min)
/// 3. 必杀技 B - 时间机器 (1.5min)
/// 4. 必杀技 C - 多智能体协作 (1.5min)
/// 5. 性能优化展示 (1min)
/// 6. 预测分析展示 (1min)
/// 7. 总结与展望 (0.5min)
class CompetitionDemoScreen extends StatefulWidget {
  const CompetitionDemoScreen({super.key});

  @override
  State<CompetitionDemoScreen> createState() => _CompetitionDemoScreenState();
}

class _CompetitionDemoScreenState extends State<CompetitionDemoScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  Timer? _autoPlayTimer;

  int _currentStep = 0;
  final int _totalSteps = 7;
  bool _isAutoPlaying = false;

  final List<_DemoStep> _steps = [
    _DemoStep(
      title: '项目介绍',
      subtitle: 'Sparkle - AI 时间导师',
      duration: const Duration(seconds: 60),
      icon: Icons.auto_awesome,
      gradient: [DS.brandPrimary.shade600, Colors.purple.shade600],
    ),
    _DemoStep(
      title: '必杀技 A',
      subtitle: 'GraphRAG 可视化',
      duration: const Duration(seconds: 90),
      icon: Icons.auto_graph,
      gradient: [Colors.cyan.shade600, DS.brandPrimary.shade600],
    ),
    _DemoStep(
      title: '必杀技 B',
      subtitle: '交互式时间机器',
      duration: const Duration(seconds: 90),
      icon: Icons.access_time,
      gradient: [DS.brandPrimary.shade600, DS.error.shade600],
    ),
    _DemoStep(
      title: '必杀技 C',
      subtitle: '多智能体协作',
      duration: const Duration(seconds: 90),
      icon: Icons.psychology,
      gradient: [Colors.purple.shade600, Colors.pink.shade600],
    ),
    _DemoStep(
      title: '性能优化',
      subtitle: 'Redis 缓存 + 连接池',
      duration: const Duration(seconds: 60),
      icon: Icons.speed,
      gradient: [DS.success.shade600, Colors.teal.shade600],
    ),
    _DemoStep(
      title: '预测分析',
      subtitle: 'AI 驱动的学习洞察',
      duration: const Duration(seconds: 60),
      icon: Icons.analytics,
      gradient: [Colors.indigo.shade600, DS.brandPrimary.shade600],
    ),
    _DemoStep(
      title: '总结展望',
      subtitle: '未来发展方向',
      duration: const Duration(seconds: 30),
      icon: Icons.rocket_launch,
      gradient: [Colors.amber.shade600, DS.brandPrimary.shade600],
    ),
  ];

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    _autoPlayTimer?.cancel();
    super.dispose();
  }

  void _startAutoPlay() {
    setState(() => _isAutoPlaying = true);
    _playStep(_currentStep);
  }

  void _stopAutoPlay() {
    _autoPlayTimer?.cancel();
    setState(() => _isAutoPlaying = false);
  }

  void _playStep(int index) {
    if (index >= _totalSteps) {
      _stopAutoPlay();
      return;
    }

    setState(() => _currentStep = index);
    _animationController.forward(from: 0);
    HapticFeedback.mediumImpact();

    final duration = _steps[index].duration;
    _autoPlayTimer = Timer(duration, () {
      _playStep(index + 1);
    });
  }

  void _nextStep() {
    if (_currentStep < _totalSteps - 1) {
      _stopAutoPlay();
      setState(() => _currentStep++);
      _animationController.forward(from: 0);
      HapticFeedback.lightImpact();
    }
  }

  void _previousStep() {
    if (_currentStep > 0) {
      _stopAutoPlay();
      setState(() => _currentStep--);
      _animationController.forward(from: 0);
      HapticFeedback.lightImpact();
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentStep = _steps[_currentStep];

    return Scaffold(
      backgroundColor: AppDesignTokens.deepSpaceStart,
      body: Stack(
        children: [
          // Background gradient
          AnimatedContainer(
            duration: const Duration(milliseconds: 800),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: currentStep.gradient,
              ),
            ),
          ),

          // Main content
          SafeArea(
            child: Column(
              children: [
                // Header with controls
                _buildHeader(),

                // Step content
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 500),
                    child: _buildStepContent(currentStep),
                  ),
                ),

                // Navigation controls
                _buildNavigationControls(),
              ],
            ),
          ),

          // Timer overlay
          if (_isAutoPlaying) _buildTimerOverlay(currentStep),
        ],
      ),
    );
  }

  Widget _buildHeader() => Padding(
      padding: const EdgeInsets.all(DS.lg),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.close, color: DS.brandPrimary),
            onPressed: () => Navigator.of(context).pop(),
          ),
          Expanded(
            child: Column(
              children: [
                const Text(
                  'Sparkle 竞赛演示',
                  style: TextStyle(
                    color: DS.brandPrimary,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  '步骤 ${_currentStep + 1}/$_totalSteps',
                  style: TextStyle(
                    color: DS.brandPrimary.withValues(alpha: 0.8),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: Icon(
              _isAutoPlaying ? Icons.pause : Icons.play_arrow,
              color: DS.brandPrimary,
            ),
            onPressed: _isAutoPlaying ? _stopAutoPlay : _startAutoPlay,
          ),
        ],
      ),
    );

  Widget _buildStepContent(_DemoStep step) => SingleChildScrollView(
      key: ValueKey(_currentStep),
      padding: const EdgeInsets.all(DS.xxl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Icon
          FadeTransition(
            opacity: _animationController,
            child: Container(
              padding: const EdgeInsets.all(DS.xl),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Icon(
                step.icon,
                size: 80,
                color: DS.brandPrimary,
              ),
            ),
          ),
          const SizedBox(height: DS.xxl),

          // Title
          FadeTransition(
            opacity: _animationController,
            child: Text(
              step.title,
              style: const TextStyle(
                color: DS.brandPrimary,
                fontSize: 48,
                fontWeight: FontWeight.bold,
                height: 1.2,
              ),
            ),
          ),
          const SizedBox(height: DS.lg),

          // Subtitle
          FadeTransition(
            opacity: _animationController,
            child: Text(
              step.subtitle,
              style: TextStyle(
                color: DS.brandPrimary.withValues(alpha: 0.9),
                fontSize: 28,
                fontWeight: FontWeight.w300,
              ),
            ),
          ),
          const SizedBox(height: DS.xxxl),

          // Content
          _buildStepDetails(_currentStep),
        ],
      ),
    );

  Widget _buildStepDetails(int index) {
    switch (index) {
      case 0:
        return _buildIntroContent();
      case 1:
        return _buildGraphRAGContent();
      case 2:
        return _buildTimeMachineContent();
      case 3:
        return _buildMultiAgentContent();
      case 4:
        return _buildPerformanceContent();
      case 5:
        return _buildPredictiveContent();
      case 6:
        return _buildConclusionContent();
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildIntroContent() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildBulletPoint('AI 时间导师，帮助大学生高效学习'),
        _buildBulletPoint('混合架构：Go Gateway + Python Agent + Flutter'),
        _buildBulletPoint('核心特性：知识星图、智能对话、任务管理'),
        _buildBulletPoint('三大必杀技 + 性能优化 + 预测分析'),
      ],
    );

  Widget _buildGraphRAGContent() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildBulletPoint('混合检索：向量搜索 + 图谱遍历 + 用户兴趣'),
        _buildBulletPoint('实时可视化：右下角显示检索过程'),
        _buildBulletPoint('颜色编码：蓝色=向量，紫色=图谱，绿色=兴趣'),
        _buildBulletPoint('性能提升：相比纯向量检索提升 40%'),
        const SizedBox(height: DS.xxl),
        _buildDemoBox(
          '演示要点',
          [
            '展示聊天界面',
            '发送查询："解释微积分的基本原理"',
            '观察右下角 GraphRAG 可视化动画',
            '说明三种检索方法的融合',
          ],
        ),
      ],
    );

  Widget _buildTimeMachineContent() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildBulletPoint('基于 Ebbinghaus 遗忘曲线的知识衰减预测'),
        _buildBulletPoint('拖动滑块查看未来 0-90 天的知识状态'),
        _buildBulletPoint('"如果现在复习？" - 模拟干预效果'),
        _buildBulletPoint('颜色变化：绿色→橙色→红色（掌握度下降）'),
        const SizedBox(height: DS.xxl),
        _buildDemoBox(
          '演示要点',
          [
            '打开 Galaxy 界面',
            '拖动时间滑块到"未来 30 天"',
            '观察节点颜色/透明度变化',
            '点击"如果现在复习？"按钮',
            '展示复习后的状态改善',
          ],
        ),
      ],
    );

  Widget _buildMultiAgentContent() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildBulletPoint('4 个专家智能体：数学、代码、写作、科学'),
        _buildBulletPoint('Orchestrator 根据查询路由到最合适的智能体'),
        _buildBulletPoint('可视化推理过程，提高透明度'),
        _buildBulletPoint('支持多智能体协作（例如：代码+数学）'),
        const SizedBox(height: DS.xxl),
        _buildDemoBox(
          '演示要点',
          [
            '发送查询："用 Python 实现快速排序并分析时间复杂度"',
            '展示 Code Expert 的代码实现',
            '展示 Math Expert 的复杂度分析',
            '显示智能体头像和推理过程',
          ],
        ),
      ],
    );

  Widget _buildPerformanceContent() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildBulletPoint('Redis 语义缓存：SHA256 哈希，TTL 管理'),
        _buildBulletPoint('缓存命中率统计，LRU 驱逐策略'),
        _buildBulletPoint('PostgreSQL 连接池优化：pool_size=20, max_overflow=30'),
        _buildBulletPoint('连接健康检查，Prometheus 监控集成'),
        const SizedBox(height: DS.xxl),
        _buildMetricsBox([
          _Metric('缓存命中率', '85%', Icons.trending_up),
          _Metric('平均响应时间', '< 100ms', Icons.speed),
          _Metric('并发连接', '50+', Icons.people),
        ]),
      ],
    );

  Widget _buildPredictiveContent() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildBulletPoint('活跃度预测：基于学习模式预测下次活跃时间'),
        _buildBulletPoint('难度预测：评估主题难度和前置知识'),
        _buildBulletPoint('最佳时间推荐：分析历史数据找出高效时段'),
        _buildBulletPoint('流失风险检测：早期发现学习倦怠'),
        const SizedBox(height: DS.xxl),
        _buildDemoBox(
          '演示要点',
          [
            '打开学习预测洞察屏幕',
            '展示活跃度热力图（GitHub 风格）',
            '显示 AI 预测的最佳学习时间',
            '说明风险评估和干预建议',
          ],
        ),
      ],
    );

  Widget _buildConclusionContent() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          '核心亮点',
          style: TextStyle(
            color: DS.brandPrimary,
            fontSize: 32,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: DS.xl),
        _buildBulletPoint('技术栈：Go + Python + Flutter 混合架构'),
        _buildBulletPoint('创新点：GraphRAG、时间机器、多智能体'),
        _buildBulletPoint('工程化：性能优化、监控、测试'),
        _buildBulletPoint('用户体验：可视化、交互式、智能化'),
        const SizedBox(height: DS.xxxl),
        const Text(
          '未来方向',
          style: TextStyle(
            color: DS.brandPrimary,
            fontSize: 32,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: DS.xl),
        _buildBulletPoint('增强 AI 推理能力（Agent SDK 集成）'),
        _buildBulletPoint('扩展知识领域（6+1 星域全覆盖）'),
        _buildBulletPoint('社交学习功能（组队、PK、排行榜）'),
        _buildBulletPoint('移动端性能优化（离线模式、增量同步）'),
      ],
    );

  Widget _buildBulletPoint(String text) => Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 8),
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: DS.brandPrimary,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: DS.lg),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                color: DS.brandPrimary,
                fontSize: 20,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );

  Widget _buildDemoBox(String title, List<String> points) => Container(
      padding: const EdgeInsets.all(DS.xl),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: DS.brandPrimary,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: DS.lg),
          ...points.map((point) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    const Icon(Icons.arrow_right, color: DS.brandPrimary, size: 20),
                    const SizedBox(width: DS.sm),
                    Expanded(
                      child: Text(
                        point,
                        style: const TextStyle(color: DS.brandPrimary, fontSize: 16),
                      ),
                    ),
                  ],
                ),
              ),),
        ],
      ),
    );

  Widget _buildMetricsBox(List<_Metric> metrics) => Container(
      padding: const EdgeInsets.all(DS.xl),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: metrics.map((m) => Column(
              children: [
                Icon(m.icon, color: DS.brandPrimary, size: 40),
                const SizedBox(height: DS.md),
                Text(
                  m.value,
                  style: const TextStyle(
                    color: DS.brandPrimary,
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: DS.xs),
                Text(
                  m.label,
                  style: TextStyle(
                    color: DS.brandPrimary.withValues(alpha: 0.8),
                    fontSize: 14,
                  ),
                ),
              ],
            ),).toList(),
      ),
    );

  Widget _buildNavigationControls() => Padding(
      padding: const EdgeInsets.all(DS.xl),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Previous button
          ElevatedButton.icon(
            onPressed: _currentStep > 0 ? _previousStep : null,
            icon: const Icon(Icons.arrow_back),
            label: const Text('上一步'),
            style: ElevatedButton.styleFrom(
              backgroundColor: DS.brandPrimary.withValues(alpha: 0.2),
              foregroundColor: DS.brandPrimary,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            ),
          ),

          // Progress indicator
          Row(
            children: List.generate(_totalSteps, (index) => Container(
                width: index == _currentStep ? 32 : 10,
                height: 10,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  color: index <= _currentStep
                      ? DS.brandPrimary
                      : DS.brandPrimary.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(5),
                ),
              ),),
          ),

          // Next button
          ElevatedButton.icon(
            onPressed: _currentStep < _totalSteps - 1 ? _nextStep : null,
            icon: const Icon(Icons.arrow_forward),
            label: const Text('下一步'),
            style: ElevatedButton.styleFrom(
              backgroundColor: DS.brandPrimary.withValues(alpha: 0.2),
              foregroundColor: DS.brandPrimary,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            ),
          ),
        ],
      ),
    );

  Widget _buildTimerOverlay(_DemoStep step) => Positioned(
      top: 80,
      right: 20,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.timer, color: DS.brandPrimary, size: 16),
            const SizedBox(width: DS.sm),
            Text(
              '${step.duration.inSeconds}s',
              style: const TextStyle(color: DS.brandPrimary, fontSize: 14),
            ),
          ],
        ),
      ),
    );
}

class _DemoStep {

  _DemoStep({
    required this.title,
    required this.subtitle,
    required this.duration,
    required this.icon,
    required this.gradient,
  });
  final String title;
  final String subtitle;
  final Duration duration;
  final IconData icon;
  final List<Color> gradient;
}

class _Metric {

  _Metric(this.label, this.value, this.icon);
  final String label;
  final String value;
  final IconData icon;
}
