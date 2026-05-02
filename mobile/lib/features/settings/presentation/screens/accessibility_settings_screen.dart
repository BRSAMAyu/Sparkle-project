import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

String _a11yCopy({required String zh, required String en}) =>
    I18nService.instance.isChinese ? zh : en;

class AccessibilitySettingsScreen extends ConsumerWidget {
  const AccessibilitySettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(accessibilitySettingsProvider);
    final notifier = ref.read(accessibilitySettingsProvider.notifier);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            final navigator = Navigator.of(context);
            if (navigator.canPop()) {
              navigator.pop();
            }
          },
        ),
        title: Text(
          _a11yCopy(
            zh: '无障碍与低负荷',
            en: 'Accessibility',
          ),
        ),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            semanticLabel: _a11yCopy(zh: '恢复默认', en: 'Reset'),
            icon: const Icon(Icons.restart_alt_rounded),
            onPressed: settings.isSaving
                ? null
                : () => unawaited(_reset(context, notifier)),
          ),
        ],
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
          children: [
            if (!settings.isLoaded) const LinearProgressIndicator(minHeight: 3),
            if (settings.lastError != null) ...[
              _StatusBanner(
                icon: Icons.sync_problem_rounded,
                text: _a11yCopy(
                  zh: '保存失败，已保留上一次设置。',
                  en: 'Save failed. Previous settings were restored.',
                ),
                isError: true,
              ),
              const SizedBox(height: DS.spacing12),
            ] else if (settings.isSaving) ...[
              _StatusBanner(
                icon: Icons.sync_rounded,
                text: _a11yCopy(zh: '正在同步到账号设置', en: 'Syncing settings'),
              ),
              const SizedBox(height: DS.spacing12),
            ],
            GraphiteCardSurface(
              child: _LowLoadSection(
                settings: settings,
                onChanged: (value) => unawaited(notifier.setLowLoadMode(value)),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            GraphiteCardSurface(
              child: _ReadingSection(
                settings: settings,
                onFontScaleChanged: (value) => unawaited(
                  notifier.patch(fontScale: value),
                ),
                onHighContrastChanged: (value) => unawaited(
                  notifier.patch(highContrast: value),
                ),
                onColorBlindChanged: (value) => unawaited(
                  notifier.patch(colorBlindFriendly: value),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            GraphiteCardSurface(
              child: _InteractionSection(
                settings: settings,
                onTouchTargetChanged: (value) => unawaited(
                  notifier.patch(touchTargetSize: value),
                ),
                onReduceMotionChanged: (value) => unawaited(
                  notifier.patch(reduceMotion: value),
                ),
                onHapticChanged: (value) => unawaited(
                  notifier.patch(hapticFeedback: value),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            GraphiteCardSurface(
              child: _AssistiveTechSection(
                settings: settings,
                onScreenReaderChanged: (value) => unawaited(
                  notifier.patch(screenReaderOptimized: value),
                ),
                onTtsChanged: (value) => unawaited(
                  notifier.patch(ttsEnabled: value),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            const GraphiteCardSurface(
              child: _WcagChecklistSection(),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _reset(
    BuildContext context,
    AccessibilitySettingsNotifier notifier,
  ) async {
    await notifier.reset();
    if (context.mounted) {
      AppFeedback.success(
        context,
        _a11yCopy(zh: '已恢复默认无障碍设置', en: 'Accessibility settings reset'),
      );
    }
  }
}

class _LowLoadSection extends StatelessWidget {
  const _LowLoadSection({
    required this.settings,
    required this.onChanged,
  });

  final AccessibilitySettings settings;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(
            icon: Icons.bolt_rounded,
            title: _a11yCopy(zh: '低负荷模式', en: 'Low-load mode'),
            subtitle: _a11yCopy(
              zh: '减少动效、放大触控区域，并优先使用更清晰的阅读节奏。',
              en: 'Reduces motion, enlarges touch targets, and favors calmer reading.',
            ),
          ),
          const SizedBox(height: DS.spacing8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              _a11yCopy(
                zh: '启用低负荷体验',
                en: 'Enable low-load experience',
              ),
            ),
            subtitle: Text(
              _a11yCopy(
                zh: '开启后会同步调整动画、屏幕阅读和触控默认值。',
                en: 'Also adjusts motion, screen reader, and touch defaults.',
              ),
            ),
            value: settings.lowLoadMode,
            onChanged: onChanged,
            activeThumbColor: DS.primaryBase,
          ),
        ],
      );
}

class _ReadingSection extends StatelessWidget {
  const _ReadingSection({
    required this.settings,
    required this.onFontScaleChanged,
    required this.onHighContrastChanged,
    required this.onColorBlindChanged,
  });

  final AccessibilitySettings settings;
  final ValueChanged<double> onFontScaleChanged;
  final ValueChanged<bool> onHighContrastChanged;
  final ValueChanged<bool> onColorBlindChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(
            icon: Icons.format_size_rounded,
            title: _a11yCopy(zh: '阅读与颜色', en: 'Reading and color'),
            subtitle: _a11yCopy(
              zh: '集中管理字体缩放、对比度和色盲友好配色。',
              en: 'Central controls for text scale, contrast, and color-safe palettes.',
            ),
          ),
          const SizedBox(height: DS.spacing12),
          _SliderRow(
            title: _a11yCopy(zh: '字体缩放', en: 'Font scale'),
            valueLabel: '${(settings.fontScale * 100).round()}%',
            child: Slider(
              value: settings.fontScale,
              min: 0.85,
              max: 1.4,
              divisions: 11,
              label: '${(settings.fontScale * 100).round()}%',
              onChanged: onFontScaleChanged,
            ),
          ),
          const Divider(height: DS.spacing24),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_a11yCopy(zh: '高对比度', en: 'High contrast')),
            subtitle: Text(
              _a11yCopy(
                zh: '优先使用更明显的文字、边框和状态区分。',
                en: 'Uses stronger text, borders, and state separation.',
              ),
            ),
            value: settings.highContrast,
            onChanged: onHighContrastChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_a11yCopy(zh: '色盲友好', en: 'Color-blind friendly')),
            subtitle: Text(
              _a11yCopy(
                zh: '用形状、明暗和标签辅助颜色差异。',
                en: 'Adds shape, tone, and labels where color carries meaning.',
              ),
            ),
            value: settings.colorBlindFriendly,
            onChanged: onColorBlindChanged,
            activeThumbColor: DS.primaryBase,
          ),
        ],
      );
}

class _InteractionSection extends StatelessWidget {
  const _InteractionSection({
    required this.settings,
    required this.onTouchTargetChanged,
    required this.onReduceMotionChanged,
    required this.onHapticChanged,
  });

  final AccessibilitySettings settings;
  final ValueChanged<TouchTargetSize> onTouchTargetChanged;
  final ValueChanged<bool> onReduceMotionChanged;
  final ValueChanged<bool> onHapticChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(
            icon: Icons.touch_app_rounded,
            title: _a11yCopy(zh: '触控与动效', en: 'Touch and motion'),
            subtitle: _a11yCopy(
              zh: '统一触控目标、动画减弱和震动反馈默认值。',
              en: 'Shared defaults for touch targets, reduced motion, and haptics.',
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            _a11yCopy(zh: '触控目标尺寸', en: 'Touch target size'),
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: TouchTargetSize.values
                .map(
                  (size) => ChoiceChip(
                    label: Text(_touchTargetLabel(size)),
                    selected: settings.touchTargetSize == size,
                    onSelected: (_) => onTouchTargetChanged(size),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: DS.spacing12),
          _TouchPreview(size: settings.minimumTouchTargetSize),
          const Divider(height: DS.spacing24),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_a11yCopy(zh: '减弱动画', en: 'Reduce motion')),
            subtitle: Text(
              _a11yCopy(
                zh: '缩短或移除非必要转场、粒子和弹性动画。',
                en: 'Shortens or removes nonessential transitions and effects.',
              ),
            ),
            value: settings.reduceMotion,
            onChanged: onReduceMotionChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_a11yCopy(zh: '震动反馈', en: 'Haptic feedback')),
            subtitle: Text(
              _a11yCopy(
                zh: '控制选择、确认和错误提示的触觉反馈。',
                en: 'Controls tactile feedback for selection, confirmation, and errors.',
              ),
            ),
            value: settings.hapticFeedback,
            onChanged: onHapticChanged,
            activeThumbColor: DS.primaryBase,
          ),
        ],
      );
}

class _AssistiveTechSection extends StatelessWidget {
  const _AssistiveTechSection({
    required this.settings,
    required this.onScreenReaderChanged,
    required this.onTtsChanged,
  });

  final AccessibilitySettings settings;
  final ValueChanged<bool> onScreenReaderChanged;
  final ValueChanged<bool> onTtsChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(
            icon: Icons.record_voice_over_rounded,
            title: _a11yCopy(zh: '辅助技术', en: 'Assistive technology'),
            subtitle: _a11yCopy(
              zh: '屏幕阅读优化与 TTS 默认值会同步给可视化与学习场景。',
              en: 'Screen reader and TTS defaults sync into visual and learning surfaces.',
            ),
          ),
          const SizedBox(height: DS.spacing8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title:
                Text(_a11yCopy(zh: '屏幕阅读优化', en: 'Screen reader optimization')),
            subtitle: Text(
              _a11yCopy(
                zh: '为图谱、卡片和复杂控件提供更完整的语义顺序。',
                en: 'Prioritizes semantic order for graphs, cards, and complex controls.',
              ),
            ),
            value: settings.screenReaderOptimized,
            onChanged: onScreenReaderChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(_a11yCopy(zh: 'TTS 朗读', en: 'TTS reading')),
            subtitle: Text(
              _a11yCopy(
                zh: '允许学习摘要、步骤和复盘内容进入朗读模式。',
                en: 'Allows summaries, steps, and reviews to enter read-aloud mode.',
              ),
            ),
            value: settings.ttsEnabled,
            onChanged: onTtsChanged,
            activeThumbColor: DS.primaryBase,
          ),
        ],
      );
}

