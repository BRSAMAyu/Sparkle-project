import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/providers/theme_provider.dart';

class ThemeSettingsScreen extends ConsumerWidget {
  const ThemeSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeManager = ref.watch(themeManagerProvider);
    final currentMode = ref.watch(appThemeModeProvider);
    final currentPreset = ref.watch(brandPresetProvider);
    final highContrast = ref.watch(highContrastProvider);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.themeSettings),
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.lg,
            vertical: DS.md,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GraphiteCardSurface(
                child: _ThemeModeSection(
                  currentMode: currentMode,
                  onModeChanged: themeManager.setAppThemeMode,
                ),
              ),
              const SizedBox(height: DS.xl),
              GraphiteCardSurface(
                child: _BrandPresetSection(
                  currentPreset: currentPreset,
                  onPresetChanged: themeManager.setBrandPreset,
                ),
              ),
              const SizedBox(height: DS.xl),
              GraphiteCardSurface(
                child: _HighContrastSection(
                  highContrast: highContrast,
                  onToggled: themeManager.toggleHighContrast,
                ),
              ),
              const SizedBox(height: DS.xl),
              GraphiteCardSurface(
                child: _ResetButton(
                  onPressed: () {
                    unawaited(themeManager.reset());
                    if (context.mounted) {
                      AppFeedback.success(
                        context,
                        context.l10n.themeResetSuccess,
                      );
                    }
                  },
                ),
              ),
              const SizedBox(height: DS.xl),
              const GraphiteCardSurface(
                child: _ColorPreviewSection(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ThemeModeSection extends StatelessWidget {
  const _ThemeModeSection({
    required this.currentMode,
    required this.onModeChanged,
  });

  final AppThemeMode currentMode;
  final void Function(AppThemeMode) onModeChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionIntro(
            title: '主题模式',
            description: '控制页面亮暗模式，让视觉节奏和使用环境保持一致。',
          ),
          const SizedBox(height: DS.md),
          DecoratedBox(
            decoration: BoxDecoration(
              border: Border.all(color: DS.borderSubtle),
              borderRadius: BorderRadius.circular(DS.md),
              color: DS.surfaceSecondary,
            ),
            child: Row(
              children: [
                _SegmentItem(
                  label: context.l10n.themeModeLight,
                  selected: currentMode == AppThemeMode.light,
                  onTap: () => onModeChanged(AppThemeMode.light),
                  isLeading: true,
                ),
                _SegmentItem(
                  label: context.l10n.themeModeDark,
                  selected: currentMode == AppThemeMode.dark,
                  onTap: () => onModeChanged(AppThemeMode.dark),
                ),
                _SegmentItem(
                  label: context.l10n.themeModeSystem,
                  selected: currentMode == AppThemeMode.system,
                  onTap: () => onModeChanged(AppThemeMode.system),
                  isTrailing: true,
                ),
              ],
            ),
          ),
        ],
      );
}

class _SegmentItem extends StatelessWidget {
  const _SegmentItem({
    required this.label,
    required this.selected,
    required this.onTap,
    this.isLeading = false,
    this.isTrailing = false,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool isLeading;
  final bool isTrailing;

  @override
  Widget build(BuildContext context) => Expanded(
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: DS.md),
            decoration: BoxDecoration(
              color: selected ? DS.brandPrimary : Colors.transparent,
              borderRadius: isLeading
                  ? const BorderRadius.only(
                      topLeft: Radius.circular(DS.md - 2),
                      bottomLeft: Radius.circular(DS.md - 2),
                    )
                  : isTrailing
                      ? const BorderRadius.only(
                          topRight: Radius.circular(DS.md - 2),
                          bottomRight: Radius.circular(DS.md - 2),
                        )
                      : BorderRadius.zero,
            ),
            child: Center(
              child: Text(
                label,
                style: DS.bodyMedium.copyWith(
                  color: selected ? DS.textOnPrimary : DS.textPrimary,
                  fontWeight:
                      selected ? DS.fontWeightSemibold : DS.fontWeightRegular,
                ),
              ),
            ),
          ),
        ),
      );
}

class _BrandPresetSection extends StatelessWidget {
  const _BrandPresetSection({
    required this.currentPreset,
    required this.onPresetChanged,
  });

