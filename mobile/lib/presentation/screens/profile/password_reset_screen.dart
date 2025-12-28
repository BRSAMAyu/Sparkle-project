import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class PasswordResetScreen extends ConsumerStatefulWidget {
  const PasswordResetScreen({super.key});

  @override
  ConsumerState<PasswordResetScreen> createState() => _PasswordResetScreenState();
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
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('密码修改成功'), backgroundColor: DS.success),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('修改失败: $e'), backgroundColor: DS.error),
        );
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
        title: const Text('重置密码'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppDesignTokens.spacing24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '请确保您的新密码包含至少 8 个字符。',
                style: TextStyle(
                  color: isDark ? DS.brandPrimary70 : DS.brandPrimary.shade600,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: AppDesignTokens.spacing24),
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
              const SizedBox(height: AppDesignTokens.spacing16),
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
              const SizedBox(height: AppDesignTokens.spacing16),
              _buildPasswordField(
                label: '确认新密码',
                controller: _confirmPasswordController,
                obscureText: _obscureConfirm,
                onToggle: () => setState(() => _obscureConfirm = !_obscureConfirm),
                validator: (value) {
                  if (value != _newPasswordController.text) return '两次输入的密码不一致';
                  return null;
                },
              ),
              const SizedBox(height: AppDesignTokens.spacing32),
              ElevatedButton(
                onPressed: _isLoading ? null : _handleReset,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppDesignTokens.primaryBase,
                  foregroundColor: DS.brandPrimary,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: AppDesignTokens.borderRadius12,
                  ),
                  elevation: 0,
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(color: DS.brandPrimary, strokeWidth: 2),
                      )
                    : const Text('更新密码', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
              ),
            ],
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
            suffixIcon: IconButton(
              icon: Icon(
                obscureText ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                size: 20,
              ),
              onPressed: onToggle,
            ),
            filled: true,
            fillColor: isDark ? DS.brandPrimary.shade900 : DS.brandPrimary.shade50,
            border: OutlineInputBorder(
              borderRadius: AppDesignTokens.borderRadius12,
              borderSide: BorderSide(color: isDark ? DS.brandPrimary.shade700 : DS.brandPrimary.shade300),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: AppDesignTokens.borderRadius12,
              borderSide: BorderSide(color: isDark ? DS.brandPrimary.shade700 : DS.brandPrimary.shade300),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: AppDesignTokens.borderRadius12,
              borderSide: const BorderSide(color: AppDesignTokens.primaryBase, width: 2),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
        ),
      ],
    );
  }
}
