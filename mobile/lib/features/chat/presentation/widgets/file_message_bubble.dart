import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

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
  bool _isSavingToLibrary = false;

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

  Future<void> _saveToLibrary() async {
    final groupId = widget.groupId;
    if (groupId == null || widget.data.fileId.isEmpty || _isSavingToLibrary) {
      return;
    }

    setState(() => _isSavingToLibrary = true);
    try {
      await ref
          .read(fileRepositoryProvider)
          .copyGroupFileToMyLibrary(groupId, widget.data.fileId);
      if (!mounted) return;
      AppFeedback.success(context, context.l10n.chatFileSavedToLibrary);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, context.l10n.chatFileSaveFailed(e.toString()));
    } finally {
      if (mounted) {
        setState(() => _isSavingToLibrary = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final sizeText =
        widget.data.fileSize == null ? '' : _formatSize(widget.data.fileSize!);
    final statusText = _statusLabel(widget.data.status);
    final accentColor = widget.isMe ? DS.chatBubbleUserText : DS.brandPrimary;
    final secondaryColor = widget.isMe
        ? DS.chatBubbleUserText.withValues(alpha: 0.74)
        : (isDark ? DS.neutral300 : DS.neutral600);
    final borderColor = widget.isMe
        ? DS.chatBubbleUserText.withValues(alpha: 0.12)
        : DS.borderSubtle;

    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: widget.isMe ? DS.chatBubbleUser : DS.chatBubbleOther,
        borderRadius: BorderRadius.circular(18),
        boxShadow: widget.isMe
            ? [
                BoxShadow(
                  color: DS.chatBubbleUser.withValues(alpha: 0.24),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ]
            : DS.shadowSm,
        border: Border.all(color: borderColor),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: accentColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  context.l10n.chatFileLearningMaterial,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: DS.fontWeightSemiBold,
                    color: accentColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: SizedBox(
                  width: 64,
                  height: 64,
                  child: FutureBuilder<File?>(
                    future: _thumbnailFuture,
                    builder: (context, snapshot) {
                      if (snapshot.hasData && snapshot.data != null) {
                        return Image.file(
                          snapshot.data!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) =>
                              _fallbackIcon(accentColor),
                        );
                      }
                      return _fallbackIcon(accentColor);
                    },
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _iconForMime(
                              widget.data.mimeType, widget.data.fileName),
                          size: 18,
                          color: accentColor,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            widget.data.fileName,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontWeight: DS.fontWeightSemiBold,
                              color: widget.isMe
                                  ? DS.chatBubbleUserText
                                  : DS.chatBubbleOtherText,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      [
                        _typeLabel(widget.data.mimeType, widget.data.fileName),
                        if (sizeText.isNotEmpty) sizeText,
                        if (statusText.isNotEmpty) statusText,
                      ].where((part) => part.isNotEmpty).join(' · '),
                      style: TextStyle(
                        fontSize: 12,
                        color: secondaryColor,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Row(
            children: [
              Expanded(
                child: _ActionPill(
                  label: '查看',
                  icon: Icons.open_in_new_rounded,
                  onTap: _openFile,
                  accentColor: accentColor,
                ),
              ),
              if (widget.groupId != null) ...[
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: _ActionPill(
                    label: _isSavingToLibrary
                        ? context.l10n.chatFileSaving
                        : context.l10n.chatFileSaveToLibrary,
                    icon: Icons.bookmark_add_outlined,
                    onTap: _isSavingToLibrary ? null : _saveToLibrary,
                    accentColor: accentColor,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _fallbackIcon(Color accentColor) => ColoredBox(
        color: accentColor.withValues(alpha: 0.10),
        child: Center(
          child: Icon(
            _iconForMime(widget.data.mimeType, widget.data.fileName),
            color: accentColor,
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

  String _statusLabel(String? status) {
    final l10n = I18nService.instance.l10n;
    switch (status) {
      case 'processing':
        return l10n.fileStatusProcessing;
      case 'processed':
        return l10n.fileStatusReady;
      case 'failed':
        return l10n.fileStatusFailed;
      case 'uploaded':
        return l10n.fileStatusUploaded;
      default:
        return status ?? '';
    }
  }

  IconData _iconForMime(String? mimeType, String fileName) {
    final normalizedMime = mimeType?.toLowerCase() ?? '';
    final extension = fileName.split('.').last.toLowerCase();

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

  String _typeLabel(String? mimeType, String fileName) {
    final normalizedMime = mimeType?.toLowerCase() ?? '';
    final extension =
        fileName.contains('.') ? fileName.split('.').last.toUpperCase() : '';

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

class _ActionPill extends StatelessWidget {
  const _ActionPill({
    required this.label,
    required this.icon,
    required this.onTap,
    required this.accentColor,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final Color accentColor;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: Semantics(
          button: true,
          label: 'Chat file message bubble control 1',
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(12),
            child: Ink(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10,
                vertical: DS.spacing10,
              ),
              decoration: BoxDecoration(
                color: accentColor.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: accentColor.withValues(alpha: 0.16)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, size: 16, color: accentColor),
                  const SizedBox(width: DS.spacing6),
                  Flexible(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: DS.fontWeightSemiBold,
                        color: accentColor,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
