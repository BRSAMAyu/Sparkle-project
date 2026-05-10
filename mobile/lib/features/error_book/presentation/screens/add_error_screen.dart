import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/unsaved_changes_guard.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/question_image_reference.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_question_image.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';
import 'package:sparkle/features/file/data/services/file_upload_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

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

  bool get _isDirty =>
      _questionController.text.isNotEmpty ||
      _userAnswerController.text.isNotEmpty ||
      _correctAnswerController.text.isNotEmpty ||
      _chapterController.text.isNotEmpty;

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
      AppFeedback.success(context, context.l10n.ebQuestionImageUploadSuccess);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _localQuestionImage = null;
      });
      AppFeedback.error(context, context.l10n.ebImageUploadFailed(e.toString()));
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
      return context.l10n.ebQuestionOrImageRequired;
    }
    if (content.isNotEmpty && content.length < 5) {
      return context.l10n.ebQuestionTooShort;
    }
    if (content.length > 5000) {
      return context.l10n.ebQuestionTooLong;
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
      AppFeedback.info(context, context.l10n.ebImageStillUploading);
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
        widget.isEditMode
            ? context.l10n.ebErrorUpdated
            : context.l10n.ebErrorAdded,
      );
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          widget.isEditMode
              ? context.l10n.ebUpdateFailed(e.toString())
              : context.l10n.ebAddFailed(e.toString()),
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
                context.l10n.ebQuestionImageOptional,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const Spacer(),
              if (_hasQuestionImage)
                TextButton.icon(
                  onPressed: _isUploadingImage ? null : _removeQuestionImage,
                  icon: const Icon(Icons.delete_outline),
                  label: Text(context.l10n.ebRemove),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.ebQuestionImageHint,
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
                                context.l10n.ebNoImageUploaded,
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
              context.l10n.ebUploadProgress('${(_uploadProgress * 100).toStringAsFixed(0)}%'),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: DS.spacing12),
          ],
          FilledButton.icon(
            onPressed: _isUploadingImage ? null : _pickQuestionImage,
            icon: const Icon(Icons.upload_file_outlined),
            label: Text(_hasQuestionImage ? context.l10n.ebReuploadImage : context.l10n.ebUploadImage),
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
          title: Text(widget.isEditMode ? context.l10n.ebEditError : context.l10n.ebAddError),
        ),
        child: const SparkleListSkeleton(),
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
            title: Text(context.l10n.ebEditError),
          ),
          child: Center(
            child: Text(context.l10n.ebLoadErrorFailed(error.toString())),
          ),
        ),
      );
    }

    return _buildForm(context);
  }

  Widget _buildForm(BuildContext context) {
    final theme = Theme.of(context);

    return UnsavedChangesGuard(
      isDirty: _isDirty,
      child: SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(widget.isEditMode ? context.l10n.ebEditError : context.l10n.ebAddError),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: DS.spacing8),
            child: SparkleButton(
              variant: ButtonVariant.ghost,
              onPressed: _isSubmitting ? null : _submit,
              loading: _isSubmitting,
              icon: const Icon(Icons.check),
              label: _isSubmitting ? context.l10n.ebSaving : context.l10n.ebSave,
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
                context.l10n.ebSubjectLabel,
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
                decoration: InputDecoration(
                  labelText: context.l10n.ebChapterOptional,
                  hintText: context.l10n.ebChapterHint,
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.folder_outlined),
                  helperText: context.l10n.ebChapterHelper,
                ),
                textInputAction: TextInputAction.next,
              ),
              const SizedBox(height: 20),
              _buildImagePreview(context),
              const SizedBox(height: 20),
              TextFormField(
                controller: _questionController,
                decoration: InputDecoration(
                  labelText: context.l10n.ebQuestionContent,
                  hintText: context.l10n.ebQuestionHint,
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.quiz_outlined),
                  alignLabelWithHint: true,
                  helperText: context.l10n.ebQuestionHelper,
                ),
                maxLines: 6,
                textInputAction: TextInputAction.newline,
                validator: _validateQuestionText,
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _userAnswerController,
                decoration: InputDecoration(
                  labelText: context.l10n.ebYourAnswer,
                  hintText: context.l10n.ebYourAnswerHint,
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.edit_outlined),
                  alignLabelWithHint: true,
                ),
                maxLines: 4,
                textInputAction: TextInputAction.newline,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return context.l10n.ebEnterAnswer;
                  }
                  if (value.trim().length > 2000) {
                    return context.l10n.ebAnswerTooLong;
                  }
                  return null;
                },
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _correctAnswerController,
                decoration: InputDecoration(
                  labelText: context.l10n.ebCorrectAnswer,
                  hintText: context.l10n.ebCorrectAnswerHint,
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.check_circle_outline),
                  alignLabelWithHint: true,
                ),
                maxLines: 4,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _submit(),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return context.l10n.ebCorrectAnswerRequired;
                  }
                  if (value.trim().length > 2000) {
                    return context.l10n.ebAnswerTooLong;
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
                      ? context.l10n.ebSavingPleaseWait
                      : (widget.isEditMode
                          ? context.l10n.ebSaveChanges
                          : context.l10n.ebSaveError),
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
                  ? context.l10n.ebEditHintInfo
                  : context.l10n.ebNewHintInfo,
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
