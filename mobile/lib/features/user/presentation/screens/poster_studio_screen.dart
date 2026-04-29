import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class PosterStudioScreen extends ConsumerStatefulWidget {
  const PosterStudioScreen({super.key});

  @override
  ConsumerState<PosterStudioScreen> createState() => _PosterStudioScreenState();
}

class _PosterStudioScreenState extends ConsumerState<PosterStudioScreen> {
  String _selectedPresetId = 'identity';
  String _selectedTemplateId = 'cosmic';
  bool _isGeneratingPreview = false;
  File? _previewFile;
  String? _previewSignature;
  String? _scheduledPreviewSignature;
  String? _previewError;

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final achievementState = ref.watch(achievementProvider);
    final planState = ref.watch(planListProvider);
    final capsuleState = ref.watch(capsuleProvider);

    if (user == null) {
      return const SizedBox.shrink();
    }

    final presets = _buildPresets(
      user,
      achievementState,
      planState.activePlans,
      capsuleState.valueOrNull ?? const [],
    );
    final selectedPreset = presets.firstWhere(
      (preset) => preset.id == _selectedPresetId,
      orElse: () => presets.first,
    );
    final selectedPayload =
        selectedPreset.payload.copyWith(templateId: _selectedTemplateId);
    final signature =
        '${selectedPreset.id}::$_selectedTemplateId::${selectedPayload.title}::${selectedPayload.subtitle ?? ''}';

