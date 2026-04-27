import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Goal Arbitration Card — multi-goal conflict surface
///
/// Shown when Aurora detects the user has multiple active goals competing for
/// attention. Surfaces the recommended focus priority and time split so the
/// user can make an informed choice rather than context-switching blindly.
class GoalArbitrationCard extends StatefulWidget {
  const GoalArbitrationCard({
    required this.primaryGoalTitle,
    required this.reason,
    required this.goals,
    required this.conflicts,
    required this.onFocusPrimary,
    required this.onContinueMulti,
    required this.onDismiss,
    super.key,
  });

  final String primaryGoalTitle;
  final String reason;

  /// Ordered by priority. Each map: {goal_id, title, time_fraction, score}.
  final List<Map<String, dynamic>> goals;
  final List<String> conflicts;
  final VoidCallback onFocusPrimary;
  final VoidCallback onContinueMulti;
  final VoidCallback onDismiss;

  @override
  State<GoalArbitrationCard> createState() => _GoalArbitrationCardState();
}

class _GoalArbitrationCardState extends State<GoalArbitrationCard>
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
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));
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
            border: Border.all(color: DS.warning.withValues(alpha: 0.35)),
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
              _Header(onDismiss: widget.onDismiss),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Divider(height: 1, color: DS.borderSubtle),
              ),
              if (widget.reason.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
                  child: Text(
                    widget.reason,
                    style: DS.labelSmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
                  ),
                ),
              if (widget.conflicts.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 6, 16, 0),
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: widget.conflicts
                        .map((c) => _ConflictPill(label: _conflictLabel(c)))
                        .toList(),
                  ),
                ),
              if (widget.goals.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '推荐时间分配',
                        style: DS.labelSmall.copyWith(
                          color: DS.textTertiary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 8),
                      ...widget.goals.asMap().entries.map(
                            (e) => _GoalRow(
                              index: e.key,
                              data: e.value,
                              isPrimary: e.value['goal_id'] ==
                                  _primaryGoalId(),
                            ),
                          ),
                    ],
                  ),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 14, 12, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: _ActionButton(
                        label: '专注主目标',
                        color: DS.warning,
                        onTap: () {
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          );
                          widget.onFocusPrimary();
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _ActionButton(
                        label: '继续多线推进',
                        color: DS.textTertiary,
                        outlined: true,
                        onTap: () {
                          SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
                          widget.onContinueMulti();
                        },
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

  String? _primaryGoalId() {
    try {
      return widget.goals
          .reduce(
            (a, b) =>
                (a['score'] as num) >= (b['score'] as num) ? a : b,
          )['goal_id']
          ?.toString();
    } catch (_) {
      return null;
    }
  }

  String _conflictLabel(String key) {
    switch (key) {
      case 'multiple_urgent_deadlines':
        return '多个紧急截止';
      case 'bottleneck_goals_exist':
        return '存在瓶颈目标';
      case 'stalled_goals_exist':
        return '存在停滞目标';
      default:
        return key.replaceAll('_', ' ');
    }
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.onDismiss});
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
                Icons.account_tree_outlined,
                size: 15,
                color: DS.warning,
              ),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                '多目标冲突检测',
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

class _GoalRow extends StatelessWidget {
  const _GoalRow({
    required this.index,
    required this.data,
    required this.isPrimary,
  });

  final int index;
  final Map<String, dynamic> data;
  final bool isPrimary;

  @override
  Widget build(BuildContext context) {
    final title = data['title']?.toString() ?? '';
    final fraction = (data['time_fraction'] as num?)?.toDouble() ?? 0.0;
    final pct = (fraction * 100).round();

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          if (isPrimary)
            Icon(Icons.star_rounded, size: 13, color: DS.warning)
          else
            Icon(Icons.circle, size: 7, color: DS.textTertiary),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: DS.labelSmall.copyWith(
                          color:
                              isPrimary ? DS.textPrimary : DS.textSecondary,
                          fontWeight: isPrimary
                              ? FontWeight.w600
                              : FontWeight.w400,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Text(
                      '$pct%',
                      style: DS.labelSmall.copyWith(
                        color: isPrimary ? DS.warning : DS.textTertiary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: fraction.clamp(0.0, 1.0),
                    minHeight: 4,
                    backgroundColor: DS.borderSubtle,
                    valueColor: AlwaysStoppedAnimation(
                      isPrimary
                          ? DS.warning
                          : DS.warning.withValues(alpha: 0.35),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ConflictPill extends StatelessWidget {
  const _ConflictPill({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: DS.warning.withValues(alpha: 0.25)),
        ),
        child: Text(
          label,
          style: DS.labelSmall.copyWith(
            color: DS.warning,
            fontSize: 10,
            fontWeight: FontWeight.w500,
          ),
        ),
      );
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.color,
    required this.onTap,
    this.outlined = false,
  });

  final String label;
  final Color color;
  final VoidCallback onTap;
  final bool outlined;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: outlined ? DS.surfaceHigh : color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: outlined
                  ? DS.borderSubtle
                  : color.withValues(alpha: 0.25),
            ),
          ),
          child: Center(
            child: Text(
              label,
              style: DS.labelSmall.copyWith(
                color: outlined ? DS.textTertiary : color,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ),
      );
}
