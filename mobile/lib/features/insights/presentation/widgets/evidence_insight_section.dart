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
/// - V4-U13 三态分别呈现（SCREEN_FAMILIES「没有数据就说明尚未形成结论」）：
///   无数据（schema 合法零卡）→ 显式一行「还没有可分析的记录」；契约版本
///   不支持 / 加载中 / 出错 → 整区隐藏（不占位、不伪造契约字段、不出无证据
///   结论）——隐藏与无数据是不同状态，绝不互相冒充；
/// - 证据深链走应用内路由。
class EvidenceInsightSection extends ConsumerWidget {
  const EvidenceInsightSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feedAsync = ref.watch(evidenceInsightFeedProvider);
    return feedAsync.maybeWhen(
      data: (feed) {
        if (feed.isUnsupported) {
          // 契约版本门 fail-closed：旧后端/未知契约 → 不渲染（与无数据互斥）。
          return const SizedBox.shrink();
        }
        if (feed.isNoData) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _sectionHeader(context),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.eicEmptyNoData,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: DS.textSecondary, height: 1.52),
              ),
            ],
          );
        }
        if (!feed.isReady || feed.cards.isEmpty) {
          return const SizedBox.shrink();
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionHeader(context),
            const SizedBox(height: DS.spacing4),
            Text(
              context.l10n.eicSectionSubtitle,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: DS.textSecondary, height: 1.52),
            ),
            const SizedBox(height: DS.spacing12),
            for (final card in feed.cards) ...[
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

  Widget _sectionHeader(BuildContext context) => Row(
        children: [
          Icon(
            Icons.verified_outlined,
            color: DS.brandPrimary,
            size: 18,
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              context.l10n.eicSectionTitle,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ),
        ],
      );

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
