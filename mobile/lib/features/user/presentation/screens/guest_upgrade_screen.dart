import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/social_auth_service.dart';
import 'package:sparkle/features/auth/auth.dart';

class GuestUpgradeScreen extends ConsumerStatefulWidget {
  const GuestUpgradeScreen({super.key});

  @override
  ConsumerState<GuestUpgradeScreen> createState() => _GuestUpgradeScreenState();
}

class _GuestUpgradeScreenState extends ConsumerState<GuestUpgradeScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _acceptedTos = false;
  bool _acceptedPrivacy = false;
  bool _isLoading = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _upgradeWithEmail() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_acceptedTos || !_acceptedPrivacy) {
      AppFeedback.info(
          context, context.l10n.guestUpgradeAcceptPoliciesRequired,);
      return;
    }

    final agreedLocale = Localizations.localeOf(context).toLanguageTag();
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    setState(() => _isLoading = true);
    try {
      await ref.read(authProvider.notifier).upgradeGuest(
            username: _usernameController.text.trim(),
            email: _emailController.text.trim(),
            password: _passwordController.text.trim(),
            acceptedTos: _acceptedTos,
            acceptedPrivacy: _acceptedPrivacy,
            agreedLocale: agreedLocale,
          );
      if (!mounted) return;
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      AppFeedback.success(context, context.l10n.guestUpgradeSuccess);
      context.go('/profile');
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _upgradeWithSocial(String provider) async {
    if (!_acceptedTos || !_acceptedPrivacy) {
      AppFeedback.info(
          context, context.l10n.guestUpgradeAcceptPoliciesRequired,);
      return;
    }

    final agreedLocale = Localizations.localeOf(context).toLanguageTag();
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
    setState(() => _isLoading = true);
    try {
      final SocialAuthResult? result;
      switch (provider) {
        case 'google':
          result = await SocialAuthService().signInWithGoogle();
        case 'apple':
          result = await SocialAuthService().signInWithApple();
        case 'wechat':
          result = await SocialAuthService().signInWithWeChat();
        default:
          result = null;
      }
      if (result == null) return;
      final socialProvider = result.provider;
      final socialToken = result.token;
      final socialOpenId = result.openid;
      await ref.read(authProvider.notifier).upgradeGuestWithSocial(
            provider: socialProvider,
            token: socialToken,
            openid: socialOpenId,
            acceptedTos: _acceptedTos,
            acceptedPrivacy: _acceptedPrivacy,
            agreedLocale: agreedLocale,
          );
      if (!mounted) return;
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      AppFeedback.success(
        context,
        context.l10n.guestUpgradeSocialSuccess,
      );
      context.go('/profile');
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.guestUpgradeTitle),
        centerTitle: true,
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.spacing24),
          children: [
            SparkleStaggerItem(
              index: 0,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.panel,
                child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: [
                      _buildMetaChip(
                        context,
                        icon: Icons.upgrade_rounded,
                        label: '升级完整账号',
                      ),
                      _buildMetaChip(
                        context,
                        icon: Icons.verified_user_outlined,
                        label: '保留当前数据',
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing12),
                  Text(
                    l10n.guestUpgradeIntro,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                ],
              ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            SparkleStaggerItem(
              index: 1,
              child: GraphiteCardSurface(
                child: Form(
                key: _formKey,
                child: Column(
                  children: [
                    TextFormField(
                      controller: _usernameController,
                      decoration: InputDecoration(
                        labelText: l10n.username,
                        filled: true,
                        fillColor: DS.surfaceSecondary,
                        border: const OutlineInputBorder(
                          borderRadius: DS.borderRadius12,
                        ),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().length < 3) {
                          return l10n.guestUpgradeUsernameMinLength;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextFormField(
                      controller: _emailController,
                      decoration: InputDecoration(
                        labelText: l10n.email,
                        filled: true,
                        fillColor: DS.surfaceSecondary,
                        border: const OutlineInputBorder(
                          borderRadius: DS.borderRadius12,
                        ),
                      ),
                      validator: (value) {
                        if (value == null ||
                            !RegExp(r'^[^@]+@[^@]+\.[^@]+')
                                .hasMatch(value.trim())) {
                          return l10n.invalidEmail;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: true,
                      decoration: InputDecoration(
                        labelText: l10n.password,
                        filled: true,
                        fillColor: DS.surfaceSecondary,
                        border: const OutlineInputBorder(
                          borderRadius: DS.borderRadius12,
                        ),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().length < 8) {
                          return l10n.guestUpgradePasswordMinLength;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextFormField(
                      controller: _confirmPasswordController,
                      obscureText: true,
                      decoration: InputDecoration(
                        labelText: l10n.confirmPassword,
                        filled: true,
                        fillColor: DS.surfaceSecondary,
                        border: const OutlineInputBorder(
                          borderRadius: DS.borderRadius12,
                        ),
                      ),
                      validator: (value) {
                        if (value != _passwordController.text) {
                          return l10n.passwordsDoNotMatch;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _acceptedTos,
                      onChanged: (value) {
                        unawaited(
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          ),
                        );
                        setState(() => _acceptedTos = value ?? false);
                      },
                      title: Text(l10n.guestUpgradeAgreeTerms),
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () => context.push('/legal/terms'),
                        child: Text(l10n.guestUpgradeViewTerms),
                      ),
                    ),
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _acceptedPrivacy,
                      onChanged: (value) {
                        unawaited(
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          ),
                        );
                        setState(() => _acceptedPrivacy = value ?? false);
                      },
                      title: Text(l10n.guestUpgradeAgreePrivacy),
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () => context.push('/legal/privacy'),
                        child: Text(l10n.guestUpgradeViewPrivacy),
                      ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    SparkleButton(
                      label: l10n.guestUpgradeWithEmail,
                      expand: true,
                      loading: _isLoading,
                      onPressed: _isLoading
                          ? null
                          : () {
                              unawaited(_upgradeWithEmail());
                            },
                    ),
                  ],
                ),
              ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.guestUpgradeSocialSectionTitle,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    '你也可以直接绑定社交账号，减少后续重复登录和验证成本。',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.4,
                        ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  SparkleButton(
                    label: l10n.guestUpgradeWithGoogle,
                    variant: ButtonVariant.outline,
                    expand: true,
                    loading: _isLoading,
                    onPressed: _isLoading
                        ? null
                        : () {
                            unawaited(_upgradeWithSocial('google'));
                          },
                  ),
                  const SizedBox(height: DS.spacing12),
                  SparkleButton(
                    label: l10n.guestUpgradeWithApple,
                    variant: ButtonVariant.outline,
                    expand: true,
                    loading: _isLoading,
                    onPressed: _isLoading
                        ? null
                        : () {
                            unawaited(_upgradeWithSocial('apple'));
                          },
                  ),
                  if (SocialAuthService().isWeChatAvailable) ...[
                    const SizedBox(height: DS.spacing12),
                    SparkleButton(
                      label: l10n.guestUpgradeWithWeChat,
                      variant: ButtonVariant.outline,
                      expand: true,
                      loading: _isLoading,
                      onPressed: _isLoading
                          ? null
                          : () {
                              unawaited(_upgradeWithSocial('wechat'));
                            },
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetaChip(
    BuildContext context, {
    required IconData icon,
    required String label,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
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
}
