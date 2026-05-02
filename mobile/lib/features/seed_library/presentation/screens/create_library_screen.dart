import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Create Library Screen
/// Allows users to create a new seed library
class CreateLibraryScreen extends ConsumerStatefulWidget {
  const CreateLibraryScreen({super.key});

  @override
  ConsumerState<CreateLibraryScreen> createState() =>
      _CreateLibraryScreenState();
}

class _CreateLibraryScreenState extends ConsumerState<CreateLibraryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _tagsController = TextEditingController();

  LibraryCategory _selectedCategory = LibraryCategory.custom;
  LibraryVisibility _selectedVisibility = LibraryVisibility.private;
  final List<String> _tags = [];
  bool _isCreating = false;

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _tagsController.dispose();
    super.dispose();
  }

  Future<void> _createLibrary() async {
    if (!_formKey.currentState!.validate()) return;

    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
    );
    setState(() {
      _isCreating = true;
    });

    try {
      final repository = ref.read(seedLibraryRepositoryProvider);
      await repository.createLibrary(
        CreateLibraryRequest(
          name: _nameController.text.trim(),
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
          category: _selectedCategory,
          visibility: _selectedVisibility,
          tags: _tags.isEmpty ? null : _tags,
        ),
      );

      if (mounted) {
        final zh = I18nService.instance.isChinese;
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.success),
        );
        AppFeedback.success(
            context, zh ? '种子库创建成功' : 'Library created successfully');
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCreating = false;
        });
        AppFeedback.error(context, context.l10n.seedCreateFailed(e.toString()));
      }
    }
  }

  void _addTag() {
    final tag = _tagsController.text.trim();
    if (tag.isEmpty) return;
    if (_tags.contains(tag)) {
      final zh = I18nService.instance.isChinese;
      AppFeedback.info(context, zh ? '标签已存在' : 'Tag already exists');
      return;
    }

    setState(() {
      _tags.add(tag);
      _tagsController.clear();
    });
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
    );
  }

  void _removeTag(String tag) {
    setState(() {
      _tags.remove(tag);
    });
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          title: Text(context.l10n.seedCreateTitle),
        ),
        bottomNavigationBar: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: SparkleButton(
              label: context.l10n.seedCreateTitle,
              onPressed: _createLibrary,
              loading: _isCreating,
              expand: true,
            ),
          ),
        ),
        child: ContentConstraint(
          child: Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(DS.spacing16),
              children: [
                SparkleStaggerItem(
                  index: 0,
                  child: TextFormField(
                    controller: _nameController,
                    decoration: InputDecoration(
                      labelText: context.l10n.seedNameLabel,
                      hintText: context.l10n.seedNameHint,
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        final zh = I18nService.instance.isChinese;
                        return zh ? '请输入名称' : 'Please enter a name';
                      }
                      return null;
                    },
                  ),
                ),
                const SizedBox(height: DS.spacing16),

                SparkleStaggerItem(
                  index: 1,
                  child: TextFormField(
                    controller: _descriptionController,
                    decoration: InputDecoration(
                      labelText: context.l10n.seedDescLabel,
                      hintText: context.l10n.seedDescHint,
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 3,
                  ),
                ),
                const SizedBox(height: DS.spacing24),

                SparkleStaggerItem(
                  index: 2,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        I18nService.instance.isChinese ? '分类' : 'Category',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Wrap(
                        spacing: DS.spacing8,
                        children: LibraryCategory.values.map((category) {
                          final isSelected = _selectedCategory == category;
                          return ChoiceChip(
                            label: Text(category.label(context.l10n)),
                            selected: isSelected,
                            onSelected: (selected) {
                              unawaited(
                                SensoryFeedbackService.emit(
                                  SensoryFeedbackEvent.selection,
                                ),
                              );
                              setState(() {
                                _selectedCategory = category;
                              });
                            },
                            selectedColor:
                                Theme.of(context).colorScheme.primaryContainer,
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing24),

                SparkleStaggerItem(
                  index: 3,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        I18nService.instance.isChinese ? '可见性' : 'Visibility',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Wrap(
                        spacing: DS.spacing8,
                        children: LibraryVisibility.values.map((visibility) {
                          final isSelected = _selectedVisibility == visibility;
                          return ChoiceChip(
                            label: Text(visibility.label(context.l10n)),
                            selected: isSelected,
                            onSelected: (selected) {
                              unawaited(
                                SensoryFeedbackService.emit(
                                  SensoryFeedbackEvent.selection,
                                ),
                              );
                              setState(() {
                                _selectedVisibility = visibility;
                              });
                            },
                            selectedColor:
                                Theme.of(context).colorScheme.primaryContainer,
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing24),

                // Tags
                Text(
                  I18nService.instance.isChinese ? '标签' : 'Tags',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: DS.spacing8),

                // Tags input
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _tagsController,
                        decoration: InputDecoration(
                          hintText: context.l10n.seedTagHint,
                          border: OutlineInputBorder(),
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: DS.spacing12,
                            vertical: DS.spacing12,
                          ),
                        ),
                        onSubmitted: (_) => _addTag(),
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    SparkleIconButton(
                      variant: ButtonVariant.secondary,
                      icon: const Icon(Icons.add),
                      onPressed: _addTag,
                    ),
                  ],
                ),

                // Tags display
                if (_tags.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing12),
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: _tags
                        .map(
                          (tag) => Chip(
                            label: Text(tag),
                            deleteIcon: const Icon(Icons.close, size: 18),
                            onDeleted: () => _removeTag(tag),
                          ),
                        )
                        .toList(),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
}
