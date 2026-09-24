import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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

    final event = _buildEvent(context, kind);
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

  static AchievementUnlockEvent _buildEvent(BuildContext context, MirofishMilestoneKind kind) {
    final now = DateTime.now();
    switch (kind) {
      case MirofishMilestoneKind.firstSimulation:
        return AchievementUnlockEvent(
          achievementId: 'mirofish_first_simulation',
          name: context.l10n.auto_simulationdebut,
          rarity: AchievementRarity.rare,
          unlockedAt: now,
          visualEffectType: VisualEffectType.gravityWave,
          rewardPreview: <String>[
            context.l10n.auto_unlocksimulationhighlightstyle,
            context.l10n.auto_canbearchivedasreportsorsimula,
          ],
          surfacePreview: <String>[
            context.l10n.auto_learningscenariosimulation,
            context.l10n.auto_interactivediscussiontimeline,
          ],
          gloryLines: <String>[
            context.l10n.auto_youbroughtknowledgeintorealdis,
          ],
        );
      case MirofishMilestoneKind.firstTheater:
        return AchievementUnlockEvent(
          achievementId: 'mirofish_first_theater',
          name: context.l10n.auto_pathrehearser,
          rarity: AchievementRarity.epic,
          unlockedAt: now,
          visualEffectType: VisualEffectType.supernova,
          rewardPreview: <String>[
            context.l10n.auto_unlocktheatertimelineperspecti,
            context.l10n.auto_supportpathadoptionandbackfill,
          ],
          surfacePreview: <String>[
            context.l10n.auto_knowledgedeductiontheater,
            context.l10n.auto_whatifbranchcomparison,
          ],
          gloryLines: <String>[
            context.l10n.auto_youlitupthefirstexplorablemapo,
          ],
        );
      case MirofishMilestoneKind.firstReport:
        return AchievementUnlockEvent(
          achievementId: 'mirofish_first_report',
          name: context.l10n.auto_insightarchiver,
          rarity: AchievementRarity.rare,
          unlockedAt: now,
          visualEffectType: VisualEffectType.nebulaTransform,
          rewardPreview: <String>[
            context.l10n.auto_unlockdiagnosticdashboardpersp,
            context.l10n.auto_canconvertdiscoveriesintoactio,
          ],
          surfacePreview: <String>[
            context.l10n.auto_learninganalysisreport,
            context.l10n.auto_trendcomparisonandactionsugges,
          ],
          gloryLines: <String>[
            context.l10n.auto_younowhavethefirstreviewablele,
          ],
        );
    }
  }
}
