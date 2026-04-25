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
  static const int _pageSize = 20;
  List<AuthAuditLogModel> _logs = const [];
  bool _isLoading = true;
  bool _isLoadingMore = false;
  bool _hasMore = true;
  final Set<int> _expandedIndices = {};

  @override
  void initState() {
    super.initState();
    unawaited(_loadLogs());
  }

  Future<void> _loadLogs() async {
    setState(() {
      _isLoading = true;
      _hasMore = true;
    });
    try {
      final logs = await ref.read(authProvider.notifier).getSecurityLog(
            limit: _pageSize,
            offset: 0,
          );
      if (!mounted) return;
      setState(() => _logs = logs);
      _expandedIndices.clear();
      _hasMore = logs.length == _pageSize;
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _loadMoreLogs() async {
    if (_isLoadingMore || !_hasMore) {
      return;
    }
    setState(() => _isLoadingMore = true);
    try {
      final moreLogs = await ref.read(authProvider.notifier).getSecurityLog(
            limit: _pageSize,
            offset: _logs.length,
          );
      if (!mounted) return;
      setState(() {
        _logs = [..._logs, ...moreLogs];
        _hasMore = moreLogs.length == _pageSize;
      });
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoadingMore = false);
      }
    }
  }

  String _formatTime(DateTime value) =>
      Formatters.formatDateTime(value.toLocal());

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

  IconData _actionIcon(String action) {
    switch (action) {
      case 'login':
        return Icons.login_rounded;
      case 'login_failed':
        return Icons.warning_amber_rounded;
      case 'logout':
        return Icons.logout_rounded;
      case 'register':
        return Icons.person_add_outlined;
      case 'password_change':
      case 'password_reset':
        return Icons.lock_reset_rounded;
      case 'social_link':
        return Icons.link_rounded;
      case 'social_unlink':
        return Icons.link_off_rounded;
      case 'account_delete':
        return Icons.delete_forever_rounded;
      case 'token_refresh':
        return Icons.refresh_rounded;
      case 'email_verify':
        return Icons.mark_email_read_outlined;
      case 'guest_upgrade':
        return Icons.upgrade_rounded;
      default:
        return Icons.history_rounded;
    }
  }

  Color _actionColor(String action) {
    switch (action) {
      case 'login_failed':
      case 'account_delete':
        return DS.error;
      case 'login':
      case 'register':
      case 'guest_upgrade':
        return DS.success;
      case 'logout':
        return DS.warning;
      default:
        return DS.info;
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
                              icon: Icons.history_rounded,
                              label: '共 ${_logs.length} 条记录',
                            ),
                            _buildInfoChip(
                              context,
                              icon: Icons.warning_amber_rounded,
                              label:
                                  '异常 ${_logs.where((item) => item.action == 'login_failed' || item.action == 'account_delete').length} 条',
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.spacing12),
                        Text(
                          context.l10n.securityLogIntro,
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
                else if (_logs.isEmpty)
                  GraphiteCardSurface(
                    child: Text(context.l10n.securityLogEmpty),
                  )
                else
                  ..._logs.asMap().entries.map(
                    (entry) {
                      final index = entry.key;
                      final item = entry.value;
                      final isExpanded = _expandedIndices.contains(index);
                      final color = _actionColor(item.action);

                      return Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing12),
                        child: SparkleStaggerItem(
                          index: index + 1,
                          child: GraphiteCardSurface(
                            child: InkWell(
                              borderRadius: DS.borderRadius16,
                              onTap: () {
                                setState(() {
                                  if (isExpanded) {
                                    _expandedIndices.remove(index);
                                  } else {
                                    _expandedIndices.add(index);
                                  }
                                });
                              },
                              child: Padding(
                                padding: const EdgeInsets.all(DS.spacing16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.all(DS.sm),
                                          decoration: BoxDecoration(
                                            color:
                                                color.withValues(alpha: 0.12),
                                            borderRadius: DS.borderRadius8,
                                          ),
                                          child: Icon(
                                            _actionIcon(item.action),
                                            size: 18,
                                            color: color,
                                          ),
                                        ),
                                        const SizedBox(width: DS.spacing12),
                                        Expanded(
                                          child: Wrap(
                                            spacing: DS.spacing8,
                                            runSpacing: DS.spacing8,
                                            children: [
                                              Text(
                                                _actionLabel(item.action),
                                                style: Theme.of(context)
                                                    .textTheme
                                                    .titleMedium
                                                    ?.copyWith(
                                                      fontWeight:
                                                          DS.fontWeightBold,
                                                    ),
                                              ),
                                              _SecurityStatePill(
                                                label: item.action,
                                                color: color,
                                              ),
                                            ],
                                          ),
                                        ),
                                        Icon(
                                          isExpanded
                                              ? Icons.keyboard_arrow_up_rounded
                                              : Icons
                                                  .keyboard_arrow_down_rounded,
                                          color: DS.textSecondary,
                                          size: 20,
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: DS.spacing10),
                                    _buildMetaLine(
                                      context.l10n.securityLogOccurredAt(
                                        _formatTime(item.occurredAt),
                                      ),
                                    ),
                                    if ((item.ipAddress ?? '').isNotEmpty)
                                      _buildMetaLine('IP: ${item.ipAddress}'),
                                    if (isExpanded) ...[
                                      const SizedBox(height: DS.spacing10),
                                      if ((item.userAgent ?? '').isNotEmpty)
                                        Container(
                                          padding: const EdgeInsets.all(
                                            DS.spacing12,
                                          ),
                                          decoration: BoxDecoration(
                                            color: DS.surfaceSecondary,
                                            borderRadius: DS.borderRadius12,
                                            border: Border.all(
                                              color: DS.borderSubtle,
                                            ),
                                          ),
                                          child: Text(
                                            context.l10n.securityLogDevice(
                                              item.userAgent!,
                                            ),
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodySmall
                                                ?.copyWith(
                                                  color: DS.textSecondary,
                                                  height: 1.4,
                                                ),
                                            maxLines: 3,
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      if ((item.metadata ?? const {})
                                          .isNotEmpty) ...[
                                        const SizedBox(height: DS.spacing8),
                                        Container(
                                          padding: const EdgeInsets.all(
                                            DS.spacing12,
                                          ),
                                          decoration: BoxDecoration(
                                            color: DS.surfaceSecondary,
                                            borderRadius: DS.borderRadius12,
                                            border: Border.all(
                                              color: DS.borderSubtle,
                                            ),
                                          ),
                                          child: Text(
                                            context.l10n
                                                .securityLogAdditionalInfo(
                                              item.metadata.toString(),
                                            ),
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodySmall
                                                ?.copyWith(
                                                  color: DS.textSecondary,
                                                  height: 1.4,
                                                ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                if (!_isLoading && _logs.isNotEmpty && _hasMore)
                  Padding(
                    padding: const EdgeInsets.only(top: DS.spacing8),
                    child: SparkleButton.ghost(
                      label: _isLoadingMore ? '加载中…' : '加载更多记录',
                      onPressed: _isLoadingMore ? () {} : _loadMoreLogs,
                      expand: true,
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

  Widget _buildMetaLine(String text) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing4),
        child: SelectableText(
          text,
          style: TextStyle(
            color: DS.textSecondary,
            fontSize: 13,
          ),
        ),
      );
}

class _SecurityStatePill extends StatelessWidget {
  const _SecurityStatePill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: color,
                fontWeight: DS.fontWeightBold,
              ),
        ),
      );
}
