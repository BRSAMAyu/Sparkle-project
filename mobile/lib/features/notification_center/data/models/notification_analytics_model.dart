/// Notification analytics models
library;

/// Summary statistics for notifications
class NotificationAnalyticsSummary {

  NotificationAnalyticsSummary({
    required this.totalSent,
    required this.totalViewed,
    required this.totalClicked,
    required this.viewRate,
    required this.clickRate,
    required this.avgTimeToAction,
  });

  factory NotificationAnalyticsSummary.fromJson(Map<String, dynamic> json) {
    return NotificationAnalyticsSummary(
      totalSent: json['total_sent'] as int? ?? 0,
      totalViewed: json['total_viewed'] as int? ?? 0,
      totalClicked: json['total_clicked'] as int? ?? 0,
      viewRate: (json['view_rate'] as num?)?.toDouble() ?? 0.0,
      clickRate: (json['click_rate'] as num?)?.toDouble() ?? 0.0,
      avgTimeToAction: (json['avg_time_to_action'] as num?)?.toDouble() ?? 0.0,
    );
  }
  final int totalSent;
  final int totalViewed;
  final int totalClicked;
  final double viewRate;
  final double clickRate;
  final double avgTimeToAction;

  Map<String, dynamic> toJson() => {
      'total_sent': totalSent,
      'total_viewed': totalViewed,
      'total_clicked': totalClicked,
      'view_rate': viewRate,
      'click_rate': clickRate,
      'avg_time_to_action': avgTimeToAction,
    };
}

/// Statistics for a specific notification type
class NotificationTypeStats {

  NotificationTypeStats({
    required this.type,
    required this.sent,
    required this.viewed,
    required this.clicked,
    required this.viewRate,
    required this.clickRate,
  });

  factory NotificationTypeStats.fromJson(Map<String, dynamic> json) {
    return NotificationTypeStats(
      type: json['type'] as String,
      sent: json['sent'] as int? ?? 0,
      viewed: json['viewed'] as int? ?? 0,
      clicked: json['clicked'] as int? ?? 0,
      viewRate: (json['view_rate'] as num?)?.toDouble() ?? 0.0,
      clickRate: (json['click_rate'] as num?)?.toDouble() ?? 0.0,
    );
  }
  final String type;
  final int sent;
  final int viewed;
  final int clicked;
  final double viewRate;
  final double clickRate;

  Map<String, dynamic> toJson() => {
      'type': type,
      'sent': sent,
      'viewed': viewed,
      'clicked': clicked,
      'view_rate': viewRate,
      'click_rate': clickRate,
    };
}

/// Trend data point (date + metrics)
class NotificationTrendData {

  NotificationTrendData({
    required this.date,
    required this.sent,
    required this.viewed,
    required this.clicked,
  });

  factory NotificationTrendData.fromJson(Map<String, dynamic> json) {
    return NotificationTrendData(
      date: json['date'] as String,
      sent: json['sent'] as int? ?? 0,
      viewed: json['viewed'] as int? ?? 0,
      clicked: json['clicked'] as int? ?? 0,
    );
  }
  final String date;
  final int sent;
  final int viewed;
  final int clicked;

  Map<String, dynamic> toJson() => {
      'date': date,
      'sent': sent,
      'viewed': viewed,
      'clicked': clicked,
    };

  /// Parse date
  DateTime get parsedDate => DateTime.parse(date);
}

/// Complete analytics response
class NotificationAnalytics { // 24 values

  NotificationAnalytics({
    required this.summary,
    required this.byType,
    required this.trends,
    required this.hourlyDistribution,
  });

  factory NotificationAnalytics.fromJson(Map<String, dynamic> json) {
    final byTypeMap = <String, NotificationTypeStats>{};
    if (json['by_type'] != null) {
      (json['by_type'] as Map<String, dynamic>).forEach((key, value) {
        byTypeMap[key] = NotificationTypeStats.fromJson(value as Map<String, dynamic>);
      });
    }

    final trendsList = <NotificationTrendData>[];
    if (json['trends'] != null) {
      for (var item in json['trends'] as List) {
        trendsList.add(NotificationTrendData.fromJson(item as Map<String, dynamic>));
      }
    }

    final distributionList = <int>[];
    if (json['hourly_distribution'] != null) {
      for (var item in json['hourly_distribution'] as List) {
        distributionList.add(item as int);
      }
    }

    return NotificationAnalytics(
      summary: NotificationAnalyticsSummary.fromJson(json['summary'] as Map<String, dynamic>),
      byType: byTypeMap,
      trends: trendsList,
      hourlyDistribution: distributionList,
    );
  }
  final NotificationAnalyticsSummary summary;
  final Map<String, NotificationTypeStats> byType;
  final List<NotificationTrendData> trends;
  final List<int> hourlyDistribution;

  Map<String, dynamic> toJson() => {
      'summary': summary.toJson(),
      'by_type': byType.map((k, v) => MapEntry(k, v.toJson())),
      'trends': trends.map((t) => t.toJson()).toList(),
      'hourly_distribution': hourlyDistribution,
    };

  /// Get max value in hourly distribution
  int get maxHourlyActivity {
    if (hourlyDistribution.isEmpty) return 0;
    return hourlyDistribution.reduce((a, b) => a > b ? a : b);
  }

  /// Get most active hour (0-23)
  int get mostActiveHour {
    if (hourlyDistribution.isEmpty) return 0;
    var maxVal = hourlyDistribution[0];
    var maxHour = 0;
    for (var i = 1; i < hourlyDistribution.length; i++) {
      if (hourlyDistribution[i] > maxVal) {
        maxVal = hourlyDistribution[i];
        maxHour = i;
      }
    }
    return maxHour;
  }
}