    if (_previewSignature != signature &&
        !_isGeneratingPreview &&
        _scheduledPreviewSignature != signature) {
      _scheduledPreviewSignature = signature;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _scheduledPreviewSignature = null;
        if (!mounted) return;
        unawaited(_requestPreviewGeneration(selectedPayload, signature));
      });
    }

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.posterTitle),
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.spacing16),
          children: [
            _PosterStudioHero(
              selectedPreset: selectedPreset,
              selectedTemplateId: _selectedTemplateId,
            ),
            const SizedBox(height: DS.spacing20),
            Text(
              context.l10n.posterTypeLabel,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing10),
            LayoutBuilder(
              builder: (context, constraints) {
                final crossAxisCount = constraints.maxWidth < 560 ? 1 : 2;
                final itemHeight = crossAxisCount == 1 ? 124.0 : 136.0;
                return GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: presets.length,
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: crossAxisCount,
                    mainAxisSpacing: DS.spacing10,
                    crossAxisSpacing: DS.spacing10,
                    mainAxisExtent: itemHeight,
                  ),
                  itemBuilder: (context, index) {
                    final preset = presets[index];
                    final selected = preset.id == selectedPreset.id;
                    return _PosterPresetTile(
                      preset: preset,
                      selected: selected,
                      onTap: () => setState(() {
                        _selectedPresetId = preset.id;
                      }),
                    );
                  },
                );
              },
            ),
            const SizedBox(height: DS.spacing20),
            Text(
              context.l10n.posterTemplateLabel,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: DefaultShareTemplates.all
                  .map(
                    (template) => ChoiceChip(
                      label: Text(template.name),
                      selected: _selectedTemplateId == template.id,
                      onSelected: (_) => setState(() {
                        _selectedTemplateId = template.id;
                      }),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: DS.spacing10),
            _SelectedTemplateCaption(templateId: _selectedTemplateId),
            const SizedBox(height: DS.spacing20),
            Text(
              context.l10n.posterPreviewLabel,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing10),
            _PosterPreviewCard(
              isGenerating: _isGeneratingPreview,
              previewFile: _previewFile,
              errorMessage: _previewError,
            ),
            const SizedBox(height: DS.spacing16),
            Wrap(
              spacing: DS.spacing12,
              runSpacing: DS.spacing12,
              children: [
                SizedBox(
                  width: double.infinity,
                  child: SparkleButton(
                    expand: true,
                    icon: const Icon(Icons.share_outlined),
                    label: context.l10n.posterShareOrDownload,
                    onPressed: () => showUniversalShareSheet(
                      context,
                      payload: selectedPayload,
                      onGenerateCard: (payload) =>
                          SharePosterService().generatePoster(context, payload),
                    ),
                  ),
                ),
                SizedBox(
                  width: double.infinity,
                  child: SparkleButton(
                    expand: true,
                    icon: const Icon(Icons.refresh_rounded),
                    label: context.l10n.posterRegenerate,
                    variant: ButtonVariant.secondary,
                    disabled: _isGeneratingPreview,
                    onPressed: () => unawaited(
                      _requestPreviewGeneration(
                        selectedPayload,
                        signature,
                        force: true,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _requestPreviewGeneration(
    UniversalSharePayload payload,
    String signature, {
    bool force = false,
  }) async {
    if (_isGeneratingPreview) {
      return;
    }
    await _generatePreview(payload, signature, force: force);
  }

  Future<void> _generatePreview(
    UniversalSharePayload payload,
    String signature, {
    bool force = false,
  }) async {
    if (!force && _previewSignature == signature && _previewFile != null) {
      return;
    }
    setState(() {
      _isGeneratingPreview = true;
      _previewSignature = signature;
      _previewError = null;
    });
    try {
      final file = await SharePosterService().generatePoster(context, payload);
      if (!mounted) return;
      setState(() {
        _previewFile = file;
        _previewError = file == null ? context.l10n.posterPreviewFailed : null;
      });
      if (file == null) {
        AppFeedback.error(context, context.l10n.posterPreviewError);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _previewError = _friendlyError(error);
      });
      AppFeedback.error(context, context.l10n.posterPreviewErrorWith(_friendlyError(error)));
    } finally {
      if (!mounted) return;
      setState(() {
        _isGeneratingPreview = false;
      });
    }
  }

  String _friendlyError(Object error) {
    final message = error.toString().trim();
    if (message.isEmpty) {
      return context.l10n.posterUnknownError;
    }
    return message.replaceFirst('Exception: ', '');
  }

  List<_PosterPreset> _buildPresets(
    UserModel user,
    AchievementState achievementState,
    List<PlanModel> activePlans,
    List<CuriosityCapsuleModel> capsules,
  ) {
    final l10n = context.l10n;
    final unlocked = achievementState.achievements
        .where((achievement) => achievement.isUnlocked)
        .toList()
      ..sort((a, b) {
        final rarityCompare =
            b.achievement.rarity.index.compareTo(a.achievement.rarity.index);
        if (rarityCompare != 0) return rarityCompare;
        final aTime = a.userProgress?.unlockedAt;
        final bTime = b.userProgress?.unlockedAt;
        if (aTime == null || bTime == null) return 0;
        return bTime.compareTo(aTime);
      });
    final topAchievement = unlocked.isNotEmpty ? unlocked.first : null;
    final activePlan = activePlans.isNotEmpty ? activePlans.first : null;
    final latestCapsule = capsules.isNotEmpty ? capsules.first : null;
    final userName = user.nickname ?? user.username;
    final flameBrightness = (user.flameBrightness * 100).round();

    return [
      _PosterPreset(
        id: 'identity',
        title: l10n.posterIdentityTitle,
        subtitle: l10n.posterIdentitySubtitle,
        icon: Icons.workspace_premium_rounded,
        accent: const Color(0xFFF0C676),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.achievement,
          resourceId: topAchievement?.achievement.id ?? user.id,
          title: l10n.posterIdentityPayloadTitle(userName),
          subtitle: topAchievement?.achievement.name ?? l10n.posterIdentityDefaultSubtitle,
          description: topAchievement?.achievement.description,
          metadata: {
            'rarity': topAchievement?.achievement.rarity.name ?? l10n.posterIdentityDefaultRarity,
            'unlocked_count': unlocked.length,
            'flame_level': user.flameLevel,
            'equipped_title': achievementState.titles
                    .where((title) => title.isEquipped)
                    .firstOrNull
                    ?.titleDisplay ??
                l10n.posterIdentityGrowing,
          },
          templateId: 'elegant',
        ),
      ),
      _PosterPreset(
        id: 'growth',
        title: l10n.posterGrowthTitle,
        subtitle: l10n.posterGrowthSubtitle,
        icon: Icons.insights_rounded,
        accent: const Color(0xFF7AA5F8),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.learningReport,
          resourceId: user.id,
          title: l10n.posterGrowthPayloadTitle(userName),
          subtitle: l10n.posterGrowthPayloadSubtitle(user.flameLevel, flameBrightness),
          description: l10n.posterGrowthDesc,
          metadata: {
            'report_type': l10n.posterGrowthReportType,
            'active_plans': activePlans.length,
            'unlocked_achievements': unlocked.length,
            'flame_brightness': '$flameBrightness%',
          },
        ),
      ),
      _PosterPreset(
        id: 'plan',
        title: l10n.posterPlanTitle,
        subtitle: l10n.posterPlanSubtitle,
        icon: Icons.flag_rounded,
        accent: const Color(0xFF5BA8FF),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.planProgress,
          resourceId: activePlan?.id ?? user.id,
          title: activePlan?.name ?? l10n.posterPlanDefaultTitle,
          subtitle: activePlan?.description ?? l10n.posterPlanDefaultSubtitle,
          description: activePlan?.description,
          metadata: {
            'progress': activePlan?.progress ?? 0.0,
            'completed_tasks': activePlan?.tasks
                    ?.where((task) => task.status.name == 'completed')
                    .length ??
                0,
            'total_tasks': activePlan?.tasks?.length ?? 0,
            'subject': activePlan?.subject ?? l10n.posterPlanDefaultSubject,
            'deadline': activePlan?.targetDate?.toIso8601String(),
          },
          templateId: 'minimal',
        ),
      ),
      _PosterPreset(
        id: 'capsule',
        title: l10n.posterCapsuleTitle,
        subtitle: l10n.posterCapsuleSubtitle,
        icon: Icons.auto_awesome_rounded,
        accent: const Color(0xFFD29BFF),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.capsule,
          resourceId: latestCapsule?.id ?? user.id,
          title: latestCapsule?.title ?? l10n.posterCapsuleDefaultTitle,
          subtitle: latestCapsule == null
              ? l10n.posterCapsuleDefaultSubtitle
              : latestCapsule.content.split('\n').first,
          description: latestCapsule?.content ?? l10n.posterCapsuleDefaultDesc,
          metadata: {
            'depth_label': latestCapsule?.depthLabel ?? l10n.posterCapsuleDefaultDepth,
            'word_count': latestCapsule?.content.length ?? 0,
            'created_at': latestCapsule?.createdAt.toIso8601String(),
            'related_subject': latestCapsule?.relatedSubject,
          },
          templateId: 'neon',
        ),
      ),
    ];
  }
}

class _PosterPreset {
  const _PosterPreset({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.payload,
  });

  final String id;
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final UniversalSharePayload payload;
}

class _PosterPresetTile extends StatelessWidget {
  const _PosterPresetTile({
    required this.preset,
    required this.selected,
    required this.onTap,
  });

  final _PosterPreset preset;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                preset.accent.withValues(alpha: selected ? 0.20 : 0.10),
                DS.surfaceSecondary,
              ],
            ),
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: selected
                  ? preset.accent.withValues(alpha: 0.65)
                  : DS.borderSubtle,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(preset.icon, color: preset.accent),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      preset.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: DS.bodyMedium.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Text(
                      preset.subtitle,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Icon(
                selected
                    ? Icons.check_circle_rounded
                    : Icons.radio_button_unchecked,
                size: 18,
                color: selected ? preset.accent : DS.textTertiary,
              ),
            ],
          ),
        ),
      );
}

