import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/chat_continuity_banner.dart';
import 'package:sparkle/core/widgets/mirofish_stage_header.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/mirofish/presentation/support/mirofish_milestone_service.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/features/theater/presentation/providers/theater_provider.dart';
import 'package:sparkle/features/theater/presentation/widgets/knowledge_theater_graph.dart';

class KnowledgeTheaterScreen extends ConsumerStatefulWidget {
  const KnowledgeTheaterScreen({
    super.key,
    this.initialTopic,
    this.initialTargetNodeId,
    this.initialPredictionId,
    this.initialRouteId,
    this.initialSourceChatSessionId,
    this.initialSimulationSessionId,
  });

  final String? initialTopic;
  final String? initialTargetNodeId;
  final String? initialPredictionId;
  final String? initialRouteId;
  final String? initialSourceChatSessionId;
  final String? initialSimulationSessionId;

  @override
  ConsumerState<KnowledgeTheaterScreen> createState() =>
      _KnowledgeTheaterScreenState();
}

enum _TheaterWorkbenchTab { graph, paths, discussion, calibration }

class _KnowledgeTheaterScreenState
    extends ConsumerState<KnowledgeTheaterScreen> {
  late final TextEditingController _topicController;
  late final ProviderSubscription<TheaterState> _theaterSubscription;
  late final TheaterNotifier _theaterNotifier;
  Timer? _timelinePlaybackTimer;
  bool _showCelebration = false;
  bool _playCelebration = false;
  bool _isTimelinePlaying = false;
  bool _disclaimerDismissed = false;
  String? _selectedNodeId;
  _TheaterWorkbenchTab _activeWorkbenchTab = _TheaterWorkbenchTab.graph;

  String _buildSimulationRoute(TheaterPathOption route) {
    final prediction = ref.read(theaterProvider).prediction;
    final query = <String, String>{
      'topic': prediction?.topic ?? _topicController.text.trim(),
      'scenario_key': 'what_if_path',
      'prediction_id': prediction?.predictionId ?? '',
      'route_id': route.id,
      'route_title': route.title,
      'target_name': prediction?.targetName ?? '',
      if ((widget.initialSourceChatSessionId ?? '').trim().isNotEmpty)
        'source_chat_session_id': widget.initialSourceChatSessionId!.trim(),
      if ((widget.initialSimulationSessionId ?? '').trim().isNotEmpty)
        'simulation_session_id': widget.initialSimulationSessionId!.trim(),
    }..removeWhere((key, value) => value.trim().isEmpty);
    return Uri(
      path: SimulationRoutes.simulation,
      queryParameters: query,
    ).toString();
  }

  @override
  void initState() {
    super.initState();
    _topicController = TextEditingController(text: widget.initialTopic ?? '');
    _theaterNotifier = ref.read(theaterProvider.notifier);
    _theaterSubscription = ref.listenManual<TheaterState>(
      theaterProvider,
      (previous, next) {
        final previousPlanId = previous?.adoptionResult?.planId;
        final nextPlanId = next.adoptionResult?.planId;
        if (nextPlanId == null || nextPlanId == previousPlanId) {
        } else {
          _triggerAdoptionCelebration();
        }

        final previousPredictionId = previous?.prediction?.predictionId;
        final nextPrediction = next.prediction;
        if (nextPrediction != null &&
            nextPrediction.predictionId != previousPredictionId) {
          _selectedNodeId = nextPrediction.graphNodes.isEmpty
              ? null
              : nextPrediction.graphNodes.first.id;
          _activeWorkbenchTab = _TheaterWorkbenchTab.graph;
          _disclaimerDismissed = false;
          unawaited(_celebrateTheaterMilestone(nextPrediction));
        }
      },
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        ref.read(simulationProvider.notifier).loadRecommendedSeeds(
              scenarioKey: 'study_group',
              silent: true,
            ),
      );
      if ((widget.initialPredictionId ?? '').trim().isNotEmpty) {
        unawaited(
          ref.read(theaterProvider.notifier).loadPredictionById(
                widget.initialPredictionId!.trim(),
                preferredRouteId: widget.initialRouteId?.trim(),
              ),
        );
      } else if ((widget.initialTopic ?? '').trim().isNotEmpty) {
        unawaited(_generatePrediction(widget.initialTopic!.trim()));
      }
    });
  }

  @override
  void dispose() {
    _timelinePlaybackTimer?.cancel();
    _theaterSubscription.close();
    _topicController.dispose();
    _theaterNotifier.clearOverlay();
    super.dispose();
  }

  Future<void> _generatePrediction(String topic) async {
    if (topic.trim().isEmpty) {
      return;
    }
    _stopTimelinePlayback();
    setState(() {
      _activeWorkbenchTab = _TheaterWorkbenchTab.graph;
    });
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    await ref.read(theaterProvider.notifier).generatePrediction(
          topic: topic.trim(),
          targetNodeId: widget.initialTargetNodeId,
          simulationSessionId: widget.initialSimulationSessionId,
        );
  }

  void _toggleTimelinePlayback() {
    final prediction = ref.read(theaterProvider).prediction;
    final timeline = prediction?.timeline ?? const <TheaterTimelineFrame>[];
    if (timeline.isEmpty) {
      return;
    }
    if (_isTimelinePlaying) {
      _stopTimelinePlayback();
      return;
    }
    if (ref.read(theaterProvider).timelineIndex >= timeline.length - 1) {
      ref.read(theaterProvider.notifier).setTimelineIndex(0);
    }
    setState(() => _isTimelinePlaying = true);
    _timelinePlaybackTimer?.cancel();
    _timelinePlaybackTimer = Timer.periodic(
      const Duration(milliseconds: 1400),
      (_) => _advanceTimelinePlayback(),
    );
  }

  void _advanceTimelinePlayback() {
    final state = ref.read(theaterProvider);
    final timeline =
        state.prediction?.timeline ?? const <TheaterTimelineFrame>[];
    if (timeline.isEmpty) {
      _stopTimelinePlayback();
      return;
    }
    final currentIndex = state.timelineIndex.clamp(0, timeline.length - 1);
    if (currentIndex >= timeline.length - 1) {
      _stopTimelinePlayback();
      return;
    }
    ref.read(theaterProvider.notifier).setTimelineIndex(currentIndex + 1);
  }

  void _resetTimelinePlayback() {
    _stopTimelinePlayback();
    ref.read(theaterProvider.notifier).setTimelineIndex(0);
  }

  void _stopTimelinePlayback() {
    _timelinePlaybackTimer?.cancel();
    _timelinePlaybackTimer = null;
    if (mounted && _isTimelinePlaying) {
      setState(() => _isTimelinePlaying = false);
    }
  }

  void _triggerAdoptionCelebration() {
    setState(() {
      _showCelebration = true;
      _playCelebration = true;
    });
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
    unawaited(
      Future<void>.delayed(const Duration(milliseconds: 1200)).then((_) {
        if (!mounted) {
          return;
        }
        setState(() => _playCelebration = false);
      }),
    );
    unawaited(
      Future<void>.delayed(const Duration(seconds: 3)).then((_) {
        if (!mounted) {
          return;
        }
        setState(() => _showCelebration = false);
      }),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(theaterProvider);
    final simulationState = ref.watch(simulationProvider);
    final route = state.selectedRoute;
    final prediction = state.prediction;
    final timeline = prediction?.timeline ?? const <TheaterTimelineFrame>[];
    final timelineIndex = state.timelineIndex.clamp(
      0,
      timeline.isEmpty ? 0 : timeline.length - 1,
    );
    final focusNodeIds = timeline.isNotEmpty
        ? timeline[timelineIndex].focusNodeIds
        : (route?.steps.map((step) => step.nodeId).take(3).toList() ??
            const <String>[]);

    return Scaffold(
      appBar: AppBar(
        title: Text(context.l10n.theaterTitle),
        actions: [
          IconButton(
            onPressed: prediction == null
                ? null
                : () => unawaited(_showTheaterShareSheet()),
            icon: const Icon(Icons.share_outlined),
          ),
          IconButton(
            onPressed: prediction == null ? null : () => context.go('/galaxy'),
            icon: const Icon(Icons.auto_graph_rounded),
          ),
        ],
      ),
      body: SparkleConfetti(
        play: _playCelebration,
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Theme.of(context)
                    .colorScheme
                    .surfaceContainerHighest
                    .withValues(alpha: 0.45),
                Theme.of(context).scaffoldBackgroundColor,
              ],
            ),
          ),
          child: Stack(
            children: [
              SafeArea(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    if (prediction == null) {
                      final introBody = _TheaterIntroState(
                        key: const ValueKey('theater-intro'),
                        isLoading: state.isLoading,
                        loadingStage: state.loadingStage,
                        latestSnapshot: state.snapshot,
                        suggestions: simulationState.recommendedSeeds,
                        error: state.error,
                        onStartFirstPrediction: () => unawaited(
                          _generatePrediction(_topicController.text),
                        ),
                        onRetry: () => unawaited(
                          _generatePrediction(_topicController.text),
                        ),
                        onChangeTarget: () {
                          _topicController.clear();
                          ref.read(theaterProvider.notifier).clearError();
                        },
                      );

                      final contentChildren = <Widget>[
                        if ((widget.initialSourceChatSessionId ?? '')
                            .trim()
                            .isNotEmpty) ...[
                          ChatContinuityBanner(
                            sourceChatSessionId:
                                widget.initialSourceChatSessionId!.trim(),
                            kind: ChatContinuityKind.journey,
                            subtitle: context.l10n.theaterContinuityBanner,
                          ),
                          const SizedBox(height: 16),
                        ],
                        _ComposerCard(
                          controller: _topicController,
                          isLoading: state.isLoading,
                          suggestions: simulationState.recommendedSeeds,
                          onSuggestionTap: (topic) {
                            _topicController.text = topic;
                            unawaited(_generatePrediction(topic));
                          },
                          onSubmit: () => unawaited(
                            _generatePrediction(_topicController.text),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ];

                      return ListView(
                        padding: EdgeInsets.fromLTRB(
                          16,
                          16,
                          16,
                          math.max(
                            24,
                            MediaQuery.of(context).padding.bottom + 16,
                          ),
                        ),
                        keyboardDismissBehavior:
                            ScrollViewKeyboardDismissBehavior.onDrag,
                        children: [
                          ...contentChildren,
                          introBody,
                        ],
                      );
                    }

                    return CustomScrollView(
                      keyboardDismissBehavior:
                          ScrollViewKeyboardDismissBehavior.onDrag,
                      slivers: [
                        SliverPadding(
                          padding: EdgeInsets.fromLTRB(
                            16,
                            12,
                            16,
                            math.max(
                              20,
                              MediaQuery.of(context).padding.bottom + 14,
                            ),
                          ),
                          sliver: SliverList(
                            delegate: SliverChildListDelegate([
                              if ((widget.initialSourceChatSessionId ?? '')
                                  .trim()
                                  .isNotEmpty) ...[
                                ChatContinuityBanner(
                                  sourceChatSessionId:
                                      widget.initialSourceChatSessionId!.trim(),
                                  kind: ChatContinuityKind.journey,
                                  subtitle: context.l10n.theaterContinuityBanner,
                                ),
                                const SizedBox(height: 12),
                              ],
                              GraphiteCardSurface(
                                surfaceRole: SparkleSurfaceRole.card,
                                padding: const EdgeInsets.all(14),
                                child: _TheaterImmersiveTopBar(
                                  topic: prediction.topic,
                                  targetName: prediction.targetName,
                                  targetResolutionMode:
                                      prediction.targetResolutionMode,
                                  semanticMatchCount:
                                      prediction.semanticMatches.length,
                                  selectedRoute: route,
                                  onOpenSettings: () => unawaited(
                                    _openSettingsSheet(
                                      prediction: prediction,
                                      state: state,
                                      simulationState: simulationState,
                                    ),
                                  ),
                                  onShare: () =>
                                      unawaited(_showTheaterShareSheet()),
                                  onOpenGalaxy:
                                      prediction.hasMappedGalaxyReferences
                                          ? () => context.go(GalaxyRoutes.home)
                                          : null,
                                ),
                              ),
                              if ((prediction.disclaimer ?? '')
                                      .trim()
                                      .isNotEmpty &&
                                  !_disclaimerDismissed) ...[
                                const SizedBox(height: 12),
                                _TheaterDisclaimerBanner(
                                  message: prediction.disclaimer!.trim(),
                                  onDismiss: () => setState(
                                      () => _disclaimerDismissed = true),
                                ),
                              ],
                              const SizedBox(height: 12),
                              if (constraints.maxWidth < 340 &&
                                  prediction.paths.isNotEmpty) ...[
                                _CompactRoutePreviewCard(
                                  selectedRoute: route ??
                                      prediction.paths.firstWhere(
                                        (item) =>
                                            item.id ==
                                            prediction.recommendedRouteId,
                                        orElse: () => prediction.paths.first,
                                      ),
                                  recommendedRouteId:
                                      prediction.recommendedRouteId,
                                  alternatives: prediction.paths
                                      .where(
                                        (item) =>
                                            item.id !=
                                            (route?.id ??
                                                prediction.recommendedRouteId),
                                      )
                                      .toList(),
                                  onOpenPathWorkbench: () {
                                    setState(
                                      () => _activeWorkbenchTab =
                                          _TheaterWorkbenchTab.paths,
                                    );
                                  },
                                ),
                                const SizedBox(height: 12),
                              ],
                              SizedBox(
                                height: math.max(
                                  520,
                                  constraints.maxHeight - 72,
                                ),
                                child: _PredictionView(
                                  key: ValueKey(prediction.predictionId),
                                  prediction: prediction,
                                  selectedRoute: route,
                                  timeline: timeline,
                                  timelineIndex: timelineIndex,
                                  focusNodeIds: focusNodeIds,
                                  selectedNodeId: _selectedNodeId,
                                  isTimelinePlaying: _isTimelinePlaying,
                                  recommendedRouteId:
                                      prediction.recommendedRouteId,
                                  whatIfResult: state.whatIfResult,
                                  snapshot: state.snapshot,
                                  adoptionResult: state.adoptionResult,
                                  accuracySummary: state.accuracySummary,
                                  accuracyOverview: state.accuracyOverview,
                                  accuracyTracking: prediction.accuracyTracking,
                                  isLoading: state.isLoading,
                                  isAdopting: state.isAdopting,
                                  isSavingSnapshot: state.isSavingSnapshot,
                                  error: state.error,
                                  activeTab: _activeWorkbenchTab,
                                  onWorkbenchTabChanged: (tab) {
                                    setState(() => _activeWorkbenchTab = tab);
                                  },
                                  onRouteSelected: (routeId) => ref
                                      .read(theaterProvider.notifier)
                                      .selectRoute(routeId),
                                  onTimelineSelected: (index) {
                                    unawaited(
                                      SensoryFeedbackService.emit(
                                        SensoryFeedbackEvent.selection,
                                      ),
                                    );
                                    if (_isTimelinePlaying) {
                                      _stopTimelinePlayback();
                                    }
                                    ref
                                        .read(theaterProvider.notifier)
                                        .setTimelineIndex(index);
                                  },
                                  onToggleTimelinePlayback:
                                      _toggleTimelinePlayback,
                                  onResetTimelinePlayback:
                                      _resetTimelinePlayback,
                                  onAdopt: route == null
                                      ? null
                                      : () => unawaited(
                                            ref
                                                .read(theaterProvider.notifier)
                                                .adoptSelectedRouteWithSource(
                                                  sourceChatSessionId: widget
                                                      .initialSourceChatSessionId,
                                                ),
                                          ),
                                  onOpenSimulation: route == null
                                      ? null
                                      : () => context.push(
                                            _buildSimulationRoute(route),
                                          ),
                                  onRunWhatIf: route == null
                                      ? null
                                      : (nodeIds) => unawaited(
                                            ref
                                                .read(theaterProvider.notifier)
                                                .runWhatIfForSteps(nodeIds),
                                          ),
                                  onSaveSnapshot: () => unawaited(
                                    ref
                                        .read(theaterProvider.notifier)
                                        .saveSnapshot(),
                                  ),
                                  isPromotingNode: state.isPromotingNode,
                                  onPromoteNodeToGalaxy: (node) =>
                                      unawaited(_promoteNodeToGalaxy(node)),
                                  onNodeTap: (node) => unawaited(
                                    _handleNodeTap(node, route),
                                  ),
                                  onRecordActual: () => unawaited(
                                    _showActualOutcomeSheet(),
                                  ),
                                  onEdgeLongPress: (edge, globalPosition) =>
                                      unawaited(
                                    _showEdgeTooltip(edge, globalPosition),
                                  ),
                                ),
                              ),
                            ]),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
              if (_showCelebration && state.adoptionResult != null)
                Positioned.fill(
                  child: _AdoptionSuccessOverlay(
                    planName: state.adoptionResult!.planName,
                    planId: state.adoptionResult!.planId,
                    createdTasks: state.adoptionResult!.createdTasks,
                    checkpointDates: state.adoptionResult!.checkpointDates,
                    onDismiss: () => setState(() => _showCelebration = false),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _showTheaterShareSheet() async {
    final state = ref.read(theaterProvider);
    final route = state.selectedRoute;
    final prediction = state.prediction;
    if (prediction == null) {
      return;
    }
    final shareRoute = route ?? prediction.paths.firstOrNull;
    final shareNode = prediction.graphNodes.isEmpty
        ? null
        : prediction.graphNodes.firstWhere(
            (item) => item.id == prediction.targetNodeId,
            orElse: () => prediction.graphNodes.first,
          );
    await showUniversalShareSheet(
      context,
      payload: UniversalSharePayload(
        contentType: shareRoute != null
            ? ShareableContentType.planProgress
            : ShareableContentType.knowledgeNode,
        resourceId: shareRoute?.id ?? shareNode?.id ?? prediction.predictionId,
        title: shareRoute?.title ?? shareNode?.name ?? prediction.targetName,
        subtitle: shareRoute?.summary ?? prediction.topic,
        description: context.l10n.theaterShareTopic(prediction.topic),
        metadata: <String, dynamic>{
          'progress':
              ((shareRoute?.estimatedCompletionRate ?? 0.72) * 100).round(),
          'mastery': (shareRoute?.estimatedMastery ??
                  shareNode?.predictedMastery ??
                  72)
              .round(),
          'learning_time': shareRoute?.dailyMinutes ?? prediction.horizonDays,
          'connections': prediction.graphEdges.length,
        },
        shareMessage:
            context.l10n.theaterShareMessage(prediction.topic, shareRoute?.title ?? prediction.targetName, shareRoute?.summary ?? context.l10n.theaterShareSuggestion),
      ),
      onGenerateCard: (payload) =>
          SharePosterService().generatePoster(context, payload),
      onCommunityShare: () => unawaited(
        showShareResourceSheet(
          context,
          resourceType:
              state.adoptionResult != null ? 'plan' : 'knowledge_node',
          resourceId: state.adoptionResult?.planId ??
              shareNode?.id ??
              prediction.targetNodeId,
          title: state.adoptionResult?.planName ??
              shareRoute?.title ??
              shareNode?.name ??
              prediction.targetName,
          subtitle: prediction.topic,
        ),
      ),
    );
  }

  Future<void> _celebrateTheaterMilestone(TheaterPrediction prediction) async {
    await MirofishMilestoneService.celebrateIfFirstTime(
      context,
      ref,
      kind: MirofishMilestoneKind.firstTheater,
      onShare: () {
        unawaited(_showTheaterShareSheet());
      },
    );
  }

  Future<void> _showActualOutcomeSheet() async {
    final completionController = ValueNotifier<double>(0.72);
    final masteryController = ValueNotifier<double>(0.74);
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                sheetContext.l10n.theaterRecordActualTitle,
                style: Theme.of(sheetContext).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                sheetContext.l10n.theaterRecordActualDesc,
                style: Theme.of(sheetContext).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 18),
              ValueListenableBuilder<double>(
                valueListenable: completionController,
                builder: (context, value, _) => _ActualMetricSlider(
                  label: sheetContext.l10n.theaterActualCompletionRate,
                  value: value,
                  onChanged: (next) => completionController.value = next,
                ),
              ),
              const SizedBox(height: 12),
              ValueListenableBuilder<double>(
                valueListenable: masteryController,
                builder: (context, value, _) => _ActualMetricSlider(
                  label: sheetContext.l10n.theaterActualMastery,
                  value: value,
                  onChanged: (next) => masteryController.value = next,
                ),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      onPressed: () {
                        Navigator.of(sheetContext).pop();
                        unawaited(
                          ref
                              .read(theaterProvider.notifier)
                              .recordActualOutcome(
                                actualCompletionRate:
                                    completionController.value,
                                actualMastery: masteryController.value * 100,
                              ),
                        );
                      },
                      child: Text(sheetContext.l10n.theaterSubmitCalibration),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
    completionController.dispose();
    masteryController.dispose();
  }

  Future<void> _openSettingsSheet({
    required TheaterPrediction prediction,
    required TheaterState state,
    required SimulationState simulationState,
  }) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        final screenHeight = MediaQuery.of(sheetContext).size.height;
        return SafeArea(
          child: SizedBox(
            height: math.min(480, screenHeight * 0.65),
            child: _TheaterSettingsDrawer(
              controller: _topicController,
              isLoading: state.isLoading,
              currentTargetName: prediction.targetName,
              suggestions: simulationState.recommendedSeeds,
              sourceChatSessionId: widget.initialSourceChatSessionId,
              onClose: () => Navigator.of(sheetContext).pop(),
              onSuggestionTap: (topic) {
                Navigator.of(sheetContext).pop();
                _topicController.text = topic;
                unawaited(_generatePrediction(topic));
              },
              onSubmit: () {
                Navigator.of(sheetContext).pop();
                unawaited(_generatePrediction(_topicController.text));
              },
            ),
          ),
        );
      },
    );
  }

  Future<void> _showNodeDetailSheet({
    required TheaterGraphNode node,
    required TheaterPathOption? selectedRoute,
    required ValueChanged<String>? onRunWhatIf,
    required Future<void> Function(TheaterGraphNode node) onPromoteNode,
    required bool isPromotingNode,
  }) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    final canRunWhatIf =
        selectedRoute?.steps.any((step) => step.nodeId == node.id) ?? false;
    final matchedStep = selectedRoute?.steps
        .where((step) => step.nodeId == node.id)
        .firstOrNull;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (sheetContext) {
        final scheme = Theme.of(sheetContext).colorScheme;
        final delta = node.predictedMastery - node.currentMastery;
        final mediaQuery = MediaQuery.of(sheetContext);
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
              20,
              4,
              20,
              math.max(24, mediaQuery.viewInsets.bottom + 16),
            ),
            child: SizedBox(
              height: mediaQuery.size.height * 0.82,
              child: ListView(
                shrinkWrap: true,
                children: [
                  Text(
                    node.name,
                    style: Theme.of(sheetContext)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    node.description.isEmpty
                        ? sheetContext.l10n.theaterNodeDescriptionFallback
                        : node.description,
                    style:
                        Theme.of(sheetContext).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      _NodeStatChip(
                        label: sheetContext.l10n.theaterNodeCurrentMastery,
                        value: '${node.currentMastery.round()}%',
                      ),
                      _NodeStatChip(
                        label: sheetContext.l10n.theaterNodePredictedMastery,
                        value: '${node.predictedMastery.round()}%',
                      ),
                      _NodeStatChip(
                        label: sheetContext.l10n.theaterNodeDelta,
                        value: '${delta >= 0 ? '+' : ''}${delta.round()}%',
                        accent: delta >= 0 ? DS.success : scheme.error,
                      ),
                       _NodeStatChip(
                        label: sheetContext.l10n.theaterNodeRisk,
                        value: _riskLabel(sheetContext, node.riskLevel),
                        accent: _riskColor(node.riskLevel, scheme),
                      ),
                    ],
                  ),
                  if (matchedStep != null) ...[
                    const SizedBox(height: 18),
                    Text(
                      sheetContext.l10n.theaterNodeRoleInPath,
                      style:
                          Theme.of(sheetContext).textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: scheme.surfaceContainerHighest
                            .withValues(alpha: 0.72),
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            sheetContext.l10n.theaterNodeStepLabel(matchedStep.dayLabel, matchedStep.index.toString()),
                            style: Theme.of(sheetContext)
                                .textTheme
                                .labelLarge
                                ?.copyWith(
                                  color: _riskColor(node.riskLevel, scheme),
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            matchedStep.rationale,
                            style: Theme.of(sheetContext)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.45,
                                ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            sheetContext.l10n.theaterNodeNextAction(matchedStep.estimatedMinutes.toString()),
                            style: Theme.of(sheetContext)
                                .textTheme
                                .bodySmall
                                ?.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.45,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      FilledButton.tonal(
                        onPressed: canRunWhatIf && onRunWhatIf != null
                            ? () {
                                Navigator.of(sheetContext).pop();
                                onRunWhatIf(node.id);
                              }
                            : null,
                        child: Text(sheetContext.l10n.theaterWhatIfStart),
                      ),
                      FilledButton(
                        onPressed: isPromotingNode
                            ? null
                            : () {
                                Navigator.of(sheetContext).pop();
                                unawaited(onPromoteNode(node));
                              },
                        child: Text(
                          _nodePrimaryGalaxyActionLabel(sheetContext, node, isPromotingNode),
                        ),
                      ),
                      OutlinedButton(
                        onPressed: (node.mappedGalaxyNodeId ?? '').isEmpty
                            ? null
                            : () {
                                Navigator.of(sheetContext).pop();
                                unawaited(
                                  context.push(
                                    GalaxyRoutes.knowledgeDetail.replaceFirst(
                                      ':id',
                                      node.mappedGalaxyNodeId!,
                                    ),
                                  ),
                                );
                              },
                         child: Text(sheetContext.l10n.theaterViewGalaxyRef),
                      ),
                    ],
                  ),
                  if (!canRunWhatIf) ...[
                    const SizedBox(height: 12),
                    Text(
                      sheetContext.l10n.theaterNodeNotInWhatIfPath,
                      style:
                          Theme.of(sheetContext).textTheme.bodySmall?.copyWith(
                                color: DS.textSecondary,
                              ),
                    ),
                  ],
                  if ((node.mappedGalaxyNodeId ?? '').isEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      sheetContext.l10n.theaterNodeNoGalaxyRef,
                      style:
                          Theme.of(sheetContext).textTheme.bodySmall?.copyWith(
                                color: DS.textSecondary,
                              ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _handleNodeTap(
    TheaterGraphNode node,
    TheaterPathOption? selectedRoute,
  ) async {
    setState(() => _selectedNodeId = node.id);
    await _showNodeDetailSheet(
      node: node,
      selectedRoute: selectedRoute,
      onRunWhatIf: selectedRoute == null
          ? null
          : (nodeId) => unawaited(
                ref.read(theaterProvider.notifier).runWhatIfForStep(nodeId),
              ),
      onPromoteNode: _promoteNodeToGalaxy,
      isPromotingNode: ref.read(theaterProvider).isPromotingNode,
    );
  }

  Future<void> _promoteNodeToGalaxy(TheaterGraphNode node) async {
    final mappedNodeId = (node.mappedGalaxyNodeId ?? '').trim();
    final opensExisting = node.sourceType == 'graph_explicit' ||
        node.sourceType == 'hybrid_reference';
    if (opensExisting && mappedNodeId.isNotEmpty) {
      if (!mounted) {
        return;
      }
      await context.push(
        GalaxyRoutes.knowledgeDetail.replaceFirst(':id', mappedNodeId),
      );
      return;
    }

    final result =
        await ref.read(theaterProvider.notifier).promoteNodeToGalaxy(node.id);
    if (!mounted) {
      return;
    }
    if (result == null) {
      final errorMessage = ref.read(theaterProvider).error ?? context.l10n.theaterPromoteNodeFailed;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(content: Text(errorMessage)),
        );
      return;
    }
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            result.created
                ? context.l10n.theaterPromoteNodeCreated(result.nodeName)
                : context.l10n.theaterPromoteNodeFound(result.nodeName),
          ),
          action: SnackBarAction(
            label: context.l10n.theaterGoImprove,
            onPressed: () {
              unawaited(
                context.push(
                  GalaxyRoutes.knowledgeDetail.replaceFirst(
                    ':id',
                    result.galaxyNodeId,
                  ),
                ),
              );
            },
          ),
        ),
      );
  }

  Future<void> _showEdgeTooltip(
    TheaterGraphEdge edge,
    Offset globalPosition,
  ) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    final overlay =
        Overlay.of(context).context.findRenderObject() as RenderBox?;
    final size = overlay?.size ?? const Size(1200, 800);
    await showMenu<void>(
      context: context,
      position: RelativeRect.fromLTRB(
        globalPosition.dx,
        globalPosition.dy,
        size.width - globalPosition.dx,
        size.height - globalPosition.dy,
      ),
      items: [
        PopupMenuItem<void>(
          enabled: false,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 220),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                    _relationLabel(context, edge.relationType),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  '${context.l10n.theaterEdgeStrength((edge.strength * 100).round().toString())}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  String _riskLabel(BuildContext context, String level) {
    switch (level) {
      case 'high':
        return context.l10n.theaterRiskHigh;
      case 'medium':
        return context.l10n.theaterRiskMedium;
      default:
        return context.l10n.theaterRiskLow;
    }
  }

  Color _riskColor(String level, ColorScheme scheme) {
    switch (level) {
      case 'high':
        return scheme.error;
      case 'medium':
        return DS.warning;
      default:
        return DS.success;
    }
  }

  String _relationLabel(BuildContext context, String relationType) => switch (relationType) {
        'prerequisite' => context.l10n.theaterRelationPrerequisite,
        'explains' => context.l10n.theaterRelationExplains,
        'supports' => context.l10n.theaterRelationSupports,
        'contradicts' => context.l10n.theaterRelationContradicts,
        _ => relationType,
      };
}

class _NodeStatChip extends StatelessWidget {
  const _NodeStatChip({
    required this.label,
    required this.value,
    this.accent,
  });

  final String label;
  final String value;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    final chipAccent = accent ?? Theme.of(context).colorScheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: chipAccent.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: chipAccent,
                ),
          ),
        ],
      ),
    );
  }
}

class _SelectedNodeBanner extends StatelessWidget {
  const _SelectedNodeBanner({
    required this.node,
    required this.isPromotingNode,
    required this.onPromoteToGalaxy,
  });

  final TheaterGraphNode node;
  final bool isPromotingNode;
  final VoidCallback onPromoteToGalaxy;

  @override
  Widget build(BuildContext context) {
    final masteryDelta = node.predictedMastery - node.currentMastery;
    final accent = switch (node.riskLevel) {
      'high' => DS.error,
      'medium' => DS.warning,
      _ => DS.success,
    };
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            accent.withValues(alpha: 0.12),
            Theme.of(context)
                .colorScheme
                .surfaceContainerHighest
                .withValues(alpha: 0.9),
          ],
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.theaterSelectedNode(node.name),
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: accent,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            node.description.isEmpty ? context.l10n.theaterNodeTapHint : node.description,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _NodeStatChip(
                label: context.l10n.theaterNodeStatCurrent,
                value: '${node.currentMastery.round()}%',
                accent: accent,
              ),
              _NodeStatChip(
                label: context.l10n.theaterNodeStatPredicted,
                value: '${node.predictedMastery.round()}%',
                accent: accent,
              ),
              _NodeStatChip(
                label: context.l10n.theaterNodeStatLift,
                value:
                    '${masteryDelta >= 0 ? '+' : ''}${masteryDelta.round()}%',
                accent: masteryDelta >= 0 ? DS.success : DS.error,
              ),
              _NodeStatChip(
                label: context.l10n.theaterNodeStatSource,
                value: _nodeSourceLabel(context, node),
                accent: accent,
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              FilledButton.icon(
                onPressed: isPromotingNode ? null : onPromoteToGalaxy,
                icon: Icon(
                  _nodeCanOpenGalaxy(node)
                      ? Icons.open_in_new_rounded
                      : Icons.add_circle_outline_rounded,
                ),
                label: Text(
                  _nodePrimaryGalaxyActionLabel(context, node, isPromotingNode),
                ),
              ),
              ConstrainedBox(
                constraints: const BoxConstraints(minWidth: 180, maxWidth: 420),
                child: Text(
                  _nodeBannerHint(context, node),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ComposerCard extends StatelessWidget {
  const _ComposerCard({
    required this.controller,
    required this.isLoading,
    required this.suggestions,
    required this.onSuggestionTap,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool isLoading;
  final List<SimulationSeedModel> suggestions;
  final ValueChanged<String> onSuggestionTap;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final topSuggestions = suggestions
        .where((seed) => seed.topic.trim().isNotEmpty)
        .take(3)
        .toList();
    return MirofishStageHeader(
      icon: Icons.travel_explore_rounded,
      eyebrow: context.l10n.theaterComposerEyebrow,
      title: context.l10n.theaterComposerTitle,
      subtitle: context.l10n.theaterComposerSubtitle,
      metrics: <MirofishStageMetric>[
        MirofishStageMetric(
          label: context.l10n.theaterComposerCurrentTarget,
          value:
              controller.text.trim().isEmpty ? context.l10n.theaterComposerWaitingInput : controller.text.trim(),
          accent: DS.info,
          icon: Icons.flag_rounded,
        ),
        MirofishStageMetric(
          label: context.l10n.theaterComposerRecommendedEntry,
          value:
              topSuggestions.isEmpty ? context.l10n.theaterComposerInputPrompt : topSuggestions.first.topic,
          accent: DS.warning,
          icon: Icons.lightbulb_rounded,
        ),
        MirofishStageMetric(
          label: context.l10n.theaterComposerOutput,
          value: context.l10n.theaterComposerOutputDesc,
          accent: DS.success,
          icon: Icons.route_rounded,
        ),
      ],
      primaryLabel: isLoading ? context.l10n.theaterComposerLoading : context.l10n.theaterComposerStart,
      onPrimaryTap: isLoading ? null : onSubmit,
      secondaryLabel:
          topSuggestions.length > 1 ? context.l10n.theaterComposerTrySuggestion(topSuggestions[1].topic) : null,
      onSecondaryTap: topSuggestions.length > 1
          ? () => onSuggestionTap(topSuggestions[1].topic)
          : null,
      accent: DS.info,
      footer: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 420;
              final field = TextField(
                controller: controller,
                textInputAction: TextInputAction.go,
                onSubmitted: (_) => onSubmit(),
                decoration: InputDecoration(
                  hintText: context.l10n.theaterComposerHint,
                  prefixIcon: Icon(
                    Icons.search_rounded,
                    color: scheme.primary,
                  ),
                  filled: true,
                  fillColor:
                      scheme.surfaceContainerHighest.withValues(alpha: 0.55),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20),
                    borderSide: BorderSide.none,
                  ),
                ),
              );
              final submitButton = FilledButton.icon(
                onPressed: isLoading ? null : onSubmit,
                icon: const Icon(Icons.auto_awesome),
                label: Text(isLoading ? context.l10n.theaterComposerDeducing : context.l10n.theaterComposerGenerating),
              );
              if (compact) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    field,
                    const SizedBox(height: 12),
                    submitButton,
                  ],
                );
              }
              return Row(
                children: [
                  Expanded(child: field),
                  const SizedBox(width: 12),
                  submitButton,
                ],
              );
            },
          ),
          if (suggestions.isNotEmpty) ...[
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: suggestions.take(6).map((seed) {
                final topic = seed.topic;
                if (topic.isEmpty) {
                  return const SizedBox.shrink();
                }
                return ActionChip(
                  avatar: const Icon(Icons.bolt_rounded, size: 16),
                  label: Text(topic),
                  onPressed: () => onSuggestionTap(topic),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _TheaterImmersiveTopBar extends StatelessWidget {
  const _TheaterImmersiveTopBar({
    required this.topic,
    required this.targetName,
    required this.targetResolutionMode,
    required this.semanticMatchCount,
    required this.selectedRoute,
    required this.onOpenSettings,
    required this.onShare,
    required this.onOpenGalaxy,
  });

  final String topic;
  final String targetName;
  final String targetResolutionMode;
  final int semanticMatchCount;
  final TheaterPathOption? selectedRoute;
  final VoidCallback onOpenSettings;
  final VoidCallback onShare;
  final VoidCallback? onOpenGalaxy;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  topic,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filledTonal(
                tooltip: context.l10n.theaterTopBarAdjustTarget,
                onPressed: onOpenSettings,
                icon: const Icon(Icons.tune_rounded),
              ),
              IconButton.filledTonal(
                tooltip: context.l10n.theaterTopBarShare,
                onPressed: onShare,
                icon: const Icon(Icons.share_outlined),
              ),
              IconButton.filledTonal(
                tooltip: onOpenGalaxy == null ? context.l10n.theaterTopBarNoGalaxyRef : context.l10n.theaterTopBarViewGalaxy,
                onPressed: onOpenGalaxy,
                icon: const Icon(Icons.auto_graph_rounded),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _MetricPill(label: context.l10n.theaterTopBarTarget(targetName)),
                const SizedBox(width: 8),
                if (selectedRoute != null) ...[
                  _MetricPill(label: context.l10n.theaterTopBarPath(selectedRoute!.title)),
                  const SizedBox(width: 8),
                ],
                _MetricPill(
                  label: context.l10n.theaterTopBarMode(_targetModeLabel(context, targetResolutionMode)),
                ),
                const SizedBox(width: 8),
                _MetricPill(
                  label: semanticMatchCount > 0
                      ? context.l10n.theaterTopBarRefMap(semanticMatchCount.toString())
                      : context.l10n.theaterTopBarFreeForm,
                ),
                const SizedBox(width: 8),
                _MetricPill(
                  label: context.l10n.theaterTopBarMastery(selectedRoute?.estimatedMastery.round().toString() ?? '--'),
                ),
              ],
            ),
          ),
        ],
      );
}

class _TheaterSettingsDrawer extends StatelessWidget {
  const _TheaterSettingsDrawer({
    required this.controller,
    required this.isLoading,
    required this.currentTargetName,
    required this.suggestions,
    required this.onSuggestionTap,
    required this.onSubmit,
    required this.onClose,
    this.sourceChatSessionId,
  });

  final TextEditingController controller;
  final bool isLoading;
  final String currentTargetName;
  final List<SimulationSeedModel> suggestions;
  final ValueChanged<String> onSuggestionTap;
  final VoidCallback onSubmit;
  final VoidCallback onClose;
  final String? sourceChatSessionId;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 10, 10),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.theaterSettingsTitle,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        context.l10n.theaterSettingsSubtitle,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.4,
                            ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: onClose,
                  icon: const Icon(Icons.close_rounded),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
              children: [
                if ((sourceChatSessionId ?? '').trim().isNotEmpty) ...[
                  ChatContinuityBanner(
                    sourceChatSessionId: sourceChatSessionId!.trim(),
                    kind: ChatContinuityKind.journey,
                    subtitle: context.l10n.theaterSettingsContinuity,
                  ),
                  const SizedBox(height: 12),
                ],
                Text(
                  context.l10n.theaterSettingsCurrentTarget(currentTargetName),
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: DS.info,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: controller,
                  textInputAction: TextInputAction.go,
                  onSubmitted: (_) {
                    if (!isLoading) {
                      onSubmit();
                    }
                  },
                  decoration: InputDecoration(
                    labelText: context.l10n.theaterSettingsLabel,
                  hintText: context.l10n.theaterComposerHint,
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 14),
                FilledButton.icon(
                  onPressed: isLoading ? null : onSubmit,
                  icon: const Icon(Icons.auto_awesome_rounded),
                  label: Text(isLoading ? context.l10n.theaterComposerLoading : context.l10n.theaterSettingsGenerate),
                ),
                if (suggestions.isNotEmpty) ...[
                  const SizedBox(height: 18),
                  Text(
                    context.l10n.theaterSettingsSuggestions,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: suggestions.take(6).map((seed) {
                      final topic = seed.topic.trim();
                      if (topic.isEmpty) {
                        return const SizedBox.shrink();
                      }
                      return ActionChip(
                        avatar: const Icon(Icons.bolt_rounded, size: 16),
                        label: Text(topic),
                        onPressed: () => onSuggestionTap(topic),
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
        ],
      );
}

class _TheaterWorkbenchTabs extends StatelessWidget {
  const _TheaterWorkbenchTabs({
    required this.activeTab,
    required this.onChanged,
  });

  final _TheaterWorkbenchTab activeTab;
  final ValueChanged<_TheaterWorkbenchTab> onChanged;

  Key _tabKey(_TheaterWorkbenchTab tab) =>
      ValueKey<String>('theater-workbench-tab-${tab.name}');

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 420) {
            final items = <({
              _TheaterWorkbenchTab value,
              String label,
              IconData icon,
            })>[
              (
                value: _TheaterWorkbenchTab.graph,
                label: context.l10n.theaterTabGraph,
                icon: Icons.hub_rounded,
              ),
              (
                value: _TheaterWorkbenchTab.paths,
                label: context.l10n.theaterTabPaths,
                icon: Icons.route_rounded,
              ),
              (
                value: _TheaterWorkbenchTab.discussion,
                label: context.l10n.theaterTabDiscussion,
                icon: Icons.forum_rounded,
              ),
              (
                value: _TheaterWorkbenchTab.calibration,
                label: context.l10n.theaterTabCalibration,
                icon: Icons.tune_rounded,
              ),
            ];
            return Wrap(
              spacing: 8,
              runSpacing: 8,
              children: items
                  .map(
                    (item) => ChoiceChip(
                      key: _tabKey(item.value),
                      avatar: Icon(item.icon, size: 16),
                      label: Text(item.label),
                      selected: activeTab == item.value,
                      onSelected: (_) => onChanged(item.value),
                    ),
                  )
                  .toList(),
            );
          }
          return SegmentedButton<_TheaterWorkbenchTab>(
            segments: [
              ButtonSegment<_TheaterWorkbenchTab>(
                value: _TheaterWorkbenchTab.graph,
                label: Text(context.l10n.theaterTabGraph),
                icon: const Icon(Icons.hub_rounded),
              ),
              ButtonSegment<_TheaterWorkbenchTab>(
                value: _TheaterWorkbenchTab.paths,
                label: Text(context.l10n.theaterTabPaths),
                icon: const Icon(Icons.route_rounded),
              ),
              ButtonSegment<_TheaterWorkbenchTab>(
                value: _TheaterWorkbenchTab.discussion,
                label: Text(context.l10n.theaterTabDiscussion),
                icon: const Icon(Icons.forum_rounded),
              ),
              ButtonSegment<_TheaterWorkbenchTab>(
                value: _TheaterWorkbenchTab.calibration,
                label: Text(context.l10n.theaterTabCalibration),
                icon: const Icon(Icons.tune_rounded),
              ),
            ],
            selected: <_TheaterWorkbenchTab>{activeTab},
            onSelectionChanged: (selection) => onChanged(selection.first),
            showSelectedIcon: false,
          );
        },
      );
}

class _TheaterIntroState extends StatelessWidget {
  const _TheaterIntroState({
    required this.isLoading,
    required this.loadingStage,
    required this.latestSnapshot,
    required this.suggestions,
    required this.error,
    required this.onStartFirstPrediction,
    required this.onRetry,
    required this.onChangeTarget,
    super.key,
  });

  final bool isLoading;
  final String loadingStage;
  final TheaterSnapshot? latestSnapshot;
  final List<SimulationSeedModel> suggestions;
  final String? error;
  final VoidCallback onStartFirstPrediction;
  final VoidCallback onRetry;
  final VoidCallback onChangeTarget;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return _PredictionLoadingState(loadingStage: loadingStage);
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (error != null) ...[
          _TheaterErrorCard(
            message: error!,
            onRetry: onRetry,
            onSecondary: onChangeTarget,
             secondaryLabel: context.l10n.theaterIntroChangeTarget,
          ),
          const SizedBox(height: 14),
        ],
        GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      DS.info.withValues(alpha: 0.9),
                      DS.brandPrimary.withValues(alpha: 0.82),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(22),
                ),
                child: const Icon(
                  Icons.travel_explore_rounded,
                  color: Colors.white,
                  size: 32,
                ),
              ),
              const SizedBox(height: 18),
              Text(
                context.l10n.theaterIntroTitle,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 10),
              Text(
                context.l10n.theaterIntroSteps,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.55,
                    ),
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: onStartFirstPrediction,
                icon: const Icon(Icons.play_arrow_rounded),
                label: Text(context.l10n.theaterIntroStartFirst),
              ),
            ],
          ),
        ),
        if (latestSnapshot != null) ...[
          const SizedBox(height: 14),
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.theaterIntroLastSnapshot,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: 10),
                Text(
                  latestSnapshot!.title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  latestSnapshot!.topic,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ],
            ),
          ),
        ],
        if (suggestions.isNotEmpty) ...[
          const SizedBox(height: 14),
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.theaterIntroSuggestions,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: 10),
                ...suggestions.take(3).map(
                      (seed) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.adjust_rounded, size: 16),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '${seed.topic}\n${seed.tensionPoint}',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.45,
                                    ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _PredictionView extends StatelessWidget {
  const _PredictionView({
    required this.prediction,
    required this.selectedRoute,
    required this.timeline,
    required this.timelineIndex,
    required this.focusNodeIds,
    required this.selectedNodeId,
    required this.isTimelinePlaying,
    required this.recommendedRouteId,
    required this.whatIfResult,
    required this.snapshot,
    required this.adoptionResult,
    required this.accuracySummary,
    required this.accuracyOverview,
    required this.accuracyTracking,
    required this.isLoading,
    required this.isAdopting,
    required this.isPromotingNode,
    required this.isSavingSnapshot,
    required this.error,
    required this.activeTab,
    required this.onWorkbenchTabChanged,
    required this.onRouteSelected,
    required this.onTimelineSelected,
    required this.onToggleTimelinePlayback,
    required this.onResetTimelinePlayback,
    required this.onAdopt,
    required this.onOpenSimulation,
    required this.onRunWhatIf,
    required this.onSaveSnapshot,
    required this.onRecordActual,
    required this.onPromoteNodeToGalaxy,
    required this.onNodeTap,
    required this.onEdgeLongPress,
    super.key,
  });

  final TheaterPrediction prediction;
  final TheaterPathOption? selectedRoute;
  final List<TheaterTimelineFrame> timeline;
  final int timelineIndex;
  final List<String> focusNodeIds;
  final String? selectedNodeId;
  final bool isTimelinePlaying;
  final String recommendedRouteId;
  final TheaterWhatIfResult? whatIfResult;
  final TheaterSnapshot? snapshot;
  final TheaterAdoptionResult? adoptionResult;
  final TheaterAccuracySummary? accuracySummary;
  final TheaterAccuracyOverview? accuracyOverview;
  final TheaterAccuracyTracking? accuracyTracking;
  final bool isLoading;
  final bool isAdopting;
  final bool isPromotingNode;
  final bool isSavingSnapshot;
  final String? error;
  final _TheaterWorkbenchTab activeTab;
  final ValueChanged<_TheaterWorkbenchTab> onWorkbenchTabChanged;
  final ValueChanged<String> onRouteSelected;
  final ValueChanged<int> onTimelineSelected;
  final VoidCallback onToggleTimelinePlayback;
  final VoidCallback onResetTimelinePlayback;
  final VoidCallback? onAdopt;
  final VoidCallback? onOpenSimulation;
  final ValueChanged<List<String>>? onRunWhatIf;
  final VoidCallback onSaveSnapshot;
  final VoidCallback onRecordActual;
  final ValueChanged<TheaterGraphNode> onPromoteNodeToGalaxy;
  final ValueChanged<TheaterGraphNode> onNodeTap;
  final void Function(TheaterGraphEdge edge, Offset globalPosition)
      onEdgeLongPress;

  @override
  Widget build(BuildContext context) {
    if (prediction.paths.isEmpty) {
      return _TheaterEmptyState(
        title: context.l10n.theaterEmptyTitle,
        message: context.l10n.theaterEmptyMessage,
      );
    }
    final route = selectedRoute;
    final selectedNode = prediction.graphNodes
        .where((node) => node.id == selectedNodeId)
        .firstOrNull;
    final routeTimeline = route == null
        ? timeline
        : timeline.where((frame) => frame.routeId == route.id).toList();
    final safeTimelineIndex = routeTimeline.isEmpty
        ? 0
        : timelineIndex.clamp(0, routeTimeline.length - 1);
    final activeRoute = route ??
        prediction.paths.firstWhere(
          (item) => item.id == recommendedRouteId,
          orElse: () => prediction.paths.first,
        );
    final compactWidth = MediaQuery.sizeOf(context).width < 420;

    final graphTab = ListView(
      key: const PageStorageKey<String>('theater-graph-tab'),
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      children: [
        GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          padding: const EdgeInsets.all(14),
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MetricPill(label: context.l10n.theaterGraphRecommended(activeRoute.title)),
              _MetricPill(
                label: context.l10n.theaterGraphEstimatedMastery(activeRoute.estimatedMastery.round().toString()),
              ),
              _MetricPill(label: context.l10n.theaterGraphRisk(_headlineRisk(context, activeRoute))),
              _MetricPill(
                label: context.l10n.theaterGraphMode(_targetModeLabel(context, prediction.targetResolutionMode)),
              ),
              _MetricPill(
                label: prediction.semanticMatches.isNotEmpty
                    ? context.l10n.theaterGraphRefCount(prediction.semanticMatches.length.toString())
                    : context.l10n.theaterGraphPendingEntry,
              ),
              _MetricPill(label: context.l10n.theaterGraphNodeCount(prediction.graphNodes.length.toString())),
            ],
          ),
        ),
        const SizedBox(height: 12),
        GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(
                    context.l10n.theaterGraphMainStage,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  _MetricPill(
                    label: prediction.hasMappedGalaxyReferences
                        ? context.l10n.theaterGraphWithGalaxy
                        : context.l10n.theaterGraphStandalone,
                  ),
                  if (routeTimeline.isNotEmpty)
                    _MetricPill(
                      label: routeTimeline[safeTimelineIndex].label,
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                context.l10n.theaterGraphInstructions,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 10),
              if (prediction.semanticMatches.isNotEmpty) ...[
                _SemanticMatchSummary(matches: prediction.semanticMatches),
                const SizedBox(height: 12),
              ],
              if (selectedNode != null) ...[
                _SelectedNodeBanner(
                  node: selectedNode,
                  isPromotingNode: isPromotingNode,
                  onPromoteToGalaxy: () => onPromoteNodeToGalaxy(selectedNode),
                ),
                const SizedBox(height: 12),
              ],
              SizedBox(
                height: math.max(460, MediaQuery.sizeOf(context).height * 0.66),
                child: KnowledgeTheaterGraph(
                  nodes: prediction.graphNodes,
                  edges: prediction.graphEdges,
                  focusNodeIds: focusNodeIds,
                  selectedNodeId: selectedNodeId,
                  routeNodeIds:
                      route?.steps.map((step) => step.nodeId).toList() ??
                          const <String>[],
                  onNodeTap: onNodeTap,
                  onEdgeLongPress: onEdgeLongPress,
                  expandToFill: true,
                ),
              ),
            ],
          ),
        ),
        if (compactWidth && prediction.paths.isNotEmpty) ...[
          const SizedBox(height: 12),
          _CompactRoutePreviewCard(
            selectedRoute: activeRoute,
            recommendedRouteId: recommendedRouteId,
            alternatives: prediction.paths
                .where((item) => item.id != activeRoute.id)
                .toList(),
            onOpenPathWorkbench: () =>
                onWorkbenchTabChanged(_TheaterWorkbenchTab.paths),
          ),
        ],
      ],
    );

    final pathTab = ListView(
      key: const PageStorageKey<String>('theater-paths-tab'),
      children: [
        _RouteSection(
          routes: prediction.paths,
          selectedRouteId: route?.id,
          recommendedRouteId: recommendedRouteId,
          onSelect: onRouteSelected,
          onAdopt: onAdopt,
          onOpenSimulation: onOpenSimulation,
          isAdopting: isAdopting,
          adoptionResult: adoptionResult,
        ),
        if (route != null && prediction.paths.length > 1) ...[
          const SizedBox(height: 14),
          _RouteComparisonCard(
            selectedRoute: route,
            recommendedRouteId: recommendedRouteId,
            alternatives:
                prediction.paths.where((item) => item.id != route.id).toList(),
          ),
        ],
        if (route != null) ...[
          const SizedBox(height: 14),
          _WhatIfSection(
            route: route,
            result: whatIfResult,
            onRun: onRunWhatIf,
          ),
        ],
      ],
    );

    final discussionTab = ListView(
      key: const PageStorageKey<String>('theater-discussion-tab'),
      children: [
        if (timeline.isNotEmpty) ...[
          _TimelineSection(
            timeline: routeTimeline,
            selectedIndex: safeTimelineIndex,
            turns: prediction.discussionTurns,
            isPlaying: isTimelinePlaying,
            onSelected: onTimelineSelected,
            onTogglePlayback: onToggleTimelinePlayback,
            onReset: onResetTimelinePlayback,
            branchTimeline: whatIfResult?.branchTimeline ?? const [],
          ),
          const SizedBox(height: 14),
        ],
        _DiscussionSection(turns: prediction.discussionTurns),
      ],
    );

    final calibrationTab = ListView(
      key: const PageStorageKey<String>('theater-calibration-tab'),
      children: [
        GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.theaterCalibrationTitle,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                context.l10n.theaterCalibrationSubtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _SnapshotSection(
          snapshot: snapshot,
          isSaving: isSavingSnapshot,
          onSave: onSaveSnapshot,
        ),
        if (accuracySummary != null) ...[
          const SizedBox(height: 14),
          _AccuracyCard(
            summary: accuracySummary,
            overview: accuracyOverview,
          ),
        ] else if (accuracyTracking != null) ...[
          const SizedBox(height: 14),
          _AccuracyCard.pending(
            tracking: accuracyTracking,
            overview: accuracyOverview,
            onRecordActual: onRecordActual,
          ),
        ],
        if (error != null) ...[
          const SizedBox(height: 14),
          _TheaterErrorCard(message: error!),
        ],
      ],
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        _TheaterWorkbenchTabs(
          activeTab: activeTab,
          onChanged: onWorkbenchTabChanged,
        ),
        const SizedBox(height: 12),
        if (error != null && activeTab != _TheaterWorkbenchTab.calibration) ...[
          _TheaterErrorCard(message: error!),
          const SizedBox(height: 12),
        ],
        if (isLoading) ...[
          const LinearProgressIndicator(minHeight: 3),
          const SizedBox(height: 12),
        ],
        Expanded(
          child: IndexedStack(
            index: activeTab.index,
            children: [
              graphTab,
              pathTab,
              discussionTab,
              calibrationTab,
            ],
          ),
        ),
      ],
    );
  }
}

