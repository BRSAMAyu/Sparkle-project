import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Configuration for PNG report generation
class ReportConfig {
  const ReportConfig({
    this.size = const ExportDimensions(1080, 1920),
    this.pixelRatio = 2.0,
    this.backgroundColor,
    this.primaryColor,
    this.secondaryColor,
    this.includeWatermark = true,
    this.watermarkText = 'Sparkle AI',
  });

  /// Size of the report
  final ExportDimensions size;

  /// Pixel ratio for higher resolution (default: 2.0)
  final double pixelRatio;

  /// Background color
  final Color? backgroundColor;

  /// Primary accent color
  final Color? primaryColor;

  /// Secondary accent color
  final Color? secondaryColor;

  /// Whether to include a watermark
  final bool includeWatermark;

  /// Watermark text
  final String watermarkText;

  Color get resolvedBackgroundColor => backgroundColor ?? DS.brandPrimary;
  Color get resolvedPrimaryColor => primaryColor ?? DS.onBrandPrimary;
  Color get resolvedSecondaryColor =>
      secondaryColor ?? DS.onBrandPrimary.withValues(alpha: 0.9);

  /// Get a landscape config
  ReportConfig toLandscape() => ReportConfig(
        size: ExportDimensions(size.height, size.width),
        pixelRatio: pixelRatio,
        backgroundColor: backgroundColor,
        primaryColor: primaryColor,
        secondaryColor: secondaryColor,
        includeWatermark: includeWatermark,
        watermarkText: watermarkText,
      );
}

/// Report section data
class ReportSection {
  const ReportSection({
    required this.title,
    required this.content,
    this.enabled = true,
  });

  /// Title of the section
  final String title;

  /// Content widget to render
  final Widget content;

  /// Whether this section should be included
  final bool enabled;
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

    final size = ExportDimensions(
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
    ExportDimensions size,
    ReportConfig config,
  ) async {
    final gradient = LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [
        config.resolvedBackgroundColor,
        config.resolvedBackgroundColor.withValues(alpha: 0.75),
      ],
    );

