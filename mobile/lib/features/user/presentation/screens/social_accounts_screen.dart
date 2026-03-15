import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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
      AppFeedback.info(context, '微信 SDK 未初始化，请检查配置。');
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
            title: Text('解绑${_providerLabel(provider)}'),
            content: const Text('解绑后，该方式将不能再用于登录当前账号。'),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: const Text('取消'),
              ),
              FilledButton(
                onPressed: () => Navigator.of(dialogContext).pop(true),
                child: const Text('确认解绑'),
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
    switch (provider) {
      case 'google':
        return 'Google';
      case 'apple':
        return 'Apple';
      case 'wechat':
        return '微信';
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
          title: const Text('关联账号'),
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
                    '你可以在这里绑定更多登录方式，提升账号找回与多端登录的灵活性。',
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
                                        ? '已绑定，可用于登录或找回账号'
                                        : account.provider == 'wechat'
                                            ? '等待微信登录接入完成后可绑定'
                                            : '未绑定，建议补充一个备用登录方式',
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(color: DS.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: DS.spacing12),
                            SizedBox(
                              width: 110,
                              child: account.linked
                                  ? SparkleButton(
                                      label: '解绑',
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
                                      label: '绑定',
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
