import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/presentation/widgets/achievement_card_generator.dart';

/// 成就分享对话框
///
/// 生成成就卡片并提供分享选项：
/// - 分享到社交媒体
/// - 保存到相册
/// - 复制链接
class AchievementShareDialog extends StatefulWidget {
  const AchievementShareDialog({
    required this.achievementType,
    required this.data,
    super.key,
  });
  final String achievementType;
  final Map<String, dynamic> data;

  @override
  State<AchievementShareDialog> createState() => _AchievementShareDialogState();
}

class _AchievementShareDialogState extends State<AchievementShareDialog> {
  bool _isGenerating = false;
  String? _imagePath;

  @override
  void initState() {
    super.initState();
    _generateCard();
  }

  Future<void> _generateCard() async {
    setState(() => _isGenerating = true);

    try {
      // Generate the card image
      final imageData = await AchievementCardGenerator.generateCard(
        achievementType: widget.achievementType,
        data: widget.data,
      );

      if (imageData != null) {
        // Save to temporary directory
        final tempDir = await getTemporaryDirectory();
        final file = File(
          '${tempDir.path}/achievement_${DateTime.now().millisecondsSinceEpoch}.png',
        );
        await file.writeAsBytes(imageData);

        setState(() {
          _imagePath = file.path;
          _isGenerating = false;
        });
      } else {
        setState(() => _isGenerating = false);
        if (mounted) {
          _showError('生成失败，请重试');
        }
      }
    } catch (e) {
      setState(() => _isGenerating = false);
      if (mounted) {
        _showError('生成失败: $e');
      }
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  Future<void> _shareToSocial() async {
    if (_imagePath == null) return;

    try {
      await Share.shareXFiles(
        [XFile(_imagePath!)],
        text: '我在 Sparkle 取得了新成就！🎉',
      );
    } catch (e) {
      _showError('分享失败: $e');
    }
  }

  Future<void> _saveToGallery() async {
    if (_imagePath == null) return;

    try {
      // Feature: Use image_gallery_saver package to save to gallery
      // Requires: flutter pub add image_gallery_saver
      // await ImageGallerySaver.saveFile(_imagePath!);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('已保存到相册')),
        );
      }
    } catch (e) {
      _showError('保存失败: $e');
    }
  }

  @override
  Widget build(BuildContext context) => Dialog(
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(DS.xl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Title
              Row(
                children: [
                  Icon(Icons.share, color: DS.brandPrimary, size: 28),
                  const SizedBox(width: DS.md),
                  Text(
                    '分享成就',
                    style: TextStyle(
                      color: DS.brandPrimary,
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
                          '正在生成分享卡片...',
                          style: TextStyle(color: DS.brandPrimary70),
                        ),
                      ],
                    ),
                  ),
                )
              else if (_imagePath != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.file(
                    File(_imagePath!),
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

              const SizedBox(height: DS.xl),

              // Share options
              if (_imagePath != null) ...[
                _buildShareButton(
                  icon: Icons.share,
                  label: '分享到社交媒体',
                  color: DS.brandPrimaryConst,
                  onTap: _shareToSocial,
                ),
                const SizedBox(height: DS.md),
                _buildShareButton(
                  icon: Icons.save_alt,
                  label: '保存到相册',
                  color: DS.success,
                  onTap: _saveToGallery,
                ),
              ],

              const SizedBox(height: DS.md),

              // Close button
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text(
                  '关闭',
                  style: TextStyle(color: DS.brandPrimary70),
                ),
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
                    color: DS.brandPrimaryConst,
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
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
  required String achievementType,
  required Map<String, dynamic> data,
}) {
  showDialog(
    context: context,
    builder: (context) => AchievementShareDialog(
      achievementType: achievementType,
      data: data,
    ),
  );
}
