import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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
      AppFeedback.info(context, '当前账号没有可用于重新验证的社交登录方式。');
      return;
    }
    if (provider == 'wechat' && !SocialAuthService().isWeChatAvailable) {
      AppFeedback.info(context, '微信 SDK 未初始化，请先设置密码后再注销。');
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
      AppFeedback.success(context, '已完成重新验证，可以继续注销账号。');
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
      AppFeedback.info(context, '请输入 DELETE 以确认注销');
      return;
    }
    if (!_isGuest && _requiresPassword && _passwordController.text.isEmpty) {
      AppFeedback.info(context, '请输入当前密码');
      return;
    }
    if (!_isGuest && !_requiresPassword && (_providerToken?.isEmpty ?? true)) {
      AppFeedback.info(context, '请先完成社交账号重新验证');
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
      AppFeedback.success(context, '账号已注销');
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
          title: const Text('注销账号'),
          centerTitle: true,
        ),
        child: ContentConstraint(
          child: ListView(
            padding: const EdgeInsets.all(DS.spacing24),
            children: [
              const GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '注销前请确认',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    SizedBox(height: DS.spacing12),
                    Text('1. 当前账号会立即失效，所有设备会被强制下线。'),
                    Text('2. 账号资料会进入删除流程，后续可能无法恢复。'),
                    Text('3. 如果你只是想临时退出，建议使用普通登出。'),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '输入 DELETE 确认',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    TextField(
                      controller: _confirmationController,
                      decoration: const InputDecoration(
                        hintText: '请输入 DELETE',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    if (_requiresPassword) ...[
                      const SizedBox(height: DS.spacing16),
                      const Text(
                        '当前密码',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: DS.spacing12),
                      TextField(
                        controller: _passwordController,
                        obscureText: true,
                        decoration: const InputDecoration(
                          hintText: '请输入当前密码',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ] else if (!_isGuest) ...[
                      const SizedBox(height: DS.spacing16),
                      Text(
                        '当前账号需要通过${_socialProvider == 'apple' ? 'Apple' : _socialProvider == 'google' ? 'Google' : '社交账号'}重新验证后才能注销。',
                      ),
                      const SizedBox(height: DS.spacing12),
                      SparkleButton(
                        label: _providerToken == null ? '重新验证身份' : '已完成验证',
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
                      label: '确认注销账号',
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
