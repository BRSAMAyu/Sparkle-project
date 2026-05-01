import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class ChatNewMessagesDivider extends StatelessWidget {
  const ChatNewMessagesDivider({super.key});

  @override
  Widget build(BuildContext context) {
    final label = context.l10n.chatNewMessagesDivider;
    return Semantics(
      label: label,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
        child: Row(
          children: [
            Expanded(
              child: Divider(
                height: 1,
                color: DS.primaryBase.withValues(alpha: 0.18),
              ),
            ),
            Container(
              margin: const EdgeInsets.symmetric(horizontal: DS.spacing8),
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: DS.primaryBase.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                label,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: DS.primaryBase,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ),
            Expanded(
              child: Divider(
                height: 1,
                color: DS.primaryBase.withValues(alpha: 0.18),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ChatHistoryInlineError extends StatelessWidget {
  const ChatHistoryInlineError({
    required this.message,
    super.key,
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: GraphiteCardSurface(
          borderColor: DS.error.withValues(alpha: 0.14),
          surfaceRole: SparkleSurfaceRole.card,
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error_outline_rounded, color: DS.error),
                const SizedBox(height: DS.sm),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
                if (onRetry != null) ...[
                  const SizedBox(height: DS.md),
                  SparkleButton(
                    label: context.l10n.chatRetryGeneric,
                    icon: const Icon(Icons.refresh_rounded),
                    onPressed: onRetry,
                    variant: ButtonVariant.secondary,
                  ),
                ],
              ],
            ),
          ),
        ),
      );
}

class ChatQuickActionChip extends StatefulWidget {
  const ChatQuickActionChip({
    required this.icon,
    required this.label,
    required this.color,
    required this.isNarrow,
    required this.onTap,
    super.key,
    this.subtitle,
  });

  final IconData icon;
  final String label;
  final String? subtitle;
  final Color color;
  final bool isNarrow;
  final VoidCallback onTap;

  @override
  State<ChatQuickActionChip> createState() => _ChatQuickActionChipState();
}

class ChatContextToggle extends StatelessWidget {
  const ChatContextToggle({
    required this.isExpanded,
    required this.reasoningLabel,
    required this.modeLabel,
    required this.planLabel,
    required this.onTap,
    super.key,
  });

  final bool isExpanded;
  final String reasoningLabel;
  final String modeLabel;
  final String planLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final labelColor =
        isDark ? DS.textPrimary.withValues(alpha: 0.92) : DS.textSecondary;
    final iconColor =
        isDark ? DS.secondaryLight.withValues(alpha: 0.92) : DS.textSecondary;
    final resolvedPlanLabel =
        planLabel.isEmpty ? context.l10n.chatPlanUnbound : planLabel;
    final semanticsLabel = '$reasoningLabel, $modeLabel, $resolvedPlanLabel';

    return Semantics(
      button: true,
      label: semanticsLabel,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: DS.borderRadius16,
          onTap: onTap,
          child: Ink(
            decoration: BoxDecoration(
              color: isDark
                  ? DS.surfaceTertiary.withValues(alpha: 0.92)
                  : DS.surfaceOverlay,
              borderRadius: DS.borderRadius16,
              border: Border.all(
                color: isDark
                    ? DS.borderStrong.withValues(alpha: 0.68)
                    : DS.borderSubtle,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing8,
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.tune_rounded,
                    size: DS.iconSizeSm,
                    color: iconColor,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      '$reasoningLabel · $modeLabel · $resolvedPlanLabel',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: DS.bodySmall.copyWith(
                        color: labelColor,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Icon(
                    isExpanded
                        ? Icons.keyboard_arrow_down_rounded
                        : Icons.keyboard_arrow_up_rounded,
                    size: DS.iconSizeSm,
                    color: iconColor,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class DailyStartupRetryBanner extends StatelessWidget {
  const DailyStartupRetryBanner({
    required this.isRetrying,
    required this.onRetry,
    super.key,
  });

  final bool isRetrying;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Semantics(
        liveRegion: true,
        label: context.l10n.chatLoadingDailyOverview,
        child: Container(
          margin: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing4,
            DS.spacing16,
            DS.spacing8,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: DS.warning.withValues(alpha: 0.08),
            borderRadius: DS.borderRadius12,
            border: Border.all(color: DS.warning.withValues(alpha: 0.22)),
          ),
          child: Row(
            children: [
              SizedBox.square(
                dimension: DS.iconSizeSm,
                child: isRetrying
                    ? CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(DS.warning),
                      )
                    : Icon(
                        Icons.hourglass_top_rounded,
                        size: DS.iconSizeSm,
                        color: DS.warning,
                      ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  context.l10n.chatLoadingDailyOverview,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: DS.warning,
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing4),
              IconButton(
                visualDensity: VisualDensity.compact,
                tooltip: context.l10n.chatRetryDailyOverview,
                onPressed: isRetrying ? null : onRetry,
                icon: Icon(
                  Icons.refresh_rounded,
                  size: DS.iconSizeSm,
                  color: isRetrying
                      ? DS.textSecondary.withValues(alpha: 0.45)
                      : DS.warning,
                ),
              ),
            ],
          ),
        ),
      );
}

class _ChatQuickActionChipState extends State<ChatQuickActionChip> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final backgroundColor = DS.surfaceTertiary;
    final labelColor = DS.textPrimary;
    final horizontalPadding = widget.isNarrow ? DS.spacing12 : DS.spacing16;
    final hasSubtitle =
        widget.subtitle != null && widget.subtitle!.trim().isNotEmpty;

    return Semantics(
      button: true,
      label: widget.label,
      hint: widget.subtitle,
      child: GestureDetector(
        onTapDown: (_) => setState(() => _isPressed = true),
        onTapUp: (_) => setState(() => _isPressed = false),
        onTapCancel: () => setState(() => _isPressed = false),
        onTap: widget.onTap,
        child: AnimatedScale(
          scale: _isPressed ? 0.95 : 1.0,
          duration: DS.durationFast,
          curve: DS.curveEaseOut,
          child: Container(
            constraints: BoxConstraints(
              minHeight: DS.touchTargetMinSize,
              minWidth: widget.isNarrow ? 0 : 168,
            ),
            padding: EdgeInsets.symmetric(
              horizontal: horizontalPadding,
              vertical: hasSubtitle ? DS.spacing10 : DS.spacing8,
            ),
            decoration: BoxDecoration(
              color: backgroundColor,
              borderRadius: DS.borderRadius20,
              border: Border.all(
                color: widget.color.withValues(alpha: _isPressed ? 0.6 : 0.3),
                width: _isPressed ? 1.5 : 1.0,
              ),
              boxShadow: [
                BoxShadow(
                  color: widget.color.withValues(alpha: _isPressed ? 0.2 : 0.1),
                  blurRadius: _isPressed ? 4 : 8,
                  offset: _isPressed ? const Offset(0, 2) : const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: hasSubtitle
                  ? CrossAxisAlignment.start
                  : CrossAxisAlignment.center,
              children: [
                Icon(
                  widget.icon,
                  size: DS.iconSizeSm,
                  color: widget.color,
                ),
                const SizedBox(width: DS.spacing8),
                Flexible(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.label,
                        style: TextStyle(
                          color: labelColor,
                          fontWeight: DS.fontWeightMedium,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (hasSubtitle) ...[
                        const SizedBox(height: DS.spacing2),
                        Text(
                          widget.subtitle!,
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                            height: 1.35,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
