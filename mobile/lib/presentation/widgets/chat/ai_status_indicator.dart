import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// AI 状态指示器
/// 显示 AI 的当前状态（THINKING, GENERATING, EXECUTING_TOOL 等）
class AiStatusIndicator extends StatelessWidget {

  const AiStatusIndicator({
    super.key,
    this.status,
    this.details,
  });
  final String? status;
  final String? details;

  @override
  Widget build(BuildContext context) {
    if (status == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: _getStatusColor(status!).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _getStatusColor(status!).withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 动画指示器
          _buildIndicator(),
          const SizedBox(width: DS.md),
          // 状态文本
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _getStatusText(status!),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: _getStatusColor(status!),
                  ),
                ),
                if (details != null && details!.isNotEmpty) ...[
                  const SizedBox(height: DS.xs),
                  Text(
                    details!,
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(context).textTheme.bodySmall?.color,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIndicator() => SizedBox(
      width: 20,
      height: 20,
      child: CircularProgressIndicator(
        strokeWidth: 2,
        valueColor: AlwaysStoppedAnimation<Color>(_getStatusColor(status!)),
      ),
    );

  String _getStatusText(String status) {
    switch (status) {
      case 'THINKING':
        return '思考中...';
      case 'GENERATING':
        return '正在生成回复...';
      case 'EXECUTING_TOOL':
        return '正在使用工具...';
      case 'SEARCHING':
        return '正在搜索...';
      case 'UNKNOWN':
      default:
        return '处理中...';
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'THINKING':
        return const Color(0xFF6366F1); // Indigo
      case 'GENERATING':
        return const Color(0xFF10B981); // Green
      case 'EXECUTING_TOOL':
        return const Color(0xFFF59E0B); // Amber
      case 'SEARCHING':
        return const Color(0xFF3B82F6); // Blue
      case 'UNKNOWN':
      default:
        return const Color(0xFF8B5CF6); // Purple
    }
  }
}

/// AI 状态气泡（紧凑版，用于聊天气泡中）
class AiStatusBubble extends StatelessWidget {

  const AiStatusBubble({
    required this.status,
    super.key,
  });
  final String status;

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _getStatusColor(status).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 12,
            height: 12,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(_getStatusColor(status)),
            ),
          ),
          const SizedBox(width: DS.sm),
          Text(
            _getStatusText(status),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: _getStatusColor(status),
            ),
          ),
        ],
      ),
    );

  String _getStatusText(String status) {
    switch (status) {
      case 'THINKING':
        return '思考中';
      case 'GENERATING':
        return '生成中';
      case 'EXECUTING_TOOL':
        return '工具执行中';
      case 'SEARCHING':
        return '搜索中';
      default:
        return '处理中';
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'THINKING':
        return const Color(0xFF6366F1);
      case 'GENERATING':
        return const Color(0xFF10B981);
      case 'EXECUTING_TOOL':
        return const Color(0xFFF59E0B);
      case 'SEARCHING':
        return const Color(0xFF3B82F6);
      default:
        return const Color(0xFF8B5CF6);
    }
  }
}
