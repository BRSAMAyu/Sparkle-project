import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/user_routes.dart';

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

    final l10n = context.l10n;
    setState(() => _isLoading = true);
    try {
      await ref.read(authProvider.notifier).changePassword(
            _oldPasswordController.text,
            _newPasswordController.text,
          );
      if (mounted) {
        AppFeedback.success(context, l10n.passwordResetSuccess);
        UserRoutes.popOrGoProfile(context);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, l10n.passwordResetFailed(e.toString()));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
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
        title: Text(l10n.passwordReset),
        centerTitle: true,
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.spacing24),
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.passwordResetHint,
                    style: TextStyle(
                      color:
                          isDark ? DS.brandPrimary70 : DS.brandPrimary.shade600,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: DS.spacing24),
                  _buildPasswordField(
                    label: l10n.passwordResetCurrentLabel,
                    controller: _oldPasswordController,
                    obscureText: _obscureOld,
                    onToggle: () => setState(() => _obscureOld = !_obscureOld),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return l10n.passwordResetCurrentRequired;
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: DS.spacing16),
                  _buildPasswordField(
                    label: l10n.passwordResetNewLabel,
                    controller: _newPasswordController,
                    obscureText: _obscureNew,
                    onToggle: () => setState(() => _obscureNew = !_obscureNew),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return l10n.passwordResetNewRequired;
                      }
                      if (value.length < 8) {
                        return l10n.passwordResetNewMinLength;
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: DS.spacing16),
                  _buildPasswordField(
                    label: l10n.passwordResetConfirmLabel,
                    controller: _confirmPasswordController,
                    obscureText: _obscureConfirm,
                    onToggle: () =>
                        setState(() => _obscureConfirm = !_obscureConfirm),
                    validator: (value) {
                      if (value != _newPasswordController.text) {
                        return l10n.passwordResetConfirmMismatch;
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: DS.spacing32),
                  SparkleButton(
                    onPressed: _isLoading ? null : _handleReset,
                    label: l10n.passwordResetButton,
                    loading: _isLoading,
                    expand: true,
                  ),
                ],
              ),
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
            fillColor: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
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
            contentPadding:
                const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.md),
          ),
        ),
      ],
    );
  }
}