class _TheaterErrorCard extends StatelessWidget {
  const _TheaterErrorCard({
    required this.message,
    this.onRetry,
    this.onSecondary,
    this.secondaryLabel,
  });

  final String message;
  final VoidCallback? onRetry;
  final VoidCallback? onSecondary;
  final String? secondaryLabel;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: scheme.error.withValues(alpha: 0.25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.error_outline_rounded,
                color: scheme.error,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  message,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: scheme.error,
                        height: 1.5,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                ),
              ),
            ],
          ),
          if (onRetry != null || onSecondary != null) ...[
            const SizedBox(height: 14),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                if (onRetry != null)
                  FilledButton.tonalIcon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(context.l10n.theaterRetry),
                  ),
                if (onSecondary != null)
                  OutlinedButton(
                    onPressed: onSecondary,
                    child: Text(secondaryLabel ?? context.l10n.theaterGotIt),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _TheaterEmptyState extends StatelessWidget {
  const _TheaterEmptyState({
    required this.title,
    required this.message,
  });

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.route_outlined,
                size: 36,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 12),
              Text(
                title,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
            ],
          ),
        ),
      );
}

class _SemanticMatchSummary extends StatelessWidget {
  const _SemanticMatchSummary({
    required this.matches,
  });

  final List<TheaterSemanticMatch> matches;

