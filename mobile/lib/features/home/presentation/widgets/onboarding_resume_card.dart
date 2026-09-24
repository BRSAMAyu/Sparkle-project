import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/user_routes.dart';

/// J-02（A-SPEC8B G1 软化）· 引导未完成的「继续引导」入口卡。
///
/// 语义：注册墙从全域硬重定向改为「放行 + 提醒」——未完成引导的注册用户
/// 可自由使用产品（价值先于画像），本卡在首页承担提醒职责：内联非弹窗，
/// 单击进入 persona 引导（skip 链到建模访谈原样保留）。
///
/// 可见性（与 M6-07 语义对齐）：
/// - 仅注册用户（guest 恒 completed，走 N40 转化卡，互斥）；
/// - onboardingCompleted == true / null（同步未决）不显示；
/// - 完成引导后卡自然消失（provider 驱动，无第二持久状态）。
class OnboardingResumeCard extends ConsumerWidget {
  const OnboardingResumeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final onboardingCompleted = ref.watch(onboardingCompletedProvider);
    final isGuestUser = authState.user?.registrationSource == 'guest';
    final visible = authState.isAuthenticated &&
        authState.user != null &&
        !isGuestUser &&
        onboardingCompleted == false;
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
                  Icons.flag_circle_outlined,
                  size: 20,
                  color: colors.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.homeOnboardingResumeTitle,
                  style: typo.titleLarge.copyWith(color: colors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            l10n.homeOnboardingResumeSummary,
            style: typo.bodyMedium.copyWith(
              color: colors.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          SizedBox(
            width: double.infinity,
            // F-8（wt324 证据包）：首页唯一 Primary Action 归属 cockpit
            // 本卡 CTA 降为 ghost 档——仅降视觉权重（10% 表面色 tonal +
            // brandPrimary 文字，全既有令牌），可点性与跳转语义不变，
            // 消除与 cockpit「和 AI 定目标」的双深棕填充竞争。
            child: SparkleButton.ghost(
              label: l10n.homeOnboardingResumeCta,
              // 跳 persona 引导；完成后路由守卫按 completed 语义自然收敛回 home。
              onPressed: () => context.go(UserRoutes.personaOnboarding),
            ),
          ),
        ],
      ),
    );
  }
}
