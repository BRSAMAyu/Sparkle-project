import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';

/// Template info for share cards
class ShareTemplate {
  const ShareTemplate({
    required this.id,
    required this.name,
    required this.description,
    this.icon,
    this.color,
  });

  final String id;
  final String name;
  final String? description;
  final IconData? icon;
  final Color? color;
}

/// Default share templates
class DefaultShareTemplates {
  static const List<ShareTemplate> all = [
    ShareTemplate(
      id: 'cosmic',
      name: '星空',
      description: '星空主题',
      icon: Icons.auto_awesome,
      color: Color(0xFF6366F1),
    ),
    ShareTemplate(
      id: 'minimal',
      name: '简约',
      description: '简约风格',
      icon: Icons.minimize,
      color: Color(0xFF64748B),
    ),
    ShareTemplate(
      id: 'neon',
      name: '霓虹',
      description: '霓虹风格',
      icon: Icons.light_mode,
      color: Color(0xFF22D3EE),
    ),
    ShareTemplate(
      id: 'elegant',
      name: '典雅',
      description: '典雅风格',
      icon: Icons.star_outline,
      color: Color(0xFFD4AF37),
    ),
  ];
}

/// Universal share bottom sheet with multi-channel options
///
/// Provides sharing options:
/// - Template selection
/// - Privacy controls
/// - WeChat friends/moments (if available)
/// - System share
/// - Share to community
/// - Save to gallery
/// - Copy deep link
class UniversalShareBottomSheet extends ConsumerStatefulWidget {
  const UniversalShareBottomSheet({
    required this.payload,
    this.onGenerateCard,
    this.onCommunityShare,
    this.templates = DefaultShareTemplates.all,
    super.key,
  });

  /// The share payload containing content info
  final UniversalSharePayload payload;

  /// Callback to generate share card image
  /// Should return a File or null if generation fails
  final Future<File?> Function(UniversalSharePayload payload)? onGenerateCard;

  /// Custom callback for community share
  final VoidCallback? onCommunityShare;

  /// Available templates
  final List<ShareTemplate> templates;

  @override
  ConsumerState<UniversalShareBottomSheet> createState() =>
      _UniversalShareBottomSheetState();
}

