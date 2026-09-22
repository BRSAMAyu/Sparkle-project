import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/presentation/providers/squad_provider.dart';

/// D-COMM-5：把一张自己的错题分享到冲刺小队。
///
/// 客户端**只传 error_id**（内容一律服务端从错题记录取——不可伪造、
/// 不可选字段）；分享目标由用户在小队列表中选定。空列表诚实引导
/// （先创建/加入小队），不造假目标。
class ShareErrorToSquadDialog extends ConsumerStatefulWidget {
  const ShareErrorToSquadDialog({required this.errorId, super.key});

  final String errorId;

  @override
  ConsumerState<ShareErrorToSquadDialog> createState() =>
      _ShareErrorToSquadDialogState();
}

class _ShareErrorToSquadDialogState
    extends ConsumerState<ShareErrorToSquadDialog> {
  String? _selectedSquadId;
  bool _submitting = false;
  String? _errorMessage;

  Future<void> _submit() async {
    final squadId = _selectedSquadId;
    if (squadId == null || _submitting) {
      return;
    }
    setState(() {
      _submitting = true;
      _errorMessage = null;
    });
    try {
      await ref.read(squadRepositoryProvider).shareError(
            squadId,
            widget.errorId,
          );
      if (mounted) {
        AppFeedback.success(context, context.l10n.squadShareSuccess);
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _submitting = false;
          _errorMessage = context.l10n.squadShareFailed(error);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final squadsAsync = ref.watch(squadListProvider);
    final colors = context.colors;
    final typo = context.typo;
    final l10n = context.l10n;

    return AlertDialog(
      title: Text(l10n.squadShareDialogTitle),
      content: SizedBox(
        width: double.maxFinite,
        child: squadsAsync.when(
          loading: () => const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: SparkleCardSkeleton(),
          ),
          error: (Object error, StackTrace stackTrace) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                l10n.squadLoadFailed(error),
                style: typo.bodySmall.copyWith(color: colors.error),
              ),
              SizedBox(height: context.space.sm),
              SparkleButton(
                variant: ButtonVariant.outline,
                label: l10n.squadRetry,
                onPressed: () => ref.invalidate(squadListProvider),
              ),
            ],
          ),
          data: (List<SquadListItem> squads) {
            if (squads.isEmpty) {
              // 空态诚实：没有小队就没有分享目标——引导先组队。
              return Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.squadShareDialogEmpty,
                    style:
                        typo.bodyMedium.copyWith(color: colors.textSecondary),
                  ),
                  SizedBox(height: context.space.md),
                  SparkleButton(
                    key: const ValueKey('squad-share-empty-go-squads'),
                    variant: ButtonVariant.outline,
                    label: l10n.squadShareDialogGoSquads,
                    onPressed: () {
                      Navigator.of(context).pop(false);
                      unawaited(context.push(CommunityRoutes.squads));
                    },
                  ),
                ],
              );
            }
            return Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Flexible(
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: squads.length,
                    itemBuilder: (context, index) {
                      final squad = squads[index];
                      final selected = _selectedSquadId == squad.id;
                      return InkWell(
                        key: ValueKey('squad-share-option-${squad.id}'),
                        onTap: () =>
                            setState(() => _selectedSquadId = squad.id),
                        borderRadius: BorderRadius.circular(context.radius.sm),
                        child: Padding(
                          padding: EdgeInsets.symmetric(
                            vertical: context.space.sm,
                            horizontal: context.space.xs,
                          ),
                          child: Row(
                            children: [
                              Icon(
                                selected
                                    ? Icons.radio_button_checked
                                    : Icons.radio_button_off,
                                size: typo.labelLarge.fontSize ?? 14,
                                color: selected
                                    ? colors.brandPrimary
                                    : colors.textTertiary,
                              ),
                              SizedBox(width: context.space.sm),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      squad.name,
                                      style: typo.bodyMedium.copyWith(
                                        color: colors.textPrimary,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    Text(
                                      l10n.squadMembersCount(
                                        squad.memberCount,
                                        squad.maxMembers,
                                      ),
                                      style: typo.labelSmall.copyWith(
                                        color: colors.textTertiary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
                if (_errorMessage != null) ...[
                  SizedBox(height: context.space.sm),
                  Text(
                    _errorMessage!,
                    key: const ValueKey('squad-share-error-text'),
                    style: typo.bodySmall.copyWith(color: colors.error),
                  ),
                ],
              ],
            );
          },
        ),
      ),
      actions: [
        SparkleButton(
          variant: ButtonVariant.ghost,
          onPressed: () => Navigator.of(context).pop(false),
          disabled: _submitting,
          label: l10n.cancel,
        ),
        SparkleButton(
          key: const ValueKey('squad-share-confirm-button'),
          onPressed: (_submitting || _selectedSquadId == null)
              ? null
              : () => unawaited(_submit()),
          label: l10n.squadShareConfirm,
        ),
      ],
    );
  }
}
