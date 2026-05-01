import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';

class ComebackBanner extends StatefulWidget {
  const ComebackBanner({
    required this.contextData,
    super.key,
    this.onDismiss,
    this.onContinue,
    this.onResumeCoreSession,
    this.onItemSelected,
  });

  final AuroraComebackContext contextData;
  final VoidCallback? onDismiss;
  final VoidCallback? onContinue;
  final VoidCallback? onResumeCoreSession;
  final ValueChanged<AuroraComebackItem>? onItemSelected;

  @override
  State<ComebackBanner> createState() => _ComebackBannerState();
}

class _ComebackBannerState extends State<ComebackBanner> {
  bool _skipEntranceAnimation = false;

  void _finishEntranceAnimation() {
    if (_skipEntranceAnimation || !mounted) {
      return;
    }
    setState(() {
      _skipEntranceAnimation = true;
    });
  }

  Widget _staggered({
    required int index,
    required Widget child,
  }) {
    if (_skipEntranceAnimation || context.reduceMotion) {
      return child;
    }

    return SparkleStaggerItem(
      index: index,
      initialDelay: const Duration(milliseconds: 100),
      stepDelay: const Duration(milliseconds: 100),
      offset: 0.025,
      child: child,
    );
  }

  @override
  Widget build(BuildContext context) {
    final contextData = widget.contextData;
    final title = contextData.title.isNotEmpty
        ? contextData.title
        : contextData.topicSummary.isNotEmpty
            ? contextData.topicSummary
            : context.l10n.chatContinueFromConversation;
    final body = contextData.message.isNotEmpty
        ? contextData.message
        : contextData.pendingQuestion;
    final items = contextData.unfinishedItems;

    return Listener(
      behavior: HitTestBehavior.translucent,
      onPointerDown: (_) => _finishEntranceAnimation(),
      child: Semantics(
        container: true,
        liveRegion: true,
        label: [title, body].where((text) => text.trim().isNotEmpty).join('. '),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 240),
          switchInCurve: Curves.easeOutCubic,
          switchOutCurve: Curves.easeInCubic,
          child: Container(
            key: ValueKey(
              '${contextData.comebackKind}:${contextData.lastActiveAt}',
            ),
            width: double.infinity,
            margin: const EdgeInsets.fromLTRB(
              DS.spacing16,
              DS.spacing8,
              DS.spacing16,
              DS.spacing8,
            ),
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfacePrimary.withValues(alpha: 0.94),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: DS.primaryBase.withValues(alpha: 0.18),
              ),
              boxShadow: [
                BoxShadow(
                  color: DS.primaryBase.withValues(alpha: 0.08),
                  blurRadius: 16,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: DS.primaryBase.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(
                        Icons.history_rounded,
                        size: 18,
                        color: DS.primaryBase,
                      ),
                    ),
                    const SizedBox(width: DS.spacing10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _staggered(
                            index: 0,
                            child: Text(
                              title,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                          ),
                          if (body.isNotEmpty) ...[
                            const SizedBox(height: DS.spacing4),
                            _staggered(
                              index: 1,
                              child: Text(
                                body,
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.36,
                                    ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (widget.onDismiss != null)
                      IconButton(
                        tooltip: MaterialLocalizations.of(context)
                            .closeButtonTooltip,
                        onPressed: widget.onDismiss,
                        icon: Icon(
                          Icons.close_rounded,
                          color: DS.textSecondary,
                        ),
                      ),
                  ],
                ),
                if (items.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing10),
                  _staggered(
                    index: 2,
                    child: Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: [
                        for (final item in items)
                          _ComebackItemChip(
                            item: item,
                            onTap: widget.onItemSelected == null
                                ? null
                                : () => widget.onItemSelected!(item),
                          ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: DS.spacing10),
                Row(
                  children: [
                    if (contextData.hasActiveCoreSession &&
                        widget.onResumeCoreSession != null)
                      TextButton.icon(
                        onPressed: widget.onResumeCoreSession,
                        icon: const Icon(Icons.play_arrow_rounded, size: 18),
                        label: Text(context.l10n.taskActionResume),
                      ),
                    const Spacer(),
                    TextButton.icon(
                      onPressed: widget.onContinue,
                      icon: const Icon(
                        Icons.chat_bubble_outline_rounded,
                        size: 18,
                      ),
                      label: Text(context.l10n.chatContinueInChat),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ComebackItemChip extends StatelessWidget {
  const _ComebackItemChip({
    required this.item,
    this.onTap,
  });

  final AuroraComebackItem item;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final icon = switch (item.type) {
      'core_session' => Icons.auto_awesome_rounded,
      'pending_question' => Icons.help_outline_rounded,
      'task' => Icons.playlist_add_check_rounded,
      _ => Icons.chat_bubble_outline_rounded,
    };
    final subtitle = item.subtitle.trim();
    return Semantics(
      button: onTap != null,
      label: [item.title, subtitle].where((text) => text.isNotEmpty).join('. '),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 280),
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary.withValues(alpha: 0.72),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: DS.borderSubtle.withValues(alpha: 0.7),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 16, color: DS.primaryBase),
              const SizedBox(width: DS.spacing6),
              Flexible(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      item.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: DS.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    if (subtitle.isNotEmpty)
                      Text(
                        subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: DS.textSecondary,
                            ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
