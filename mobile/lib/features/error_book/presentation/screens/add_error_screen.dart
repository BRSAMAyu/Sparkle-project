import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/question_image_reference.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_question_image.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';
import 'package:sparkle/features/file/data/services/file_upload_service.dart';

class AddErrorScreen extends ConsumerStatefulWidget {
  const AddErrorScreen({
    super.key,
    this.errorId,
    this.initialError,
  });

  final String? errorId;
  final ErrorRecord? initialError;

  bool get isEditMode => errorId != null;

  @override
  ConsumerState<AddErrorScreen> createState() => _AddErrorScreenState();
}

class _AddErrorScreenState extends ConsumerState<AddErrorScreen> {
  final _formKey = GlobalKey<FormState>();
  final _questionController = TextEditingController();
  final _userAnswerController = TextEditingController();
  final _correctAnswerController = TextEditingController();
  final _chapterController = TextEditingController();
  final _imagePicker = ImagePicker();

  String _selectedSubject = 'math';
  bool _isSubmitting = false;
  bool _isUploadingImage = false;
  double _uploadProgress = 0;
  bool _hasHydratedInitialValues = false;
  XFile? _localQuestionImage;
  String? _questionImageReference;

  String? get _originalQuestionImageReference =>
      widget.initialError?.questionImageUrl;

  bool get _hasQuestionImage =>
      (_questionImageReference != null &&
          _questionImageReference!.trim().isNotEmpty) ||
      _localQuestionImage != null;

  @override
  void dispose() {
    _questionController.dispose();
    _userAnswerController.dispose();
    _correctAnswerController.dispose();
    _chapterController.dispose();
    super.dispose();
  }

  void _hydrateFromError(ErrorRecord error) {
    _questionController.text = error.questionText;
    _userAnswerController.text = error.userAnswer;
    _correctAnswerController.text = error.correctAnswer;
    _chapterController.text = error.chapter ?? '';
    _selectedSubject = error.subject;
    _questionImageReference = error.questionImageUrl;
    _hasHydratedInitialValues = true;
  }

  Future<void> _pickQuestionImage() async {
    if (_isUploadingImage) return;

    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    final image = await _imagePicker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 85,
      maxWidth: 2048,
    );
    if (image == null) {
      return;
    }

    if (!mounted) return;
    setState(() {
      _localQuestionImage = image;
      _uploadProgress = 0;
    });

