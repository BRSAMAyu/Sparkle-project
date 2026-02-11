import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 错误组件类型
enum ErrorType {
  page, // 全屏错误页
  banner, // 顶部错误横幅
  inline, // 内联错误提示
}

/// 错误严重程度
enum ErrorSeverity {
  error, // 错误（红色）
  warning, // 警告（橙色）
  info, // 信息（蓝色）
}

/// 自定义错误组件
///
/// 支持多种错误展示样式：全屏错误页、顶部横幅、内联提示
class CustomErrorWidget extends StatelessWidget {
  const CustomErrorWidget({
    required this.message,
    super.key,
    this.type = ErrorType.inline,
    this.severity = ErrorSeverity.error,
    this.title,
    this.icon,
    this.onRetry,
    this.onClose,
    this.actions,
    this.showIcon = true,
    this.l10n,
  });

  /// 全屏错误页工厂构造函数（带本地化支持）
  factory CustomErrorWidget.page({
    required String message,
    required BuildContext context,
    Key? key,
    String? title,
    IconData? icon,
    VoidCallback? onRetry,
    List<Widget>? actions,
    ErrorSeverity severity = ErrorSeverity.error,
  }) {
    final l10n = AppLocalizations.of(context);
    return CustomErrorWidget(
      key: key,
      type: ErrorType.page,
      severity: severity,
      title: title,
      message: message,
      icon: icon,
      onRetry: onRetry,
      actions: actions,
      l10n: l10n,
    );
  }

  /// 错误横幅工厂构造函数（带本地化支持）
  factory CustomErrorWidget.banner({
    required String message,
    required BuildContext context,
    Key? key,
    String? title,
    VoidCallback? onClose,
    ErrorSeverity severity = ErrorSeverity.error,
  }) {
    final l10n = AppLocalizations.of(context);
    return CustomErrorWidget(
      key: key,
      type: ErrorType.banner,
      severity: severity,
      title: title,
      message: message,
      onClose: onClose,
      l10n: l10n,
    );
  }

  /// 内联错误提示工厂构造函数（带本地化支持）
  factory CustomErrorWidget.inline({
    required String message,
    required BuildContext context,
    Key? key,
    IconData? icon,
    bool showIcon = true,
    ErrorSeverity severity = ErrorSeverity.error,
  }) {
    final l10n = AppLocalizations.of(context);
    return CustomErrorWidget(
      key: key,
      severity: severity,
      message: message,
      icon: icon,
      showIcon: showIcon,
      l10n: l10n,
    );
  }

  /// 错误类型
  final ErrorType type;

  /// 错误严重程度
  final ErrorSeverity severity;

  /// 错误标题
  final String? title;

  /// 错误消息
  final String message;

  /// 错误图标
  final IconData? icon;

  /// 重试回调
  final VoidCallback? onRetry;

  /// 关闭回调（仅适用于banner类型）
  final VoidCallback? onClose;

  /// 自定义操作按钮
  final List<Widget>? actions;

  /// 是否显示图标
  final bool showIcon;

  /// 本地化实例
  final AppLocalizations? l10n;

  @override
  Widget build(BuildContext context) {
    switch (type) {
      case ErrorType.page:
        return _buildErrorPage(context);
      case ErrorType.banner:
        return _buildErrorBanner(context);
      case ErrorType.inline:
        return _buildInlineError(context);
    }
  }

  Color _getBackgroundColor() {
    switch (severity) {
      case ErrorSeverity.error:
        return DS.error;
      case ErrorSeverity.warning:
        return DS.warning;
      case ErrorSeverity.info:
        return DS.info;
    }
  }

  Color _getLightBackgroundColor() {
    switch (severity) {
      case ErrorSeverity.error:
        return DS.errorLight.withValues(alpha: 0.1);
      case ErrorSeverity.warning:
        return DS.warningLight.withValues(alpha: 0.1);
      case ErrorSeverity.info:
        return DS.infoLight.withValues(alpha: 0.1);
    }
  }

  LinearGradient _getGradient() {
    switch (severity) {
      case ErrorSeverity.error:
        return DS.errorGradient;
      case ErrorSeverity.warning:
        return DS.warningGradient;
      case ErrorSeverity.info:
        return DS.infoGradient;
    }
  }

  IconData _getDefaultIcon() {
    switch (severity) {
      case ErrorSeverity.error:
        return Icons.error_outline_rounded;
      case ErrorSeverity.warning:
        return Icons.warning_amber_rounded;
      case ErrorSeverity.info:
        return Icons.info_outline_rounded;
    }
  }

  String _getDefaultTitle() {
    switch (severity) {
      case ErrorSeverity.error:
        return l10n?.errorTitle ?? '哎呀，出错了';
      case ErrorSeverity.warning:
        return l10n?.warningTitle ?? '温馨提示';
      case ErrorSeverity.info:
        return l10n?.infoTitle ?? '小提示';
    }
  }

  String _getRetryText() => l10n?.retry ?? '重试';

