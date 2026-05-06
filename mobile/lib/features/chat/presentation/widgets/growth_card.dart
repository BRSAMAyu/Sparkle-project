import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Growth Card — divine moment #1 "看见坚持"
///
/// Surfaces when the user achieves a significant streak or growth milestone.
/// Explains how the system's behavior changed (e.g., challenge level, tone,
/// reminders) while allowing the user to say "I'm actually tired."
class GrowthCard extends StatefulWidget {
  const GrowthCard({
    required this.title,
    required this.narrative,
    required this.streakDays,
    required this.strategyEffect,
    required this.isMilestone,
    required this.actions,
    required this.onAction,
    super.key,
  });

  final String title;
  final String narrative;
  final int streakDays;
  final String strategyEffect;
  final bool isMilestone;
  final List<String> actions;
  final ValueChanged<String> onAction;

  @override
  State<GrowthCard> createState() => _GrowthCardState();
}

class _GrowthCardState extends State<GrowthCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnim;
  late final Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _fadeAnim = CurvedAnimation(parent: _controller, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.06),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    _controller.forward();
    SensoryFeedbackService.emit(SensoryFeedbackEvent.achievementCommon);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: widget.title,
      child: FadeTransition(
      opacity: _fadeAnim,
      child: SlideTransition(
        position: _slideAnim,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: DS.surfaceHigh,
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color:
                  DS.success.withValues(alpha: widget.isMilestone ? 0.5 : 0.3),
            ),
            boxShadow: [
              BoxShadow(
                color: DS.success.withValues(alpha: 0.08),
                blurRadius: 12,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 8, 8),
                child: Row(
                  children: [
                    Icon(
                      widget.isMilestone
                          ? Icons.emoji_events_outlined
                          : Icons.local_fire_department_outlined,
                      size: 20,
                      color: DS.success,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        widget.title,
                        style: DS.titleMedium.copyWith(color: DS.textPrimary),
                      ),
                    ),
                    if (widget.streakDays > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: DS.success.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          context.l10n.chatGrowthStreakDays(widget.streakDays),
                          style: DS.labelSmall.copyWith(
                            color: DS.success,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              // Narrative
              if (widget.narrative.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                  child: Text(
                    widget.narrative,
                    style: DS.bodySmall.copyWith(color: DS.textSecondary),
                  ),
                ),
              // Strategy effect explanation
              if (widget.strategyEffect.isNotEmpty)
                Container(
                  margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: DS.success.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.tune, size: 14, color: DS.success),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          widget.strategyEffect,
                          style: DS.labelSmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              // Action chips
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
                child: Row(
                  children: widget.actions.map((action) {
                    final isDismiss = action.contains('累') ||
                        action.contains(context.l10n.chatNotNeeded);
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ActionChip(
                        label: Text(action),
                        labelStyle: DS.labelSmall.copyWith(
                          color: isDismiss ? DS.textSecondary : DS.success,
                        ),
                        backgroundColor: isDismiss
                            ? DS.surfaceSecondary
                            : DS.success.withValues(alpha: 0.1),
                        side: BorderSide(
                          color: isDismiss
                              ? DS.borderSubtle
                              : DS.success.withValues(alpha: 0.3),
                        ),
                        onPressed: () => widget.onAction(action),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        ),
      ),
      ),
    );
  }
}
