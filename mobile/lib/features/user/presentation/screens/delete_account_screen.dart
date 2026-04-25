import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
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

  Future<void> _confirmAndSubmit() async {
    final confirmed = await showSensoryDialog<bool>(
          context: context,
          builder: (dialogContext) => Dialog(
            backgroundColor: Colors.transparent,
            insetPadding:
                const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
            child: GraphiteModalSurface(
              title: context.l10n.deleteAccountTitle,
              showHandle: false,
              borderRadius: BorderRadius.circular(28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '这个操作不可撤销，所有与账号绑定的个人数据、偏好和历史记录都将永久移除。',
                    style:
                        Theme.of(dialogContext).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  Row(
                    children: [
                      Expanded(
                        child: SparkleButton.ghost(
                          label: context.l10n.cancel,
                          onPressed: () =>
                              Navigator.of(dialogContext).pop(false),
                          expand: true,
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: SparkleButton.destructive(
                          label: context.l10n.deleteAccountConfirmButton,
                          onPressed: () =>
                              Navigator.of(dialogContext).pop(true),
                          expand: true,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ) ??
        false;

    if (!confirmed) {
      return;
    }
    await _submit();
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
                          _buildFlag(
                            icon: Icons.warning_amber_rounded,
                            label: '高风险操作',
                            color: DS.warning,
                          ),
                          _buildFlag(
                            icon: Icons.auto_delete_rounded,
                            label: '不可恢复',
                            color: DS.error,
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing12),
                      Text(
                        context.l10n.deleteAccountChecklistTitle,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing12),
                      _buildChecklistItem(
                          context.l10n.deleteAccountChecklistItem1,),
                      _buildChecklistItem(
                          context.l10n.deleteAccountChecklistItem2,),
                      _buildChecklistItem(
                          context.l10n.deleteAccountChecklistItem3,),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleStaggerItem(
                index: 1,
                child: GraphiteCardSurface(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.deleteAccountConfirmInputTitle,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        '请输入确认信息后再继续，这一步只在你明确要删除账号时才建议操作。',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.4,
                            ),
                      ),
                      const SizedBox(height: DS.spacing16),
                      _buildLabel(context.l10n.deleteAccountConfirmInputTitle),
                      const SizedBox(height: DS.spacing8),
                      TextField(
                        controller: _confirmationController,
                        decoration: _buildInputDecoration(
                          hintText: context.l10n.deleteAccountConfirmInputHint,
                          icon: Icons.keyboard_alt_rounded,
                        ),
                      ),
                      if (_requiresPassword) ...[
                        const SizedBox(height: DS.spacing20),
                        _buildLabel(context.l10n.deleteAccountPasswordLabel),
                        const SizedBox(height: DS.spacing8),
                        TextField(
                          controller: _passwordController,
                          obscureText: true,
                          decoration: _buildInputDecoration(
                            hintText: context.l10n.deleteAccountPasswordHint,
                            icon: Icons.lock_outline_rounded,
                          ),
                        ),
                      ] else if (!_isGuest) ...[
                        const SizedBox(height: DS.spacing20),
                        Container(
                          padding: const EdgeInsets.all(DS.spacing16),
                          decoration: BoxDecoration(
                            color: DS.surfaceSecondary,
                            borderRadius: DS.borderRadius16,
                            border: Border.all(color: DS.borderSubtle),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                context.l10n.deleteAccountSocialReauthNotice(
                                  _socialProvider == 'apple'
                                      ? 'Apple'
                                      : _socialProvider == 'google'
                                          ? 'Google'
                                          : context
                                              .l10n.deleteAccountSocialProvider,
                                ),
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.4,
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
                          ),
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
                                unawaited(_confirmAndSubmit());
                              },
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      );

  Widget _buildChecklistItem(String text) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              margin: const EdgeInsets.only(top: 2),
              width: 20,
              height: 20,
              decoration: BoxDecoration(
                color: DS.error.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: DS.error.withValues(alpha: 0.18)),
              ),
              child: Icon(
                Icons.priority_high_rounded,
                size: 12,
                color: DS.error,
              ),
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Text(
                text,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
            ),
          ],
        ),
      );

  Widget _buildFlag({
    required IconData icon,
    required String label,
    required Color color,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: color.withValues(alpha: 0.16)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: color,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );

  Widget _buildLabel(String text) => Text(
        text,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
      );

  InputDecoration _buildInputDecoration({
    required String hintText,
    required IconData icon,
  }) =>
      InputDecoration(
        hintText: hintText,
        prefixIcon: Icon(icon, size: 20),
        filled: true,
        fillColor: DS.surfaceSecondary,
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
          borderSide: BorderSide(color: DS.primaryBase, width: 1.5),
        ),
      );
}
