import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/widgets/onboarding/architecture_animation.dart';

/// 交互式引导流程 - Week 7
///
/// 新用户首次使用时的引导体验
/// 包含：
/// 1. 欢迎页
/// 2. 架构可视化动画
/// 3. 核心功能介绍（Galaxy、Chat、Tasks）
/// 4. 权限请求
/// 5. 个性化设置
class InteractiveOnboardingScreen extends StatefulWidget {

  const InteractiveOnboardingScreen({
    required this.onComplete,
    super.key,
  });
  final VoidCallback onComplete;

  @override
  State<InteractiveOnboardingScreen> createState() =>
      _InteractiveOnboardingScreenState();
}

class _InteractiveOnboardingScreenState
    extends State<InteractiveOnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  final int _totalPages = 6;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _nextPage() {
    if (_currentPage < _totalPages - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      widget.onComplete();
    }
  }

  void _skipAll() {
    widget.onComplete();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      backgroundColor: DS.deepSpaceStart,
      body: SafeArea(
        child: Column(
          children: [
            // Skip button
            if (_currentPage < _totalPages - 1)
              Align(
                alignment: Alignment.topRight,
                child: TextButton(
                  onPressed: _skipAll,
                  child: Text(
                    '跳过',
                    style: TextStyle(color: DS.brandPrimary70),
                  ),
                ),
              ),

            // PageView
            Expanded(
              child: PageView(
                controller: _pageController,
                onPageChanged: (index) {
                  setState(() => _currentPage = index);
                  HapticFeedback.lightImpact();
                },
                children: [
                  _buildWelcomePage(),
                  _buildArchitecturePage(),
                  _buildGalaxyFeaturePage(),
                  _buildChatFeaturePage(),
                  _buildTaskFeaturePage(),
                  _buildPersonalizationPage(),
                ],
              ),
            ),

            // Page indicator
            Padding(
              padding: const EdgeInsets.all(DS.lg),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Page dots
                  Row(
                    children: List.generate(_totalPages, (index) => Container(
                        width: index == _currentPage ? 24 : 8,
                        height: 8,
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        decoration: BoxDecoration(
                          color: index == _currentPage
                              ? DS.brandPrimary
                              : DS.brandPrimary.withValues(alpha: 0.3),
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),),
                  ),

                  // Next/Done button
                  ElevatedButton(
                    onPressed: _nextPage,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: DS.brandPrimary.shade600,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 32,
                        vertical: 16,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: Text(
                      _currentPage == _totalPages - 1 ? '开始使用' : '下一步',
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );

  // Page 1: Welcome
  Widget _buildWelcomePage() => Padding(
      padding: const EdgeInsets.all(DS.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Logo animation
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: 1),
            duration: const Duration(seconds: 1),
            curve: Curves.elasticOut,
            builder: (context, value, child) => Transform.scale(
                scale: value,
                child: Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: [
                        DS.brandPrimary.shade400,
                        Colors.purple.shade400,
                      ],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: DS.brandPrimary.withValues(alpha: 0.5),
                        blurRadius: 40,
                        spreadRadius: 10,
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.auto_awesome,
                    size: 60,
                    color: DS.brandPrimaryConst,
                  ),
                ),
              ),
          ),
          const SizedBox(height: DS.xxxl),

          // Title
          Text(
            '欢迎来到 Sparkle',
            style: TextStyle(
              color: DS.brandPrimaryConst,
              fontSize: 32,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: DS.lg),

          // Subtitle
          Text(
            '你的 AI 学习助手\n让知识点亮智慧之光',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: DS.brandPrimary.withValues(alpha: 0.8),
              fontSize: 18,
            ),
          ),
          const SizedBox(height: DS.xxxl),

          // Features preview
          _buildFeaturePreview(
              Icons.auto_graph, '知识星图', '可视化学习网络',),
          const SizedBox(height: DS.lg),
          _buildFeaturePreview(
              Icons.psychology, 'AI 对话', '智能学习伙伴',),
          const SizedBox(height: DS.lg),
          _buildFeaturePreview(
              Icons.task_alt, '智能任务', '个性化学习计划',),
        ],
      ),
    );

  Widget _buildFeaturePreview(IconData icon, String title, String description) => Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(DS.md),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: DS.brandPrimaryConst, size: 24),
          ),
          const SizedBox(width: DS.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  description,
                  style: TextStyle(
                    color: DS.brandPrimary.withValues(alpha: 0.7),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );

  // Page 2: Architecture Animation
  Widget _buildArchitecturePage() => Padding(
      padding: const EdgeInsets.all(DS.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '系统架构',
            style: TextStyle(
              color: DS.brandPrimaryConst,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: DS.lg),
          Text(
            '了解 Sparkle 如何工作',
            style: TextStyle(
              color: DS.brandPrimary.withValues(alpha: 0.8),
              fontSize: 16,
            ),
          ),
          const SizedBox(height: DS.xxl),

          // Architecture Animation
          const ArchitectureAnimation(),
        ],
      ),
    );

  // Page 3: Galaxy Feature
  Widget _buildGalaxyFeaturePage() => _buildFeaturePage(
      icon: Icons.auto_graph,
      iconGradient: [DS.brandPrimary.shade400, Colors.cyan.shade400],
      title: '知识星图',
      description: '将你的知识可视化为一张星图',
      features: [
        '6大知识星域：理性、造物、灵感、文明、生活、精神',
        '实时衰减预测：了解知识遗忘曲线',
        '交互式时间机器：预测未来学习状态',
        '智能推荐：基于知识图谱的学习路径',
      ],
      demoWidget: _buildGalaxyDemo(),
    );

  // Page 4: Chat Feature
  Widget _buildChatFeaturePage() => _buildFeaturePage(
      icon: Icons.psychology,
      iconGradient: [Colors.purple.shade400, Colors.pink.shade400],
      title: 'AI 对话',
      description: '你的智能学习伙伴',
      features: [
        '多智能体协作：数学、代码、写作、科学专家',
        'GraphRAG 检索：实时显示知识检索过程',
        '上下文理解：记住你的学习历史',
        '工具调用：执行任务、查询知识、管理计划',
      ],
      demoWidget: _buildChatDemo(),
    );

  // Page 5: Task Feature
  Widget _buildTaskFeaturePage() => _buildFeaturePage(
      icon: Icons.task_alt,
      iconGradient: [DS.success.shade400, Colors.teal.shade400],
      title: '智能任务',
      description: '个性化学习计划',
      features: [
        '6种任务类型：学习、训练、纠错、反思、社交、规划',
        '智能推送：基于学习状态的提醒',
        'Sprint 计划：短期冲刺目标',
        'Growth Plan：长期成长规划',
      ],
      demoWidget: _buildTaskDemo(),
    );

  // Page 6: Personalization
  Widget _buildPersonalizationPage() => Padding(
      padding: const EdgeInsets.all(DS.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.settings_suggest,
            size: 80,
            color: DS.brandPrimaryConst,
          ),
          const SizedBox(height: DS.xxl),

          Text(
            '个性化设置',
            style: TextStyle(
              color: DS.brandPrimaryConst,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: DS.lg),
          Text(
            '让 Sparkle 更懂你',
            style: TextStyle(
              color: DS.brandPrimary.withValues(alpha: 0.8),
              fontSize: 16,
            ),
          ),
          const SizedBox(height: DS.xxxl),

          // Settings options
          _buildSettingOption(
            icon: Icons.notifications_active,
            title: '学习提醒',
            description: '在最佳时间推送学习建议',
            value: true,
          ),
          const SizedBox(height: DS.lg),
          _buildSettingOption(
            icon: Icons.analytics,
            title: '学习分析',
            description: '生成个性化学习报告',
            value: true,
          ),
          const SizedBox(height: DS.lg),
          _buildSettingOption(
            icon: Icons.auto_awesome,
            title: 'AI 助手',
            description: '自动创建学习任务',
            value: true,
          ),
        ],
      ),
    );

  Widget _buildFeaturePage({
    required IconData icon,
    required List<Color> iconGradient,
    required String title,
    required String description,
    required List<String> features,
    required Widget demoWidget,
  }) => SingleChildScrollView(
      padding: const EdgeInsets.all(DS.xxl),
      child: Column(
        children: [
          // Icon
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: iconGradient),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Icon(icon, size: 48, color: DS.brandPrimary),
          ),
          const SizedBox(height: DS.xl),

          // Title
          Text(
            title,
            style: TextStyle(
              color: DS.brandPrimaryConst,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: DS.md),

          // Description
          Text(
            description,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: DS.brandPrimary.withValues(alpha: 0.8),
              fontSize: 16,
            ),
          ),
          const SizedBox(height: DS.xxl),

          // Demo widget
          demoWidget,
          const SizedBox(height: DS.xxl),

          // Features list
          ...features.map((feature) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.check_circle,
                      color: iconGradient[0],
                      size: 24,
                    ),
                    const SizedBox(width: DS.md),
                    Expanded(
                      child: Text(
                        feature,
                        style: TextStyle(
                          color: DS.brandPrimaryConst,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ],
                ),
              ),),
        ],
      ),
    );

  Widget _buildSettingOption({
    required IconData icon,
    required String title,
    required String description,
    required bool value,
  }) => Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(icon, color: DS.brandPrimary.shade400, size: 32),
          const SizedBox(width: DS.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  description,
                  style: TextStyle(
                    color: DS.brandPrimary.withValues(alpha: 0.7),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: (v) {},
            activeThumbColor: DS.brandPrimary.shade400,
          ),
        ],
      ),
    );

  // Demo widgets
  Widget _buildGalaxyDemo() => Container(
      height: 200,
      decoration: BoxDecoration(
        gradient: RadialGradient(
          colors: [
            DS.brandPrimary.withValues(alpha: 0.3),
            Colors.transparent,
          ],
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Center(
        child: Icon(
          Icons.auto_graph,
          size: 80,
          color: DS.brandPrimary.shade400,
        ),
      ),
    );

  Widget _buildChatDemo() => Container(
      height: 200,
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildChatMessage('你好！我能帮你什么？', true),
          const SizedBox(height: DS.sm),
          _buildChatMessage('解释一下微积分的基本原理', false),
          const SizedBox(height: DS.sm),
          _buildChatMessage('微积分研究函数的变化率...', true),
        ],
      ),
    );

  Widget _buildChatMessage(String text, bool isAI) => Align(
      alignment: isAI ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: isAI
              ? Colors.purple.withValues(alpha: 0.2)
              : DS.brandPrimary.withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          text,
          style: TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
        ),
      ),
    );

  Widget _buildTaskDemo() => Container(
      height: 200,
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          _buildTaskItem('学习任务', '完成微积分第一章', DS.brandPrimary),
          const SizedBox(height: DS.sm),
          _buildTaskItem('训练任务', '完成10道练习题', DS.success),
          const SizedBox(height: DS.sm),
          _buildTaskItem('反思任务', '总结本周学习收获', Colors.purple),
        ],
      ),
    );

  Widget _buildTaskItem(String type, String title, Color color) => Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(Icons.circle, size: 12, color: color),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  type,
                  style: TextStyle(
                    color: color,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  title,
                  style: TextStyle(color: DS.brandPrimaryConst, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
}
