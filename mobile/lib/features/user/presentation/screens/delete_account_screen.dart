import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/social_auth_service.dart';
import 'package:sparkle/features/auth/auth.dart';

class DeleteAccountScreen extends ConsumerStatefulWidget {
  const DeleteAccountScreen({super.key});

  @override
  ConsumerState<DeleteAccountScreen> createState() =>
      _DeleteAccountScreenState();
}

class _DeleteAccountScreenState extends ConsumerState<DeleteAccountScreen> {
  final _confirmationController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  String? _providerToken;
  String? _provider;

  @override
  void dispose() {
    _confirmationController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  String? get _socialProvider {
    final user = ref.read(currentUserProvider);
    if (user == null) return null;
    final source = user.registrationSource;
    if (source == 'google' || source == 'apple' || source == 'wechat') {
      return source;
    }
    if (user.linkedProviders.isNotEmpty) {
      return user.linkedProviders.first;
    }
    return null;
  }

  bool get _requiresPassword =>
      ref.read(currentUserProvider)?.passwordLoginEnabled ?? false;

  bool get _isGuest =>
      ref.read(currentUserProvider)?.registrationSource == 'guest';

  Future<void> _reauthWithSocial() async {
    final provider = _socialProvider;
    if (provider == null) {
      AppFeedback.info(context, context.l10n.deleteAccountNoSocialProvider);
      return;
    }
    if (provider == 'wechat' && !SocialAuthService().isWeChatAvailable) {
      AppFeedback.info(context, context.l10n.deleteAccountWeChatUnavailable);
      return;
    }

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
      final providerToken = result.token;
      if (!mounted) return;
      setState(() {
        _provider = provider;
        _providerToken = providerToken;
      });
      AppFeedback.success(context, context.l10n.deleteAccountReauthSuccess);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _submit() async {
    if (_confirmationController.text.trim().toUpperCase() != 'DELETE') {
      AppFeedback.info(context, context.l10n.deleteAccountRequireDeleteInput);
      return;
    }
    if (!_isGuest && _requiresPassword && _passwordController.text.isEmpty) {
      AppFeedback.info(context, context.l10n.deleteAccountRequirePassword);
      return;
    }
    if (!_isGuest && !_requiresPassword && (_providerToken?.isEmpty ?? true)) {
      AppFeedback.info(context, context.l10n.deleteAccountRequireReauth);
      return;
    }

    setState(() => _isLoading = true);
    try {
      await ref.read(authProvider.notifier).deleteAccount(
            confirmation: _confirmationController.text.trim(),
            password: _requiresPassword ? _passwordController.text : null,
            provider: !_requiresPassword ? _provider : null,
            providerToken: !_requiresPassword ? _providerToken : null,
          );
      if (!mounted) return;
      AppFeedback.success(context, context.l10n.deleteAccountSuccess);
      context.go('/login');
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
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.settings,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.deleteAccountTitle),
        centerTitle: true,
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.spacing24),
          children: [
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.l10n.deleteAccountChecklistTitle,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  Text(context.l10n.deleteAccountChecklistItem1),
                  Text(context.l10n.deleteAccountChecklistItem2),
                  Text(context.l10n.deleteAccountChecklistItem3),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing16),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.l10n.deleteAccountConfirmInputTitle,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  TextField(
                    controller: _confirmationController,
                    decoration: InputDecoration(
                      hintText: context.l10n.deleteAccountConfirmInputHint,
                      border: const OutlineInputBorder(),
                    ),
                  ),
                  if (_requiresPassword) ...[
                    const SizedBox(height: DS.spacing16),
                    Text(
                      context.l10n.deleteAccountPasswordLabel,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    TextField(
                      controller: _passwordController,
                      obscureText: true,
                      decoration: InputDecoration(
                        hintText: context.l10n.deleteAccountPasswordHint,
                        border: const OutlineInputBorder(),
                      ),
                    ),
                  ] else if (!_isGuest) ...[
                    const SizedBox(height: DS.spacing16),
                    Text(
                      context.l10n.deleteAccountSocialReauthNotice(
                        _socialProvider == 'apple'
                            ? 'Apple'
                            : _socialProvider == 'google'
                                ? 'Google'
                                : context.l10n.deleteAccountSocialProvider,
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    SparkleButton(
                      label: _providerToken == null
                          ? context.l10n.deleteAccountReauthButton
                          : context.l10n.deleteAccountReauthDone,
                      variant: ButtonVariant.outline,
                      expand: true,
                      loading: _isLoading,
                        onPressed: _isLoading
                            ? null
                            : () {
                                unawaited(_reauthWithSocial());
                              },
                      ),
                    ],
                    const SizedBox(height: DS.spacing24),
                    SparkleButton(
                      label: context.l10n.deleteAccountConfirmButton,
                      variant: ButtonVariant.destructive,
                      expand: true,
                      loading: _isLoading,
                      onPressed: _isLoading
                          ? null
                          : () {
                              unawaited(_submit());
                            },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}
