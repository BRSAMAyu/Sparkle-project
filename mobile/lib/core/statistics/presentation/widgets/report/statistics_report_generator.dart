import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/statistics/config/statistics_config.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/domain/services/statistics_export_service.dart';

/// Configuration for PNG report generation
class ReportConfig {
  /// Size of the report
  final Size size;

  /// Pixel ratio for higher resolution (default: 2.0)
  final double pixelRatio;

  /// Background color
  final Color backgroundColor;

  /// Primary accent color
  final Color primaryColor;

  /// Secondary accent color
  final Color secondaryColor;

  /// Whether to include a watermark
  final bool includeWatermark;

  /// Watermark text
  final String watermarkText;

  const ReportConfig({
    this.size = const Size(1080, 1920),
    this.pixelRatio = 2.0,
    this.backgroundColor = const Color(0xFF6366F1),
    this.primaryColor = const Color(0xFFFFFFFF),
    this.secondaryColor = const Color(0xFFFFFFFF),
    this.includeWatermark = true,
    this.watermarkText = '星火AI学习助手',
  });

  /// Get a landscape config
  ReportConfig toLandscape() {
    return ReportConfig(
      size: Size(size.height, size.width),
      pixelRatio: pixelRatio,
      backgroundColor: backgroundColor,
      primaryColor: primaryColor,
      secondaryColor: secondaryColor,
      includeWatermark: includeWatermark,
      watermarkText: watermarkText,
    );
  }
}

/// Report section data
class ReportSection {
  /// Title of the section
  final String title;

  /// Content widget to render
  final Widget content;

  /// Whether this section should be included
  final bool enabled;

  const ReportSection({
    required this.title,
    required this.content,
    this.enabled = true,
  });
}

/// Statistics report generator
class StatisticsReportGenerator {
  /// Generate a PNG report from statistics data
  ///
  /// Returns the raw PNG bytes
  static Future<Uint8List> generatePng({
    required StatisticsEntity statistics,
    required List<ReportSection> sections,
    ReportConfig config = const ReportConfig(),
  }) async {
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);

    final size = Size(
      config.size.width * config.pixelRatio,
      config.size.height * config.pixelRatio,
    );

    // Draw background
    await _drawBackground(canvas, size, config);

    // Draw header
    await _drawHeader(canvas, size, statistics, config);

    // Draw sections
    await _drawSections(canvas, size, sections, config);

    // Draw footer
    await _drawFooter(canvas, size, config);