class _UniversalShareBottomSheetState
    extends ConsumerState<UniversalShareBottomSheet> {
  final UniversalShareService _shareService = UniversalShareService();

  File? _shareCardFile;
  bool _isLoading = true;
  String? _errorMessage;

  bool _wechatAvailable = false;
  bool _wechatInstalled = false;

  late String _selectedTemplateId;
  late UniversalSharePrivacySettings _privacySettings;
  late List<ShareCaptionOption> _captionOptions;
  int _selectedCaptionIndex = 0;

  bool _showPrivacySettings = false;

  @override
  void initState() {
    super.initState();
    _selectedTemplateId = widget.payload.templateId;
    _privacySettings = widget.payload.privacySettings;
    _captionOptions = _shareService.buildCaptionOptions(widget.payload);
    _initializeAndPrepare();
  }

  Future<void> _initializeAndPrepare() async {
    await Future.wait([
      _checkWeChatAvailability(),
    ]);

    await _prepareShareCard();
  }

  Future<void> _checkWeChatAvailability() async {
    final available = _shareService.isWeChatAvailable;
    bool installed = false;
    if (available) {
      installed = await _shareService.isWeChatInstalled();
    }

    if (mounted) {
      setState(() {
        _wechatAvailable = available;
        _wechatInstalled = installed;
      });
    }
  }

  Future<void> _prepareShareCard() async {
    try {
      // If there's a pre-generated card URL, download it
      if (widget.payload.cardImageUrl != null &&
          widget.payload.cardImageUrl!.isNotEmpty) {
        final file = await _shareService.downloadCardImage(
          widget.payload.cardImageUrl!,
          fileName:
              '${widget.payload.contentType.stringValue}_${widget.payload.resourceId}',
        );

        if (mounted) {
          setState(() {
            _shareCardFile = file;
            _isLoading = false;
            _errorMessage = file == null ? 'Failed to download card' : null;
          });
        }
        return;
      }

      // Otherwise, use the onGenerateCard callback
      if (widget.onGenerateCard != null) {
        final updatedPayload = widget.payload.copyWith(
          templateId: _selectedTemplateId,
          privacySettings: _privacySettings,
        );

        final file = await widget.onGenerateCard!(updatedPayload);

        if (mounted) {
          setState(() {
            _shareCardFile = file;
            _isLoading = false;
            _errorMessage = file == null ? 'Failed to generate card' : null;
          });
        }
        return;
      }

      // No card generation available
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'No card generation available';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  void _onTemplateSelected(String templateId) {
    if (_selectedTemplateId == templateId) return;

    setState(() {
      _selectedTemplateId = templateId;
      _isLoading = true;
    });
    _prepareShareCard();
  }

  void _onPrivacySettingsChanged(UniversalSharePrivacySettings settings) {
    if (_privacySettings.settingsHash() == settings.settingsHash()) return;

    setState(() {
      _privacySettings = settings;
      _isLoading = true;
    });
    _prepareShareCard();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          child: Padding(
            padding: EdgeInsets.only(
              left: DS.lg,
              right: DS.lg,
              top: DS.lg,
              bottom: MediaQuery.of(context).viewInsets.bottom + DS.lg,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Handle bar
                Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: DS.neutral300,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                const SizedBox(height: DS.md),

                // Title
                Text(
                  l10n.shareOptionsTitle,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: DS.md),

                // Template Selector
                if (widget.templates.isNotEmpty) ...[
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      l10n.shareTemplateTitle,
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        fontWeight: DS.fontWeightMedium,
                        color: DS.textSecondary,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  _buildTemplateSelector(),
                  const SizedBox(height: DS.md),
                ],

                // Privacy Settings Toggle
                InkWell(
                  onTap: () {
                    setState(() {
                      _showPrivacySettings = !_showPrivacySettings;
                    });
                  },
                  borderRadius: DS.borderRadius8,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: DS.sm),
                    child: Row(
                      children: [
                        Icon(
                          _showPrivacySettings
                              ? Icons.expand_less
                              : Icons.expand_more,
                          color: DS.textSecondary,
                          size: 20,
                        ),
                        const SizedBox(width: DS.xs),
                        Text(
                          l10n.sharePrivacyTitle,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            fontWeight: DS.fontWeightMedium,
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                if (_showPrivacySettings) ...[
                  const SizedBox(height: DS.sm),
                  _buildPrivacySettings(),
                ],
                const SizedBox(height: DS.md),

                // Preview
                _buildPreview(),
                const SizedBox(height: DS.lg),
                _buildCaptionStudio(),
                const SizedBox(height: DS.md),

                // Share options
                if (_isLoading)
                  _buildLoadingState()
                else if (_errorMessage != null)
                  _buildErrorState()
                else
                  _buildShareOptions(),

                const SizedBox(height: DS.md),

                // Cancel button
                SparkleButton(
                  label: l10n.cancel,
                  variant: ButtonVariant.ghost,
                  onPressed: () => Navigator.of(context).pop(),
                  expand: true,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTemplateSelector() => SizedBox(
        height: 80,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: widget.templates.length,
          separatorBuilder: (_, __) => const SizedBox(width: DS.sm),
          itemBuilder: (context, index) {
            final template = widget.templates[index];
            final isSelected = template.id == _selectedTemplateId;

            return GestureDetector(
              onTap: () => _onTemplateSelected(template.id),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 72,
                decoration: BoxDecoration(
                  borderRadius: DS.borderRadius12,
                  border: Border.all(
                    color: isSelected ? DS.brandPrimary : DS.border,
                    width: isSelected ? 2 : 1,
                  ),
                  color: isSelected
                      ? DS.brandPrimary.withValues(alpha: 0.1)
                      : DS.surfaceSecondary,
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        borderRadius: DS.borderRadius8,
                        color: (template.color ?? DS.brandPrimary)
                            .withValues(alpha: 0.2),
                      ),
                      child: Icon(
                        template.icon ?? Icons.image,
                        color: template.color ?? DS.brandPrimary,
                        size: 20,
                      ),
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      template.name,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        fontWeight:
                            isSelected ? DS.fontWeightBold : DS.fontWeightMedium,
                        color: isSelected ? DS.brandPrimary : DS.textPrimary,
                      ),
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      );

  Widget _buildPrivacySettings() => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildPrivacyToggle(
              title: '显示头像',
              subtitle: '在卡片上显示头像',
              icon: Icons.account_circle_outlined,
              value: _privacySettings.showUserAvatar,
              onChanged: (v) => _onPrivacySettingsChanged(
                _privacySettings.copyWith(showUserAvatar: v),
              ),
            ),
            const SizedBox(height: DS.sm),
            _buildPrivacyToggle(
              title: '显示统计',
              subtitle: '显示详细统计数据',
              icon: Icons.bar_chart_outlined,
              value: _privacySettings.showDetailedStats,
              onChanged: (v) => _onPrivacySettingsChanged(
                _privacySettings.copyWith(showDetailedStats: v),
              ),
            ),
            const SizedBox(height: DS.sm),
            _buildPrivacyToggle(
              title: '显示进度',
              subtitle: '显示完成百分比',
              icon: Icons.show_chart,
              value: _privacySettings.showProgressPercentage,
              onChanged: (v) => _onPrivacySettingsChanged(
                _privacySettings.copyWith(showProgressPercentage: v),
              ),
            ),
          ],
        ),
      );

  Widget _buildPrivacyToggle({
    required String title,
    required String subtitle,
    required IconData icon,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) =>
      Container(
        padding: const EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: DS.borderRadius8,
        ),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: value
                    ? DS.brandPrimary.withValues(alpha: 0.1)
                    : DS.surfaceSecondary,
                borderRadius: DS.borderRadius8,
              ),
              child: Icon(
                icon,
                size: 18,
                color: value ? DS.brandPrimary : DS.textTertiary,
              ),
            ),
            const SizedBox(width: DS.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: DS.fontSizeSm,
                      fontWeight: DS.fontWeightMedium,
                      color: DS.textPrimary,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.textTertiary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            Transform.scale(
              scale: 0.8,
              child: Switch(
                value: value,
                onChanged: onChanged,
                activeTrackColor: DS.brandPrimary.withValues(alpha: 0.3),
              ),
            ),
          ],
        ),
      );

  Widget _buildPreview() {
    if (_isLoading) {
      return Container(
        height: 160,
        width: 120,
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(height: DS.sm),
              Text(
                'Loading...',
                style: TextStyle(
                  color: DS.textTertiary,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (_shareCardFile != null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Image.file(
          _shareCardFile!,
          height: 160,
          fit: BoxFit.cover,
        ),
      );
    }

    // Fallback preview with content info
    return Container(
      width: 200,
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.border),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _getContentTypeIcon(),
            size: 32,
            color: DS.brandPrimary,
          ),
          const SizedBox(height: DS.sm),
          Text(
            widget.payload.title,
            style: TextStyle(
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          if (widget.payload.subtitle != null) ...[
            const SizedBox(height: DS.xs),
            Text(
              widget.payload.subtitle!,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textSecondary,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }

  IconData _getContentTypeIcon() => switch (widget.payload.contentType) {
        ShareableContentType.achievement => Icons.emoji_events,
        ShareableContentType.taskCompletion => Icons.task_alt,
        ShareableContentType.planProgress => Icons.flag,
        ShareableContentType.capsule => Icons.access_time,
        ShareableContentType.knowledgeNode => Icons.school,
        ShareableContentType.learningReport => Icons.assessment,
        ShareableContentType.cognitivePrism => Icons.psychology,
      };

  Widget _buildLoadingState() => Padding(
        padding: const EdgeInsets.all(DS.xl),
        child: Column(
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: DS.sm),
            Text(
              context.l10n.sharePreviewLoading,
              style: TextStyle(color: DS.textSecondary),
            ),
          ],
        ),
      );

  Widget _buildErrorState() => Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          children: [
            Text(
              _errorMessage!,
              style: TextStyle(color: DS.error),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.sm),
            TextButton.icon(
              onPressed: () {
                setState(() {
                  _isLoading = true;
                  _errorMessage = null;
                });
                _prepareShareCard();
              },
              icon: const Icon(Icons.refresh),
              label: Text(context.l10n.shareRegenerateCard),
            ),
          ],
        ),
      );

  Widget _buildShareOptions() => Column(
        children: [
          // WeChat options (conditional)
          if (_wechatAvailable && _wechatInstalled) ...[
            _buildShareOption(
              icon: Icons.chat,
              label: context.l10n.shareToWeChatFriends,
              color: const Color(0xFF07C160),
              onTap: () => _shareToWeChatSession(),
            ),
            _buildShareOption(
              icon: Icons.timeline,
              label: context.l10n.shareToWeChatMoments,
              color: const Color(0xFF07C160),
              onTap: () => _shareToWeChatTimeline(),
            ),
          ],

          // System share
          _buildShareOption(
            icon: Icons.share,
            label: context.l10n.shareToSystem,
            color: DS.brandPrimary,
            onTap: () => _shareToSystem(),
          ),
          _buildShareOption(
            icon: Icons.content_copy_rounded,
            label: '复制分享文案',
            color: const Color(0xFF8B6CEB),
            onTap: () => _copySelectedCaption(),
          ),

          // Community share
          _buildShareOption(
            icon: Icons.groups,
            label: context.l10n.shareToCommunity,
            color: DS.info,
            onTap: () => _shareToCommunity(),
          ),

          // Save to gallery
          _buildShareOption(
            icon: Icons.save_alt,
            label: context.l10n.saveImageToGallery,
            color: DS.success,
            onTap: () => _saveToGallery(),
          ),

          // Copy link
          _buildShareOption(
            icon: Icons.link,
            label: context.l10n.copyDeepLink,
            color: DS.warning,
            onTap: () => _copyDeepLink(),
          ),
        ],
      );

  Widget _buildCaptionStudio() {
    final selectedCaption = _captionOptions[_selectedCaptionIndex];

    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '分享文案',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            '除了海报，也给你准备好了适合发朋友圈、群聊和私聊的文案。',
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
          const SizedBox(height: DS.sm),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: List.generate(_captionOptions.length, (index) {
              final option = _captionOptions[index];
              final selected = index == _selectedCaptionIndex;
              return ChoiceChip(
                selected: selected,
                label: Text('${option.icon} ${option.title}'),
                onSelected: (_) {
                  setState(() {
                    _selectedCaptionIndex = index;
                  });
                },
              );
            }),
          ),
          const SizedBox(height: DS.sm),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.md),
            decoration: BoxDecoration(
              color: DS.surfacePrimary,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.border),
            ),
            child: Text(
              selectedCaption.caption,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textPrimary,
                height: 1.6,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildShareOption({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) =>
      InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.lg,
            vertical: DS.md,
          ),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: DS.fontSizeBase,
                    fontWeight: DS.fontWeightMedium,
                    color: DS.textPrimary,
                  ),
                ),
              ),
              Icon(
                Icons.arrow_forward_ios,
                color: DS.neutral400,
                size: 16,
              ),
            ],
          ),
        ),
      );

  Future<void> _shareToWeChatSession() async {
    if (_shareCardFile == null) return;

    final result = await _shareService.shareToWeChatSession(_shareCardFile!);
    _handleShareResult(result);
  }

  Future<void> _shareToWeChatTimeline() async {
    if (_shareCardFile == null) return;

    final result = await _shareService.shareToWeChatTimeline(_shareCardFile!);
    _handleShareResult(result);
  }

  Future<void> _shareToSystem() async {
    if (_shareCardFile == null) return;

    final result = await _shareService.shareToSystem(
      imageFile: _shareCardFile!,
      text: _captionOptions[_selectedCaptionIndex].caption,
    );
    _handleShareResult(result);
  }

  Future<void> _copySelectedCaption() async {
    await _shareService.copyText(_captionOptions[_selectedCaptionIndex].caption);
    if (mounted) {
      AppFeedback.success(context, '分享文案已复制');
    }
  }

  Future<void> _shareToCommunity() async {
    Navigator.of(context).pop();

    if (widget.onCommunityShare != null) {
      widget.onCommunityShare!();
      return;
    }

    // Check if content type is supported for community sharing
    final unsupportedTypes = [
      ShareableContentType.achievement,
      ShareableContentType.learningReport,
    ];
    if (unsupportedTypes.contains(widget.payload.contentType)) {
      if (mounted) {
        AppFeedback.warning(
          context,
          context.l10n.shareTypeNotSupportedYet,
        );
      }
      return;
    }

    // Default: show community share sheet
    await showShareResourceSheet(
      context,
      resourceType: widget.payload.contentType.stringValue,
      resourceId: widget.payload.resourceId,
      title: widget.payload.title,
      subtitle: widget.payload.subtitle,
    );
  }

  Future<void> _saveToGallery() async {
    if (_shareCardFile == null) return;

    final result = await _shareService.saveToGallery(
      _shareCardFile!,
      name: '${widget.payload.contentType.stringValue}_${widget.payload.resourceId}',
    );

    if (mounted) {
      if (result.isSuccess) {
        AppFeedback.success(context, context.l10n.savedToGallery);
      } else if (result.error == 'Permission denied') {
        await showAppPermissionDialog(
          context,
          permission: Platform.isAndroid
              ? AppPermissionKind.storage
              : AppPermissionKind.photos,
        );
      } else {
        AppFeedback.error(context, context.l10n.gallerySaveFailed);
      }
    }
  }

  Future<void> _copyDeepLink() async {
    final deepLink = widget.payload.deepLink;

    await Clipboard.setData(ClipboardData(text: deepLink));

    if (mounted) {
      AppFeedback.success(context, context.l10n.linkCopied);
    }
  }

  void _handleShareResult(UniversalShareResult result) {
    if (result.isSuccess) {
      Navigator.of(context).pop();
    } else if (result.error == 'Permission denied' ||
        result.error?.contains('unavailable') == true) {
      AppFeedback.warning(context, context.l10n.wechatNotInstalled);
    } else if (result.error != null) {
      AppFeedback.error(
          context, context.l10n.shareFailed(result.error!));
    }
  }
}

/// Convenience function to show the universal share bottom sheet
Future<void> showUniversalShareSheet(
  BuildContext context, {
  required UniversalSharePayload payload,
  Future<File?> Function(UniversalSharePayload payload)? onGenerateCard,
  VoidCallback? onCommunityShare,
  List<ShareTemplate> templates = DefaultShareTemplates.all,
}) async {
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
    builder: (context) => UniversalShareBottomSheet(
      payload: payload,
      onGenerateCard: onGenerateCard,
      onCommunityShare: onCommunityShare,
      templates: templates,
    ),
  );
}
