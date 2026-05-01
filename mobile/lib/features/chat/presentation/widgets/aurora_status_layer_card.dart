import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Collapsible card used by the deep Aurora status layer.
class AuroraStatusLayerCard extends StatefulWidget {
  const AuroraStatusLayerCard({
    required this.title,
    required this.icon,
    required this.accentColor,
    required this.summary,
    required this.expandLabel,
    required this.collapseLabel,
    this.bullets = const [],
    this.confidenceLabel,
    this.initiallyExpanded = true,
    super.key,
  });

  final String title;
  final IconData icon;
  final Color accentColor;
  final String summary;
  final String? confidenceLabel;
  final List<String> bullets;
  final String expandLabel;
  final String collapseLabel;
  final bool initiallyExpanded;

  @override
  State<AuroraStatusLayerCard> createState() => _AuroraStatusLayerCardState();
}

class _AuroraStatusLayerCardState extends State<AuroraStatusLayerCard> {
  late bool _expanded;

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
  }

  @override
  Widget build(BuildContext context) {
    final semanticLabel = _expanded
        ? '${widget.title}. ${widget.collapseLabel}'
        : '${widget.title}. ${widget.expandLabel}';
    return Semantics(
      container: true,
      button: true,
      label: semanticLabel,
      onTap: () => setState(() => _expanded = !_expanded),
      child: ExcludeSemantics(
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          width: double.infinity,
          padding: const EdgeInsets.all(DS.spacing10),
          decoration: BoxDecoration(
            color: DS.surfacePrimary.withValues(alpha: 0.72),
            borderRadius: BorderRadius.circular(DS.radius8),
            border: Border.all(
              color: widget.accentColor.withValues(alpha: 0.24),
              width: 0.8,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              InkWell(
                borderRadius: BorderRadius.circular(DS.radius8),
                onTap: () => setState(() => _expanded = !_expanded),
                child: Row(
                  children: [
                    Icon(widget.icon, size: 15, color: widget.accentColor),
                    const SizedBox(width: DS.spacing6),
                    Expanded(
                      child: Text(
                        widget.title,
                        style: TextStyle(
                          color: DS.textPrimary,
                          fontSize: DS.fontSizeSm,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                      ),
                    ),
                    if (widget.confidenceLabel != null) ...[
                      Text(
                        widget.confidenceLabel!,
                        style: TextStyle(
                          color: widget.accentColor,
                          fontSize: 11,
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                      const SizedBox(width: DS.spacing4),
                    ],
                    Tooltip(
                      message:
                          _expanded ? widget.collapseLabel : widget.expandLabel,
                      child: Icon(
                        _expanded
                            ? Icons.expand_less_rounded
                            : Icons.expand_more_rounded,
                        size: 18,
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              AnimatedCrossFade(
                firstChild: const SizedBox.shrink(),
                secondChild: Padding(
                  padding: const EdgeInsets.only(top: DS.spacing8),
                  child: _ExpandedCardBody(
                    summary: widget.summary,
                    bullets: widget.bullets,
                    accentColor: widget.accentColor,
                  ),
                ),
                crossFadeState: _expanded
                    ? CrossFadeState.showSecond
                    : CrossFadeState.showFirst,
                duration: const Duration(milliseconds: 180),
                firstCurve: Curves.easeOutCubic,
                secondCurve: Curves.easeOutCubic,
                sizeCurve: Curves.easeOutCubic,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExpandedCardBody extends StatelessWidget {
  const _ExpandedCardBody({
    required this.summary,
    required this.bullets,
    required this.accentColor,
  });

  final String summary;
  final List<String> bullets;
  final Color accentColor;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            summary,
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: DS.fontSizeXs,
              height: 1.38,
            ),
          ),
          if (bullets.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: bullets
                  .take(4)
                  .map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 5,
                            height: 5,
                            margin: const EdgeInsets.only(
                              top: 6,
                              right: DS.spacing6,
                            ),
                            decoration: BoxDecoration(
                              color: accentColor.withValues(alpha: 0.72),
                              shape: BoxShape.circle,
                            ),
                          ),
                          Expanded(
                            child: Text(
                              item,
                              style: TextStyle(
                                color: DS.textSecondary,
                                fontSize: 11,
                                height: 1.35,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      );
}
