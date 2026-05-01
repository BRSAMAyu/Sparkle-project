import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_display_settings_provider.dart';

class GalaxySimulationSettingsSheet extends StatelessWidget {
  const GalaxySimulationSettingsSheet({
    required this.isDarkMode,
    required this.settings,
    required this.onTextFadeThresholdChanged,
    required this.onNodeSizeScaleChanged,
    required this.onLinkThicknessScaleChanged,
    required this.onCenterForceChanged,
    required this.onRepelForceChanged,
    required this.onLinkForceChanged,
    required this.onLinkDistanceChanged,
    required this.onReplaySpeedChanged,
    required this.onReset,
    super.key,
  });

  final bool isDarkMode;
  final GalaxyDisplaySettings settings;
  final ValueChanged<double> onTextFadeThresholdChanged;
  final ValueChanged<double> onNodeSizeScaleChanged;
  final ValueChanged<double> onLinkThicknessScaleChanged;
  final ValueChanged<double> onCenterForceChanged;
  final ValueChanged<double> onRepelForceChanged;
  final ValueChanged<double> onLinkForceChanged;
  final ValueChanged<double> onLinkDistanceChanged;
  final ValueChanged<double> onReplaySpeedChanged;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).padding.bottom;
    final maxSheetHeight = MediaQuery.of(context).size.height * 0.82;
    final backgroundColor = isDarkMode
        ? const Color(0xEE0E1523)
        : Colors.white.withValues(alpha: 0.95);
    final borderColor = isDarkMode
        ? Colors.white.withValues(alpha: 0.1)
        : Colors.black.withValues(alpha: 0.08);
    final titleColor = isDarkMode ? Colors.white : Colors.black87;
    final bodyColor = isDarkMode ? Colors.white70 : Colors.black54;

    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                backgroundColor,
                Color.alphaBlend(
                  const Color(0xFF6B8CFF)
                      .withValues(alpha: isDarkMode ? 0.08 : 0.04),
                  backgroundColor,
                ),
              ],
            ),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            border: Border(top: BorderSide(color: borderColor)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDarkMode ? 0.26 : 0.08),
                blurRadius: 26,
                offset: const Offset(0, -8),
              ),
            ],
          ),
          child: SafeArea(
            top: false,
            child: Padding(
              padding: EdgeInsets.fromLTRB(20, 16, 20, 20 + bottomInset),
              child: SizedBox(
                height: maxSheetHeight,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: Container(
                        width: 40,
                        height: 4,
                        decoration: BoxDecoration(
                          color: borderColor.withValues(alpha: 0.9),
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '星图视图设置',
                                style: TextStyle(
                                  color: titleColor,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '调节显示密度、力场参数与回放节奏，让星图浏览更顺手、更直观。',
                                style: TextStyle(
                                  color: bodyColor,
                                  fontSize: 12,
                                  height: 1.4,
                                ),
                              ),
                            ],
                          ),
                        ),
                        TextButton.icon(
                          onPressed: onReset,
                          icon: const Icon(Icons.restart_alt_rounded, size: 18),
                          label: const Text('恢复默认'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: SingleChildScrollView(
                        physics: const BouncingScrollPhysics(),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _SectionTitle(
                              title: '常用调整',
                              subtitle: '第一眼只保留最常用、最直接影响整体体验的四项。',
                              isDarkMode: isDarkMode,
                            ),
                            _SliderTile(
                              label: '中心吸引力',
                              valueLabel:
                                  settings.centerForce.toStringAsFixed(4),
                              value: settings.centerForce,
                              min: kGalaxyCenterForceMin,
                              max: kGalaxyCenterForceMax,
                              onChanged: onCenterForceChanged,
                            ),
                            _SliderTile(
                              label: '节点排斥力',
                              valueLabel:
                                  settings.repelForce.toStringAsFixed(0),
                              value: settings.repelForce,
                              min: kGalaxyRepelForceMin,
                              max: kGalaxyRepelForceMax,
                              onChanged: onRepelForceChanged,
                            ),
                            _SliderTile(
                              label: '连线牵引力',
                              valueLabel: settings.linkForce.toStringAsFixed(3),
                              value: settings.linkForce,
                              min: kGalaxyLinkForceMin,
                              max: kGalaxyLinkForceMax,
                              onChanged: onLinkForceChanged,
                            ),
                            _SliderTile(
                              label: '回放速度',
                              valueLabel:
                                  '${settings.replaySpeed.toStringAsFixed(1)}x',
                              value: settings.replaySpeed,
                              min: kGalaxyReplaySpeedMin,
                              max: kGalaxyReplaySpeedMax,
                              onChanged: onReplaySpeedChanged,
                            ),
                            const SizedBox(height: 12),
                            _SectionTitle(
                              title: '高级调整',
                              subtitle: '需要微调视觉密度时再展开，默认不用第一眼看到。',
                              isDarkMode: isDarkMode,
                            ),
                            _ExpandablePanel(
                              title: '展开高级选项',
                              isDarkMode: isDarkMode,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  _SliderTile(
                                    label: '文字显现阈值',
                                    valueLabel: settings.textFadeThreshold
                                        .toStringAsFixed(2),
                                    value: settings.textFadeThreshold,
                                    min: kGalaxyTextFadeThresholdMin,
                                    max: kGalaxyTextFadeThresholdMax,
                                    onChanged: onTextFadeThresholdChanged,
                                  ),
                                  _SliderTile(
                                    label: '节点尺寸',
                                    valueLabel:
                                        '${settings.nodeSizeScale.toStringAsFixed(2)}x',
                                    value: settings.nodeSizeScale,
                                    min: kGalaxyNodeSizeScaleMin,
                                    max: kGalaxyNodeSizeScaleMax,
                                    onChanged: onNodeSizeScaleChanged,
                                  ),
                                  _SliderTile(
                                    label: '连线粗细',
                                    valueLabel:
                                        '${settings.linkThicknessScale.toStringAsFixed(2)}x',
                                    value: settings.linkThicknessScale,
                                    min: kGalaxyLinkThicknessScaleMin,
                                    max: kGalaxyLinkThicknessScaleMax,
                                    onChanged: onLinkThicknessScaleChanged,
                                  ),
                                  _SliderTile(
                                    label: '连线距离',
                                    valueLabel: settings.linkDistance
                                        .toStringAsFixed(0),
                                    value: settings.linkDistance,
                                    min: kGalaxyLinkDistanceMin,
                                    max: kGalaxyLinkDistanceMax,
                                    onChanged: onLinkDistanceChanged,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.subtitle,
    required this.isDarkMode,
  });

  final String title;
  final String subtitle;
  final bool isDarkMode;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: isDarkMode ? Colors.white60 : Colors.black54,
                    height: 1.35,
                  ),
            ),
          ],
        ),
      );
}

