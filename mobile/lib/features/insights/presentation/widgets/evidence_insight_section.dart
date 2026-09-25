import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/insights/presentation/providers/evidence_insight_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/evidence_insight_card.dart';

/// D-07 证据洞察区：洞察总览顶部的 evidence-driven 洞察卡列表。
///
/// - 每次进入现取（后端现算，纠正落库后重进即更新）；
/// - 无数据/加载中/出错 → 整区隐藏（不占位、不出无证据结论）；
/// - 证据深链走应用内路由。
class EvidenceInsightSection extends ConsumerWidget {
  const EvidenceInsightSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cardsAsync = ref.watch(evidenceInsightCardsProvider);
    return cardsAsync.maybeWhen(
      data: (cards) {
        if (cards.isEmpty) {
          return const SizedBox.shrink();
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.verified_outlined,
                    color: DS.brandPrimary, size: 18,),
                const SizedBox(width: DS.spacing8),
                Text(
                  context.l10n.eicSectionTitle,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.eicSectionSubtitle,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: DS.textSecondary, height: 1.52),
            ),
            const SizedBox(height: DS.spacing12),
            for (final card in cards) ...[
              EvidenceInsightCardWidget(
                card: card,
                onOpenDeepLink: (link) => unawaitedPush(context, link),
              ),
              const SizedBox(height: DS.spacing12),
            ],
          ],
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }

  /// 深链跳转：路由缺失等异常不阻断洞察区本身（诚实失败：留日志不 crash）。
  void unawaitedPush(BuildContext context, String link) {
    unawaited(_push(context, link));
  }

  Future<void> _push(BuildContext context, String link) async {
    try {
      await context.push(link);
    } on Object catch (error) {
      FlutterError.reportError(
        FlutterErrorDetails(
          exception: error,
          library: 'insights',
          context: ErrorDescription('evidence deep link: $link'),
        ),
      );
    }
  }
}
