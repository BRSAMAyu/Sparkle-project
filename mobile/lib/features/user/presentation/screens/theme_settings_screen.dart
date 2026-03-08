import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/providers/theme_provider.dart';

/// Theme Settings Screen - 主题设置屏幕
///
/// 用户可以在此屏幕上：
/// - 切换深色/浅色/系统主题模式
/// - 选择品牌预设 (Sparkle/Ocean/Forest)
/// - 启用/禁用高对比度模式
/// - 恢复默认设置
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
          size: DS.touchTargetMinSize,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('主题设置'),
        elevation: 0,
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        foregroundColor: Theme.of(context).textTheme.titleLarge?.color,
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          child: Padding(
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
                      themeManager.reset();
                      if (context.mounted) {
                        AppFeedback.success(context, '已恢复为默认设置');
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
      ),
    );
  }
}

/// 主题模式选择部分
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
          Text(
            '主题模式',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: DS.md),
          _SegmentedThemeButton(
            currentMode: currentMode,
            onModeChanged: onModeChanged,
          ),
        ],
      );
}

/// 分段的主题切换按钮
class _SegmentedThemeButton extends StatelessWidget {
  const _SegmentedThemeButton({
    required this.currentMode,
    required this.onModeChanged,
  });

  final AppThemeMode currentMode;
  final void Function(AppThemeMode) onModeChanged;

  @override
  Widget build(BuildContext context) {
    const modes = AppThemeMode.values;
    final modeLabels = ['浅色', '深色', '跟随系统'];

    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: DS.brandPrimary30),
        borderRadius: BorderRadius.circular(DS.md),
      ),
      child: Row(
        children: List.generate(modes.length, (index) {
          final mode = modes[index];
          final label = modeLabels[index];
          final isSelected = currentMode == mode;

          return Expanded(
            child: GestureDetector(
              onTap: () => onModeChanged(mode),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: DS.md),
                decoration: BoxDecoration(
                  color: isSelected
                      ? DS.brandPrimary
                      : DS.surfacePrimary.withValues(alpha: 0),
                  borderRadius: index == 0
                      ? const BorderRadius.only(
                          topLeft: Radius.circular(DS.md - 2),
                          bottomLeft: Radius.circular(DS.md - 2),
                        )
                      : index == modes.length - 1
                          ? const BorderRadius.only(
                              topRight: Radius.circular(DS.md - 2),
                              bottomRight: Radius.circular(DS.md - 2),
                            )
                          : BorderRadius.zero,
                  border: index > 0
                      ? Border(
                          left: BorderSide(color: DS.brandPrimary30),
                        )
                      : null,
                ),
                child: Center(
                  child: Text(
                    label,
                    style: TextStyle(
                      color: isSelected
                          ? DS.textOnPrimary
                          : Theme.of(context).textTheme.bodyMedium?.color,
                      fontWeight:
                          isSelected ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

/// 品牌预设选择部分
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
          Text(
            '品牌预设',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: DS.md),
          Wrap(
            spacing: DS.md,
            runSpacing: DS.md,
            children: BrandPreset.values.map((preset) {
              final isSelected = currentPreset == preset;
              final presetName = preset.name.substring(0, 1).toUpperCase() +
                  preset.name.substring(1);

              return GestureDetector(
                onTap: () => onPresetChanged(preset),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.lg,
                    vertical: DS.md,
                  ),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: isSelected ? DS.brandPrimary : DS.brandPrimary30,
                      width: isSelected ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(DS.md),
                    color: isSelected
                        ? DS.brandPrimary12
                        : DS.surfacePrimary.withValues(alpha: 0),
                  ),
                  child: Text(
                    presetName,
                    style: TextStyle(
                      fontWeight:
                          isSelected ? FontWeight.w600 : FontWeight.normal,
                      color: isSelected
                          ? DS.brandPrimary
                          : Theme.of(context).textTheme.bodyMedium?.color,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      );
}

/// 高对比度模式部分
class _HighContrastSection extends StatelessWidget {
  const _HighContrastSection({
    required this.highContrast,
    required this.onToggled,
  });

  final bool highContrast;
  final void Function(bool) onToggled;

  @override
  Widget build(BuildContext context) => Container(
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '高对比度模式',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: DS.xs),
                Text(
                  '增强文字和背景的对比度',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ],
            ),
            Switch(
              value: highContrast,
              onChanged: onToggled,
              activeThumbColor: DS.brandPrimary,
            ),
          ],
        ),
      );
}

/// 恢复默认值按钮
class _ResetButton extends StatelessWidget {
  const _ResetButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: double.infinity,
        child: SparkleButton.outline(
          onPressed: onPressed,
          label: '恢复默认设置',
          expand: true,
        ),
      );
}

/// 颜色预览部分
class _ColorPreviewSection extends ConsumerWidget {
  const _ColorPreviewSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeManager = ref.watch(themeManagerProvider);
    final colors = themeManager.current.colors;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '颜色预览',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: DS.md),
        // Brand Colors
        Row(
          children: [
            Expanded(
              child: _ColorBox(
                color: colors.brandPrimary,
                label: '主色',
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: _ColorBox(
                color: colors.brandSecondary,
                label: '次色',
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.md),
        // Semantic Colors
        Row(
          children: [
            Expanded(
              child: _ColorBox(
                color: colors.semanticSuccess,
                label: '成功',
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: _ColorBox(
                color: colors.semanticWarning,
                label: '警告',
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: _ColorBox(
                color: colors.semanticError,
                label: '错误',
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.md),
        // Task Type Colors
        Text(
          '任务类型颜色',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
        const SizedBox(height: DS.md),
        Wrap(
          spacing: DS.md,
          runSpacing: DS.md,
          children: [
            _ColorBox(color: colors.taskLearning, label: '学习', size: 60),
            _ColorBox(color: colors.taskTraining, label: '训练', size: 60),
            _ColorBox(color: colors.taskErrorFix, label: '修复', size: 60),
            _ColorBox(color: colors.taskReflection, label: '反思', size: 60),
            _ColorBox(color: colors.taskSocial, label: '社交', size: 60),
            _ColorBox(color: colors.taskPlanning, label: '规划', size: 60),
          ],
        ),
      ],
    );
  }
}

/// 颜色展示框
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
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      );
}
