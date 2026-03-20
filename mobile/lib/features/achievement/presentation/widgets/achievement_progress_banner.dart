import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/achievement/presentation/providers/close_to_unlock_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// Close-to-unlock achievement progress banner
/// Displays at the bottom of the screen when an achievement is close to being unlocked
class AchievementProgressBanner extends ConsumerStatefulWidget {
  const AchievementProgressBanner({super.key});

  @override
  ConsumerState<AchievementProgressBanner> createState() =>
      _AchievementProgressBannerState();
}

class _AchievementProgressBannerState
    extends ConsumerState<AchievementProgressBanner>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 1), // Start from bottom
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOut,
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bannerState = ref.watch(closeToUnlockProvider);
    final l10n = context.l10n;
    final bottomPadding = MediaQuery.of(context).padding.bottom;
    final isVisible = bannerState.isVisible && bannerState.item != null;

    if (!isVisible) {
      return Positioned(
        bottom: kBottomNavigationBarHeight + bottomPadding + DS.spacing8,
        left: DS.spacing16,
        right: DS.spacing16,
        child: const SizedBox.shrink(),
      );
    }

    final item = bannerState.item!;
    final achievement = item.achievement;
    final rarity = achievement.rarity;

    // Start slide-in animation
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _controller.status == AnimationStatus.dismissed) {
        unawaited(_controller.forward());
      }
    });

    return Positioned(
      bottom: kBottomNavigationBarHeight + bottomPadding + DS.spacing8,
      left: DS.spacing16,
      right: DS.spacing16,
      child: SlideTransition(
        position: _slideAnimation,
        child: GestureDetector(
          onTap: () {
            // Navigate to achievement details
            unawaited(context.push('/achievements/${achievement.id}'));
            // Dismiss banner after navigation
            ref.read(closeToUnlockProvider.notifier).dismiss();
          },
          child: Material(
            color: DS.surfacePrimaryElevated,
            borderRadius: BorderRadius.circular(DS.spacing12),
            elevation: 4,
            child: Container(
              height: 56,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing8,
              ),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(DS.spacing12),
                border: Border.all(
                  color: DS.borderSubtle,
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  // Left: Achievement icon with rarity color
                  _buildRarityIcon(rarity),

                  const SizedBox(width: DS.spacing12),

                  // Center: Achievement info
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Achievement name
                        Text(
                          achievement.name,
                          style: TextStyle(
                            fontSize: DS.fontSizeBase,
                            fontWeight: DS.fontWeightMedium,
                            color: DS.textPrimary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),

                        const SizedBox(height: 2),

                        // Progress text
                        Text(
                          _getProgressText(item, l10n),
                          style: TextStyle(
                            fontSize: DS.fontSizeXs,
                            color: DS.textSecondary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(width: DS.spacing8),

                  // Right: Arrow icon
                  Icon(
                    Icons.arrow_forward_ios_rounded,
                    size: 14,
                    color: DS.neutral400,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// Build rarity icon
  Widget _buildRarityIcon(AchievementRarity rarity) {
    final color = _getRarityColor(rarity);
    final iconData = _getRarityIcon(rarity);

    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(DS.spacing8),
      ),
      child: Icon(
        iconData,
        color: color,
        size: 20,
      ),
    );
  }

  /// Get progress text based on achievement category and progress
  String _getProgressText(AchievementWithProgress item, AppLocalizations l10n) {
    final achievement = item.achievement;
    final category = achievement.category ?? 'task';
    final current = item.userProgress?.progressValue ?? 0;
    final target = item.userProgress?.progressTarget ?? 1;
    final remaining = target - current;

    // Use dynamic action text based on category
    final actionText = _getActionText(category, remaining, l10n);

    return l10n.achievementNeedMore(actionText);
  }

  /// Get action text based on category
  String _getActionText(String category, int remaining, AppLocalizations l10n) {
    // Map category to action text
    switch (category.toLowerCase()) {
      case 'task':
      case 'tasks':
        return l10n.achievementCompleteTasks(remaining);
      case 'node':
      case 'nodes':
      case 'knowledge':
        return l10n.achievementUnlockNodes(remaining);
      case 'chat':
      case 'chats':
        return l10n.achievementChatCount(remaining);
      case 'streak':
      case 'checkin':
        return l10n.achievementCheckinDays(remaining);
      case 'plan':
      case 'plans':
        return l10n.achievementCreatePlans(remaining);
      default:
        // Generic fallback
        return l10n.achievementProgressGeneric(remaining);
    }
  }

  /// Get rarity color
  Color _getRarityColor(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return DS.neutral400;
      case AchievementRarity.rare:
        return DS.rarityRare;
      case AchievementRarity.epic:
        return DS.rarityEpic;
      case AchievementRarity.legendary:
        return DS.rarityLegendary;
    }
  }

  /// Get rarity icon
  IconData _getRarityIcon(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return Icons.military_tech;
      case AchievementRarity.rare:
        return Icons.stars;
      case AchievementRarity.epic:
        return Icons.auto_awesome;
      case AchievementRarity.legendary:
        return Icons.diamond;
    }
  }
}
