import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 成就分享卡片生成器 - Week 7
///
/// 生成精美的成就分享卡片（PNG格式）
/// 用于社交分享、保存到相册等
///
/// 成就类型：
/// - learning_milestone: 学习里程碑（完成100个知识点）
/// - streak_record: 连续学习记录（连续30天）
/// - mastery_achievement: 精通成就（某领域达到90%掌握度）
/// - task_completion: 任务完成（完成所有Sprint任务）
class AchievementCardGenerator {
  /// 生成成就卡片并返回图片数据
  static Future<Uint8List?> generateCard({
    required String achievementType,
    required Map<String, dynamic> data,
  }) async {
    // Create the widget to be converted
    final cardWidget = _buildAchievementCard(achievementType, data);

    // Convert widget to image
    return _widgetToImage(cardWidget);
  }

  /// 将 Widget 转换为图片
  static Future<Uint8List?> _widgetToImage(Widget widget) async {
    final repaintBoundary = RenderRepaintBoundary();

    // Create pipeline owner
    final pipelineOwner = PipelineOwner();
    final buildOwner = BuildOwner(focusManager: FocusManager());

    // Create render object
    final renderView = RenderView(
      view: WidgetsBinding.instance.platformDispatcher.views.first,
      child: RenderPositionedBox(
        child: repaintBoundary,
      ),
      configuration: const ViewConfiguration(), // Use default configuration
    );

    // Prepare the pipeline
    pipelineOwner.rootNode = renderView;
    renderView.prepareInitialFrame();

    // Build the widget tree
    final rootElement = RenderObjectToWidgetAdapter<RenderBox>(
      container: repaintBoundary,
      child: Directionality(
        textDirection: TextDirection.ltr,
        child: widget,
      ),
    ).attachToRenderTree(buildOwner);

    // Layout and paint
    buildOwner.buildScope(rootElement);
    buildOwner.finalizeTree();

    pipelineOwner.flushLayout();
    pipelineOwner.flushCompositingBits();
    pipelineOwner.flushPaint();

    // Convert to image
    final image = await repaintBoundary.toImage(pixelRatio: 3.0);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);

    return byteData?.buffer.asUint8List();
  }

  /// 构建成就卡片 Widget
  static Widget _buildAchievementCard(
      String achievementType, Map<String, dynamic> data,) {
    switch (achievementType) {
      case 'learning_milestone':
        return _LearningMilestoneCard(data: data);
      case 'streak_record':
        return _StreakRecordCard(data: data);
      case 'mastery_achievement':
        return _MasteryAchievementCard(data: data);
      case 'task_completion':
        return _TaskCompletionCard(data: data);
      default:
        return _GenericAchievementCard(data: data);
    }
  }
}

/// 学习里程碑卡片
class _LearningMilestoneCard extends StatelessWidget {

  const _LearningMilestoneCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final nodeCount = data['node_count'] ?? 100;
    final username = data['username'] ?? 'Sparkle User';
    final date = data['date'] ?? DateTime.now().toString().split(' ')[0];

