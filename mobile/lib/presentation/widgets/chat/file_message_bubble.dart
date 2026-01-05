import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:url_launcher/url_launcher.dart';

class FileMessageBubbleWithThumbnail extends ConsumerStatefulWidget {
  const FileMessageBubbleWithThumbnail({
    required this.data,
    required this.isMe,
    super.key,
    this.groupId,
  });

  final FileMessageData data;
  final bool isMe;
  final String? groupId;

  @override
  ConsumerState<FileMessageBubbleWithThumbnail> createState() =>
      _FileMessageBubbleWithThumbnailState();
}

class _FileMessageBubbleWithThumbnailState
    extends ConsumerState<FileMessageBubbleWithThumbnail> {
  Future<File?>? _thumbnailFuture;

  @override
  void initState() {
    super.initState();
    _thumbnailFuture = _loadThumbnail();
  }

  @override
  void didUpdateWidget(covariant FileMessageBubbleWithThumbnail oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data.fileId != widget.data.fileId ||
        oldWidget.groupId != widget.groupId) {
      _thumbnailFuture = _loadThumbnail();
    }
  }

  Future<File?> _loadThumbnail() async {
    final repo = ref.read(fileRepositoryProvider);
    final cache = ref.read(fileCacheServiceProvider);
    final cacheKey = 'thumb_${widget.data.fileId}';
    final cached = await cache.getCachedFile(cacheKey);
    if (cached != null) return cached;

    final presigned =
        await repo.getThumbnailUrl(widget.data.fileId, groupId: widget.groupId);
    if (presigned.url.isEmpty) return null;
    return cache.fetchAndCache(cacheKey, presigned.url, extension: '.jpg');
  }

  Future<void> _openFile() async {
    if (widget.data.fileId.isEmpty) return;
    final repo = ref.read(fileRepositoryProvider);
    final presigned =
        await repo.getDownloadUrl(widget.data.fileId, groupId: widget.groupId);
    final uri = Uri.tryParse(presigned.url);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final sizeText =
        widget.data.fileSize == null ? '' : _formatSize(widget.data.fileSize!);
    final statusText = _statusLabel(widget.data.status);

    return GestureDetector(
      onTap: _openFile,
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: widget.isMe ? DS.primaryBase : DS.brandPrimary,
          borderRadius: BorderRadius.circular(16),
          boxShadow: widget.isMe
              ? [
                  BoxShadow(
                      color: DS.primaryBase.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 4),),
                ]
              : DS.shadowSm,
          border: widget.isMe ? null : Border.all(color: DS.neutral100),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: SizedBox(
                width: 56,
                height: 56,
                child: FutureBuilder<File?>(
                  future: _thumbnailFuture,
                  builder: (context, snapshot) {
                    if (snapshot.hasData && snapshot.data != null) {
                      return Image.file(
                        snapshot.data!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => _fallbackIcon(),
                      );
                    }
                    return _fallbackIcon();
                  },
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    widget.data.fileName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontWeight: DS.fontWeightSemiBold,
                      color: widget.isMe ? DS.brandPrimary : DS.neutral900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    [
                      if (sizeText.isNotEmpty) sizeText,
                      if (statusText.isNotEmpty) statusText,
                    ].join(' · '),
                    style: TextStyle(
                      fontSize: 12,
                      color: widget.isMe
                          ? DS.brandPrimary38
                          : (isDark ? DS.neutral300 : DS.neutral600),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            Icon(
              Icons.download_rounded,
              size: 18,
              color: widget.isMe ? DS.brandPrimary : DS.neutral700,
            ),
          ],
        ),
      ),
    );
  }

  Widget _fallbackIcon() => ColoredBox(
        color: DS.neutral200,
        child: Center(
          child: Icon(Icons.insert_drive_file, color: DS.neutral600),
        ),
      );

  String _formatSize(int bytes) {
    if (bytes < 1024) return '${bytes}B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)}KB';
    if (bytes < 1024 * 1024 * 1024)
      return '${(bytes / 1024 / 1024).toStringAsFixed(1)}MB';
    return '${(bytes / 1024 / 1024 / 1024).toStringAsFixed(1)}GB';
  }

  String _statusLabel(String? status) {
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
        return status ?? '';
    }
  }
}
