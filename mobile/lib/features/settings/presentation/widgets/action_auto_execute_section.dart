import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/settings/data/repositories/action_permission_repository.dart';

/// P-04 · 授权设置面：低风险 auto-execute 预授权（allowlist grant/revoke）.
///
/// 真源口径（不重建）：授权判定/revoke 时序/风险门全在引擎
/// （`/action-permissions`，`ActionPermissionService`）；本组件只做投影与
/// 命令转发——每次进出设置页重读真源（与服务端「授权不缓存」同口径），
/// 变更后 invalidate 重读，成功失败都诚实呈现（不假装成功）。
///
/// 红线呈现：
/// - 不可预授权类别（不可逆/词表外）显式标注，不藏在开关后面；
/// - 总开关关闭时逐类别开关即便开着也不会 auto（合成真值由服务端给出）；
/// - 变更失败 → SnackBar 提示 + 重读回退（乐观态零残留）。
class ActionAutoExecuteSection extends ConsumerWidget {
  const ActionAutoExecuteSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stateAsync = ref.watch(actionPermissionStateProvider);
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.actionAutoSectionTitle,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.xs),
          Text(
            context.l10n.actionAutoSectionDesc,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: DS.sm),
          stateAsync.when(
            loading: () => Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: DS.md),
                child: LoadingIndicator.circular(strokeWidth: 2),
              ),
            ),
            error: (error, _) => ListTile(
              leading: const Icon(Icons.error_outline),
              title: Text(context.l10n.actionAutoLoadFailed),
              trailing: SparkleButton(
                label: context.l10n.actionAutoRetry,
                variant: ButtonVariant.text,
                size: ButtonSize.small,
                onPressed: () =>
                    ref.invalidate(actionPermissionStateProvider),
              ),
            ),
            data: (state) => Column(
              children: [
                if (!state.masterGrant)
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.info_outline),
                    title: Text(
                      context.l10n.actionAutoMasterOffHint,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ...state.grantable.map(
                  (category) => SwitchListTile(
                    value: category.allowed,
                    onChanged: (value) => unawaited(
                      _toggle(ref, context, category.category, value),
                    ),
                    title: Text(_categoryLabel(context, category.category)),
                    subtitle: Text(
                      context.l10n.actionAutoReceiptHint,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ),
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.lock_outline),
                  title: Text(
                    context.l10n.actionAutoIneligibleHint,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// 授权面类别的人类标签（封闭词表内逐一映射；未知类别回退原名——不猜）。
  String _categoryLabel(BuildContext context, String category) {
    final l10n = context.l10n;
    return switch (category) {
      'task.update_status' => l10n.actionAutoCategoryTaskUpdateStatus,
      'task.update_fields' => l10n.actionAutoCategoryTaskUpdateFields,
      _ => category,
    };
  }

  Future<void> _toggle(
    WidgetRef ref,
    BuildContext context,
    String category,
    bool grant,
  ) async {
    // async gap 前捕获：l10n 文案与 messenger（use_build_context_synchronously）
    final messenger = ScaffoldMessenger.maybeOf(context);
    final notGrantableMessage = context.l10n.actionAutoNotGrantable;
    final changeFailedMessage = context.l10n.actionAutoChangeFailed;
    final repository = ref.read(actionPermissionRepositoryProvider);
    try {
      if (grant) {
        await repository.grant(category);
      } else {
        await repository.revoke(category);
      }
    } on DioException catch (e) {
      _showMessage(
        messenger,
        isPermissionRejected(e) ? notGrantableMessage : changeFailedMessage,
      );
    } on Exception catch (e) {
      _showMessage(messenger, UserFacingError.from(e));
    } finally {
      // 成败都重读真源：成功刷新到新状态，失败回退开关（零乐观残留）。
      ref.invalidate(actionPermissionStateProvider);
    }
  }

  void _showMessage(ScaffoldMessengerState? messenger, String message) {
    if (messenger == null) return;
    messenger.showSnackBar(SnackBar(content: Text(message)));
  }
}