  Widget _buildErrorPage(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // 错误图标
              if (showIcon)
                Container(
                  width: 120.0,
                  height: 120.0,
                  decoration: BoxDecoration(
                    gradient: _getGradient(),
                    borderRadius: DS.borderRadiusFull,
                    boxShadow: [
                      BoxShadow(
                        color: _getBackgroundColor().withValues(alpha: 0.3),
                        blurRadius: 24,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Icon(
                    icon ?? _getDefaultIcon(),
                    size: DS.iconSize3xl,
                    color: DS.brandPrimaryConst,
                  ),
                ),
              const SizedBox(height: DS.spacing32),
              // 错误标题
              Text(
                title ?? _getDefaultTitle(),
                style: TextStyle(
                  fontSize: DS.fontSize2xl,
                  fontWeight: DS.fontWeightBold,
                  color: DS.neutral900,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.spacing12),
              // 错误消息
              Text(
                message,
                style: TextStyle(
                  fontSize: DS.fontSizeBase,
                  color: DS.neutral600,
                  height: DS.lineHeightNormal,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.spacing32),
              // 操作按钮
              if (actions != null)
                ...actions!
              else if (onRetry != null)
                CustomButton.primary(
                  text: _getRetryText(),
                  onPressed: onRetry,
                  icon: Icons.refresh_rounded,
                  customGradient: _getGradient(),
                ),
            ],
          ),
        ),
      );

  Widget _buildErrorBanner(BuildContext context) => Container(
        width: double.infinity,
        decoration: BoxDecoration(
          gradient: _getGradient(),
          boxShadow: DS.shadowMd,
        ),
        child: Material(
          color: DS.neutral0.withValues(alpha: 0),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing12,
            ),
            child: Row(
              children: [
                // 图标
                Icon(
                  icon ?? _getDefaultIcon(),
                  color: DS.brandPrimaryConst,
                  size: DS.iconSizeBase,
                ),
                const SizedBox(width: DS.spacing12),
                // 内容
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (title != null) ...[
                        Text(
                          title!,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            fontWeight: DS.fontWeightSemibold,
                            color: DS.brandPrimaryConst,
                          ),
                        ),
                        const SizedBox(height: DS.spacing4),
                      ],
                      Text(
                        message,
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          color: DS.brandPrimaryConst,
                        ),
                      ),
                    ],
                  ),
                ),
                // 关闭按钮
                if (onClose != null) ...[
                  const SizedBox(width: DS.spacing12),
                  InkWell(
                    onTap: onClose,
                    borderRadius: BorderRadius.circular(DS.radius8),
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing4),
                      child: Icon(
                        Icons.close_rounded,
                        color: DS.brandPrimaryConst,
                        size: DS.iconSizeSm,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );

  Widget _buildInlineError(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: _getLightBackgroundColor(),
          border: Border.all(
            color: _getBackgroundColor().withValues(alpha: 0.3),
          ),
          borderRadius: DS.borderRadius12,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (showIcon) ...[
              Icon(
                icon ?? _getDefaultIcon(),
                color: _getBackgroundColor(),
                size: DS.iconSizeSm,
              ),
              const SizedBox(width: DS.spacing8),
            ],
            Expanded(
              child: Text(
                message,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: _getBackgroundColor(),
                  height: DS.lineHeightNormal,
                ),
              ),
            ),
          ],
        ),
      );
}

/// 网络错误页面
class NetworkErrorPage extends StatelessWidget {
  const NetworkErrorPage({
    super.key,
    this.onRetry,
  });
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (l10n == null) {
      return const SizedBox.shrink();
    }
    return CustomErrorWidget.page(
      message: l10n.errorConnectionFailed,
      context: context,
      icon: Icons.wifi_off_rounded,
      onRetry: onRetry,
    );
  }
}

/// 404错误页面
class NotFoundErrorPage extends StatelessWidget {
  const NotFoundErrorPage({
    super.key,
    this.onGoBack,
  });
  final VoidCallback? onGoBack;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (l10n == null) {
      return const SizedBox.shrink();
    }
    return CustomErrorWidget.page(
      message: l10n.errorNotFound,
      context: context,
      icon: Icons.search_off_rounded,
      severity: ErrorSeverity.warning,
      actions: [
        if (onGoBack != null)
          CustomButton.primary(
            text: l10n.back,
            onPressed: onGoBack,
            icon: Icons.arrow_back_rounded,
            customGradient: DS.warningGradient,
          ),
      ],
    );
  }
}

/// 服务器错误页面
class ServerErrorPage extends StatelessWidget {
  const ServerErrorPage({
    super.key,
    this.onRetry,
    this.errorMessage,
  });
  final VoidCallback? onRetry;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (l10n == null) {
      return const SizedBox.shrink();
    }
    return CustomErrorWidget.page(
      message: errorMessage ?? l10n.errorServerIssue,
      context: context,
      icon: Icons.cloud_off_rounded,
      onRetry: onRetry,
    );
  }
}
