import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
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
    final confirmed = await showSensoryDialog<bool>(
          context: context,
          builder: (dialogContext) {
            final media = MediaQuery.of(dialogContext);
            final stackActions = media.size.width < 360;
            return Dialog(
              backgroundColor: Colors.transparent,
              insetPadding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth: 460,
                  maxHeight: media.size.height * 0.85,
                ),
                child: GraphiteModalSurface(
                  title: context.l10n.socialAccountsUnlinkTitle(
                    _providerLabel(provider),
                  ),
                  showHandle: false,
                  borderRadius: BorderRadius.circular(28),
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.l10n.socialAccountsUnlinkMessage,
                          style: Theme.of(dialogContext)
                              .textTheme
                              .bodyMedium
                              ?.copyWith(
                                color: DS.textSecondary,
                                height: 1.45,
                              ),
                        ),
                        const SizedBox(height: DS.spacing16),
                        if (stackActions) ...[
                          SizedBox(
                            width: double.infinity,
                            child: SparkleButton.outline(
                              label: context.l10n.socialAccountsUnlinkConfirm,
                              onPressed: () =>
                                  Navigator.of(dialogContext).pop(true),
                              expand: true,
                            ),
                          ),
                          const SizedBox(height: DS.spacing12),
                          SizedBox(
                            width: double.infinity,
                            child: SparkleButton.ghost(
                              label: context.l10n.cancel,
                              onPressed: () =>
                                  Navigator.of(dialogContext).pop(false),
                              expand: true,
                            ),
                          ),
                        ] else
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
                                child: SparkleButton.outline(
                                  label:
                                      context.l10n.socialAccountsUnlinkConfirm,
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
              ),
            );
          },
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
              padding: const EdgeInsets.symmetric(vertical: DS.spacing24),
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
                            _buildInfoChip(
                              context,
                              icon: Icons.link_rounded,
                              label: context.l10n.socialAcctLinkedCount('${_accounts.where((item) => item.linked).length}'),
                            ),
                            _buildInfoChip(
                              context,
                              icon: Icons.security_rounded,
                              label: context.l10n.socialAcctUnifiedLogin,
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.spacing12),
                        Text(
                          context.l10n.socialAccountsIntro,
                          style:
                              Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.45,
                                  ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: DS.spacing40),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else
                  ..._accounts.asMap().entries.map(
                        (entry) => Padding(
                          padding: const EdgeInsets.only(bottom: DS.spacing12),
                          child: SparkleStaggerItem(
                            index: entry.key + 1,
                            child: _SocialAccountCard(
                              providerLabel:
                                  _providerLabel(entry.value.provider),
                              providerIcon: _providerIcon(entry.value.provider),
                              linked: entry.value.linked,
                              hint: entry.value.linked
                                  ? context.l10n.socialAccountsLinked
                                  : entry.value.provider == 'wechat'
                                      ? context.l10n.socialAccountsWeChatPending
                                      : context.l10n.socialAccountsUnlinkedHint,
                              loading: _busyProvider == entry.value.provider,
                              actionLabel: entry.value.linked
                                  ? context.l10n.socialAccountsUnlink
                                  : context.l10n.socialAccountsLink,
                              actionVariant: entry.value.linked
                                  ? ButtonVariant.outline
                                  : ButtonVariant.primary,
                              onPressed: _busyProvider == null
                                  ? () {
                                      unawaited(
                                        entry.value.linked
                                            ? _unlink(entry.value.provider)
                                            : _link(entry.value.provider),
                                      );
                                    }
                                  : null,
                            ),
                          ),
                        ),
                      ),
              ],
            ),
          ),
        ),
      );

  Widget _buildInfoChip(
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
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );
}

class _SocialAccountCard extends StatelessWidget {
  const _SocialAccountCard({
    required this.providerLabel,
    required this.providerIcon,
    required this.linked,
    required this.hint,
    required this.loading,
    required this.actionLabel,
    required this.actionVariant,
    required this.onPressed,
  });

  final String providerLabel;
  final IconData providerIcon;
  final bool linked;
  final String hint;
  final bool loading;
  final String actionLabel;
  final ButtonVariant actionVariant;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 360;
            final button = SparkleButton(
              label: actionLabel,
              variant: actionVariant,
              loading: loading,
              onPressed: onPressed,
              expand: compact,
            );

            final info = Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  backgroundColor: DS.surfaceSecondary,
                  foregroundColor: DS.textPrimary,
                  child: Icon(providerIcon),
                ),
                const SizedBox(width: DS.spacing16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: [
                          Text(
                            providerLabel,
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(fontWeight: DS.fontWeightBold),
                          ),
                          _AccountStatusPill(linked: linked),
                        ],
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        hint,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                              height: 1.4,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            );

            if (compact) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  info,
                  const SizedBox(height: DS.spacing12),
                  button,
                ],
              );
            }

            return Row(
              children: [
                Expanded(child: info),
                const SizedBox(width: DS.spacing12),
                ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: 110,
                    minWidth: 72,
                  ),
                  child: button,
                ),
              ],
            );
          },
        ),
      );
}

class _AccountStatusPill extends StatelessWidget {
  const _AccountStatusPill({required this.linked});

  final bool linked;

  @override
  Widget build(BuildContext context) {
    final color = linked ? DS.success : DS.textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        linked
            ? context.l10n.socialAcctConnected
            : context.l10n.socialAcctNotConnected,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: DS.fontWeightBold,
            ),
      ),
    );
  }
}
