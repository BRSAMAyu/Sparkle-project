import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/chat_continuity_banner.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
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
          return;
        }
        _triggerAdoptionCelebration();
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
            onPressed: state.snapshot == null ? null : _shareSnapshotSummary,
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
        intensity: SparkleCelebrationIntensity.large,
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
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      if ((widget.initialSourceChatSessionId ?? '')
                          .trim()
                          .isNotEmpty) ...[
                        ChatContinuityBanner(
                          sourceChatSessionId:
                              widget.initialSourceChatSessionId!.trim(),
                          subtitle: '这次推演来自刚才的聊天桥接。你可以随时回到原对话继续追问路径、风险和具体行动。',
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
                      Expanded(
                        child: AnimatedSwitcher(
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
                                  isTimelinePlaying: _isTimelinePlaying,
                                  whatIfResult: state.whatIfResult,
                                  snapshot: state.snapshot,
                                  adoptionResult: state.adoptionResult,
                                  accuracySummary: state.accuracySummary,
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
                                  onRunWhatIf: route == null
                                      ? null
                                      : (nodeId) => unawaited(
                                            ref
                                                .read(theaterProvider.notifier)
                                                .runWhatIfForStep(nodeId),
                                          ),
                                  onSaveSnapshot: () => unawaited(
                                    ref
                                        .read(theaterProvider.notifier)
                                        .saveSnapshot(),
                                  ),
                                  onNodeTap: (node) => unawaited(
                                    _showNodeDetailSheet(
                                      node: node,
                                      selectedRoute: route,
                                      onRunWhatIf: route == null
                                          ? null
                                          : (nodeId) => unawaited(
                                                ref
                                                    .read(
                                                      theaterProvider.notifier,
                                                    )
                                                    .runWhatIfForStep(nodeId),
                                              ),
                                    ),
                                  ),
                                  onEdgeLongPress: (edge, globalPosition) =>
                                      unawaited(
                                    _showEdgeTooltip(edge, globalPosition),
                                  ),
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (_showCelebration && state.adoptionResult != null)
                Positioned.fill(
                  child: _AdoptionSuccessOverlay(
                    planName: state.adoptionResult!.planName,
                    planId: state.adoptionResult!.planId,
                    onDismiss: () => setState(() => _showCelebration = false),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _shareSnapshotSummary() async {
    final state = ref.read(theaterProvider);
    final snapshot = state.snapshot;
    final route = state.selectedRoute;
    final prediction = state.prediction;
    if (snapshot == null || route == null || prediction == null) {
      return;
    }
    await share_plus.SharePlus.instance.share(
      share_plus.ShareParams(
        text:
            '知识推演剧场\n主题：${prediction.topic}\n路径：${route.title}\n摘要：${route.summary}',
      ),
    );
  }

  Future<void> _showNodeDetailSheet({
    required TheaterGraphNode node,
    required TheaterPathOption? selectedRoute,
    required ValueChanged<String>? onRunWhatIf,
  }) async {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    final canRunWhatIf =
        selectedRoute?.steps.any((step) => step.nodeId == node.id) ?? false;
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
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: DS.info.withValues(alpha: 0.14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '让 AI 帮你推演多条学习路径',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            '你可以输入一个学习目标，也可以直接点选下方最近最值得推演的主题。',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: TextField(
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
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: isLoading ? null : onSubmit,
                icon: const Icon(Icons.auto_awesome),
                label: Text(isLoading ? '推演中' : '开始'),
              ),
            ],
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
    required this.isTimelinePlaying,
    required this.whatIfResult,
    required this.snapshot,
    required this.adoptionResult,
    required this.accuracySummary,
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
    required this.onNodeTap,
    required this.onEdgeLongPress,
    super.key,
  });

  final TheaterPrediction prediction;
  final TheaterPathOption? selectedRoute;
  final List<TheaterTimelineFrame> timeline;
  final int timelineIndex;
  final List<String> focusNodeIds;
  final bool isTimelinePlaying;
  final TheaterWhatIfResult? whatIfResult;
  final TheaterSnapshot? snapshot;
  final TheaterAdoptionResult? adoptionResult;
  final TheaterAccuracySummary? accuracySummary;
  final bool isLoading;
  final bool isAdopting;
  final bool isSavingSnapshot;
  final String? error;
  final ValueChanged<String> onRouteSelected;
  final ValueChanged<int> onTimelineSelected;
  final VoidCallback onToggleTimelinePlayback;
  final VoidCallback onResetTimelinePlayback;
  final VoidCallback? onAdopt;
  final ValueChanged<String>? onRunWhatIf;
  final VoidCallback onSaveSnapshot;
  final ValueChanged<TheaterGraphNode> onNodeTap;
  final void Function(TheaterGraphEdge edge, Offset globalPosition)
      onEdgeLongPress;

  @override
  Widget build(BuildContext context) {
    final route = selectedRoute;
    return ListView(
      children: [
        _SectionEntrance(
          delay: 0,
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  prediction.topic,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  '围绕 ${prediction.targetName}，AI 正在帮你比较多条学习路径、关键风险和知识依赖。',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                ),
              ],
            ),
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
              timeline: timeline,
              selectedIndex: timelineIndex,
              turns: prediction.discussionTurns,
              isPlaying: isTimelinePlaying,
              onSelected: onTimelineSelected,
              onTogglePlayback: onToggleTimelinePlayback,
              onReset: onResetTimelinePlayback,
            ),
          ),
        ],
        const SizedBox(height: 14),
        _SectionEntrance(
          delay: 320,
          child: _RouteSection(
            routes: prediction.paths,
            selectedRouteId: route?.id,
            onSelect: onRouteSelected,
            onAdopt: onAdopt,
            isAdopting: isAdopting,
            adoptionResult: adoptionResult,
          ),
        ),
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
            child: _AccuracyCard(summary: accuracySummary!),
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
      Future<void>.delayed(Duration(milliseconds: widget.delay)).then((_) {
        if (!mounted) {
          return;
        }
        setState(() => _visible = true);
      }),
    );
  }

  @override
  Widget build(BuildContext context) => AnimatedSlide(
        duration: DS.durationNormal,
        curve: Curves.easeOutCubic,
        offset: _visible ? Offset.zero : const Offset(0, 0.06),
        child: AnimatedOpacity(
          duration: DS.durationNormal,
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
  });

  final List<TheaterTimelineFrame> timeline;
  final int selectedIndex;
  final List<TheaterDiscussionTurn> turns;
  final bool isPlaying;
  final ValueChanged<int> onSelected;
  final VoidCallback onTogglePlayback;
  final VoidCallback onReset;

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
                '自动播放会按时间顺序推进焦点节点，你也可以手动点选任一阶段并点击图中节点查看详情。',
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
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              value:
                  timeline.isEmpty ? 0 : (selectedIndex + 1) / timeline.length,
              minHeight: 7,
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 96,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: timeline.length,
              separatorBuilder: (_, __) => const SizedBox(width: 10),
              itemBuilder: (context, index) {
                final frame = timeline[index];
                final isSelected = index == selectedIndex;
                return InkWell(
                  onTap: () => onSelected(index),
                  borderRadius: BorderRadius.circular(18),
                  child: Ink(
                    width: 108,
                    decoration: BoxDecoration(
                      color: isSelected
                          ? Theme.of(context).colorScheme.primaryContainer
                          : Theme.of(context)
                              .colorScheme
                              .surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isSelected
                                ? Theme.of(context).colorScheme.primary
                                : Theme.of(context)
                                    .colorScheme
                                    .surfaceContainerHigh,
                          ),
                          child: Icon(
                            Icons.adjust_rounded,
                            size: 16,
                            color: isSelected
                                ? Theme.of(context).colorScheme.onPrimary
                                : Theme.of(context).colorScheme.primary,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          frame.label,
                          style: Theme.of(context).textTheme.labelLarge,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'T${index + 1}',
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          if (summaryTurn != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Text(
                summaryTurn.content,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '当前阶段：${timeline[selectedIndex].label} · 聚焦 ${timeline[selectedIndex].focusNodeIds.length} 个关键节点',
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
    required this.onSelect,
    required this.onAdopt,
    required this.isAdopting,
    required this.adoptionResult,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
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
            Row(
              children: [
                Text(
                  '路径对比',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const Spacer(),
                SegmentedButton<bool>(
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
                ),
              ],
            ),
            const SizedBox(height: 12),
            AnimatedSwitcher(
              duration: DS.durationNormal,
              child: _compareMode
                  ? _RouteComparePager(
                      key: const ValueKey('compare'),
                      routes: widget.routes,
                      selectedRouteId: widget.selectedRouteId,
                      pageController: _pageController,
                      onSelect: widget.onSelect,
                      onAdopt: widget.onAdopt,
                      isAdopting: widget.isAdopting,
                    )
                  : _RouteListView(
                      key: const ValueKey('list'),
                      routes: widget.routes,
                      selectedRouteId: widget.selectedRouteId,
                      onSelect: widget.onSelect,
                      onAdopt: widget.onAdopt,
                      isAdopting: widget.isAdopting,
                    ),
            ),
            if (widget.adoptionResult != null) ...[
              const SizedBox(height: 10),
              Text(
                '已创建计划：${widget.adoptionResult!.planName}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.success,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ],
        ),
      );
}

class _RouteListView extends StatelessWidget {
  const _RouteListView({
    required this.routes,
    required this.selectedRouteId,
    required this.onSelect,
    required this.onAdopt,
    required this.isAdopting,
    super.key,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
  final bool isAdopting;

  @override
  Widget build(BuildContext context) => Column(
        children: routes.map((route) {
          final isSelected = route.id == selectedRouteId;
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
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          route.title,
                          style: Theme.of(context)
                              .textTheme
                              .titleSmall
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                      if (isSelected)
                        FilledButton(
                          onPressed: isAdopting ? null : onAdopt,
                          child: Text(isAdopting ? '采纳中' : '采纳此路径'),
                        ),
                    ],
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
    required this.pageController,
    required this.onSelect,
    required this.onAdopt,
    required this.isAdopting,
    super.key,
  });

  final List<TheaterPathOption> routes;
  final String? selectedRouteId;
  final PageController pageController;
  final ValueChanged<String> onSelect;
  final VoidCallback? onAdopt;
  final bool isAdopting;

  @override
  Widget build(BuildContext context) {
    final currentIndex =
        routes.indexWhere((route) => route.id == selectedRouteId);
    final safeIndex = currentIndex < 0 ? 0 : currentIndex;
    return Column(
      children: [
        SizedBox(
          height: 320,
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
              return Padding(
                padding: const EdgeInsets.only(right: 10),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color:
                        Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Row(
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
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ),
            Text(
              value,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
      );
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

class _WhatIfSection extends StatefulWidget {
  const _WhatIfSection({
    required this.route,
    required this.result,
    required this.onRun,
  });

  final TheaterPathOption route;
  final TheaterWhatIfResult? result;
  final ValueChanged<String>? onRun;

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
                          ? _defaultCandidate.nodeId
                          : selectedSteps.first.nodeId,
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
                    '原始 ${widget.route.estimatedMastery.round()}% / ${(widget.route.estimatedCompletionRate * 100).round()}%'
                    '  →  调整后 ${widget.result!.predictedMastery.round()}% / ${(widget.result!.predictedCompletionRate * 100).round()}%',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
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
        child: Row(
          children: [
            Expanded(
              child: Column(
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
                    snapshot == null
                        ? '把当前推演保存下来，稍后可以继续回看。'
                        : '已保存：${snapshot!.title}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            FilledButton.tonal(
              onPressed: isSaving ? null : onSave,
              child: Text(isSaving ? '保存中' : '保存'),
            ),
          ],
        ),
      );
}

class _AccuracyCard extends StatelessWidget {
  const _AccuracyCard({required this.summary});

  final TheaterAccuracySummary summary;

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
            Text(
              '预测 ${(summary.predictedCompletionRate * 100).round()}% / ${summary.predictedMastery.round()}%，'
              ' 实际 ${(summary.actualCompletionRate * 100).round()}% / ${summary.actualMastery.round()}%',
            ),
            const SizedBox(height: 6),
            Text('准确度 ${(summary.accuracyScore * 100).round()}%'),
          ],
        ),
      );
}

class _AdoptionSuccessOverlay extends StatelessWidget {
  const _AdoptionSuccessOverlay({
    required this.planName,
    required this.planId,
    required this.onDismiss,
  });

  final String planName;
  final String planId;
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
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton(
                          onPressed: () => context.push(
                            PlanRoutes.planDetail.replaceFirst(':id', planId),
                          ),
                          child: const Text('查看计划'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: onDismiss,
                          child: const Text('继续探索'),
                        ),
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
