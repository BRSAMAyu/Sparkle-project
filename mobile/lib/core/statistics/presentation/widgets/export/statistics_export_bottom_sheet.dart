import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Export option button widget
class ExportOptionButton extends StatelessWidget {

  const ExportOptionButton({
    required this.format, required this.icon, required this.label, required this.description, required this.onTap, super.key,
    this.isSelected = false,
  });
  /// Export format
  final ExportFormat format;

  /// Icon for the option
  final IconData icon;

  /// Label for the option
  final String label;

  /// Description of the format
  final String description;

  /// Whether this option is selected
  final bool isSelected;

  /// Callback when tapped
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: StatisticsAnimationConfig.fast,
        curve: StatisticsAnimationConfig.easeOut,
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: isSelected ? DS.brandPrimary.withValues(alpha: 0.1) : DS.neutral50,
          borderRadius: BorderRadius.circular(DS.borderRadiusLG),
          border: Border.all(
            color: isSelected ? DS.brandPrimary : DS.neutral200,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: isSelected ? DS.brandPrimary : DS.white,
                borderRadius: BorderRadius.circular(DS.borderRadiusMD),
              ),
              child: Icon(
                icon,
                color: isSelected ? DS.white : DS.neutral600,
                size: 24,
              ),
            ),
            const SizedBox(height: DS.sm),
            Text(
              label,
              style: DS.bodyStyle.copyWith(
                fontWeight: DS.fontWeightMedium,
                color: isSelected ? DS.brandPrimary : DS.neutral700,
              ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              description,
              style: DS.captionStyle.copyWith(
                color: DS.neutral400,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
}

/// Bottom sheet for exporting statistics
class StatisticsExportBottomSheet extends StatefulWidget {

  const StatisticsExportBottomSheet({
    required this.onExport, super.key,
    this.availableFormats = const [
      ExportFormat.json,
      ExportFormat.csv,
      ExportFormat.pngReport,
    ],
    this.selectedFormat,
    this.showChartOptions = true,
    this.includeCharts = true,
  });
  /// Available export formats
  final List<ExportFormat> availableFormats;

  /// Currently selected format
  final ExportFormat? selectedFormat;

  /// Callback when export is confirmed
  final Future<void> Function(ExportFormat format) onExport;

  /// Whether to show chart options
  final bool showChartOptions;

  /// Initial value for include charts
  final bool includeCharts;

  @override
  State<StatisticsExportBottomSheet> createState() =>
      _StatisticsExportBottomSheetState();

  /// Show the bottom sheet
  static Future<void> show({
    required BuildContext context,
    required Future<void> Function(ExportFormat format) onExport, List<ExportFormat> availableFormats = const [
      ExportFormat.json,
      ExportFormat.csv,
      ExportFormat.pngReport,
    ],
    ExportFormat? selectedFormat,
    bool showChartOptions = true,
    bool includeCharts = true,
  }) => showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => StatisticsExportBottomSheet(
        availableFormats: availableFormats,
        selectedFormat: selectedFormat,
        onExport: onExport,
        showChartOptions: showChartOptions,
        includeCharts: includeCharts,
      ),
    );
}

class _StatisticsExportBottomSheetState extends State<StatisticsExportBottomSheet> {
  late ExportFormat? _selectedFormat;
  late bool _includeCharts;
  bool _isExporting = false;

  @override
  void initState() {
    super.initState();
    _selectedFormat = widget.selectedFormat;
    _includeCharts = widget.includeCharts;
  }

  @override
  Widget build(BuildContext context) => Container(
      decoration: const BoxDecoration(
        color: DS.white,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(DS.borderRadiusXL),
          topRight: Radius.circular(DS.borderRadiusXL),
        ),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(DS.xl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(),
              const SizedBox(height: DS.lg),
              _buildFormatOptions(),
              if (widget.showChartOptions) ...[
                const SizedBox(height: DS.lg),
                _buildChartOptions(),
              ],
              const SizedBox(height: DS.xl),
              _buildExportButton(),
            ],
          ),
        ),
      ),
    );

  Widget _buildHeader() => Row(
      children: [
        Text(
          '导出统计数据',
          style: DS.headlineStyle.copyWith(
            fontSize: 20,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const Spacer(),
        IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.close),
          style: IconButton.styleFrom(
            backgroundColor: DS.neutral100,
          ),
        ),
      ],
    );

  Widget _buildFormatOptions() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '选择导出格式',
          style: DS.bodyStyle.copyWith(
            fontWeight: DS.fontWeightMedium,
            color: DS.neutral600,
          ),
        ),
        const SizedBox(height: DS.md),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 3,
          mainAxisSpacing: DS.md,
          crossAxisSpacing: DS.md,
          childAspectRatio: 1.2,
          children: widget.availableFormats.map((format) => ExportOptionButton(
              format: format,
              icon: _getIconForFormat(format),
              label: format.label,
              description: _getDescriptionForFormat(format),
              isSelected: _selectedFormat == format,
              onTap: () {
                setState(() {
                  _selectedFormat = format;
                });
              },
            ),).toList(),
        ),
      ],
    );

  Widget _buildChartOptions() => Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.neutral50,
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
      ),
      child: Row(
        children: [
          Icon(
            Icons.bar_chart,
            color: DS.neutral600,
            size: 20,
          ),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Text(
              '包含图表数据',
              style: DS.bodyStyle.copyWith(
                color: DS.neutral700,
              ),
            ),
          ),
          Switch(
            value: _includeCharts,
            onChanged: (value) {
              setState(() {
                _includeCharts = value;
              });
            },
            activeThumbColor: DS.brandPrimary,
          ),
        ],
      ),
    );

  Widget _buildExportButton() {
    final canExport = _selectedFormat != null;

    return ElevatedButton(
      onPressed: canExport && !_isExporting
          ? _handleExport
          : null,
      style: ElevatedButton.styleFrom(
        backgroundColor: DS.brandPrimary,
        foregroundColor: DS.white,
        disabledBackgroundColor: DS.neutral200,
        padding: const EdgeInsets.symmetric(vertical: DS.md),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        ),
      ),
      child: _isExporting
          ? const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            )
          : Text(
              '导出为 ${_selectedFormat?.label ?? ''}',
              style: DS.bodyStyle.copyWith(
                fontWeight: DS.fontWeightMedium,
              ),
            ),
    );
  }

  IconData _getIconForFormat(ExportFormat format) {
    switch (format) {
      case ExportFormat.json:
        return Icons.code;
      case ExportFormat.csv:
        return Icons.table_chart;
      case ExportFormat.pngReport:
        return Icons.image;
      case ExportFormat.pdfReport:
        return Icons.picture_as_pdf;
    }
  }

  String _getDescriptionForFormat(ExportFormat format) {
    switch (format) {
      case ExportFormat.json:
        return '结构化数据';
      case ExportFormat.csv:
        return '电子表格';
      case ExportFormat.pngReport:
        return '高清图片';
      case ExportFormat.pdfReport:
        return 'PDF文档';
    }
  }

  Future<void> _handleExport() async {
    if (_selectedFormat == null || _isExporting) return;

    setState(() {
      _isExporting = true;
    });

    try {
      await widget.onExport(_selectedFormat!);
      if (mounted) {
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('导出失败: $e'),
            backgroundColor: DS.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isExporting = false;
        });
      }
    }
  }
}

