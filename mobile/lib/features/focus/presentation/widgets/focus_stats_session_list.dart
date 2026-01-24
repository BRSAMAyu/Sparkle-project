import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/focus/data/models/focus_session_model.dart';

/// List of recent focus sessions
class FocusStatsSessionList extends StatelessWidget {
  const FocusStatsSessionList({
    required this.sessions,
    this.onLoadMore,
    this.hasMore = false,
    this.isLoading = false,
    super.key,
  });

  final List<FocusSessionDetail> sessions;
  final VoidCallback? onLoadMore;
  final bool hasMore;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    if (sessions.isEmpty && !isLoading) {
      return SizedBox(
        height: 120,
        child: Center(
          child: Text(
            '暂无专注记录',
            style: TextStyle(color: DS.neutral400),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.history, color: DS.brandPrimary.shade600, size: 20),
            const SizedBox(width: DS.sm),
            const Text(
              '最近会话',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.md),
        ...sessions.map((session) => _SessionItem(session: session)),
        if (hasMore && onLoadMore != null)
          TextButton.icon(
            onPressed: isLoading ? null : onLoadMore,
            icon: isLoading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.expand_more, size: 18),
            label: Text(isLoading ? '加载中...' : '查看更多'),
            style: TextButton.styleFrom(
              foregroundColor: DS.brandPrimary,
            ),
          ),
      ],
    );
  }
}

class _SessionItem extends StatelessWidget {
  const _SessionItem({required this.session});

  final FocusSessionDetail session;

  @override
  Widget build(BuildContext context) {
    final isCompleted = session.status == 'completed';
    final timeAgo = _getTimeAgo(session.startTime);

    return Container(
      margin: const EdgeInsets.only(bottom: DS.sm),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.neutral50,
        borderRadius: BorderRadius.circular(DS.sm),
        border: Border.all(
          color: isCompleted
              ? DS.brandPrimary.withValues(alpha: 0.2)
              : DS.neutral200,
        ),
      ),
      child: Row(
        children: [
          _buildStatusIcon(isCompleted),
          const SizedBox(width: DS.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  session.taskTitle ?? '自由专注',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: DS.xs),
                Row(
                  children: [
                    Icon(
                      Icons.timer_outlined,
                      size: 12,
                      color: DS.neutral500,
                    ),
                    const SizedBox(width: DS.xs),
                    Text(
                      '${session.durationMinutes}分钟',
                      style: TextStyle(
                        fontSize: 12,
                        color: DS.neutral500,
                      ),
                    ),
                    const SizedBox(width: DS.sm),
                    Text(
                      timeAgo,
                      style: TextStyle(
                        fontSize: 11,
                        color: DS.neutral400,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          _buildFocusTypeBadge(session.focusType),
        ],
      ),
    );
  }

  Widget _buildStatusIcon(bool isCompleted) {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: isCompleted
            ? DS.brandPrimary.withValues(alpha: 0.15)
            : DS.neutral200,
        shape: BoxShape.circle,
      ),
      child: Icon(
        isCompleted ? Icons.check : Icons.close,
        color: isCompleted ? DS.brandPrimary : DS.neutral500,
        size: 18,
      ),
    );
  }

  Widget _buildFocusTypeBadge(String focusType) {
    final isPomodoro = focusType == 'pomodoro';
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.sm,
        vertical: DS.xs,
      ),
      decoration: BoxDecoration(
        color: isPomodoro
            ? Colors.deepPurple.withValues(alpha: 0.1)
            : DS.neutral200,
        borderRadius: BorderRadius.circular(DS.sm),
      ),
      child: Text(
        isPomodoro ? '番茄' : '正计',
        style: TextStyle(
          fontSize: 11,
          color: isPomodoro ? Colors.deepPurple : DS.neutral600,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  String _getTimeAgo(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);

    if (difference.inMinutes < 60) {
      return '${difference.inMinutes}分钟前';
    } else if (difference.inHours < 24) {
      return '${difference.inHours}小时前';
    } else if (difference.inDays == 1) {
      return '昨天';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}天前';
    } else {
      return '${dateTime.month}/${dateTime.day}';
    }
  }
}
