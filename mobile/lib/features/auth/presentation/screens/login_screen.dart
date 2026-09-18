import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
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
  // Brand colors — single source: the SparkleColors palette (batch2
  // convergence, read via the unified context.colors entry from batch3).
  SparkleColors get _brandColors => context.colors;
  Color get _brandPrimary => _brandColors.brandPrimary;
  Color get _brandPrimaryDeep => _brandColors.brandPrimaryDeep;
  Color get _brandSecondary => _brandColors.brandSecondary;
  Color get _brandSecondaryDeep => _brandColors.brandSecondaryDeep;

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
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
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
      AppFeedback.error(context, UserFacingError.from(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final l10n = AppLocalizations.of(context);

    if (l10n == null) {
      return const Scaffold(
        body: Center(child: LoadingIndicator()),
      );
    }

    // Listen for errors and show a SnackBar
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.error != null && (previous?.error != next.error)) {
        final failure = next.failure;
        AppFeedback.error(
          context,
          failure?.userMessage ??
              ErrorMessages.getLocalizedMessage(
                l10n,
                next.errorCode ?? 'AUTH_ERROR',
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
          child: SingleChildScrollView(
            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
            padding: const EdgeInsets.all(DS.xl),
            // Form-factor constraint (batch3 W-7): keep the login form a
            // centered column on desktop/web instead of a 1200px stretch.
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: DS.contentMaxWidthForm,
                ),
                child: Form(
                  key: _formKey,
                  child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: DS.spacing24),
                  _BrandMark(
                    primary: _brandPrimary,
                    primaryDeep: _brandPrimaryDeep,
                  ),
                  const SizedBox(height: DS.lg),
                  _BrandWordmark(
                    title: l10n.appTitle,
                    secondary: _brandSecondary,
                    secondaryDeep: _brandSecondaryDeep,
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
                    autofillHints: const [AutofillHints.username],
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
                    autofillHints: const [AutofillHints.password],
                    obscureText: !_isPasswordVisible,
                    obscuringCharacter: '●',
                    style: const TextStyle(letterSpacing: 0),
                    decoration: InputDecoration(
                      labelText: l10n.password,
                      border: const OutlineInputBorder(),
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _isPasswordVisible
                              ? Icons.visibility
                              : Icons.visibility_off,
                        ),
                        onPressed: () {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            ),
                          );
                          setState(
                            () => _isPasswordVisible = !_isPasswordVisible,
                          );
                        },
                      ),
                    ),
                    validator: (value) =>
                        value!.isEmpty ? l10n.pleaseEnterPassword : null,
                  ),
                  const SizedBox(height: DS.sm),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: authState.isLoading
                          ? null
                          : () => context.push('/forgot-password'),
                      child: Text(l10n.authForgotPassword),
                    ),
                  ),
                  const SizedBox(height: DS.xl),
                  SparkleButton(
                    label: l10n.login,
                    onPressed: authState.isLoading ? null : _submit,
                    expand: true,
                    loading: authState.isLoading,
                    disabled: authState.isLoading,
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
                  const SizedBox(height: DS.xxxl),
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
                  Center(
                    child: SparkleButton.ghost(
                      label: l10n.noAccount,
                      onPressed: () => context.push('/register'),
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  Wrap(
                    alignment: WrapAlignment.center,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: DS.spacing4,
                    children: [
                      Text(
                        l10n.authLoginAgreement,
                        style: context.typo.bodySmall,
                      ),
                      TextButton(
                        onPressed: () => context.push('/legal/terms'),
                        child: Text(l10n.authUserAgreement),
                      ),
                      Text(
                        l10n.authAnd,
                        style: context.typo.bodySmall,
                      ),
                      TextButton(
                        onPressed: () => context.push('/legal/privacy'),
                        child: Text(l10n.authPrivacyPolicy),
                      ),
                    ],
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
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark({
    required this.primary,
    required this.primaryDeep,
  });

  final Color primary;
  final Color primaryDeep;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 96,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Container(
              width: 92,
              height: 92,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    primary.withValues(alpha: 0.22),
                    primary.withValues(alpha: 0.08),
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.58, 1.0],
                ),
              ),
            ),
            Container(
              width: 74,
              height: 74,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [primary, primaryDeep],
                ),
                boxShadow: [
                  BoxShadow(
                    color: primary.withValues(alpha: 0.28),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.whatshot_rounded,
              size: 34,
              color: Colors.white,
            ),
          ],
        ),
      );
}

class _BrandWordmark extends StatelessWidget {
  const _BrandWordmark({
    required this.title,
    required this.secondary,
    required this.secondaryDeep,
  });

  final String title;
  final Color secondary;
  final Color secondaryDeep;

  @override
  Widget build(BuildContext context) {
    // SparkleTypography role (batch3 W-7): Material headlineSmall is not
    // mapped by _buildTextTheme, so the wordmark previously fell back to
    // the M3 default scale instead of the design system's.
    final baseStyle = context.typo.headingMedium.copyWith(
          fontWeight: FontWeight.w800,
          letterSpacing: 0.2,
          height: 1.05,
          color: secondaryDeep,
        );

    return ShaderMask(
      shaderCallback: (bounds) => LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [secondary, secondaryDeep],
      ).createShader(bounds),
      blendMode: BlendMode.srcIn,
      child: Text(
        title,
        textAlign: TextAlign.center,
        style: baseStyle.copyWith(
          shadows: [
            Shadow(
              color: secondary.withValues(alpha: 0.16),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
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