class _SliderTile extends StatelessWidget {
  const _SliderTile({
    required this.label,
    required this.valueLabel,
    required this.value,
    required this.min,
    required this.max,
    required this.onChanged,
  });

  final String label;
  final String valueLabel;
  final double value;
  final double min;
  final double max;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Container(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
        decoration: BoxDecoration(
          color: Color.alphaBlend(
            colorScheme.primary.withValues(alpha: 0.03),
            Theme.of(context).colorScheme.surface,
          ),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: colorScheme.outlineVariant.withValues(alpha: 0.45),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                ),
                Text(
                  valueLabel,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: colorScheme.primary,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ],
            ),
            Slider(
              value: value.clamp(min, max),
              min: min,
              max: max,
              onChanged: onChanged,
            ),
          ],
        ),
      ),
    );
  }
}

class _ExpandablePanel extends StatelessWidget {
  const _ExpandablePanel({
    required this.title,
    required this.isDarkMode,
    required this.child,
  });

  final String title;
  final bool isDarkMode;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          colorScheme.primary.withValues(alpha: 0.03),
          Theme.of(context).colorScheme.surface,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: colorScheme.outlineVariant.withValues(alpha: 0.45),
        ),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 14),
          childrenPadding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
          iconColor: isDarkMode ? Colors.white70 : colorScheme.primary,
          collapsedIconColor: isDarkMode ? Colors.white54 : colorScheme.primary,
          title: Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          children: [child],
        ),
      ),
    );
  }
}
