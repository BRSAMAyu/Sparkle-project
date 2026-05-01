import 'dart:typed_data';
import 'package:sparkle/core/statistics/domain/entities/statistics_entity.dart';
import 'package:sparkle/core/statistics/domain/entities/statistics_period.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Export format options
enum ExportFormat {
  /// JSON format for data export
  json,

  /// CSV format for spreadsheet compatibility
  csv,

  /// PNG image report
  pngReport,

  /// PDF document report
  pdfReport,
}

/// Extension for ExportFormat
extension ExportFormatExt on ExportFormat {
  String get label => localizedLabel(null);

  String localizedLabel(AppLocalizations? l10n) {
    switch (this) {
      case ExportFormat.json:
        return 'JSON';
      case ExportFormat.csv:
        return 'CSV';
      case ExportFormat.pngReport:
        return l10n?.statisticsExportImageReport ?? '图片报告';
      case ExportFormat.pdfReport:
        return l10n?.statisticsExportPDFReport ?? 'PDF报告';
    }
  }

  String get fileExtension {
    switch (this) {
      case ExportFormat.json:
        return 'json';
      case ExportFormat.csv:
        return 'csv';
      case ExportFormat.pngReport:
        return 'png';
      case ExportFormat.pdfReport:
        return 'pdf';
    }
  }

  /// MIME type for content type header
  String get mimeType {
    switch (this) {
      case ExportFormat.json:
        return 'application/json';
      case ExportFormat.csv:
        return 'text/csv';
      case ExportFormat.pngReport:
        return 'image/png';
      case ExportFormat.pdfReport:
        return 'application/pdf';
    }
  }
}

/// Configuration for export operations
class StatisticsExportConfig {

  const StatisticsExportConfig({
    required this.format,
    required this.period,
    this.customStart,
    this.customEnd,
    this.includeCharts = true,
    this.includeDetails = true,
    this.pngScale = 2.0,
    this.customSize,
    this.includeMetadata = true,
  });
  /// The export format
  final ExportFormat format;

  /// The time period to export
  final StatisticsPeriod period;

  /// Custom date range for period.custom
  final DateTime? customStart;
  final DateTime? customEnd;

  /// Whether to include charts in the export
  final bool includeCharts;

  /// Whether to include detailed data in the export
  final bool includeDetails;

  /// PNG-specific: Scale factor for higher resolution (default 2.0 for 2x)
  final double pngScale;

  /// PNG/PDF-specific: Custom size for the exported image/report
  final ExportSize? customSize;

  /// Whether to include metadata (export time, app version, etc.)
  final bool includeMetadata;

  /// Copy with modified values
  StatisticsExportConfig copyWith({
    ExportFormat? format,
    StatisticsPeriod? period,
    DateTime? customStart,
    DateTime? customEnd,
    bool? includeCharts,
    bool? includeDetails,
    double? pngScale,
    ExportSize? customSize,
    bool? includeMetadata,
  }) => StatisticsExportConfig(
      format: format ?? this.format,
      period: period ?? this.period,
      customStart: customStart ?? this.customStart,
      customEnd: customEnd ?? this.customEnd,
      includeCharts: includeCharts ?? this.includeCharts,
      includeDetails: includeDetails ?? this.includeDetails,
      pngScale: pngScale ?? this.pngScale,
      customSize: customSize ?? this.customSize,
      includeMetadata: includeMetadata ?? this.includeMetadata,
    );
}

/// Predefined export sizes
class ExportSize {
  /// Mobile portrait (1080x1920)
  static const mobilePortrait = _ExportSize(ExportDimensions(1080, 1920), 'mobilePortrait');

  /// Mobile landscape (1920x1080)
  static const mobileLandscape = _ExportSize(ExportDimensions(1920, 1080), 'mobileLandscape');

  /// Square (1080x1080)
  static const square = _ExportSize(ExportDimensions(1080, 1080), 'square');

  /// Instagram story (1080x1920)
  static const instagramStory = _ExportSize(ExportDimensions(1080, 1920), 'instagramStory');

  /// Twitter post (1200x675)
  static const twitterPost = _ExportSize(ExportDimensions(1200, 675), 'twitterPost');
}

class _ExportSize {

  const _ExportSize(this.size, this.name);
  final ExportDimensions size;
  final String name;
}

/// Size class for export dimensions
class ExportDimensions {

  const ExportDimensions(this.width, this.height);
  final double width;
  final double height;
}

/// Statistics export service interface
///
/// Provides export functionality for all statistics types.
/// Implementations should handle file generation and sharing.
abstract class StatisticsExportService<T extends StatisticsEntity> {
  /// Export statistics data in the specified format
  Future<Uint8List> export(
    T statistics,
    StatisticsExportConfig config,
  );

  /// Generate a filename for the exported file
  String generateFilename(
    StatisticsType type,
    StatisticsPeriod period,
    ExportFormat format, {
    DateTime? timestamp,
  });

  /// Generate a shareable content for social media
  ///
  /// Returns text content that can be shared along with the image
  Future<String> generateShareContent(T statistics);

  /// Check if a format is supported for this statistics type
  bool isFormatSupported(ExportFormat format);

  /// Get available formats for this statistics type
  List<ExportFormat> getSupportedFormats();

  /// Export multiple statistics types at once
  Future<List<Uint8List>> exportMultiple(
    List<T> statisticsList,
    StatisticsExportConfig config,
  );

  /// Generate a preview of the export
  ///
  /// Returns a thumbnail or snippet of what the export will look like
  Future<Uint8List?> generatePreview(
    T statistics,
    ExportFormat format,
  );
}
