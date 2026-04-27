import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Strategy Intervention Card — divine moment #5 "阻止低收益"
///
/// Proactive risk warning that surfaces when Aurora detects the user's current
/// path has low ROI. Shown before the user wastes time, not after.
class StrategyInterventionCard extends StatefulWidget {
  const StrategyInterventionCard({
    required this.label,
    required this.reason,
    required this.suggestedAction,
    required this.onAdjust,
    required this.onDismiss,
    super.key,
  });

  final String label;
  final String reason;
  final String suggestedAction;
  final VoidCallback onAdjust;
  final VoidCallback onDismiss;

  @override
  State<StrategyInterventionCard> createState() =>
      _StrategyInterventionCardState();
}

class _StrategyInterventionCardState extends State<StrategyInterventionCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnim;
  late final Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 340),
    );
    _fadeAnim = CurvedAnimation(parent: _controller, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.06),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    _controller.forward();
    SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnim,
      child: SlideTransition(
        position: _slideAnim,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: DS.surfaceHigh,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: DS.warning.withValues(alpha: 0.3),
            ),
            boxShadow: [
              BoxShadow(
                color: DS.warning.withValues(alpha: 0.06),
                blurRadius: 10,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _Header(
                label: widget.label,
                onDismiss: widget.onDismiss,
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Divider(height: 1, color: DS.borderSubtle),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.priority_high_rounded,
                      size: 15,
                      color: DS.warning,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        widget.reason,
                        style: DS.labelSmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () {
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          );
                          widget.onAdjust();
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: DS.warning.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                              color: DS.warning.withValues(alpha: 0.25),
                            ),
                          ),
                          child: Center(
                            child: Text(
                              widget.suggestedAction,
                              style: DS.labelSmall.copyWith(
                                color: DS.warning,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: () {
                        SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
                        widget.onDismiss();
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: DS.surfaceHigh,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: DS.borderSubtle),
                        ),
                        child: Text(
                          '知道了',
                          style: DS.labelSmall.copyWith(
                            color: DS.textTertiary,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.label,
    required this.onDismiss,
  });

  final String label;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(5),
              decoration: BoxDecoration(
                color: DS.warning.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(7),
              ),
              child: Icon(
                Icons.shield_outlined,
                size: 15,
                color: DS.warning,
              ),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                label,
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            IconButton(
              icon: Icon(Icons.close, size: 15, color: DS.textTertiary),
              onPressed: onDismiss,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
            ),
          ],
        ),
      );
}
