import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/community_model.dart'
    show GroupRole, UserBrief;
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/presentation/widgets/file_picker_with_presigned.dart';
import 'package:url_launcher/url_launcher.dart';

enum KnowledgeBaseSort { recency, popularity, trustLevel }

class GroupKnowledgeBaseView extends ConsumerStatefulWidget {
  const GroupKnowledgeBaseView({
    required this.groupId,
    super.key,
    this.currentUserRole,
  });

  final String groupId;
  final GroupRole? currentUserRole;

  @override
  ConsumerState<GroupKnowledgeBaseView> createState() =>
      _GroupKnowledgeBaseViewState();
}

class _GroupKnowledgeBaseViewState
    extends ConsumerState<GroupKnowledgeBaseView> {
  Future<List<GroupFileInfo>>? _filesFuture;
  Future<List<GroupFileCategoryStat>>? _categoriesFuture;
  final Map<String, bool> _officialOverrides = <String, bool>{};
  final Map<String, String> _descriptionOverrides = <String, String>{};
  final Map<String, bool> _galaxyOverrides = <String, bool>{};
  String? _selectedCategory;
  String _query = '';
  bool _gridView = false;
  KnowledgeBaseSort _sort = KnowledgeBaseSort.recency;

  bool get _canUpload => widget.currentUserRole != null;
  bool get _isAdmin => widget.currentUserRole == GroupRole.owner ||
      widget.currentUserRole == GroupRole.admin;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final repo = ref.read(fileRepositoryProvider);
    setState(() {
      _filesFuture = repo.listGroupFiles(
        widget.groupId,
        category: _selectedCategory,
        limit: 200,
      );
      _categoriesFuture = repo.getGroupFileCategories(widget.groupId);
    });
  }

  List<GroupFileInfo> _applySearchAndSort(List<GroupFileInfo> files) {
    final normalizedQuery = _query.trim().toLowerCase();

    final filtered = files.where((file) {
      if (_selectedCategory != null && file.category != _selectedCategory) {
        return false;
      }
      if (normalizedQuery.isEmpty) {
        return true;
      }
      final haystack = <String>[
        file.fileName,
        file.category ?? '',
        _descriptionFor(file),
        ...file.tags,
        file.sharedBy?.displayName ?? '',
      ].join(' ').toLowerCase();
      return haystack.contains(normalizedQuery);
    }).toList()
      ..sort((a, b) {
      switch (_sort) {
        case KnowledgeBaseSort.popularity:
          return b.downloadCount.compareTo(a.downloadCount);
        case KnowledgeBaseSort.trustLevel:
          final trustCompare = (_isOfficial(b) ? 1 : 0) - (_isOfficial(a) ? 1 : 0);
          if (trustCompare != 0) {
            return trustCompare;
          }
          return b.createdAt.compareTo(a.createdAt);
        case KnowledgeBaseSort.recency:
          return b.createdAt.compareTo(a.createdAt);
      }
      });

    return filtered;
  }

  String _descriptionFor(GroupFileInfo file) =>
      _descriptionOverrides[file.fileId] ??
      file.description ??
      (file.tags.isEmpty ? '' : file.tags.join(' · '));

  bool _isOfficial(GroupFileInfo file) =>
      _officialOverrides[file.fileId] ?? file.isOfficial;

  bool _isInGalaxy(GroupFileInfo file) =>
      _galaxyOverrides[file.fileId] ?? file.isInGroupGalaxy;

  Future<void> _openFile(GroupFileInfo file) async {
    if (!file.canDownload) {
      AppFeedback.info(context, '暂无下载权限');
      return;
    }
    final presigned = await ref
        .read(fileRepositoryProvider)
        .getDownloadUrl(file.fileId, groupId: widget.groupId);
    final uri = Uri.tryParse(presigned.url);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _saveToMyLibrary(GroupFileInfo file) async {
    try {
      await ref
          .read(fileRepositoryProvider)
          .copyGroupFileToMyLibrary(widget.groupId, file.fileId);
      if (!mounted) return;
      AppFeedback.success(context, '已保存到我的资料库');
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, '保存失败: $e');
    }
  }

  void _toggleOfficial(GroupFileInfo file) {
    if (!_isAdmin) return;
    final nextValue = !_isOfficial(file);
    setState(() => _officialOverrides[file.fileId] = nextValue);
    AppFeedback.success(
      context,
      nextValue ? '已标记为官方资料' : '已移除官方资料标记',
    );
  }

  Future<void> _showUploadFlow() async {
    final categoryController = TextEditingController();
    final descriptionController = TextEditingController();
    var addToGalaxy = false;
    var markOfficial = false;

    final confirmed = await showSensoryModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setModalState) => SafeArea(
          top: false,
          child: SingleChildScrollView(
            padding: EdgeInsets.only(
              left: DS.spacing16,
              right: DS.spacing16,
              top: DS.spacing16,
              bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing20,
            ),
            child: GraphiteModalSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '添加到知识库',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    '填写资料说明后开始上传。上传完成后会自动进入群知识库。',
                    style: TextStyle(color: DS.textSecondary, height: 1.4),
                  ),
                  const SizedBox(height: DS.spacing16),
                  TextField(
                    controller: categoryController,
                    decoration: const InputDecoration(
                      labelText: '分类',
                      hintText: '例如：真题、写作模板、词汇表',
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  TextField(
                    controller: descriptionController,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: '描述',
                      hintText: '补充这份资料适合谁、怎么使用、重点看哪里。',
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('加入群星图'),
                    subtitle: const Text('让这份资料也出现在群组知识星图索引里'),
                    value: addToGalaxy,
                    onChanged: (value) =>
                        setModalState(() => addToGalaxy = value),
                  ),
                  if (_isAdmin)
                    SwitchListTile.adaptive(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('标记为官方资料'),
                      subtitle: const Text('官方资料会获得金色星标并优先展示'),
                      value: markOfficial,
                      onChanged: (value) =>
                          setModalState(() => markOfficial = value),
                    ),
                  const SizedBox(height: DS.spacing16),
                  Row(
                    children: [
                      Expanded(
                        child: SparkleButton.ghost(
                          label: context.l10n.cancel,
                          onPressed: () => Navigator.pop(context, false),
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: SparkleButton.primary(
                          label: '继续上传',
                          onPressed: () => Navigator.pop(context, true),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    final category = categoryController.text.trim();
    final description = descriptionController.text.trim();
    categoryController.dispose();
    descriptionController.dispose();

    if (confirmed != true || !mounted) return;

    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (context) => FilePickerWithPresignedUpload(
          groupId: widget.groupId,
          onUploaded: (file) async {
            final repo = ref.read(fileRepositoryProvider);
            final sharedFile = await repo.shareToGroup(
              widget.groupId,
              file.id,
              category: category.isEmpty ? null : category,
              description: description.isEmpty ? null : description,
              addToGroupGalaxy: addToGalaxy,
              isOfficial: markOfficial ? true : null,
            );
            if (!mounted || !context.mounted) return;
            Navigator.pop(context);
            setState(() {
              if (description.isNotEmpty) {
                _descriptionOverrides[sharedFile.fileId] = description;
              }
              if (markOfficial) {
                _officialOverrides[sharedFile.fileId] = true;
              }
              if (addToGalaxy) {
                _galaxyOverrides[sharedFile.fileId] = true;
              }
            });
            _reload();
            AppFeedback.success(context, '资料已加入群知识库');
          },
          onError: (message) {
            if (!mounted) return;
            AppFeedback.error(context, message);
          },
        ),
      ),
    );
  }

  void _openContributorProfile(UserBrief? contributor) {
    if (contributor == null) return;
    final route = CommunityRoutes.userProfile.replaceFirst(':id', contributor.id);
    final name = Uri.encodeComponent(contributor.displayName);
    unawaited(context.push('$route?name=$name'));
  }

  void _showDocumentDetail(GroupFileInfo file) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (context) => SafeArea(
          top: false,
          child: SingleChildScrollView(
            padding: EdgeInsets.only(
              left: DS.spacing16,
              right: DS.spacing16,
              top: DS.spacing16,
              bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing20,
            ),
            child: GraphiteModalSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              file.fileName,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(fontWeight: DS.fontWeightBold),
                            ),
                            const SizedBox(height: DS.spacing8),
                            Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: [
                                _MetaChip(
                                  icon: _iconForMime(file.mimeType, file.fileName),
                                  label: _typeLabel(file.mimeType, file.fileName),
                                ),
                                _MetaChip(
                                  icon: Icons.sd_storage_outlined,
                                  label: _formatSize(file.fileSize),
                                ),
                                _MetaChip(
                                  icon: Icons.download_outlined,
                                  label: '${file.downloadCount} 次下载',
                                ),
                                if (_isOfficial(file))
                                  const _MetaChip(
                                    icon: Icons.star_rounded,
                                    label: '官方资料',
                                    accentColor: Color(0xFFE0A800),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      if (_isAdmin)
                        SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          icon: Icon(
                            _isOfficial(file)
                                ? Icons.star_rounded
                                : Icons.star_outline_rounded,
                            color: _isOfficial(file)
                                ? const Color(0xFFE0A800)
                                : DS.textSecondary,
                          ),
                          onPressed: () => _toggleOfficial(file),
                        ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing16),
                  _DocumentPreviewPanel(
                    groupId: widget.groupId,
                    file: file,
                    description: _descriptionFor(file),
                  ),
                  const SizedBox(height: DS.spacing16),
                  InkWell(
                    onTap: () => _openContributorProfile(file.sharedBy),
                    borderRadius: BorderRadius.circular(16),
                    child: Ink(
                      padding: const EdgeInsets.all(DS.spacing12),
                      decoration: BoxDecoration(
                        color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: DS.borderSubtle),
                      ),
                      child: Row(
                        children: [
                          SparkleAvatar(
                            radius: 22,
                            url: file.sharedBy?.avatarUrl,
                            fallbackText: file.sharedBy?.displayName,
                          ),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  file.sharedBy?.displayName ?? '群成员',
                                  style: TextStyle(
                                    fontWeight: DS.fontWeightSemiBold,
                                    color: DS.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '贡献者资料页',
                                  style: TextStyle(color: DS.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          Icon(
                            Icons.chevron_right_rounded,
                            color: DS.textSecondary,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  Row(
                    children: [
                      Expanded(
                        child: SparkleButton.ghost(
                          label: '查看',
                          icon: const Icon(Icons.open_in_new_rounded),
                          onPressed: () => _openFile(file),
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: SparkleButton.primary(
                          label: '保存到我的资料库',
                          icon: const Icon(Icons.bookmark_add_outlined),
                          onPressed: () => _saveToMyLibrary(file),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.currentUserRole == null) {
      return const _LockedKnowledgeBase();
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing16,
            DS.spacing16,
            DS.spacing12,
          ),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '群知识库',
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(fontWeight: DS.fontWeightBold),
                        ),
                        const SizedBox(height: DS.spacing4),
                        Text(
                          '共享学习资料、真题、模板和群内精选知识。',
                          style: TextStyle(
                            color: DS.textSecondary,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  SparkleIconButton(
                    icon: Icon(
                      _gridView ? Icons.view_list_rounded : Icons.grid_view_rounded,
                    ),
                    variant: ButtonVariant.ghost,
                    onPressed: () => setState(() => _gridView = !_gridView),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              LayoutBuilder(
                builder: (context, constraints) {
                  final searchField = TextField(
                    decoration: InputDecoration(
                      hintText: '搜索群内资料内容、分类或贡献者',
                      prefixIcon: const Icon(Icons.search),
                      filled: true,
                      fillColor: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: BorderSide.none,
                      ),
                    ),
                    onChanged: (value) =>
                        setState(() => _query = value.trim()),
                  );

                  final uploadButton = SparkleButton.primary(
                    label: '添加到知识库',
                    icon: const Icon(Icons.add_circle_outline_rounded),
                    onPressed: _showUploadFlow,
                  );

                  if (!_canUpload) {
                    return searchField;
                  }

                  if (constraints.maxWidth < 520) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        searchField,
                        const SizedBox(height: DS.spacing12),
                        uploadButton,
                      ],
                    );
                  }

                  return Row(
                    children: [
                      Expanded(child: searchField),
                      const SizedBox(width: DS.spacing12),
                      uploadButton,
                    ],
                  );
                },
              ),
              const SizedBox(height: DS.spacing12),
              SizedBox(
                height: 40,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    _SortChip(
                      label: '最新',
                      selected: _sort == KnowledgeBaseSort.recency,
                      onTap: () =>
                          setState(() => _sort = KnowledgeBaseSort.recency),
                    ),
                    _SortChip(
                      label: '最受欢迎',
                      selected: _sort == KnowledgeBaseSort.popularity,
                      onTap: () =>
                          setState(() => _sort = KnowledgeBaseSort.popularity),
                    ),
                    _SortChip(
                      label: '可信度',
                      selected: _sort == KnowledgeBaseSort.trustLevel,
                      onTap: () =>
                          setState(() => _sort = KnowledgeBaseSort.trustLevel),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing10),
              FutureBuilder<List<GroupFileCategoryStat>>(
                future: _categoriesFuture,
                builder: (context, snapshot) {
                  final categories = snapshot.data ?? const [];
                  return SizedBox(
                    height: 36,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      children: [
                        _CategoryChip(
                          label: '全部',
                          selected: _selectedCategory == null,
                          onTap: () {
                            setState(() => _selectedCategory = null);
                            _reload();
                          },
                        ),
                        for (final item in categories)
                          _CategoryChip(
                            label: item.category ?? '未分类',
                            selected: _selectedCategory == item.category,
                            onTap: () {
                              setState(() => _selectedCategory = item.category);
                              _reload();
                            },
                          ),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
        ),
        Expanded(
          child: FutureBuilder<List<GroupFileInfo>>(
            future: _filesFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(
                  child: Text('加载失败: ${snapshot.error}'),
                );
              }

              final files = _applySearchAndSort(snapshot.data ?? const []);
              if (files.isEmpty) {
                return RefreshIndicator(
                  onRefresh: () async => _reload(),
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(DS.spacing24),
                    children: const [
                      SizedBox(height: 80),
                      _KnowledgeBaseEmptyState(),
                    ],
                  ),
                );
              }

              if (_gridView) {
                return RefreshIndicator(
                  onRefresh: () async => _reload(),
                  child: GridView.builder(
                    padding: const EdgeInsets.fromLTRB(
                      DS.spacing16,
                      0,
                      DS.spacing16,
                      DS.spacing24,
                    ),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: context.isMobile ? 2 : 3,
                      mainAxisSpacing: DS.spacing12,
                      crossAxisSpacing: DS.spacing12,
                      childAspectRatio: context.isMobile ? 0.85 : 0.94,
                    ),
                    itemCount: files.length,
                    itemBuilder: (context, index) => _KnowledgeBaseGridCard(
                      file: files[index],
                      description: _descriptionFor(files[index]),
                      isOfficial: _isOfficial(files[index]),
                      isInGalaxy: _isInGalaxy(files[index]),
                      onTap: () => _showDocumentDetail(files[index]),
                    ),
                  ),
                );
              }

              return RefreshIndicator(
                onRefresh: () async => _reload(),
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    0,
                    DS.spacing16,
                    DS.spacing24,
                  ),
                  itemCount: files.length,
                  separatorBuilder: (_, __) =>
                      const SizedBox(height: DS.spacing12),
                  itemBuilder: (context, index) => _KnowledgeBaseListCard(
                    file: files[index],
                    description: _descriptionFor(files[index]),
                    isOfficial: _isOfficial(files[index]),
                    isInGalaxy: _isInGalaxy(files[index]),
                    onTap: () => _showDocumentDetail(files[index]),
                    onContributorTap: () =>
                        _openContributorProfile(files[index].sharedBy),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  String _formatSize(int bytes) {
    if (bytes < 1024) return '${bytes}B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)}KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / 1024 / 1024).toStringAsFixed(1)}MB';
    }
    return '${(bytes / 1024 / 1024 / 1024).toStringAsFixed(1)}GB';
  }

  IconData _iconForMime(String mimeType, String fileName) {
    final normalizedMime = mimeType.toLowerCase();
    final extension = fileName.contains('.')
        ? fileName.split('.').last.toLowerCase()
        : '';

    if (normalizedMime.contains('pdf') || extension == 'pdf') {
      return Icons.picture_as_pdf_rounded;
    }
    if (normalizedMime.contains('presentation') || extension == 'pptx') {
      return Icons.slideshow_rounded;
    }
    if (normalizedMime.contains('word') || extension == 'docx') {
      return Icons.description_rounded;
    }
    if (normalizedMime.startsWith('image/')) {
      return Icons.image_outlined;
    }
    if (normalizedMime.contains('text') || extension == 'txt') {
      return Icons.notes_rounded;
    }
    return Icons.insert_drive_file_rounded;
  }

  String _typeLabel(String mimeType, String fileName) {
    final normalizedMime = mimeType.toLowerCase();
    final extension = fileName.contains('.')
        ? fileName.split('.').last.toUpperCase()
        : '';

    if (normalizedMime.contains('pdf')) return 'PDF';
    if (normalizedMime.contains('presentation') || extension == 'PPTX') {
      return 'PPTX';
    }
    if (normalizedMime.contains('word') || extension == 'DOCX') {
      return 'DOCX';
    }
    if (normalizedMime.startsWith('image/')) return 'IMAGE';
    if (normalizedMime.contains('text') || extension == 'TXT') return 'TXT';
    return extension.isEmpty ? 'FILE' : extension;
  }
}

class _KnowledgeBaseListCard extends StatelessWidget {
  const _KnowledgeBaseListCard({
    required this.file,
    required this.description,
    required this.isOfficial,
    required this.isInGalaxy,
    required this.onTap,
    required this.onContributorTap,
  });

  final GroupFileInfo file;
  final String description;
  final bool isOfficial;
  final bool isInGalaxy;
  final VoidCallback onTap;
  final VoidCallback onContributorTap;

  @override
  Widget build(BuildContext context) {
    final formattedDate =
        DateFormat.yMMMd(context.l10n.localeName).format(file.createdAt);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(22),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(
                    _iconForMime(file.mimeType, file.fileName),
                    color: DS.brandPrimary,
                    size: 26,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              file.fileName,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(fontWeight: DS.fontWeightBold),
                            ),
                          ),
                          if (isOfficial)
                            const Padding(
                              padding: EdgeInsets.only(left: DS.spacing8),
                              child: Icon(
                                Icons.star_rounded,
                                color: Color(0xFFE0A800),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing6),
                      Text(
                        [
                          _typeLabel(file.mimeType, file.fileName),
                          _formatSize(file.fileSize),
                          '$formattedDate 上传',
                        ].join(' · '),
                        style: TextStyle(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (description.isNotEmpty) ...[
              const SizedBox(height: DS.spacing12),
              Text(
                description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
            ],
            const SizedBox(height: DS.spacing12),
            Row(
              children: [
                InkWell(
                  onTap: onContributorTap,
                  borderRadius: BorderRadius.circular(999),
                  child: Ink(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing8,
                      vertical: DS.spacing6,
                    ),
                    decoration: BoxDecoration(
                      color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SparkleAvatar(
                          radius: 12,
                          url: file.sharedBy?.avatarUrl,
                          fallbackText: file.sharedBy?.displayName,
                        ),
                        const SizedBox(width: DS.spacing8),
                        Text(
                          file.sharedBy?.displayName ?? '群成员',
                          style: TextStyle(
                            fontSize: 12,
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const Spacer(),
                if (file.category?.isNotEmpty ?? false)
                  _InlinePill(label: file.category!, icon: Icons.folder_outlined),
                if (isInGalaxy) ...[
                  const SizedBox(width: DS.spacing8),
                  const _InlinePill(
                    label: '群星图',
                    icon: Icons.auto_awesome_outlined,
                  ),
                ],
                const SizedBox(width: DS.spacing8),
                _InlinePill(
                  label: '${file.downloadCount}',
                  icon: Icons.download_outlined,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  IconData _iconForMime(String mimeType, String fileName) {
    final normalizedMime = mimeType.toLowerCase();
    final extension = fileName.contains('.')
        ? fileName.split('.').last.toLowerCase()
        : '';

    if (normalizedMime.contains('pdf') || extension == 'pdf') {
      return Icons.picture_as_pdf_rounded;
    }
    if (normalizedMime.contains('presentation') || extension == 'pptx') {
      return Icons.slideshow_rounded;
    }
    if (normalizedMime.contains('word') || extension == 'docx') {
      return Icons.description_rounded;
    }
    if (normalizedMime.startsWith('image/')) {
      return Icons.image_outlined;
    }
    if (normalizedMime.contains('text') || extension == 'txt') {
      return Icons.notes_rounded;
    }
    return Icons.insert_drive_file_rounded;
  }

  String _typeLabel(String mimeType, String fileName) {
    final normalizedMime = mimeType.toLowerCase();
    final extension = fileName.contains('.')
        ? fileName.split('.').last.toUpperCase()
        : '';

    if (normalizedMime.contains('pdf')) return 'PDF';
    if (normalizedMime.contains('presentation') || extension == 'PPTX') {
      return 'PPTX';
    }
    if (normalizedMime.contains('word') || extension == 'DOCX') {
      return 'DOCX';
    }
    if (normalizedMime.startsWith('image/')) return 'IMAGE';
    if (normalizedMime.contains('text') || extension == 'TXT') return 'TXT';
    return extension.isEmpty ? 'FILE' : extension;
  }

  String _formatSize(int bytes) {
    if (bytes < 1024) return '${bytes}B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)}KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / 1024 / 1024).toStringAsFixed(1)}MB';
    }
    return '${(bytes / 1024 / 1024 / 1024).toStringAsFixed(1)}GB';
  }
}

class _KnowledgeBaseGridCard extends StatelessWidget {
  const _KnowledgeBaseGridCard({
    required this.file,
    required this.description,
    required this.isOfficial,
    required this.isInGalaxy,
    required this.onTap,
  });

  final GroupFileInfo file;
  final String description;
  final bool isOfficial;
  final bool isInGalaxy;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      _iconForMime(file.mimeType, file.fileName),
                      color: DS.brandPrimary,
                    ),
                  ),
                  const Spacer(),
                  if (isOfficial)
                    const Icon(
                      Icons.star_rounded,
                      color: Color(0xFFE0A800),
                    ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                file.fileName,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                description.isEmpty ? '点击查看预览与详情' : description,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: DS.textSecondary, height: 1.35),
              ),
              const Spacer(),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _InlinePill(
                    label: _typeLabel(file.mimeType, file.fileName),
                    icon: Icons.label_outline_rounded,
                  ),
                  _InlinePill(
                    label: '${file.downloadCount}',
                    icon: Icons.download_outlined,
                  ),
                  if (isInGalaxy)
                    const _InlinePill(
                      label: '群星图',
                      icon: Icons.auto_awesome_outlined,
                    ),
                ],
              ),
            ],
          ),
        ),
      );

  IconData _iconForMime(String mimeType, String fileName) {
    final normalizedMime = mimeType.toLowerCase();
    final extension = fileName.contains('.')
        ? fileName.split('.').last.toLowerCase()
        : '';

    if (normalizedMime.contains('pdf') || extension == 'pdf') {
      return Icons.picture_as_pdf_rounded;
    }
    if (normalizedMime.contains('presentation') || extension == 'pptx') {
      return Icons.slideshow_rounded;
    }
    if (normalizedMime.contains('word') || extension == 'docx') {
      return Icons.description_rounded;
    }
    if (normalizedMime.startsWith('image/')) {
      return Icons.image_outlined;
    }
    if (normalizedMime.contains('text') || extension == 'txt') {
      return Icons.notes_rounded;
    }
    return Icons.insert_drive_file_rounded;
  }

  String _typeLabel(String mimeType, String fileName) {
    final normalizedMime = mimeType.toLowerCase();
    final extension = fileName.contains('.')
        ? fileName.split('.').last.toUpperCase()
        : '';

    if (normalizedMime.contains('pdf')) return 'PDF';
    if (normalizedMime.contains('presentation') || extension == 'PPTX') {
      return 'PPTX';
    }
    if (normalizedMime.contains('word') || extension == 'DOCX') {
      return 'DOCX';
    }
    if (normalizedMime.startsWith('image/')) return 'IMAGE';
    if (normalizedMime.contains('text') || extension == 'TXT') return 'TXT';
    return extension.isEmpty ? 'FILE' : extension;
  }
}

class _DocumentPreviewPanel extends ConsumerStatefulWidget {
  const _DocumentPreviewPanel({
    required this.groupId,
    required this.file,
    required this.description,
  });

  final String groupId;
  final GroupFileInfo file;
  final String description;

  @override
  ConsumerState<_DocumentPreviewPanel> createState() =>
      _DocumentPreviewPanelState();
}

class _DocumentPreviewPanelState extends ConsumerState<_DocumentPreviewPanel> {
  Future<File?>? _thumbnailFuture;

  @override
  void initState() {
    super.initState();
    _thumbnailFuture = _loadThumbnail();
  }

  Future<File?> _loadThumbnail() async {
    final repo = ref.read(fileRepositoryProvider);
    final cache = ref.read(fileCacheServiceProvider);
    final cacheKey = 'kb_thumb_${widget.file.fileId}';
    final cached = await cache.getCachedFile(cacheKey);
    if (cached != null) return cached;

    final presigned = await repo.getThumbnailUrl(
      widget.file.fileId,
      groupId: widget.groupId,
    );
    if (presigned.url.isEmpty) return null;
    return cache.fetchAndCache(cacheKey, presigned.url, extension: '.jpg');
  }

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(20),
              ),
              child: SizedBox(
                height: 180,
                width: double.infinity,
                child: FutureBuilder<File?>(
                  future: _thumbnailFuture,
                  builder: (context, snapshot) {
                    if (snapshot.hasData && snapshot.data != null) {
                      return Image.file(
                        snapshot.data!,
                        fit: BoxFit.cover,
                      );
                    }

                    return DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            DS.brandPrimary.withValues(alpha: 0.14),
                            DS.info.withValues(alpha: 0.06),
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                      ),
                      child: Center(
                        child: Icon(
                          Icons.menu_book_rounded,
                          size: 44,
                          color: DS.brandPrimary,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '预览摘录',
                    style: TextStyle(
                      fontWeight: DS.fontWeightSemiBold,
                      color: DS.textPrimary,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    widget.description.isEmpty
                        ? '文件已上传到群知识库。若系统已生成预览，将显示首页缩略图；保存到个人资料库后也会触发后续处理。'
                        : widget.description,
                    style: TextStyle(
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _LockedKnowledgeBase extends StatelessWidget {
  const _LockedKnowledgeBase();

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 76,
                height: 76,
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.10),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.folder_copy_outlined,
                  size: 34,
                  color: DS.brandPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                '加入群组后可浏览共享资料',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: DS.fontWeightBold),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                '群知识库会展示群成员共享的学习材料、官方文档和精选资源。',
                textAlign: TextAlign.center,
                style: TextStyle(color: DS.textSecondary, height: 1.4),
              ),
            ],
          ),
        ),
      );
}

class _KnowledgeBaseEmptyState extends StatelessWidget {
  const _KnowledgeBaseEmptyState();

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.10),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.auto_stories_outlined,
              size: 34,
              color: DS.brandPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            '还没有共享资料',
            textAlign: TextAlign.center,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: DS.fontWeightBold),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '上传真题、词汇表、写作模板或复习笔记，让群知识库开始生长。',
            textAlign: TextAlign.center,
            style: TextStyle(color: DS.textSecondary, height: 1.4),
          ),
        ],
      );
}

class _SortChip extends StatelessWidget {
  const _SortChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(right: DS.spacing8),
        child: FilterChip(
          label: Text(label),
          selected: selected,
          onSelected: (_) => onTap(),
        ),
      );
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(right: DS.spacing8),
        child: ChoiceChip(
          label: Text(label),
          selected: selected,
          onSelected: (_) => onTap(),
        ),
      );
}

class _InlinePill extends StatelessWidget {
  const _InlinePill({
    required this.label,
    required this.icon,
  });

  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.icon,
    required this.label,
    this.accentColor,
  });

  final IconData icon;
  final String label;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: (accentColor ?? DS.brandPrimary).withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: accentColor ?? DS.brandPrimary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: DS.fontWeightSemiBold,
                color: accentColor ?? DS.textPrimary,
              ),
            ),
          ],
        ),
      );
}
