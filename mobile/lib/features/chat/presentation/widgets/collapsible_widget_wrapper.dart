import 'dart:collection';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// A collapsible wrapper for metadata widgets rendered after AI messages.
///
/// Default state: collapsed — shows a compact chip with icon + label.
/// Tapped: expands to reveal the full widget content.
/// Has a collapse button (top-right) when expanded.
class CollapsibleWidgetWrapper extends StatefulWidget {
  const CollapsibleWidgetWrapper({
    required this.label,
    required this.icon,
    required this.child,
    super.key,
    this.accentColor,
    this.defaultExpanded = false,
    this.persistId,
  });

  /// Short label shown on the collapsed chip, e.g. "任务", "计划", context.l10n.chatWidgetCognitiveAnalysis.
  final String label;

  /// Icon shown on the collapsed chip.
  final IconData icon;

  /// The full widget content revealed when expanded.
  final Widget child;

  /// Optional accent color for the chip border/icon tint.
  final Color? accentColor;

  /// Whether the widget starts expanded. Defaults to collapsed.
  final bool defaultExpanded;

  /// Optional stable identifier so expanded state is remembered across
  /// parent rebuilds within the same session, even when the widget key changes.
  final String? persistId;

  @override
  State<CollapsibleWidgetWrapper> createState() =>
      _CollapsibleWidgetWrapperState();
}

class _CollapsibleWidgetWrapperState extends State<CollapsibleWidgetWrapper>
    with SingleTickerProviderStateMixin {
  static const _animationDuration = Duration(milliseconds: 200);
  static final LinkedHashMap<String, bool> _persistedState = LinkedHashMap();
  static const int _maxEntries = 100;

  static void _putState(String key, bool value) {
    if (_persistedState.length >= _maxEntries && !_persistedState.containsKey(key)) {
      _persistedState.remove(_persistedState.keys.first);
    }
    _persistedState[key] = value;
  }

  @override
  Widget build(BuildContext context) {
    final accent = widget.accentColor ?? Theme.of(context).colorScheme.primary;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedSize(
      duration: _animationDuration,
      curve: Curves.easeInOutCubic,
      alignment: Alignment.topCenter,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Collapsed chip / expand-collapse header
          Material(
            color: Colors.transparent,
            child: Semantics(
              button: true,
              label: 'Chat collapsible widget wrapper control 1',
              child: InkWell(
                onTap: () async {
                  await SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                  _setExpanded(!_expanded);
                },
                borderRadius: BorderRadius.circular(999),
                child: AnimatedContainer(
                  duration: _animationDuration,
                  padding: EdgeInsets.symmetric(
                    horizontal: _expanded ? DS.spacing12 : DS.spacing8,
                    vertical: _expanded ? DS.spacing6 : DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: _expanded
                        ? accent.withValues(alpha: isDark ? 0.16 : 0.10)
                        : DS.surfacePanel,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                      color: _expanded
                          ? accent.withValues(alpha: 0.35)
                          : DS.borderSubtle,
                      width: _expanded ? 1.2 : 1.0,
                    ),
                    boxShadow: _expanded && !isDark
                        ? [
                            BoxShadow(
                              color: accent.withValues(alpha: 0.12),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ]
                        : null,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        widget.icon,
                        size: 14,
                        color: _expanded ? accent : DS.textSecondary,
                      ),
                      const SizedBox(width: DS.spacing6),
                      Text(
                        widget.label,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              fontSize: DS.fontSizeXs,
                              color: _expanded ? accent : DS.textSecondary,
                              fontWeight: _expanded
                                  ? DS.fontWeightSemibold
                                  : DS.fontWeightMedium,
                            ),
                      ),
                      const SizedBox(width: DS.spacing4),
                      AnimatedRotation(
                        duration: _animationDuration,
                        turns: _expanded ? 0.5 : 0,
                        child: Icon(
                          Icons.keyboard_arrow_down,
                          size: 14,
                          color: _expanded ? accent : DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Expanded content
          if (_expanded) ...[
            const SizedBox(height: DS.sm),
            Stack(
              children: [
                DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: accent.withValues(alpha: 0.12),
                    ),
                    borderRadius: BorderRadius.circular(DS.spacing10),
                  ),
                  child: widget.child,
                ),
                // Collapse button — top-right
                Positioned(
                  top: DS.spacing4,
                  right: DS.spacing4,
                  child: Material(
                    color: Colors.transparent,
                    child: Semantics(
                      button: true,
                      label: 'Chat collapsible widget wrapper control 2',
                      child: InkWell(
                        onTap: () => _setExpanded(false),
                        borderRadius: BorderRadius.circular(999),
                        child: Container(
                          padding: const EdgeInsets.all(DS.spacing4),
                          decoration: BoxDecoration(
                            color: DS.surfacePanel.withValues(alpha: 0.9),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            Icons.close,
                            size: 14,
                            color: DS.textSecondary,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  bool _expanded = false;
  String? _effectivePersistId;

  @override
  void initState() {
    super.initState();
    _resolvePersistState();
  }

  @override
  void didUpdateWidget(covariant CollapsibleWidgetWrapper oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.persistId != widget.persistId ||
        oldWidget.label != widget.label) {
      _resolvePersistState();
    }
  }

  void _resolvePersistState() {
    final id = widget.persistId ?? '${widget.label}_${widget.icon.codePoint}';
    _effectivePersistId = id;
    _expanded = _persistedState[id] ?? widget.defaultExpanded;
  }

  void _setExpanded(bool value) {
    setState(() => _expanded = value);
    if (_effectivePersistId != null) {
      _putState(_effectivePersistId!, value);
    }
  }
}
