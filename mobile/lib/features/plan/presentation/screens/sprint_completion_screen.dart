import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_portfolio_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

class SprintCompletionScreen extends ConsumerStatefulWidget {
  const SprintCompletionScreen({
    required this.planId,
    this.subjectName = '',
    this.initialSummary,
    this.shareImageBuilder,
    this.shareLauncher,
    super.key,
  });

  final String planId;
  final String subjectName;
  final SprintCompletionSummary? initialSummary;

  @visibleForTesting
  final Future<File?> Function()? shareImageBuilder;

  @visibleForTesting
  final Future<void> Function(File imageFile, String shareText)? shareLauncher;

  @override
  ConsumerState<SprintCompletionScreen> createState() =>
      _SprintCompletionScreenState();
}

class _SprintCompletionScreenState
    extends ConsumerState<SprintCompletionScreen> {
  final GlobalKey _shareBoundaryKey = GlobalKey();
  SprintCompletionSummary? _loadedSummary;
  bool _isLoading = false;
  bool _isSharing = false;

  SprintCompletionSummary? get _summary =>
      widget.initialSummary ?? _loadedSummary;

  String get _subjectLabel {
    final subject = widget.subjectName.trim();
    return subject.isEmpty ? '7 天备考成果' : '$subject 7 天备考成果';
  }

  @override
  void initState() {
    super.initState();
    if (widget.initialSummary == null) {
      unawaited(_loadSummary());
    }
  }

  Future<void> _loadSummary() async {
    if (widget.planId.trim().isEmpty) return;
    setState(() => _isLoading = true);
    try {
      final result = await ref
          .read(examSprintRepositoryProvider)
          .checkSprintCompletion(widget.planId.trim());
      if (!mounted) return;
      setState(() {
        _loadedSummary = result.summary;
        _isLoading = false;
      });
      if (!result.completed || result.summary == null) {
        AppFeedback.warning(context, context.l10n.planSprintStillSummarizing);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      AppFeedback.error(context, e.toString());
    }
  }

  Future<void> _share() async {
    final summary = _summary;
    if (summary == null || _isSharing) return;

    setState(() => _isSharing = true);
    try {
      final imageFile =
          await (widget.shareImageBuilder?.call() ?? _captureShareImage());
      if (!mounted || imageFile == null) return;

      final shareText = _buildShareText(summary);
      final launcher = widget.shareLauncher;
      if (launcher != null) {
        await launcher(imageFile, shareText);
      } else {
        final result = await ref
            .read(universalShareServiceProvider)
            .shareToSystem(imageFile: imageFile, text: shareText);
        if (!mounted) return;
        if (result.isSuccess) {
          AppFeedback.success(context, context.l10n.planSprintShareOpened);
        } else if (result.error != null) {
          AppFeedback.error(context, result.error!);
        }
      }
    } finally {
      if (mounted) {
        setState(() => _isSharing = false);
      }
    }
  }

  Future<File?> _captureShareImage() async {
    await WidgetsBinding.instance.endOfFrame;
    final boundary = _shareBoundaryKey.currentContext?.findRenderObject()
        as RenderRepaintBoundary?;
    if (boundary == null) return null;

    final image = await boundary.toImage(pixelRatio: 3);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    if (byteData == null) return null;

    final tempDir = await getTemporaryDirectory();
    final file = File(
      '${tempDir.path}/sparkle_sprint_completion_${widget.planId}_${DateTime.now().millisecondsSinceEpoch}.png',
    );
    await file.writeAsBytes(byteData.buffer.asUint8List(), flush: true);
    return file;
  }

  String _buildShareText(SprintCompletionSummary summary) =>
      context.l10n.planSprintShareText(
      
      ;

  void _invalidateLinkedViews() {
    ref.invalidate(learningPortfolioProvider);
    ref.invalidate(weeklyGrowthNarrativeProvider);
    final planId = widget.planId.trim();
    if (planId.isNotEmpty) {
      ref.invalidate(planDetailProvider(planId));
    }
  }

  void _closeScreen() {
    _invalidateLinkedViews();
    RouteResilience.popOrGo(
      context,
      fallbackRoute: PlanRoutes.learningPortfolio,
    );
  }

  void _openPostExamReview() {
    final query = <String, String>{
      if (widget.planId.trim().isNotEmpty) 'plan_id': widget.planId.trim(),
      if (widget.subjectName.trim().isNotEmpty)
        'subject': widget.subjectName.trim(),
    };
    final uri = Uri(path: '/exam-sprint/review', queryParameters: query);
    unawaited(context.push(uri.toString()));
  }

  void _openLearningPortfolio() {
    _invalidateLinkedViews();
    context.go(PlanRoutes.learningPortfolio);
  }

  void _returnHome() {
    _invalidateLinkedViews();
    context.go(HomeRoutes.home);
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;

    return RouteResilienceScope(
      fallbackRoute: PlanRoutes.learningPortfolio,
      child: PopScope(
        onPopInvokedWithResult: (didPop, result) {
          _invalidateLinkedViews();
        },
        child: Scaffold(
          backgroundColor: DS.surfacePrimary,
          body: SparkleConfetti(
            play: summary != null,
            intensity: SparkleCelebrationIntensity.large,
            child: SafeArea(
              child: Stack(
                children: [
                  Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            DS.surfacePrimary,
                            DS.surfaceSecondary,
                            DS.success.withValues(alpha: 0.14),
                            DS.warning.withValues(alpha: 0.10),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    top: DS.spacing8,
                    left: DS.spacing8,
                    child: Tooltip(
                      message: context.l10n.planSprintBack,
                      child: SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        icon: const Icon(Icons.close_rounded),
                        onPressed: _closeScreen,
                      ),
                    ),
                  ),
                  if (_isLoading && summary == null)
                    const Center(child: LoadingIndicator())
                  else if (summary == null)
                    _CompletionUnavailable(onRetry: _loadSummary)
                  else
                    _CompletionContent(
                      subjectLabel: _subjectLabel,
                      summary: summary,
                      shareBoundaryKey: _shareBoundaryKey,
                      isSharing: _isSharing,
                      onShare: _share,
                      onPostExamReview: _openPostExamReview,
                      onViewPortfolio: _openLearningPortfolio,
                      onReturnHome: _returnHome,
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

class _CompletionContent extends StatelessWidget {
  const _CompletionContent({
    required this.subjectLabel,
    required this.summary,
    required this.shareBoundaryKey,
    required this.isSharing,
    required this.onShare,
    required this.onPostExamReview,
    required this.onViewPortfolio,
    required this.onReturnHome,
  });

  final String subjectLabel;
  final SprintCompletionSummary summary;
  final GlobalKey shareBoundaryKey;
  final bool isSharing;
  final VoidCallback onShare;
  final VoidCallback onPostExamReview;
  final VoidCallback onViewPortfolio;
  final VoidCallback onReturnHome;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 520;
          final maxWidth = compact ? double.infinity : 760.0;
          return Center(
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(
                DS.spacing20,
                compact ? DS.spacing56 : DS.spacing32,
                DS.spacing20,
                DS.spacing24,
              ),
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxWidth),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    RepaintBoundary(
                      key: shareBoundaryKey,
                      child: _ShareableCompletionCard(
                        subjectLabel: subjectLabel,
                        summary: summary,
                      ),
                    ),
                    const SizedBox(height: DS.spacing20),
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: DS.spacing12,
                      runSpacing: DS.spacing12,
                      children: [
                        SparkleButton(
                          key: const ValueKey('sprint-completion-share'),
                          label: context.l10n.planSprintShareAction,
                          icon: const Icon(Icons.ios_share_rounded),
                          loading: isSharing,
                          onPressed: isSharing ? null : onShare,
                        ),
                        SparkleButton.secondary(
                          label: context.l10n.planSprintRecordResult,
                          icon: const Icon(Icons.fact_check_outlined),
                          onPressed: onPostExamReview,
                        ),
                        SparkleButton.secondary(
                          label: context.l10n.planSprintBackHome,
                          icon: const Icon(Icons.home_outlined),
                          onPressed: onReturnHome,
                        ),
                        TextButton.icon(
                          onPressed: onViewPortfolio,
                          icon: const Icon(Icons.collections_bookmark_outlined),
                          label: Text(context.l10n.planSprintViewArchive),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      );
}

class _ShareableCompletionCard extends StatelessWidget {
  const _ShareableCompletionCard({
    required this.subjectLabel,
    required this.summary,
  });

  final String subjectLabel;
  final SprintCompletionSummary summary;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing24),
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(28),
          border: Border.all(color: DS.borderSubtle),
          boxShadow: DS.shadowXl,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(
                    Icons.workspace_premium_rounded,
                    color: DS.warning,
                    size: 28,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        subjectLabel,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: DS.textSecondary,
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        context.l10n.planSprintYourResult,
                        style:
                            Theme.of(context).textTheme.headlineSmall?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  height: 1.15,
                                ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing20),
            Text(
              context.l10n.planSprintResultSummary(summary.masteredNodesCount, summary.repairedErrorsCount, summary.completedTasksCount),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    height: 1.45,
                    fontWeight: FontWeight.w800,
                    color: DS.textPrimary,
                  ),
            ),
            const SizedBox(height: DS.spacing20),
            _CompletionMetricGrid(summary: summary),
            const SizedBox(height: DS.spacing20),
            _AreaInsightRow(
              icon: Icons.trending_up_rounded,
              label: context.l10n.planSprintStrongest,
              value: summary.strongestArea,
              color: DS.success,
            ),
            const SizedBox(height: DS.spacing10),
            _AreaInsightRow(
              icon: Icons.auto_fix_high_rounded,
              label: context.l10n.planSprintRoomToGrow,
              value: summary.growthArea,
              color: DS.info,
            ),
            const SizedBox(height: DS.spacing20),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                context.l10n.planSprintHashtag,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: DS.brandPrimary,
                      fontWeight: FontWeight.w900,
                    ),
              ),
            ),
          ],
        ),
      );
}

class _CompletionMetricGrid extends StatelessWidget {
  const _CompletionMetricGrid({required this.summary});

  final SprintCompletionSummary summary;

  @override
  Widget build(BuildContext context) {
    final metrics = [
      _MetricSpec(
        label: context.l10n.planSprintKnowledgeNodes,
        value: summary.masteredNodesCount,
        icon: Icons.hub_outlined,
        color: DS.success,
      ),
      _MetricSpec(
        label: context.l10n.planSprintErrorPatterns,
        value: summary.repairedErrorsCount,
        icon: Icons.healing_rounded,
        color: DS.warning,
      ),
      _MetricSpec(
        label: context.l10n.planSprintCompletedTasksLabel,
        value: summary.completedTasksCount,
        icon: Icons.task_alt_rounded,
        color: DS.info,
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth < 520 ? 1 : 3;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: metrics.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: DS.spacing10,
            mainAxisSpacing: DS.spacing10,
            mainAxisExtent: 116,
          ),
          itemBuilder: (context, index) => _AnimatedMetricCard(
            spec: metrics[index],
          ),
        );
      },
    );
  }
}

class _AnimatedMetricCard extends StatelessWidget {
  const _AnimatedMetricCard({required this.spec});

  final _MetricSpec spec;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing14),
        decoration: BoxDecoration(
          color: spec.color.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: spec.color.withValues(alpha: 0.24)),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: spec.color.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(spec.icon, color: spec.color, size: 22),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  TweenAnimationBuilder<int>(
                    tween: IntTween(begin: 0, end: spec.value),
                    duration: const Duration(milliseconds: 900),
                    curve: Curves.easeOutCubic,
                    builder: (context, value, _) => Text(
                      '$value',
                      style:
                          Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontWeight: FontWeight.w900,
                                color: DS.textPrimary,
                                height: 1,
                              ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing6),
                  Text(
                    spec.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: DS.textSecondary,
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _AreaInsightRow extends StatelessWidget {
  const _AreaInsightRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing14),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(width: DS.spacing10),
            Text(
              '$label：',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: DS.textSecondary,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            Expanded(
              child: Text(
                value,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: DS.textPrimary,
                    ),
              ),
            ),
          ],
        ),
      );
}

class _CompletionUnavailable extends StatelessWidget {
  const _CompletionUnavailable({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.hourglass_bottom_rounded, color: DS.info, size: 42),
              const SizedBox(height: DS.spacing12),
              Text(
                context.l10n.planSprintStillSummarizingTitle,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.planSprintWaitForSync,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleButton.secondary(
                label: context.l10n.planSprintRecheck,
                icon: const Icon(Icons.refresh_rounded),
                onPressed: onRetry,
              ),
            ],
          ),
        ),
      );
}

class _MetricSpec {
  const _MetricSpec({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  final String label;
  final int value;
  final IconData icon;
  final Color color;
}
