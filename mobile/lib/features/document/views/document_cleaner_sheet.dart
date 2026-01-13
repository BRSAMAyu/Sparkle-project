import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart'; // Assuming DS exists
import 'package:sparkle/features/document/controllers/document_controller.dart';
import 'package:sparkle/features/document/models/document_cleaning_model.dart';

class DocumentCleanerSheet extends ConsumerStatefulWidget {
  const DocumentCleanerSheet({required this.onResult, super.key});
  final ValueChanged<String> onResult;

  @override
  ConsumerState<DocumentCleanerSheet> createState() =>
      _DocumentCleanerSheetState();
}

class _DocumentCleanerSheetState extends ConsumerState<DocumentCleanerSheet> {
  File? _selectedFile;
  bool _enableOcr = true;

  @override
  void dispose() {
    // Reset controller when closing sheet
    // ref.read(documentControllerProvider.notifier).reset();
    // Wait, autoDispose handles it usually, but let's be safe if we want to clear state on exit
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'docx', 'pptx'],
    );

    if (result != null) {
      setState(() {
        _selectedFile = File(result.files.single.path!);
      });
    }
  }

  Future<void> _startCleaning() async {
    if (_selectedFile == null) return;
    await ref.read(documentControllerProvider.notifier).startCleaning(
          _selectedFile!,
          enableOcr: _enableOcr,
        );
    // Cleanup temporary files from file_picker cache
    try {
      await FilePicker.platform.clearTemporaryFiles();
    } catch (e) {
      debugPrint('Error clearing temp files: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(documentControllerProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: isDark ? DS.neutral900 : DS.brandPrimary,
        borderRadius: const BorderRadius.vertical(
            top: Radius.circular(DS.borderRadiusXl),),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Drag handle for better UX
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
          Text(
            '智能文档备考',
            style: TextStyle(
              fontSize: 20,
              fontWeight: DS.fontWeightBold,
              color: isDark ? DS.brandPrimary : DS.neutral900,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          state.when(
            data: (taskStatus) {
              if (taskStatus == null) {
                return _buildFilePicker(isDark);
              } else if (taskStatus.status == 'queued' ||
                  taskStatus.status == 'processing') {
                return _buildProgress(taskStatus, isDark);
              } else if (taskStatus.status == 'completed') {
                return _buildSuccess(taskStatus.result, isDark);
              } else {
                return _buildError(taskStatus.message, isDark);
              }
            },
            error: (err, stack) => _buildError(err.toString(), isDark),
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(child: CircularProgressIndicator()),
            ),
          ),
        ],
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
                          Icon(Icons.cloud_upload_outlined,
                              size: 48, color: DS.primaryBase,),
                          const SizedBox(height: 12),
                          Text(
                            '点击选择 PDF/Word/PPT',
                            style: TextStyle(
                                color: isDark ? DS.neutral400 : DS.neutral600,),
                          ),
                        ],
                      )
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.insert_drive_file,
                              size: 48, color: DS.primaryBase,),
                          const SizedBox(height: 12),
                          Text(
                            _selectedFile!.path.split('/').last,
                            style: TextStyle(
                              fontWeight: DS.fontWeightSemiBold,
                              color: isDark ? DS.brandPrimary : DS.neutral900,
                            ),
                          ),
                          TextButton(
                            onPressed: _pickFile,
                            child: Text('更换文件',
                                style: TextStyle(color: DS.primaryBase),),
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
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _selectedFile == null ? null : _startCleaning,
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 54),
              backgroundColor: DS.primaryBase,
              foregroundColor: DS.brandPrimaryConst,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(27),),
              elevation: 0,
            ),
            child: const Text('开始 AI 清洗',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),),
          ),
        ],
      );

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
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: DS.success.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child:
                Icon(Icons.check_circle_rounded, color: DS.success, size: 64),
          ),
          const SizedBox(height: 24),
          Text(
            '文档分析成功！',
            style: TextStyle(
              fontSize: 20,
              fontWeight: DS.fontWeightBold,
              color: isDark ? DS.brandPrimary : DS.neutral900,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '已提取 ${result.charCount} 字符 \n分析模式: ${result.mode == "map_reduce" ? "深度摘要" : "全量清洗"}',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: isDark ? DS.neutral400 : DS.neutral600, height: 1.5,),
          ),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            onPressed: () {
              widget.onResult(result.summary);
              Navigator.pop(context);
            },
            icon: const Icon(Icons.send_rounded),
            label: const Text('将摘要发送到对话',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),),
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 54),
              backgroundColor: DS.success,
              foregroundColor: DS.brandPrimaryConst,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(27),),
            ),
          ),
          const SizedBox(height: 12),
        ],
      );

  Widget _buildError(String message, bool isDark) => Column(
        children: [
          Icon(Icons.error_outline_rounded, color: DS.error, size: 64),
          const SizedBox(height: 24),
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
          TextButton(
            onPressed: () =>
                ref.read(documentControllerProvider.notifier).reset(),
            child: Text('重新尝试',
                style: TextStyle(
                    color: DS.primaryBase, fontWeight: FontWeight.bold,),),
          ),
        ],
      );
}
