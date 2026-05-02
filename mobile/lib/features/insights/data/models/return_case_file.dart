/// GOAL-011: ReturnCaseFile model.
///
/// Represents the system's pre-built "what we know about you" snapshot for
/// users who have been away. Backend assembles this from GrowthChronicle so
/// returning users are never treated as new users.
class ReturnCaseFileInsight {
  ReturnCaseFileInsight({
    required this.claim,
    required this.scope,
    required this.confidence,
    this.recommendedFutureUse,
  });

  factory ReturnCaseFileInsight.fromJson(Map<String, dynamic> json) =>
      ReturnCaseFileInsight(
        claim: (json['claim'] ?? '').toString(),
        scope: (json['scope'] ?? '').toString(),
        confidence: (json['confidence'] is num)
            ? (json['confidence'] as num).toDouble()
            : 0.0,
        recommendedFutureUse: json['recommended_future_use'] as String?,
      );

  final String claim;
  final String scope;
  final double confidence;
  final String? recommendedFutureUse;
}

class ReturnCaseFileSummary {
  ReturnCaseFileSummary({
    required this.totalEntries,
    required this.confirmedCount,
    required this.pendingCount,
  });

  factory ReturnCaseFileSummary.fromJson(Map<String, dynamic> json) {
    int asInt(dynamic value) {
      if (value is num) return value.toInt();
      if (value is String) return int.tryParse(value) ?? 0;
      return 0;
    }

    return ReturnCaseFileSummary(
      totalEntries: asInt(json['total_entries']),
      confirmedCount: asInt(json['confirmed_count']),
      pendingCount: asInt(json['pending_count']),
    );
  }

  final int totalEntries;
  final int confirmedCount;
  final int pendingCount;
}

class ReturnCaseFile {
  ReturnCaseFile({
    required this.userId,
    required this.summary,
    required this.confirmedInsights,
    required this.pendingReviewIds,
    required this.generatedAt,
    required this.source,
  });

  factory ReturnCaseFile.fromJson(Map<String, dynamic> json) {
    final rawInsights = json['confirmed_insights'];
    final insights = <ReturnCaseFileInsight>[];
    if (rawInsights is List) {
      for (final entry in rawInsights) {
        if (entry is Map<String, dynamic>) {
          insights.add(ReturnCaseFileInsight.fromJson(entry));
        } else if (entry is Map) {
          insights.add(
            ReturnCaseFileInsight.fromJson(
              Map<String, dynamic>.from(entry),
            ),
          );
        }
      }
    }

    final rawPending = json['pending_review'];
    final pendingIds = <String>[];
    if (rawPending is List) {
      for (final entry in rawPending) {
        pendingIds.add(entry.toString());
      }
    }

    return ReturnCaseFile(
      userId: (json['user_id'] ?? '').toString(),
      summary: ReturnCaseFileSummary.fromJson(
        Map<String, dynamic>.from(json['chronicle_summary'] as Map? ?? {}),
      ),
      confirmedInsights: insights,
      pendingReviewIds: pendingIds,
      generatedAt: (json['generated_at'] ?? '').toString(),
      source: (json['source'] ?? 'rebuild').toString(),
    );
  }

  final String userId;
  final ReturnCaseFileSummary summary;
  final List<ReturnCaseFileInsight> confirmedInsights;
  final List<String> pendingReviewIds;
  final String generatedAt;
  final String source;

  bool get isEmpty =>
      summary.confirmedCount == 0 &&
      summary.pendingCount == 0 &&
      confirmedInsights.isEmpty;
}