class _PosterPreviewCard extends StatelessWidget {
  const _PosterPreviewCard({
    required this.isGenerating,
    required this.previewFile,
    this.errorMessage,
  });

  final bool isGenerating;
  final File? previewFile;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius20,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: AspectRatio(
          aspectRatio: 396 / 704,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: ColoredBox(
              color: DS.surfacePrimary,
              child: isGenerating
                  ? const Center(child: CircularProgressIndicator())
                  : errorMessage != null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(DS.spacing16),
                            child: Text(
                              errorMessage!,
                              textAlign: TextAlign.center,
                              style: DS.bodyMedium.copyWith(
                                color: DS.textSecondary,
                              ),
                            ),
                          ),
                        )
                      : previewFile != null
                          ? Image.file(previewFile!, fit: BoxFit.cover)
                          : Center(
                              child: Text(
                                AppLocalizations.of(context)!.posterPreviewGenerating,
                                style: DS.bodyMedium.copyWith(
                                  color: DS.textSecondary,
                                ),
                              ),
                            ),
            ),
          ),
        ),
      );
}

class _PosterStudioHero extends StatelessWidget {
  const _PosterStudioHero({
    required this.selectedPreset,
    required this.selectedTemplateId,
  });

  final _PosterPreset selectedPreset;
  final String selectedTemplateId;