  @override
  Widget build(BuildContext context) {
    final preview = matches.take(2).toList();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context)
            .colorScheme
            .surfaceContainerHighest
            .withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.theaterSemanticMatchTitle,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            preview
                .map(
                  (item) =>
                      context.l10n.theaterSemanticMatchItem(item.freeformNodeName, item.galaxyNodeName),
                )
                .join('；'),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
        ],
      ),
    );
  }
}

class _PredictionLoadingState extends StatefulWidget {
  const _PredictionLoadingState({
    required this.loadingStage,
  });

  final String loadingStage;

  @override
  State<_PredictionLoadingState> createState() =>
      _PredictionLoadingStateState();
}

class _PredictionLoadingStateState extends State<_PredictionLoadingState>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  static List<({String key, String title, IconData icon})> _buildStages(BuildContext context) => [
    (
      key: 'graph',
      title: context.l10n.theaterStageBuildGraph,
      icon: Icons.hub_rounded,
    ),
    (
      key: 'paths',
      title: context.l10n.theaterStageAnalyzePaths,
      icon: Icons.route_rounded,
    ),
    (
      key: 'prediction',
      title: context.l10n.theaterStageGenerateRisk,
      icon: Icons.analytics_rounded,
    ),
    (
      key: 'done',
      title: context.l10n.theaterStagePrepare,
      icon: Icons.check_circle_rounded,
    ),
  ];

  int _stageIndex(BuildContext context, String stage) {
    final stages = _buildStages(context);
    final index = stages.indexWhere((item) => item.key == stage);
    return index >= 0 ? index : 0;
  }

  @override
  Widget build(BuildContext context) {
    final stages = _buildStages(context);
    final currentStageIndex = _stageIndex(context, widget.loadingStage);
    final scheme = Theme.of(context).colorScheme;
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.theaterLoadingTitle,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 10),
          Text(
            context.l10n.theaterLoadingSubtitle,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: 18),
          ...List.generate(stages.length, (index) {
            final item = stages[index];
            final isCompleted = index < currentStageIndex;
            final isCurrent = index == currentStageIndex;
            final accent = isCompleted
                ? DS.success
                : (isCurrent
                    ? DS.info
                    : scheme.outline.withValues(alpha: 0.65));
            return Padding(
              padding: EdgeInsets.only(
                bottom: index == stages.length - 1 ? 0 : 12,
              ),
              child: AnimatedBuilder(
                animation: _controller,
                builder: (context, _) {
                  final pulseScale =
                      isCurrent ? (0.96 + (_controller.value * 0.08)) : 1.0;
                  return Row(
                    children: [
                      Transform.scale(
                        scale: pulseScale,
                        child: Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                            color: accent.withValues(alpha: 0.14),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: accent.withValues(alpha: 0.32),
                            ),
                          ),
                          child: isCompleted
                              ? Icon(
                                  Icons.check_rounded,
                                  color: DS.success,
                                  size: 20,
                                )
                              : Icon(
                                  item.icon,
                                  color: accent,
                                  size: 20,
                                ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          item.title,
                          style:
                              Theme.of(context).textTheme.titleSmall?.copyWith(
                                    fontWeight: DS.fontWeightBold,
                                    color: isCurrent || isCompleted
                                        ? null
                                        : DS.textSecondary,
                                  ),
                        ),
                      ),
                      if (isCurrent)
                        SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.2,
                            valueColor: AlwaysStoppedAnimation<Color>(accent),
                          ),
                        )
                      else if (isCompleted)
                        Icon(
                          Icons.check_circle_rounded,
                          color: DS.success,
                          size: 18,
                        )
                      else
                        Icon(
                          Icons.more_horiz_rounded,
                          color: scheme.outline.withValues(alpha: 0.8),
                          size: 18,
                        ),
                    ],
                  );
                },
              ),
            );
          }),
          const SizedBox(height: 20),
          const _SkeletonGraphStage(),
        ],
      ),
    );
  }
}