class _WcagChecklistSection extends StatelessWidget {
  const _WcagChecklistSection();

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(
            icon: Icons.fact_check_rounded,
            title: _a11yCopy(zh: 'WCAG AA 检查', en: 'WCAG AA checks'),
            subtitle: _a11yCopy(
              zh: '本页控件按可触达、可读和可理解的设置面板标准维护。',
              en: 'This panel is maintained against operable, readable, and understandable checks.',
            ),
          ),
          const SizedBox(height: DS.spacing12),
          _ChecklistRow(
            text: _a11yCopy(
              zh: '正文与控件文字支持 200% 以内缩放',
              en: 'Text and controls support up to 200% user scaling',
            ),
          ),
          _ChecklistRow(
            text: _a11yCopy(
              zh: '触控目标不低于 48dp，且可提升至 64dp',
              en: 'Touch targets start at 48dp and can increase to 64dp',
            ),
          ),
          _ChecklistRow(
            text: _a11yCopy(
              zh: '颜色设置不依赖单一色相表达状态',
              en: 'Color options do not rely on hue alone for state',
            ),
          ),
          _ChecklistRow(
            text: _a11yCopy(
              zh: '屏幕阅读、TTS、动效和震动均可独立控制',
              en: 'Screen reader, TTS, motion, and haptics are independently controlled',
            ),
          ),
        ],
      );
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: DS.primaryBase),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                ),
              ],
            ),
          ),
        ],
      );
}