  @override
  Widget build(BuildContext context) {
    final template = DefaultShareTemplates.all.firstWhere(
      (item) => item.id == selectedTemplateId,
      orElse: () => DefaultShareTemplates.all.first,
    );

    return Container(
      padding: const EdgeInsets.all(DS.spacing18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            selectedPreset.accent.withValues(alpha: 0.14),
            DS.surfacePrimaryElevated,
            (template.color ?? DS.brandPrimary).withValues(alpha: 0.08),
          ],
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: selectedPreset.accent.withValues(alpha: 0.18),
        ),
        boxShadow: [
          BoxShadow(
            color: selectedPreset.accent.withValues(alpha: 0.10),
            blurRadius: 24,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _HeroBadge(
                icon: selectedPreset.icon,
                label: selectedPreset.title,
                color: selectedPreset.accent,
              ),
              _HeroBadge(
                icon: template.icon ?? Icons.auto_awesome,
                label: AppLocalizations.of(context)!.posterTemplateSuffix(template.name),
                color: template.color ?? DS.brandPrimary,
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            AppLocalizations.of(context)!.posterHeroHeadline,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ) ??
                TextStyle(
                  fontSize: 24,
                  height: 1.15,
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            AppLocalizations.of(context)!.posterHeroDesc,
            maxLines: 4,
            overflow: TextOverflow.ellipsis,
            style: DS.bodyMedium.copyWith(
              color: DS.textSecondary,
              height: 1.55,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _HeroChip(label: AppLocalizations.of(context)!.communityShareCorePosters),
              _HeroChip(label: AppLocalizations.of(context)!.posterChipLivePreview),
              _HeroChip(label: AppLocalizations.of(context)!.posterChipDownload),
              _HeroChip(label: AppLocalizations.of(context)!.posterChipSystemShare),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeroBadge extends StatelessWidget {
  const _HeroBadge({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width < 360 ? 148 : 188,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.10),
          borderRadius: DS.borderRadius20,
          border: Border.all(color: color.withValues(alpha: 0.18)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: DS.spacing6),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightSemibold,
                        ) ??
                    DS.bodySmall.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightSemibold,
                    ),
              ),
            ),
          ],
        ),
      );
}

class _HeroChip extends StatelessWidget {
  const _HeroChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: DS.borderRadius20,
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: DS.labelSmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );
}

class _SelectedTemplateCaption extends StatelessWidget {
  const _SelectedTemplateCaption({required this.templateId});

  final String templateId;

  @override
  Widget build(BuildContext context) {
    final template = DefaultShareTemplates.all.firstWhere(
      (item) => item.id == templateId,
      orElse: () => DefaultShareTemplates.all.first,
    );

    return GraphiteCardSurface(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing12,
      ),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color:
                  (template.color ?? DS.brandPrimary).withValues(alpha: 0.12),
              borderRadius: DS.borderRadius12,
            ),
            child: Icon(
              template.icon ?? Icons.auto_awesome,
              color: template.color ?? DS.brandPrimary,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppLocalizations.of(context)!.posterTemplateSuffix(template.name),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: DS.bodyMedium.copyWith(
                    fontWeight: DS.fontWeightBold,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing2),
                Text(
                  template.description ?? AppLocalizations.of(context)!.posterTemplateDefaultDesc,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