class _SkeletonGraphStage extends StatefulWidget {
  const _SkeletonGraphStage();

  @override
  State<_SkeletonGraphStage> createState() => _SkeletonGraphStageState();
}

class _SkeletonGraphStageState extends State<_SkeletonGraphStage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );
    unawaited(_controller.repeat(reverse: true));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final pulse = 0.18 + (_controller.value * 0.24);
          return Container(
            height: 240,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Theme.of(context)
                      .colorScheme
                      .surfaceContainerHighest
                      .withValues(alpha: 0.72),
                  Theme.of(context)
                      .colorScheme
                      .surfaceContainerHigh
                      .withValues(alpha: 0.42),
                ],
              ),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Stack(
              children: [
                ...const [
                  Offset(72, 64),
                  Offset(188, 58),
                  Offset(122, 144),
                  Offset(248, 148),
                ].map(
                  (offset) => Positioned(
                    left: offset.dx,
                    top: offset.dy,
                    child: const _SkeletonNode(),
                  ),
                ),
                Positioned.fill(
                  child: IgnorePointer(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(24),
                        color: DS.info.withValues(alpha: pulse),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      );
}

class _SkeletonNode extends StatelessWidget {
  const _SkeletonNode();

  @override
  Widget build(BuildContext context) => Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: Theme.of(context)
              .colorScheme
              .surfaceContainerHighest
              .withValues(alpha: 0.88),
          shape: BoxShape.circle,
        ),
      );
}

