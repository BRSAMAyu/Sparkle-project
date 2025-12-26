import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/screens/profile/password_reset_screen.dart';
import 'package:sparkle/presentation/widgets/profile/avatar_selection_dialog.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';
import 'package:sparkle/data/models/user_model.dart';

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
    _nicknameController = TextEditingController(text: user?.nickname ?? user?.username ?? '');
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
      showDialog(
        context: context,
        builder: (context) => AvatarSelectionDialog(
          currentAvatarUrl: user?.avatarUrl,
          onAvatarSelected: (url) async {
            setState(() => _isLoading = true);
            try {
              await ref.read(authProvider.notifier).updateAvatar(url);
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('头像更新成功'), backgroundColor: Colors.green),
                );
              }
            } catch (e) {
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('更新失败: $e'), backgroundColor: Colors.red),
                );
              }
            } finally {
              if (mounted) setState(() => _isLoading = false);
            }
          },
        ),
      );
      return;
    }

    final imageSource = source == 'camera' ? ImageSource.camera : ImageSource.gallery;
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
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('头像更新成功'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('上传失败: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _saveProfile() async {
    final nickname = _nicknameController.text.trim();
    final email = _emailController.text.trim();

    if (nickname.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('昵称不能为空')),
      );
      return;
    }

    if (email.isNotEmpty && !RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请输入有效的邮箱地址')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      await ref.read(authProvider.notifier).updateProfile({
        'nickname': nickname,
        'email': email,
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('资料更新成功'), backgroundColor: Colors.green),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('更新失败: $e'), backgroundColor: Colors.red),
        );
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

    return Scaffold(
      appBar: AppBar(
        title: const Text('编辑资料'),
        centerTitle: true,
        actions: [
          TextButton(
            onPressed: _isLoading ? null : _saveProfile,
            child: _isLoading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text(
                    '保存',
                    style: TextStyle(
                      color: AppDesignTokens.primaryBase,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDesignTokens.spacing24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Avatar Section
            Center(
              child: GestureDetector(
                onTap: _isLoading ? null : _pickAndUploadAvatar,
                child: Stack(
                  children: [
                    SparkleAvatar(
                      radius: 50,
                      backgroundColor: isDark ? Colors.grey.shade800 : Colors.grey.shade200,
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
                          color: AppDesignTokens.primaryBase,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: isDark ? Colors.grey.shade900 : Colors.white,
                            width: 2,
                          ),
                        ),
                        child: const Icon(
                          Icons.camera_alt_rounded,
                          size: 16,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (user?.avatarStatus == AvatarStatus.pending) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.amber.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.hourglass_empty_rounded, size: 14, color: Colors.amber),
                    SizedBox(width: 6),
                    Text(
                      '新头像正在审核中...',
                      style: TextStyle(fontSize: 12, color: Colors.amber, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 8),
            TextButton(
              onPressed: _isLoading ? null : _pickAndUploadAvatar,
              child: const Text(
                '更换头像',
                style: TextStyle(
                  color: AppDesignTokens.primaryBase,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing24),

            // Form Fields
            _buildInputField(
              label: '昵称',
              controller: _nicknameController,
              hint: '请输入昵称',
              icon: Icons.person_outline_rounded,
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            _buildInputField(
              label: '邮箱',
              controller: _emailController,
              hint: '请输入邮箱',
              icon: Icons.email_outlined,
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            _buildReadOnlyField(
              label: '用户名',
              value: user?.username ?? '',
              icon: Icons.badge_outlined,
              helperText: '用户名不可修改',
            ),
            const SizedBox(height: AppDesignTokens.spacing24),

            // Security Section
            _buildSectionHeader(isDark, '账户安全'),
            const SizedBox(height: AppDesignTokens.spacing12),
            Container(
              decoration: BoxDecoration(
                color: isDark ? Colors.grey.shade900 : Colors.white,
                borderRadius: AppDesignTokens.borderRadius12,
                border: Border.all(
                  color: isDark ? Colors.grey.shade800 : Colors.grey.shade200,
                ),
              ),
              child: ListTile(
                leading: const Icon(Icons.lock_reset_rounded, color: AppDesignTokens.primaryBase),
                title: const Text('重置密码', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const PasswordResetScreen()),
                  );
                },
              ),
            ),
            
            const SizedBox(height: AppDesignTokens.spacing24),

            // Account Info Section
            _buildSectionHeader(isDark, '账户信息'),
            const SizedBox(height: AppDesignTokens.spacing12),
            Container(
              padding: const EdgeInsets.all(AppDesignTokens.spacing16),
              decoration: BoxDecoration(
                color: isDark ? Colors.grey.shade900 : Colors.grey.shade50,
                borderRadius: AppDesignTokens.borderRadius12,
                border: Border.all(
                  color: isDark ? Colors.grey.shade800 : Colors.grey.shade200,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildInfoRow('火焰等级', 'Lv.${user?.flameLevel ?? 1}'),
                  _buildInfoRow('火焰亮度', '${((user?.flameBrightness ?? 0.5) * 100).toInt()}%'),
                  _buildInfoRow('账户类型', user?.id.startsWith('guest') == true ? '游客账户' : '正式账户'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(bool isDark, String title) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        title,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: isDark ? Colors.white70 : Colors.grey.shade700,
        ),
      ),
    );
  }

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
            color: isDark ? Colors.white70 : Colors.grey.shade700,
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
                ? (isDark ? Colors.grey.shade900 : Colors.grey.shade50)
                : (isDark ? Colors.grey.shade800 : Colors.grey.shade100),
            border: OutlineInputBorder(
              borderRadius: AppDesignTokens.borderRadius12,
              borderSide: BorderSide(color: isDark ? Colors.grey.shade700 : Colors.grey.shade300),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: AppDesignTokens.borderRadius12,
              borderSide: BorderSide(color: isDark ? Colors.grey.shade700 : Colors.grey.shade300),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: AppDesignTokens.borderRadius12,
              borderSide: const BorderSide(color: AppDesignTokens.primaryBase, width: 2),
            ),
            disabledBorder: OutlineInputBorder(
              borderRadius: AppDesignTokens.borderRadius12,
              borderSide: BorderSide(color: isDark ? Colors.grey.shade800 : Colors.grey.shade200),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
        ),
        if (helperText != null) ...[
          const SizedBox(height: 4),
          Text(
            helperText,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? Colors.white38 : Colors.grey.shade500,
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
            color: isDark ? Colors.white70 : Colors.grey.shade700,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: isDark ? Colors.grey.shade800 : Colors.grey.shade100,
            borderRadius: AppDesignTokens.borderRadius12,
            border: Border.all(color: isDark ? Colors.grey.shade700 : Colors.grey.shade200),
          ),
          child: Row(
            children: [
              Icon(icon, size: 20, color: isDark ? Colors.white38 : Colors.grey.shade500),
              const SizedBox(width: 12),
              Text(
                value,
                style: TextStyle(
                  fontSize: 16,
                  color: isDark ? Colors.white54 : Colors.grey.shade600,
                ),
              ),
            ],
          ),
        ),
        if (helperText != null) ...[
          const SizedBox(height: 4),
          Text(
            helperText,
            style: TextStyle(
              fontSize: 12,
              color: isDark ? Colors.white38 : Colors.grey.shade500,
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
              color: isDark ? Colors.white54 : Colors.grey.shade600,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: isDark ? Colors.white : AppDesignTokens.neutral900,
            ),
          ),
        ],
      ),
    );
  }
}