    // Convert to image
    final picture = recorder.endRecording();
    final image = await picture.toImage(
      size.width.toInt(),
      size.height.toInt(),
    );
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);

    return byteData!.buffer.asUint8List();
  }

  /// Draw the background gradient
  static Future<void> _drawBackground(
    Canvas canvas,
    Size size,
    ReportConfig config,
  ) async {
    final gradient = LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [
        config.backgroundColor,
        config.backgroundColor.withBlue(200),
      ],
    );

    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    final paint = Paint()..shader = gradient.createShader(rect);
    canvas.drawRect(rect, paint);
  }

  /// Draw the header section
  static Future<void> _drawHeader(
    Canvas canvas,
    Size size,
    StatisticsEntity statistics,
    ReportConfig config,
  ) async {
    final padding = size.width * 0.08;

    // Draw title
    final titlePainter = TextPainter(
      text: TextSpan(
        text: statistics.type.displayName,
        style: TextStyle(
          color: config.primaryColor,
          fontSize: 56 * config.pixelRatio,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    titlePainter.layout(maxWidth: size.width - padding * 2);
    titlePainter.paint(
      canvas,
      Offset(padding, size.height * 0.1),
    );

    // Draw period
    final periodPainter = TextPainter(
      text: TextSpan(
        text: statistics.period.label,
        style: TextStyle(
          color: config.primaryColor.withValues(alpha: 0.9),
          fontSize: 36 * config.pixelRatio,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    periodPainter.layout();
    periodPainter.paint(
      canvas,
      Offset(padding, size.height * 0.1 + titlePainter.height + 20 * config.pixelRatio),
    );

    // Draw date
    final datePainter = TextPainter(
      text: TextSpan(
        text: _formatDate(DateTime.now()),
        style: TextStyle(
          color: config.primaryColor.withValues(alpha: 0.7),
          fontSize: 28 * config.pixelRatio,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    datePainter.layout();
    datePainter.paint(
      canvas,
      Offset(padding, size.height * 0.1 + titlePainter.height + periodPainter.height + 40 * config.pixelRatio),
    );
  }

  /// Draw the content sections
  static Future<void> _drawSections(
    Canvas canvas,
    Size size,
    List<ReportSection> sections,
    ReportConfig config,
  ) async {
    final enabledSections = sections.where((s) => s.enabled).toList();
    if (enabledSections.isEmpty) return;

    final startY = size.height * 0.25;
    final availableHeight = size.height * 0.65;
    final sectionHeight = availableHeight / enabledSections.length;

    for (int i = 0; i < enabledSections.length; i++) {
      final section = enabledSections[i];
      final sectionY = startY + sectionHeight * i;

      // Draw section title
      final titlePainter = TextPainter(
        text: TextSpan(
          text: section.title,
          style: TextStyle(
            color: config.primaryColor.withValues(alpha: 0.8),
            fontSize: 32 * config.pixelRatio,
            fontWeight: FontWeight.w500,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      titlePainter.layout(maxWidth: size.width - size.width * 0.16);
      titlePainter.paint(
        canvas,
        Offset(size.width * 0.08, sectionY),
      );

      // Draw section background card
      final cardRect = Rect.fromLTWH(
        size.width * 0.08,
        sectionY + titlePainter.height + 20 * config.pixelRatio,
        size.width * 0.84,
        sectionHeight - titlePainter.height - 40 * config.pixelRatio,
      );

      final cardPaint = Paint()
        ..color = config.primaryColor.withValues(alpha: 0.15);
      final rrect = RRect.fromRectAndRadius(
        cardRect,
        Radius.circular(24 * config.pixelRatio),
      );
      canvas.drawRRect(rrect, cardPaint);

      // Note: Actual widget rendering would require flutter_test or similar
      // For production, you would render the widget to an image
      // and draw it here
    }
  }

  /// Draw the footer section
  static Future<void> _drawFooter(
    Canvas canvas,
    Size size,
    ReportConfig config,
  ) async {
    if (!config.includeWatermark) return;

    final footerY = size.height * 0.92;

    // Draw watermark text
    final watermarkPainter = TextPainter(
      text: TextSpan(
        text: config.watermarkText,
        style: TextStyle(
          color: config.primaryColor.withValues(alpha: 0.5),
          fontSize: 24 * config.pixelRatio,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    watermarkPainter.layout();
    watermarkPainter.paint(
      canvas,
      Offset(
        (size.width - watermarkPainter.width) / 2,
        footerY,
      ),
    );
  }

  /// Format date for display
  static String _formatDate(DateTime date) {
    return '${date.year}年${date.month}月${date.day}日';
  }
}

/// Widget for generating a report preview
class ReportPreviewWidget extends StatefulWidget {
  final StatisticsEntity statistics;
  final List<ReportSection> sections;
  final ReportConfig config;

  const ReportPreviewWidget({
    super.key,
    required this.statistics,
    required this.sections,
    this.config = const ReportConfig(),
  });

  @override
  State<ReportPreviewWidget> createState() => _ReportPreviewWidgetState();
}

class _ReportPreviewWidgetState extends State<ReportPreviewWidget> {
  bool _isGenerating = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            widget.config.backgroundColor,
            widget.config.backgroundColor.withBlue(200),
          ],
        ),
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
      ),
      child: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: SingleChildScrollView(
                padding: EdgeInsets.all(DS.lg),
                child: Column(
                  children: [
                    ...widget.sections.where((s) => s.enabled).map((section) {
                      return _buildSectionCard(section);
                    }),
                  ],
                ),
              ),
            ),
            _buildFooter(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: EdgeInsets.all(DS.xl),
      child: Column(
        children: [
          Text(
            widget.statistics.type.displayName,
            style: TextStyle(
              color: widget.config.primaryColor,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: DS.sm),
          Text(
            widget.statistics.period.label,
            style: TextStyle(
              color: widget.config.primaryColor.withValues(alpha: 0.9),
              fontSize: 18,
            ),
          ),
          SizedBox(height: DS.xs),
          Text(
            StatisticsReportGenerator._formatDate(DateTime.now()),
            style: TextStyle(
              color: widget.config.primaryColor.withValues(alpha: 0.7),
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionCard(ReportSection section) {
    return Container(
      margin: EdgeInsets.only(bottom: DS.md),
      padding: EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: widget.config.primaryColor.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            section.title,
            style: TextStyle(
              color: widget.config.primaryColor,
              fontSize: 16,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          SizedBox(height: DS.md),
          section.content,
        ],
      ),
    );
  }

  Widget _buildFooter() {
    if (!widget.config.includeWatermark) return const SizedBox.shrink();

    return Padding(
      padding: EdgeInsets.all(DS.lg),
      child: Text(
        widget.config.watermarkText,
        style: TextStyle(
          color: widget.config.primaryColor.withValues(alpha: 0.5),
          fontSize: 12,
        ),
      ),
    );
  }
}