class _TimelineSection extends StatelessWidget {
  const _TimelineSection({
    required this.timeline,
    required this.selectedIndex,
    required this.turns,
    required this.isPlaying,
    required this.onSelected,
    required this.onTogglePlayback,
    required this.onReset,
    required this.branchTimeline,
  });

  final List<TheaterTimelineFrame> timeline;
  final int selectedIndex;
  final List<TheaterDiscussionTurn> turns;
  final bool isPlaying;
  final ValueChanged<int> onSelected;
  final VoidCallback onTogglePlayback;
  final VoidCallback onReset;
  final List<TheaterTimelineFrame> branchTimeline;

  @override
  Widget build(BuildContext context) {
    final summaryTurn = timeline.isEmpty
        ? null
        : turns.cast<TheaterDiscussionTurn?>().elementAt(
              timeline[selectedIndex].discussionTurnIndex.clamp(
                    0,
                    turns.isEmpty ? 0 : turns.length - 1,
                  ),
            );
    final currentFrame = timeline.isEmpty ? null : timeline[selectedIndex];
    final branchFrame = branchTimeline.isEmpty
        ? null
        : branchTimeline[selectedIndex.clamp(0, branchTimeline.length - 1)];
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.theaterTimelineTitle,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                context.l10n.theaterTimelineSubtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton.tonalIcon(
                    onPressed: onTogglePlayback,
                    icon: Icon(
                      isPlaying
                          ? Icons.pause_circle_outline_rounded
                          : Icons.play_circle_outline_rounded,
                    ),
                    label: Text(isPlaying ? context.l10n.theaterTimelinePause : context.l10n.theaterTimelineAutoPlay),
                  ),
                  OutlinedButton.icon(
                    onPressed: onReset,
                    icon: const Icon(Icons.restart_alt_rounded),
                    label: Text(context.l10n.theaterTimelineReset),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (timeline.isNotEmpty) ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context)
                    .colorScheme
                    .surfaceContainerHighest
                    .withValues(alpha: 0.68),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    currentFrame?.label ?? context.l10n.theaterTimelineCurrentPhase,
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: DS.brandPrimary,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    currentFrame?.activeStepTitle ?? context.l10n.theaterTimelineWaitingPath,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    currentFrame?.compareLabel ?? context.l10n.theaterTimelineBaseline,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                  if (summaryTurn != null) ...[
                    const SizedBox(height: 10),
                    Text(
                      context.l10n.theaterTimelineDiscussionHere,
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: DS.textSecondary,
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      summaryTurn.content,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.4,
                          ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 12),
            SliderTheme(
              data: SliderTheme.of(context).copyWith(
                thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 8),
              ),
              child: Slider(
                value: selectedIndex.toDouble(),
                max: (timeline.length - 1).toDouble(),
                divisions: timeline.length - 1,
                label: timeline[selectedIndex].label,
                onChanged: (value) => onSelected(value.round()),
              ),
            ),
            Row(
              children: [
                Expanded(
                  child: _TimelineMetricTile(
                    label: context.l10n.theaterTimelineMastery,
                    value:
                        '${timeline[selectedIndex].projectedMastery.round()}%',
                    accent: DS.success,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _TimelineMetricTile(
                    label: context.l10n.theaterTimelineCompletion,
                    value:
                        '${(timeline[selectedIndex].projectedCompletionRate * 100).round()}%',
                    accent: DS.info,
                  ),
                ),
              ],
            ),
            if (branchFrame != null) ...[
              const SizedBox(height: 10),
              _BranchDeltaCard(
                baseline: timeline[selectedIndex],
                branch: branchFrame,
              ),
            ],
          ],
          if (summaryTurn != null) ...[
            const SizedBox(height: 8),
            Text(
              context.l10n.theaterTimelinePhaseWithSteps(currentFrame?.label ?? '', currentFrame?.activeStepTitle ?? context.l10n.theaterTimelineWaitingDeduction, currentFrame?.compareLabel ?? ''),
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _RouteSection extends StatefulWidget {
  const _RouteSection({
    required this.routes,
    required this.selectedRouteId,
    required this.recommendedRouteId,
    required this.onSelect,
    required this.onAdopt,
    required this.onOpenSimulation,
    required this.isAdopting,
    required this.adoptionResult,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final String recommendedRouteId;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
  final VoidCallback? onOpenSimulation;
  final bool isAdopting;
  final TheaterAdoptionResult? adoptionResult;

  @override
  State<_RouteSection> createState() => _RouteSectionState();
}

class _RouteSectionState extends State<_RouteSection> {
  bool _compareMode = false;
  late final PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(
      viewportFraction: 0.92,
      initialPage: _selectedIndex,
    );
  }

  @override
  void didUpdateWidget(covariant _RouteSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedRouteId != widget.selectedRouteId &&
        _pageController.hasClients) {
      unawaited(
        _pageController.animateToPage(
          _selectedIndex,
          duration: DS.durationNormal,
          curve: Curves.easeOutCubic,
        ),
      );
    }
  }

  int get _selectedIndex {
    final index = widget.routes.indexWhere(
      (route) => route.id == widget.selectedRouteId,
    );
    return index < 0 ? 0 : index;
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 420;
                final segmentControl = SegmentedButton<bool>(
                  segments: [
                    ButtonSegment<bool>(
                      value: false,
                      label: Text(context.l10n.theaterRouteList),
                    ),
                    ButtonSegment<bool>(
                      value: true,
                      label: Text(context.l10n.theaterRouteCompare),
                    ),
                  ],
                  selected: <bool>{_compareMode},
                  onSelectionChanged: (selection) {
                    unawaited(
                      SensoryFeedbackService.emit(
                        SensoryFeedbackEvent.selection,
                      ),
                    );
                    setState(() => _compareMode = selection.first);
                  },
                );
                if (compact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.theaterRouteComparisonTitle,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                      const SizedBox(height: 12),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: segmentControl,
                      ),
                    ],
                  );
                }
                return Row(
                  children: [
                    Text(
                      context.l10n.theaterRouteComparisonTitle,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const Spacer(),
                    segmentControl,
                  ],
                );
              },
            ),
            const SizedBox(height: 12),
            AnimatedSwitcher(
              duration: DS.durationNormal,
              child: _compareMode
                  ? _RouteComparePager(
                      key: const ValueKey('compare'),
                      routes: widget.routes,
                      selectedRouteId: widget.selectedRouteId,
                      recommendedRouteId: widget.recommendedRouteId,
                      pageController: _pageController,
                      onSelect: widget.onSelect,
                      onAdopt: widget.onAdopt,
                      onOpenSimulation: widget.onOpenSimulation,
                      isAdopting: widget.isAdopting,
                    )
                  : _RouteListView(
                      key: const ValueKey('list'),
                      routes: widget.routes,
                      selectedRouteId: widget.selectedRouteId,
                      recommendedRouteId: widget.recommendedRouteId,
                      onSelect: widget.onSelect,
                      onAdopt: widget.onAdopt,
                      onOpenSimulation: widget.onOpenSimulation,
                      isAdopting: widget.isAdopting,
                    ),
            ),
            if (widget.adoptionResult != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: DS.success.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.theaterRouteAdoptedPlan(widget.adoptionResult!.planName),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.success,
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    if (widget.adoptionResult!.createdTasks.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        context.l10n.theaterRouteFirstWeekTasks(widget.adoptionResult!.createdTasks.take(3).map((item) => item.title).join('、')),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.4,
                            ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ],
        ),
      );
}

