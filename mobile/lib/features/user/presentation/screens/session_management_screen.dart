import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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

  String _formatTime(DateTime value) {
    final local = value.toLocal();
    final two = (int n) => n.toString().padLeft(2, '0');
    return '${local.year}-${two(local.month)}-${two(local.day)} ${two(local.hour)}:${two(local.minute)}';
  }

  String _deviceTitle(UserSessionModel session) {
    if ((session.deviceName ?? '').isNotEmpty) {
      return session.deviceName!;
    }
    if ((session.deviceType ?? '').isNotEmpty) {
      return session.deviceType!.toUpperCase();
    }
    return '未知设备';
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
          title: const Text('登录设备管理'),
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
                        '这里会展示最近活跃的登录设备。若你怀疑账号在陌生设备上登录，可以一键下线其他设备。',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: DS.spacing16),
                      SparkleButton(
                        label: '下线其他设备',
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
                  const GraphiteCardSurface(
                    child: Text('当前还没有可展示的会话记录。'),
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
                              children: [
                                Icon(
                                  session.isCurrent
                                      ? Icons.smartphone_rounded
                                      : Icons.devices_other_rounded,
                                  color: DS.primaryBase,
                                ),
                                const SizedBox(width: DS.spacing12),
                                Expanded(
                                  child: Text(
                                    _deviceTitle(session),
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleMedium
                                        ?.copyWith(fontWeight: FontWeight.w700),
                                  ),
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
                                    child: const Text('当前设备'),
                                  ),
                              ],
                            ),
                            const SizedBox(height: DS.spacing12),
                            Text('最近活跃：${_formatTime(session.lastActiveAt)}'),
                            Text('首次登录：${_formatTime(session.createdAt)}'),
                            if ((session.ipAddress ?? '').isNotEmpty)
                              Text('IP：${session.ipAddress}'),
                            if ((session.userAgent ?? '').isNotEmpty)
                              Text(
                                'UA：${session.userAgent}',
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            const SizedBox(height: DS.spacing16),
                            Align(
                              alignment: Alignment.centerRight,
                              child: session.isCurrent
                                  ? Text(
                                      '当前设备请使用“退出登录”处理',
                                      style: TextStyle(
                                        color: DS.textSecondary,
                                      ),
                                    )
                                  : SparkleButton(
                                      label: '下线此设备',
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
