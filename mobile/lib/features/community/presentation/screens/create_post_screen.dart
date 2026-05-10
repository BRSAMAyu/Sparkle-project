import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/widgets/unsaved_changes_guard.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/presentation/providers/community_providers.dart';
import 'package:sparkle/features/file/data/services/file_upload_service.dart';

class CreatePostScreen extends ConsumerStatefulWidget {
  const CreatePostScreen({super.key});

  @override
  ConsumerState<CreatePostScreen> createState() => _CreatePostScreenState();
}

class _CreatePostScreenState extends ConsumerState<CreatePostScreen> {
  final _contentController = TextEditingController();
  final _topicController = TextEditingController();
  final _contentFocus = FocusNode();
  final _topicFocus = FocusNode();
  bool _isPosting = false;
  int _moodIndex = -1;

  static const _moodIcons = [
    Icons.local_fire_department_rounded,
    Icons.lightbulb_rounded,
    Icons.favorite_rounded,
    Icons.fitness_center_rounded,
    Icons.auto_stories_rounded,
  ];

  static const _moodLabels = ['🔥', '💡', '❤️', '💪', '📚'];

  bool get _isDirty =>
      _contentController.text.isNotEmpty ||
      _topicController.text.isNotEmpty ||
      _selectedImage != null ||
      _moodIndex >= 0;
  XFile? _selectedImage;

  @override
  void initState() {
    super.initState();
    _contentController.addListener(() => setState(() {}));
  }

