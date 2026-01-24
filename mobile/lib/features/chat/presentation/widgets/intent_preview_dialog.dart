import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/intent/data/models/intent_data.dart';
import 'package:sparkle/features/intent/data/repositories/intent_repository.dart';

/// Intent Preview Dialog
///
/// Shows a preview of detected intents in the user's message
/// before execution. Allows the user to confirm or modify.
class IntentPreviewDialog extends ConsumerStatefulWidget {
  const IntentPreviewDialog({
    required this.message,
    required this.onConfirm,
    super.key,
  });

  final String message;
  final VoidCallback onConfirm;

  @override
  ConsumerState<IntentPreviewDialog> createState() => _IntentPreviewDialogState();
}

class _IntentPreviewDialogState extends ConsumerState<IntentPreviewDialog> {
  bool _isAnalyzing = true;
  bool _isExecuting = false;
  List<IntentData> _intents = [];
  String? _errorMessage;
  String? _executionPlan;
  int? _estimatedTime;

  @override
  void initState() {
    super.initState();
    _analyzeIntents();
  }

  @override
  Widget build(BuildContext context) => Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          _buildHeader(),

          // Content
          Flexible(
            child: _buildContent(),
          ),

          // Actions
          _buildActions(),
        ],
      ),
    );

  Widget _buildHeader() => Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: Colors.grey[200]!,
          ),
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.auto_awesome, color: Colors.blue),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              '意图分析',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );

  Widget _buildContent() {
    if (_isAnalyzing) {
      return const SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text('正在分析意图...'),
            ],
          ),
        ),
      );
    }

    if (_errorMessage != null) {
      return SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, color: Colors.red, size: 48),
              const SizedBox(height: 16),
              Text(_errorMessage!),
              const SizedBox(height: 16),
              TextButton(
                onPressed: _analyzeIntents,
                child: const Text('重试'),
              ),
            ],
          ),
        ),
      );
    }

    if (_intents.isEmpty) {
      return SizedBox(
        height: 200,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.info_outline, color: Colors.blue, size: 48),
              const SizedBox(height: 16),
              const Text('识别到单一意图'),
              const SizedBox(height: 8),
              Text(
                '"${widget.message}"',
                style: const TextStyle(
                  color: Colors.grey,
                  fontStyle: FontStyle.italic,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '识别到 ${_intents.length} 个意图：',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 12),
          ...List.generate(_intents.length, (index) => _buildIntentItem(_intents[index], index + 1)),
          const SizedBox(height: 12),
          _buildExecutionPlan(),
        ],
      ),
    );
  }

  Widget _buildIntentItem(IntentData intent, int index) => Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _getIntentColor(intent.type).withValues(alpha: 0.3),
          width: 2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _getIntentColor(intent.type),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '#$index',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _getIntentLabel(intent.type),
                  style: const TextStyle(
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: _getConfidenceColor(intent.confidence),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${(intent.confidence * 100).toInt()}%',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            intent.content,
            style: const TextStyle(fontSize: 14),
          ),
          if (intent.agentRole != null) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(Icons.person, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(
                  '助手: ${_getAgentRoleLabel(intent.agentRole!)}',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );

  Widget _buildExecutionPlan() {
    final planText = _executionPlan ?? _generateExecutionPlan();
    final timeText = _estimatedTime != null ? ' (约 ${_estimatedTime!} 秒)' : '';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue[50],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.schedule, size: 16, color: Colors.blue[700]),
              const SizedBox(width: 8),
              Text(
                '执行计划$timeText',
                style: TextStyle(
                  color: Colors.blue[700],
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            planText,
            style: const TextStyle(fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildActions() => Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: Colors.grey[200]!,
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('取消'),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: ElevatedButton(
              onPressed: _isExecuting ? null : _executeIntents,
              child: _isExecuting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('确认执行'),
            ),
          ),
        ],
      ),
    );

  Color _getIntentColor(String type) {
    switch (type) {
      case 'task_management':
        return Colors.orange;
      case 'knowledge_query':
        return Colors.blue;
      case 'time_planning':
        return Colors.green;
      case 'social':
        return Colors.purple;
      case 'learning':
        return Colors.teal;
      case 'reflection':
        return Colors.indigo;
      case 'tool_call':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return Colors.green;
    if (confidence >= 0.6) return Colors.orange;
    return Colors.red;
  }

  String _getIntentLabel(String type) {
    switch (type) {
      case 'task_management':
        return '任务管理';
      case 'knowledge_query':
        return '知识查询';
      case 'time_planning':
        return '时间规划';
      case 'social':
        return '社交互动';
      case 'learning':
        return '学习内容';
      case 'reflection':
        return '复习反思';
      case 'tool_call':
        return '工具调用';
      default:
        return '未知';
    }
  }

  String _getAgentRoleLabel(String role) {
    switch (role) {
      case 'galaxy_guide':
        return '星图向导';
      case 'time_tutor':
        return '时间导师';
      case 'exam_oracle':
        return '考试预言家';
      case 'study_buddy':
        return '学习伙伴';
      default:
        return role;
    }
  }

  String _generateExecutionPlan() {
    if (_intents.isEmpty) return '直接执行';

    final buffer = StringBuffer();
    for (var i = 0; i < _intents.length; i++) {
      if (i > 0) buffer.write(' → ');
      buffer.write(_getIntentLabel(_intents[i].type));
    }

    return buffer.toString();
  }

  Future<void> _analyzeIntents() async {
    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
      _executionPlan = null;
      _estimatedTime = null;
    });

    try {
      final repository = ref.read(intentRepositoryProvider);
      final response = await repository.previewIntents(widget.message);

      if (mounted) {
        setState(() {
          _isAnalyzing = false;
          _intents = response.detectedIntents;
          _executionPlan = response.executionPlan;
          _estimatedTime = response.estimatedTime;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isAnalyzing = false;
          _errorMessage = '意图分析失败: ${e.toString()}';
        });
      }
    }
  }

  Future<void> _executeIntents() async {
    setState(() => _isExecuting = true);

    try {
      // TODO: Call actual execution API
      await Future<void>.delayed(const Duration(milliseconds: 500));

      if (mounted) {
        Navigator.of(context).pop(true);
        widget.onConfirm();
      }
    } catch (e) {
      setState(() => _isExecuting = false);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('执行失败: $e')),
        );
      }
    }
  }
}
