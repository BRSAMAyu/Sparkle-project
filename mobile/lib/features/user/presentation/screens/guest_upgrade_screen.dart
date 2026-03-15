import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/social_auth_service.dart';
import 'package:sparkle/features/auth/auth.dart';

class GuestUpgradeScreen extends ConsumerStatefulWidget {
  const GuestUpgradeScreen({super.key});

  @override
  ConsumerState<GuestUpgradeScreen> createState() => _GuestUpgradeScreenState();
}

class _GuestUpgradeScreenState extends ConsumerState<GuestUpgradeScreen> {
  static const _tosVersion = 'v1';
  static const _privacyVersion = 'v1';
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
      AppFeedback.info(context, '请先同意用户协议与隐私政策');
      return;
    }

    setState(() => _isLoading = true);
    try {
      await ref.read(authProvider.notifier).upgradeGuest(
            username: _usernameController.text.trim(),
            email: _emailController.text.trim(),
            password: _passwordController.text.trim(),
            acceptedTos: _acceptedTos,
            acceptedPrivacy: _acceptedPrivacy,
            tosVersion: _tosVersion,
            privacyVersion: _privacyVersion,
            agreedLocale: Localizations.localeOf(context).toLanguageTag(),
          );
      if (!mounted) return;
      AppFeedback.success(context, '游客账号已升级，欢迎回来。');
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
      AppFeedback.info(context, '请先同意用户协议与隐私政策');
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
      await ref.read(authProvider.notifier).upgradeGuestWithSocial(
            provider: result.provider,
            token: result.token,
            openid: result.openid,
            acceptedTos: _acceptedTos,
            acceptedPrivacy: _acceptedPrivacy,
            tosVersion: _tosVersion,
            privacyVersion: _privacyVersion,
            agreedLocale: Localizations.localeOf(context).toLanguageTag(),
          );
      if (!mounted) return;
      AppFeedback.success(context, '游客账号已升级，后续可以使用社交账号直接登录。');
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
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.settings,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: const Text('升级游客账号'),
          centerTitle: true,
        ),
        child: ContentConstraint(
          child: ListView(
            padding: const EdgeInsets.all(DS.spacing24),
            children: [
              GraphiteCardSurface(
                child: Text(
                  '把当前游客账号升级为正式账号后，你的学习记录和个人数据会保留下来，后续也能在新设备上继续使用。',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      TextFormField(
                        controller: _usernameController,
                        decoration: const InputDecoration(
                          labelText: '用户名',
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value == null || value.trim().length < 3) {
                            return '用户名至少 3 个字符';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: DS.spacing16),
                      TextFormField(
                        controller: _emailController,
                        decoration: const InputDecoration(
                          labelText: '邮箱',
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value == null ||
                              !RegExp(r'^[^@]+@[^@]+\.[^@]+')
                                  .hasMatch(value.trim())) {
                            return '请输入有效邮箱';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: DS.spacing16),
                      TextFormField(
                        controller: _passwordController,
                        obscureText: true,
                        decoration: const InputDecoration(
                          labelText: '密码',
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value == null || value.trim().length < 8) {
                            return '密码至少 8 位';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: DS.spacing16),
                      TextFormField(
                        controller: _confirmPasswordController,
                        obscureText: true,
                        decoration: const InputDecoration(
                          labelText: '确认密码',
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (value != _passwordController.text) {
                            return '两次输入的密码不一致';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: DS.spacing16),
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: _acceptedTos,
                        onChanged: (value) =>
                            setState(() => _acceptedTos = value ?? false),
                        title: const Text('同意《用户协议》'),
                        controlAffinity: ListTileControlAffinity.leading,
                      ),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton(
                          onPressed: () => context.push('/legal/terms'),
                          child: const Text('查看用户协议'),
                        ),
                      ),
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: _acceptedPrivacy,
                        onChanged: (value) =>
                            setState(() => _acceptedPrivacy = value ?? false),
                        title: const Text('同意《隐私政策》'),
                        controlAffinity: ListTileControlAffinity.leading,
                      ),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton(
                          onPressed: () => context.push('/legal/privacy'),
                          child: const Text('查看隐私政策'),
                        ),
                      ),
                      const SizedBox(height: DS.spacing16),
                      SparkleButton(
                        label: '升级为邮箱账号',
                        variant: ButtonVariant.primary,
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
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      '或者直接绑定一个社交账号',
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: DS.spacing16),
                    SparkleButton(
                      label: '使用 Google 升级',
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
                      label: '使用 Apple 升级',
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
                        label: '使用微信升级',
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