  Future<void> _pickImage() async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      setState(() {
        _selectedImage = image;
      });
    }
  }

  void _removeImage() {
    setState(() {
      _selectedImage = null;
    });
  }

  Future<void> _submit() async {
    final content = _contentController.text.trim();
    if (content.isEmpty || content.length > 500) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));

    setState(() => _isPosting = true);

    try {
      String? imageUrl;
      if (_selectedImage != null) {
        final storedFile = await ref.read(fileUploadServiceProvider).uploadFile(
              File(_selectedImage!.path),
              visibility: 'public',
            );
        imageUrl = '${ApiConstants.baseUrl}${ApiConstants.apiBasePath}'
            '${ApiEndpoints.fileDownload(storedFile.id)}';
      }

      await ref.read(feedProvider.notifier).addPostOptimistically(
            content,
            imageUrl != null ? [imageUrl] : [],
            _topicController.text.trim(),
          );
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        debugPrint('Post failed: $e');
        AppFeedback.error(
          context,
          context.l10n.communityPostFailed,
        );
      }
    } finally {
      if (mounted) setState(() => _isPosting = false);
    }
  }

  @override
  void dispose() {
    _contentController.dispose();
    _topicController.dispose();
    _contentFocus.dispose();
    _topicFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return UnsavedChangesGuard(
      isDirty: _isDirty,
      discardTitle: context.l10n.communityDiscardDraft,
      discardMessage: context.l10n.communityUnsavedContent,
      keepEditingLabel: context.l10n.communityKeepEditing,
      discardLabel: context.l10n.communityDiscard,
      child: SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.close_rounded),
            onPressed: () => context.pop(),
          ),
          title: Text(context.l10n.communityNewPost),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: DS.md),
              child: SparkleButton.primary(
                label: context.l10n.communityPost,
                onPressed:
                    _contentController.text.trim().isEmpty || _isPosting
                        ? () {}
                        : _submit,
                loading: _isPosting,
              ),
            ),
          ],
        ),
        child: ContentConstraint(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.lg,
              vertical: DS.md,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Main content area
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Mood selector row
                      Text(
                        context.l10n.communityMoodPrompt,
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          fontWeight: DS.fontWeightSemibold,
                          color: DS.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      _buildMoodSelector(),
                      const SizedBox(height: DS.spacing16),

                      // Content text field
                      TextField(
                        controller: _contentController,
                        focusNode: _contentFocus,
                        autofocus: true,
                        maxLength: 500,
                        maxLines: 10,
                        minLines: 6,
                        style: TextStyle(
                          color: DS.textPrimary,
                          fontSize: DS.fontSizeBase,
                          height: 1.6,
                        ),
                        decoration: InputDecoration(
                          hintText: context.l10n.communityContentHint,
                          hintStyle: TextStyle(
                            color: DS.textTertiary,
                            height: 1.6,
                          ),
                          border: InputBorder.none,
                          counterStyle: TextStyle(
                            fontSize: 0, // hide default counter
                          ),
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),

                      // Character count
                      Align(
                        alignment: Alignment.centerRight,
                        child: Text(
                          '${_contentController.text.length}/500',
                          style: TextStyle(
                            fontSize: DS.fontSizeXs,
                            color: _contentController.text.length > 500
                                ? DS.error
                                : DS.textTertiary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing12),

                // Image preview
                if (_selectedImage != null) ...[
                  GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.card,
                    padding: const EdgeInsets.all(DS.spacing12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.image_rounded,
                                size: 16, color: DS.brandPrimary),
                            const SizedBox(width: DS.spacing8),
                            Text(
                              context.l10n.communityAttachment,
                              style: TextStyle(
                                fontSize: DS.fontSizeSm,
                                fontWeight: DS.fontWeightSemibold,
                                color: DS.textSecondary,
                              ),
                            ),
                            const Spacer(),
                            SparkleIconButton(
                              variant: ButtonVariant.ghost,
                              icon: Icon(Icons.close_rounded,
                                  size: 18, color: DS.textTertiary),
                              onPressed: _removeImage,
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.spacing8),
                        ClipRRect(
                          borderRadius: DS.borderRadius12,
                          child: ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 200),
                            child: Image.file(
                              File(_selectedImage!.path),
                              fit: BoxFit.cover,
                              width: double.infinity,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                ],

                // Topic field
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  child: TextField(
                    controller: _topicController,
                    style: TextStyle(
                      color: DS.brandPrimary,
                      fontSize: DS.fontSizeBase,
                      fontWeight: DS.fontWeightMedium,
                    ),
                    decoration: InputDecoration(
                      prefixText: '# ',
                      prefixStyle: TextStyle(
                        color: DS.brandPrimary,
                        fontWeight: DS.fontWeightBold,
                        fontSize: DS.fontSizeBase,
                      ),
                      hintText: context.l10n.communityTopicHint,
                      hintStyle: TextStyle(color: DS.textTertiary),
                      border: InputBorder.none,
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),

                // Toolbar
                Row(
                  children: [
                    _ToolbarButton(
                      icon: Icons.image_outlined,
                      label: context.l10n.communityPhoto,
                      onPressed: _pickImage,
                    ),
                    const SizedBox(width: DS.spacing8),
                    _ToolbarButton(
                      icon: Icons.tag_rounded,
                      label: context.l10n.communityTopic,
                      onPressed: () {
                        _contentFocus.unfocus();
                        FocusScope.of(context).requestFocus(_topicFocus);
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMoodSelector() {
    return Row(
      children: List.generate(_moodIcons.length, (index) {
        final selected = _moodIndex == index;
        return Padding(
          padding: const EdgeInsets.only(right: DS.spacing8),
          child: GestureDetector(
            onTap: () {
              unawaited(SensoryFeedbackService.emit(
                  SensoryFeedbackEvent.selection));
              setState(() {
                _moodIndex = selected ? -1 : index;
              });
            },
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOutCubic,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing8,
              ),
              decoration: BoxDecoration(
                color: selected
                    ? DS.brandPrimary.withValues(alpha: 0.12)
                    : DS.surfaceSecondary,
                borderRadius: DS.borderRadius12,
                border: Border.all(
                  color: selected
                      ? DS.brandPrimary.withValues(alpha: 0.3)
                      : DS.borderSubtle,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _moodLabels[index],
                    style: const TextStyle(fontSize: 16),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    _moodIcons[index],
                    size: 14,
                    color: selected ? DS.brandPrimary : DS.textTertiary,
                  ),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
}

class _ToolbarButton extends StatelessWidget {
  const _ToolbarButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => SparkleIconButton(
        variant: ButtonVariant.ghost,
        icon: Icon(icon, size: 20, color: DS.textSecondary),
        onPressed: onPressed,
      );
}
