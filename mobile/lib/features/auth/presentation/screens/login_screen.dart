import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/social_auth_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isPasswordVisible = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      unawaited(
        ref.read(authProvider.notifier).login(
              _usernameController.text.trim(),
              _passwordController.text.trim(),
            ),
      );
    }
  }

  Future<void> _handleSocialLogin(
    Future<SocialAuthResult?> Function() loginMethod,
  ) async {
    try {
      final result = await loginMethod();
      if (result != null) {
        if (!mounted) return;
        unawaited(
          ref.read(authProvider.notifier).socialLogin(
                provider: result.provider,
                token: result.token,
                openid: result.openid,
                email: result.email,
                nickname: result.nickname,
                avatarUrl: result.avatarUrl,
              ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, 'Login Failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final l10n = AppLocalizations.of(context);

    if (l10n == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    // Listen for errors and show a SnackBar
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.error != null && (previous?.error != next.error)) {
        AppFeedback.error(
          context,
          ErrorMessages.getLocalizedMessage(
            l10n,
            'AUTH_ERROR', // Default error code since AuthState doesn't have errorCode
            next.error,
          ),
        );
      }
      // Successful login is handled by router redirect
    });

    return SparklePageScaffold(
      role: SparklePageRole.auth,
      safeArea: false,
      child: SafeArea(
        child: ContentConstraint(
          child: LayoutBuilder(
            builder: (context, constraints) => SingleChildScrollView(
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: const EdgeInsets.all(DS.xl),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: IntrinsicHeight(
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(height: DS.spacing24),
                        Icon(
                          Icons.whatshot_outlined,
                          size: 60,
                          color: DS.brandPrimaryConst,
                        ),
                        const SizedBox(height: DS.lg),
                        Text(
                          l10n.appTitle,
                          textAlign: TextAlign.center,
                          style: Theme.of(context)
                              .textTheme
                              .headlineSmall
                              ?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Theme.of(context).colorScheme.secondary,
                              ),
                        ),
                        const SizedBox(height: DS.sm),
                        Text(
                          l10n.welcomeSubtitle,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: DS.xxxl),
                        TextFormField(
                          controller: _usernameController,
                          decoration: InputDecoration(
                            labelText: l10n.username,
                            border: const OutlineInputBorder(),
                            prefixIcon: const Icon(Icons.person_outline),
                          ),
                          validator: (value) =>
                              value!.isEmpty ? l10n.pleaseEnterUsername : null,
                        ),
                        const SizedBox(height: DS.lg),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: !_isPasswordVisible,
                          decoration: InputDecoration(
                            labelText: l10n.password,
                            border: const OutlineInputBorder(),
                            prefixIcon: const Icon(Icons.lock_outline),
                            suffixIcon: SparkleIconButton(
                              icon: Icon(
                                _isPasswordVisible
                                    ? Icons.visibility_off
                                    : Icons.visibility,
                              ),
                              onPressed: () => setState(
                                () => _isPasswordVisible = !_isPasswordVisible,
                              ),
                              variant: ButtonVariant.ghost,
                              size: DS.touchTargetMinSize,
                            ),
                          ),
                          validator: (value) =>
                              value!.isEmpty ? l10n.pleaseEnterPassword : null,
                        ),
                        const SizedBox(height: DS.xl),
                        SparkleButton(
                          label: l10n.login,
                          onPressed: authState.isLoading ? null : _submit,
                          variant: ButtonVariant.primary,
                          expand: true,
                          loading: authState.isLoading,
                          disabled: authState.isLoading,
                        ),
                        const Spacer(),
                        Row(
                          children: [
                            const Expanded(child: Divider()),
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing16,
                              ),
                              child: Text(
                                l10n.orText,
                                style: TextStyle(color: DS.brandPrimary),
                              ),
                            ),
                            const Expanded(child: Divider()),
                          ],
                        ),
                        const SizedBox(height: DS.xl),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                          children: [
                            _SocialLoginButton(
                              icon: Icons.g_mobiledata_rounded,
                              label: l10n.google,
                              onTap: () => _handleSocialLogin(
                                SocialAuthService().signInWithGoogle,
                              ),
                            ),
                            _SocialLoginButton(
                              icon: Icons.apple_rounded,
                              label: l10n.apple,
                              onTap: () => _handleSocialLogin(
                                SocialAuthService().signInWithApple,
                              ),
                            ),
                            _SocialLoginButton(
                              icon: Icons.wechat_rounded,
                              label: l10n.wechat,
                              onTap: () => _handleSocialLogin(
                                SocialAuthService().signInWithWeChat,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.lg),
                        SparkleButton.ghost(
                          label: l10n.noAccount,
                          onPressed: () => context.go('/register'),
                        ),
                        const SizedBox(height: DS.sm),
                        SparkleButton(
                          label: l10n.continueAsGuest,
                          onPressed: authState.isLoading
                              ? null
                              : () async {
                                  await ref
                                      .read(authProvider.notifier)
                                      .loginAsGuest();
                                },
                          loading: authState.isLoading,
                          disabled: authState.isLoading,
                          variant: ButtonVariant.ghost,
                          expand: true,
                        ),
                        const SizedBox(height: DS.sm),
                        SparkleButton(
                          label: '演示账号登录',
                          onPressed: authState.isLoading
                              ? null
                              : () async {
                                  await ref
                                      .read(authProvider.notifier)
                                      .loginAsDemoAccount();
                                },
                          loading: authState.isLoading,
                          disabled: authState.isLoading,
                          variant: ButtonVariant.ghost,
                          expand: true,
                        ),
                        const SizedBox(height: DS.spacing12),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SocialLoginButton extends StatelessWidget {
  const _SocialLoginButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: colorScheme.surface,
          border: Border.all(color: colorScheme.outline.withValues(alpha: 0.2)),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.05),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Icon(
          icon,
          size: 32,
          color: colorScheme.onSurface,
        ),
      ),
    );
  }
}
