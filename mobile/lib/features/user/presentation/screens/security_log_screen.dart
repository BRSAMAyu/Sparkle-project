import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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
    final local = value.toLocal();
    final two = (int n) => n.toString().padLeft(2, '0');
    return '${local.year}-${two(local.month)}-${two(local.day)} ${two(local.hour)}:${two(local.minute)}';
  }

  String _actionLabel(String action) {
    switch (action) {
      case 'login':
        return '登录成功';
      case 'login_failed':
        return '登录失败';
      case 'logout':
        return '退出登录';
      case 'register':
        return '注册账号';
      case 'password_change':
        return '修改密码';
      case 'password_reset':
        return '重置密码';
      case 'social_link':
        return '绑定社交账号';
      case 'social_unlink':
        return '解绑社交账号';
      case 'account_delete':
        return '注销账号';
      case 'token_refresh':
        return '刷新登录状态';
      case 'email_verify':
        return '验证邮箱';
      case 'guest_upgrade':
        return '游客升级';
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
          title: const Text('安全日志'),
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
                    '这里保留最近的登录、安全与账号变更记录，方便你排查异常行为。',
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
                  const GraphiteCardSurface(
                    child: Text('最近 30 天内还没有安全日志。'),
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
                            Text('发生时间：${_formatTime(item.occurredAt)}'),
                            if ((item.ipAddress ?? '').isNotEmpty)
                              Text('IP：${item.ipAddress}'),
                            if ((item.userAgent ?? '').isNotEmpty)
                              Text(
                                '设备：${item.userAgent}',
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            if ((item.metadata ?? const {}).isNotEmpty) ...[
                              const SizedBox(height: DS.spacing8),
                              Text(
                                '附加信息：${item.metadata}',
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
