import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/models/account_security_model.dart';

class SessionManagementScreen extends ConsumerStatefulWidget {
  const SessionManagementScreen({super.key});

  @override
  ConsumerState<SessionManagementScreen> createState() =>
      _SessionManagementScreenState();
}

class _SessionManagementScreenState
    extends ConsumerState<SessionManagementScreen> {
  List<UserSessionModel> _sessions = const [];
  bool _isLoading = true;
  String? _busySessionId;
  bool _isRevokingOthers = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadSessions());
  }

  Future<void> _loadSessions() async {
    setState(() => _isLoading = true);
    try {
      final sessions = await ref.read(authProvider.notifier).getSessions();
      if (!mounted) return;
      setState(() => _sessions = sessions);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _revokeSession(String sessionId) async {
    setState(() => _busySessionId = sessionId);
    try {
      final message =
          await ref.read(authProvider.notifier).revokeSession(sessionId);
      if (!mounted) return;
      AppFeedback.success(context, message);
      await _loadSessions();
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _busySessionId = null);
      }
    }
  }

  Future<void> _revokeOthers() async {
    setState(() => _isRevokingOthers = true);
    try {
      final message =
          await ref.read(authProvider.notifier).revokeOtherSessions();
      if (!mounted) return;
      AppFeedback.success(context, message);
      await _loadSessions();
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    } finally {
      if (mounted) {
        setState(() => _isRevokingOthers = false);
      }
    }
  }

  String _formatTime(DateTime value) => Formatters.formatDateTime(value.toLocal());

  String _deviceTitle(UserSessionModel session) {
    final l10n = context.l10n;
    if ((session.deviceName ?? '').isNotEmpty) {
      return session.deviceName!;
    }
    if ((session.deviceType ?? '').isNotEmpty) {
      return session.deviceType!.toUpperCase();
    }
    return l10n.sessionManagementUnknownDevice;
  }

  Widget _buildInfoRow(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: DS.textSecondary),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 13,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
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
          title: Text(context.l10n.sessionManagementTitle),
          centerTitle: true,
        ),
        child: ContentConstraint(
          child: RefreshIndicator(
            onRefresh: _loadSessions,
            child: ListView(
              padding: const EdgeInsets.all(DS.spacing24),
              children: [
                GraphiteCardSurface(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.sessionManagementIntro,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: DS.spacing16),
                      SparkleButton(
                        label: context.l10n.sessionManagementRevokeOthers,
                        variant: ButtonVariant.destructive,
                        expand: true,
                        loading: _isRevokingOthers,
                        onPressed: _isRevokingOthers
                            ? null
                            : () {
                                unawaited(_revokeOthers());
                              },
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: DS.spacing40),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (_sessions.isEmpty)
                  GraphiteCardSurface(
                    child: Text(context.l10n.sessionManagementEmpty),
                  )
                else
                  ..._sessions.map(
                    (session) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing12),
                      child: GraphiteCardSurface(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(DS.spacing8),
                                  decoration: BoxDecoration(
                                    color: DS.primaryBase.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(DS.spacing8),
                                  ),
                                  child: Icon(
                                    session.isCurrent
                                        ? Icons.smartphone_rounded
                                        : Icons.devices_other_rounded,
                                    color: DS.primaryBase,
                                  ),
                                ),
                                const SizedBox(width: DS.spacing12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Wrap(
                                        spacing: DS.spacing8,
                                        crossAxisAlignment: WrapCrossAlignment.center,
                                        children: [
                                          Text(
                                            _deviceTitle(session),
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium
                                                ?.copyWith(fontWeight: FontWeight.w700),
                                          ),
                                          if (session.isCurrent)
                                            Container(
                                              padding: const EdgeInsets.symmetric(
                                                horizontal: DS.spacing8,
                                                vertical: DS.spacing4,
                                              ),
                                              decoration: BoxDecoration(
                                                color: DS.success.withValues(alpha: 0.12),
                                                borderRadius: BorderRadius.circular(999),
                                              ),
                                              child: Text(
                                                context.l10n.sessionManagementCurrent,
                                                style: TextStyle(
                                                  fontSize: 12,
                                                  color: DS.success,
                                                  fontWeight: FontWeight.w500,
                                                ),
                                              ),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: DS.spacing12),
                                      _buildInfoRow(
                                        Icons.access_time_rounded,
                                        context.l10n.sessionManagementLastActive(
                                          _formatTime(session.lastActiveAt),
                                        ),
                                      ),
                                      _buildInfoRow(
                                        Icons.login_rounded,
                                        context.l10n.sessionManagementFirstLogin(
                                          _formatTime(session.createdAt),
                                        ),
                                      ),
                                      if ((session.ipAddress ?? '').isNotEmpty)
                                        _buildInfoRow(
                                          Icons.wifi_rounded,
                                          'IP: ${session.ipAddress}',
                                        ),
                                      if ((session.userAgent ?? '').isNotEmpty)
                                        _buildInfoRow(
                                          Icons.info_outline_rounded,
                                          session.userAgent!,
                                        ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: DS.spacing16),
                            Align(
                              alignment: Alignment.centerRight,
                              child: session.isCurrent
                                  ? Text(
                                      context.l10n
                                          .sessionManagementCurrentHint,
                                      style: TextStyle(
                                        color: DS.textSecondary,
                                      ),
                                    )
                                  : SparkleButton(
                                      label: context
                                          .l10n.sessionManagementRevokeThis,
                                      variant: ButtonVariant.outline,
                                      loading:
                                          _busySessionId == session.sessionId,
                                      onPressed: _busySessionId == null
                                          ? () {
                                              unawaited(
                                                _revokeSession(
                                                  session.sessionId,
                                                ),
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
