import 'package:cloud_firestore/cloud_firestore.dart';

/// Unified notification model combining system and intervention notifications
class UnifiedNotification {

  UnifiedNotification({
    required this.id,
    required this.sourceType,
    required this.title,
    required this.content,
    required this.priority, required this.isRead, required this.createdAt, this.type,
    this.readAt,
    this.metadata = const {},
  });

  factory UnifiedNotification.fromJson(Map<String, dynamic> json) => UnifiedNotification(
      id: json['id'] as String,
      sourceType: json['source_type'] as String,
      title: json['title'] as String,
      content: json['content'] as String,
      type: json['type'] as String?,
      priority: json['priority'] as String? ?? 'medium',
      isRead: json['is_read'] as bool? ?? false,
      createdAt: DateTime.parse(json['created_at'] as String),
      readAt: json['read_at'] != null
          ? DateTime.parse(json['read_at'] as String)
          : null,
      metadata: json['metadata'] as Map<String, dynamic>? ?? {},
    );
  final String id;
  final String sourceType; // 'system' or 'intervention'
  final String title;
  final String content;
  final String? type;
  final String priority; // 'low', 'medium', 'high'
  final bool isRead;
  final DateTime createdAt;
  final DateTime? readAt;
  final Map<String, dynamic> metadata;

  Map<String, dynamic> toJson() => {
      'id': id,
      'source_type': sourceType,
      'title': title,
      'content': content,
      if (type != null) 'type': type,
      'priority': priority,
      'is_read': isRead,
      'created_at': createdAt.toIso8601String(),
      if (readAt != null) 'read_at': readAt!.toIso8601String(),
      'metadata': metadata,
    };

  /// Get icon based on notification type
  String get icon {
    if (sourceType == 'intervention') {
      return '⚠️';
    }

    // System notification icons
    switch (type) {
      case 'plan_archived':
      case 'plan_deleted':
      case 'plan_restored':
        return '📋';
      case 'settings_updated':
        return '⚙️';
      case 'memory_cleanup':
        return '🧹';
      case 'achievement':
        return '🏆';
      default:
        return '🔔';
    }
  }

  /// Get relative time (e.g., "5 minutes ago")
  String get relativeTime {
    final now = DateTime.now();
    final difference = now.difference(createdAt);

    if (difference.inSeconds < 60) {
      return '刚刚';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes} 分钟前';
    } else if (difference.inHours < 24) {
      return '${difference.inHours} 小时前';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} 天前';
    } else {
      return '${createdAt.year}-${createdAt.month.toString().padLeft(2, '0')}-${createdAt.day.toString().padLeft(2, '0')}';
    }
  }

  /// Get priority color
  int get priorityColor {
    switch (priority) {
      case 'high':
        return 0xFFFF5252; // Red
      case 'medium':
        return 0xFFFFB74D; // Orange
      case 'low':
      default:
        return 0xFF81C784; // Green
    }
  }

  /// Check if notification is from today
  bool get isToday {
    final now = DateTime.now();
    return createdAt.year == now.year &&
           createdAt.month == now.month &&
           createdAt.day == now.day;
  }

  /// Check if notification is from this week
  bool get isThisWeek {
    final now = DateTime.now();
    final weekAgo = now.subtract(const Duration(days: 7));
    return createdAt.isAfter(weekAgo);
  }

  UnifiedNotification copyWith({
    String? id,
    String? sourceType,
    String? title,
    String? content,
    String? type,
    String? priority,
    bool? isRead,
    DateTime? createdAt,
    DateTime? readAt,
    Map<String, dynamic>? metadata,
  }) => UnifiedNotification(
      id: id ?? this.id,
      sourceType: sourceType ?? this.sourceType,
      title: title ?? this.title,
      content: content ?? this.content,
      type: type ?? this.type,
      priority: priority ?? this.priority,
      isRead: isRead ?? this.isRead,
      createdAt: createdAt ?? this.createdAt,
      readAt: readAt ?? this.readAt,
      metadata: metadata ?? this.metadata,
    );
}
