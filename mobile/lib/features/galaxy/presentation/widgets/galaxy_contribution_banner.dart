import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';

class GalaxyContributionBanner extends StatelessWidget {
  const GalaxyContributionBanner({
    required this.isDarkMode,
    required this.stats,
    super.key,
    this.isLoading = false,
  });

  const GalaxyContributionBanner.loading({
    required this.isDarkMode,
    super.key,
  })  : stats = UserGalaxyContribution.empty,
        isLoading = true;

  final bool isDarkMode;
  final UserGalaxyContribution stats;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final surface = isDarkMode
        ? const Color(0xCC0F1728)
        : DS.neutral0.withValues(alpha: 0.94);
    final border =
        (isDarkMode ? DS.neutral0 : DS.neutral900).withValues(alpha: 0.08);
    final foreground = isDarkMode ? DS.neutral0 : const Color(0xFF111827);
    final secondary = foreground.withValues(alpha: 0.68);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isLoading
            ? null
            : () => showSensoryModalBottomSheet<void>(
                  context: context,
                  isScrollControlled: true,
                  builder: (_) => GalaxyContributionDetailSheet(
                    stats: stats,
                    isDarkMode: isDarkMode,
                  ),
                ),
        borderRadius: BorderRadius.circular(22),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: surface,
            borderRadius: BorderRadius.circular(22),
            border: Border.all(color: border),
            boxShadow: [
              BoxShadow(
                color:
                    DS.galaxyShadow.withValues(alpha: isDarkMode ? 0.18 : 0.08),
                blurRadius: 24,
                offset: const Offset(0, 14),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: isLoading
                ? Row(
                    children: [
                      SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: foreground,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          context.l10n.galaxyContribLoading,
                          style: TextStyle(
                            color: foreground,
                            fontSize: 14,
                            fontWeight: DS.fontWeightSemibold,
                          ),
                        ),
                      ),
                    ],
                  )
                : stats.isEmpty
                    ? Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.l10n.galaxyContribStartLearning,
                            style: TextStyle(
                              color: foreground,
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            context.l10n.galaxyContribIntro,
                            style: TextStyle(
                              color: secondary,
                              fontSize: 13,
                              height: 1.45,
                            ),
                          ),
                        ],
                      )
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: 10,
                            runSpacing: 10,
                            children: [
                              _ContributionMetricPill(
                                label: context.l10n.galaxyContribFirstLight,
                                count: stats.firstActivationCount,
                                foreground: foreground,
                                background: foreground.withValues(alpha: 0.08),
                              ),
                              _ContributionMetricPill(
                                label: context.l10n.galaxyContribErrorFix,
                                count: stats.errorRepairedCount,
                                foreground: foreground,
                                background: foreground.withValues(alpha: 0.08),
                              ),
                              _ContributionMetricPill(
                                label: context.l10n.galaxyContribChatUpdate,
                                count: stats.conversationUpdatedCount,
                                foreground: foreground,
                                background: foreground.withValues(alpha: 0.08),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            context.l10n.galaxyContribTapDetails,
                            style: TextStyle(
                              color: secondary,
                              fontSize: 12,
                              fontWeight: DS.fontWeightSemibold,
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

class _ContributionMetricPill extends StatelessWidget {
  const _ContributionMetricPill({
    required this.label,
    required this.count,
    required this.foreground,
    required this.background,
  });

  final String label;
  final int count;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: foreground.withValues(alpha: 0.08),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: foreground.withValues(alpha: 0.72),
                  fontSize: 11,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: 2),
              SparkleCountUp(
                end: count,
                suffix: context.l10n.galaxyContribNodesSuffix,
                style: TextStyle(
                  color: foreground,
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      );
}

class GalaxyContributionDetailSheet extends StatelessWidget {
  const GalaxyContributionDetailSheet({
    required this.stats,
    required this.isDarkMode,
    super.key,
  });

  final UserGalaxyContribution stats;
  final bool isDarkMode;

  @override
  Widget build(BuildContext context) {
    final foreground = isDarkMode ? DS.neutral0 : const Color(0xFF111827);
    final secondary = foreground.withValues(alpha: 0.68);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 4,
                decoration: BoxDecoration(
                  color: foreground.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              context.l10n.galaxyContribMyDetails,
              style: TextStyle(
                color: foreground,
                fontSize: 20,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              context.l10n.galaxyContribDetailIntro,
              style: TextStyle(
                color: secondary,
                fontSize: 13,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 18),
            ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: MediaQuery.sizeOf(context).height * 0.62,
              ),
              child: ListView(
                shrinkWrap: true,
                children: [
                  _ContributionSection(
                    title: context.l10n.galaxyContribFirstLearnTitle,
                    emptyText: context.l10n.galaxyContribFirstLearnEmpty,
                    items: stats.firstActivatedNodes,
                    foreground: foreground,
                    secondary: secondary,
                  ),
                  const SizedBox(height: 16),
                  _ContributionSection(
                    title: context.l10n.galaxyContribChatCorrectionTitle,
                    emptyText: context.l10n.galaxyContribChatCorrectionEmpty,
                    items: stats.conversationUpdatedNodes,
                    foreground: foreground,
                    secondary: secondary,
                  ),
                  const SizedBox(height: 16),
                  _ContributionSection(
                    title: context.l10n.galaxyContribReviewTitle,
                    emptyText: context.l10n.galaxyContribReviewEmpty,
                    items: stats.errorRepairedNodes,
                    foreground: foreground,
                    secondary: secondary,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ContributionSection extends StatelessWidget {
  const _ContributionSection({
    required this.title,
    required this.emptyText,
    required this.items,
    required this.foreground,
    required this.secondary,
  });

  final String title;
  final String emptyText;
  final List<GalaxyContributionNodeItem> items;
  final Color foreground;
  final Color secondary;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: foreground,
              fontSize: 15,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 10),
          if (items.isEmpty)
            Text(
              emptyText,
              style: TextStyle(
                color: secondary,
                fontSize: 13,
              ),
            )
          else
            ...items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: foreground.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: foreground.withValues(alpha: 0.08),
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            item.nodeName,
                            style: TextStyle(
                              color: foreground,
                              fontSize: 14,
                              fontWeight: DS.fontWeightSemibold,
                            ),
                          ),
                        ),
                        Text(
                          item.masteryDelta > 0
                              ? '+${item.masteryDelta}'
                              : '${item.masteryDelta}',
                          style: TextStyle(
                            color: foreground.withValues(alpha: 0.76),
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      );
}
