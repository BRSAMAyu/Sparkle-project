import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

class NightlyReviewPayload {
  NightlyReviewPayload({
    required this.id,
    required this.status,
    this.widgetPayload,
    this.reviewedAt,
  });

  factory NightlyReviewPayload.fromJson(Map<String, dynamic> json) {
    final widgetJson = json['widget_payload'] as Map<String, dynamic>?;
    return NightlyReviewPayload(
      id: json['id'] as String,
      status: json['status'] as String? ?? 'generated',
      widgetPayload:
          widgetJson != null ? WidgetPayload.fromJson(widgetJson) : null,
      reviewedAt: json['reviewed_at'] as String?,
    );
  }

  final String id;
  final String status;
  final WidgetPayload? widgetPayload;
  final String? reviewedAt;
}
