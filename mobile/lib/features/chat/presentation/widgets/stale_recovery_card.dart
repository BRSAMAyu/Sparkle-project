import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Time-Aware Recovery Card — divine moment #4 "记得时间"
///
/// Displayed when StaleStateGuard detects user return after >60 min.
/// Shows elapsed time and 4 resume options so the user feels understood.
class StaleRecoveryCard extends StatefulWidget {
  const StaleRecoveryCard({
    required this.elapsedMinutes,
    required this.pendingTaskStatus,
    required this.resumeOptions,
    required this.onOptionSelected,
    required this.onDismiss,
    super.key,
  });

  final int elapsedMinutes;
  final String pendingTaskStatus;
  final List<String> resumeOptions;
  final void Function(String option) onOptionSelected;
  final VoidCallback onDismiss;

  @override
  State<StaleRecoveryCard> createState() => _StaleRecoveryCardState();
}

class _StaleRecoveryCardState extends State<StaleRecoveryCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnim;
  late final Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 380),
    );
    _fadeAnim = CurvedAnimation(parent: _controller, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.08),
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

  String get _elapsedLabel {
    if (widget.elapsedMinutes < 60) return context.l10n.chatStaleMinutes(widget.elapsedMinutes);
    if (widget.elapsedMinutes >= 1440) {
      final days = widget.elapsedMinutes ~/ 1440;
      final remaining = widget.elapsedMinutes % 1440;
      final hours = remaining ~/ 60;
      return hours > 0 ? context.l10n.chatStaleDaysHours(days, hours) : context.l10n.chatStaleDaysOnly(days);
    }
    final hours = widget.elapsedMinutes ~/ 60;
    final mins = widget.elapsedMinutes % 60;
    return mins > 0 ? context.l10n.chatStaleHoursMins(hours, mins) : context.l10n.chatStaleHoursOnly(hours);
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
        opacity: _fadeAnim,
        child: SlideTransition(
          position: _slideAnim,
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: DS.surfaceHigh,
              borderRadius: BorderRadius.circular(16),
              border:
                  Border.all(color: DS.brandPrimary.withValues(alpha: 0.3)),
              boxShadow: [
                BoxShadow(
                  color: DS.brandPrimary.withValues(alpha: 0.06),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _Header(
                  elapsedLabel: _elapsedLabel,
                  onDismiss: widget.onDismiss,
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Divider(height: 1, color: DS.borderSubtle),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
                  child: Text(
                    context.l10n.chatStaleLastTaskProgress,
                    style: DS.labelSmall.copyWith(color: DS.textSecondary),
                  ),
                ),
                _OptionsRow(
                  options: widget.resumeOptions,
                  onSelected: (opt) {
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                    widget.onOptionSelected(opt);
                  },
                ),
                const SizedBox(height: 12),
              ],
            ),
          ),
        ),
      );
}

class _Header extends StatelessWidget {
  const _Header({required this.elapsedLabel, required this.onDismiss});

  final String elapsedLabel;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 8, 0),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                Icons.access_time_rounded,
                size: 16,
                color: DS.brandPrimary,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                context.l10n.chatStaleWelcomeBack(elapsedLabel),
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            IconButton(
              icon: Icon(Icons.close, size: 16, color: DS.textTertiary),
              onPressed: onDismiss,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
            ),
          ],
        ),
      );
}

class _OptionsRow extends StatelessWidget {
  const _OptionsRow({required this.options, required this.onSelected});

  final List<String> options;
  final void Function(String) onSelected;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options
              .map(
                (opt) =>
                    _OptionChip(label: opt, onTap: () => onSelected(opt)),
              )
              .toList(),
        ),
      );
}

class _OptionChip extends StatelessWidget {
  const _OptionChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.25),
            ),
          ),
          child: Text(
            label,
            style: DS.labelSmall.copyWith(
              color: DS.brandPrimary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      );
}
