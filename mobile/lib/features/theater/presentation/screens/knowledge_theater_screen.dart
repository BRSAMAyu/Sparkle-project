import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
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
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/features/theater/presentation/providers/theater_provider.dart';
import 'package:sparkle/features/theater/presentation/widgets/knowledge_theater_graph.dart';

class KnowledgeTheaterScreen extends ConsumerStatefulWidget {
  const KnowledgeTheaterScreen({
    super.key,
    this.initialTopic,
    this.initialTargetNodeId,
    this.initialSourceChatSessionId,
  });

  final String? initialTopic;
  final String? initialTargetNodeId;
  final String? initialSourceChatSessionId;

  @override
  ConsumerState<KnowledgeTheaterScreen> createState() =>
      _KnowledgeTheaterScreenState();
}

class _KnowledgeTheaterScreenState
    extends ConsumerState<KnowledgeTheaterScreen> {
  late final TextEditingController _topicController;
  late final ProviderSubscription<TheaterState> _theaterSubscription;
  late final TheaterNotifier _theaterNotifier;
  Timer? _timelinePlaybackTimer;
  bool _showCelebration = false;
  bool _playCelebration = false;
  bool _isTimelinePlaying = false;
  String? _selectedNodeId;

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
      if ((widget.initialTopic ?? '').trim().isNotEmpty) {
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
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    await ref.read(theaterProvider.notifier).generatePrediction(
          topic: topic.trim(),
          targetNodeId: widget.initialTargetNodeId,
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
        title: const Text('知识推演剧场'),
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
                    final compactHeight = constraints.maxHeight < 720;
                    final predictionBody = AnimatedSwitcher(
                      duration: DS.durationNormal,
                      switchInCurve: Curves.easeOutCubic,
                      switchOutCurve: Curves.easeInCubic,
                      child: prediction == null
                          ? _TheaterIntroState(
                              key: const ValueKey('theater-intro'),
                              isLoading: state.isLoading,
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
                                ref
                                    .read(theaterProvider.notifier)
                                    .clearError();
                              },
                            )
                          : _PredictionView(
                              key: ValueKey(prediction.predictionId),
                              prediction: prediction,
                              selectedRoute: route,
                              timeline: timeline,
                              timelineIndex: timelineIndex,
                              focusNodeIds: focusNodeIds,
                              selectedNodeId: _selectedNodeId,
                              isTimelinePlaying: _isTimelinePlaying,
                              recommendedRouteId: prediction.recommendedRouteId,
                              whatIfResult: state.whatIfResult,
                              snapshot: state.snapshot,
                              adoptionResult: state.adoptionResult,
                              accuracySummary: state.accuracySummary,
                              accuracyTracking: prediction.accuracyTracking,
                              isLoading: state.isLoading,
                              isAdopting: state.isAdopting,
                              isSavingSnapshot: state.isSavingSnapshot,
                              error: state.error,
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
                              onResetTimelinePlayback: _resetTimelinePlayback,
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
                              onRunWhatIf: route == null
                                  ? null
                                  : (nodeIds) => unawaited(
                                        ref
                                            .read(theaterProvider.notifier)
                                            .runWhatIfForSteps(nodeIds),
                                      ),
                              onSaveSnapshot: () => unawaited(
                                ref.read(theaterProvider.notifier).saveSnapshot(),
                              ),
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
                    );

                    final contentChildren = <Widget>[
                      if ((widget.initialSourceChatSessionId ?? '')
                          .trim()
                          .isNotEmpty) ...[
                        ChatContinuityBanner(
                          sourceChatSessionId:
                              widget.initialSourceChatSessionId!.trim(),
                          kind: ChatContinuityKind.journey,
                          subtitle:
                              '这次推演承接了你刚才的探索流程。你可以随时回到原对话，继续追问路径、风险和具体行动。',
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

                    if (compactHeight) {
                      return ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          ...contentChildren,
                          SizedBox(
                            height: math.max(
                              420,
                              constraints.maxHeight - 96,
                            ),
                            child: predictionBody,
                          ),
                        ],
                      );
                    }

                    return Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          ...contentChildren,
                          Expanded(child: predictionBody),
                        ],
                      ),
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
        description: '推演主题：${prediction.topic}',
        metadata: <String, dynamic>{
          'progress': ((shareRoute?.estimatedCompletionRate ?? 0.72) * 100)
              .round(),
          'mastery': (shareRoute?.estimatedMastery ??
                  shareNode?.predictedMastery ??
                  72)
              .round(),
          'learning_time': shareRoute?.dailyMinutes ?? prediction.horizonDays,
          'connections': prediction.graphEdges.length,
        },
        shareMessage:
            '我刚在 Sparkle 推演了一条学习路径：${prediction.topic}\n${shareRoute?.title ?? prediction.targetName}\n${shareRoute?.summary ?? '先把关键节点和风险看清楚，再决定怎么学。'}',
      ),
      onGenerateCard: (payload) =>
          SharePosterService().generatePoster(context, payload),
      onCommunityShare: () => unawaited(
        showShareResourceSheet(
          context,
          resourceType: state.adoptionResult != null
              ? 'plan'
              : 'knowledge_node',
          resourceId:
              state.adoptionResult?.planId ??
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
                '记录 7 天后的真实表现',
                style: Theme.of(sheetContext).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                '回填真实完成率和掌握度后，剧场会给你一份预测校准反馈。',
                style: Theme.of(sheetContext).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 18),
              ValueListenableBuilder<double>(
                valueListenable: completionController,
                builder: (context, value, _) => _ActualMetricSlider(
                  label: '真实完成率',
                  value: value,
                  onChanged: (next) => completionController.value = next,
                ),
              ),
              const SizedBox(height: 12),
              ValueListenableBuilder<double>(
                valueListenable: masteryController,
                builder: (context, value, _) => _ActualMetricSlider(
                  label: '真实掌握度',
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
                      child: const Text('提交校准'),
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

  Future<void> _showNodeDetailSheet({
    required TheaterGraphNode node,
    required TheaterPathOption? selectedRoute,
    required ValueChanged<String>? onRunWhatIf,
  }) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    final canRunWhatIf =
        selectedRoute?.steps.any((step) => step.nodeId == node.id) ?? false;
    final matchedStep = selectedRoute?.steps
        .where((step) => step.nodeId == node.id)
        .firstOrNull;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (sheetContext) {
        final scheme = Theme.of(sheetContext).colorScheme;
        final delta = node.predictedMastery - node.currentMastery;
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  node.name,
                  style:
                      Theme.of(sheetContext).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                ),
                const SizedBox(height: 8),
                Text(
                  node.description.isEmpty
                      ? '这个节点是当前推演中的关键知识点。'
                      : node.description,
                  style: Theme.of(sheetContext).textTheme.bodyMedium?.copyWith(
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
                      label: '当前掌握度',
                      value: '${node.currentMastery.round()}%',
                    ),
                    _NodeStatChip(
                      label: '预测掌握度',
                      value: '${node.predictedMastery.round()}%',
                    ),
                    _NodeStatChip(
                      label: '变化',
                      value: '${delta >= 0 ? '+' : ''}${delta.round()}%',
                      accent: delta >= 0 ? DS.success : scheme.error,
                    ),
                    _NodeStatChip(
                      label: '风险',
                      value: _riskLabel(node.riskLevel),
                      accent: _riskColor(node.riskLevel, scheme),
                    ),
                  ],
                ),
                if (matchedStep != null) ...[
                  const SizedBox(height: 18),
                  Text(
                    '它在当前路径里的作用',
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
                          '${matchedStep.dayLabel} · 第 ${matchedStep.index} 步',
                          style: Theme.of(sheetContext)
                              .textTheme
                              .labelLarge
                              ?.copyWith(
                                color: _riskColor(node.riskLevel, scheme),
                                fontWeight: FontWeight.w700,
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
                          '下一步动作：先用约 ${matchedStep.estimatedMinutes} 分钟处理这个节点，再进入后续步骤。',
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
                      child: const Text('开始 What-If'),
                    ),
                    OutlinedButton(
                      onPressed: () {
                        Navigator.of(sheetContext).pop();
                        unawaited(
                          context.push(
                            GalaxyRoutes.knowledgeDetail.replaceFirst(
                              ':id',
                              node.id,
                            ),
                          ),
                        );
                      },
                      child: const Text('查看 Galaxy'),
                    ),
                  ],
                ),
                if (!canRunWhatIf) ...[
                  const SizedBox(height: 12),
                  Text(
                    '这个节点当前不在已选路径的可推演步骤里，所以暂时不能直接做 What-If。',
                    style: Theme.of(sheetContext).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ],
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
                  _relationLabel(edge.relationType),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  '关系强度 ${(edge.strength * 100).round()}%',
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

  String _riskLabel(String level) {
    switch (level) {
      case 'high':
        return '高风险';
      case 'medium':
        return '中风险';
      default:
        return '低风险';
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

  String _relationLabel(String relationType) => switch (relationType) {
        'prerequisite' => '前置依赖',
        'explains' => '解释关系',
        'supports' => '支持关系',
        'contradicts' => '矛盾关系',
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
  const _SelectedNodeBanner({required this.node});

  final TheaterGraphNode node;

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
            '已选节点 · ${node.name}',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: accent,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            node.description.isEmpty ? '点击节点可查看详细推演说明。' : node.description,
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
                label: '当前',
                value: '${node.currentMastery.round()}%',
                accent: accent,
              ),
              _NodeStatChip(
                label: '预测',
                value: '${node.predictedMastery.round()}%',
                accent: accent,
              ),
              _NodeStatChip(
                label: '提升',
                value:
                    '${masteryDelta >= 0 ? '+' : ''}${masteryDelta.round()}%',
                accent: masteryDelta >= 0 ? DS.success : DS.error,
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
      eyebrow: '推演决策面板',
      title: '先定目标，再看清多条路径',
      subtitle: '先确定想推进的目标，再比较切入方式、主要风险和每日投入，最后决定要不要采纳这条路径。',
      metrics: <MirofishStageMetric>[
        MirofishStageMetric(
          label: '当前目标',
          value: controller.text.trim().isEmpty ? '等待输入' : controller.text.trim(),
          accent: DS.info,
          icon: Icons.flag_rounded,
        ),
        MirofishStageMetric(
          label: '推荐切入',
          value: topSuggestions.isEmpty ? '输入后即可开始' : topSuggestions.first.topic,
          accent: DS.warning,
          icon: Icons.lightbulb_rounded,
        ),
        MirofishStageMetric(
          label: '输出结果',
          value: '路径 + 风险 + 检查点',
          accent: DS.success,
          icon: Icons.route_rounded,
        ),
      ],
      primaryLabel: isLoading ? '推演中...' : '开始推演',
      onPrimaryTap: isLoading ? null : onSubmit,
      secondaryLabel:
          topSuggestions.length > 1 ? '试试 ${topSuggestions[1].topic}' : null,
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
                  hintText: '例如：两周内掌握线性代数的特征值部分',
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
                label: Text(isLoading ? '推演中' : '生成'),
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

class _TheaterIntroState extends StatelessWidget {
  const _TheaterIntroState({
    required this.isLoading,
    required this.latestSnapshot,
    required this.suggestions,
    required this.error,
    required this.onStartFirstPrediction,
    required this.onRetry,
    required this.onChangeTarget,
    super.key,
  });

  final bool isLoading;
  final TheaterSnapshot? latestSnapshot;
  final List<SimulationSeedModel> suggestions;
  final String? error;
  final VoidCallback onStartFirstPrediction;
  final VoidCallback onRetry;
  final VoidCallback onChangeTarget;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const _PredictionLoadingState();
    }

    return ListView(
      children: [
        if (error != null) ...[
          _TheaterErrorCard(
            message: error!,
            onRetry: onRetry,
            onSecondary: onChangeTarget,
            secondaryLabel: '换个目标',
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
                '选一个目标，AI 帮你看清多条路径',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 10),
              Text(
                '1. 选择一个目标\n2. AI 推演多条学习路径\n3. 采纳最适合你的方案并同步到 Sprint',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.55,
                    ),
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: onStartFirstPrediction,
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('开始第一次推演'),
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
                  '最近一次推演',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 10),
                Text(
                  latestSnapshot!.title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
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
                  '从这些主题开始更顺手',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
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
    required this.accuracyTracking,
    required this.isLoading,
    required this.isAdopting,
    required this.isSavingSnapshot,
    required this.error,
    required this.onRouteSelected,
    required this.onTimelineSelected,
    required this.onToggleTimelinePlayback,
    required this.onResetTimelinePlayback,
    required this.onAdopt,
    required this.onRunWhatIf,
    required this.onSaveSnapshot,
    required this.onRecordActual,
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
  final TheaterAccuracyTracking? accuracyTracking;
  final bool isLoading;
  final bool isAdopting;
  final bool isSavingSnapshot;
  final String? error;
  final ValueChanged<String> onRouteSelected;
  final ValueChanged<int> onTimelineSelected;
  final VoidCallback onToggleTimelinePlayback;
  final VoidCallback onResetTimelinePlayback;
  final VoidCallback? onAdopt;
  final ValueChanged<List<String>>? onRunWhatIf;
  final VoidCallback onSaveSnapshot;
  final VoidCallback onRecordActual;
  final ValueChanged<TheaterGraphNode> onNodeTap;
  final void Function(TheaterGraphEdge edge, Offset globalPosition)
      onEdgeLongPress;

  @override
  Widget build(BuildContext context) {
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
    return ListView(
      children: [
        _SectionEntrance(
          delay: 0,
          child: MirofishStageHeader(
            icon: Icons.auto_graph_rounded,
            eyebrow: '推演决策面板',
            title: prediction.topic,
            subtitle: route == null
                ? '围绕 ${prediction.targetName}，先看推荐路径、关键风险和知识依赖，再决定采纳哪一种方案。'
                : '当前正在查看「${route.title}」，重点是 ${route.summary}',
            metrics: <MirofishStageMetric>[
              MirofishStageMetric(
                label: '推荐路径',
                value: prediction.paths
                        .firstWhere(
                          (item) => item.id == prediction.recommendedRouteId,
                          orElse: () => prediction.paths.first,
                        )
                        .title,
                accent: DS.success,
                icon: Icons.star_rounded,
              ),
              MirofishStageMetric(
                label: '预计掌握度',
                value:
                    '${(route ?? prediction.paths.firstWhere((item) => item.id == prediction.recommendedRouteId, orElse: () => prediction.paths.first)).estimatedMastery.round()}%',
                accent: DS.info,
                icon: Icons.stacked_line_chart_rounded,
              ),
              MirofishStageMetric(
                label: '主要风险',
                value: _headlineRisk(
                  route ??
                      prediction.paths.firstWhere(
                        (item) => item.id == prediction.recommendedRouteId,
                        orElse: () => prediction.paths.first,
                      ),
                ),
                accent: DS.warning,
                icon: Icons.warning_amber_rounded,
              ),
            ],
            primaryLabel: route == null ? '查看推荐路径' : '采纳当前路径',
            onPrimaryTap: route == null
                ? () => onRouteSelected(prediction.recommendedRouteId)
                : onAdopt,
            accent: DS.brandPrimary,
          ),
        ),
        const SizedBox(height: 14),
        _SectionEntrance(
          delay: 120,
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      '关系图谱',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: Theme.of(context)
                            .colorScheme
                            .surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        ' ${prediction.graphNodes.length} 节点',
                        style: Theme.of(context).textTheme.labelMedium,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (selectedNode != null) ...[
                  _SelectedNodeBanner(node: selectedNode),
                  const SizedBox(height: 12),
                ],
                ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: InteractiveViewer(
                    minScale: 0.9,
                    maxScale: 2.2,
                    boundaryMargin: const EdgeInsets.all(32),
                    child: KnowledgeTheaterGraph(
                      nodes: prediction.graphNodes,
                      edges: prediction.graphEdges,
                      focusNodeIds: focusNodeIds,
                      selectedNodeId: selectedNodeId,
                      routeNodeIds: route?.steps
                              .map((step) => step.nodeId)
                              .toList() ??
                          const <String>[],
                      onNodeTap: onNodeTap,
                      onEdgeLongPress: onEdgeLongPress,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        if (timeline.isNotEmpty) ...[
          const SizedBox(height: 14),
          _SectionEntrance(
            delay: 220,
            child: _TimelineSection(
              timeline: routeTimeline,
              selectedIndex: safeTimelineIndex,
              turns: prediction.discussionTurns,
              isPlaying: isTimelinePlaying,
              onSelected: onTimelineSelected,
              onTogglePlayback: onToggleTimelinePlayback,
              onReset: onResetTimelinePlayback,
              branchTimeline: whatIfResult?.branchTimeline ?? const [],
            ),
          ),
        ],
        const SizedBox(height: 14),
        _SectionEntrance(
          delay: 320,
          child: _RouteSection(
            routes: prediction.paths,
            selectedRouteId: route?.id,
            recommendedRouteId: recommendedRouteId,
            onSelect: onRouteSelected,
            onAdopt: onAdopt,
            isAdopting: isAdopting,
            adoptionResult: adoptionResult,
          ),
        ),
        if (route != null && prediction.paths.length > 1) ...[
          const SizedBox(height: 14),
          _SectionEntrance(
            delay: 380,
            child: _RouteComparisonCard(
              selectedRoute: route,
              recommendedRouteId: recommendedRouteId,
              alternatives: prediction.paths.where((item) => item.id != route.id).toList(),
            ),
          ),
        ],
        if (route != null) ...[
          const SizedBox(height: 14),
          _SectionEntrance(
            delay: 420,
            child: _WhatIfSection(
              route: route,
              result: whatIfResult,
              onRun: onRunWhatIf,
            ),
          ),
        ],
        const SizedBox(height: 14),
        _SectionEntrance(
          delay: 520,
          child: _DiscussionSection(turns: prediction.discussionTurns),
        ),
        const SizedBox(height: 14),
        _SectionEntrance(
          delay: 620,
          child: _SnapshotSection(
            snapshot: snapshot,
            isSaving: isSavingSnapshot,
            onSave: onSaveSnapshot,
          ),
        ),
        if (accuracySummary != null) ...[
          const SizedBox(height: 14),
          _SectionEntrance(
            delay: 720,
            child: _AccuracyCard(summary: accuracySummary),
          ),
        ] else if (accuracyTracking != null) ...[
          const SizedBox(height: 14),
          _SectionEntrance(
            delay: 720,
            child: _AccuracyCard.pending(
              tracking: accuracyTracking,
              onRecordActual: onRecordActual,
            ),
          ),
        ],
        if (error != null) ...[
          const SizedBox(height: 14),
          _TheaterErrorCard(
            message: error!,
          ),
        ],
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
                        fontWeight: FontWeight.w600,
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
                    label: const Text('重试'),
                  ),
                if (onSecondary != null)
                  OutlinedButton(
                    onPressed: onSecondary,
                    child: Text(secondaryLabel ?? '知道了'),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _PredictionLoadingState extends StatelessWidget {
  const _PredictionLoadingState();

  @override
  Widget build(BuildContext context) => ListView(
        children: [
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AI 正在分析知识结构...',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 10),
                Text(
                  '节点会逐步亮起，路径卡片和专家讨论会依次出现。',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
                const SizedBox(height: 20),
                const _SkeletonGraphStage(),
              ],
            ),
          ),
        ],
      );
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

class _SectionEntrance extends StatefulWidget {
  const _SectionEntrance({
    required this.child,
    required this.delay,
  });

  final Widget child;
  final int delay;

  @override
  State<_SectionEntrance> createState() => _SectionEntranceState();
}

class _SectionEntranceState extends State<_SectionEntrance> {
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    unawaited(
      Future<void>.delayed(
        Duration(milliseconds: widget.delay > 140 ? 140 : widget.delay),
      ).then((_) {
        if (!mounted) {
          return;
        }
        setState(() => _visible = true);
      }),
    );
  }

  @override
  Widget build(BuildContext context) => AnimatedSlide(
        duration: context.reduceMotion ? Duration.zero : DS.durationNormal,
        curve: Curves.easeOutCubic,
        offset: _visible ? Offset.zero : const Offset(0, 0.06),
        child: AnimatedOpacity(
          duration: context.reduceMotion ? Duration.zero : DS.durationNormal,
          opacity: _visible ? 1 : 0,
          child: widget.child,
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
                '推演时间轴',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                '现在可以按天拖动预测进度，直接对比基线路径和 What-If 分支的差异。',
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
                    label: Text(isPlaying ? '暂停播放' : '自动播放'),
                  ),
                  OutlinedButton.icon(
                    onPressed: onReset,
                    icon: const Icon(Icons.restart_alt_rounded),
                    label: const Text('回到起点'),
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
                    currentFrame?.label ?? '当前阶段',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: DS.brandPrimary,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    currentFrame?.activeStepTitle ?? '等待路径生成',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    currentFrame?.compareLabel ?? '基线预测',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                  if (summaryTurn != null) ...[
                    const SizedBox(height: 10),
                    Text(
                      '讲到这里',
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: DS.textSecondary,
                            fontWeight: FontWeight.w700,
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
                    label: '当前预测掌握度',
                    value:
                        '${timeline[selectedIndex].projectedMastery.round()}%',
                    accent: DS.success,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _TimelineMetricTile(
                    label: '当前预测完成率',
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
              '当前阶段：${currentFrame?.label ?? ''} · ${currentFrame?.activeStepTitle ?? '等待推演'} · ${currentFrame?.compareLabel ?? ''}',
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
    required this.isAdopting,
    required this.adoptionResult,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final String recommendedRouteId;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
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
                  segments: const [
                    ButtonSegment<bool>(
                      value: false,
                      label: Text('列表'),
                    ),
                    ButtonSegment<bool>(
                      value: true,
                      label: Text('对比'),
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
                        '路径对比',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
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
                      '路径对比',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
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
                      isAdopting: widget.isAdopting,
                    )
                  : _RouteListView(
                      key: const ValueKey('list'),
                      routes: widget.routes,
                      selectedRouteId: widget.selectedRouteId,
                      recommendedRouteId: widget.recommendedRouteId,
                      onSelect: widget.onSelect,
                      onAdopt: widget.onAdopt,
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
                      '已创建计划：${widget.adoptionResult!.planName}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.success,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    if (widget.adoptionResult!.createdTasks.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        '首周任务：${widget.adoptionResult!.createdTasks.take(3).map((item) => item.title).join('、')}',
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

String _headlineRisk(TheaterPathOption route) {
  if (route.risks.isEmpty) {
    return '整体可控';
  }
  final firstRisk = route.risks.first.trim();
  if (firstRisk.isEmpty) {
    return '需要留意节奏';
  }
  return firstRisk;
}

class _RouteListView extends StatelessWidget {
  const _RouteListView({
    required this.routes,
    required this.selectedRouteId,
    required this.recommendedRouteId,
    required this.onSelect,
    required this.onAdopt,
    required this.isAdopting,
    super.key,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final String recommendedRouteId;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
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
                          if (isRecommended) const _MetricPill(label: '推荐'),
                        ],
                      );
                      final adoptButton = FilledButton(
                        onPressed: isAdopting ? null : onAdopt,
                        child: Text(isAdopting ? '采纳中' : '采纳此路径'),
                      );
                      if (compact) {
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            titleRow,
                            if (isSelected) ...[
                              const SizedBox(height: 10),
                              adoptButton,
                            ],
                          ],
                        );
                      }
                      return Row(
                        children: [
                          Expanded(child: titleRow),
                          if (isSelected) ...[
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
                        label:
                            '完成率 ${(route.estimatedCompletionRate * 100).round()}%',
                      ),
                      _MetricPill(
                        label: '掌握度 ${route.estimatedMastery.round()}%',
                      ),
                      _MetricPill(label: '日均 ${route.dailyMinutes} 分钟'),
                      _MetricPill(label: '${route.risks.length} 个风险点'),
                      _MetricPill(label: '综合 ${route.routeScore.round()} 分'),
                    ],
                  ),
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
    required this.isAdopting,
    super.key,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final String recommendedRouteId;
  final PageController pageController;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
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
                              const _MetricPill(label: '推荐基线'),
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
                                  label: '完成率',
                                  value:
                                      '${(route.estimatedCompletionRate * 100).round()}%',
                                ),
                                _RouteMetricRow(
                                  label: '掌握度',
                                  value: '${route.estimatedMastery.round()}%',
                                ),
                                _RouteMetricRow(
                                  label: '日均时间',
                                  value: '${route.dailyMinutes} 分钟',
                                ),
                                _RouteMetricRow(
                                  label: '风险数',
                                  value: '${route.risks.length}',
                                ),
                                _RouteMetricRow(
                                  label: '综合分',
                                  value: '${route.routeScore.round()}',
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            FilledButton(
                              onPressed: safeIndex == index && !isAdopting
                                  ? onAdopt
                                  : () => onSelect(route.id),
                              child: Text(
                                safeIndex == index
                                    ? (isAdopting ? '采纳中' : '采纳此路径')
                                    : '切换到此路径',
                              ),
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
                                    const _MetricPill(label: '推荐基线'),
                                  ],
                                  const SizedBox(height: 10),
                                  _RouteMetricRow(
                                    label: '完成率',
                                    value:
                                        '${(route.estimatedCompletionRate * 100).round()}%',
                                  ),
                                  _RouteMetricRow(
                                    label: '掌握度',
                                    value: '${route.estimatedMastery.round()}%',
                                  ),
                                  _RouteMetricRow(
                                    label: '日均时间',
                                    value: '${route.dailyMinutes} 分钟',
                                  ),
                                  _RouteMetricRow(
                                    label: '风险数',
                                    value: '${route.risks.length}',
                                  ),
                                  _RouteMetricRow(
                                    label: '综合分',
                                    value: '${route.routeScore.round()}',
                                  ),
                                  const Spacer(),
                                  FilledButton(
                                    onPressed: safeIndex == index && !isAdopting
                                        ? onAdopt
                                        : () => onSelect(route.id),
                                    child: Text(
                                      safeIndex == index
                                          ? (isAdopting ? '采纳中' : '采纳此路径')
                                          : '切换到此路径',
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
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${step.dayLabel} · ${step.estimatedMinutes} 分钟',
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
          fontWeight: FontWeight.w700,
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
  const _MetricPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelMedium,
        ),
      );
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
            '路径对比',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            '把当前方案和另一条代表性路径放在一起比较，更容易判断该走稳一点还是快一点。',
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
                    '指标',
                    selectedRoute.title,
                    compareRoute.title,
                    header: true,
                  ),
                  _comparisonRow(
                    context,
                    '预计掌握度',
                    '${selectedRoute.estimatedMastery.round()}%',
                    '${compareRoute.estimatedMastery.round()}%',
                  ),
                  _comparisonRow(
                    context,
                    '时间投入',
                    '${selectedRoute.dailyMinutes} 分/天',
                    '${compareRoute.dailyMinutes} 分/天',
                  ),
                  _comparisonRow(
                    context,
                    '风险等级',
                    _routeRiskLabel(selectedRoute),
                    _routeRiskLabel(compareRoute),
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

  String _routeRiskLabel(TheaterPathOption route) {
    if (route.risks.isEmpty) {
      return '低';
    }
    if (route.risks.length >= 2) {
      return '中高';
    }
    return '中';
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
            'What-If 分支对比',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            '掌握度 ${masteryDelta >= 0 ? '+' : ''}${masteryDelta.round()}% · 完成率 ${(completionDelta * 100).round()}%',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: masteryDelta >= 0 ? DS.success : DS.warning,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            '${branch.activeStepTitle ?? '分支路径'} · ${branch.compareLabel ?? 'What-If'}',
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
            'What-if 沙盘',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            '点选想跳过的节点，先看预计影响，再生成完整推演结果。',
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
                  '预计影响预览',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 10),
                _PreviewMetricBar(
                  label: '掌握度',
                  originalValue: widget.route.estimatedMastery / 100,
                  newValue: previewMastery / 100,
                ),
                const SizedBox(height: 10),
                _PreviewMetricBar(
                  label: '完成率',
                  originalValue: widget.route.estimatedCompletionRate,
                  newValue: previewCompletion,
                ),
                const SizedBox(height: 12),
                Text(
                  _selectedNodeIds.isEmpty
                      ? '当前没有标记跳过节点，保持原始路径。'
                      : '你已标记跳过 ${selectedSteps.map((step) => step.nodeName).join('、')}。',
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
              _selectedNodeIds.isEmpty ? '先选择一个节点' : '生成完整 What-If 结果',
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
                    '原始 ${widget.result!.originalMastery.round()}% / ${(widget.result!.originalCompletionRate * 100).round()}%'
                    '  →  调整后 ${widget.result!.predictedMastery.round()}% / ${(widget.result!.predictedCompletionRate * 100).round()}%',
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
                      '分支剩余路径：${widget.result!.remainingPath.map((item) => item.nodeName).join(' → ')}',
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
                    fontWeight: FontWeight.w700,
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
              '专家圆桌',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
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
                          fontWeight: FontWeight.w700,
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
                                ?.copyWith(fontWeight: FontWeight.w700),
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
              child: Text(isSaving ? '保存中' : '保存'),
            );
            final content = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '保存快照',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  snapshot == null ? '把当前推演保存下来，稍后可以继续回看。' : '已保存：${snapshot!.title}',
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
  })  : tracking = null,
        onRecordActual = null;

  const _AccuracyCard.pending({
    required this.tracking,
    required this.onRecordActual,
  }) : summary = null;

  final TheaterAccuracySummary? summary;
  final TheaterAccuracyTracking? tracking;
  final VoidCallback? onRecordActual;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '预测校准',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 8),
            if (summary != null) ...[
              Text(
                '预测 ${(summary!.predictedCompletionRate * 100).round()}% / ${summary!.predictedMastery.round()}%，'
                ' 实际 ${(summary!.actualCompletionRate * 100).round()}% / ${summary!.actualMastery.round()}%',
              ),
              const SizedBox(height: 6),
              Text('准确度 ${(summary!.accuracyScore * 100).round()}%'),
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
                '建议回填日期：${tracking!.dueOn}',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 10),
              FilledButton.tonalIcon(
                onPressed: onRecordActual,
                icon: const Icon(Icons.fact_check_outlined),
                label: const Text('记录实际表现'),
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
                    '已同步到你的 Sprint',
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
                            '首周任务',
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
                              '检查点：${checkpointDates.map((item) => item['date']).join('、')}',
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
                        child: const Text('查看计划'),
                      ),
                      OutlinedButton(
                        onPressed: onDismiss,
                        child: const Text('继续探索'),
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
