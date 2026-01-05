import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 成就卡片生成器 - 生成用于分享的精美卡片
class AchievementCardGenerator extends StatelessWidget {
  const AchievementCardGenerator({
    required this.type,
    required this.data,
    super.key,
  });
  final String type;
  final Map<String, dynamic> data;

  static Future<Uint8List?> generateCard({
    required String achievementType,
    required Map<String, dynamic> data,
  }) async {
    // TODO: Implement actual image generation logic
    // This typically requires wrapping the widget in a RepaintBoundary, 
    // rendering it to an image, and converting to byte data.
    // For now, returning null to allow compilation.
    return null;
  }

  @override
  Widget build(BuildContext context) {
    switch (type) {
      case 'milestone':
        return _MilestoneCard(data: data);
      case 'streak':
        return _StreakRecordCard(data: data);
      case 'mastery':
        return _MasteryAchievementCard(data: data);
      case 'task_complete':
        return _TaskCompletionCard(data: data);
      default:
        return _MilestoneCard(data: data);
    }
  }
}

/// 学习里程碑卡片
class _MilestoneCard extends StatelessWidget {
  const _MilestoneCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final nodeCount = data['node_count'] as int? ?? 0;
    final username = data['username'] as String? ?? 'Sparkle User';
    final date = data['date'] as String? ?? '2024.01.01';

    return Container(
      width: 800,
      height: 1200,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.brandPrimary.shade900,
            DS.brandSecondary.shade900,
          ],
        ),
      ),
      child: Stack(
        children: [
          ..._buildStars(),
          Padding(
            padding: const EdgeInsets.all(60),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(height: 40),
                // Achievement icon
                Container(
                  width: 180,
                  height: 180,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: DS.brandPrimary.withValues(alpha: 0.2),
                    border: Border.all(
                      color: DS.brandPrimaryConst,
                      width: 4,
                    ),
                  ),
                  child: Icon(
                    Icons.auto_awesome,
                    size: 100,
                    color: DS.brandPrimaryConst,
                  ),
                ),
                const SizedBox(height: 60),

                // Achievement title
                Text(
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
    return List.generate(
      30,
      (index) => Positioned(
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
      ),
    );
  }
}

/// 连续学习记录卡片
class _StreakRecordCard extends StatelessWidget {
  const _StreakRecordCard({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final streakDays = data['streak_days'] as int? ?? 30;
    final username = data['username'] as String? ?? 'Sparkle User';

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

            Text(
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
    final domain = data['domain'] as String? ?? '数学';
    final masteryPercent = data['mastery_percent'] as int? ?? 90;
    final username = data['username'] as String? ?? 'Sparkle User';

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

            Text(
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
    final taskCount = data['task_count'] as int? ?? 20;
    final sprintName = data['sprint_name'] as String? ?? 'Sprint #1';
    final username = data['username'] as String? ?? 'Sparkle User';

    return Container(
      width: 800,
      height: 1200,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.brandSecondary.shade900,
            DS.brandPrimary.shade900,
          ],
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(60),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Check icon
            Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: DS.brandSecondary.shade400,
                boxShadow: [
                  BoxShadow(
                    color: DS.brandSecondary.withValues(alpha: 0.6),
                    blurRadius: 60,
                    spreadRadius: 20,
                  ),
                ],
              ),
              child: Icon(
                Icons.check_circle_outline,
                size: 120,
                color: DS.brandPrimaryConst,
              ),
            ),
            const SizedBox(height: 60),

            Text(
              '任务圆满完成',
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
                fontSize: 64,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 20),

            Text(
              '完成 $taskCount 项任务',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 72,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 40),

            Text(
              '$username 在本次冲刺中表现卓越\n效率之星实至名归！',
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