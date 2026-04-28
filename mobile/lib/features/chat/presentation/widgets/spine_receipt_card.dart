import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Aurora Judgment-Correction Card — divine moment #2 "承认误判"
///
/// Displayed when the Spine orchestrator sends a UserVisibleReceipt via
/// metadata['spine_receipt']. Surfaces "因为X我调整了Y" to the user and
/// offers correction chips when correctable == true.
class SpineReceiptCard extends StatefulWidget {
  const SpineReceiptCard({
    required this.trigger,
    required this.summary,
    required this.correctable,
    required this.correctionOptions,
    required this.onCorrect,
    required this.onDismiss,
    super.key,
  });

  final String trigger;
  final String summary;
  final bool correctable;
  final List<String> correctionOptions;
  final void Function(String correction) onCorrect;
  final VoidCallback onDismiss;

  @override
  State<SpineReceiptCard> createState() => _SpineReceiptCardState();
}

class _SpineReceiptCardState extends State<SpineReceiptCard>
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
              color: DS.warning.withValues(alpha: 0.35),
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
              _Header(onDismiss: widget.onDismiss),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Divider(height: 1, color: DS.borderSubtle),
              ),
              _SummaryBody(summary: widget.summary),
              if (widget.correctable && widget.correctionOptions.isNotEmpty)
                _CorrectionRow(
                  options: widget.correctionOptions,
                  onSelected: (opt) {
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                    widget.onCorrect(opt);
                  },
                ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
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
                Icons.tune_rounded,
                size: 15,
                color: DS.warning,
              ),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                context.l10n.chatSpineSorryMistake,
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

class _SummaryBody extends StatelessWidget {
  const _SummaryBody({required this.summary});

  final String summary;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
        child: Text(
          summary,
          style: DS.labelSmall.copyWith(color: DS.textSecondary),
        ),
      );
}

class _CorrectionRow extends StatelessWidget {
  const _CorrectionRow({
    required this.options,
    required this.onSelected,
  });

  final List<String> options;
  final void Function(String) onSelected;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.chatSpineAccurateAsk,
              style: DS.labelSmall.copyWith(color: DS.textTertiary),
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: options
                  .map(
                    (opt) => _CorrectionChip(
                      label: opt,
                      onTap: () => onSelected(opt),
                    ),
                  )
                  .toList(),
            ),
          ],
        ),
      );
}

class _CorrectionChip extends StatelessWidget {
  const _CorrectionChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          decoration: BoxDecoration(
            color: DS.warning.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: DS.warning.withValues(alpha: 0.28),
            ),
          ),
          child: Text(
            label,
            style: DS.labelSmall.copyWith(
              color: DS.warning,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      );
}
