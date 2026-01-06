import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/presentation/widgets/file/file_picker_with_presigned.dart';
import 'package:url_launcher/url_launcher.dart';

class GroupFilesScreen extends ConsumerStatefulWidget {
  const GroupFilesScreen({required this.groupId, super.key});

  final String groupId;

  @override
  ConsumerState<GroupFilesScreen> createState() => _GroupFilesScreenState();
}

class _GroupFilesScreenState extends ConsumerState<GroupFilesScreen> {
  Future<List<GroupFileInfo>>? _filesFuture;
  Future<List<GroupFileCategoryStat>>? _categoriesFuture;
  String? _category;
  String _query = '';
  bool _gridView = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final repo = ref.read(fileRepositoryProvider);
    setState(() {
      _filesFuture = repo.listGroupFiles(widget.groupId, category: _category);
      _categoriesFuture = repo.getGroupFileCategories(widget.groupId);
    });
  }

  Future<void> _openFile(GroupFileInfo file) async {
    if (!file.canDownload) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('暂无下载权限')),
      );
      return;
    }
    final repo = ref.read(fileRepositoryProvider);
    final presigned =
        await repo.getDownloadUrl(file.fileId, groupId: widget.groupId);
    final uri = Uri.tryParse(presigned.url);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('群文件库'),
        actions: [
          IconButton(
            icon: Icon(
                _gridView ? Icons.view_list_rounded : Icons.grid_view_rounded,),
            onPressed: () => setState(() => _gridView = !_gridView),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            backgroundColor: Colors.transparent,
            builder: (context) => FilePickerWithPresignedUpload(
              groupId: widget.groupId,
              onUploaded: (file) async {
                Navigator.pop(context);
                final repo = ref.read(fileRepositoryProvider);
                await repo.shareToGroup(
                  widget.groupId,
                  file.id,
                  sendMessage: false,
                );
                _reload();
              },
            ),
          );
        },
        child: const Icon(Icons.upload_file_rounded),
      ),
      body: Column(
        children: [
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.sm),
            child: TextField(
              decoration: InputDecoration(
                hintText: '搜索文件',
                prefixIcon: const Icon(Icons.search),
                filled: true,
                fillColor: isDark ? DS.neutral800 : DS.neutral100,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
              onChanged: (value) => setState(() => _query = value.trim()),
            ),
          ),
          SizedBox(
            height: 36,
            child: FutureBuilder<List<GroupFileCategoryStat>>(
              future: _categoriesFuture,
              builder: (context, snapshot) {
                final categories = snapshot.data ?? [];
                return ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: DS.lg),
                  children: [
                    _buildCategoryChip('全部', null),
                    for (final item in categories)
                      _buildCategoryChip(item.category ?? '未分类', item.category),
                  ],
                );
              },
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: FutureBuilder<List<GroupFileInfo>>(
              future: _filesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text('加载失败: ${snapshot.error}'));
                }

                final files = (snapshot.data ?? [])
                    .where((f) =>
                        _query.isEmpty ||
                        f.fileName.toLowerCase().contains(_query.toLowerCase()),)
                    .toList();

                if (files.isEmpty) {
                  return const Center(child: Text('暂无文件'));
                }

                if (_gridView) {
                  return GridView.builder(
                    padding: const EdgeInsets.all(DS.lg),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      mainAxisSpacing: 12,
                      crossAxisSpacing: 12,
                      childAspectRatio: 1.2,
                    ),
                    itemCount: files.length,
                    itemBuilder: (context, index) =>
                        _buildGridItem(files[index]),
                  );
                }

                return ListView.separated(
                  padding: const EdgeInsets.all(DS.lg),
                  itemCount: files.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, index) => _buildListItem(files[index]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryChip(String label, String? category) {
    final isSelected = category == _category;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: isSelected,
        onSelected: (_) {
          setState(() => _category = category);
          _reload();
        },
      ),
    );
  }

  Widget _buildListItem(GroupFileInfo file) => InkWell(
        onTap: () => _openFile(file),
        child: Container(
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: DS.neutral100,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              const Icon(Icons.insert_drive_file, size: 32),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(file.fileName,
                        maxLines: 1, overflow: TextOverflow.ellipsis,),
                    const SizedBox(height: 4),
                    Text(
                        '${_formatSize(file.fileSize)} · ${_statusLabel(file.status)}',
                        style: TextStyle(color: DS.neutral600),),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      );

  Widget _buildGridItem(GroupFileInfo file) => InkWell(
        onTap: () => _openFile(file),
        child: Container(
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: DS.neutral100,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.insert_drive_file, size: 36),
              const SizedBox(height: 8),
              Text(file.fileName, maxLines: 2, overflow: TextOverflow.ellipsis),
              const Spacer(),
              Text(_formatSize(file.fileSize),
                  style: TextStyle(color: DS.neutral600, fontSize: 12),),
            ],
          ),
        ),
      );

  String _formatSize(int bytes) {
    if (bytes < 1024) return '${bytes}B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)}KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / 1024 / 1024).toStringAsFixed(1)}MB';
    }
    return '${(bytes / 1024 / 1024 / 1024).toStringAsFixed(1)}GB';
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'processing':
        return '处理中';
      case 'processed':
        return '就绪';
      case 'failed':
        return '失败';
      case 'uploaded':
        return '已上传';
      default:
        return status;
    }
  }
}