String _headlineRisk(BuildContext context, TheaterPathOption route) {
  if (route.risks.isEmpty) {
    return context.l10n.theaterRouteRiskControllable;
  }
  final firstRisk = route.risks.first.trim();
  if (firstRisk.isEmpty) {
    return context.l10n.theaterRouteRiskPacing;
  }
  return firstRisk;
}

String _routeCompletionDisplay(BuildContext context, TheaterPathOption route,
    {bool compact = false}) {
  if (route.dataQuality == 'low') {
    final low = (route.completionRangeLow * 100).round();
    final high = (route.completionRangeHigh * 100).round();
    return context.l10n.theaterRouteEstimatedRange(low.toString(), high.toString());
  }
  return '${(route.estimatedCompletionRate * 100).round()}%';
}

String _routeMasteryDisplay(BuildContext context, TheaterPathOption route, {bool compact = false}) {
  if (route.dataQuality == 'low') {
    final low = route.masteryRangeLow.round();
    final high = route.masteryRangeHigh.round();
    return context.l10n.theaterRouteEstimatedRange(low.toString(), high.toString());
  }
  return '${route.estimatedMastery.round()}%';
}

String _routeDataBadgeLabel(BuildContext context, TheaterPathOption route) {
  switch (route.dataQuality) {
    case 'low':
      return context.l10n.theaterRouteDataQualityLow;
    case 'medium':
      return context.l10n.theaterRouteDataQualityMedium;
    case 'high':
      return context.l10n.theaterRouteDataQualityHigh((route.dataSufficiencyScore * 100).round().toString());
    default:
      return context.l10n.theaterRouteDataQualityFallback;
  }
}

String _routeDataNote(BuildContext context, TheaterPathOption route) {
  switch (route.dataQuality) {
    case 'low':
      return context.l10n.theaterRouteDataNoteLow;
    case 'medium':
      return context.l10n.theaterRouteDataNoteMedium;
    default:
      return '';
  }
}

Color _routeMetricBackgroundColor(
    BuildContext context, TheaterPathOption route) {
  if (route.dataQuality == 'low') {
    return Theme.of(context).colorScheme.surfaceContainerHighest;
  }
  if (route.dataQuality == 'medium') {
    return DS.warning.withValues(alpha: 0.14);
  }
  return Theme.of(context).colorScheme.surface;
}

Color _routeMetricLabelColor(BuildContext context, TheaterPathOption route) {
  if (route.dataQuality == 'low') {
    return DS.textSecondary;
  }
  if (route.dataQuality == 'medium') {
    return DS.warning;
  }
  return Theme.of(context).textTheme.labelMedium?.color ?? DS.textPrimary;
}

String _targetModeLabel(BuildContext context, String mode) {
  switch (mode) {
    case 'graph_explicit':
      return context.l10n.theaterRouteModeAnchored;
    case 'hybrid_semantic':
      return context.l10n.theaterRouteModeHybrid;
    case 'freeform_only':
      return context.l10n.theaterRouteModeFree;
    default:
      return context.l10n.theaterRouteModeDeducing;
  }
}

bool _nodeCanOpenGalaxy(TheaterGraphNode node) =>
    (node.mappedGalaxyNodeId ?? '').trim().isNotEmpty &&
    (node.sourceType == 'graph_explicit' ||
        node.sourceType == 'hybrid_reference');

String _nodePrimaryGalaxyActionLabel(
  BuildContext context,
  TheaterGraphNode node,
  bool isPromotingNode,
) {
  if (isPromotingNode) {
    return context.l10n.theaterNodeGalaxySyncing;
  }
  return _nodeCanOpenGalaxy(node) ? context.l10n.theaterNodeOpenGalaxy : context.l10n.theaterNodeAddToGalaxy;
}

String _nodeSourceLabel(BuildContext context, TheaterGraphNode node) {
  switch (node.sourceType) {
    case 'graph_explicit':
      return context.l10n.theaterNodeSourceExplicit;
    case 'hybrid_reference':
      return context.l10n.theaterNodeSourceHybrid;
    default:
      return node.candidateStatus == 'pending_review' ? context.l10n.theaterNodeSourcePending : context.l10n.theaterNodeSourceFree;
  }
}

String _nodeBannerHint(BuildContext context, TheaterGraphNode node) {
  if (_nodeCanOpenGalaxy(node)) {
    return context.l10n.theaterNodeBannerOpenGalaxy;
  }
  if ((node.mappedGalaxyNodeId ?? '').trim().isNotEmpty) {
    return context.l10n.theaterNodeBannerHasMapping;
  }
  return context.l10n.theaterNodeBannerFreeform;
}

class _RouteListView extends StatelessWidget {
  const _RouteListView({
    required this.routes,
    required this.selectedRouteId,
    required this.recommendedRouteId,
    required this.onSelect,
    required this.onAdopt,
    required this.onOpenSimulation,
    required this.isAdopting,
    super.key,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final String recommendedRouteId;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
  final VoidCallback? onOpenSimulation;
  final bool isAdopting;

  @override
  Widget build(BuildContext context) => Column(
        children: routes.map((route) {
          final isSelected = route.id == selectedRouteId;
          final isRecommended = route.id == recommendedRouteId;
          return AnimatedContainer(
            duration: DS.durationNormal,
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: isSelected
                  ? Theme.of(context).colorScheme.primaryContainer
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: isSelected
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context)
                        .colorScheme
                        .outlineVariant
                        .withValues(alpha: 0.45),
              ),
            ),
            child: InkWell(
              onTap: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                );
                onSelect(route.id);
              },
              borderRadius: BorderRadius.circular(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final compact = constraints.maxWidth < 420;
                      final titleRow = Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            route.title,
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          if (isRecommended) _MetricPill(label: context.l10n.theaterRouteRecommended),
                        ],
                      );
                      final adoptButton = FilledButton(
                        onPressed: isAdopting ? null : onAdopt,
                        child: Text(isAdopting ? context.l10n.theaterRouteAdopting : context.l10n.theaterRouteAdopt),
                      );
                      final simulateButton = FilledButton.tonalIcon(
                        onPressed: onOpenSimulation,
                        icon: const Icon(Icons.forum_outlined),
                        label: Text(context.l10n.theaterRouteSimulate),
                      );
                      if (compact) {
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            titleRow,
                            if (isSelected) ...[
                              const SizedBox(height: 10),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: [
                                  adoptButton,
                                  simulateButton,
                                ],
                              ),
                            ],
                          ],
                        );
                      }
                      return Row(
                        children: [
                          Expanded(child: titleRow),
                          if (isSelected) ...[
                            const SizedBox(width: 12),
                            simulateButton,
                            const SizedBox(width: 12),
                            adoptButton,
                          ],
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 8),
                  Text(
                    route.summary,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _MetricPill(
                        label: context.l10n.theaterRouteCompletion(_routeCompletionDisplay(context, route, compact: true)),
                        backgroundColor:
                            _routeMetricBackgroundColor(context, route),
                        labelColor: _routeMetricLabelColor(context, route),
                      ),
                      _MetricPill(
                        label: context.l10n.theaterRouteMasteryLabel(_routeMasteryDisplay(context, route, compact: true)),
                        backgroundColor:
                            _routeMetricBackgroundColor(context, route),
                        labelColor: _routeMetricLabelColor(context, route),
                      ),
                      _MetricPill(label: context.l10n.theaterRouteDailyMinutes(route.dailyMinutes.toString())),
                      _MetricPill(label: context.l10n.theaterRouteRiskCount(route.risks.length.toString())),
                      _MetricPill(label: context.l10n.theaterRouteScore(route.routeScore.round().toString())),
                      _MetricPill(
                        label: _routeDataBadgeLabel(context, route),
                        backgroundColor:
                            _routeMetricBackgroundColor(context, route),
                        labelColor: _routeMetricLabelColor(context, route),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    context.l10n.theaterRouteRangePrediction(
                      (route.completionRangeLow * 100).round().toString(),
                      (route.completionRangeHigh * 100).round().toString(),
                      route.masteryRangeLow.round().toString(),
                      route.masteryRangeHigh.round().toString(),
                    ),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                  if (_routeDataNote(context, route).isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      _routeDataNote(context, route),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: route.dataQuality == 'low'
                                ? DS.textTertiary
                                : DS.textSecondary,
                          ),
                    ),
                  ],
                ],
              ),
            ),
          );
        }).toList(),
      );
}

