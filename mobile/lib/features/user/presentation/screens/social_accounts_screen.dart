import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/social_auth_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/models/account_security_model.dart';

class SocialAccountsScreen extends ConsumerStatefulWidget {
  const SocialAccountsScreen({super.key});

  @override
  ConsumerState<SocialAccountsScreen> createState() =>
      _SocialAccountsScreenState();
}

class _SocialAccountsScreenState extends ConsumerState<SocialAccountsScreen> {
  List<SocialAccountStatusModel> _accounts = const [];
  bool _isLoading = true;
  String? _busyProvider;

  @override
  void initState() {
    super.initState();
    unawaited(_loadAccounts());
  }

  Future<void> _loadAccounts() async {
    setState(() => _isLoading = true);
    try {
      final accounts =
          await ref.read(authProvider.notifier).getSocialAccounts();
      if (!mounted) return;
      setState(() => _accounts = accounts);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _link(String provider) async {
    if (provider == 'wechat' && !SocialAuthService().isWeChatAvailable) {
      AppFeedback.info(context, context.l10n.socialAccountsWeChatUnavailable);
      return;
    }

    setState(() => _busyProvider = provider);
    try {
      final result = await _signIn(provider);
      if (result == null) return;
      final socialProvider = result.provider;
      final socialToken = result.token;
      final socialOpenId = result.openid;
      final message = await ref.read(authProvider.notifier).linkSocial(
            provider: socialProvider,
            token: socialToken,
            openid: socialOpenId,
          );
      if (!mounted) return;
      AppFeedback.success(context, message);
      await _loadAccounts();
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _busyProvider = null);
      }
    }
  }

  Future<void> _unlink(String provider) async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: Text(
              context.l10n.socialAccountsUnlinkTitle(
                _providerLabel(provider),
              ),
            ),
            content: Text(context.l10n.socialAccountsUnlinkMessage),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: Text(context.l10n.cancel),
              ),
              FilledButton(
                onPressed: () => Navigator.of(dialogContext).pop(true),
                child: Text(context.l10n.socialAccountsUnlinkConfirm),
              ),
            ],
          ),
        ) ??
        false;

    if (!confirmed) return;

    setState(() => _busyProvider = provider);
    try {
      final message =
          await ref.read(authProvider.notifier).unlinkSocial(provider);
      if (!mounted) return;
      AppFeedback.success(context, message);
      await _loadAccounts();
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _busyProvider = null);
      }
    }
  }

  Future<SocialAuthResult?> _signIn(String provider) {
    switch (provider) {
      case 'google':
        return SocialAuthService().signInWithGoogle();
      case 'apple':
        return SocialAuthService().signInWithApple();
      case 'wechat':
        return SocialAuthService().signInWithWeChat();
      default:
        return Future<SocialAuthResult?>.value();
    }
  }

  String _providerLabel(String provider) {
    final l10n = context.l10n;
    switch (provider) {
      case 'google':
        return l10n.google;
      case 'apple':
        return l10n.apple;
      case 'wechat':
        return l10n.wechat;
      default:
        return provider;
    }
  }

  IconData _providerIcon(String provider) {
    switch (provider) {
      case 'google':
        return Icons.g_mobiledata_rounded;
      case 'apple':
        return Icons.apple_rounded;
      case 'wechat':
        return Icons.wechat_rounded;
      default:
        return Icons.link_rounded;
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
          title: Text(context.l10n.socialAccountsTitle),
          centerTitle: true,
        ),
        child: ContentConstraint(
          child: RefreshIndicator(
            onRefresh: _loadAccounts,
            child: ListView(
              padding: const EdgeInsets.all(DS.spacing24),
              children: [
                GraphiteCardSurface(
                  child: Text(
                    context.l10n.socialAccountsIntro,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: DS.spacing40),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else
                  ..._accounts.map(
                    (account) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing12),
                      child: GraphiteCardSurface(
                        surfaceRole: SparkleSurfaceRole.card,
                        child: Row(
                          children: [
                            CircleAvatar(
                              backgroundColor: DS.surfaceSecondary,
                              foregroundColor: DS.textPrimary,
                              child: Icon(_providerIcon(account.provider)),
                            ),
                            const SizedBox(width: DS.spacing16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _providerLabel(account.provider),
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleMedium
                                        ?.copyWith(fontWeight: FontWeight.w700),
                                  ),
                                  const SizedBox(height: DS.spacing4),
                                  Text(
                                    account.linked
                                        ? context.l10n.socialAccountsLinked
                                        : account.provider == 'wechat'
                                            ? context
                                                .l10n.socialAccountsWeChatPending
                                            : context
                                                .l10n.socialAccountsUnlinkedHint,
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(color: DS.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: DS.spacing12),
                            ConstrainedBox(
                              constraints: const BoxConstraints(
                                maxWidth: 110,
                                minWidth: 72,
                              ),
                              child: account.linked
                                  ? SparkleButton(
                                      label: context.l10n.socialAccountsUnlink,
                                      variant: ButtonVariant.outline,
                                      loading:
                                          _busyProvider == account.provider,
                                      onPressed: _busyProvider == null
                                          ? () {
                                              unawaited(
                                                _unlink(account.provider),
                                              );
                                            }
                                          : null,
                                    )
                                  : SparkleButton(
                                      label: context.l10n.socialAccountsLink,
                                      loading:
                                          _busyProvider == account.provider,
                                      onPressed: _busyProvider == null
                                          ? () {
                                              unawaited(
                                                _link(account.provider),
                                              );
                                            }
                                          : null,
                                    ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
}
