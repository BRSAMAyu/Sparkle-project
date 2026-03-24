import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
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

    if (_previewSignature != signature && !_isGeneratingPreview) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        unawaited(_generatePreview(selectedPayload, signature));
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
        title: const Text('海报工坊'),
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
              '海报类型',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing10),
            LayoutBuilder(
              builder: (context, constraints) {
                final crossAxisCount = constraints.maxWidth < 420 ? 1 : 2;
                final itemWidth = (constraints.maxWidth -
                        ((crossAxisCount - 1) * DS.spacing10)) /
                    crossAxisCount;
                final itemHeight = crossAxisCount == 1 ? 108.0 : 120.0;
                final ratio = itemWidth / itemHeight;
                return GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: presets.length,
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: crossAxisCount,
                    mainAxisSpacing: DS.spacing10,
                    crossAxisSpacing: DS.spacing10,
                    childAspectRatio: ratio,
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
              '视觉模板',
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
              '实时预览',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing10),
            _PosterPreviewCard(
              isGenerating: _isGeneratingPreview,
              previewFile: _previewFile,
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
                    label: '分享或下载',
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
                  child: SparkleButton.secondary(
                    expand: true,
                    icon: const Icon(Icons.refresh_rounded),
                    label: '重新生成预览',
                    onPressed: () => unawaited(
                      _generatePreview(selectedPayload, signature, force: true),
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

  Future<void> _generatePreview(
    UniversalSharePayload payload,
    String signature, {
    bool force = false,
  }) async {
    if (!force && _previewSignature == signature) return;
    setState(() {
      _isGeneratingPreview = true;
      _previewSignature = signature;
    });
    final file = await SharePosterService().generatePoster(context, payload);
    if (!mounted) return;
    setState(() {
      _previewFile = file;
      _isGeneratingPreview = false;
    });
  }

  List<_PosterPreset> _buildPresets(
    UserModel user,
    AchievementState achievementState,
    List<PlanModel> activePlans,
    List<CuriosityCapsuleModel> capsules,
  ) {
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
    final topAchievement =
        unlocked.isNotEmpty ? unlocked.first : null;
    final activePlan = activePlans.isNotEmpty ? activePlans.first : null;
    final latestCapsule =
        capsules.isNotEmpty ? capsules.first : null;
    final userName = user.nickname ?? user.username;
    final flameBrightness = (user.flameBrightness * 100).round();

    return [
      _PosterPreset(
        id: 'identity',
        title: '荣耀身份海报',
        subtitle: '展示你的称号、等级与代表成就',
        icon: Icons.workspace_premium_rounded,
        accent: const Color(0xFFF0C676),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.achievement,
          resourceId: topAchievement?.achievement.id ?? user.id,
          title: '$userName 的荣耀身份',
          subtitle: topAchievement?.achievement.name ?? '把成长高光分享给朋友',
          description: topAchievement?.achievement.description,
          metadata: {
            'rarity': topAchievement?.achievement.rarity.name ?? '荣耀',
            'unlocked_count': unlocked.length,
            'flame_level': user.flameLevel,
            'equipped_title': achievementState.titles
                    .where((title) => title.isEquipped)
                    .firstOrNull
                    ?.titleDisplay ??
                '持续成长中',
          },
          templateId: 'elegant',
        ),
      ),
      _PosterPreset(
        id: 'growth',
        title: '本周成长海报',
        subtitle: '把成长趋势、亮度和活跃计划做成一张战报',
        icon: Icons.insights_rounded,
        accent: const Color(0xFF7AA5F8),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.learningReport,
          resourceId: user.id,
          title: '$userName 的本周成长',
          subtitle: '等级 Lv.${user.flameLevel} · 亮度 $flameBrightness%',
          description: '继续保持这个节奏，你的学习势能已经在持续上升。',
          metadata: {
            'report_type': '成长周报',
            'active_plans': activePlans.length,
            'unlocked_achievements': unlocked.length,
            'flame_brightness': '$flameBrightness%',
          },
        ),
      ),
      _PosterPreset(
        id: 'plan',
        title: '计划战报海报',
        subtitle: '把当前正在推进的计划做成一张高质感进度卡',
        icon: Icons.flag_rounded,
        accent: const Color(0xFF5BA8FF),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.planProgress,
          resourceId: activePlan?.id ?? user.id,
          title: activePlan?.name ?? '我的下一阶段计划',
          subtitle: activePlan?.description ?? '把目标拆成任务，稳定推进。',
          description: activePlan?.description,
          metadata: {
            'progress': activePlan?.progress ?? 0.0,
            'completed_tasks': activePlan?.tasks
                    ?.where((task) => task.status.name == 'completed')
                    .length ??
                0,
            'total_tasks': activePlan?.tasks?.length ?? 0,
            'subject': activePlan?.subject ?? '个人成长',
            'deadline': activePlan?.targetDate?.toIso8601String(),
          },
          templateId: 'minimal',
        ),
      ),
      _PosterPreset(
        id: 'capsule',
        title: '灵感胶囊海报',
        subtitle: '把最近一次洞察或好奇心胶囊做成可分享的思考卡片',
        icon: Icons.auto_awesome_rounded,
        accent: const Color(0xFFD29BFF),
        payload: UniversalSharePayload(
          contentType: ShareableContentType.capsule,
          resourceId: latestCapsule?.id ?? user.id,
          title: latestCapsule?.title ?? '今天的灵感胶囊',
          subtitle: latestCapsule == null
              ? '把一个新的想法，留成值得回看的海报。'
              : latestCapsule.content.split('\n').first,
          description: latestCapsule?.content ?? '新的洞察正在生成，等你点亮。',
          metadata: {
            'depth_label': latestCapsule?.depthLabel ?? '灵感',
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
        child: Column(
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
            const SizedBox(height: DS.spacing10),
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
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                  height: 1.35,
                ),
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
  });

  final bool isGenerating;
  final File? previewFile;

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
                : previewFile != null
                    ? Image.file(previewFile!, fit: BoxFit.cover)
                    : Center(
                        child: Text(
                          '预览生成中',
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
                label: '${template.name} 模板',
                color: template.color ?? DS.brandPrimary,
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            '把你的成长，做成值得分享的一张图',
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
            '海报工坊会自动读取你的真实成就、计划、胶囊和成长数据，生成适合分享到社交平台或保存到相册的高质感海报。',
            style: DS.bodyMedium.copyWith(
              color: DS.textSecondary,
              height: 1.55,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          const Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _HeroChip(label: '4 种核心海报'),
              _HeroChip(label: '实时预览'),
              _HeroChip(label: '下载图片'),
              _HeroChip(label: '系统分享'),
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
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ) ??
                DS.bodySmall.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
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
              color: (template.color ?? DS.brandPrimary).withValues(alpha: 0.12),
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
                  '${template.name} 模板',
                  style: DS.bodyMedium.copyWith(
                    fontWeight: DS.fontWeightBold,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing2),
                Text(
                  template.description ?? '适合分享你的成长亮点',
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
