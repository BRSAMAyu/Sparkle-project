import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/presentation/providers/community_providers.dart';

class CreatePostScreen extends ConsumerStatefulWidget {
  const CreatePostScreen({super.key});

  @override
  ConsumerState<CreatePostScreen> createState() => _CreatePostScreenState();
}

class _CreatePostScreenState extends ConsumerState<CreatePostScreen> {
  final _contentController = TextEditingController();
  final _topicController = TextEditingController();
  bool _isPosting = false;
  XFile? _selectedImage;
  String? _selectedLocation;

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

  Future<void> _pickLocation() async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    // Feature: Implement location picker using geolocator package
    // Requires: flutter pub add geolocator
    // 暂时使用模拟位置
    setState(() {
      _selectedLocation = I18nService.instance.isChinese ? '模拟位置' : 'Mock Location';
    });

    AppFeedback.info(context, I18nService.instance.isChinese ? '位置选择功能开发中，使用模拟位置' : 'Location picker is under development, using mock location');
  }

  Future<void> _submit() async {
    final content = _contentController.text.trim();
    if (content.isEmpty) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));

    setState(() => _isPosting = true);

    try {
      await ref.read(feedProvider.notifier).addPostOptimistically(
            content,
            _selectedImage != null ? [_selectedImage!.path] : [],
            _topicController.text.trim(),
          );
      // Feature: Save location data separately if provided
      if (_selectedLocation != null) {
        if (kDebugMode) {
          debugPrint('Location info: $_selectedLocation');
        }
      }
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, I18nService.instance.isChinese ? '发布失败：$e' : 'Post failed: $e');
      }
    } finally {
      if (mounted) setState(() => _isPosting = false);
    }
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(I18nService.instance.isChinese ? '发布动态' : 'New Post'),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: DS.md),
              child: SparkleButton(
                label: I18nService.instance.isChinese ? '发布' : 'Post',
                onPressed: _isPosting ? null : _submit,
                variant: ButtonVariant.ghost,
                size: ButtonSize.small,
                loading: _isPosting,
              ),
            ),
          ],
        ),
        child: ContentConstraint(
          child: Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              child: SingleChildScrollView(
                child: Column(
                children: [
                  TextField(
                    controller: _contentController,
                    autofocus: true,
                    maxLines: 8,
                    style: TextStyle(color: DS.textPrimary, fontSize: 16),
                    decoration: InputDecoration(
                      hintText: I18nService.instance.isChinese ? '分享你此刻的想法...' : "What's on your mind?",
                      hintStyle: TextStyle(
                          color: DS.textSecondary.withValues(alpha: 0.7),),
                      border: InputBorder.none,
                    ),
                  ),
                  Divider(color: DS.borderSubtle),
                  SparkleStaggerItem(
                    index: 0,
                    child: TextField(
                      controller: _topicController,
                      style: TextStyle(color: DS.textPrimary),
                      decoration: InputDecoration(
                        prefixText: '# ',
                        hintText: I18nService.instance.isChinese ? '话题（可选）' : 'Topic (optional)',
                        hintStyle: TextStyle(
                            color: DS.textSecondary.withValues(alpha: 0.7),),
                        border: InputBorder.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing24),
                  // Toolbar (Placeholder)
                  SparkleStaggerItem(
                    index: 1,
                    axis: Axis.horizontal,
                    child: Row(
                      children: [
                        SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          icon: Icon(
                            Icons.image_outlined,
                            color: _selectedImage != null
                                ? DS.brandPrimary
                                : DS.brandPrimary,
                          ),
                          onPressed: _pickImage,
                        ),
                        SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          icon: Icon(
                            Icons.location_on_outlined,
                            color: _selectedLocation != null
                                ? DS.brandPrimary
                                : DS.brandPrimary,
                          ),
                          onPressed: _pickLocation,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              ),
            ),
          ),
        ),
      );
}