    return Container(
      width: 800,
      height: 1200,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppDesignTokens.deepSpaceStart,
            AppDesignTokens.deepSpaceEnd,
            AppDesignTokens.secondaryDark,
          ],
        ),
      ),
      child: Stack(
        children: [
          // Background stars
          ..._buildStars(),

          // Content
          Padding(
            padding: const EdgeInsets.all(60),
            child: Column(
              children: [
                const Spacer(),

                // Icon
                Container(
                  width: 200,
                  height: 200,
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
                        blurRadius: 60,
                        spreadRadius: 20,
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.auto_awesome,
                    size: 100,
                    color: DS.brandPrimaryConst,
                  ),
                ),
                const SizedBox(height: 60),

                // Achievement title
                const Text(
                  '学习里程碑',
                  style: TextStyle(
                    color: DS.brandPrimaryConst,
                    fontSize: 48,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 30),

                // Main achievement
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 40,
                    vertical: 20,
                  ),
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: DS.brandPrimary.withValues(alpha: 0.3),
                      width: 2,
                    ),
                  ),
                  child: Text(
                    '$nodeCount 个知识点',
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: 72,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(height: 40),

                // Description
                Text(
                  '恭喜你已掌握 $nodeCount 个知识点\n知识之光照亮前行之路',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: DS.brandPrimary.withValues(alpha: 0.9),
                    fontSize: 28,
                    height: 1.5,
                  ),
                ),

                const Spacer(),

                // User info
                Container(
                  padding: const EdgeInsets.all(30),
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    children: [
                      Text(
                        username,
                        style: TextStyle(
                          color: DS.brandPrimaryConst,
                          fontSize: 36,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        date,
                        style: TextStyle(
                          color: DS.brandPrimary.withValues(alpha: 0.7),
                          fontSize: 24,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 40),

                // Sparkle logo
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.auto_awesome,
                      color: DS.brandPrimaryConst,
                      size: 32,
                    ),
                    const SizedBox(width: DS.md),
                    Text(
                      'Sparkle',
                      style: TextStyle(
                        color: DS.brandPrimary.withValues(alpha: 0.8),
                        fontSize: 32,
                        fontWeight: FontWeight.w300,
                        letterSpacing: 3,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildStars() {
    final random = [0.1, 0.3, 0.5, 0.7, 0.9];
    return List.generate(30, (index) => Positioned(
        left: (index * 73 % 800).toDouble(),
        top: (index * 97 % 1200).toDouble(),
        child: Container(
          width: 4,
          height: 4,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: DS.brandPrimary.withValues(alpha: random[index % 5]),
          ),
        ),
      ),);
  }
}

/// 连续学习记录卡片
class _StreakRecordCard extends StatelessWidget {

  const _StreakRecordCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final streakDays = data['streak_days'] ?? 30;
    final username = data['username'] ?? 'Sparkle User';

    return Container(
      width: 800,
      height: 1200,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.brandPrimary.shade900,
            DS.error.shade900,
          ],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(60),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Fire icon
            Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: DS.brandPrimary.shade400,
                boxShadow: [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.6),
                    blurRadius: 60,
                    spreadRadius: 20,
                  ),
                ],
              ),
              child: Icon(
                Icons.local_fire_department,
                size: 120,
                color: DS.brandPrimaryConst,
              ),
            ),
            const SizedBox(height: 60),

            const Text(
              '连续学习记录',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 48,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 40),

            Text(
              '$streakDays 天',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 120,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 40),

            Text(
              '$username 已连续学习 $streakDays 天\n坚持的力量无可阻挡！',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 28,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 精通成就卡片
class _MasteryAchievementCard extends StatelessWidget {

  const _MasteryAchievementCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final domain = data['domain'] ?? '数学';
    final masteryPercent = data['mastery_percent'] ?? 90;
    final username = data['username'] ?? 'Sparkle User';

    return Container(
      width: 800,
      height: 1200,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.success.shade900,
            Colors.teal.shade900,
          ],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(60),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Trophy icon
            Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.amber.shade400,
                boxShadow: [
                  BoxShadow(
                    color: Colors.amber.withValues(alpha: 0.6),
                    blurRadius: 60,
                    spreadRadius: 20,
                  ),
                ],
              ),
              child: Icon(
                Icons.emoji_events,
                size: 120,
                color: DS.brandPrimaryConst,
              ),
            ),
            const SizedBox(height: 60),

            const Text(
              '领域精通',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 48,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 40),

            Text(
              domain,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 72,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),

            Text(
              '$masteryPercent% 掌握度',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 48,
              ),
            ),
            const SizedBox(height: 40),

            Text(
              '$username 在 $domain 领域已达到精通水平\n继续保持！',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 28,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 任务完成卡片
class _TaskCompletionCard extends StatelessWidget {

  const _TaskCompletionCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final taskCount = data['task_count'] ?? 20;
    final sprintName = data['sprint_name'] ?? 'Sprint #1';

    return Container(
      width: 800,
      height: 1200,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.indigo.shade900,
            DS.brandPrimary.shade900,
          ],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(60),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.check_circle,
              size: 200,
              color: DS.brandPrimaryConst,
            ),
            const SizedBox(height: 60),

            const Text(
              '任务完成',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 48,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 40),

            Text(
              sprintName,
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 56,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),

            Text(
              '完成 $taskCount 个任务',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 40,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 通用成就卡片
class _GenericAchievementCard extends StatelessWidget {

  const _GenericAchievementCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) => Container(
      width: 800,
      height: 1200,
      color: DS.brandPrimary.shade900,
      child: Center(
        child: Text(
          'Achievement',
          style: TextStyle(color: DS.brandPrimaryConst, fontSize: 48),
        ),
      ),
    );
}