/// Share bottom sheet for sharing statistics
class StatisticsShareBottomSheet extends StatelessWidget {

  const StatisticsShareBottomSheet({
    required this.options, required this.onShare, super.key,
  });
  /// Available share options
  final List<ShareOption> options;

  /// Callback when an option is selected
  final Future<void> Function(ShareOption option) onShare;

  @override
  Widget build(BuildContext context) => Container(
      decoration: const BoxDecoration(
        color: DS.white,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(DS.borderRadiusXL),
          topRight: Radius.circular(DS.borderRadiusXL),
        ),
      ),
      padding: const EdgeInsets.all(DS.xl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHeader(context),
          const SizedBox(height: DS.lg),
          _buildShareOptions(),
        ],
      ),
    );

  Widget _buildHeader(BuildContext context) => Row(
      children: [
        Text(
          '分享统计数据',
          style: DS.headlineStyle.copyWith(
            fontSize: 20,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const Spacer(),
        IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.close),
          style: IconButton.styleFrom(
            backgroundColor: DS.neutral100,
          ),
        ),
      ],
    );

  Widget _buildShareOptions() => GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 4,
      mainAxisSpacing: DS.lg,
      crossAxisSpacing: DS.md,
      children: options.map((option) => _ShareOptionButton(
          option: option,
          onTap: () async {
            await onShare(option);
            if (option.closeOnTap) {
              // Navigator.pop(context);
            }
          },
        ),).toList(),
    );

  /// Show the share bottom sheet
  static Future<void> show({
    required BuildContext context,
    required List<ShareOption> options,
    required Future<void> Function(ShareOption option) onShare,
  }) => showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => StatisticsShareBottomSheet(
        options: options,
        onShare: onShare,
      ),
    );
}

class _ShareOptionButton extends StatelessWidget {

  const _ShareOptionButton({
    required this.option,
    required this.onTap,
  });
  final ShareOption option;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: option.color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(DS.borderRadiusLG),
            ),
            child: Icon(
              option.icon,
              color: option.color,
              size: 28,
            ),
          ),
          const SizedBox(height: DS.sm),
          Text(
            option.label,
            style: DS.captionStyle.copyWith(
              color: DS.neutral600,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
}

/// Share option data class
class ShareOption {

  const ShareOption({
    required this.id,
    required this.label,
    required this.icon,
    required this.color,
    required this.action, this.closeOnTap = true,
  });
  /// Unique identifier
  final String id;

  /// Display label
  final String label;

  /// Icon for the option
  final IconData icon;

  /// Color for the icon
  final Color color;

  /// Whether to close bottom sheet after share
  final bool closeOnTap;

  /// Share action
  final Future<void> Function() action;
}

/// Common share options
class CommonShareOptions {
  /// Share to WeChat
  static ShareOption weChat({required Future<void> Function() action}) => ShareOption(
      id: 'wechat',
      label: '微信',
      icon: Icons.chat,
      color: const Color(0xFF07C160),
      action: action,
    );

  /// Share to WeChat Moments
  static ShareOption weChatMoments({required Future<void> Function() action}) => ShareOption(
      id: 'wechat_moments',
      label: '朋友圈',
      icon: Icons.photo_camera,
      color: const Color(0xFF07C160),
      action: action,
    );

  /// Save to gallery
  static ShareOption saveToGallery({required Future<void> Function() action}) => ShareOption(
      id: 'save',
      label: '保存图片',
      icon: Icons.download,
      color: const Color(0xFF6366F1),
      action: action,
    );

  /// Copy link
  static ShareOption copyLink({required Future<void> Function() action}) => ShareOption(
      id: 'copy_link',
      label: '复制链接',
      icon: Icons.link,
      color: const Color(0xFF6B7280),
      action: action,
    );

  /// More options
  static ShareOption more({required Future<void> Function() action}) => ShareOption(
      id: 'more',
      label: '更多',
      icon: Icons.more_horiz,
      color: const Color(0xFF6B7280),
      action: action,
    );
}
