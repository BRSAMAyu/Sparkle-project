import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_unlock_dialog.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

enum MirofishMilestoneKind {
  firstSimulation,
  firstTheater,
  firstReport,
}

class MirofishMilestoneService {
  MirofishMilestoneService._();

  static const _storageVersion = 'v1';

  static Future<bool> celebrateIfFirstTime(
    BuildContext context,
    WidgetRef ref, {
    required MirofishMilestoneKind kind,
    VoidCallback? onShare,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'mirofish_milestone_$_storageVersion:${kind.name}';
    final alreadyUnlocked = prefs.getBool(key) ?? false;
    if (alreadyUnlocked) {
      return false;
    }

    await prefs.setBool(key, true);
    if (!context.mounted) {
      return true;
    }
    if (AppLocalizations.of(context) == null) {
      return true;
    }

    final event = _buildEvent(kind);
    unawaited(
      ref.read(appEventStreamServiceProvider).recordEntityExecution(
            entityType: 'mirofish_milestone',
            entityId: event.achievementId,
            actionType: 'unlock',
            source: 'mirofish_phase5',
            payload: <String, dynamic>{
              'milestone_kind': kind.name,
            },
          ),
    );

    await AchievementUnlockDialog.show(
      context,
      event,
      onShare: onShare,
    );
    return true;
  }

  static AchievementUnlockEvent _buildEvent(MirofishMilestoneKind kind) {
    final now = DateTime.now();
    switch (kind) {
      case MirofishMilestoneKind.firstSimulation:
        return AchievementUnlockEvent(
          achievementId: 'mirofish_first_simulation',
          name: '仿真开场',
          rarity: AchievementRarity.rare,
          unlockedAt: now,
          visualEffectType: VisualEffectType.gravityWave,
          rewardPreview: const <String>[
            '解锁仿真高光样式',
            '后续可继续沉淀为报告或推演',
          ],
          surfacePreview: const <String>[
            '学习场景模拟',
            '互动讨论时间线',
          ],
          gloryLines: const <String>[
            '你第一次把知识点拉进了真实讨论现场。',
          ],
        );
      case MirofishMilestoneKind.firstTheater:
        return AchievementUnlockEvent(
          achievementId: 'mirofish_first_theater',
          name: '路径预演者',
          rarity: AchievementRarity.epic,
          unlockedAt: now,
          visualEffectType: VisualEffectType.supernova,
          rewardPreview: const <String>[
            '解锁剧场时间轴视角',
            '支持路径采纳与回填校准',
          ],
          surfacePreview: const <String>[
            '知识推演剧场',
            'What-If 分支对比',
          ],
          gloryLines: const <String>[
            '你已经点亮第一张可探索的学习未来地图。',
          ],
        );
      case MirofishMilestoneKind.firstReport:
        return AchievementUnlockEvent(
          achievementId: 'mirofish_first_report',
          name: '洞察归档员',
          rarity: AchievementRarity.rare,
          unlockedAt: now,
          visualEffectType: VisualEffectType.nebulaTransform,
          rewardPreview: const <String>[
            '解锁诊断仪表盘视角',
            '可直接把发现转成行动入口',
          ],
          surfacePreview: const <String>[
            '学习分析报告',
            '趋势对比与行动建议',
          ],
          gloryLines: const <String>[
            '你已经拥有第一份可回看的学习洞察档案。',
          ],
        );
    }
  }
}
