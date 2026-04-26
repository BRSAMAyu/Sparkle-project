import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/file/file.dart';

class FilePickerWithPresignedUpload extends ConsumerStatefulWidget {
  const FilePickerWithPresignedUpload({
    super.key,
    this.groupId,
    this.onUploaded,
    this.onError,
    this.secondaryActionLabel,
    this.onSecondaryAction,
  });

  final String? groupId;
  final void Function(StoredFile file)? onUploaded;
  final void Function(String message)? onError;
  final String? secondaryActionLabel;
  final VoidCallback? onSecondaryAction;

  @override
  ConsumerState<FilePickerWithPresignedUpload> createState() =>
      _FilePickerWithPresignedUploadState();
}

class _FilePickerWithPresignedUploadState
    extends ConsumerState<FilePickerWithPresignedUpload> {
  File? _selectedFile;
  double _progress = 0;
  bool _isUploading = false;
  String? _error;
  UploadSession? _resumeSession;

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: [
        'pdf',
        'docx',
        'pptx',
        'txt',
        'png',
        'jpg',
        'jpeg',
        'gif',
      ],
    );

    if (result != null && result.files.single.path != null) {
      setState(() {
        _selectedFile = File(result.files.single.path!);
        _error = null;
        _progress = 0;
        _resumeSession = null;
      });
    }
  }

  Future<void> _startUpload() async {
    if (_selectedFile == null || _isUploading) return;
    setState(() {
      _isUploading = true;
      _error = null;
    });

    try {
      final service = ref.read(fileUploadServiceProvider);
      final file = _resumeSession == null
          ? await service.uploadFile(
              _selectedFile!,
              groupId: widget.groupId,
              visibility: widget.groupId == null ? 'private' : 'group',
              onProgress: (progress) {
                if (mounted) {
                  setState(() {
                    _progress = progress;
                  });
                }
              },
            )
          : await service.resumeUpload(
              _selectedFile!,
              _resumeSession!,
              groupId: widget.groupId,
              visibility: widget.groupId == null ? 'private' : 'group',
              onProgress: (progress) {
                if (mounted) {
                  setState(() {
                    _progress = progress;
                  });
                }
              },
            );
      _resumeSession = null;
      widget.onUploaded?.call(file);
    } on UploadInterruptedException catch (e) {
      final l10n = context.l10n;
      if (mounted) {
        setState(() {
          _resumeSession = e.session;
          _error = l10n.fileUploadNetworkError;
        });
      }
      widget.onError?.call(l10n.fileUploadNetworkError);
    } catch (e) {
      final message = context.l10n.fileUploadFailed(e.toString());
      widget.onError?.call(message);
      if (mounted) {
        setState(() {
          _error = message;
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fileName = _selectedFile?.path.split('/').last;
    final fileType = fileName?.split('.').last.toUpperCase();
    final fileSize = _selectedFile == null
        ? null
        : '${(_selectedFile!.lengthSync() / 1024 / 1024).toStringAsFixed(1)} MB';

    return SafeArea(
      top: false,
      child: SingleChildScrollView(
        child: Container(
          padding: const EdgeInsets.all(DS.lg),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: const BorderRadius.vertical(
              top: Radius.circular(DS.borderRadiusXl),
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: DS.surfaceTertiary,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Icon(
                      Icons.upload_file_rounded,
                      color: DS.brandPrimary,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.l10n.fileUploadTitle,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: DS.fontWeightBold,
                            color: DS.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          context.l10n.fileUploadDesc,
                          style: TextStyle(
                            color: DS.textSecondary,
                            height: 1.45,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              Wrap(
                spacing: DS.spacing12,
                runSpacing: DS.spacing12,
                children: [
                  _UploadMetric(
                    label: context.l10n.fileUploadType,
                    value: fileType ?? '--',
                    icon: Icons.insert_drive_file_outlined,
                  ),
                  _UploadMetric(
                    label: context.l10n.fileUploadSize,
                    value: fileSize ?? '--',
                    icon: Icons.sd_storage_outlined,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              GestureDetector(
                onTap: _isUploading ? null : _pickFile,
                child: Container(
                  constraints: const BoxConstraints(minHeight: 148),
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: DS.surfaceTertiary,
                      width: 1.5,
                    ),
                    borderRadius: BorderRadius.circular(DS.borderRadiusLg),
                    color: isDark ? DS.surfaceTertiary : DS.neutral50,
                  ),
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing16),
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
                                  context.l10n.fileUploadClickToSelect,
                                  style: TextStyle(
                                    color: DS.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  context.l10n.fileUploadSupportedFormats,
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: DS.textTertiary,
                                  ),
                                ),
                              ],
                            )
                          : Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.insert_drive_file,
                                  size: 40,
                                  color: DS.primaryBase,
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  fileName ?? '',
                                  textAlign: TextAlign.center,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontWeight: DS.fontWeightSemiBold,
                                    color: DS.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  fileSize == null
                                      ? context.l10n.fileUploadSelected
                                      : context.l10n.fileUploadFormat(fileType ?? context.l10n.fileUploadType, fileSize),
                                  style: TextStyle(
                                    color: DS.textSecondary,
                                  ),
                                ),
                                if (_isUploading) ...[
                                  const SizedBox(height: 8),
                                  Text(
                                    context.l10n.fileUploadProgress('${(_progress * 100).toStringAsFixed(0)}'),
                                    style: TextStyle(
                                      color: DS.textSecondary,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    _error!,
                    style: TextStyle(color: DS.error, fontSize: 12),
                  ),
                ),
              LayoutBuilder(
                builder: (context, constraints) {
                  final compact = constraints.maxWidth < 460;
                  final l10n = context.l10n;
                  final pickButton = SparkleButton(
                    expand: true,
                    label: _selectedFile == null ? l10n.fileUploadSelect : l10n.fileUploadReselect,
                    variant: ButtonVariant.ghost,
                    onPressed: _isUploading ? null : _pickFile,
                  );
                  final uploadButton = SparkleButton(
                    expand: true,
                    label: _resumeSession == null ? l10n.fileUploadStart : l10n.fileUploadResume,
                    onPressed: _selectedFile == null || _isUploading
                        ? null
                        : _startUpload,
                    loading: _isUploading,
                  );

                  if (compact) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (widget.secondaryActionLabel != null &&
                            widget.onSecondaryAction != null) ...[
                          SparkleButton(
                            expand: true,
                            label: widget.secondaryActionLabel!,
                            variant: ButtonVariant.ghost,
                            onPressed: widget.onSecondaryAction,
                            icon: const Icon(Icons.auto_fix_high_rounded),
                          ),
                          const SizedBox(height: 12),
                        ],
                        pickButton,
                        const SizedBox(height: 12),
                        uploadButton,
                      ],
                    );
                  }

                  return Row(
                    children: [
                      if (widget.secondaryActionLabel != null &&
                          widget.onSecondaryAction != null) ...[
                        Expanded(
                          child: SparkleButton(
                            expand: true,
                            label: widget.secondaryActionLabel!,
                            variant: ButtonVariant.ghost,
                            onPressed: widget.onSecondaryAction,
                            icon: const Icon(Icons.auto_fix_high_rounded),
                          ),
                        ),
                        const SizedBox(width: 12),
                      ],
                      Expanded(child: pickButton),
                      const SizedBox(width: 12),
                      Expanded(child: uploadButton),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _UploadMetric extends StatelessWidget {
  const _UploadMetric({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(minWidth: 132),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing10,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: DS.brandPrimary),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: 11,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}
