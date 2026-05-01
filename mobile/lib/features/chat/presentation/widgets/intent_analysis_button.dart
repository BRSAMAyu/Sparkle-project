import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/widgets/intent_preview_dialog.dart';
import 'package:sparkle/features/intent/data/models/intent_data.dart';
import 'package:sparkle/features/intent/data/repositories/intent_repository.dart';

/// Intent Analysis Button
///
/// A button that appears in the chat input area when the user's message
/// might contain multiple intents. Tapping it analyzes the message and
/// shows a preview of the detected intents.
class IntentAnalysisButton extends ConsumerWidget {
  const IntentAnalysisButton({
    required this.message,
    required this.onConfirm,
    super.key,
  });

  final String message;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context, WidgetRef ref) => InkWell(
        onTap: () => _showIntentPreview(context),
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Theme.of(context).primaryColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Theme.of(context).primaryColor.withValues(alpha: 0.3),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.auto_awesome,
                size: 16,
                color: Theme.of(context).primaryColor,
              ),
              const SizedBox(width: 6),
              Text(
                context.l10n.intentAnalysisLabel,
                style: TextStyle(
                  color: Theme.of(context).primaryColor,
                  fontSize: 13,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ],
          ),
        ),
      );

  Future<void> _showIntentPreview(BuildContext context) async {
    final result = await showSensoryModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (context) => IntentPreviewDialog(
        message: message,
        onConfirm: onConfirm,
      ),
    );

    if (result ?? false) {
      onConfirm();
    }
  }
}

/// Intent Analysis Button for Chat Input
///
/// A smaller version that integrates directly into the chat input bar
class IntentAnalysisChip extends ConsumerStatefulWidget {
  const IntentAnalysisChip({
    required this.message,
    required this.onAnalyzed,
    super.key,
  });

  final String message;
  final void Function(List<IntentData> intents) onAnalyzed;

  @override
  ConsumerState<IntentAnalysisChip> createState() => _IntentAnalysisChipState();
}

class _IntentAnalysisChipState extends ConsumerState<IntentAnalysisChip> {
  bool _isAnalyzing = false;

  @override
  Widget build(BuildContext context) {
    if (_isAnalyzing) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Theme.of(context).primaryColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Theme.of(context).primaryColor,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              context.l10n.intentAnalysisInProgress,
              style: TextStyle(
                color: Theme.of(context).primaryColor,
                fontSize: 12,
              ),
            ),
          ],
        ),
      );
    }

    return InkWell(
      onTap: _analyzeIntents,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Theme.of(context).primaryColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: Theme.of(context).primaryColor.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.auto_awesome,
              size: 14,
              color: Theme.of(context).primaryColor,
            ),
            const SizedBox(width: 6),
            Text(
              context.l10n.intentAnalysisMultiIntent,
              style: TextStyle(
                color: Theme.of(context).primaryColor,
                fontSize: 12,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _analyzeIntents() async {
    setState(() => _isAnalyzing = true);

    try {
      final repository = ref.read(intentRepositoryProvider);
      final response = await repository.previewIntents(widget.message);

      if (mounted) {
        widget.onAnalyzed(response.detectedIntents);
        setState(() => _isAnalyzing = false);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isAnalyzing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SparkleSnackBar.error(context.l10n.intentAnalysisFailed(e.toString())),
        );
      }
    }
  }
}
