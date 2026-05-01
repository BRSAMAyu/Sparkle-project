import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Community Insight Card — divine moment #6 "社群经验转策略"
///
/// Surfaces anonymous cohort mistakes or partner observations as in-chat
/// strategy nudges. Privacy-safe: individual identities are never revealed.
class CommunityInsightCard extends StatefulWidget {
  const CommunityInsightCard({
    required this.hintType,
    required this.title,
    required this.anonymousSummary,
    required this.tip,
    required this.onApply,
    required this.onDismiss,
    super.key,
  });

  final String hintType;
  final String title;
  final String anonymousSummary;
  final String tip;
  final VoidCallback onApply;
  final VoidCallback onDismiss;

  @override
  State<CommunityInsightCard> createState() => _CommunityInsightCardState();
}

class _CommunityInsightCardState extends State<CommunityInsightCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnim;
  late final Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 360),
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

  IconData get _icon {
    switch (widget.hintType) {
      case 'partner_feedback':
        return Icons.people_outline_rounded;
      default:
        return Icons.group_outlined;
    }
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
              color: DS.info.withValues(alpha: 0.3),
            ),
            boxShadow: [
              BoxShadow(
                color: DS.info.withValues(alpha: 0.05),
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
                icon: _icon,
                title: widget.title,
                onDismiss: widget.onDismiss,
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Divider(height: 1, color: DS.borderSubtle),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
                child: Text(
                  widget.anonymousSummary,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: DS.labelSmall.copyWith(color: DS.textSecondary),
                ),
              ),
              if (widget.tip.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.lightbulb_outline,
                        size: 13,
                        color: DS.info,
                      ),
                      const SizedBox(width: 5),
                      Expanded(
                        child: Text(
                          widget.tip,
                          style: DS.labelSmall.copyWith(
                            color: DS.textSecondary,
                            fontStyle: FontStyle.italic,
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
                      child: Semantics(
                        button: true,
                        label: 'Chat community insight card control 1',
                        child: GestureDetector(
                          onTap: () {
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            );
                            widget.onApply();
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            decoration: BoxDecoration(
                              color: DS.info.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: DS.info.withValues(alpha: 0.25),
                              ),
                            ),
                            child: Center(
                              child: Text(
                                context.l10n.chatCommunityInsightRefer,
                                style: DS.labelSmall.copyWith(
                                  color: DS.info,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Semantics(
                      button: true,
                      label: 'Chat community insight card control 2',
                      child: GestureDetector(
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
                            '忽略',
                            style: DS.labelSmall.copyWith(
                              color: DS.textTertiary,
                            ),
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
    required this.icon,
    required this.title,
    required this.onDismiss,
  });

  final IconData icon;
  final String title;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(5),
              decoration: BoxDecoration(
                color: DS.info.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(7),
              ),
              child: Icon(icon, size: 15, color: DS.info),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                title,
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Semantics(
              button: true,
              label: 'Chat community insight card control 3',
              child: IconButton(
                icon: Icon(Icons.close, size: 15, color: DS.textTertiary),
                onPressed: onDismiss,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
              ),
            ),
          ],
        ),
      );
}
