import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:gal/gal.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

typedef AchievementShareCardDownloader = Future<File> Function(
  AchievementShareCard shareCard,
);
typedef AchievementShareFileAction = Future<void> Function(
  File file,
  AchievementShareCard shareCard,
);
typedef AchievementSharePreviewBuilder = Widget Function(
  File file,
  AchievementShareCard shareCard,
);

/// 成就分享对话框
///
/// 加载服务端生成的成就卡片并提供分享选项：
/// - 分享到社交媒体
/// - 保存到相册
class AchievementShareDialog extends StatefulWidget {
  const AchievementShareDialog({
    required this.shareCardFuture,
    this.downloadCard,
    this.shareFile,
    this.saveFileToGallery,
    this.previewBuilder,
    this.showFeedback = true,
    super.key,
  });
  final Future<AchievementShareCard?> shareCardFuture;
  final AchievementShareCardDownloader? downloadCard;
  final AchievementShareFileAction? shareFile;
  final AchievementShareFileAction? saveFileToGallery;
  final AchievementSharePreviewBuilder? previewBuilder;
  final bool showFeedback;

  @override
  State<AchievementShareDialog> createState() => _AchievementShareDialogState();
}

class _AchievementShareDialogState extends State<AchievementShareDialog> {
  bool _isGenerating = false;
  File? _imageFile;
  AchievementShareCard? _shareCard;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    unawaited(_prepareCard());
  }

  Future<void> _prepareCard() async {
    setState(() => _isGenerating = true);

    try {
      final shareCard = await widget.shareCardFuture;
      if (shareCard == null) {
        throw Exception(context.l10n.shareCardGenerateFailed);
      }

      final downloader = widget.downloadCard ?? _downloadCardToTempFile;
      final file = await downloader(shareCard);

      if (!mounted) return;
      setState(() {
        _shareCard = shareCard;
        _imageFile = file;
        _errorMessage = null;
        _isGenerating = false;
      });
    } catch (e) {
      setState(() {
        _isGenerating = false;
        _errorMessage = e.toString();
      });
      if (mounted) {
        _showError(context.l10n.shareCardPrepareFailed(e.toString()));
      }
    }
  }

  void _showError(String message) {
    if (!widget.showFeedback) {
      return;
    }
    AppFeedback.error(context, message);
  }

  Future<void> _shareToSocial() async {
    if (_imageFile == null || _shareCard == null) return;

    try {
      final shareFile = widget.shareFile ?? _shareFile;
      await shareFile(_imageFile!, _shareCard!);
    } catch (e) {
      _showError(context.l10n.shareFailed(e.toString()));
    }
  }

  Future<void> _saveToGallery() async {
    if (_imageFile == null || _shareCard == null) return;

    try {
      final photoStatus = await Permission.photos.request();
      PermissionStatus? storageStatus;
      if (!photoStatus.isGranted &&
          !photoStatus.isLimited &&
          Platform.isAndroid) {
        storageStatus = await Permission.storage.request();
      }
      final hasPermission = photoStatus.isGranted ||
          photoStatus.isLimited ||
          (storageStatus?.isGranted ?? false);
      if (!hasPermission) {
        if (mounted) {
          await showAppPermissionDialog(
            context,
            permission: Platform.isAndroid
                ? AppPermissionKind.storage
                : AppPermissionKind.photos,
          );
        }
        throw Exception(context.l10n.noGalleryPermission);
      }

      final saveFile = widget.saveFileToGallery ?? _saveImageToGallery;
      await saveFile(_imageFile!, _shareCard!);
      if (mounted && widget.showFeedback) {
        AppFeedback.success(context, context.l10n.savedToGallery);
      }
    } catch (e) {
      _showError(context.l10n.saveFailed(e.toString()));
    }
  }

  @override
  Widget build(BuildContext context) => Dialog(
        backgroundColor: DS.surfaceTertiary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(DS.xl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Title
              Row(
                children: [
                  Icon(Icons.share, color: DS.brandPrimaryConst, size: 28),
                  const SizedBox(width: DS.md),
                  Text(
                    context.l10n.shareAchievement,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.xl),

              // Preview
              if (_isGenerating)
                SizedBox(
                  height: 200,
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const CircularProgressIndicator(),
                        const SizedBox(height: DS.lg),
                        Text(
                          context.l10n.sharePreparingCard,
                          style: TextStyle(color: DS.textSecondary),
                        ),
                      ],
                    ),
                  ),
                )
              else if (_imageFile != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child:
                      widget.previewBuilder?.call(_imageFile!, _shareCard!) ??
                          Image.file(
                            _imageFile!,
                            height: 300,
                            fit: BoxFit.cover,
                          ),
                )
              else
                SizedBox(
                  height: 200,
                  child: Center(
                    child: Icon(
                      Icons.error_outline,
                      color: DS.error,
                      size: 64,
                    ),
                  ),
                ),

              if (_errorMessage != null) ...[
                const SizedBox(height: DS.md),
                Text(
                  _errorMessage!,
                  style: TextStyle(color: DS.textSecondary),
                  textAlign: TextAlign.center,
                ),
              ],

              const SizedBox(height: DS.xl),

              // Share options
              if (_imageFile != null) ...[
                _buildShareButton(
                  icon: Icons.share,
                  label: context.l10n.shareToSocialMedia,
                  color: DS.brandPrimaryConst,
                  onTap: _shareToSocial,
                ),
                const SizedBox(height: DS.md),
                _buildShareButton(
                  icon: Icons.save_alt,
                  label: context.l10n.saveToGallery,
                  color: DS.success,
                  onTap: _saveToGallery,
                ),
              ],

              const SizedBox(height: DS.md),

              // Close button
              SparkleButton(
                label: context.l10n.close,
                variant: ButtonVariant.ghost,
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
        ),
      );

  Widget _buildShareButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) =>
      InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(DS.lg),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color.withValues(alpha: 0.5)),
          ),
          child: Row(
            children: [
              Icon(icon, color: color, size: 24),
              const SizedBox(width: DS.lg),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontSize: 16,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ),
              Icon(Icons.arrow_forward_ios, color: color, size: 16),
            ],
          ),
        ),
      );
}

