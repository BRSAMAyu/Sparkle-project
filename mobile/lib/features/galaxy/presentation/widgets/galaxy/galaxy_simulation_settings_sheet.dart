import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class GalaxySimulationSettingsSheet extends StatelessWidget {
  const GalaxySimulationSettingsSheet({
    required this.isDarkMode,
    required this.springStrength,
    required this.repulsionStrength,
    required this.centerGravity,
    required this.replaySpeed,
    required this.onSpringChanged,
    required this.onRepulsionChanged,
    required this.onCenterGravityChanged,
    required this.onReplaySpeedChanged,
    required this.onReset,
    super.key,
  });

  final bool isDarkMode;
  final double springStrength;
  final double repulsionStrength;
  final double centerGravity;
  final double replaySpeed;
  final ValueChanged<double> onSpringChanged;
  final ValueChanged<double> onRepulsionChanged;
  final ValueChanged<double> onCenterGravityChanged;
  final ValueChanged<double> onReplaySpeedChanged;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
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
            color: backgroundColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            border: Border(top: BorderSide(color: borderColor)),
          ),
          child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
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
                              l10n.galaxySimulationTitle,
                              style: TextStyle(
                                color: titleColor,
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              l10n.galaxySimulationSubtitle,
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
                        label: Text(l10n.galaxySimulationReset),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _SliderTile(
                    label: l10n.galaxySimulationGravity,
                    valueLabel: springStrength.toStringAsFixed(3),
                    value: springStrength,
                    min: 0.02,
                    max: 0.09,
                    onChanged: onSpringChanged,
                  ),
                  _SliderTile(
                    label: l10n.galaxySimulationRepulsion,
                    valueLabel: repulsionStrength.toStringAsFixed(0),
                    value: repulsionStrength,
                    min: 6000,
                    max: 22000,
                    onChanged: onRepulsionChanged,
                  ),
                  _SliderTile(
                    label: l10n.galaxySimulationCenterGravity,
                    valueLabel: centerGravity.toStringAsFixed(4),
                    value: centerGravity,
                    min: 0.0006,
                    max: 0.004,
                    onChanged: onCenterGravityChanged,
                  ),
                  _SliderTile(
                    label: l10n.galaxySimulationReplaySpeed,
                    valueLabel: '${replaySpeed.toStringAsFixed(1)}x',
                    value: replaySpeed,
                    min: 0.4,
                    max: 2.4,
                    onChanged: onReplaySpeedChanged,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  label,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              Text(
                valueLabel,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: colorScheme.primary,
                      fontWeight: FontWeight.w700,
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
    );
  }
}
