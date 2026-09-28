import 'package:flutter/material.dart';

/// V4-F04 · Shell 目的地数据模型——图标语义独立。
///
/// 卡面「图标语义独立，不照抄四Tab参考图」的落点：可访问名称不派生自
/// 图标字形、视觉位置或图标码点，由 [semanticsLabel] 显式携带（当前
/// 与 [label] 同源的 l10n 文案；两者解耦后语义可独立演化）；未读角标
/// 另带 [badgeSemanticsLabel]（如「3 条未读通知」），不把数字混进 tab 名。
///
/// 数据即合同：底栏 / 平板 rail / 桌面侧栏三个呈现面消费同一模型，
/// 保证三档语义一致（V4-F04 响应式升级的组件化面）。
@immutable
class ShellDestination {
  const ShellDestination({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.semanticsLabel,
    this.badgeCount = 0,
    this.badgeSemanticsLabel,
    this.badgeOverflowLabel = '9+',
  });

  /// 未选中态图标（视觉字形；不参与语义命名）。
  final IconData icon;

  /// 选中态图标（视觉字形；不参与语义命名）。
  final IconData selectedIcon;

  /// 视觉标签（l10n）。
  final String label;

  /// 无障碍名称（l10n；与图标字形/视觉位置独立）。
  final String semanticsLabel;

  /// 未读角标计数（0 = 无角标；沿用 IR-G2/N24「进入即清」上游计数）。
  final int badgeCount;

  /// 角标语义（l10n unreadNotifications(count)；仅 [badgeCount] > 0 使用）。
  final String? badgeSemanticsLabel;

  /// 角标溢出文案（沿用 l10n.badgeOverflow「9+」）。
  final String badgeOverflowLabel;

  bool get hasBadge => badgeCount > 0;
}
