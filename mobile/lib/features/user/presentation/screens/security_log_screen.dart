import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/models/account_security_model.dart';

class SecurityLogScreen extends ConsumerStatefulWidget {
  const SecurityLogScreen({super.key});

  @override
  ConsumerState<SecurityLogScreen> createState() => _SecurityLogScreenState();
}

class _SecurityLogScreenState extends ConsumerState<SecurityLogScreen> {
  List<AuthAuditLogModel> _logs = const [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    unawaited(_loadLogs());
  }

  Future<void> _loadLogs() async {
    setState(() => _isLoading = true);
    try {
      final logs = await ref.read(authProvider.notifier).getSecurityLog();
      if (!mounted) return;
      setState(() => _logs = logs);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  String _formatTime(DateTime value) {
    return Formatters.formatDateTime(value.toLocal());
  }

  String _actionLabel(String action) {
    final l10n = context.l10n;
    switch (action) {
      case 'login':
        return l10n.securityLogActionLoginSuccess;
      case 'login_failed':
        return l10n.securityLogActionLoginFailed;
      case 'logout':
        return l10n.securityLogActionLogout;
      case 'register':
        return l10n.securityLogActionRegister;
      case 'password_change':
        return l10n.securityLogActionPasswordChange;
      case 'password_reset':
        return l10n.securityLogActionPasswordReset;
      case 'social_link':
        return l10n.securityLogActionSocialLink;
      case 'social_unlink':
        return l10n.securityLogActionSocialUnlink;
      case 'account_delete':
        return l10n.securityLogActionAccountDelete;
      case 'token_refresh':
        return l10n.securityLogActionTokenRefresh;
      case 'email_verify':
        return l10n.securityLogActionEmailVerify;
      case 'guest_upgrade':
        return l10n.securityLogActionGuestUpgrade;
      default:
        return action;
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
          title: Text(context.l10n.securityLogTitle),
          centerTitle: true,
        ),
        child: ContentConstraint(
          child: RefreshIndicator(
            onRefresh: _loadLogs,
            child: ListView(
              padding: const EdgeInsets.all(DS.spacing24),
              children: [
                GraphiteCardSurface(
                  child: Text(
                    context.l10n.securityLogIntro,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: DS.spacing40),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (_logs.isEmpty)
                  GraphiteCardSurface(
                    child: Text(context.l10n.securityLogEmpty),
                  )
                else
                  ..._logs.map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing12),
                      child: GraphiteCardSurface(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _actionLabel(item.action),
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                            const SizedBox(height: DS.spacing8),
                            Text(
                              context.l10n.securityLogOccurredAt(
                                _formatTime(item.occurredAt),
                              ),
                            ),
                            if ((item.ipAddress ?? '').isNotEmpty)
                              Text('IP：${item.ipAddress}'),
                            if ((item.userAgent ?? '').isNotEmpty)
                              Text(
                                context.l10n
                                    .securityLogDevice(item.userAgent!),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            if ((item.metadata ?? const {}).isNotEmpty) ...[
                              const SizedBox(height: DS.spacing8),
                              Text(
                                context.l10n.securityLogAdditionalInfo(
                                  item.metadata.toString(),
                                ),
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: DS.textSecondary),
                              ),
                            ],
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
