import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/domain/services/statistics_export_service.dart';

/// Default implementation of the statistics export service
///
/// Supports JSON, CSV, and PNG report exports.
class StatisticsExportServiceImpl<T extends StatisticsEntity>
    implements StatisticsExportService<T> {
  /// Whether to include app metadata in exports
  final bool includeMetadata;

  /// App version string (for metadata)
  final String appVersion;

  StatisticsExportServiceImpl({
    this.includeMetadata = true,
    this.appVersion = '1.0.0',
  });

  // ============================================
  // INTERFACE IMPLEMENTATION
  // ============================================

  @override
  Future<Uint8List> export(
    T statistics,
    StatisticsExportConfig config,
  ) async {
    switch (config.format) {
      case ExportFormat.json:
        return _exportJson(statistics, config);
      case ExportFormat.csv:
        return _exportCsv(statistics, config);
      case ExportFormat.pngReport:
        return _exportPngReport(statistics, config);
      case ExportFormat.pdfReport:
        // PDF not implemented yet, return empty
        throw UnimplementedError('PDF export not implemented');
    }
  }

  @override
  String generateFilename(
    StatisticsType type,
    StatisticsPeriod period,
    ExportFormat format, {
    DateTime? timestamp,
  }) {
    final ts = timestamp ?? DateTime.now();
    final dateStr = '${ts.year}${ts.month.toString().padLeft(2, '0')}'
        '${ts.day.toString().padLeft(2, '0')}';
    final timeStr = '${ts.hour.toString().padLeft(2, '0')}'
        '${ts.minute.toString().padLeft(2, '0')}'
        '${ts.second.toString().padLeft(2, '0')}';

    return 'sparkle_${type.code}_${period.name}_$dateStr'
        '_$timeStr.${format.fileExtension}';
  }

  @override
  Future<String> generateShareContent(T statistics) async {
    final type = statistics.type.displayName;
    final period = statistics.period.label;
    final date = DateTime.now();

    final buffer = StringBuffer();
    buffer.writeln('📊 我的$type数据');
    buffer.writeln('📅 统计周期: $period');
    buffer.writeln('🕐 导出时间: ${_formatDateTime(date)}');
    buffer.writeln('');
    buffer.writeln('📈 数据来自 星火AI学习助手');

    return buffer.toString();
  }

  @override
  bool isFormatSupported(ExportFormat format) {
    return format != ExportFormat.pdfReport; // PDF not implemented
  }

  @override
  List<ExportFormat> getSupportedFormats() {
    return [
      ExportFormat.json,
      ExportFormat.csv,
      ExportFormat.pngReport,
    ];
  }

  @override
  Future<List<Uint8List>> exportMultiple(
    List<T> statisticsList,
    StatisticsExportConfig config,
  ) async {
    final results = <Uint8List>[];

    for (final statistics in statisticsList) {
      final data = await export(statistics, config);
      results.add(data);
    }

    return results;
  }

  @override
  Future<Uint8List?> generatePreview(
    T statistics,
    ExportFormat format,
  ) async {
    // Generate a small preview thumbnail
    // For simplicity, we'll generate a small placeholder
    // In production, this would render a miniature version

    if (format == ExportFormat.pngReport) {
      // Create a simple placeholder preview
      final recorder = ui.PictureRecorder();
      final canvas = Canvas(recorder);
      final size = ExportDimensions(200, 200);

      // Draw background
      final bgPaint = Paint()..color = Colors.white;
      canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), bgPaint);

      // Draw preview text
      final textPainter = TextPainter(
        text: TextSpan(
          text: '预览\n${statistics.type.displayName}',
          style: const TextStyle(
            color: Colors.black,
            fontSize: 20,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset(
          (size.width - textPainter.width) / 2,
          (size.height - textPainter.height) / 2,
        ),
      );

      final picture = recorder.endRecording();
      final image = await picture.toImage(
        size.width.toInt(),
        size.height.toInt(),
      );
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      return byteData?.buffer.asUint8List();
    }

    return null;
  }

  // ============================================
  // PRIVATE EXPORT METHODS
  // ============================================

  /// Export as JSON
  Uint8List _exportJson(T statistics, StatisticsExportConfig config) {
    final json = {
      'type': statistics.type.code,
      'period': statistics.period.name,
      'lastRefreshedAt': statistics.lastRefreshedAt.toIso8601String(),
      'isFromCache': statistics.isFromCache,
    };

    // Add metadata if enabled
    if (config.includeMetadata && includeMetadata) {
      json['metadata'] = {
        'appVersion': appVersion,
        'exportedAt': DateTime.now().toIso8601String(),
        'format': 'json',
      };
    }

    // Add entity-specific data (to be overridden by subclasses)
    _addEntityDataToJson(json, statistics);

    final jsonString = jsonEncode(json);
    final bytes = utf8.encode(jsonString);
    return Uint8List.fromList(bytes);
  }

  /// Export as CSV
  Uint8List _exportCsv(T statistics, StatisticsExportConfig config) {
    final buffer = StringBuffer();

    // Write header
    _writeCsvHeader(buffer, statistics);

    // Write data rows
    _writeCsvData(buffer, statistics);

    // Add metadata if enabled
    if (config.includeMetadata && includeMetadata) {
      buffer.writeln('');
      buffer.writeln('# Metadata');
      buffer.writeln('# App Version: $appVersion');
      buffer.writeln('# Exported At: ${DateTime.now().toIso8601String()}');
      buffer.writeln('# Format: csv');
    }

    final bytes = utf8.encode(buffer.toString());
    return Uint8List.fromList(bytes);
  }

  /// Export as PNG report
  Future<Uint8List> _exportPngReport(
    T statistics,
    StatisticsExportConfig config,
  ) async {
    // This is a placeholder implementation
    // In production, this would:
    // 1. Render the widget to a canvas
    // 2. Include charts if config.includeCharts is true
    // 3. Apply the scale factor for high-resolution output

    // Use a default size for now - the ExportSize configuration needs to be refactored
    const size = ExportDimensions(1080, 1920);

    final scaledSize = ExportDimensions(
      size.width * config.pngScale,
      size.height * config.pngScale,
    );

    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);

    // Draw background gradient
    final bgGradient = const LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [
        Color(0xFF6366F1),
        Color(0xFF8B5CF6),
      ],
    );

    final bgRect = Rect.fromLTWH(0, 0, scaledSize.width, scaledSize.height);
    final bgPaint = Paint()..shader = bgGradient.createShader(bgRect);
    canvas.drawRect(bgRect, bgPaint);

    // Draw title
    const titleStyle = TextStyle(
      color: Colors.white,
      fontSize: 48,
      fontWeight: FontWeight.bold,
    );
    final titlePainter = TextPainter(
      text: TextSpan(
        text: '${statistics.type.displayName}统计',
        style: titleStyle,
      ),
      textDirection: TextDirection.ltr,
    );
    titlePainter.layout();
    titlePainter.paint(
      canvas,
      Offset(
        (scaledSize.width - titlePainter.width) / 2,
        100 * config.pngScale,
      ),
    );

    // Draw period
    const periodStyle = TextStyle(
      color: Colors.white,
      fontSize: 32,
    );
    final periodPainter = TextPainter(
      text: TextSpan(
        text: statistics.period.label,
        style: periodStyle,
      ),
      textDirection: TextDirection.ltr,
    );
    periodPainter.layout();
    periodPainter.paint(
      canvas,
      Offset(
        (scaledSize.width - periodPainter.width) / 2,
        180 * config.pngScale,
      ),
    );

    // Draw date
    const dateStyle = TextStyle(
      color: Colors.white,
      fontSize: 24,
    );
    final datePainter = TextPainter(
      text: TextSpan(
        text: _formatDateTime(DateTime.now()),
        style: dateStyle,
      ),
      textDirection: TextDirection.ltr,
    );
    datePainter.layout();
    datePainter.paint(
      canvas,
      Offset(
        (scaledSize.width - datePainter.width) / 2,
        240 * config.pngScale,
      ),
    );

    // Add entity-specific visual data
    await _drawPngReportData(canvas, statistics, scaledSize, config);

    // Draw footer
    const footerStyle = TextStyle(
      color: Colors.white,
      fontSize: 20,
    );
    final footerPainter = TextPainter(
      text: TextSpan(
        text: '星火AI学习助手 · $appVersion',
        style: footerStyle,
      ),
      textDirection: TextDirection.ltr,
    );
    footerPainter.layout();
    footerPainter.paint(
      canvas,
      Offset(
        (scaledSize.width - footerPainter.width) / 2,
        scaledSize.height - 100 * config.pngScale,
      ),
    );

    final picture = recorder.endRecording();
    final image = await picture.toImage(
      scaledSize.width.toInt(),
      scaledSize.height.toInt(),
    );
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);

    if (byteData == null) {
      throw Exception('Failed to generate PNG');
    }

    return byteData.buffer.asUint8List();
  }

  // ============================================
  // OVERRIDE HOOKS (for subclasses)
  // ============================================

  /// Add entity-specific data to JSON export
  ///
  /// Subclasses should override this to include their specific data
  void _addEntityDataToJson(Map<String, dynamic> json, T statistics) {
    // Default: no additional data
    // Subclasses should override this
  }

  /// Write CSV header
  ///
  /// Subclasses should override this for custom headers
  void _writeCsvHeader(StringBuffer buffer, T statistics) {
    buffer.writeln('Metric,Value');
  }

  /// Write CSV data rows
  ///
  /// Subclasses should override this for custom data
  void _writeCsvData(StringBuffer buffer, T statistics) {
    buffer.writeln('Type,${statistics.type.code}');
    buffer.writeln('Period,${statistics.period.name}');
    buffer.writeln('Last Refreshed,${statistics.lastRefreshedAt.toIso8601String()}');
    buffer.writeln('From Cache,${statistics.isFromCache}');
  }

  /// Draw entity-specific data on PNG report
  ///
  /// Subclasses should override this to add charts and data visualization
  Future<void> _drawPngReportData(
    Canvas canvas,
    T statistics,
    ExportDimensions size,
    StatisticsExportConfig config,
  ) async {
    // Default: draw a placeholder message
    final msgPainter = TextPainter(
      text: TextSpan(
        text: '数据图表区域\n(子类需实现具体绘制)',
        style: TextStyle(
          fontSize: 28 * config.pngScale,
          color: Colors.white.withValues(alpha: 0.8),
        ),
      ),
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
    );
    msgPainter.layout(maxWidth: size.width - 100 * config.pngScale);
    msgPainter.paint(
      canvas,
      Offset(
        50 * config.pngScale,
        size.height / 2 - 100 * config.pngScale,
      ),
    );
  }

  // ============================================
  // UTILITY METHODS
  // ============================================

  /// Format datetime for display
  String _formatDateTime(DateTime dt) {
    return '${dt.year}年${dt.month}月${dt.day}日 '
        '${dt.hour.toString().padLeft(2, '0')}:'
        '${dt.minute.toString().padLeft(2, '0')}';
  }
}

/// Provider for statistics export service
///
/// Usage:
/// ```dart
/// ref.read(statisticsExportServiceProvider(type: StatisticsType.focus))
/// ```
// @riverpod
// StatisticsExportService<StatisticsEntity> statisticsExportService(
//   StatisticsExportServiceRef ref, {
//   required StatisticsType type,
// }) {
//   return StatisticsExportServiceImpl<StatisticsEntity>();
// }
