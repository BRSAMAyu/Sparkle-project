import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

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
        title: Text(context.l10n.settA11yTitle),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            semanticLabel: context.l10n.settA11yReset,
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
                text: context.l10n.settA11ySaveFailed,
                isError: true,
              ),
              const SizedBox(height: DS.spacing12),
            ] else if (settings.isSaving) ...[
              _StatusBanner(
                icon: Icons.sync_rounded,
                text: context.l10n.settA11ySyncing,
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
      AppFeedback.success(context, context.l10n.settA11yResetDone);
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
            title: context.l10n.settA11yLowLoadTitle,
            subtitle: context.l10n.settA11yLowLoadDesc,
          ),
          const SizedBox(height: DS.spacing8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(context.l10n.settA11yLowLoadToggle),
            subtitle: Text(context.l10n.settA11yLowLoadToggleDesc),
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
            title: context.l10n.settA11yReadingTitle,
            subtitle: context.l10n.settA11yReadingDesc,
          ),
          const SizedBox(height: DS.spacing12),
          _SliderRow(
            title: context.l10n.settA11yFontScale,
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
            title: Text(context.l10n.settA11yHighContrast),
            subtitle: Text(context.l10n.settA11yHighContrastDesc),
            value: settings.highContrast,
            onChanged: onHighContrastChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(context.l10n.settA11yColorBlind),
            subtitle: Text(context.l10n.settA11yColorBlindDesc),
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
            title: context.l10n.settA11yTouchMotionTitle,
            subtitle: context.l10n.settA11yTouchMotionDesc,
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            context.l10n.settA11yTouchTargetSize,
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: TouchTargetSize.values
                .map(
                  (size) => ChoiceChip(
                    label: Text(_touchTargetLabel(context, size)),
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
            title: Text(context.l10n.settA11yReduceMotion),
            subtitle: Text(context.l10n.settA11yReduceMotionDesc),
            value: settings.reduceMotion,
            onChanged: onReduceMotionChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(context.l10n.settA11yHaptic),
            subtitle: Text(context.l10n.settA11yHapticDesc),
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
            title: context.l10n.settA11yAssistiveTitle,
            subtitle: context.l10n.settA11yAssistiveDesc,
          ),
          const SizedBox(height: DS.spacing8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(context.l10n.settA11yScreenReader),
            subtitle: Text(context.l10n.settA11yScreenReaderDesc),
            value: settings.screenReaderOptimized,
            onChanged: onScreenReaderChanged,
            activeThumbColor: DS.primaryBase,
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(context.l10n.settA11yTtsReading),
            subtitle: Text(context.l10n.settA11yTtsReadingDesc),
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
            title: context.l10n.settA11yWcagTitle,
            subtitle: context.l10n.settA11yWcagDesc,
          ),
          const SizedBox(height: DS.spacing12),
          _ChecklistRow(text: context.l10n.settA11yWcagTextScale),
          _ChecklistRow(text: context.l10n.settA11yWcagTouchTarget),
          _ChecklistRow(text: context.l10n.settA11yWcagColorState),
          _ChecklistRow(text: context.l10n.settA11yWcagIndependent),
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
              context.l10n.settA11yTouchPreview(size.round()),
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

String _touchTargetLabel(BuildContext context, TouchTargetSize size) =>
    switch (size) {
      TouchTargetSize.comfortable => context.l10n.settA11yTouchComfort,
      TouchTargetSize.large => context.l10n.settA11yTouchLarge,
      TouchTargetSize.extraLarge => context.l10n.settA11yTouchXl,
    };