class _RouteComparePager extends StatelessWidget {
  const _RouteComparePager({
    required this.routes,
    required this.selectedRouteId,
    required this.recommendedRouteId,
    required this.pageController,
    required this.onSelect,
    required this.onAdopt,
    required this.onOpenSimulation,
    required this.isAdopting,
    super.key,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final String recommendedRouteId;
  final PageController pageController;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
  final VoidCallback? onOpenSimulation;
  final bool isAdopting;

  @override
  Widget build(BuildContext context) {
    final currentIndex =
        routes.indexWhere((route) => route.id == selectedRouteId);
    final safeIndex = currentIndex < 0 ? 0 : currentIndex;
    final compact = MediaQuery.sizeOf(context).width < 420;
    return Column(
      children: [
        SizedBox(
          height: compact ? 460 : 320,
          child: PageView.builder(
            controller: pageController,
            itemCount: routes.length,
            onPageChanged: (index) {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
              );
              onSelect(routes[index].id);
            },
            itemBuilder: (context, index) {
              final route = routes[index];
              final isRecommended = route.id == recommendedRouteId;
              return Padding(
                padding: const EdgeInsets.only(right: 10),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color:
                        Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: compact
                      ? Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              route.title,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.w800,
                                  ),
                            ),
                            if (isRecommended) ...[
                              const SizedBox(height: 6),
                              _MetricPill(label: context.l10n.theaterRouteRecommendedBaseline),
                            ],
                            const SizedBox(height: 12),
                            Expanded(
                              child: _RouteFlowChain(steps: route.steps),
                            ),
                            const SizedBox(height: 12),
                            Wrap(
                              spacing: 12,
                              children: [
                                _RouteMetricRow(
                                  label: context.l10n.theaterRouteCompletionRate,
                                  value: _routeCompletionDisplay(context, route),
                                ),
                                _RouteMetricRow(
                                  label: context.l10n.theaterRouteMasteryRate,
                                  value: _routeMasteryDisplay(context, route),
                                ),
                                _RouteMetricRow(
                                  label: context.l10n.theaterRouteDailyTime,
                                  value: context.l10n.theaterRouteDailyMinutes(route.dailyMinutes.toString()),
                                ),
                                _RouteMetricRow(
                                  label: context.l10n.theaterRouteRiskLevel,
                                  value: '${route.risks.length}',
                                ),
                                _RouteMetricRow(
                                  label: context.l10n.theaterRouteOverallScore,
                                  value: '${route.routeScore.round()}',
                                ),
                                _RouteMetricRow(
                                  label: context.l10n.theaterRouteDataNote,
                                  value: _routeDataBadgeLabel(context, route),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Text(
                              context.l10n.theaterRouteRangePrediction(
                                (route.completionRangeLow * 100).round().toString(),
                                (route.completionRangeHigh * 100).round().toString(),
                                route.masteryRangeLow.round().toString(),
                                route.masteryRangeHigh.round().toString(),
                              ),
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: DS.textSecondary),
                            ),
                            if (_routeDataNote(context, route).isNotEmpty) ...[
                              const SizedBox(height: 6),
                              Text(
                                _routeDataNote(context, route),
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: DS.textSecondary),
                              ),
                            ],
                            const SizedBox(height: 12),
                            Wrap(
                              spacing: 10,
                              runSpacing: 10,
                              children: [
                                FilledButton.tonalIcon(
                                  onPressed: safeIndex == index
                                      ? onOpenSimulation
                                      : () => onSelect(route.id),
                                  icon: const Icon(Icons.forum_outlined),
                                  label: Text(
                                    safeIndex == index ? context.l10n.theaterRouteSimulateFromCurrent : context.l10n.theaterRouteSimulateAfterSwitch,
                                  ),
                                ),
                                FilledButton(
                                  onPressed: safeIndex == index && !isAdopting
                                      ? onAdopt
                                      : () => onSelect(route.id),
                                  child: Text(
                                    safeIndex == index
                                        ? (isAdopting ? context.l10n.theaterRouteAdopting : context.l10n.theaterRouteAdopt)
                                        : context.l10n.theaterRouteSwitchToThis,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        )
                      : Row(
                          children: [
                            Expanded(
                              child: _RouteFlowChain(steps: route.steps),
                            ),
                            const SizedBox(width: 16),
                            SizedBox(
                              width: 150,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    route.title,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleSmall
                                        ?.copyWith(
                                          fontWeight: FontWeight.w800,
                                        ),
                                  ),
                                  if (isRecommended) ...[
                                    const SizedBox(height: 6),
                                    _MetricPill(label: context.l10n.theaterRouteRecommendedBaseline),
                                  ],
                                  const SizedBox(height: 10),
                                  _RouteMetricRow(
                                    label: context.l10n.theaterRouteCompletionRate,
                                    value: _routeCompletionDisplay(context, route),
                                  ),
                                  _RouteMetricRow(
                                    label: context.l10n.theaterRouteMasteryRate,
                                    value: _routeMasteryDisplay(context, route),
                                  ),
                                  _RouteMetricRow(
                                    label: context.l10n.theaterRouteDailyTime,
                                    value: context.l10n.theaterRouteDailyMinutes(route.dailyMinutes.toString()),
                                  ),
                                  _RouteMetricRow(
                                    label: context.l10n.theaterRouteRiskLevel,
                                    value: '${route.risks.length}',
                                  ),
                                  _RouteMetricRow(
                                    label: context.l10n.theaterRouteOverallScore,
                                    value: '${route.routeScore.round()}',
                                  ),
                                  _RouteMetricRow(
                                    label: context.l10n.theaterRouteDataNote,
                                    value: _routeDataBadgeLabel(context, route),
                                  ),
                                  const SizedBox(height: 10),
                                  Text(
                                    context.l10n.theaterRouteRangePrediction(
                                      (route.completionRangeLow * 100).round().toString(),
                                      (route.completionRangeHigh * 100).round().toString(),
                                      route.masteryRangeLow.round().toString(),
                                      route.masteryRangeHigh.round().toString(),
                                    ),
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodySmall
                                        ?.copyWith(color: DS.textSecondary),
                                  ),
                                  if (_routeDataNote(context, route).isNotEmpty) ...[
                                    const SizedBox(height: 6),
                                    Text(
                                      _routeDataNote(context, route),
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodySmall
                                          ?.copyWith(color: DS.textSecondary),
                                    ),
                                  ],
                                  const Spacer(),
                                  FilledButton.tonalIcon(
                                    onPressed: safeIndex == index
                                        ? onOpenSimulation
                                        : () => onSelect(route.id),
                                    icon: const Icon(Icons.forum_outlined),
                                    label: Text(
                                      safeIndex == index ? context.l10n.theaterRouteSimulateFromCurrent : context.l10n.theaterRouteSimulateAfterSwitch,
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  FilledButton(
                                    onPressed: safeIndex == index && !isAdopting
                                        ? onAdopt
                                        : () => onSelect(route.id),
                                    child: Text(
                                      safeIndex == index
                                          ? (isAdopting ? context.l10n.theaterRouteAdopting : context.l10n.theaterRouteAdopt)
                                          : context.l10n.theaterRouteSwitchToThis,
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
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(
            routes.length,
            (index) => AnimatedContainer(
              duration: DS.durationNormal,
              width: safeIndex == index ? 24 : 8,
              height: 8,
              margin: const EdgeInsets.symmetric(horizontal: 4),
              decoration: BoxDecoration(
                color: safeIndex == index
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context)
                        .colorScheme
                        .outlineVariant
                        .withValues(alpha: 0.55),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _RouteFlowChain extends StatelessWidget {
  const _RouteFlowChain({required this.steps});

  final List<TheaterPathStep> steps;

  @override
  Widget build(BuildContext context) => ListView.separated(
        itemCount: steps.length,
        physics: const NeverScrollableScrollPhysics(),
        itemBuilder: (context, index) {
          final step = steps[index];
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                children: [
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: Theme.of(context).colorScheme.primaryContainer,
                    ),
                    alignment: Alignment.center,
                    child: Text('${index + 1}'),
                  ),
                  if (index < steps.length - 1)
                    Container(
                      width: 2,
                      height: 28,
                      color: Theme.of(context)
                          .colorScheme
                          .outlineVariant
                          .withValues(alpha: 0.6),
                    ),
                ],
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        step.nodeName,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        context.l10n.theaterRouteStepMinutes(step.dayLabel, step.estimatedMinutes.toString()),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
        separatorBuilder: (_, __) => const SizedBox(height: 2),
        shrinkWrap: true,
      );
}

class _RouteMetricRow extends StatelessWidget {
  const _RouteMetricRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final compact = MediaQuery.sizeOf(context).width < 420;
    final labelStyle = Theme.of(context).textTheme.bodySmall?.copyWith(
          color: DS.textSecondary,
        );
    final valueStyle = Theme.of(context).textTheme.labelLarge?.copyWith(
          fontWeight: DS.fontWeightBold,
        );
    if (compact) {
      return Container(
        constraints: const BoxConstraints(minWidth: 108, maxWidth: 160),
        padding: const EdgeInsets.only(bottom: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: labelStyle),
            const SizedBox(height: 4),
            Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: valueStyle,
            ),
          ],
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: labelStyle,
            ),
          ),
          Flexible(
            child: Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.end,
              style: valueStyle,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
    required this.label,
    this.backgroundColor,
    this.labelColor,
  });

  final String label;
  final Color? backgroundColor;
  final Color? labelColor;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: backgroundColor ?? Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.labelMedium?.copyWith(color: labelColor),
        ),
      );
}

class _TheaterDisclaimerBanner extends StatelessWidget {
  const _TheaterDisclaimerBanner({
    required this.message,
    required this.onDismiss,
  });

  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.info.withValues(alpha: 0.09),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: DS.info.withValues(alpha: 0.18),
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded, color: DS.info),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: onDismiss,
              icon: const Icon(Icons.close_rounded),
              tooltip: context.l10n.theaterDismissTooltip,
              visualDensity: VisualDensity.compact,
            ),
          ],
        ),
      );
}

class _CompactRoutePreviewCard extends StatelessWidget {
  const _CompactRoutePreviewCard({
    required this.selectedRoute,
    required this.recommendedRouteId,
    required this.alternatives,
    required this.onOpenPathWorkbench,
  });

  final TheaterPathOption selectedRoute;
  final String recommendedRouteId;
  final List<TheaterPathOption> alternatives;
  final VoidCallback onOpenPathWorkbench;

  @override
  Widget build(BuildContext context) {
    final compareRoute = alternatives.firstWhere(
      (item) => item.id == recommendedRouteId,
      orElse: () => alternatives.firstOrNull ?? selectedRoute,
    );
    final focusSummary = selectedRoute.summary.trim().isNotEmpty
        ? selectedRoute.summary.trim()
        : _buildFallbackSummary(context, selectedRoute);
    final compareSummary = compareRoute.id == selectedRoute.id
        ? null
        : (compareRoute.summary.trim().isNotEmpty
            ? compareRoute.summary.trim()
            : _buildFallbackSummary(context, compareRoute));
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.theaterCompactComparisonTitle,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            focusSummary,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
          ),
          if (compareSummary != null) ...[
            const SizedBox(height: 8),
            Text(
              context.l10n.theaterCompactComparisonSummary(compareSummary),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MetricPill(label: context.l10n.theaterCompactComparisonCurrent(selectedRoute.title)),
              _MetricPill(
                label: context.l10n.theaterCompactComparisonMastery(selectedRoute.estimatedMastery.round().toString()),
              ),
              _MetricPill(label: context.l10n.theaterCompactComparisonTime(selectedRoute.dailyMinutes.toString())),
              if (compareRoute.id != selectedRoute.id)
                _MetricPill(label: context.l10n.theaterCompactComparisonAlt(compareRoute.title)),
            ],
          ),
          const SizedBox(height: 12),
          FilledButton.tonalIcon(
            onPressed: onOpenPathWorkbench,
            icon: const Icon(Icons.route_rounded),
            label: Text(context.l10n.theaterCompactOpenDetail),
          ),
        ],
      ),
    );
  }

  String _buildFallbackSummary(BuildContext context, TheaterPathOption route) {
    if (route.steps.isEmpty) {
      return route.title;
    }
    final first = route.steps.first.nodeName;
    final last = route.steps.last.nodeName;
    if (route.steps.length == 1) {
      return context.l10n.theaterCompactFallbackSingle(first);
    }
    return context.l10n.theaterCompactFallbackMulti(first, last);
  }
}

class _TimelineMetricTile extends StatelessWidget {
  const _TimelineMetricTile({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              value,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: accent,
                  ),
            ),
          ],
        ),
      );
}

class _RouteComparisonCard extends StatelessWidget {
  const _RouteComparisonCard({
    required this.selectedRoute,
    required this.recommendedRouteId,
    required this.alternatives,
  });

  final TheaterPathOption selectedRoute;
  final String recommendedRouteId;
  final List<TheaterPathOption> alternatives;

