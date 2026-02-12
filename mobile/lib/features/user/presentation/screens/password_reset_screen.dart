import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/auth/auth.dart';

class PasswordResetScreen extends ConsumerStatefulWidget {
  const PasswordResetScreen({super.key});

  @override
  ConsumerState<PasswordResetScreen> createState() =>
      _PasswordResetScreenState();
}

class _PasswordResetScreenState extends ConsumerState<PasswordResetScreen> {
  final _formKey = GlobalKey<FormState>();
  final _oldPasswordController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _isLoading = false;
  bool _obscureOld = true;
  bool _obscureNew = true;
  bool _obscureConfirm = true;

  @override
  void dispose() {
    _oldPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _handleReset() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    try {
      await ref.read(authProvider.notifier).changePassword(
            _oldPasswordController.text,
            _newPasswordController.text,
          );
      if (mounted) {
        AppFeedback.success(context, '密码修改成功');
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '修改失败: $e');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          size: DS.touchTargetMinSize,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('重置密码'),
        centerTitle: true,
      ),
      body: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.spacing24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  '请确保您的新密码包含至少 8 个字符。',
                  style: TextStyle(
                    color:
                        isDark ? DS.brandPrimary70 : DS.brandPrimary.shade600,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: DS.spacing24),
                _buildPasswordField(
                  label: '当前密码',
                  controller: _oldPasswordController,
                  obscureText: _obscureOld,
                  onToggle: () => setState(() => _obscureOld = !_obscureOld),
                  validator: (value) {
                    if (value == null || value.isEmpty) return '请输入当前密码';
                    return null;
                  },
                ),
                const SizedBox(height: DS.spacing16),
                _buildPasswordField(
                  label: '新密码',
                  controller: _newPasswordController,
                  obscureText: _obscureNew,
                  onToggle: () => setState(() => _obscureNew = !_obscureNew),
                  validator: (value) {
                    if (value == null || value.isEmpty) return '请输入新密码';
                    if (value.length < 8) return '密码长度至少为 8 位';
                    return null;
                  },
                ),
                const SizedBox(height: DS.spacing16),
                _buildPasswordField(
                  label: '确认新密码',
                  controller: _confirmPasswordController,
                  obscureText: _obscureConfirm,
                  onToggle: () =>
                      setState(() => _obscureConfirm = !_obscureConfirm),
                  validator: (value) {
                    if (value != _newPasswordController.text)
                      return '两次输入的密码不一致';
                    return null;
                  },
                ),
                const SizedBox(height: DS.spacing32),
                SparkleButton(
                  onPressed: _isLoading
                      ? null
                      : () {
                          _handleReset();
                        },
                  label: '更新密码',
                  loading: _isLoading,
                  expand: true,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPasswordField({
    required String label,
    required TextEditingController controller,
    required bool obscureText,
    required VoidCallback onToggle,
    String? Function(String?)? validator,
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
        TextFormField(
          controller: controller,
          obscureText: obscureText,
          validator: validator,
          decoration: InputDecoration(
            prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20),
            suffixIcon: SparkleIconButton(
              variant: ButtonVariant.ghost,
              size: DS.spacing32,
              icon: Icon(
                obscureText
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
                size: 20,
              ),
              onPressed: onToggle,
            ),
            filled: true,
            fillColor:
                isDark ? DS.brandPrimary.shade900 : DS.brandPrimary.shade50,
            border: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(
                color: isDark
                    ? DS.brandPrimary.shade700
                    : DS.brandPrimary.shade300,
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(
                color: isDark
                    ? DS.brandPrimary.shade700
                    : DS.brandPrimary.shade300,
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: DS.borderRadius12,
              borderSide: BorderSide(color: DS.primaryBase, width: 2),
            ),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.md),
          ),
        ),
      ],
    );
  }
}