    await _uploadQuestionImage(image);
  }

  Future<void> _uploadQuestionImage(XFile image) async {
    setState(() {
      _isUploadingImage = true;
    });

    try {
      final storedFile = await ref.read(fileUploadServiceProvider).uploadFile(
        File(image.path),
        visibility: 'private',
        onProgress: (progress) {
          if (!mounted) return;
          setState(() {
            _uploadProgress = progress;
          });
        },
      );

      if (!mounted) return;
      setState(() {
        _questionImageReference = buildSparkleFileReference(storedFile.id);
      });
      AppFeedback.success(context, '题目图片上传成功');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _localQuestionImage = null;
      });
      AppFeedback.error(context, '图片上传失败: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isUploadingImage = false;
          _uploadProgress = 0;
        });
      }
    }
  }

  void _removeQuestionImage() {
    setState(() {
      _localQuestionImage = null;
      _questionImageReference = '';
      _uploadProgress = 0;
      _isUploadingImage = false;
    });
  }

  String? _validateQuestionText(String? value) {
    final content = value?.trim() ?? '';
    if (content.isEmpty && !_hasQuestionImage) {
      return '请输入题目内容或上传题目图片';
    }
    if (content.isNotEmpty && content.length < 5) {
      return '题目内容至少需要 5 个字符';
    }
    if (content.length > 5000) {
      return '题目内容过长（最多 5000 字符）';
    }
    return null;
  }

  String? _questionImageForCreate() {
    final reference = _questionImageReference?.trim();
    if (reference == null || reference.isEmpty) {
      return null;
    }
    return reference;
  }

  String? _questionImageForUpdate() {
    final current = (_questionImageReference ?? '').trim();
    final original = (_originalQuestionImageReference ?? '').trim();
    if (current == original) {
      return null;
    }
    return current;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_isSubmitting) return;
    if (_isUploadingImage) {
      AppFeedback.info(context, '题目图片仍在上传，请稍候');
      return;
    }

    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    setState(() => _isSubmitting = true);

    try {
      if (widget.isEditMode) {
        await ref.read(errorOperationsProvider.notifier).updateError(
              widget.errorId!,
              questionText: _questionController.text.trim(),
              userAnswer: _userAnswerController.text.trim(),
              correctAnswer: _correctAnswerController.text.trim(),
              subject: _selectedSubject,
              chapter: _chapterController.text.trim().isEmpty
                  ? null
                  : _chapterController.text.trim(),
              questionImageUrl: _questionImageForUpdate(),
            );
      } else {
        await ref.read(errorOperationsProvider.notifier).createError(
              questionText: _questionController.text.trim(),
              userAnswer: _userAnswerController.text.trim(),
              correctAnswer: _correctAnswerController.text.trim(),
              subject: _selectedSubject,
              chapter: _chapterController.text.trim().isEmpty
                  ? null
                  : _chapterController.text.trim(),
              questionImageUrl: _questionImageForCreate(),
            );
      }

      if (!mounted) return;
      AppFeedback.success(
        context,
        widget.isEditMode ? '错题已更新' : '错题已添加，AI 正在分析中...',
      );
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          widget.isEditMode ? '更新失败: $e' : '添加失败: $e',
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  Widget _buildImagePreview(BuildContext context) {
    final theme = Theme.of(context);
    final imageReference = _questionImageReference?.trim();

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: theme.colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.image_outlined, color: theme.colorScheme.primary),
              const SizedBox(width: DS.spacing8),
              Text(
                '题目图片（可选）',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const Spacer(),
              if (_hasQuestionImage)
                TextButton.icon(
                  onPressed: _isUploadingImage ? null : _removeQuestionImage,
                  icon: const Icon(Icons.delete_outline),
                  label: const Text('移除'),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '支持拍照后的题目截图或试卷照片。若未填写题干，AI 会优先尝试 OCR 识别图片文字。',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              height: 1.5,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: ColoredBox(
              color: theme.colorScheme.surfaceContainerHighest,
              child: SizedBox(
                width: double.infinity,
                height: 220,
                child: _localQuestionImage != null
                    ? Image.file(
                        File(_localQuestionImage!.path),
                        fit: BoxFit.cover,
                      )
                    : (imageReference != null && imageReference.isNotEmpty)
                        ? ErrorQuestionImage(
                            imageReference: imageReference,
                            height: 220,
                          )
                        : Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.photo_library_outlined,
                                size: 42,
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                              const SizedBox(height: DS.spacing12),
                              Text(
                                '还没有上传题目图片',
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          if (_isUploadingImage) ...[
            LinearProgressIndicator(value: _uploadProgress),
            const SizedBox(height: DS.spacing8),
            Text(
              '上传中 ${(_uploadProgress * 100).toStringAsFixed(0)}%',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: DS.spacing12),
          ],
          FilledButton.icon(
            onPressed: _isUploadingImage ? null : _pickQuestionImage,
            icon: const Icon(Icons.upload_file_outlined),
            label: Text(_hasQuestionImage ? '重新上传图片' : '上传题目图片'),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingScaffold() => SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(widget.isEditMode ? '编辑错题' : '添加错题'),
        ),
        child: const Center(child: CircularProgressIndicator()),
      );

  @override
  Widget build(BuildContext context) {
    final existingError = widget.initialError;
    if (existingError != null && !_hasHydratedInitialValues) {
      _hydrateFromError(existingError);
    }

    if (widget.isEditMode &&
        !_hasHydratedInitialValues &&
        existingError == null) {
      final errorAsync = ref.watch(errorDetailProvider(widget.errorId!));
      return errorAsync.when(
        data: (error) {
          if (!_hasHydratedInitialValues) {
            _hydrateFromError(error);
          }
          return _buildForm(context);
        },
        loading: _buildLoadingScaffold,
        error: (error, stack) => SparklePageScaffold(
          role: SparklePageRole.content,
          appBar: AppBar(
            leading: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.arrow_back),
              onPressed: () => context.pop(),
            ),
            title: const Text('编辑错题'),
          ),
          child: Center(
            child: Text('加载错题失败: $error'),
          ),
        ),
      );
    }

    return _buildForm(context);
  }

  Widget _buildForm(BuildContext context) {
    final theme = Theme.of(context);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(widget.isEditMode ? '编辑错题' : '添加错题'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: DS.spacing8),
            child: SparkleButton(
              variant: ButtonVariant.ghost,
              onPressed: _isSubmitting ? null : _submit,
              loading: _isSubmitting,
              icon: const Icon(Icons.check),
              label: _isSubmitting ? '保存中...' : '保存',
            ),
          ),
        ],
      ),
      child: ContentConstraint(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(DS.spacing16),
            children: [
              _buildInfoCard(context),
              const SizedBox(height: 20),
              Text(
                '选择科目 *',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SubjectFilterChips(
                selectedSubject: _selectedSubject,
                onSelected: (subject) {
                  unawaited(
                    SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.selection,
                    ),
                  );
                  setState(() {
                    _selectedSubject = subject ?? 'math';
                  });
                },
              ),
              const SizedBox(height: DS.spacing24),
              TextFormField(
                controller: _chapterController,
                decoration: const InputDecoration(
                  labelText: '章节（可选）',
                  hintText: '例如：第三章 牛顿运动定律',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.folder_outlined),
                  helperText: '填写后便于按章节筛选复习',
                ),
                textInputAction: TextInputAction.next,
              ),
              const SizedBox(height: 20),
              _buildImagePreview(context),
              const SizedBox(height: 20),
              TextFormField(
                controller: _questionController,
                decoration: const InputDecoration(
                  labelText: '题目内容',
                  hintText: '请输入完整的题目内容，或仅上传题目图片...',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.quiz_outlined),
                  alignLabelWithHint: true,
                  helperText: '题目文字和题目图片二选一即可，推荐两者都填以提升分析质量',
                ),
                maxLines: 6,
                textInputAction: TextInputAction.newline,
                validator: _validateQuestionText,
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _userAnswerController,
                decoration: const InputDecoration(
                  labelText: '你的答案 *',
                  hintText: '你当时写的错误答案...',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.edit_outlined),
                  alignLabelWithHint: true,
                ),
                maxLines: 4,
                textInputAction: TextInputAction.newline,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '请输入你的答案';
                  }
                  if (value.trim().length > 2000) {
                    return '答案内容过长（最多 2000 字符）';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _correctAnswerController,
                decoration: const InputDecoration(
                  labelText: '正确答案 *',
                  hintText: '标准答案或正确的解题过程...',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.check_circle_outline),
                  alignLabelWithHint: true,
                ),
                maxLines: 4,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _submit(),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '请输入正确答案';
                  }
                  if (value.trim().length > 2000) {
                    return '答案内容过长（最多 2000 字符）';
                  }
                  return null;
                },
              ),
              const SizedBox(height: DS.spacing32),
              FilledButton.icon(
                onPressed: _isSubmitting ? null : _submit,
                icon: _isSubmitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.save),
                label: Text(
                  _isSubmitting
                      ? '保存中，请稍候...'
                      : (widget.isEditMode ? '保存修改' : '保存错题'),
                ),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                  textStyle: const TextStyle(
                    fontSize: 16,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoCard(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: theme.colorScheme.primaryContainer.withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.tips_and_updates_outlined,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Text(
              widget.isEditMode
                  ? '更新后的题目、答案和图片会重新用于后续复习与分析。'
                  : '记录越完整，AI 越容易定位错误原因并推荐下一次复习时间。',
              style: theme.textTheme.bodyMedium?.copyWith(
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
