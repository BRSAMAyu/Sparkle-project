import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// U14 · 深链空对象统一面（SCREEN_FAMILIES「账号/设置/通知/异常/长尾」：
/// 「通知深链落在具体对象，对象已删或权限失效有可理解的替代页。
/// 404/离线/登录失效与模型失败不同，不全部跳『AI出错』」）。
///
/// 诚实原则：三类失效语义分开呈现——
/// - [ObjectUnavailableKind.missing]：对象已删除或不存在（有 404 类确证信号
///   才落此面；无法确认时宁可落 offline，绝不凭空宣布「已删除」）；
/// - [ObjectUnavailableKind.offline]：网络/服务暂不可达，无法确认（可重试）；
/// - [ObjectUnavailableKind.auth]：登录状态失效（去登录/回首页，路由级
///   认证闸接管后续）。
///
/// 本组件只做呈现（DS 令牌 + l10n），不做异常→类别判定——判定一律走
/// `core/display/lexicon/error_lexicon.dart` 单一 owner（N16）；也不绑定
/// feature 域路由常量（core 不反向依赖 features），落点由调用方传入。
enum ObjectUnavailableKind { missing, offline, auth }

/// 深链指向的对象无法到达时的统一替代页（非空白、非错误任务、非伪成功）。
class ObjectUnavailableSurface extends StatelessWidget {
  const ObjectUnavailableSurface({
    required this.kind,
    required this.title,
    required this.body,
    required this.fallbackRoute,
    super.key,
    this.primaryLabel,
    this.onPrimary,
    this.icon,
  });

  final ObjectUnavailableKind kind;
  final String title;
  final String body;
  final IconData? icon;

  /// 主动作文案与回调（offline = 重试；missing = 域内列表出口）。
  final String? primaryLabel;
  final VoidCallback? onPrimary;

  /// 恒在兜底出口的落点（回首页；由调用方传 feature 路由常量）。
  final String fallbackRoute;

  @override
  Widget build(BuildContext context) {
    final resolvedIcon = icon ??
        switch (kind) {
          ObjectUnavailableKind.missing => Icons.delete_outline_rounded,
          ObjectUnavailableKind.offline => Icons.cloud_off_rounded,
          ObjectUnavailableKind.auth => Icons.lock_outline_rounded,
        };
    // 提升非空提升到 build 顶部（SparkleButton.primary 要非空回调；
    // Dart 不提升实例字段，先拷贝为局部量）。
    final primaryLabel = this.primaryLabel;
    final onPrimary = this.onPrimary;
    final hasPrimary = primaryLabel != null && onPrimary != null;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          key: const ValueKey('object-unavailable-surface'),
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(resolvedIcon, size: 72, color: DS.textSecondary),
            const SizedBox(height: DS.spacing16),
            Text(
              title,
              key: const ValueKey('object-unavailable-title'),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: DS.fontWeightBold,
                    color: DS.textPrimary,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              body,
              key: const ValueKey('object-unavailable-body'),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing24),
            if (hasPrimary) ...[
              SizedBox(
                width: 220,
                child: SparkleButton.primary(
                  key: const ValueKey('object-unavailable-primary'),
                  label: primaryLabel,
                  onPressed: onPrimary,
                  expand: true,
                ),
              ),
              const SizedBox(height: DS.spacing12),
            ],
            // 恒在的兜底出口：任何失效面都不困住用户（回首页）。
            SparkleButton.ghost(
              key: const ValueKey('object-unavailable-back-home'),
              label: context.l10n.objectUnavailableBackHome,
              onPressed: () => GoRouter.of(context).go(fallbackRoute),
            ),
          ],
        ),
      ),
    );
  }
}
