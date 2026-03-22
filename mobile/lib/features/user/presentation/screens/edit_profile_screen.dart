import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/presentation/widgets/avatar_selection_dialog.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class EditProfileScreen extends ConsumerStatefulWidget {
  const EditProfileScreen({super.key});

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  late TextEditingController _nicknameController;
  late TextEditingController _emailController;
  bool _isLoading = false;
  final _picker = ImagePicker();

  bool get _isSocialAccount {
    final source = ref.read(currentUserProvider)?.registrationSource;
    return source == 'google' || source == 'apple' || source == 'wechat';
  }

  Future<bool> _ensureMediaPermission(String source) async {
    if (source == 'camera') {
      final status = await Permission.camera.request();
      if (status.isGranted) {
        return true;
      }
    } else {
      final photoStatus = await Permission.photos.request();
      if (photoStatus.isGranted || photoStatus.isLimited) {
        return true;
      }

      if (!Platform.isIOS) {
        final storageStatus = await Permission.storage.request();
        if (storageStatus.isGranted) {
          return true;
        }
      }
    }

    if (mounted) {
      await showAppPermissionDialog(
        context,
        permission: source == 'camera'
            ? AppPermissionKind.camera
            : AppPermissionKind.photos,
      );
    }
    return false;
  }

  @override
  void initState() {
    super.initState();
    final user = ref.read(currentUserProvider);
    _nicknameController =
        TextEditingController(text: user?.nickname ?? user?.username ?? '');
    _emailController = TextEditingController(text: user?.email ?? '');
  }

  @override
  void dispose() {
    _nicknameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _pickAndUploadAvatar() async {
    final l10n = context.l10n;
    final user = ref.read(currentUserProvider);
    final source = await showSensoryModalBottomSheet<String>(
      context: context,
      builder: (sheetContext) => GraphiteModalSurface(
        title: l10n.editProfileChangeAvatar,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _AvatarSourceTile(
              icon: Icons.face_retouching_natural_rounded,
              title: l10n.editProfileChooseFromPresets,
              subtitle: '从更丰富的风格头像里快速选择。',
              onTap: () => Navigator.pop(sheetContext, 'preset'),
            ),
            const SizedBox(height: DS.spacing8),
            _AvatarSourceTile(
              icon: Icons.camera_alt_rounded,
              title: l10n.editProfileTakePhoto,
              subtitle: '直接拍摄一张新头像用于上传。',
              onTap: () => Navigator.pop(sheetContext, 'camera'),
            ),
            const SizedBox(height: DS.spacing8),
            _AvatarSourceTile(
              icon: Icons.photo_library_rounded,
              title: l10n.editProfileChooseFromGallery,
              subtitle: '从相册里挑选你已经准备好的图片。',
              onTap: () => Navigator.pop(sheetContext, 'gallery'),
            ),
          ],
        ),
      ),
    );

    if (source == null) return;

    if (source == 'preset') {
      if (!mounted) return;
      final parentContext = context;
      final selectedUrl = await showSensoryDialog<String>(
        context: context,
        builder: (dialogContext) => AvatarSelectionDialog(
          currentAvatarUrl: user?.avatarUrl,
          onAvatarSelected: (_) {},
        ),
      );
      if (!mounted || selectedUrl == null) return;
      setState(() => _isLoading = true);
      try {
        await ref.read(authProvider.notifier).updateAvatar(selectedUrl);
        if (parentContext.mounted) {
          AppFeedback.success(parentContext, l10n.editProfileAvatarUpdated);
        }
      } catch (e) {
        if (parentContext.mounted) {
          AppFeedback.error(
            parentContext,
            l10n.editProfileUpdateFailed(e.toString()),
          );
        }
      } finally {
        if (mounted) setState(() => _isLoading = false);
      }
      return;
    }

    final imageSource =
        source == 'camera' ? ImageSource.camera : ImageSource.gallery;
    final hasPermission = await _ensureMediaPermission(source);
    if (!hasPermission) return;
    final pickedFile = await _picker.pickImage(
      source: imageSource,
      maxWidth: 512,
      maxHeight: 512,
      imageQuality: 75,
    );

    if (pickedFile == null) return;

    setState(() => _isLoading = true);
    try {
      await ref.read(authProvider.notifier).updateAvatar(pickedFile.path);
      if (mounted) {
        AppFeedback.success(context, l10n.editProfileAvatarUpdated);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, l10n.editProfileUploadFailed(e.toString()));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _saveProfile() async {
    final l10n = context.l10n;
    final nickname = _nicknameController.text.trim();
    final email = _emailController.text.trim();

    if (nickname.isEmpty) {
      AppFeedback.info(context, l10n.editProfileNicknameEmpty);
      return;
    }

    if (email.isNotEmpty &&
        !RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email)) {
      AppFeedback.info(context, l10n.editProfileEmailInvalid);
      return;
    }

    setState(() => _isLoading = true);

    try {
      await ref.read(authProvider.notifier).updateProfile({
        'nickname': nickname,
        'email': email,
      });

      if (mounted) {
        AppFeedback.success(context, l10n.editProfileProfileUpdated);
        UserRoutes.popOrGoProfile(context);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, l10n.editProfileUpdateFailed(e.toString()));
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _sendVerificationEmail() async {
    try {
      final message =
          await ref.read(authProvider.notifier).sendVerificationEmail();
      if (!mounted) return;
      AppFeedback.success(context, message);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    }
  }

  Future<void> _verifyEmailWithCode() async {
    final l10n = context.l10n;
    final controller = TextEditingController();
    final token = await showSensoryDialog<String>(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: GraphiteModalSurface(
          title: l10n.editProfileVerifyEmailTitle,
          showHandle: false,
          borderRadius: BorderRadius.circular(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '输入邮件里的验证码即可完成验证，验证通过后你的安全与通知能力会更完整。',
                style: Theme.of(dialogContext).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              TextField(
                controller: controller,
                decoration: InputDecoration(
                  hintText: l10n.editProfileVerifyEmailHint,
                  filled: true,
                  fillColor: DS.surfaceSecondary,
                  border: OutlineInputBorder(
                    borderRadius: DS.borderRadius12,
                    borderSide: BorderSide(color: DS.borderSubtle),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: DS.borderRadius12,
                    borderSide: BorderSide(color: DS.borderSubtle),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: DS.borderRadius12,
                    borderSide: BorderSide(color: DS.primaryBase, width: 1.5),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      label: l10n.cancel,
                      onPressed: () => Navigator.of(dialogContext).pop(),
                      expand: true,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: SparkleButton.primary(
                      label: l10n.editProfileVerifyEmailConfirm,
                      onPressed: () => Navigator.of(dialogContext)
                          .pop(controller.text.trim()),
                      expand: true,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
    controller.dispose();

    if (token == null || token.isEmpty) {
      return;
    }

    try {
      final message = await ref.read(authProvider.notifier).verifyEmail(token);
      if (!mounted) return;
      AppFeedback.success(context, message);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final user = ref.watch(currentUserProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.editProfile),
        centerTitle: true,
        actions: [
          SparkleButton(
            label: l10n.editProfileSave,
            variant: ButtonVariant.ghost,
            onPressed: _isLoading
                ? null
                : () {
                    unawaited(_saveProfile());
                  },
            loading: _isLoading,
          ),
        ],
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.spacing24),
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing16),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        DS.primaryBase.withValues(alpha: 0.10),
                        DS.surfaceSecondary,
                      ],
                    ),
                    borderRadius: DS.borderRadius16,
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: [
                          _buildMetaChip(
                            icon: Icons.auto_awesome_outlined,
                            label: '头像与资料',
                          ),
                          _buildMetaChip(
                            icon: Icons.verified_user_outlined,
                            label: '安全同步',
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing10),
                      Text(
                        '把头像、昵称和邮箱整理成一致的个人形象，同时保留安全验证与账号信息的清晰层次。',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing20),
                // Avatar Section
                Center(
                  child: GestureDetector(
                    onTap: _isLoading ? null : _pickAndUploadAvatar,
                    child: Stack(
                      children: [
                        SparkleAvatar(
                          radius: 50,
                          backgroundColor: isDark
                              ? DS.brandPrimary.shade800
                              : DS.brandPrimary.shade200,
                          url: user?.avatarStatus == AvatarStatus.pending
                              ? (user?.pendingAvatarUrl ?? user?.avatarUrl)
                              : user?.avatarUrl,
                          fallbackText: user?.nickname ?? user?.username ?? 'U',
                          status: user?.avatarStatus ?? AvatarStatus.approved,
                        ),
                        Positioned(
                          bottom: 0,
                          right: 0,
                          child: Container(
                            padding: const EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              color: DS.primaryBase,
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: isDark
                                    ? DS.brandPrimary.shade900
                                    : DS.brandPrimary,
                                width: 2,
                              ),
                            ),
                            child: Icon(
                              Icons.camera_alt_rounded,
                              size: 16,
                              color: DS.brandPrimaryConst,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                if (user?.avatarStatus == AvatarStatus.pending) ...[
                  const SizedBox(height: DS.md),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing12,
                      vertical: DS.spacing6,
                    ),
                    decoration: BoxDecoration(
                      color: DS.warning.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(20),
                      border:
                          Border.all(color: DS.warning.withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.hourglass_empty_rounded,
                          size: 14,
                          color: DS.warning,
                        ),
                        const SizedBox(width: DS.spacing6),
                        Text(
                          l10n.editProfileNewAvatarPending,
                          style: TextStyle(
                            fontSize: 12,
                            color: DS.warning,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: DS.sm),
                SparkleButton(
                  label: l10n.editProfileChangeAvatar,
                  variant: ButtonVariant.ghost,
                  onPressed: _isLoading
                      ? null
                      : () {
                          unawaited(_pickAndUploadAvatar());
                        },
                ),
                const SizedBox(height: DS.spacing24),

                // Form Fields
                _buildInputField(
                  label: l10n.editProfileNicknameLabel,
                  controller: _nicknameController,
                  hint: l10n.editProfileNicknameHint,
                  icon: Icons.person_outline_rounded,
                ),
                const SizedBox(height: DS.spacing16),
                _buildInputField(
                  label: l10n.editProfileEmailLabel,
                  controller: _emailController,
                  hint: l10n.editProfileEmailHint,
                  icon: Icons.email_outlined,
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: DS.spacing16),
                _buildReadOnlyField(
                  label: l10n.editProfileUsernameLabel,
                  value: user?.username ?? '',
                  icon: Icons.badge_outlined,
                  helperText: l10n.editProfileUsernameReadonly,
                ),
                const SizedBox(height: DS.spacing24),

                // Security Section
                _buildSectionHeader(isDark, l10n.editProfileAccountSecurity),
                const SizedBox(height: DS.spacing12),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.panel,
                  padding: EdgeInsets.zero,
                  child: Column(
                    children: [
                      ListTile(
                        leading: Icon(
                          Icons.lock_reset_rounded,
                          color: DS.primaryBase,
                        ),
                        title: Text(
                          _isSocialAccount
                              ? l10n.editProfileSetPassword
                              : l10n.editProfileResetPassword,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        subtitle: _isSocialAccount
                            ? Text(l10n.editProfileSetPasswordHint)
                            : null,
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () {
                          unawaited(context.push(UserRoutes.passwordReset));
                        },
                      ),
                      const Divider(height: 1),
                      ListTile(
                        isThreeLine: !(user?.emailVerified ?? false),
                        leading: Icon(
                          user?.emailVerified ?? false
                              ? Icons.verified_rounded
                              : Icons.mark_email_unread_outlined,
                          color: (user?.emailVerified ?? false)
                              ? DS.success
                              : DS.warning,
                        ),
                        title: Text(
                          (user?.emailVerified ?? false)
                              ? l10n.editProfileEmailVerified
                              : l10n.editProfileEmailUnverified,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        subtitle: Text(
                          (user?.emailVerified ?? false)
                              ? l10n.editProfileEmailVerifiedDesc
                              : l10n.editProfileEmailUnverifiedDesc,
                        ),
                        trailing: (user?.emailVerified ?? false)
                            ? null
                            : const Icon(Icons.mark_email_read_outlined),
                      ),
                      if (!(user?.emailVerified ?? false))
                        Padding(
                          padding: const EdgeInsets.fromLTRB(
                            DS.spacing16,
                            0,
                            DS.spacing16,
                            DS.spacing12,
                          ),
                          child: Align(
                            alignment: Alignment.centerRight,
                            child: Wrap(
                              alignment: WrapAlignment.end,
                              spacing: DS.spacing8,
                              children: [
                                TextButton(
                                  onPressed:
                                      _isLoading ? null : _verifyEmailWithCode,
                                  child: Text(l10n.editProfileEnterCode),
                                ),
                                TextButton(
                                  onPressed: _isLoading
                                      ? null
                                      : _sendVerificationEmail,
                                  child: Text(l10n.editProfileSendEmail),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),

                const SizedBox(height: DS.spacing24),

                // Account Info Section
                _buildSectionHeader(isDark, l10n.editProfileAccountInfo),
                const SizedBox(height: DS.spacing12),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.panel,
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInfoRow(
                        l10n.editProfileFlameLevel,
                        'Lv.${user?.flameLevel ?? 1}',
                      ),
                      _buildInfoRow(
                        l10n.editProfileFlameBrightness,
                        '${((user?.flameBrightness ?? 0.5) * 100).toInt()}%',
                      ),
                      _buildInfoRow(
                        l10n.editProfileAccountType,
                        user?.id.startsWith('guest') ?? false
                            ? l10n.editProfileGuestAccount
                            : l10n.editProfileFullAccount,
                      ),
                      _buildInfoRow(
                        l10n.editProfileRegistrationMethod,
                        switch (user?.registrationSource) {
                          'google' => l10n.google,
                          'apple' => l10n.apple,
                          'wechat' => l10n.wechat,
                          'guest' => l10n.editProfileGuestAccount,
                          _ => l10n.email,
                        },
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMetaChip({
    required IconData icon,
    required String label,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.textSecondary,
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
      );

  Widget _buildSectionHeader(bool isDark, String title) => Align(
        alignment: Alignment.centerLeft,
        child: Text(
          title,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: isDark ? DS.brandPrimary70 : DS.brandPrimary.shade700,
          ),
        ),
      );

  Widget _buildInputField({
    required String label,
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    bool enabled = true,
    String? helperText,
    TextInputType? keyboardType,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: isDark ? DS.brandPrimary70 : DS.brandPrimary.shade700,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          enabled: enabled,
          keyboardType: keyboardType,
          decoration: InputDecoration(
            hintText: hint,
            prefixIcon: Icon(icon, size: 20),
            filled: true,
            fillColor: enabled
                ? DS.surfaceRoleColor(SparkleSurfaceRole.panel)
                : DS.surfaceRoleColor(SparkleSurfaceRole.elevated),
            border: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: DS.borderSubtle),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: DS.borderSubtle),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: DS.primaryBase, width: 2),
            ),
            disabledBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: DS.borderSubtle),
            ),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.md),
          ),
        ),
        if (helperText != null) ...[
          const SizedBox(height: DS.xs),
          Text(
            helperText,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? DS.brandPrimary38 : DS.brandPrimary.shade500,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildReadOnlyField({
    required String label,
    required String value,
    required IconData icon,
    String? helperText,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: isDark ? DS.brandPrimary70 : DS.brandPrimary.shade700,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.md),
          decoration: BoxDecoration(
            color: DS.surfaceRoleColor(SparkleSurfaceRole.elevated),
            borderRadius: DS.borderRadius12,
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Row(
            children: [
              Icon(
                icon,
                size: 20,
                color: isDark ? DS.brandPrimary38 : DS.brandPrimary.shade500,
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Text(
                  value,
                  style: TextStyle(
                    fontSize: 16,
                    color:
                        isDark ? DS.brandPrimary54 : DS.brandPrimary.shade600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
        if (helperText != null) ...[
          const SizedBox(height: DS.xs),
          Text(
            helperText,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? DS.brandPrimary38 : DS.brandPrimary.shade500,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildInfoRow(String label, String value) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 14,
              color: isDark ? DS.brandPrimary54 : DS.brandPrimary.shade600,
            ),
          ),
          Flexible(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: isDark ? DS.brandPrimary : DS.neutral900,
              ),
              textAlign: TextAlign.end,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _AvatarSourceTile extends StatelessWidget {
  const _AvatarSourceTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius16,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: DS.borderRadius16,
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(DS.spacing10),
                decoration: BoxDecoration(
                  color: DS.primaryBase.withValues(alpha: 0.1),
                  borderRadius: DS.borderRadius12,
                ),
                child: Icon(icon, color: DS.primaryBase, size: 20),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.4,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Icon(
                Icons.arrow_forward_ios_rounded,
                size: 14,
                color: DS.textSecondary,
              ),
            ],
          ),
        ),
      );
}