  final BrandPreset currentPreset;
  final void Function(BrandPreset) onPresetChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionIntro(
            title: '品牌预设',
            description: '切换整套色彩底调，让整体气质更贴近你的使用习惯。',
          ),
          const SizedBox(height: DS.md),
          Wrap(
            spacing: DS.md,
            runSpacing: DS.md,
            children: BrandPreset.values.map((preset) {
              final selected = currentPreset == preset;
              final label = switch (preset) {
                BrandPreset.sparkle => context.l10n.brandPresetSparkle,
                BrandPreset.ocean => context.l10n.brandPresetOcean,
                BrandPreset.forest => context.l10n.brandPresetForest,
              };

              return GestureDetector(
                onTap: () => onPresetChanged(preset),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.lg,
                    vertical: DS.md,
                  ),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: selected ? DS.brandPrimary : DS.borderSubtle,
                      width: selected ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(DS.md),
                    color: selected ? DS.brandPrimary12 : DS.surfaceSecondary,
                    boxShadow: selected
                        ? [
                            BoxShadow(
                              color: DS.brandPrimary.withValues(alpha: 0.12),
                              blurRadius: 18,
                              offset: const Offset(0, 10),
                            ),
                          ]
                        : null,
                  ),
                  child: Text(
                    label,
                    style: DS.bodyMedium.copyWith(
                      fontWeight: selected
                          ? DS.fontWeightSemibold
                          : DS.fontWeightRegular,
                      color: selected ? DS.brandPrimary : DS.textPrimary,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      );
}

class _HighContrastSection extends StatelessWidget {
  const _HighContrastSection({
    required this.highContrast,
    required this.onToggled,
  });

  final bool highContrast;
  final void Function(bool) onToggled;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _SectionIntro(
              title: context.l10n.highContrastSection,
              description: context.l10n.highContrastDesc,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Switch(
            value: highContrast,
            onChanged: onToggled,
            activeThumbColor: DS.brandPrimary,
          ),
        ],
      );
}

class _ResetButton extends StatelessWidget {
  const _ResetButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: double.infinity,
        child: SparkleButton.outline(
          onPressed: onPressed,
          label: context.l10n.resetDefaults,
          expand: true,
        ),
      );
}

class _ColorPreviewSection extends ConsumerWidget {
  const _ColorPreviewSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeManager = ref.watch(themeManagerProvider);
    final colors = themeManager.current.colors;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionIntro(
          title: '颜色预览',
          description: '快速确认品牌色、语义色和任务色彩在当前主题下的表现。',
        ),
        const SizedBox(height: DS.md),
        Row(
          children: [
            Expanded(
              child: _ColorBox(
                color: colors.brandPrimary,
                label: context.l10n.colorPrimary,
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: _ColorBox(
                color: colors.brandSecondary,
                label: context.l10n.colorSecondary,
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.md),
        Row(
          children: [
            Expanded(
              child: _ColorBox(
                color: colors.semanticSuccess,
                label: context.l10n.colorSuccess,
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: _ColorBox(
                color: colors.semanticWarning,
                label: context.l10n.colorWarning,
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: _ColorBox(
                color: colors.semanticError,
                label: context.l10n.colorError,
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.md),
        Text(
          context.l10n.taskTypeColors,
          style: DS.bodyMedium.copyWith(
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const SizedBox(height: DS.md),
        Wrap(
          spacing: DS.md,
          runSpacing: DS.md,
          children: [
            _ColorBox(
              color: colors.taskLearning,
              label: context.l10n.taskTypeLearning,
              size: 60,
            ),
            _ColorBox(
              color: colors.taskTraining,
              label: context.l10n.taskTypeTraining,
              size: 60,
            ),
            _ColorBox(
              color: colors.taskErrorFix,
              label: context.l10n.taskTypeFix,
              size: 60,
            ),
            _ColorBox(
              color: colors.taskReflection,
              label: context.l10n.taskTypeReflection,
              size: 60,
            ),
            _ColorBox(
              color: colors.taskSocial,
              label: context.l10n.taskTypeSocial,
              size: 60,
            ),
            _ColorBox(
              color: colors.taskPlanning,
              label: context.l10n.taskTypePlanning,
              size: 60,
            ),
          ],
        ),
      ],
    );
  }
}

class _ColorBox extends StatelessWidget {
  const _ColorBox({
    required this.color,
    required this.label,
    this.size = 80,
  });

  final Color color;
  final String label;
  final double size;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(DS.md),
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.3),
                  blurRadius: DS.md,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.xs),
          SizedBox(
            width: size + 8,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      );
}

class _SectionIntro extends StatelessWidget {
  const _SectionIntro({
    required this.title,
    required this.description,
  });

  final String title;
  final String description;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            description,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.35,
            ),
          ),
        ],
      );
}