/// 便捷函数：显示成就分享对话框
void showAchievementShareDialog(
  BuildContext context, {
  required Future<AchievementShareCard?> shareCardFuture,
  AchievementShareCardDownloader? downloadCard,
  AchievementShareFileAction? shareFile,
  AchievementShareFileAction? saveFileToGallery,
  AchievementSharePreviewBuilder? previewBuilder,
  bool showFeedback = true,
}) {
  unawaited(
    showDialog<void>(
      context: context,
      builder: (context) => AchievementShareDialog(
        shareCardFuture: shareCardFuture,
        downloadCard: downloadCard,
        shareFile: shareFile,
        saveFileToGallery: saveFileToGallery,
        previewBuilder: previewBuilder,
        showFeedback: showFeedback,
      ),
    ),
  );
}

Future<File> _downloadCardToTempFile(AchievementShareCard shareCard) async {
  final resolvedUrl = _resolveCardUrl(shareCard.cardUrl);
  if (resolvedUrl.isEmpty) {
    throw Exception(S.shareCardUrlEmpty);
  }

  final response = await http.get(Uri.parse(resolvedUrl));
  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw Exception(S.shareCardDownloadFailed(response.statusCode));
  }

  final tempDir = await getTemporaryDirectory();
  final file = File(
    '${tempDir.path}/achievement_${shareCard.achievement.id}_${shareCard.generatedAt.millisecondsSinceEpoch}.png',
  );
  await file.writeAsBytes(response.bodyBytes);
  return file;
}

Future<void> _shareFile(File file, AchievementShareCard shareCard) async {
  await SharePlus.instance.share(
    ShareParams(
      files: [XFile(file.path)],
      text: S.shareUnlockMessage(shareCard.achievement.name),
    ),
  );
}

Future<void> _saveImageToGallery(
  File file,
  AchievementShareCard shareCard,
) async {
  final photoStatus = await Permission.photos.request();
  if (!photoStatus.isGranted && !photoStatus.isLimited && Platform.isAndroid) {
    final storageStatus = await Permission.storage.request();
    if (!storageStatus.isGranted) {
      throw Exception(S.noGalleryPermission);
    }
  } else if (!photoStatus.isGranted &&
      !photoStatus.isLimited &&
      Platform.isIOS) {
    throw Exception(S.noGalleryPermission);
  }

  await Gal.putImage(file.path, album: 'Sparkle');
}

String _resolveCardUrl(String rawUrl) {
  if (rawUrl.isEmpty) {
    return rawUrl;
  }
  final uri = Uri.parse(rawUrl);
  if (uri.hasScheme) {
    return rawUrl;
  }
  return Uri.parse(ApiConstants.baseUrl).resolve(rawUrl).toString();
}
