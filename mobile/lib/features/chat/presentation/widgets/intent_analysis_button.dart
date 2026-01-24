import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/presentation/widgets/intent_preview_dialog.dart';

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
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => _showIntentPreview(context),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Theme.of(context).primaryColor.withOpacity(0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: Theme.of(context).primaryColor.withOpacity(0.3),
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
              '分析意图',
              style: TextStyle(
                color: Theme.of(context).primaryColor,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showIntentPreview(BuildContext context) async {
    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => IntentPreviewDialog(
        message: message,
        onConfirm: onConfirm,
      ),
    );

    if (result == true) {
      onConfirm();
    }
  }
}

/// Intent Analysis Button for Chat Input
///
/// A smaller version that integrates directly into the chat input bar
class IntentAnalysisChip extends StatefulWidget {
  const IntentAnalysisChip({
    required this.message,
    required this.onAnalyzed,
    super.key,
  });

  final String message;
  final Function(List<IntentData> intents) onAnalyzed;

  @override
  State<IntentAnalysisChip> createState() => _IntentAnalysisChipState();
}

class _IntentAnalysisChipState extends State<IntentAnalysisChip> {
  bool _isAnalyzing = false;

  @override
  Widget build(BuildContext context) {
    if (_isAnalyzing) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Theme.of(context).primaryColor.withOpacity(0.1),
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
              '分析中...',
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
          color: Theme.of(context).primaryColor.withOpacity(0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: Theme.of(context).primaryColor.withOpacity(0.3),
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
              '多意图',
              style: TextStyle(
                color: Theme.of(context).primaryColor,
                fontSize: 12,
                fontWeight: FontWeight.w500,
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
      // Call API to analyze intents
      // This would integrate with your API client
      final intents = await _analyzeMessage(widget.message);

      if (mounted) {
        widget.onAnalyzed(intents);
        setState(() => _isAnalyzing = false);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isAnalyzing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('意图分析失败: $e')),
        );
      }
    }
  }

  Future<List<IntentData>> _analyzeMessage(String message) async {
    // TODO: Integrate with actual API
    // For now, return mock data
    await Future.delayed(const Duration(milliseconds: 500));

    return [
      IntentData(
        type: 'knowledge_query',
        confidence: 0.9,
        content: '复习Python闭包',
        agentRole: 'galaxy_guide',
      ),
      IntentData(
        type: 'time_planning',
        confidence: 0.85,
        content: '制定明天的学习计划',
        agentRole: 'time_tutor',
      ),
    ];
  }
}

/// Intent Data Model
class IntentData {
  IntentData({
    required this.type,
    required this.confidence,
    required this.content,
    this.agentRole,
    this.entities = const {},
  });

  final String type;
  final double confidence;
  final String content;
  final String? agentRole;
  final Map<String, dynamic> entities;
}
