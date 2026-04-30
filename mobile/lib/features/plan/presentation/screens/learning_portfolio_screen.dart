import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_portfolio_provider.dart';
import 'package:sparkle/features/user/user_routes.dart';

class LearningPortfolioScreen extends ConsumerStatefulWidget {
  const LearningPortfolioScreen({super.key});

  @override
  ConsumerState<LearningPortfolioScreen> createState() =>
      _LearningPortfolioScreenState();
}

class _LearningPortfolioScreenState
    extends ConsumerState<LearningPortfolioScreen> {
  GoRouter? _router;
  String? _lastObservedRoutePath;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _attachRouteRefreshListener();
  }

  @override
  void dispose() {
    _router?.routeInformationProvider.removeListener(
      _handleRouteVisibilityChanged,
    );
    super.dispose();
  }

  void _attachRouteRefreshListener() {
    final router = GoRouter.of(context);
    if (identical(_router, router)) {
      return;
    }
    _router?.routeInformationProvider.removeListener(
      _handleRouteVisibilityChanged,
    );
    _router = router;
    _lastObservedRoutePath = router.routeInformationProvider.value.uri.path;
    router.routeInformationProvider.addListener(_handleRouteVisibilityChanged);
  }

  void _handleRouteVisibilityChanged() {
    final path = _router?.routeInformationProvider.value.uri.path;
    final previousPath = _lastObservedRoutePath;
    _lastObservedRoutePath = path;
    if (!mounted ||
        path != PlanRoutes.learningPortfolio ||
        previousPath == PlanRoutes.learningPortfolio) {
      return;
    }

    ref.invalidate(learningPortfolioProvider);
  }

  Future<void> _refreshPortfolio() =>
      ref.refresh(learningPortfolioProvider.future);

  @override
  Widget build(BuildContext context) {
    ref.listen<AsyncValue<LearningPortfolioResult>>(
      learningPortfolioProvider,
      (previous, next) {
        next.whenOrNull(
          error: (error, _) {
            final previousMessage = (previous?.hasError ?? false)
                ? previous!.error.toString()
                : null;
            final nextMessage = error.toString();
            if (previousMessage == nextMessage) {
              return;
            }
            ScaffoldMessenger.of(context)
              ..hideCurrentSnackBar()
              ..showSnackBar(
                SparkleSnackBar.error(
                  context.l10n.planPortfolioLoadFailed(nextMessage),
                  onRetry: () => ref.invalidate(learningPortfolioProvider),
                  retryLabel: context.l10n.planPortfolioRetry,
                ),
              );
          },
        );
      },
    );

    final portfolioAsync = ref.watch(learningPortfolioProvider);

    return RouteResilienceScope(
      fallbackRoute: UserRoutes.profile,
      child: SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => RouteResilience.popOrGo(
              context,
              fallbackRoute: UserRoutes.profile,
            ),
          ),
          title: Text(context.l10n.planMyArchive),
        ),
        child: ContentConstraint(
          child: RefreshIndicator(
            onRefresh: _refreshPortfolio,
            child: portfolioAsync.when(
              loading: () => const _ScrollableStateFill(
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (Object error, StackTrace stackTrace) =>
                  _ScrollableStateFill(
                child: _PortfolioErrorState(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(learningPortfolioProvider),
                ),
              ),
              data: (LearningPortfolioResult portfolio) {
                if (portfolio.isEmpty) {
                  return _ScrollableStateFill(
                    child: _PortfolioEmptyState(
                      onStartSprint: () =>
                          context.push(PlanRoutes.examSprintSetup),
                    ),
                  );
                }

                return ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(DS.spacing16),
                  children: [
                    _PortfolioSummaryCard(portfolio: portfolio),
                    const SizedBox(height: DS.spacing16),
                    _PortfolioGroupSection(
                      title: context.l10n.planPortfolioActiveTitle,
                      subtitle: context.l10n.planPortfolioActiveSubtitle,
                      entries: portfolio.activeEntries,
                    ),
                    const SizedBox(height: DS.spacing16),
                    _PortfolioGroupSection(
                      title: context.l10n.planPortfolioCompletedTitle,
                      subtitle: context.l10n.planPortfolioCompletedSubtitle,
                      entries: portfolio.completedEntries,
                    ),
                    if (portfolio.hasMore) ...[
                      const SizedBox(height: DS.spacing16),
                      _LoadMoreButton(
                        onLoadMore: () => ref
                            .read(learningPortfolioProvider.notifier)
                            .loadMore(),
                      ),
                    ],
                    const SizedBox(height: DS.spacing16),
                    _PortfolioGroupSection(
                      title: context.l10n.planPortfolioPlannedTitle,
                      subtitle: context.l10n.planPortfolioPlannedSubtitle,
                      entries: portfolio.plannedEntries,
                    ),
                    const SizedBox(height: DS.spacing32),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _ScrollableStateFill extends StatelessWidget {
  const _ScrollableStateFill({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) => ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: constraints.maxHeight,
              child: child,
            ),
          ],
        ),
      );
}

class _PortfolioSummaryCard extends StatelessWidget {
  const _PortfolioSummaryCard({required this.portfolio});

  final LearningPortfolioResult portfolio;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color(0xFFE7F4EA),
            Color(0xFFF7EFE3),
            Color(0xFFF7F8FC),
          ],
        ),
        border: Border.all(color: const Color(0xFFCED8CE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.planPortfolioTotalMastery,
            style: DS.labelLarge.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '${portfolio.totalMasteredNodes}',
            style: DS.displayLarge.copyWith(
              fontWeight: DS.fontWeightBold,
              color: const Color(0xFF224434),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _SummaryPill(label: context.l10n.planPortfolioActivePill(portfolio.activeCount)),
              _SummaryPill(label: context.l10n.planPortfolioCompletedPill(portfolio.completedCount)),
              _SummaryPill(label: context.l10n.planPortfolioPlannedPill(portfolio.plannedCount)),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryPill extends StatelessWidget {
  const _SummaryPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.78),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFD7DFD7)),
      ),
      child: Text(
        label,
        style: DS.bodySmall.copyWith(
          color: DS.textPrimary,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }
}

class _PortfolioGroupSection extends StatelessWidget {
  const _PortfolioGroupSection({
    required this.title,
    required this.subtitle,
    required this.entries,
  });

  final String title;
  final String subtitle;
  final List<LearningPortfolioEntry> entries;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: DS.titleLarge.copyWith(fontWeight: DS.fontWeightBold),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          subtitle,
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing10),
        if (entries.isEmpty)
          GraphiteCardSurface(
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Text(
                context.l10n.planPortfolioEmptyGroup,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
            ),
          )
        else
          ...entries.map(
            (LearningPortfolioEntry entry) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing12),
              child: _PortfolioEntryCard(entry: entry),
            ),
          ),
      ],
    );
  }
}

