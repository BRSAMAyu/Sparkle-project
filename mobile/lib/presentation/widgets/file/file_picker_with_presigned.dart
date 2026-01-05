import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/file.dart';

class FilePickerWithPresignedUpload extends ConsumerStatefulWidget {
  const FilePickerWithPresignedUpload({
    super.key,
    this.groupId,
    this.onUploaded,
    this.onError,
  });

  final String? groupId;
  final void Function(StoredFile file)? onUploaded;
  final void Function(String message)? onError;

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
      if (mounted) {
        setState(() {
          _resumeSession = e.session;
          _error = '网络中断，可点击继续上传';
        });
      }
      widget.onError?.call('网络中断，可点击继续上传');
    } catch (e) {
      final message = '上传失败: $e';
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
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: isDark ? DS.neutral700 : DS.neutral300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          Text(
            '上传文件',
            style: TextStyle(
              fontSize: 18,
              fontWeight: DS.fontWeightBold,
              color: isDark ? DS.brandPrimary : DS.neutral900,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: _isUploading ? null : _pickFile,
            child: Container(
              height: 140,
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
                            '点击选择文件',
                            style: TextStyle(
                                color: isDark ? DS.neutral400 : DS.neutral600,),
                          ),
                        ],
                      )
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.insert_drive_file,
                              size: 40, color: DS.primaryBase,),
                          const SizedBox(height: 8),
                          Text(
                            _selectedFile!.path.split('/').last,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontWeight: DS.fontWeightSemiBold,
                              color: isDark ? DS.brandPrimary : DS.neutral900,
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (_isUploading)
                            Text(
                              '上传中 ${(_progress * 100).toStringAsFixed(0)}%',
                              style: TextStyle(
                                  color:
                                      isDark ? DS.neutral400 : DS.neutral600,),
                            ),
                        ],
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
          ElevatedButton(
            onPressed:
                _selectedFile == null || _isUploading ? null : _startUpload,
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 52),
              backgroundColor: DS.primaryBase,
              foregroundColor: DS.brandPrimaryConst,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(26),),
              elevation: 0,
            ),
            child: _isUploading
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(
                    _resumeSession == null ? '开始上传' : '继续上传',
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold,),
                  ),
          ),
        ],
      ),
    );
  }
}
