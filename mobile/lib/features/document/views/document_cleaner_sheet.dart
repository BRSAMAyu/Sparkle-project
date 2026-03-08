import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/document/controllers/document_controller.dart';
import 'package:sparkle/features/document/models/document_cleaning_model.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';

class DocumentCleanerSheet extends StatelessWidget {
  const DocumentCleanerSheet({required this.onResult, super.key});

  final ValueChanged<String> onResult;

  @override
  Widget build(BuildContext context) => DocumentCleanerPanel(
        onResult: onResult,
        surface: ToolSurface.sheet,
      );
}

class DocumentCleanerPanel extends ConsumerStatefulWidget {
  const DocumentCleanerPanel({
    super.key,
    this.onResult,
    this.surface = ToolSurface.page,
  });

  final ValueChanged<String>? onResult;
  final ToolSurface surface;

  @override
  ConsumerState<DocumentCleanerPanel> createState() =>
      _DocumentCleanerPanelState();
}

class _DocumentCleanerPanelState extends ConsumerState<DocumentCleanerPanel> {
  File? _selectedFile;
  bool _enableOcr = true;
  String _ocrEngine = 'zhipu';

  bool get _isSheet => widget.surface == ToolSurface.sheet;

  @override
  void dispose() {
    ref.read(documentControllerProvider.notifier).reset();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'docx', 'pptx'],
    );

    if (result == null || result.files.single.path == null) {
      return;
    }

    setState(() {
      _selectedFile = File(result.files.single.path!);
    });
  }

  Future<void> _startCleaning() async {
    if (_selectedFile == null) {
      return;
    }

    await ref.read(documentControllerProvider.notifier).startCleaning(
          _selectedFile!,
          enableOcr: _enableOcr,
          ocrEngine: _ocrEngine,
        );

    try {
      await FilePicker.platform.clearTemporaryFiles();
    } catch (e) {
      debugPrint('Error clearing temp files: $e');
    }
  }

  Future<void> _copyResult(String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (!mounted) {
      return;
    }
    AppFeedback.success(context, '清洗结果已复制');
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(documentControllerProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: isDark ? DS.neutral900 : DS.surfacePrimary,
        borderRadius: BorderRadius.vertical(
          top:
              Radius.circular(_isSheet ? DS.borderRadiusXl : DS.borderRadiusLg),
        ),
        border: Border.all(
          color: isDark ? DS.neutral800 : DS.borderSubtle,
        ),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_isSheet)
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 20),
                  decoration: BoxDecoration(
                    color: isDark ? DS.neutral700 : DS.neutral300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '智能文档备考',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: DS.fontWeightBold,
                          color: isDark ? DS.brandPrimary : DS.neutral900,
                        ),
                      ),
                      const SizedBox(height: DS.spacing6),
                      Text(
                        '上传 PDF / Word / PPT，自动走当前已接通的文档清洗与 GLM OCR 链路。',
                        style: TextStyle(
                          color: isDark ? DS.neutral400 : DS.neutral600,
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
                if (_isSheet)
                  SparkleIconButton(
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.of(context).pop(),
                    variant: ButtonVariant.ghost,
                    size: DS.touchTargetMinSize,
                  ),
              ],
            ),
            const SizedBox(height: 20),
            state.when(
              data: (taskStatus) {
                if (taskStatus == null) {
                  return _buildFilePicker(isDark);
                }
                if (taskStatus.status == 'queued' ||
                    taskStatus.status == 'processing') {
                  return _buildProgress(taskStatus, isDark);
                }
                if (taskStatus.status == 'completed' &&
                    taskStatus.result != null) {
                  return _buildSuccess(taskStatus.result!, isDark);
                }
                return _buildError(taskStatus.message, isDark);
              },
              error: (err, stack) => _buildError(err.toString(), isDark),
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: 40),
                child: Center(child: CircularProgressIndicator()),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilePicker(bool isDark) => Column(
        children: [
          GestureDetector(
            onTap: _pickFile,
            child: Container(
              height: 150,
              decoration: BoxDecoration(
                border: Border.all(
                  color: isDark ? DS.neutral700 : DS.neutral300,
                  width: 1.5,
                ),
                borderRadius: BorderRadius.circular(DS.borderRadiusLg),
                color: isDark ? DS.neutral800 : DS.neutral50,
              ),
              child: Center(
                child: _selectedFile == null
                    ? Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.cloud_upload_outlined,
                            size: 48,
                            color: DS.primaryBase,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            '点击选择 PDF / Word / PPT',
                            style: TextStyle(
                              color: isDark ? DS.neutral400 : DS.neutral600,
                            ),
                          ),
                        ],
                      )
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.insert_drive_file,
                            size: 48,
                            color: DS.primaryBase,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _selectedFile!.path.split('/').last,
                            style: TextStyle(
                              fontWeight: DS.fontWeightSemiBold,
                              color: isDark ? DS.brandPrimary : DS.neutral900,
                            ),
                          ),
                          SparkleButton(
                            label: '更换文件',
                            variant: ButtonVariant.ghost,
                            onPressed: _pickFile,
                          ),
                        ],
                      ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '启用 OCR 识别 (扫描件必备)',
                style: TextStyle(color: isDark ? DS.neutral300 : DS.neutral700),
              ),
              Switch(
                value: _enableOcr,
                activeThumbColor: DS.primaryBase,
                onChanged: (val) => setState(() => _enableOcr = val),
              ),
            ],
          ),
          if (_enableOcr) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                Text(
                  'OCR 引擎',
                  style:
                      TextStyle(color: isDark ? DS.neutral300 : DS.neutral700),
                ),
                const Spacer(),
                _buildEngineChip('本地快速', 'local', isDark),
                const SizedBox(width: 12),
                _buildEngineChip('GLM OCR 高精', 'zhipu', isDark),
              ],
            ),
          ],
          const SizedBox(height: DS.xl),
          SparkleButton(
            expand: true,
            label: '开始 AI 清洗',
            onPressed: _selectedFile == null ? null : _startCleaning,
          ),
        ],
      );

  Widget _buildEngineChip(String label, String value, bool isDark) {
    final isSelected = _ocrEngine == value;
    final color =
        isSelected ? DS.primaryBase : (isDark ? DS.neutral700 : DS.neutral200);
    final textColor = isSelected
        ? DS.brandPrimaryConst
        : (isDark ? DS.neutral300 : DS.neutral700);

    return GestureDetector(
      onTap: () => setState(() => _ocrEngine = value),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? color : DS.surfacePrimary.withValues(alpha: 0),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: color, width: 1.5),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: textColor,
            fontSize: 13,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }

  Widget _buildProgress(CleaningTaskStatus status, bool isDark) => Column(
        children: [
          const SizedBox(height: 40),
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 80,
                height: 80,
                child: CircularProgressIndicator(
                  value: status.percent / 100,
                  strokeWidth: 8,
                  backgroundColor: isDark ? DS.neutral800 : DS.neutral100,
                  valueColor: AlwaysStoppedAnimation<Color>(DS.primaryBase),
                ),
              ),
              Text(
                '${status.percent}%',
                style: TextStyle(
                  fontWeight: DS.fontWeightBold,
                  fontSize: 18,
                  color: isDark ? DS.brandPrimary : DS.neutral900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 32),
          Text(
            status.message,
            style: TextStyle(
              fontSize: 16,
              color: isDark ? DS.neutral300 : DS.neutral700,
              fontWeight: DS.fontWeightMedium,
            ),
          ),
          const SizedBox(height: 60),
        ],
      );

  Widget _buildSuccess(CleaningResult result, bool isDark) => Column(
        children: [
          Container(
            padding: const EdgeInsets.all(DS.lg),
            decoration: BoxDecoration(
              color: DS.success.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child:
                Icon(Icons.check_circle_rounded, color: DS.success, size: 64),
          ),
          const SizedBox(height: DS.xl),
          Text(
            '文档分析成功',
            style: TextStyle(
              fontSize: 20,
              fontWeight: DS.fontWeightBold,
              color: isDark ? DS.brandPrimary : DS.neutral900,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '已提取 ${result.charCount} 字符\n分析模式: ${result.mode == "map_reduce" ? "深度摘要" : "全量清洗"}',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: isDark ? DS.neutral400 : DS.neutral600,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 24),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: isDark ? DS.neutral800 : DS.neutral50,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isDark ? DS.neutral700 : DS.neutral200,
              ),
            ),
            child: Text(
              result.summary,
              maxLines: 8,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: isDark ? DS.neutral200 : DS.neutral800,
                height: 1.5,
              ),
            ),
          ),
          const SizedBox(height: 24),
          SparkleButton(
            expand: true,
            onPressed: () {
              widget.onResult?.call(result.summary);
              if (_isSheet) {
                Navigator.pop(context);
              }
            },
            icon: Icon(_isSheet ? Icons.send_rounded : Icons.check_rounded),
            label: _isSheet ? '将摘要发送到对话' : '使用清洗结果',
          ),
          const SizedBox(height: 12),
          SparkleButton.ghost(
            expand: true,
            label: '复制摘要',
            onPressed: () => _copyResult(result.summary),
          ),
        ],
      );

  Widget _buildError(String message, bool isDark) => Column(
        children: [
          Icon(Icons.error_outline_rounded, color: DS.error, size: 64),
          const SizedBox(height: DS.xl),
          Text(
            '清洗处理失败',
            style: TextStyle(
              fontSize: 20,
              fontWeight: DS.fontWeightBold,
              color: isDark ? DS.brandPrimary : DS.neutral900,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            message,
            textAlign: TextAlign.center,
            style: TextStyle(color: DS.error),
          ),
          const SizedBox(height: 32),
          SparkleButton(
            label: '重新尝试',
            variant: ButtonVariant.ghost,
            onPressed: () =>
                ref.read(documentControllerProvider.notifier).reset(),
          ),
        ],
      );
}