  @override
  Widget build(BuildContext context) {
    final compareRoute = alternatives.firstWhere(
      (item) => item.id == recommendedRouteId,
      orElse: () => alternatives.first,
    );
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.theaterComparisonTitle,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            context.l10n.theaterComparisonSubtitle,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
          const SizedBox(height: 14),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minWidth: MediaQuery.sizeOf(context).width - 64,
              ),
              child: Table(
                columnWidths: const <int, TableColumnWidth>{
                  0: FlexColumnWidth(1.15),
                  1: FlexColumnWidth(),
                  2: FlexColumnWidth(),
                },
                defaultVerticalAlignment: TableCellVerticalAlignment.middle,
                children: [
                  _comparisonRow(
                    context,
                    context.l10n.theaterComparisonMetric,
                    selectedRoute.title,
                    compareRoute.title,
                    header: true,
                  ),
                  _comparisonRow(
                    context,
                    context.l10n.theaterComparisonEstimatedMastery,
                    '${selectedRoute.estimatedMastery.round()}%',
                    '${compareRoute.estimatedMastery.round()}%',
                  ),
                  _comparisonRow(
                    context,
                    context.l10n.theaterComparisonTimeInvestment,
                    context.l10n.theaterPerDayUnit(selectedRoute.dailyMinutes.toString()),
                    context.l10n.theaterPerDayUnit(compareRoute.dailyMinutes.toString()),
                  ),
                  _comparisonRow(
                    context,
                    context.l10n.theaterComparisonRiskLevel,
                    _routeRiskLabel(context, selectedRoute),
                    _routeRiskLabel(context, compareRoute),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  TableRow _comparisonRow(
    BuildContext context,
    String metric,
    String left,
    String right, {
    bool header = false,
  }) {
    final style = header
        ? Theme.of(context).textTheme.labelLarge?.copyWith(
              fontWeight: FontWeight.w800,
            )
        : Theme.of(context).textTheme.bodySmall?.copyWith(
              height: 1.4,
            );
    return TableRow(
      children: [
        _comparisonCell(metric, style, DS.textSecondary, header: header),
        _comparisonCell(left, style, null, header: header),
        _comparisonCell(right, style, null, header: header),
      ],
    );
  }

  Widget _comparisonCell(
    String text,
    TextStyle? style,
    Color? color, {
    bool header = false,
  }) =>
      Padding(
        padding: EdgeInsets.only(bottom: header ? 10 : 12, right: 8),
        child: Text(
          text,
          style: style?.copyWith(color: color ?? style.color),
        ),
      );

  String _routeRiskLabel(BuildContext context, TheaterPathOption route) {
    if (route.risks.isEmpty) {
      return context.l10n.theaterComparisonRiskLow;
    }
    if (route.risks.length >= 2) {
      return context.l10n.theaterComparisonRiskMediumHigh;
    }
    return context.l10n.theaterComparisonRiskMedium;
  }
}

class _BranchDeltaCard extends StatelessWidget {
  const _BranchDeltaCard({
    required this.baseline,
    required this.branch,
  });

  final TheaterTimelineFrame baseline;
  final TheaterTimelineFrame branch;

  @override
  Widget build(BuildContext context) {
    final masteryDelta = branch.projectedMastery - baseline.projectedMastery;
    final completionDelta =
        branch.projectedCompletionRate - baseline.projectedCompletionRate;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.theaterBranchDeltaTitle,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            '${context.l10n.theaterRouteMasteryRate} ${masteryDelta >= 0 ? '+' : ''}${masteryDelta.round()}% · ${context.l10n.theaterRouteCompletionRate} ${(completionDelta * 100).round()}%',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: masteryDelta >= 0 ? DS.success : DS.warning,
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            '${branch.activeStepTitle ?? context.l10n.theaterBranchDeltaPath} · ${branch.compareLabel ?? context.l10n.theaterBranchDeltaWhatIf}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

class _WhatIfSection extends StatefulWidget {
  const _WhatIfSection({
    required this.route,
    required this.result,
    required this.onRun,
  });

  final TheaterPathOption route;
  final TheaterWhatIfResult? result;
  final ValueChanged<List<String>>? onRun;

  @override
  State<_WhatIfSection> createState() => _WhatIfSectionState();
}

class _WhatIfSectionState extends State<_WhatIfSection> {
  late Set<String> _selectedNodeIds;

  @override
  void initState() {
    super.initState();
    _selectedNodeIds = <String>{
      _defaultCandidate.nodeId,
    };
  }

  TheaterPathStep get _defaultCandidate => widget.route.steps.firstWhere(
        (step) => step.riskLevel != 'low',
        orElse: () => widget.route.steps.first,
      );

  @override
  void didUpdateWidget(covariant _WhatIfSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.route.id != widget.route.id) {
      _selectedNodeIds = <String>{_defaultCandidate.nodeId};
    }
  }

  @override
  Widget build(BuildContext context) {
    final selectedSteps = widget.route.steps
        .where((step) => _selectedNodeIds.contains(step.nodeId))
        .toList();
    final totalPenalty = selectedSteps.fold<double>(
      0,
      (sum, step) => sum + _penaltyForRisk(step.riskLevel),
    );
    final previewMastery =
        (widget.route.estimatedMastery - totalPenalty).clamp(0, 100).toDouble();
    final previewCompletion =
        (widget.route.estimatedCompletionRate - (selectedSteps.length * 0.05))
            .clamp(0.1, 1.0);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.theaterWhatIfTitle,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            context.l10n.theaterWhatIfSubtitle,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: widget.route.steps.map((step) {
              final selected = _selectedNodeIds.contains(step.nodeId);
              return FilterChip(
                selected: selected,
                onSelected: widget.onRun == null
                    ? null
                    : (_) {
                        unawaited(
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.toggle,
                          ),
                        );
                        setState(() {
                          if (selected) {
                            _selectedNodeIds.remove(step.nodeId);
                          } else {
                            _selectedNodeIds.add(step.nodeId);
                          }
                        });
                      },
                label: Text(step.nodeName),
                avatar: Icon(
                  Icons.radio_button_checked_rounded,
                  size: 16,
                  color: selected
                      ? Theme.of(context).colorScheme.primary
                      : Theme.of(context).colorScheme.outline,
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.theaterWhatIfPreviewTitle,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 10),
                _PreviewMetricBar(
                  label: context.l10n.theaterWhatIfPreviewMastery,
                  originalValue: widget.route.estimatedMastery / 100,
                  newValue: previewMastery / 100,
                ),
                const SizedBox(height: 10),
                _PreviewMetricBar(
                  label: context.l10n.theaterWhatIfPreviewCompletion,
                  originalValue: widget.route.estimatedCompletionRate,
                  newValue: previewCompletion,
                ),
                const SizedBox(height: 12),
                Text(
                  _selectedNodeIds.isEmpty
                      ? context.l10n.theaterWhatIfNoNodesSelected
                      : context.l10n.theaterWhatIfNodesSkipped(selectedSteps.map((step) => step.nodeName).join('、')),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.4,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: widget.onRun == null || _selectedNodeIds.isEmpty
                ? null
                : () => widget.onRun!(
                      selectedSteps.isEmpty
                          ? <String>[_defaultCandidate.nodeId]
                          : selectedSteps.map((step) => step.nodeId).toList(),
                    ),
            icon: const Icon(Icons.alt_route),
            label: Text(
              _selectedNodeIds.isEmpty ? context.l10n.theaterWhatIfSelectFirst : context.l10n.theaterWhatIfGenerateFull,
            ),
          ),
          if (widget.result != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.l10n.theaterWhatIfCombinedResult(
                      widget.result!.originalMastery.round().toString(),
                      (widget.result!.originalCompletionRate * 100).round().toString(),
                      widget.result!.predictedMastery.round().toString(),
                      (widget.result!.predictedCompletionRate * 100).round().toString(),
                    ),
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  if ((widget.result!.branchLabel ?? '').isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      widget.result!.branchLabel!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  ...widget.result!.consequences.map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text('• $item'),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.result!.suggestion,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.4,
                        ),
                  ),
                  if (widget.result!.remainingPath.isNotEmpty) ...[
                    const SizedBox(height: 10),
                  Text(
                    context.l10n.theaterWhatIfRemainingPath(widget.result!.remainingPath.map((item) => item.nodeName).join(' → ')),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.4,
                          ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  double _penaltyForRisk(String level) {
    switch (level) {
      case 'high':
        return 12;
      case 'medium':
        return 7;
      default:
        return 4;
    }
  }
}

class _PreviewMetricBar extends StatelessWidget {
  const _PreviewMetricBar({
    required this.label,
    required this.originalValue,
    required this.newValue,
  });

  final String label;
  final double originalValue;
  final double newValue;

  @override
  Widget build(BuildContext context) {
    final improving = newValue >= originalValue;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(child: Text(label)),
            Text(
              '${(newValue * 100).round()}% ${improving ? '↑' : '↓'}',
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: improving
                        ? DS.success
                        : Theme.of(context).colorScheme.error,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            minHeight: 8,
            value: originalValue.clamp(0.0, 1.0),
            color: Theme.of(context).colorScheme.outlineVariant,
            backgroundColor: Theme.of(context).colorScheme.surfaceContainerHigh,
          ),
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            minHeight: 10,
            value: newValue.clamp(0.0, 1.0),
            color: improving ? DS.success : Theme.of(context).colorScheme.error,
            backgroundColor: Theme.of(context).colorScheme.surfaceContainerHigh,
          ),
        ),
      ],
    );
  }
}

class _DiscussionSection extends StatelessWidget {
  const _DiscussionSection({required this.turns});

  final List<TheaterDiscussionTurn> turns;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.theaterDiscussionTitle,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: 12),
            ...turns.map(
              (turn) => Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    CircleAvatar(
                      radius: 18,
                      backgroundColor: DS.brandPrimary.withValues(alpha: 0.14),
                      child: Text(
                        turn.displayName.characters.first,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.primary,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            turn.displayName,
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(fontWeight: DS.fontWeightBold),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            turn.content,
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  height: 1.5,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
}

class _ActualMetricSlider extends StatelessWidget {
  const _ActualMetricSlider({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final double value;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(label)),
              Text('${(value * 100).round()}%'),
            ],
          ),
          Slider(
            value: value.clamp(0.0, 1.0),
            onChanged: onChanged,
          ),
        ],
      );
}

class _SnapshotSection extends StatelessWidget {
  const _SnapshotSection({
    required this.snapshot,
    required this.isSaving,
    required this.onSave,
  });

  final TheaterSnapshot? snapshot;
  final bool isSaving;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 420;
            final button = FilledButton.tonal(
              onPressed: isSaving ? null : onSave,
              child: Text(isSaving ? context.l10n.theaterSnapshotSaving : context.l10n.theaterSnapshotSave),
            );
            final content = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.theaterSnapshotTitle,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  snapshot == null
                      ? context.l10n.theaterSnapshotNoSnapshot
                      : context.l10n.theaterSnapshotSaved(snapshot!.title),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ],
            );
            if (compact) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  content,
                  const SizedBox(height: 12),
                  button,
                ],
              );
            }
            return Row(
              children: [
                Expanded(child: content),
                const SizedBox(width: 12),
                button,
              ],
            );
          },
        ),
      );
}

class _AccuracyCard extends StatelessWidget {
  const _AccuracyCard({
    required this.summary,
    required this.overview,
  })  : tracking = null,
        onRecordActual = null;

  const _AccuracyCard.pending({
    required this.tracking,
    required this.overview,
    required this.onRecordActual,
  }) : summary = null;

  final TheaterAccuracySummary? summary;
  final TheaterAccuracyTracking? tracking;
  final TheaterAccuracyOverview? overview;
  final VoidCallback? onRecordActual;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.theaterAccuracyTitle,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: 8),
            if (summary != null) ...[
              Text(
                context.l10n.theaterAccuracyPredictedActual(
                  (summary!.predictedCompletionRate * 100).round().toString(),
                  summary!.predictedMastery.round().toString(),
                  (summary!.actualCompletionRate * 100).round().toString(),
                  summary!.actualMastery.round().toString(),
                ),
              ),
              const SizedBox(height: 6),
              Text(context.l10n.theaterAccuracyAvgScore((summary!.accuracyScore * 100).round().toString())),
              const SizedBox(height: 8),
              Text(
                summary!.withinPredictedRange
                    ? context.l10n.theaterAccuracyWithinRange
                    : context.l10n.theaterAccuracyOutsideRange,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
            ] else if (tracking != null) ...[
              Text(
                tracking!.summaryHint,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                context.l10n.theaterAccuracyDueDate(tracking!.dueOn),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: 10),
              FilledButton.tonalIcon(
                onPressed: onRecordActual,
                icon: const Icon(Icons.fact_check_outlined),
                label: Text(context.l10n.theaterAccuracyRecordActual),
              ),
            ],
            if (overview != null) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _MetricPill(
                    label: context.l10n.theaterAccuracySampleCount(overview!.sampleCount.toString()),
                  ),
                  _MetricPill(
                    label: context.l10n.theaterAccuracyAvgScore((overview!.avgAccuracyScore * 100).round().toString()),
                  ),
                  _MetricPill(
                    label: context.l10n.theaterAccuracyConfidenceScore((overview!.confidenceScore * 100).round().toString()),
                  ),
                  if (overview!.coverageRate != null)
                    _MetricPill(
                      label: context.l10n.theaterAccuracyCoverageRate((overview!.coverageRate! * 100).round().toString()),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                context.l10n.theaterAccuracyScoreNote,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                overview!.sampleCount == 0
                    ? context.l10n.theaterAccuracyNoSamples
                    : context.l10n.theaterAccuracyHistoryBias(
                        '${overview!.completionBiasMean >= 0 ? '+' : ''}${(overview!.completionBiasMean * 100).round()}%',
                        '${overview!.masteryBiasMean >= 0 ? '+' : ''}${overview!.masteryBiasMean.round()}%',
                      ),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
            ],
          ],
        ),
      );
}

class _AdoptionSuccessOverlay extends StatelessWidget {
  const _AdoptionSuccessOverlay({
    required this.planName,
    required this.planId,
    required this.createdTasks,
    required this.checkpointDates,
    required this.onDismiss,
  });

  final String planName;
  final String planId;
  final List<TheaterTaskBrief> createdTasks;
  final List<Map<String, dynamic>> checkpointDates;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) => ColoredBox(
        color: Colors.black.withValues(alpha: 0.28),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.modal,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          DS.success.withValues(alpha: 0.9),
                          DS.brandPrimary.withValues(alpha: 0.82),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Icon(
                      Icons.check_rounded,
                      color: Colors.white,
                      size: 34,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    context.l10n.theaterAdoptionSynced,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    planName,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                  if (createdTasks.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.l10n.theaterAdoptionFirstWeekTasks,
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 8),
                          ...createdTasks.take(3).map(
                                (task) => Padding(
                                  padding: const EdgeInsets.only(bottom: 4),
                                  child: Text(
                                    '• ${task.title}',
                                    style:
                                        Theme.of(context).textTheme.bodySmall,
                                  ),
                                ),
                              ),
                          if (checkpointDates.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Text(
                              context.l10n.theaterAdoptionCheckpoints(checkpointDates.map((item) => item['date']).join('、')),
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: DS.textSecondary),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      FilledButton(
                        onPressed: () => context.push(
                          PlanRoutes.planDetail.replaceFirst(':id', planId),
                        ),
                        child: Text(context.l10n.theaterAdoptionViewPlan),
                      ),
                      OutlinedButton(
                        onPressed: onDismiss,
                        child: Text(context.l10n.theaterAdoptionContinueExploring),
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
