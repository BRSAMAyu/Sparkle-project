import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gal/gal.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/share_service.dart';
import 'package:sparkle/core/services/wechat_share_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/share_privacy_settings.dart';
import 'package:sparkle/features/achievement/presentation/widgets/share_template_selector.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// Achievement share bottom sheet with multi-channel options
///
/// Provides sharing options:
/// - Template selection (cosmic, minimal, neon, elegant)
/// - Privacy controls (display name, avatar, date, stats, badge)
/// - WeChat friends (if available)
/// - WeChat moments (if available)
/// - System share
/// - Share to community
/// - Save to gallery
/// - Copy deep link
class AchievementShareBottomSheet extends ConsumerStatefulWidget {
  const AchievementShareBottomSheet({
    required this.achievementId,
    required this.achievementName,
    this.shareCardUrl,
    this.defaultDisplayName,
    this.onCommunityShare,
    super.key,
  });

  final String achievementId;
  final String achievementName;
  final String? shareCardUrl;
  final String? defaultDisplayName;
  final VoidCallback? onCommunityShare;

  @override
  ConsumerState<AchievementShareBottomSheet> createState() =>
      _AchievementShareBottomSheetState();
}

class _AchievementShareBottomSheetState
    extends ConsumerState<AchievementShareBottomSheet> {
  final WeChatShareService _wechatShare = WeChatShareService();

  File? _shareCardFile;
  bool _isLoading = true;
  String? _errorMessage;

  bool _wechatAvailable = false;
  bool _wechatInstalled = false;

  // Template and privacy state
  List<ShareTemplateInfo> _templates = [];
  String _selectedTemplateId = 'cosmic';
  ShareCardPrivacySettings _privacySettings = ShareCardPrivacySettings();

  bool _showPrivacySettings = false;

  @override
  void initState() {
    super.initState();
    _initializeAndPrepare();
  }

  Future<void> _initializeAndPrepare() async {
    // Check WeChat availability and load templates in parallel
    await Future.wait([
      _checkWeChatAvailability(),
      _loadTemplates(),
    ]);

    // Prepare share card with initial settings
    await _prepareShareCard();
  }

  Future<void> _checkWeChatAvailability() async {
    final available = _wechatShare.isAvailable;
    var installed = false;
    if (available) {
      installed = await _wechatShare.isWeChatInstalled();
    }

    if (mounted) {
      setState(() {
        _wechatAvailable = available;
        _wechatInstalled = installed;
      });
    }
  }

  Future<void> _loadTemplates() async {
    final templates =
        await ref.read(achievementProvider.notifier).getShareTemplates();
    if (mounted && templates.isNotEmpty) {
      setState(() {
        _templates = templates;
      });
    } else {
      // Fallback to default templates
      _templates = _getDefaultTemplates();
    }
  }

  List<ShareTemplateInfo> _getDefaultTemplates() {
    final l10n = context.l10n;
    return [
      ShareTemplateInfo(
        id: 'cosmic',
        name: l10n.shareTemplateCosmic,
        description: l10n.shareTemplateCosmicDesc,
      ),
      ShareTemplateInfo(
        id: 'minimal',
        name: l10n.shareTemplateMinimal,
        description: l10n.shareTemplateMinimalDesc,
      ),
      ShareTemplateInfo(
        id: 'neon',
        name: l10n.shareTemplateNeon,
        description: l10n.shareTemplateNeonDesc,
      ),
      ShareTemplateInfo(
        id: 'elegant',
        name: l10n.shareTemplateElegant,
        description: l10n.shareTemplateElegantDesc,
      ),
    ];
  }

  Future<void> _prepareShareCard() async {
    try {
      // Get share card with current template and privacy settings
      final shareCard = await ref
          .read(achievementProvider.notifier)
          .shareAchievement(
            widget.achievementId,
            templateId: _selectedTemplateId,
            privacySettings: _privacySettings,
          );

      var cardUrl = shareCard?.cardUrl ?? widget.shareCardUrl;

      if (cardUrl == null || cardUrl.isEmpty) {
        if (mounted) {
          setState(() {
            _errorMessage = context.l10n.shareCardUrlEmpty;
            _isLoading = false;
          });
        }
        return;
      }

      // Resolve relative URL
      final resolvedUrl = _resolveCardUrl(cardUrl);
      final file = await _downloadCardToTempFile(resolvedUrl, shareCard);

      if (mounted) {
        setState(() {
          _shareCardFile = file;
          _isLoading = false;
          _errorMessage = null;
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

  Future<File> _downloadCardToTempFile(
    String url,
    AchievementShareCard? shareCard,
  ) async {
    final response = await http.get(Uri.parse(url));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(context.l10n.shareCardDownloadFailed(response.statusCode));
    }

    final tempDir = await getTemporaryDirectory();
    final timestamp = shareCard?.generatedAt.millisecondsSinceEpoch ??
        DateTime.now().millisecondsSinceEpoch;
    final privacyHash = _privacySettings.settingsHash();
    final file = File(
      '${tempDir.path}/achievement_${widget.achievementId}_${_selectedTemplateId}_$privacyHash\_$timestamp.png',
    );
    await file.writeAsBytes(response.bodyBytes);
    return file;
  }

  String _resolveCardUrl(String rawUrl) {
    if (rawUrl.isEmpty) return rawUrl;
    final uri = Uri.parse(rawUrl);
    if (uri.hasScheme) return rawUrl;
    return Uri.parse(ApiConstants.baseUrl).resolve(rawUrl).toString();
  }

  void _onTemplateSelected(String templateId) {
    if (_selectedTemplateId == templateId) return;

    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
    setState(() {
      _selectedTemplateId = templateId;
      _isLoading = true;
    });
    _prepareShareCard();
  }

  void _onPrivacySettingsChanged(ShareCardPrivacySettings settings) {
    if (_privacySettings.settingsHash() == settings.settingsHash()) return;

    SensoryFeedbackService.emit(SensoryFeedbackEvent.toggle);
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
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Theme.of(context).scaffoldBackgroundColor,
            Color.alphaBlend(
              DS.info.withValues(alpha: 0.03),
              DS.surfacePrimary,
            ),
          ],
        ),
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
                SparkleStaggerItem(
                  index: 0,
                  child: Container(
                    width: 36,
                    height: 4,
                    decoration: BoxDecoration(
                      color: DS.neutral300,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
                const SizedBox(height: DS.md),

                // Title
                SparkleStaggerItem(
                  index: 1,
                  child: Text(
                    l10n.shareOptionsTitle,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                const SizedBox(height: DS.md),

                // Template Selector
                if (_templates.isNotEmpty) ...[
                  SparkleStaggerItem(
                    index: 2,
                    child: Align(
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
                  ),
                  const SizedBox(height: DS.sm),
                  SparkleStaggerItem(
                    index: 3,
                    child: ShareTemplateSelector(
                      templates: _templates,
                      selectedId: _selectedTemplateId,
                      onSelected: _onTemplateSelected,
                    ),
                  ),
                  const SizedBox(height: DS.md),
                ],

                // Privacy Settings Toggle
                SparkleStaggerItem(
                  index: 4,
                  child: InkWell(
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
                ),
                if (_showPrivacySettings) ...[
                  const SizedBox(height: DS.sm),
                  SharePrivacySettings(
                    settings: _privacySettings,
                    onSettingsChanged: _onPrivacySettingsChanged,
                    defaultDisplayName: widget.defaultDisplayName,
                  ),
                ],
                const SizedBox(height: DS.md),

                // Preview
                SparkleStaggerItem(
                  index: 5,
                  child: _buildPreview(),
                ),
                const SizedBox(height: DS.lg),

                // Share options
                if (_isLoading)
                  Padding(
                    padding: const EdgeInsets.all(DS.xl),
                    child: Column(
                      children: [
                        const CircularProgressIndicator(),
                        const SizedBox(height: DS.sm),
                        Text(
                          l10n.sharePreviewLoading,
                          style: TextStyle(color: DS.textSecondary),
                        ),
                      ],
                    ),
                  )
                else if (_errorMessage != null)
                  Padding(
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
                          label: Text(l10n.shareRegenerateCard),
                        ),
                      ],
                    ),
                  )
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

    return Container(
      height: 160,
      width: 120,
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(
        Icons.image_not_supported_outlined,
        color: DS.neutral400,
        size: 32,
      ),
    );
  }

  Widget _buildShareOptions() {
    final l10n = context.l10n;

    return Column(
      children: [
        // WeChat options (conditional)
        if (_wechatAvailable && _wechatInstalled) ...[
          _buildShareOption(
            icon: Icons.chat,
            label: l10n.shareToWeChatFriends,
            color: const Color(0xFF07C160), // WeChat green
            onTap: () => _shareToWeChatSession(),
          ),
          _buildShareOption(
            icon: Icons.timeline,
            label: l10n.shareToWeChatMoments,
            color: const Color(0xFF07C160), // WeChat green
            onTap: () => _shareToWeChatTimeline(),
          ),
        ],

        // System share
        _buildShareOption(
          icon: Icons.share,
          label: l10n.shareToSystem,
          color: DS.brandPrimary,
          onTap: () => _shareToSystem(),
        ),

        // Community share
        _buildShareOption(
          icon: Icons.groups,
          label: l10n.shareToCommunity,
          color: DS.info,
          onTap: () => _shareToCommunity(),
        ),

        // Save to gallery
        _buildShareOption(
          icon: Icons.save_alt,
          label: l10n.saveImageToGallery,
          color: DS.success,
          onTap: () => _saveToGallery(),
        ),

        // Copy link
        _buildShareOption(
          icon: Icons.link,
          label: l10n.copyDeepLink,
          color: DS.warning,
          onTap: () => _copyDeepLink(),
        ),
      ],
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

    await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
    final result = await _wechatShare.shareImageToSession(_shareCardFile!);
    _handleShareResult(result);
  }

  Future<void> _shareToWeChatTimeline() async {
    if (_shareCardFile == null) return;

    await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
    final result = await _wechatShare.shareImageToTimeline(_shareCardFile!);
    _handleShareResult(result);
  }

  Future<void> _shareToSystem() async {
    if (_shareCardFile == null) return;

    try {
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
      await share_plus.SharePlus.instance.share(
        share_plus.ShareParams(
          files: [share_plus.XFile(_shareCardFile!.path)],
          text: context.l10n.shareUnlockMessage(widget.achievementName),
        ),
      );
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.shareFailed(e.toString()));
      }
    }
  }

  Future<void> _shareToCommunity() async {
    await SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen);
    final rootContext = Navigator.of(context, rootNavigator: true).context;
    Navigator.of(context).pop();

    if (widget.onCommunityShare != null) {
      widget.onCommunityShare!();
      return;
    }

    // Default: show community share sheet
    await showShareResourceSheet(
      rootContext,
      resourceType: 'achievement',
      resourceId: widget.achievementId,
      title: widget.achievementName,
      subtitle: context.l10n.shareUnlockMessage(widget.achievementName),
    );
  }

  Future<void> _saveToGallery() async {
    if (_shareCardFile == null) return;

    try {
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
      // Request permission
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
        return;
      }

      // Save to gallery
      await Gal.putImage(_shareCardFile!.path, album: 'Sparkle');

      if (mounted) {
        AppFeedback.success(context, context.l10n.savedToGallery);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.saveFailed(e.toString()));
      }
    }
  }

  Future<void> _copyDeepLink() async {
    // Generate deep link for achievement
    final deepLink = 'sparkle://achievement/${widget.achievementId}';

    await SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
    await Clipboard.setData(ClipboardData(text: deepLink));

    if (mounted) {
      AppFeedback.success(context, context.l10n.linkCopied);
    }
  }

  void _handleShareResult(ShareResult result) {
    switch (result) {
      case ShareResult.success:
        // Share initiated, WeChat will handle the rest
        Navigator.of(context).pop();
      case ShareResult.unavailable:
        AppFeedback.warning(context, context.l10n.wechatNotInstalled);
      case ShareResult.cancelled:
        // User cancelled, no feedback needed
        break;
      case ShareResult.error:
        if (mounted) {
          AppFeedback.error(context, context.l10n.shareFailed('Unknown error'));
        }
    }
  }
}

/// Convenience function to show the achievement share bottom sheet
Future<void> showAchievementShareSheet(
  BuildContext context, {
  required String achievementId,
  required String achievementName,
  String? shareCardUrl,
  String? defaultDisplayName,
  VoidCallback? onCommunityShare,
}) async {
  await showSensoryModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
    builder: (context) => AchievementShareBottomSheet(
      achievementId: achievementId,
      achievementName: achievementName,
      shareCardUrl: shareCardUrl,
      defaultDisplayName: defaultDisplayName,
      onCommunityShare: onCommunityShare,
    ),
  );
}
