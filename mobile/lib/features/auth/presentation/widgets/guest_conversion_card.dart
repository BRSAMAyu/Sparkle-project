import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_conversion_provider.dart';

/// N40（A-SPEC7 §4）· 访客唯一转化点引导卡（价值回顾形）。
///
/// 形制：SparkleCard 家族卡形 + core/design 令牌（取色走 context.colors、
/// 字阶走 context.typo、间距走 DS.spacing 档），内联非弹窗——挂载点为
/// home（访客落地面）与 chat（N47 增补的 chatHeaderPanels 事件横幅槽，
/// 挂载处另加「非流式中」守卫），进行中任务时不可见
/// （[guestConversionVisibleProvider] 守门）。克制红线：
/// - 同会话最多一次（点掉/点击注册后本会话硬关）；
/// - 点掉持久挂起直到下个价值信号（「暂不」→ dismissUntilNextValueSignal）；
/// - 文案为价值回顾形（进度已保存 → 注册同步），不是恐吓/骚扰式注册弹窗。
class GuestConversionCard extends ConsumerWidget {
  const GuestConversionCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final visible = ref.watch(guestConversionVisibleProvider);
    if (!visible) return const SizedBox.shrink();

    final colors = context.colors;
    final typo = context.typo;
    final l10n = context.l10n;

    return SparkleCard(
      borderColor: colors.brandPrimary.withAlpha(64),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.spacing8),
                decoration: BoxDecoration(
                  color: colors.brandPrimary.withAlpha(30),
                  borderRadius: BorderRadius.circular(DS.radius12),
                ),
                child: Icon(
                  Icons.cloud_sync_outlined,
                  size: 20,
                  color: colors.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.guestConversionCardTitle,
                  style: typo.titleLarge.copyWith(color: colors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            l10n.guestConversionCardBody,
            style: typo.bodyMedium.copyWith(
              color: colors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Row(
            children: [
              Expanded(
                child: SparkleButton.primary(
                  label: l10n.guestConversionCardCta,
                  onPressed: () => _handleRegisterTap(context, ref),
                ),
              ),
              const SizedBox(width: DS.spacing8),
              SparkleButton.ghost(
                label: l10n.guestConversionCardDismiss,
                onPressed: () => unawaited(
                  ref
                      .read(guestConversionControllerProvider.notifier)
                      .dismissUntilNextValueSignal(),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _handleRegisterTap(BuildContext context, WidgetRef ref) {
    ref
        .read(guestConversionControllerProvider.notifier)
        .markConsumedByRegister();
    unawaited(context.push('/register'));
  }
}