    final rect = Rect.fromLTWH(0, 0, size.width, size.height);
    final paint = Paint()..shader = gradient.createShader(rect);
    canvas.drawRect(rect, paint);
  }

  /// Draw the header section
  static Future<void> _drawHeader(
    Canvas canvas,
    ExportDimensions size,
    StatisticsEntity statistics,
    ReportConfig config,
  ) async {
    final horizontalInset = DS.spacing64 * config.pixelRatio;

    // Draw title
    final titlePainter = TextPainter(
      text: TextSpan(
        text: statistics.type.displayName,
        style: TextStyle(
          color: config.resolvedPrimaryColor,
          fontSize: 56 * config.pixelRatio,
          fontWeight: DS.fontWeightBold,
          fontFamilyFallback: sparkleFontFallback,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    titlePainter.layout(maxWidth: size.width - horizontalInset * 2);
    titlePainter.paint(
      canvas,
      Offset(horizontalInset, size.height * 0.1),
    );

    // Draw period
    final periodPainter = TextPainter(
      text: TextSpan(
        text: statistics.period.label,
        style: TextStyle(
          color: config.resolvedSecondaryColor,
          fontSize: 36 * config.pixelRatio,
          fontFamilyFallback: sparkleFontFallback,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    periodPainter.layout();
    periodPainter.paint(
      canvas,
      Offset(
        horizontalInset,
        size.height * 0.1 + titlePainter.height + 20 * config.pixelRatio,
      ),
    );

    // Draw date
    final datePainter = TextPainter(
      text: TextSpan(
        text: _formatDate(DateTime.now()),
        style: TextStyle(
          color: config.resolvedPrimaryColor.withValues(alpha: 0.7),
          fontSize: 28 * config.pixelRatio,
          fontFamilyFallback: sparkleFontFallback,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    datePainter.layout();
    datePainter.paint(
      canvas,
      Offset(
        horizontalInset,
        size.height * 0.1 +
            titlePainter.height +
            periodPainter.height +
            40 * config.pixelRatio,
      ),
    );
  }

  /// Draw the content sections
  static Future<void> _drawSections(
    Canvas canvas,
    ExportDimensions size,
    List<ReportSection> sections,
    ReportConfig config,
  ) async {
    final enabledSections = sections.where((s) => s.enabled).toList();
    if (enabledSections.isEmpty) return;

    final startY = size.height * 0.25;
    final availableHeight = size.height * 0.65;
    final sectionHeight = availableHeight / enabledSections.length;

    for (var i = 0; i < enabledSections.length; i++) {
      final section = enabledSections[i];
      final sectionY = startY + sectionHeight * i;

      // Draw section title
      final titlePainter = TextPainter(
        text: TextSpan(
          text: section.title,
          style: TextStyle(
            color: config.resolvedPrimaryColor.withValues(alpha: 0.8),
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
        ..color = config.resolvedPrimaryColor.withValues(alpha: 0.15);
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
    ExportDimensions size,
    ReportConfig config,
  ) async {
    if (!config.includeWatermark) return;

    final footerY = size.height * 0.92;

    // Draw watermark text
    final watermarkPainter = TextPainter(
      text: TextSpan(
        text: config.watermarkText,
        style: TextStyle(
          color: config.resolvedPrimaryColor.withValues(alpha: 0.5),
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
  static String _formatDate(DateTime date, [AppLocalizations? l10n]) {
    if (l10n != null) {
      return l10n.statisticsDateFormat(date.year.toString(), date.month.toString(), date.day.toString());
    }
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }
}

/// Widget for generating a report preview
class ReportPreviewWidget extends StatefulWidget {
  const ReportPreviewWidget({
    required this.statistics,
    required this.sections,
    super.key,
    this.config = const ReportConfig(),
  });
  final StatisticsEntity statistics;
  final List<ReportSection> sections;
  final ReportConfig config;

  @override
  State<ReportPreviewWidget> createState() => _ReportPreviewWidgetState();
}

class _ReportPreviewWidgetState extends State<ReportPreviewWidget> {
  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              widget.config.resolvedBackgroundColor,
              widget.config.resolvedBackgroundColor.withValues(alpha: 0.75),
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
                  padding: const EdgeInsets.all(DS.lg),
                  child: Column(
                    children: [
                      ...widget.sections
                          .where((s) => s.enabled)
                          .map(_buildSectionCard),
                    ],
                  ),
                ),
              ),
              _buildFooter(),
            ],
          ),
        ),
      );

  Widget _buildHeader() => Padding(
        padding: const EdgeInsets.all(DS.xl),
        child: Column(
          children: [
            Text(
              widget.statistics.type.localizedDisplayName(context.l10n),
              style: TextStyle(
                color: widget.config.resolvedPrimaryColor,
                fontSize: 28,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.sm),
            Text(
              widget.statistics.period.localizedLabel(context.l10n),
              style: TextStyle(
                color: widget.config.resolvedSecondaryColor,
                fontSize: 18,
              ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              StatisticsReportGenerator._formatDate(DateTime.now(), context.l10n),
              style: TextStyle(
                color:
                    widget.config.resolvedPrimaryColor.withValues(alpha: 0.7),
                fontSize: 14,
              ),
            ),
          ],
        ),
      );

  Widget _buildSectionCard(ReportSection section) => Container(
        margin: const EdgeInsets.only(bottom: DS.md),
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: widget.config.resolvedPrimaryColor.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              section.title,
              style: TextStyle(
                color: widget.config.resolvedPrimaryColor,
                fontSize: 16,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.md),
            section.content,
          ],
        ),
      );

  Widget _buildFooter() {
    if (!widget.config.includeWatermark) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.all(DS.lg),
      child: Text(
        widget.config.watermarkText,
        style: TextStyle(
          color: widget.config.resolvedPrimaryColor.withValues(alpha: 0.5),
          fontSize: 12,
        ),
      ),
    );
  }
}
