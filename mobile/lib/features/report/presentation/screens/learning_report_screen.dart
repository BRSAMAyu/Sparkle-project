import 'package:flutter/material.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/widgets/mastery_radar_chart.dart';

class LearningReportScreen extends StatelessWidget {
  const LearningReportScreen({
    required this.report,
    super.key,
  });

  final LearningReport report;

  @override
  Widget build(BuildContext context) {
    final chartData = report.mastery.take(4).toList();
    return Scaffold(
        appBar: AppBar(title: const Text('学习分析报告')),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            MasteryRadarChart(
              labels: chartData.map((item) => item.nodeName).toList(),
              values: chartData.map((item) => (item.masteryScore / 100).clamp(0.0, 1.0)).toList(),
            ),
            const SizedBox(height: 16),
            SelectableText(report.markdown),
          ],
        ),
      );
  }
}
