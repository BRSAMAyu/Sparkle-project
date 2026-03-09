import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/document/controllers/document_controller.dart';
import 'package:sparkle/features/document/models/document_cleaning_model.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

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
      AppFeedback.info(context, '请先选择一个文件');
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
    final accent = DS.brandPrimary;
    final fileName = _selectedFile?.path.split('/').last;
    final extension = fileName?.split('.').last.toUpperCase();
    final fileSize = _selectedFile == null
        ? null
        : '${(_selectedFile!.lengthSync() / (1024 * 1024)).toStringAsFixed(1)} MB';

    return ToolShell(
      surface: widget.surface,
      icon: Icons.auto_awesome_motion_rounded,
      title: '文档清洗',
      subtitle: '把扫描件、讲义和课件整理成可读文本。支持真实 GLM OCR 链路，适合笔记沉淀和资料预处理。',
      accentColor: accent,
      headerAction: _isSheet
          ? SparkleIconButton(
              icon: const Icon(Icons.close_rounded),
              onPressed: () => Navigator.of(context).pop(),
              variant: ButtonVariant.ghost,
            )
          : null,
      heroChips: [
        ToolHeroChip(
          label: _enableOcr ? 'OCR 已开启' : '纯文本清洗',
          accentColor: accent,
          icon: _enableOcr ? Icons.visibility_rounded : Icons.notes_rounded,
        ),
        ToolHeroChip(
          label: fileName == null ? '支持 PDF / DOCX / PPTX' : extension ?? '文件已选',
          accentColor: accent,
          icon: Icons.insert_drive_file_rounded,
        ),
      ],
      body: state.when(
        data: (taskStatus) => SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                spacing: DS.spacing12,
                runSpacing: DS.spacing12,
                children: [
                  ToolMetricCard(
                    label: '引擎',
                    value: _enableOcr
                        ? (_ocrEngine == 'zhipu' ? 'GLM OCR' : '本地 OCR')
                        : '跳过 OCR',
                    accentColor: accent,
                    icon: Icons.tune_rounded,
                    caption: '扫描件建议启用 GLM OCR',
                  ),
                  ToolMetricCard(
                    label: '文件体积',
                    value: fileSize ?? '--',
                    accentColor: accent,
                    icon: Icons.sd_storage_rounded,
                    caption: fileName == null ? '未选择文件' : '当前待处理文件',
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              if (taskStatus == null) _buildSetupCard(accent, fileName, extension),
              if (taskStatus != null &&
                  (taskStatus.status == 'queued' ||
                      taskStatus.status == 'processing'))
                _buildProgress(taskStatus, accent),
              if (taskStatus != null &&
                  taskStatus.status == 'completed' &&
                  taskStatus.result != null)
                _buildSuccess(taskStatus.result!, accent),
              if (taskStatus != null &&
                  taskStatus.status != 'queued' &&
                  taskStatus.status != 'processing' &&
                  !(taskStatus.status == 'completed' &&
                      taskStatus.result != null))
                _buildError(taskStatus.message, accent),
            ],
          ),
        ),
        error: (err, stack) => _buildError(err.toString(), accent),
        loading: () => Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: DS.spacing32),
            child: CircularProgressIndicator(color: accent),
          ),
        ),
      ),
    );
  }

  Widget _buildSetupCard(Color accent, String? fileName, String? extension) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: '文件选择',
            subtitle: '先选文件，再决定是否启用 OCR。识别结果会自动回流到文档清洗任务。',
            child: InkWell(
              onTap: _pickFile,
              borderRadius: BorderRadius.circular(24),
              child: Ink(
                padding: const EdgeInsets.all(DS.spacing20),
                decoration: BoxDecoration(
                  color: DS.surfacePrimary,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: fileName == null
                    ? Column(
                        children: [
                          Icon(
                            Icons.cloud_upload_rounded,
                            size: 44,
                            color: accent,
                          ),
                          const SizedBox(height: DS.spacing12),
                          Text(
                            '点击选择文件',
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                          const SizedBox(height: DS.spacing6),
                          Text(
                            '支持 PDF、DOCX、PPTX；扫描件推荐开启 OCR。',
                            textAlign: TextAlign.center,
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.5,
                                ),
                          ),
                        ],
                      )
                    : Row(
                        children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              color: accent.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Icon(
                              Icons.insert_drive_file_rounded,
                              color: accent,
                            ),
                          ),
                          const SizedBox(width: DS.spacing16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  fileName,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleMedium
                                      ?.copyWith(
                                        color: DS.textPrimary,
                                        fontWeight: DS.fontWeightBold,
                                      ),
                                ),
                                const SizedBox(height: DS.spacing4),
                                Text(
                                  extension ?? '文档文件',
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(color: DS.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                          SparkleButton(
                            label: '更换',
                            variant: ButtonVariant.ghost,
                            onPressed: _pickFile,
                          ),
                        ],
                      ),
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: '处理策略',
            subtitle: '扫描件建议开启 OCR；源文件已有文字层时可关闭 OCR 提升速度。',
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '启用 OCR 识别',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightSemiBold,
                            ),
                      ),
                    ),
                    Switch(
                      value: _enableOcr,
                      onChanged: (value) => setState(() => _enableOcr = value),
                    ),
                  ],
                ),
                if (_enableOcr) ...[
                  const SizedBox(height: DS.spacing16),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Wrap(
                      spacing: DS.spacing10,
                      runSpacing: DS.spacing10,
                      children: [
                        ToolChoiceChip(
                          label: '本地快速',
                          selected: _ocrEngine == 'local',
                          onTap: () => setState(() => _ocrEngine = 'local'),
                          accentColor: accent,
                          icon: Icons.speed_rounded,
                        ),
                        ToolChoiceChip(
                          label: 'GLM OCR 高精',
                          selected: _ocrEngine == 'zhipu',
                          onTap: () => setState(() => _ocrEngine = 'zhipu'),
                          accentColor: accent,
                          icon: Icons.auto_awesome_rounded,
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: DS.spacing20),
          SparkleButton(
            expand: true,
            label: '开始 AI 清洗',
            onPressed: _selectedFile == null ? null : _startCleaning,
            icon: const Icon(Icons.auto_fix_high_rounded),
          ),
        ],
      );

  Widget _buildProgress(CleaningTaskStatus status, Color accent) =>
      ToolSectionCard(
        accentColor: accent,
        title: '处理中',
        subtitle: '正在上传、解析和清洗文档，进度会实时更新。',
        child: Column(
          children: [
            Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 104,
                  height: 104,
                  child: CircularProgressIndicator(
                    value: status.percent / 100,
                    strokeWidth: 10,
                    backgroundColor: DS.surfaceTertiary,
                    valueColor: AlwaysStoppedAnimation<Color>(accent),
                  ),
                ),
                Text(
                  '${status.percent}%',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing20),
            Text(
              status.message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemiBold,
                  ),
            ),
          ],
        ),
      );

  Widget _buildSuccess(CleaningResult result, Color accent) => Column(
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: '清洗成功',
            subtitle: '结果已经整理完毕，你可以复制、发送或继续做下一轮处理。',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Wrap(
                  spacing: DS.spacing12,
                  runSpacing: DS.spacing12,
                  children: [
                    ToolMetricCard(
                      label: '字符数',
                      value: '${result.charCount ?? 0}',
                      accentColor: accent,
                      icon: Icons.text_fields_rounded,
                    ),
                    ToolMetricCard(
                      label: '模式',
                      value: result.mode == 'map_reduce' ? '深度摘要' : '全量清洗',
                      accentColor: accent,
                      icon: Icons.layers_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                Container(
                  padding: const EdgeInsets.all(DS.spacing18),
                  decoration: BoxDecoration(
                    color: DS.surfacePrimary,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: Text(
                    result.summary,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: DS.textPrimary,
                          height: 1.65,
                        ),
                  ),
                ),
                if ((result.fullTextPreview ?? '').isNotEmpty) ...[
                  const SizedBox(height: DS.spacing16),
                  Text(
                    '全文预览',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    result.fullTextPreview!,
                    maxLines: 8,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.6,
                        ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Row(
            children: [
              Expanded(
                child: SparkleButton(
                  label: _isSheet ? '发送到对话' : '使用结果',
                  onPressed: () {
                    widget.onResult?.call(result.summary);
                    if (_isSheet) {
                      Navigator.pop(context);
                    }
                  },
                  icon: Icon(
                    _isSheet ? Icons.send_rounded : Icons.arrow_forward_rounded,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: SparkleButton(
                  label: '复制摘要',
                  variant: ButtonVariant.ghost,
                  onPressed: () => _copyResult(result.summary),
                  icon: const Icon(Icons.copy_rounded),
                ),
              ),
            ],
          ),
        ],
      );

  Widget _buildError(String message, Color accent) => ToolSectionCard(
        accentColor: DS.error,
        title: '清洗失败',
        subtitle: '链路已经返回错误信息，可以直接重试或更换文件。',
        child: Column(
          children: [
            ToolEmptyState(
              icon: Icons.error_outline_rounded,
              title: '当前任务未完成',
              description: message,
              accentColor: DS.error,
            ),
            const SizedBox(height: DS.spacing16),
            SparkleButton(
              label: '重新尝试',
              variant: ButtonVariant.ghost,
              onPressed: () => ref.read(documentControllerProvider.notifier).reset(),
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
      );
}
