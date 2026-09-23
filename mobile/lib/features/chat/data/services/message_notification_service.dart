import 'package:cached_network_image/cached_network_image.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/presentation/providers/focus_mode_provider.dart';

// Notification message model
class NotificationMessage {
  NotificationMessage({
    required this.id,
    required this.senderName,
    required this.content,
    required this.timestamp,
    required this.type,
    this.senderAvatarUrl,
    this.targetId,
  });
  final String id;
  final String senderName;
  final String? senderAvatarUrl;
  final String content;
  final DateTime timestamp;
  final NotificationType type;
  final String? targetId;
}

enum NotificationType { privateMessage, groupMessage, mention }

/// Unread message count provider
///
/// N24（A-SPEC4 v1.4 §4.2/§9.1）· 打断面生命周期三声明（badge 计数类）：
/// - **触发**：community WS 收到他人消息（群聊/私聊/被@）时 increment——
///   community_provider.dart 三处（群聊消息、mention、私聊）。
/// - **清除**：①进入社群 tab 即 reset（MainNavigationShell：tab 点击、
///   路由驱动进入、冷启动深链落地三入口）——角标是召回钩子不是资产，
///   到达目标面即清（对标 Linear「打开即清」/ iOS「进 app 即清」）；
///   ②群聊会话内消息被标记已读时 decrementBy 精确抵消
///   （GroupChatNotifier._markVisibleMessagesAsRead，正在看会话不计数）。
///   只增不清的计数器禁新增（N24 机检：本文件必须含清除方法且有调用点）。
/// - **到达**：community tab 角标（shell_navigation `_buildBadgedIcon`）→
///   点达 /community 分支；home 横幅（home_notification_card，未读时
///   整卡指向 go('/community')）；dashboard 摘要计数（dashboard_screen）。
final unreadMessageCountProvider =
    StateNotifierProvider<UnreadMessageCountNotifier, int>(
  (ref) => UnreadMessageCountNotifier(),
);

class UnreadMessageCountNotifier extends StateNotifier<int> {
  UnreadMessageCountNotifier() : super(0);

  void increment() => state++;
  void add(int count) => state += count;
  void reset() => state = 0;
  void decrement() => state = state > 0 ? state - 1 : 0;

  /// N24 逐条已读清除：一次标记已读 n 条即抵消 n（钳制 ≥0，防止
  /// 冷启动从历史载入时对从未 increment 过的消息负抵消）。
  void decrementBy(int count) {
    if (count <= 0) return;
    state = state > count ? state - count : 0;
  }
}

// In-app notification stream provider
final inAppNotificationProvider =
    StateNotifierProvider<InAppNotificationNotifier, NotificationMessage?>(
  (ref) => InAppNotificationNotifier(),
);

class InAppNotificationNotifier extends StateNotifier<NotificationMessage?> {
  InAppNotificationNotifier() : super(null);
  Timer? _dismissTimer;

  void show(NotificationMessage message) {
    _dismissTimer?.cancel();
    state = message;
    _dismissTimer = Timer(const Duration(seconds: 4), dismiss);
  }

  void dismiss() {
    _dismissTimer?.cancel();
    state = null;
  }

  @override
  void dispose() {
    _dismissTimer?.cancel();
    super.dispose();
  }
}

// In-app notification overlay widget
class InAppNotificationOverlay extends ConsumerWidget {
  const InAppNotificationOverlay({required this.child, super.key});
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notification = ref.watch(inAppNotificationProvider);
    final focusMode = ref.watch(_focusModeProviderOrFalse);

    return Stack(
      children: [
        child,
        if (notification != null && !focusMode)
          Positioned(
            top: MediaQuery.of(context).padding.top + 8,
            left: 16,
            right: 16,
            child: InAppNotificationBanner(
              notification: notification,
              onDismiss: () =>
                  ref.read(inAppNotificationProvider.notifier).dismiss(),
              onTap: () {
                ref.read(inAppNotificationProvider.notifier).dismiss();
                // Navigate to chat - this would need the navigator key or context
              },
            ),
          ),
      ],
    );
  }
}

// Use focusModeProvider from community_main_screen for focus mode integration
final _focusModeProviderOrFalse = Provider<bool>((ref) {
  try {
    return ref.watch(focusModeProvider);
  } catch (_) {
    return false;
  }
});

class InAppNotificationBanner extends StatefulWidget {
  const InAppNotificationBanner({
    required this.notification,
    required this.onDismiss,
    required this.onTap,
    super.key,
  });
  final NotificationMessage notification;
  final VoidCallback onDismiss;
  final VoidCallback onTap;

  @override
  State<InAppNotificationBanner> createState() =>
      _InAppNotificationBannerState();
}

class _InAppNotificationBannerState extends State<InAppNotificationBanner>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));
    _fadeAnimation = Tween<double>(begin: 0, end: 1).animate(_controller);
    unawaited(_controller.forward());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => SlideTransition(
        position: _slideAnimation,
        child: FadeTransition(
          opacity: _fadeAnimation,
          child: Dismissible(
            key: ValueKey(widget.notification.id),
            direction: DismissDirection.up,
            onDismissed: (_) => widget.onDismiss(),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: widget.onTap,
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  padding: const EdgeInsets.all(DS.md),
                  decoration: BoxDecoration(
                    color: Theme.of(context).cardColor,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: DS.brandPrimary.withValues(alpha: 0.15),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 20,
                        backgroundImage: widget.notification.senderAvatarUrl !=
                                null
                            ? CachedNetworkImageProvider(widget.notification.senderAvatarUrl!)
                            : null,
                        child: widget.notification.senderAvatarUrl == null
                            ? Text(widget.notification.senderName[0])
                            : null,
                      ),
                      const SizedBox(width: DS.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Row(
                              children: [
                                Text(
                                  widget.notification.senderName,
                                  style: const TextStyle(
                                    fontWeight: DS.fontWeightBold,
                                  ),
                                ),
                                const SizedBox(width: DS.sm),
                                if (widget.notification.type !=
                                    NotificationType.privateMessage)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 6,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: DS.brandPrimary
                                          .withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      widget.notification.type ==
                                              NotificationType.mention
                                          ? context.l10n.chatNotificationMention
                                          : context.l10n.chatNotificationGroupMessage,
                                      style: TextStyle(
                                        fontSize: 10,
                                        color: DS.brandPrimaryConst,
                                      ),
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: DS.xs),
                            Text(
                              widget.notification.content,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.color
                                    ?.withValues(alpha: 0.7),
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),
                      SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        size: 28,
                        icon: const Icon(Icons.close, size: 18),
                        onPressed: widget.onDismiss,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      );
}

// Message badge widget for navigation bar
class MessageBadge extends ConsumerWidget {
  const MessageBadge({required this.child, super.key});
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unreadCount = ref.watch(unreadMessageCountProvider);

    return Stack(
      clipBehavior: Clip.none,
      children: [
        child,
        if (unreadCount > 0)
          Positioned(
            right: -6,
            top: -4,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: DS.error,
                borderRadius: BorderRadius.circular(10),
              ),
              constraints: const BoxConstraints(minWidth: 18, minHeight: 18),
              child: Text(
                unreadCount > 99 ? '99+' : '$unreadCount',
                style: TextStyle(
                  color: DS.brandPrimaryConst,
                  fontSize: 10,
                  fontWeight: DS.fontWeightBold,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
      ],
    );
  }
}