class _PortfolioEntryCard extends StatelessWidget {
  const _PortfolioEntryCard({required this.entry});

  final LearningPortfolioEntry entry;

  @override
  Widget build(BuildContext context) {
    return GraphiteCardSurface(
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing10,
          ),
          childrenPadding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing16,
          ),
          title: Text(
            entry.subject.isEmpty ? entry.planName : entry.subject,
            style: DS.titleMedium.copyWith(fontWeight: DS.fontWeightBold),
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: DS.spacing6),
            child: Text(
              _statusLine(context, entry),
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
          ),
          trailing: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing10,
              vertical: DS.spacing8,
            ),
            decoration: BoxDecoration(
              color: const Color(0xFFF3F5F1),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFD8DED3)),
            ),
            child: Text(
              context.l10n.planPortfolioMasteryPercent(entry.masteredNodesCount),
              style: DS.labelLarge.copyWith(
                color: const Color(0xFF355543),
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ),
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                context.l10n.planPortfolioGalaxySummary,
                style: DS.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
            if ((entry.headline ?? '').trim().isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                entry.headline!,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
            ],
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                _DetailChip(label: _scoreLabel(context, entry)),
                _DetailChip(label: _modeLabel(context, entry.sprintMode)),
                if (entry.resultRating != null)
                  _DetailChip(label: context.l10n.planPortfolioResultRating(entry.resultRating!)),
                if (entry.selfRating != null)
                  _DetailChip(label: context.l10n.planPortfolioSelfRating(entry.selfRating!)),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            _DetailRow(
              title: context.l10n.planPortfolioWeakestTitle,
              content: _joinDetails(
                entry.weakestPoints.isNotEmpty
                    ? entry.weakestPoints
                    : <String>[
                        ...?[
                          entry.growthArea,
                        ].whereType<String>()
                      ],
                fallback: context.l10n.planPortfolioWeakestFallback,
              ),
            ),
            const SizedBox(height: DS.spacing10),
            _DetailRow(
              title: context.l10n.planPortfolioProudTitle,
              content: _joinDetails(
                entry.proudNodes.isNotEmpty
                    ? entry.proudNodes
                    : <String>[
                        ...?[
                          entry.strongestArea,
                        ].whereType<String>()
                      ],
                fallback: context.l10n.planPortfolioProudFallback,
              ),
            ),
            if ((entry.resultDescription ?? '').trim().isNotEmpty) ...[
              const SizedBox(height: DS.spacing10),
              _DetailRow(
                title: context.l10n.planPortfolioGradeNotes,
                content: entry.resultDescription!,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DetailChip extends StatelessWidget {
  const _DetailChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFF7F4EC),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFE2D8C4)),
      ),
      child: Text(
        label,
        style: DS.bodySmall.copyWith(
          color: const Color(0xFF6A5740),
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.title,
    required this.content,
  });

  final String title;
  final String content;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: DS.labelLarge.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          content,
          style: DS.bodyMedium.copyWith(color: DS.textSecondary),
        ),
      ],
    );
  }
}