class _SliderRow extends StatelessWidget {
  const _SliderRow({
    required this.title,
    required this.valueLabel,
    required this.child,
  });

  final String title;
  final String valueLabel;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
              Text(
                valueLabel,
                style:
                    (Theme.of(context).textTheme.labelMedium ?? DS.labelSmall)
                        .copyWith(color: DS.primaryBase),
              ),
            ],
          ),
          child,
        ],
      );
}

class _TouchPreview extends StatelessWidget {
  const _TouchPreview({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Container(
            width: size,
            height: size,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: DS.primaryBase.withValues(alpha: 0.12),
              border: Border.all(color: DS.primaryBase),
              borderRadius: DS.borderRadius12,
            ),
            child: Icon(
              Icons.touch_app_rounded,
              color: DS.primaryBase,
              size: 22,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Text(
              _a11yCopy(
                zh: '当前最小目标 ${size.round()}dp',
                en: 'Current minimum target ${size.round()}dp',
              ),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ),
        ],
      );
}

class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.check_circle_rounded, size: 18),
            const SizedBox(width: DS.spacing8),
            Expanded(child: Text(text)),
          ],
        ),
      );
}

class _StatusBanner extends StatelessWidget {
  const _StatusBanner({
    required this.icon,
    required this.text,
    this.isError = false,
  });

  final IconData icon;
  final String text;
  final bool isError;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          borderRadius: DS.borderRadius12,
          color: isError
              ? DS.error.withValues(alpha: 0.1)
              : DS.primaryBase.withValues(alpha: 0.08),
          border: Border.all(
            color: isError
                ? DS.error.withValues(alpha: 0.4)
                : DS.primaryBase.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: isError ? DS.error : DS.primaryBase),
            const SizedBox(width: DS.spacing8),
            Expanded(child: Text(text)),
          ],
        ),
      );
}

String _touchTargetLabel(TouchTargetSize size) => switch (size) {
      TouchTargetSize.comfortable =>
        _a11yCopy(zh: '舒适 48dp', en: 'Comfort 48dp'),
      TouchTargetSize.large => _a11yCopy(zh: '加大 56dp', en: 'Large 56dp'),
      TouchTargetSize.extraLarge => _a11yCopy(zh: '特大 64dp', en: 'XL 64dp'),
    };
