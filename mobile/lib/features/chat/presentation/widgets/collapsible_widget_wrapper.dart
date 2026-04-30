import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

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

  @override
  State<CollapsibleWidgetWrapper> createState() =>
      _CollapsibleWidgetWrapperState();
}

class _CollapsibleWidgetWrapperState extends State<CollapsibleWidgetWrapper>
    with SingleTickerProviderStateMixin {
  static const _animationDuration = Duration(milliseconds: 200);

  @override
  Widget build(BuildContext context) {
    final accent =
        widget.accentColor ?? Theme.of(context).colorScheme.primary;
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
            child: InkWell(
              onTap: () => setState(() {
                _expanded = !_expanded;
              }),
              borderRadius: BorderRadius.circular(999),
              child: AnimatedContainer(
                duration: _animationDuration,
                padding: EdgeInsets.symmetric(
                  horizontal: _expanded ? DS.spacing10 : DS.spacing10,
                  vertical: DS.spacing6,
                ),
                decoration: BoxDecoration(
                  color: _expanded
                      ? accent.withValues(alpha: isDark ? 0.12 : 0.08)
                      : DS.surfacePanel,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(
                    color: _expanded
                        ? accent.withValues(alpha: 0.26)
                        : DS.borderSubtle,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      widget.icon,
                      size: 14,
                      color: _expanded
                          ? accent
                          : DS.textSecondary,
                    ),
                    const SizedBox(width: DS.spacing6),
                    Text(
                      widget.label,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            fontSize: DS.fontSizeXs,
                            color: _expanded
                                ? accent
                                : DS.textSecondary,
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
                        color: _expanded
                            ? accent
                            : DS.textSecondary,
                      ),
                    ),
                  ],
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
                    child: InkWell(
                      onTap: () => setState(() {
                        _expanded = false;
                      }),
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
              ],
            ),
          ],
        ],
      ),
    );
  }

  bool _expanded = false;

  @override
  void initState() {
    super.initState();
    _expanded = widget.defaultExpanded;
  }
}
