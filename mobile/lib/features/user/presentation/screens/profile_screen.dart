import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/widgets/achievement_summary_card.dart';
import 'package:sparkle/features/user/presentation/widgets/active_skills_card.dart';
import 'package:sparkle/features/user/presentation/widgets/engagement_state_badge.dart';
import 'package:sparkle/features/user/presentation/widgets/foresight_card.dart';
import 'package:sparkle/features/user/presentation/widgets/metacognition_panel_card.dart';
import 'package:sparkle/features/user/presentation/widgets/srl_phase_badge_card.dart';
import 'package:sparkle/features/user/presentation/widgets/statistics_card.dart';
import 'package:sparkle/features/user/presentation/widgets/traits_coldstart_questionnaire.dart';
import 'package:sparkle/features/user/presentation/widgets/traits_prior_card.dart';
import 'package:sparkle/features/user/presentation/widgets/working_memory_card.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/visual_elements/visual_elements_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final achievementState = ref.watch(achievementProvider);
    final visualState = ref.watch(visualElementProvider);
    final profileContextAsync = ref.watch(profileContextProvider);
    final profileContext = profileContextAsync.valueOrNull;
    final userState = profileContext == null
        ? UserStateV1Model()
        : UserStateV1Model.fromProfileContext(profileContext);
    final l10n = AppLocalizations.of(context)!;
    final screenHeight = MediaQuery.of(context).size.height;
    final headerHeight = screenHeight < 720 ? 164.0 : 198.0;

    if (user == null) return const SizedBox.shrink();

    return GraphiteScaffold(
      role: SparklePageRole.settings,
      safeArea: false,
      child: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            _buildHeader(context, user, headerHeight: headerHeight),
            ContentConstraint(
              child: Column(
                children: [
                  const StatisticsCard(),
                  const SizedBox(height: DS.spacing12),
                  profileContextAsync.when(
                    data: (profileContext) =>
                        _buildTraitsSection(context, ref, profileContext),
                    loading: () => const SizedBox.shrink(),
                    error: (_, __) => const SizedBox.shrink(),
                  ),
                  const SizedBox(height: DS.spacing12),
                  if (profileContext != null)
                    _buildMetacognitionSection(
                      context,
                      ref,
                      profileContext,
                      userState,
                    ),
                  if (profileContext != null)
                    const SizedBox(height: DS.spacing12),
                  if (profileContext != null &&
                      AppFeatureFlags.enableStage35ProfileCards)
                    _buildStage35Section(userState),
                  if (profileContext != null &&
                      AppFeatureFlags.enableStage35ProfileCards)
                    const SizedBox(height: DS.spacing12),
                  _buildPrestigeShowcase(
                    context,
                    achievementState,
                    visualState,
                  ),
                  const SizedBox(height: DS.spacing16),
                  _buildSettingsSection(
                    context,
                    ref,
                    l10n,
                    user,
                    profileContext,
                  ),
                  const SizedBox(height: 56),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPrestigeShowcase(
    BuildContext context,
    AchievementState achievementState,
    VisualElementState visualState,
  ) {
    final unlockedAchievements =
        achievementState.achievements.where((item) => item.isUnlocked).toList()
          ..sort((a, b) {
            final rarityCompare = b.achievement.rarity.index.compareTo(
              a.achievement.rarity.index,
            );
            if (rarityCompare != 0) return rarityCompare;
            final aTime = a.userProgress?.unlockedAt;
            final bTime = b.userProgress?.unlockedAt;
            if (aTime == null || bTime == null) return 0;
            return bTime.compareTo(aTime);
          });

    final featured = unlockedAchievements.take(3).toList();
    final equippedTitle =
        achievementState.titles.where((title) => title.isEquipped).firstOrNull;
    final equippedBackground = visualState.config?.equippedBackground;
    final equippedEffect = visualState.config?.equippedEffect;
    final equippedParticle = visualState.config?.equippedParticle;
    final prestigeColor = equippedBackground != null
        ? _colorFromElement(equippedBackground)
        : DS.brandPrimary;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color.alphaBlend(
              prestigeColor.withValues(alpha: 0.12),
              DS.surfaceSecondary,
            ),
            DS.surfacePrimaryElevated,
          ],
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: prestigeColor.withValues(alpha: 0.2)),
        boxShadow: [
          BoxShadow(
            color: prestigeColor.withValues(alpha: 0.08),
            blurRadius: 22,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.workspace_premium_rounded, color: prestigeColor),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.profilePrestigeIdentity,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightBold,
                          color: DS.textPrimary,
                        ) ??
                    TextStyle(
                      fontSize: DS.fontSizeBase,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _buildIdentityChip(
                  label: equippedTitle?.titleDisplay ?? context.l10n.profileNoTitleEquipped,
                color: prestigeColor,
              ),
              if (equippedBackground != null)
                _buildIdentityChip(
                  label: equippedBackground.prestigeLabel ??
                      equippedBackground.name,
                  color: _colorFromElement(equippedBackground),
                ),
              if (equippedEffect != null)
                _buildIdentityChip(
                  label: equippedEffect.prestigeLabel ?? equippedEffect.name,
                  color: _colorFromElement(equippedEffect),
                ),
              if (equippedParticle != null)
                _buildIdentityChip(
                  label:
                      equippedParticle.prestigeLabel ?? equippedParticle.name,
                  color: _colorFromElement(equippedParticle),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            context.l10n.profileRecentHighlights,
            style: DS.labelLarge.copyWith(
              fontWeight: DS.fontWeightSemibold,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing10),
          if (featured.isEmpty)
            Text(
              context.l10n.profileNoHighlightsHint,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            )
          else
            ...featured.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: Container(
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: Color.alphaBlend(
                      _rarityColor(
                        item.achievement.rarity,
                      ).withValues(alpha: 0.06),
                      DS.surfacePrimary.withValues(alpha: 0.9),
                    ),
                    borderRadius: DS.borderRadius16,
                    border: Border.all(
                      color: _rarityColor(
                        item.achievement.rarity,
                      ).withValues(alpha: 0.14),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.auto_awesome,
                        size: 16,
                        color: _rarityColor(item.achievement.rarity),
                      ),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          item.achievement.name,
                          style: DS.bodySmall.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightSemibold,
                          ),
                        ),
                      ),
                      Text(
                        _rarityLabel(item.achievement.rarity, context.l10n),
                        style: DS.labelSmall.copyWith(
                          color: _rarityColor(item.achievement.rarity),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildIdentityChip({required String label, required Color color}) =>
      Container(
        constraints: const BoxConstraints(maxWidth: 188),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: DS.borderRadius12,
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: DS.labelSmall.copyWith(
            color: color,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );

  Widget _buildTraitsSection(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> profileContext,
  ) {
    final userInsightState =
        profileContext['user_insight_state'] as Map<String, dynamic>? ??
            const {};
    final coldstartCompletedAt =
        userInsightState['traits_coldstart_completed_at']?.toString();
    final traits = TraitsPriorCard.fromProfileContext(profileContext);
    final srlPhase = SrlPhaseBadgeCard.fromProfileContext(profileContext);

    return Column(
      children: [
        if (srlPhase != null)
          SrlPhaseBadgeCard(
            phase: srlPhase['phase'] ?? 'UNKNOWN',
            helperText: srlPhase['helperText'] ?? '',
          ),
        if (srlPhase != null) const SizedBox(height: DS.spacing12),
        TraitsPriorCard(traits: traits),
        if ((coldstartCompletedAt == null || coldstartCompletedAt.isEmpty) &&
            traits.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: DS.spacing12),
            child: TraitsColdstartQuestionnaire(
              questions: [
                {
                  'id': 'q1',
                  'title': context.l10n.profileTraitQ1Title,
                  'options': [
                    {'id': 'structured', 'label': context.l10n.profileTraitQ1Structured},
                    {'id': 'mixed', 'label': context.l10n.profileTraitQ1Mixed},
                    {'id': 'explore', 'label': context.l10n.profileTraitQ1Explore},
                    {'id': 'skip', 'label': context.l10n.profileTraitSkip},
                  ],
                },
                {
                  'id': 'q2',
                  'title': context.l10n.profileTraitQ2Title,
                  'options': [
                    {'id': 'solo', 'label': context.l10n.profileTraitQ2Solo},
                    {'id': 'small_group', 'label': context.l10n.profileTraitQ2SmallGroup},
                    {'id': 'group', 'label': context.l10n.profileTraitQ2Group},
                    {'id': 'skip', 'label': context.l10n.profileTraitSkip},
                  ],
                },
                {
                  'id': 'q3',
                  'title': context.l10n.profileTraitQ3Title,
                  'options': [
                    {'id': 'replan', 'label': context.l10n.profileTraitQ3Replan},
                    {'id': 'pause', 'label': context.l10n.profileTraitQ3Pause},
                    {'id': 'swing', 'label': context.l10n.profileTraitQ3Swing},
                    {'id': 'skip', 'label': context.l10n.profileTraitSkip},
                  ],
                },
              ],
              onSubmit: (answers) async {
                await ref
                    .read(userRepositoryProvider)
                    .submitTraitsColdstart(answers: answers);
                ref.invalidate(profileContextProvider);
              },
              onSkip: () async {
                await ref
                    .read(userRepositoryProvider)
                    .submitTraitsColdstart(skip: true);
                ref.invalidate(profileContextProvider);
              },
            ),
          ),
      ],
    );
  }

  Widget _buildMetacognitionSection(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> profileContext,
    UserStateV1Model userState,
  ) {
    final panel = MetacognitionPanelCard.fromProfileContext(profileContext);
    if (panel == null) {
      return const SizedBox.shrink();
    }
    final cards = (panel['cards'] as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .toList();
    return MetacognitionPanelCard(
      cards: cards,
      generatedAt: panel['generatedAt']?.toString(),
      profileDimensionCount: userState.metacognitionProfile?.value.items.length,
      onHide: () async {
        await ref
            .read(userRepositoryProvider)
            .updateMetacognitionPanelPreference(hidden: true);
        ref.invalidate(profileContextProvider);
      },
    );
  }

  Widget _buildStage35Section(UserStateV1Model userState) => Column(
        children: [
          WorkingMemoryCard(snapshot: userState.workingMemorySnapshot),
          const SizedBox(height: DS.spacing12),
          AchievementSummaryCard(summary: userState.achievementSummary),
          const SizedBox(height: DS.spacing12),
          ActiveSkillsCard(summary: userState.activeSkillsSummary),
          const SizedBox(height: DS.spacing12),
          EngagementStateBadge(state: userState.engagementState),
          const SizedBox(height: DS.spacing12),
          ForesightCard(hint: userState.foresightHint),
        ],
      );

  Color _colorFromElement(dynamic element) {
    final colors = (element.config['colors'] as List<dynamic>?) ??
        (element.config['gradient'] as List<dynamic>?);
    if (colors != null && colors.isNotEmpty) {
      final value = colors.first.toString().replaceFirst('#', '');
      final hex = value.length == 6 ? 'FF$value' : value;
      final parsed = int.tryParse(hex, radix: 16);
      if (parsed != null) {
        return Color(parsed);
      }
    }
    return DS.brandPrimary;
  }

  Color _rarityColor(dynamic rarity) {
    final key = rarity.toString().split('.').last;
    switch (key) {
      case 'legendary':
        return const Color(0xFFFFA726);
      case 'epic':
        return const Color(0xFFAB47BC);
      case 'rare':
        return const Color(0xFF42A5F5);
      default:
        return const Color(0xFFB0BEC5);
    }
  }

  String _rarityLabel(dynamic rarity, AppLocalizations l10n) {
    final key = rarity.toString().split('.').last;
    switch (key) {
      case 'legendary':
        return l10n.achievementRarityLegendary;
      case 'epic':
        return l10n.achievementRarityEpic;
      case 'rare':
        return l10n.achievementRarityRare;
      default:
        return l10n.achievementRarityCommon;
    }
  }

  Widget _buildHeader(
    BuildContext context,
    UserModel user, {
    required double headerHeight,
  }) {
    final l10n = AppLocalizations.of(context)!;

    return SizedBox(
      height: headerHeight,
      child: Stack(
        children: [
          // Wave Background
          Positioned.fill(
            child: CustomPaint(
              painter: _WaveHeaderPainter(
                startColor: Color.lerp(
                  DS.surfacePrimaryElevated,
                  DS.brandPrimary,
                  0.04,
                )!,
                middleColor: Color.lerp(
                  DS.surfaceCanvas,
                  DS.surfaceSecondary,
                  0.54,
                )!,
                endColor: Color.lerp(
                  DS.surfaceCanvas,
                  DS.brandSecondary,
                  0.06,
                )!,
              ),
            ),
          ),
          // Content
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing20,
                DS.spacing12,
                DS.spacing20,
                DS.spacing12,
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      // Avatar Area
                      DecoratedBox(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: DS.borderStrong, width: 3),
                          boxShadow: DS.shadowMd,
                        ),
                        child: SparkleAvatar(
                          radius: 36,
                          backgroundColor: DS.avatarFallbackBackground,
                          url: user.avatarStatus == AvatarStatus.pending
                              ? (user.pendingAvatarUrl ?? user.avatarUrl)
                              : user.avatarUrl,
                          fallbackText: user.nickname ?? user.username,
                          status: user.avatarStatus,
                        ),
                      ),
                      const SizedBox(width: DS.spacing16),
                      // Info Area
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user.nickname ?? user.username,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing6),
                            Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: [
                                _buildHeaderPill(
                                  icon: Icons.local_fire_department_rounded,
                                  label:
                                      '${l10n.levelPrefix}${user.flameLevel}',
                                  accent: DS.brandPrimaryConst,
                                ),
                                _buildHeaderPill(
                                  icon: Icons.bolt_rounded,
                                  label:
                                      '${l10n.brightness} ${(user.flameBrightness * 100).toInt()}%',
                                  accent: DS.info,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderPill({
    required IconData icon,
    required String label,
    required Color accent,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: Color.alphaBlend(
            accent.withValues(alpha: 0.1),
            DS.surfaceOverlay,
          ),
          borderRadius: DS.borderRadius20,
          border: Border.all(color: accent.withValues(alpha: 0.14)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: accent, size: 16),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: DS.labelSmall.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ],
        ),
      );

  Widget _buildSettingsSection(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
    UserModel user,
    Map<String, dynamic>? profileContext,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Guest upgrade (conditional)
          if (user.registrationSource == 'guest') ...[
            GraphiteCardSurface(
              child: _buildSettingsTile(
                context,
                icon: Icons.upgrade_rounded,
                title: l10n.profileUpgradeGuest,
                accentColor: const Color(0xFFC37D3A),
                onTap: () => context.push(UserRoutes.guestUpgrade),
              ),
            ),
            const SizedBox(height: DS.spacing16),
          ],

          // Personal Growth
          _buildSectionLabel(context, l10n.personalGrowth),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.collections_bookmark_outlined,
                  title: l10n.profileLearningPortfolio,
                  subtitle: l10n.profileLearningPortfolioSubtitle,
                  accentColor: const Color(0xFF5F8C72),
                  onTap: () => context.push(PlanRoutes.learningPortfolio),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.emoji_events_outlined,
                  title: l10n.achievementTitle,
                  accentColor: const Color(0xFFFFD700),
                  onTap: () => context.push(AchievementRoutes.basePath),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.photo_library_outlined,
                  title: l10n.profilePosterStudio,
                  subtitle: l10n.profilePosterStudioSubtitle,
                  accentColor: const Color(0xFF6E8EF7),
                  onTap: () => context.push(UserRoutes.posterStudio),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.palette_outlined,
                  title: l10n.visualElementsTitle,
                  accentColor: const Color(0xFF7B68EE),
                  onTap: () => context.push(VisualElementsRoutes.basePath),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.psychology_alt_outlined,
                  title: l10n.myPersona,
                  accentColor: const Color(0xFF8877A6),
                  onTap: () => context.push(UserRoutes.persona),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // Settings
          _buildSectionLabel(context, l10n.settings),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.person_outline_rounded,
                  title: l10n.profilePersonalInfo,
                  accentColor: const Color(0xFF9B7A72),
                  onTap: () => context.push(UserRoutes.editProfile),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.tune_rounded,
                  title: l10n.schedulePreferences,
                  accentColor: const Color(0xFF7087A6),
                  onTap: () => context.push(UserRoutes.settings),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.auto_awesome_motion_rounded,
                  title: l10n.profileMyWay,
                  accentColor: const Color(0xFF6F8F86),
                  onTap: () => context.push(UserRoutes.skills),
                ),
                const Divider(height: 1, indent: 60),
                _buildToggleTile(
                  context,
                  icon: Icons.insights_outlined,
                  title: l10n.profileMetacognitionPanel,
                  subtitle: ((profileContext?['metacognition_dashboard']
                              as Map<String, dynamic>?)?['hidden'] ==
                          true)
                      ? l10n.profileMetacognitionHidden
                      : l10n.profileMetacognitionVisible,
                  accentColor: const Color(0xFF4A7A58),
                  value: (profileContext?['metacognition_dashboard']
                          as Map<String, dynamic>?)?['hidden'] !=
                      true,
                  onChanged: (value) async {
                    await ref
                        .read(userRepositoryProvider)
                        .updateMetacognitionPanelPreference(hidden: !value);
                    ref.invalidate(profileContextProvider);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // Account
          _buildSectionLabel(context, l10n.account),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.manage_accounts_outlined,
                  title: l10n.accountSecurity,
                  accentColor: const Color(0xFF6E8FAE),
                  onTap: () => context.push(UserRoutes.accountSecurity),
                ),
                if (AppFeatureFlags.enableUserMemoryControls) ...[
                  const Divider(height: 1, indent: 60),
                  _buildSettingsTile(
                    context,
                    icon: Icons.memory_rounded,
                    title: l10n.memoryControl,
                    accentColor: const Color(0xFF6D9282),
                    onTap: () => context.push(UserRoutes.memorySettings),
                  ),
                ],
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.download_rounded,
                  title: l10n.profileExportData,
                  accentColor: const Color(0xFF5A7FA0),
                  onTap: () => unawaited(_exportData(context, ref)),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // Sign Out
          _buildSectionLabel(context, l10n.logout),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.logout_rounded,
                  title: l10n.logout,
                  accentColor: const Color(0xFFB06F67),
                  isDestructive: true,
                  onTap: () => _showLogoutDialog(context, ref, l10n),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.delete_forever_rounded,
                  title: l10n.profileDeleteAccount,
                  accentColor: const Color(0xFFB84F45),
                  isDestructive: true,
                  onTap: () => context.push(UserRoutes.deleteAccount),
                ),
              ],
            ),
          ),
        ],
      );

  Future<void> _exportData(BuildContext context, WidgetRef ref) async {
    AppFeedback.info(context, context.l10n.profileExportPreparing);
    try {
      final bytes = await ref.read(userRepositoryProvider).exportUserData();
      if (bytes.isEmpty) throw Exception(context.l10n.profileExportEmptyFile);
      final dir = await getTemporaryDirectory();
      final now = DateTime.now();
      final filename =
          'sparkle_export_${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}.zip';
      final file = File('${dir.path}/$filename');
      await file.writeAsBytes(bytes, flush: true);
      if (!context.mounted) return;
      await SharePlus.instance.share(
        ShareParams(
          files: [XFile(file.path, mimeType: 'application/zip')],
          subject: context.l10n.profileExportShareSubject,
        ),
      );
    } catch (e) {
      if (!context.mounted) return;
      AppFeedback.error(context, context.l10n.profileExportFailed(e.toString()));
    }
  }

  void _showLogoutDialog(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
  ) {
    unawaited(
      showDialog<void>(
        context: context,
        builder: (context) => Dialog(
          backgroundColor: Colors.transparent,
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: GraphiteModalSurface(
            title: l10n.logout,
            showHandle: false,
            borderRadius: BorderRadius.circular(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.confirmLogout,
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: DS.lg),
                Row(
                  children: [
                    Expanded(
                      child: SparkleButton.ghost(
                        onPressed: () => Navigator.pop(context),
                        label: l10n.cancel,
                      ),
                    ),
                    const SizedBox(width: DS.sm),
                    Expanded(
                      child: SparkleButton.destructive(
                        onPressed: () async {
                          Navigator.pop(context);
                          await ref.read(authProvider.notifier).logout();
                          if (!context.mounted) return;
                          context.go('/login');
                        },
                        label: l10n.confirm,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSectionLabel(BuildContext context, String title) => Padding(
        padding: const EdgeInsets.only(left: DS.spacing4),
        child: Text(
          title,
          style: DS.labelLarge.copyWith(
            letterSpacing: 0.2,
            color: DS.textSecondary,
          ),
        ),
      );

  Widget _buildSettingsTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required Color accentColor,
    required VoidCallback onTap,
    String? subtitle,
    bool isDestructive = false,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing6,
      ),
      leading: Container(
        padding: const EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              accentColor.withValues(alpha: isDark ? 0.28 : 0.20),
              Color.lerp(accentColor, DS.surfacePrimaryElevated, 0.68)!,
            ],
          ),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: accentColor.withValues(alpha: isDark ? 0.36 : 0.18),
          ),
        ),
        child: Icon(icon, color: accentColor, size: 20),
      ),
      title: Row(
        children: [
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: isDestructive ? DS.error : DS.textPrimary,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.7),
              shape: BoxShape.circle,
            ),
          ),
        ],
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: DS.spacing4),
        child: Text(
          subtitle ?? _settingsSubtitle(title, context.l10n),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
      ),
      trailing: Icon(
        Icons.arrow_forward_ios_rounded,
        size: 16,
        color: DS.neutral400,
      ),
    );
  }

  Widget _buildToggleTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accentColor,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return SwitchListTile.adaptive(
      value: value,
      onChanged: onChanged,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing6,
      ),
      secondary: Container(
        padding: const EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              accentColor.withValues(alpha: isDark ? 0.28 : 0.20),
              Color.lerp(accentColor, DS.surfacePrimaryElevated, 0.68)!,
            ],
          ),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: accentColor.withValues(alpha: isDark ? 0.36 : 0.18),
          ),
        ),
        child: Icon(icon, color: accentColor, size: 20),
      ),
      title: Text(
        title,
        style: TextStyle(
          color: DS.textPrimary,
          fontWeight: DS.fontWeightMedium,
        ),
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: DS.spacing4),
        child: Text(
          subtitle,
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
      ),
      activeTrackColor: accentColor,
    );
  }

  String _settingsSubtitle(String title, AppLocalizations l10n) {
    if (title == l10n.achievementTitle) {
      return l10n.profileSubtitleAchievements;
    } else if (title == l10n.visualElementsTitle) {
      return l10n.profileSubtitleVisualElements;
    } else if (title == l10n.myPersona) {
      return l10n.profileSubtitlePersona;
    } else if (title == l10n.profilePersonalInfo) {
      return l10n.profileSubtitlePersonalInfo;
    } else if (title == l10n.schedulePreferences) {
      return l10n.profileSubtitlePreferences;
    } else if (title == l10n.profileMyWay) {
      return l10n.profileSubtitleMyWay;
    } else if (title == l10n.accountSecurity) {
      return l10n.profileSubtitleSecurity;
    } else if (title == l10n.memoryControl) {
      return l10n.profileSubtitleMemory;
    } else if (title == l10n.logout) {
      return l10n.profileSubtitleLogout;
    } else if (title == l10n.profileDeleteAccount) {
      return l10n.profileSubtitleDeleteAccount;
    } else {
      return l10n.profileSubtitleDefault;
    }
  }
}

class _WaveHeaderPainter extends CustomPainter {
  const _WaveHeaderPainter({
    required this.startColor,
    required this.middleColor,
    required this.endColor,
  });

  final Color startColor;
  final Color middleColor;
  final Color endColor;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [startColor, middleColor, endColor],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    final path = Path();
    path.lineTo(0, size.height - 60);

    // First curve
    path.quadraticBezierTo(
      size.width * 0.25,
      size.height,
      size.width * 0.5,
      size.height - 40,
    );

    // Second curve
    path.quadraticBezierTo(
      size.width * 0.75,
      size.height - 80,
      size.width,
      size.height - 20,
    );

    path.lineTo(size.width, 0);
    path.close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _WaveHeaderPainter oldDelegate) =>
      oldDelegate.startColor != startColor ||
      oldDelegate.middleColor != middleColor ||
      oldDelegate.endColor != endColor;
}