class _PortfolioEmptyState extends StatelessWidget {
  const _PortfolioEmptyState({required this.onStartSprint});

  final VoidCallback onStartSprint;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5EF),
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0xFFD5DED1)),
              ),
              child: const Icon(
                Icons.library_books_outlined,
                size: 34,
                color: Color(0xFF5A7563),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.planPortfolioNoArchiveTitle,
              textAlign: TextAlign.center,
              style: DS.titleLarge.copyWith(fontWeight: DS.fontWeightBold),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.planPortfolioNoArchiveSubtitle,
              textAlign: TextAlign.center,
              style: DS.bodyMedium.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing20),
            SparkleButton(
              onPressed: onStartSprint,
              label: context.l10n.planPortfolioCreateSprint,
            ),
          ],
        ),
      ),
    );
  }
}

class _PortfolioErrorState extends StatelessWidget {
  const _PortfolioErrorState({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              context.l10n.planPortfolioLoadFailed(message),
              textAlign: TextAlign.center,
              style: DS.bodyMedium.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing16),
            SparkleButton(
              label: context.l10n.planPortfolioRetry,
              icon: const Icon(Icons.refresh_rounded),
              onPressed: onRetry,
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadMoreButton extends StatelessWidget {
  const _LoadMoreButton({required this.onLoadMore});

  final VoidCallback onLoadMore;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SparkleButton(
        onPressed: onLoadMore,
        label: context.l10n.planPortfolioLoadMore,
        icon: const Icon(Icons.expand_more),
      ),
    );
  }
}

String _statusLine(BuildContext context, LearningPortfolioEntry entry) {
  final mode = _modeLabel(context, entry.sprintMode);
  if (entry.isCompleted) {
    final completedOn = _formatDate(context, entry.completedAt ?? entry.targetDate);
    return '$mode（已完成，$completedOn）';
  }
  if (entry.isActive) {
    final totalDays = _totalDays(entry);
    final currentDay = _currentDay(entry, totalDays);
    final remainingDays = totalDays == null ? null : (totalDays - currentDay);
    if (remainingDays != null) {
      return '$mode · 进行中（第 $currentDay 天，还剩 $remainingDays 天）';
    }
    return '$mode · 进行中';
  }
  return '$mode · 计划中';
}

String _scoreLabel(BuildContext context, LearningPortfolioEntry entry) {
  if ((entry.resultDescription ?? '').trim().isNotEmpty) {
    return entry.resultDescription!;
  }
  if (entry.currentScore != null) {
    return context.l10n.planPortfolioScoreLabel(entry.currentScore!.round());
  }
  return context.l10n.planPortfolioScorePending;
}

String _modeLabel(BuildContext context, String? sprintMode) {
  switch (sprintMode) {
    case 'last_24h_cram':
      return context.l10n.planMode24h;
    case 'seven_day_survival':
      return context.l10n.planMode7Day;
    case 'fourteen_day_build_and_retrieve':
      return context.l10n.planMode14Day;
    case 'standard_exam_sprint':
      return context.l10n.planModeStandard;
    default:
      return context.l10n.planModeExam;
  }
}

String _formatDate(BuildContext context, DateTime? value) {
  if (value == null) {
    return context.l10n.planDateTbd;
  }
  final local = value.toLocal();
  final year = local.year.toString().padLeft(4, '0');
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  return '$year-$month-$day';
}

String _joinDetails(List<String> values, {required String fallback}) {
  final sanitized = values
      .map((String item) => item.trim())
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
  if (sanitized.isEmpty) {
    return fallback;
  }
  return sanitized.join('、');
}

int? _totalDays(LearningPortfolioEntry entry) {
  if (entry.startedAt == null || entry.targetDate == null) {
    return null;
  }
  return entry.targetDate!
          .difference(
            DateTime(
              entry.startedAt!.year,
              entry.startedAt!.month,
              entry.startedAt!.day,
            ),
          )
          .inDays +
      1;
}

int _currentDay(LearningPortfolioEntry entry, int? totalDays) {
  if (totalDays == null) {
    return 1;
  }
  if (entry.progress <= 0) {
    return 1;
  }
  final current = (entry.progress * totalDays).round();
  if (current < 1) {
    return 1;
  }
  if (current > totalDays) {
    return totalDays;
  }
  return current;
}
