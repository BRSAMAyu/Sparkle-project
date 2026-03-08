import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';

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
        AppFeedback.success(context, '种子库创建成功');
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCreating = false;
        });
        AppFeedback.error(context, '创建失败：$e');
      }
    }
  }

  void _addTag() {
    final tag = _tagsController.text.trim();
    if (tag.isEmpty) return;
    if (_tags.contains(tag)) {
      AppFeedback.info(context, '标签已存在');
      return;
    }

    setState(() {
      _tags.add(tag);
      _tagsController.clear();
    });
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
          title: const Text('创建种子库'),
        ),
        child: ContentConstraint(
          child: Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(DS.spacing16),
              children: [
                // Name field
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: '名称',
                    hintText: '输入种子库名称',
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return '请输入名称';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: DS.spacing16),

                // Description field
                TextFormField(
                  controller: _descriptionController,
                  decoration: const InputDecoration(
                    labelText: '描述',
                    hintText: '输入种子库描述（可选）',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: DS.spacing24),

                // Category selection
                Text(
                  '分类',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: DS.spacing8),
                Wrap(
                  spacing: DS.spacing8,
                  children: LibraryCategory.values.map((category) {
                    final isSelected = _selectedCategory == category;
                    return ChoiceChip(
                      label: Text(category.displayName),
                      selected: isSelected,
                      onSelected: (selected) {
                        setState(() {
                          _selectedCategory = category;
                        });
                      },
                      selectedColor:
                          Theme.of(context).colorScheme.primaryContainer,
                    );
                  }).toList(),
                ),
                const SizedBox(height: DS.spacing24),

                // Visibility selection
                Text(
                  '可见性',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: DS.spacing8),
                Wrap(
                  spacing: DS.spacing8,
                  children: LibraryVisibility.values.map((visibility) {
                    final isSelected = _selectedVisibility == visibility;
                    return ChoiceChip(
                      label: Text(visibility.displayName),
                      selected: isSelected,
                      onSelected: (selected) {
                        setState(() {
                          _selectedVisibility = visibility;
                        });
                      },
                      selectedColor:
                          Theme.of(context).colorScheme.primaryContainer,
                    );
                  }).toList(),
                ),
                const SizedBox(height: DS.spacing24),

                // Tags
                Text(
                  '标签',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: DS.spacing8),

                // Tags input
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _tagsController,
                        decoration: const InputDecoration(
                          hintText: '输入标签',
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
                      size: DS.touchTargetMinSize,
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
        bottomNavigationBar: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: SparkleButton(
              label: '创建种子库',
              onPressed: _createLibrary,
              loading: _isCreating,
              expand: true,
            ),
          ),
        ),
      );
}
