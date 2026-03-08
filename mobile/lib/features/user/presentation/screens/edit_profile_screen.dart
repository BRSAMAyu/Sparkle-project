import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/user/presentation/widgets/avatar_selection_dialog.dart';
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
    final user = ref.read(currentUserProvider);
    final source = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.face_retouching_natural_rounded),
              title: const Text('从系统推荐中选择'),
              onTap: () => Navigator.pop(context, 'preset'),
            ),
            ListTile(
              leading: const Icon(Icons.camera_alt_rounded),
              title: const Text('拍照'),
              onTap: () => Navigator.pop(context, 'camera'),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_rounded),
              title: const Text('从相册选择'),
              onTap: () => Navigator.pop(context, 'gallery'),
            ),
          ],
        ),
      ),
    );

    if (source == null) return;

    if (source == 'preset') {
      if (!mounted) return;
      final parentContext = context;
      final selectedUrl = await showDialog<String>(
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
          AppFeedback.success(parentContext, '头像更新成功');
        }
      } catch (e) {
        if (parentContext.mounted) {
          AppFeedback.error(parentContext, '更新失败: $e');
        }
      } finally {
        if (mounted) setState(() => _isLoading = false);
      }
      return;
    }

    final imageSource =
        source == 'camera' ? ImageSource.camera : ImageSource.gallery;
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
        AppFeedback.success(context, '头像更新成功');
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '上传失败: $e');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _saveProfile() async {
    final nickname = _nicknameController.text.trim();
    final email = _emailController.text.trim();

    if (nickname.isEmpty) {
      AppFeedback.info(context, '昵称不能为空');
      return;
    }

    if (email.isNotEmpty &&
        !RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email)) {
      AppFeedback.info(context, '请输入有效的邮箱地址');
      return;
    }

    setState(() => _isLoading = true);

    try {
      await ref.read(authProvider.notifier).updateProfile({
        'nickname': nickname,
        'email': email,
      });

      if (mounted) {
        AppFeedback.success(context, '资料更新成功');
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '更新失败: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          size: DS.touchTargetMinSize,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('编辑资料'),
        centerTitle: true,
        actions: [
          SparkleButton(
            label: '保存',
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
                          '新头像正在审核中...',
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
                  label: '更换头像',
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
                  label: '昵称',
                  controller: _nicknameController,
                  hint: '请输入昵称',
                  icon: Icons.person_outline_rounded,
                ),
                const SizedBox(height: DS.spacing16),
                _buildInputField(
                  label: '邮箱',
                  controller: _emailController,
                  hint: '请输入邮箱',
                  icon: Icons.email_outlined,
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: DS.spacing16),
                _buildReadOnlyField(
                  label: '用户名',
                  value: user?.username ?? '',
                  icon: Icons.badge_outlined,
                  helperText: '用户名不可修改',
                ),
                const SizedBox(height: DS.spacing24),

                // Security Section
                _buildSectionHeader(isDark, '账户安全'),
                const SizedBox(height: DS.spacing12),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.panel,
                  padding: EdgeInsets.zero,
                  child: ListTile(
                    leading:
                        Icon(Icons.lock_reset_rounded, color: DS.primaryBase),
                    title: const Text(
                      '重置密码',
                      style:
                          TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
                    ),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () {
                      context.push(UserRoutes.passwordReset);
                    },
                  ),
                ),

                const SizedBox(height: DS.spacing24),

                // Account Info Section
                _buildSectionHeader(isDark, '账户信息'),
                const SizedBox(height: DS.spacing12),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.panel,
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInfoRow('火焰等级', 'Lv.${user?.flameLevel ?? 1}'),
                      _buildInfoRow(
                        '火焰亮度',
                        '${((user?.flameBrightness ?? 0.5) * 100).toInt()}%',
                      ),
                      _buildInfoRow(
                        '账户类型',
                        user?.id.startsWith('guest') ?? false ? '游客账户' : '正式账户',
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
              Text(
                value,
                style: TextStyle(
                  fontSize: 16,
                  color: isDark ? DS.brandPrimary54 : DS.brandPrimary.shade600,
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
          Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: isDark ? DS.brandPrimary : DS.neutral900,
            ),
          ),
        ],
      ),
    );
  }
}
