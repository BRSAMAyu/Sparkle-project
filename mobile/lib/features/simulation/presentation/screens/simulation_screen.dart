import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/chat_continuity_banner.dart';
import 'package:sparkle/features/mirofish/presentation/support/mirofish_milestone_service.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/presentation/widgets/simulation_chat_bubble.dart';
import 'package:sparkle/features/theater/theater_routes.dart';

class SimulationScreen extends ConsumerStatefulWidget {
  const SimulationScreen({
    super.key,
    this.initialTopic,
    this.initialScenarioKey,
    this.initialSourceChatSessionId,
  });

  final String? initialTopic;
  final String? initialScenarioKey;
  final String? initialSourceChatSessionId;

  @override
  ConsumerState<SimulationScreen> createState() => _SimulationScreenState();
}

class _SimulationScreenState extends ConsumerState<SimulationScreen> {
  static const Map<String, String> _scenarioLabels = {
    'study_group': '虚拟学习小组',
    'knowledge_debate': '知识辩论',
    'historical_roleplay': '历史角色扮演',
    'socratic_dialogue': '苏格拉底式对话',
    'case_analysis': '案例拆解',
    'what_if_path': 'What-If 推演',
    'concept_map_build': '概念图共建',
    'error_diagnosis': '错因诊断',
  };

  final _topicController = TextEditingController();
  final _interactionController = TextEditingController();
  final _roundsScrollController = ScrollController();
  late String _selectedScenarioKey;
  late final ProviderSubscription<SimulationState> _simulationSubscription;
  bool _isPlaybackPaused = false;
  bool _isInsightExpanded = false;
  List<SimulationParticipantModel>? _pausedParticipants;
  List<SimulationRoundModel>? _pausedRounds;
  String? _pausedInsightSummary;
  String? _pausedInteractionPrompt;
  List<String>? _pausedSuggestedReplies;

  @override
  void initState() {
    super.initState();
    _selectedScenarioKey = widget.initialScenarioKey ?? 'study_group';
    _simulationSubscription = ref.listenManual<SimulationState>(
      simulationProvider,
      (previous, next) {
        final previousRoundCount = previous?.liveRounds.length ?? 0;
        final nextRoundCount = next.liveRounds.length;
        if (nextRoundCount > previousRoundCount && !_isPlaybackPaused) {
          unawaited(
            SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
          );
          _scrollToLatestRound();
        }

        final previousParticipantCount = previous?.liveParticipants.length ?? 0;
        final nextParticipantCount = next.liveParticipants.length;
        if (nextParticipantCount > previousParticipantCount &&
            !_isPlaybackPaused) {
          unawaited(
            SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
          );
        }

        final previousSession = previous?.session;
        final nextSession = next.session;
        final completedNow = nextSession != null &&
            nextSession.state.toUpperCase() == 'COMPLETED' &&
            (previousSession == null ||
                previousSession.id != nextSession.id ||
                previousSession.state.toUpperCase() != 'COMPLETED');
        if (completedNow) {
          unawaited(_celebrateSimulationMilestone(nextSession));
        }
      },
    );
    if ((widget.initialTopic ?? '').trim().isNotEmpty) {
      _topicController.text = widget.initialTopic!.trim();
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        ref.read(simulationProvider.notifier).loadRecommendedSeeds(
              scenarioKey: _selectedScenarioKey,
              silent: true,
            ),
      );
      if ((widget.initialTopic ?? '').trim().isNotEmpty) {
        unawaited(
          ref.read(simulationProvider.notifier).run(
                topic: widget.initialTopic!.trim(),
                scenarioKey: _selectedScenarioKey,
              ),
        );
      }
    });
  }

  @override
  void dispose() {
    _simulationSubscription.close();
    _topicController.dispose();
    _interactionController.dispose();
    _roundsScrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(simulationProvider);
    final session = state.session;
    final liveParticipants = session?.participants ?? state.liveParticipants;
    final liveRounds = session?.rounds ?? state.liveRounds;
    final liveInsightSummary = session?.insightSummary ??
        state.liveInsightSummary ??
        (state.isLoading ? '模拟进行中，新的轮次会实时出现在下方。' : null);
    final participants = _isPlaybackPaused
        ? (_pausedParticipants ?? liveParticipants)
        : liveParticipants;
    final rounds =
        _isPlaybackPaused ? (_pausedRounds ?? liveRounds) : liveRounds;
    final insightSummary = _isPlaybackPaused
        ? (_pausedInsightSummary ?? liveInsightSummary)
        : liveInsightSummary;
    final interactionPrompt = _isPlaybackPaused
        ? (_pausedInteractionPrompt ??
            session?.interactionPrompt ??
            state.liveInteractionPrompt)
        : (session?.interactionPrompt ?? state.liveInteractionPrompt);
    final suggestedReplies = _isPlaybackPaused
        ? (_pausedSuggestedReplies ??
            session?.suggestedReplies ??
            state.liveSuggestedReplies)
        : (session?.suggestedReplies ?? state.liveSuggestedReplies);
    final pendingInteraction = _isPlaybackPaused
        ? (session?.pendingInteraction ?? state.activeInteraction)
        : (session?.pendingInteraction ?? state.activeInteraction);
    final roundCount = rounds.length;
    final expectedRounds = _expectedRoundsForScenario(
      session?.scenarioKey ?? _selectedScenarioKey,
    );
    final plannedRoundCount = (session?.plannedRoundCount ?? 0) > 0
        ? session!.plannedRoundCount
        : expectedRounds;

    return Scaffold(
      appBar: AppBar(
        title: const Text('学习场景模拟'),
        actions: [
          if (session != null)
            IconButton(
              onPressed: () => unawaited(_showSimulationShareSheet(session)),
              icon: const Icon(Icons.ios_share_rounded),
            ),
        ],
      ),
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Theme.of(context)
                  .colorScheme
                  .surfaceContainerHighest
                  .withValues(alpha: 0.32),
              Theme.of(context).scaffoldBackgroundColor,
            ],
          ),
        ),
        child: SafeArea(
          top: false,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final keyboardInset = MediaQuery.viewInsetsOf(context).bottom;
              final safeBottom = MediaQuery.paddingOf(context).bottom;
              final timelineHeight = math.max(
                280.0,
                math.min(420.0, constraints.maxHeight * 0.42),
              );

              return AnimatedPadding(
                duration: DS.durationNormal,
                curve: Curves.easeOutCubic,
                padding: EdgeInsets.only(bottom: keyboardInset),
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: EdgeInsets.fromLTRB(
                    16,
                    16,
                    16,
                    safeBottom + 20,
                  ),
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      minHeight: math.max(
                        0,
                        constraints.maxHeight - keyboardInset - 16,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if ((widget.initialSourceChatSessionId ?? '')
                            .trim()
                            .isNotEmpty) ...[
                          ChatContinuityBanner(
                            sourceChatSessionId:
                                widget.initialSourceChatSessionId!.trim(),
                            subtitle: '这一轮模拟来自你刚才的聊天桥接。点右侧按钮就能带着上下文回到原对话继续追问。',
                          ),
                          const SizedBox(height: 14),
                        ],
                        _SimulationComposer(
                          topicController: _topicController,
                          selectedScenarioKey: _selectedScenarioKey,
                          scenarioLabels: _scenarioLabels,
                          state: state,
                          onScenarioSelected: (value) {
                            setState(() => _selectedScenarioKey = value);
                            unawaited(
                              ref
                                  .read(simulationProvider.notifier)
                                  .loadRecommendedSeeds(
                                    scenarioKey: value,
                                    silent: true,
                                  ),
                            );
                          },
                          onRun: () => unawaited(_runSimulation()),
                        ),
                        const SizedBox(height: 14),
                        _RecommendedSeedStrip(
                          seeds: state.recommendedSeeds,
                          isLoading: state.isLoadingRecommendations,
                          scenarioLabels: _scenarioLabels,
                          onRefresh: () => unawaited(
                            ref
                                .read(simulationProvider.notifier)
                                .loadRecommendedSeeds(
                                  scenarioKey: _selectedScenarioKey,
                                ),
                          ),
                          onStartSeed: (seed) {
                            setState(
                              () =>
                                  _selectedScenarioKey = seed.suggestedScenario,
                            );
                            _topicController.text = seed.topic;
                            unawaited(
                              ref.read(simulationProvider.notifier).run(
                                    topic: seed.topic,
                                    scenarioKey: seed.suggestedScenario,
                                  ),
                            );
                          },
                          onOpenTheater: (seed) => context.push(
                            '${TheaterRoutes.theater}?topic=${Uri.encodeComponent(seed.topic)}',
                          ),
                        ),
                        const SizedBox(height: 14),
                        _SimulationStatusCard(
                          progress: state.progress,
                          engineState: state.engineState,
                          roundCount: roundCount,
                          expectedRounds: plannedRoundCount,
                          isRunning: state.isLoading || state.progress > 0,
                          isPaused: _isPlaybackPaused,
                          hasBufferedUpdates: _isPlaybackPaused &&
                              (liveRounds.length > rounds.length ||
                                  liveParticipants.length >
                                      participants.length),
                          participants: participants,
                          activeSpeaker:
                              rounds.isEmpty ? null : rounds.last.speaker,
                          onTogglePause: _togglePlaybackPause,
                        ),
                        if (state.error != null) ...[
                          const SizedBox(height: 12),
                          Text(
                            state.error!,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.error,
                            ),
                          ),
                        ],
                        const SizedBox(height: 14),
                        _SimulationTimelineCard(
                          rounds: rounds,
                          participants: participants,
                          activeSpeaker:
                              rounds.isEmpty ? null : rounds.last.speaker,
                          isLoading: state.isLoading,
                          topic: _topicController.text.trim(),
                          controller: _roundsScrollController,
                          height: timelineHeight,
                        ),
                        if ((interactionPrompt?.isNotEmpty ?? false) &&
                            (suggestedReplies.isNotEmpty ||
                                (pendingInteraction?.options.isNotEmpty ??
                                    false))) ...[
                          const SizedBox(height: 14),
                          _SimulationInteractionCard(
                            prompt: interactionPrompt!,
                            interactionType:
                                pendingInteraction?.interactionType ??
                                    session?.interactionType,
                            suggestedReplies: suggestedReplies,
                            options: pendingInteraction?.options ?? const [],
                            isSubmitting: state.isContinuing,
                            textController: _interactionController,
                            onReplySelected: (reply) =>
                                unawaited(_continueSimulation(reply)),
                            onSubmitText: () => unawaited(
                              _continueSimulation(_interactionController.text),
                            ),
                            onContinueInChat: (reply) =>
                                unawaited(_continueInChat(reply)),
                          ),
                        ],
                        if ((insightSummary?.isNotEmpty ?? false) ||
                            session != null) ...[
                          const SizedBox(height: 14),
                          _SimulationInsightTray(
                            summary: insightSummary ?? '',
                            expanded: _isInsightExpanded,
                            onToggleExpanded: () {
                              setState(() {
                                _isInsightExpanded = !_isInsightExpanded;
                              });
                            },
                            session: session,
                            onOpenTheater: session == null
                                ? null
                                : () => context.push(
                                      '${TheaterRoutes.theater}?topic=${Uri.encodeComponent(session.topic)}',
                                    ),
                            onOpenReport: session == null
                                ? null
                                : () => context.push(
                                      ReportRoutes.learningReport,
                                      extra: _buildSimulationReport(session),
                                    ),
                            onShare: session == null
                                ? null
                                : () => unawaited(_shareSession(session)),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Future<void> _runSimulation() async {
    final topic = _topicController.text.trim();
    if (topic.isEmpty) {
      return;
    }
    setState(() {
      _isPlaybackPaused = false;
      _pausedParticipants = null;
      _pausedRounds = null;
      _pausedInsightSummary = null;
      _pausedInteractionPrompt = null;
      _pausedSuggestedReplies = null;
      _isInsightExpanded = false;
    });
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    await ref.read(simulationProvider.notifier).run(
          topic: topic,
          scenarioKey: _selectedScenarioKey,
        );
  }

  void _togglePlaybackPause() {
    final state = ref.read(simulationProvider);
    final session = state.session;
    final liveParticipants = session?.participants ?? state.liveParticipants;
    final liveRounds = session?.rounds ?? state.liveRounds;
    final liveInsightSummary =
        session?.insightSummary ?? state.liveInsightSummary;
    setState(() {
      _isPlaybackPaused = !_isPlaybackPaused;
      if (_isPlaybackPaused) {
        _pausedParticipants =
            List<SimulationParticipantModel>.from(liveParticipants);
        _pausedRounds = List<SimulationRoundModel>.from(liveRounds);
        _pausedInsightSummary = liveInsightSummary;
        _pausedInteractionPrompt =
            session?.interactionPrompt ?? state.liveInteractionPrompt;
        _pausedSuggestedReplies = List<String>.from(
          session?.suggestedReplies ?? state.liveSuggestedReplies,
        );
      } else {
        _pausedParticipants = null;
        _pausedRounds = null;
        _pausedInsightSummary = null;
        _pausedInteractionPrompt = null;
        _pausedSuggestedReplies = null;
      }
    });
    unawaited(
      SensoryFeedbackService.emit(
        _isPlaybackPaused
            ? SensoryFeedbackEvent.toggle
            : SensoryFeedbackEvent.selection,
      ),
    );
    if (!_isPlaybackPaused) {
      _scrollToLatestRound();
    }
  }

  void _scrollToLatestRound() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_roundsScrollController.hasClients) {
        return;
      }
      unawaited(
        _roundsScrollController.animateTo(
          _roundsScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 320),
          curve: Curves.easeOutCubic,
        ),
      );
    });
  }

  int _expectedRoundsForScenario(String scenarioKey) {
    switch (scenarioKey) {
      case 'knowledge_debate':
        return 5;
      case 'historical_roleplay':
        return 6;
      case 'case_analysis':
      case 'what_if_path':
      case 'concept_map_build':
      case 'error_diagnosis':
        return 5;
      case 'socratic_dialogue':
        return 4;
      default:
        return 3;
    }
  }

  LearningReport _buildSimulationReport(SimulationSessionModel session) {
    final participants = session.participants
        .take(4)
        .map(
          (item) => LearningMasteryDatum(
            nodeName: item.name,
            masteryScore: 68 + ((item.name.hashCode.abs() % 20).toDouble()),
          ),
        )
        .toList();
    return LearningReport(
      reportId: 'simulation-${session.id}',
      markdown:
          '# 仿真洞察报告\n\n主题：${session.topic}\n\n## 关键洞察\n- ${session.insightSummary}\n- 参与者：${session.participants.map((e) => e.name).join('、')}',
      sections: const ['Executive Summary', '学习场景洞察'],
      mastery: participants,
    );
  }

  Future<void> _shareSession(SimulationSessionModel session) async {
    await share_plus.SharePlus.instance.share(
      share_plus.ShareParams(
        text:
            '学习场景模拟\n主题：${session.topic}\n场景：${_scenarioLabels[session.scenarioKey] ?? session.scenarioKey}\n洞察：${session.insightSummary}',
      ),
    );
  }

  Future<void> _showSimulationShareSheet(SimulationSessionModel session) async {
    await showUniversalShareSheet(
      context,
      payload: UniversalSharePayload(
        contentType: ShareableContentType.learningReport,
        resourceId: 'simulation-${session.id}',
        title: '学习场景模拟 · ${session.topic}',
        subtitle: _scenarioLabels[session.scenarioKey] ?? session.scenarioKey,
        description: session.insightSummary,
        metadata: <String, dynamic>{
          'active_plans': session.rounds.length,
          'unlocked_achievements': session.participants.length,
          'flame_brightness':
              session.participants.map((item) => item.name).take(3).join('、'),
        },
        shareMessage:
            '我刚在 Sparkle 跑了一场学习仿真：${session.topic}\n场景：${_scenarioLabels[session.scenarioKey] ?? session.scenarioKey}\n洞察：${session.insightSummary}',
      ),
      onGenerateCard: (payload) =>
          SharePosterService().generatePoster(context, payload),
      onCommunityShare: () => unawaited(_shareSession(session)),
    );
  }

  Future<void> _celebrateSimulationMilestone(
    SimulationSessionModel session,
  ) async {
    await MirofishMilestoneService.celebrateIfFirstTime(
      context,
      ref,
      kind: MirofishMilestoneKind.firstSimulation,
      onShare: () {
        Navigator.of(context).pop();
        unawaited(_showSimulationShareSheet(session));
      },
    );
  }

  Future<void> _continueInChat(String reply) async {
    final query = <String, String>{
      'prompt': reply,
      if ((widget.initialSourceChatSessionId ?? '').trim().isNotEmpty)
        'session_id': widget.initialSourceChatSessionId!.trim(),
    };
    await context.push(Uri(path: '/chat', queryParameters: query).toString());
  }

  Future<void> _continueSimulation(String reply) async {
    final normalized = reply.trim();
    if (normalized.isEmpty) {
      return;
    }
    _interactionController.clear();
    await ref.read(simulationProvider.notifier).continueSimulation(normalized);
  }
}

class _SimulationComposer extends StatelessWidget {
  const _SimulationComposer({
    required this.topicController,
    required this.selectedScenarioKey,
    required this.scenarioLabels,
    required this.state,
    required this.onScenarioSelected,
    required this.onRun,
  });

  final TextEditingController topicController;
  final String selectedScenarioKey;
  final Map<String, String> scenarioLabels;
  final SimulationState state;
  final ValueChanged<String> onScenarioSelected;
  final VoidCallback onRun;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.info.withValues(alpha: 0.16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        DS.info.withValues(alpha: 0.92),
                        DS.brandPrimary.withValues(alpha: 0.82),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(
                    Icons.groups_rounded,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '把一个知识点拉进真实讨论现场',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '先设定主题和讨论场景，系统会自动召集角色、逐轮生成观点并沉淀洞察。',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            TextField(
              controller: topicController,
              textInputAction: TextInputAction.go,
              onSubmitted: (_) {
                if (!state.isLoading) {
                  onRun();
                }
              },
              decoration: const InputDecoration(
                labelText: '输入一个知识点或主题',
                hintText: '例如：特征值与特征向量',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: scenarioLabels.entries
                  .map(
                    (entry) => ChoiceChip(
                      label: Text(entry.value),
                      selected: selectedScenarioKey == entry.key,
                      onSelected: state.isLoading
                          ? null
                          : (selected) {
                              if (selected) {
                                onScenarioSelected(entry.key);
                              }
                            },
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                FilledButton.icon(
                  onPressed: state.isLoading ? null : onRun,
                  icon: const Icon(Icons.play_circle_outline_rounded),
                  label: Text(state.isLoading ? '模拟进行中...' : '开始模拟'),
                ),
                if (topicController.text.trim().isNotEmpty)
                  OutlinedButton.icon(
                    onPressed: topicController.clear,
                    icon: const Icon(Icons.close_rounded),
                    label: const Text('清空主题'),
                  ),
              ],
            ),
          ],
        ),
      );
}

class _RecommendedSeedStrip extends StatelessWidget {
  const _RecommendedSeedStrip({
    required this.seeds,
    required this.isLoading,
    required this.scenarioLabels,
    required this.onRefresh,
    required this.onStartSeed,
    required this.onOpenTheater,
  });

  final List<SimulationSeedModel> seeds;
  final bool isLoading;
  final Map<String, String> scenarioLabels;
  final VoidCallback onRefresh;
  final ValueChanged<SimulationSeedModel> onStartSeed;
  final ValueChanged<SimulationSeedModel> onOpenTheater;

  @override
  Widget build(BuildContext context) {
    if (isLoading && seeds.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: CircularProgressIndicator(),
        ),
      );
    }

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '推荐场景',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: onRefresh,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(seeds.isEmpty ? '生成' : '刷新'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            seeds.isEmpty ? '还没有推荐种子，你可以先手动输入主题开始。' : '保留最有价值的几个候选场景，减少首屏干扰。',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
          if (seeds.isNotEmpty) ...[
            const SizedBox(height: 12),
            SizedBox(
              height: 208,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: seeds.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, index) => SizedBox(
                  width: 266,
                  child: _RecommendedSeedCard(
                    seed: seeds[index],
                    scenarioLabel:
                        scenarioLabels[seeds[index].suggestedScenario] ??
                            seeds[index].suggestedScenario,
                    onStart: () => onStartSeed(seeds[index]),
                    onOpenTheater: () => onOpenTheater(seeds[index]),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _RecommendedSeedCard extends StatelessWidget {
  const _RecommendedSeedCard({
    required this.seed,
    required this.scenarioLabel,
    required this.onStart,
    required this.onOpenTheater,
  });

  final SimulationSeedModel seed;
  final String scenarioLabel;
  final VoidCallback onStart;
  final VoidCallback onOpenTheater;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: DS.borderSubtle,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              seed.topic,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              seed.context,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
            ),
            const Spacer(),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Chip(label: Text(scenarioLabel)),
                if (seed.suggestedExperts.isNotEmpty)
                  Chip(label: Text(seed.suggestedExperts.first)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              seed.tensionPoint,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.tonal(
                  onPressed: onStart,
                  child: const Text('开始'),
                ),
                OutlinedButton(
                  onPressed: onOpenTheater,
                  child: const Text('转为推演'),
                ),
              ],
            ),
          ],
        ),
      );
}

class _SimulationInteractionCard extends StatelessWidget {
  const _SimulationInteractionCard({
    required this.prompt,
    required this.textController,
    required this.suggestedReplies,
    required this.options,
    required this.isSubmitting,
    required this.onReplySelected,
    required this.onSubmitText,
    required this.onContinueInChat,
    this.interactionType,
  });

  final String prompt;
  final String? interactionType;
  final TextEditingController textController;
  final List<String> suggestedReplies;
  final List<String> options;
  final bool isSubmitting;
  final ValueChanged<String> onReplySelected;
  final VoidCallback onSubmitText;
  final ValueChanged<String> onContinueInChat;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.warning.withValues(alpha: 0.18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    Icons.person_pin_circle_outlined,
                    color: DS.warning,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    '轮到你加入这场讨论',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              prompt,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    height: 1.5,
                  ),
            ),
            if ((interactionType ?? '').isNotEmpty) ...[
              const SizedBox(height: 10),
              _StatusBadge(
                icon: Icons.touch_app_rounded,
                label: '互动模式：${_interactionLabel(interactionType)}',
              ),
            ],
            if (options.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: options
                    .take(4)
                    .map(
                      (option) => Chip(
                        label: Text(option),
                      ),
                    )
                    .toList(),
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: suggestedReplies
                  .take(3)
                  .map(
                    (reply) => ActionChip(
                      label: Text(reply),
                      onPressed:
                          isSubmitting ? null : () => onReplySelected(reply),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: textController,
              enabled: !isSubmitting,
              minLines: 1,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: '或者输入你的判断',
                hintText: '例如：我会先补几何直觉，再回来刷一道题验证',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => onSubmitText(),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: isSubmitting ? null : onSubmitText,
                  icon: const Icon(Icons.send_rounded),
                  label: Text(isSubmitting ? '继续生成中...' : '继续这场模拟'),
                ),
                if (suggestedReplies.isNotEmpty)
                  OutlinedButton.icon(
                    onPressed: isSubmitting
                        ? null
                        : () => onContinueInChat(suggestedReplies.first),
                    icon: const Icon(Icons.chat_bubble_outline_rounded),
                    label: const Text('带去聊天继续'),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              '建议先在这里继续一轮，让角色真正回应你的判断；如果你想切回主对话，也可以走聊天入口。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
        ),
      );

  String _interactionLabel(String? raw) {
    switch (raw) {
      case 'open_question':
        return '开放追问';
      case 'challenge':
        return '观点挑战';
      case 'forced_choice':
      case 'vote':
        return '二选一判断';
      default:
        return '选择判断';
    }
  }
}

class _SimulationStatusCard extends StatelessWidget {
  const _SimulationStatusCard({
    required this.progress,
    required this.engineState,
    required this.roundCount,
    required this.expectedRounds,
    required this.isRunning,
    required this.isPaused,
    required this.hasBufferedUpdates,
    required this.participants,
    required this.activeSpeaker,
    required this.onTogglePause,
  });

  final double progress;
  final String? engineState;
  final int roundCount;
  final int expectedRounds;
  final bool isRunning;
  final bool isPaused;
  final bool hasBufferedUpdates;
  final List<SimulationParticipantModel> participants;
  final String? activeSpeaker;
  final VoidCallback onTogglePause;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isRunning
                            ? roundCount > 0
                                ? '正在第 $roundCount/$expectedRounds 轮'
                                : '正在召集参与者'
                            : '等待开始',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        engineState == null ? '准备中' : '当前状态：$engineState',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                            ),
                      ),
                    ],
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: isRunning ? onTogglePause : null,
                  icon: Icon(
                    isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
                  ),
                  label: Text(isPaused ? '继续' : '暂停'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: isRunning ? progress.clamp(0.0, 1.0) : 0,
                minHeight: 8,
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _StatusBadge(
                  icon: Icons.forum_rounded,
                  label: roundCount == 0 ? '等待首轮' : '$roundCount 轮观点',
                ),
                _StatusBadge(
                  icon: Icons.groups_rounded,
                  label: participants.isEmpty
                      ? '角色待加入'
                      : '${participants.length} 位角色',
                ),
                if (isPaused)
                  _StatusBadge(
                    icon: hasBufferedUpdates
                        ? Icons.sync_rounded
                        : Icons.pause_circle_outline_rounded,
                    label: hasBufferedUpdates ? '后台仍在继续生成' : '前台已暂停播放',
                  ),
              ],
            ),
            if (participants.isNotEmpty) ...[
              const SizedBox(height: 12),
              SizedBox(
                height: 44,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: participants.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final participant = participants[index];
                    return _AnimatedParticipantChip(
                      participant: participant,
                      accent: _accentForName(participant.name),
                      isActive: participant.name == activeSpeaker,
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      );

  Color _accentForName(String name) {
    final palette = <Color>[
      DS.info,
      DS.success,
      DS.warning,
      DS.brandPrimary,
      DS.accent,
    ];
    return palette[name.hashCode.abs() % palette.length];
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: 10,
          vertical: 7,
        ),
        decoration: BoxDecoration(
          color: Theme.of(context)
              .colorScheme
              .surfaceContainerHighest
              .withValues(alpha: 0.72),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ],
        ),
      );
}

class _SimulationTimelineCard extends StatelessWidget {
  const _SimulationTimelineCard({
    required this.rounds,
    required this.participants,
    required this.activeSpeaker,
    required this.isLoading,
    required this.topic,
    required this.controller,
    required this.height,
  });

  final List<SimulationRoundModel> rounds;
  final List<SimulationParticipantModel> participants;
  final String? activeSpeaker;
  final bool isLoading;
  final String topic;
  final ScrollController controller;
  final double height;

  @override
  Widget build(BuildContext context) {
    final participantByName = <String, SimulationParticipantModel>{
      for (final participant in participants) participant.name: participant,
    };
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '讨论时间线',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      topic.isEmpty ? '开始后会实时出现每一轮讨论。' : '主题：$topic',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (participants.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context)
                    .colorScheme
                    .surfaceContainerHighest
                    .withValues(alpha: 0.62),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: participants
                    .take(4)
                    .map(
                      (participant) => _ParticipantSnapshotPill(
                        participant: participant,
                        isActive: participant.name == activeSpeaker,
                      ),
                    )
                    .toList(),
              ),
            ),
          ],
          const SizedBox(height: 12),
          SizedBox(
            height: height,
            child: rounds.isEmpty
                ? _SimulationEmptyState(isLoading: isLoading)
                : ListView.separated(
                    controller: controller,
                    itemCount: rounds.length,
                    separatorBuilder: (context, index) => _RoundDivider(
                      round: rounds[index].round,
                    ),
                    itemBuilder: (context, index) {
                      final round = rounds[index];
                      return SimulationChatBubble(
                        key: ValueKey(
                          '${round.round}-${round.speaker}-${round.message}',
                        ),
                        speaker: round.speaker,
                        participant: participantByName[round.speaker],
                        message: round.message,
                        round: round.round,
                        replyToSpeaker: round.replyToSpeaker,
                        turnGoal: round.turnGoal,
                        isSpotlighted:
                            round.speaker == activeSpeaker &&
                            index == rounds.length - 1,
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _SimulationInsightTray extends StatelessWidget {
  const _SimulationInsightTray({
    required this.summary,
    required this.expanded,
    required this.onToggleExpanded,
    required this.session,
    required this.onOpenTheater,
    required this.onOpenReport,
    required this.onShare,
  });

  final String summary;
  final bool expanded;
  final VoidCallback onToggleExpanded;
  final SimulationSessionModel? session;
  final VoidCallback? onOpenTheater;
  final VoidCallback? onOpenReport;
  final VoidCallback? onShare;

  @override
  Widget build(BuildContext context) {
    final bulletPoints =
        session == null ? const <String>[] : _buildBulletPoints(session!);
    final previewText = summary.isEmpty ? '暂未生成洞察总结。' : summary;

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: onToggleExpanded,
            borderRadius: BorderRadius.circular(14),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '洞察总结',
                          style:
                              Theme.of(context).textTheme.titleSmall?.copyWith(
                                    fontWeight: FontWeight.w800,
                                  ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          previewText,
                          maxLines: expanded ? 6 : 2,
                          overflow: expanded
                              ? TextOverflow.visible
                              : TextOverflow.ellipsis,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.45,
                                  ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Icon(
                    expanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    color: DS.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          if (expanded && bulletPoints.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...bulletPoints.map(
              (point) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 2),
                      child: Icon(Icons.brightness_1, size: 7),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        point,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.4,
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
          if (session != null) ...[
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.tonalIcon(
                  onPressed: onOpenReport,
                  icon: const Icon(Icons.article_outlined),
                  label: const Text('生成学习报告'),
                ),
                FilledButton.tonalIcon(
                  onPressed: onOpenTheater,
                  icon: const Icon(Icons.auto_graph_rounded),
                  label: const Text('以此推演'),
                ),
                OutlinedButton.icon(
                  onPressed: onShare,
                  icon: const Icon(Icons.share_outlined),
                  label: const Text('分享洞察'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  List<String> _buildBulletPoints(SimulationSessionModel session) {
    final points = <String>[
      '参与者：${session.participants.map((item) => item.name).join('、')}',
      '总轮次：${session.rounds.length} 轮，适合沉淀为下一步推演或复盘报告。',
    ];
    if (session.rounds.isNotEmpty) {
      points.add('开场重点：${session.rounds.first.message}');
    }
    return points.take(3).toList();
  }
}

class _AnimatedParticipantChip extends StatefulWidget {
  const _AnimatedParticipantChip({
    required this.participant,
    required this.accent,
    this.isActive = false,
  });

  final SimulationParticipantModel participant;
  final Color accent;
  final bool isActive;

  @override
  State<_AnimatedParticipantChip> createState() =>
      _AnimatedParticipantChipState();
}

class _AnimatedParticipantChipState extends State<_AnimatedParticipantChip> {
  bool _entered = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      setState(() => _entered = true);
    });
  }

  @override
  Widget build(BuildContext context) => AnimatedSlide(
        duration: DS.durationNormal,
        curve: Curves.easeOutCubic,
        offset: _entered ? Offset.zero : const Offset(-0.12, 0),
        child: AnimatedOpacity(
          duration: DS.durationNormal,
          opacity: _entered ? 1 : 0,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  widget.accent.withValues(alpha: widget.isActive ? 0.2 : 0.1),
                  Theme.of(context)
                      .colorScheme
                      .surfaceContainerHighest
                      .withValues(alpha: 0.84),
                ],
              ),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: widget.accent.withValues(
                  alpha: widget.isActive ? 0.34 : 0.14,
                ),
              ),
              boxShadow: widget.isActive
                  ? [
                      BoxShadow(
                        color: widget.accent.withValues(alpha: 0.14),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ]
                  : null,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircleAvatar(
                  radius: 12,
                  backgroundColor: widget.accent.withValues(alpha: 0.14),
                  child: Text(
                    widget.participant.name.isEmpty
                        ? '?'
                        : widget.participant.name[0],
                    style: TextStyle(
                      fontSize: 11,
                      color: widget.accent,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  widget.participant.name,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        fontWeight:
                            widget.isActive ? FontWeight.w800 : FontWeight.w600,
                      ),
                ),
                if (widget.isActive) ...[
                  const SizedBox(width: 8),
                  Icon(
                    Icons.wifi_tethering_rounded,
                    size: 15,
                    color: widget.accent,
                  ),
                ],
              ],
            ),
          ),
        ),
      );
}

class _ParticipantSnapshotPill extends StatelessWidget {
  const _ParticipantSnapshotPill({
    required this.participant,
    this.isActive = false,
  });

  final SimulationParticipantModel participant;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final accent = _accentForName(participant.name);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            accent.withValues(alpha: isActive ? 0.14 : 0.08),
            Theme.of(context).colorScheme.surface.withValues(alpha: 0.76),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: accent.withValues(alpha: isActive ? 0.34 : 0.14),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isActive ? Icons.mic_rounded : Icons.person_rounded,
                size: 14,
                color: accent,
              ),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  participant.name,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: accent,
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
            ],
          ),
          if (participant.roleHint.isNotEmpty ||
              (participant.stance?.isNotEmpty ?? false)) ...[
            const SizedBox(height: 4),
            Text(
              [
                if (participant.roleHint.isNotEmpty) participant.roleHint,
                if (participant.stance?.isNotEmpty ?? false)
                  participant.stance!,
              ].join(' · '),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
        ],
      ),
    );
  }

  Color _accentForName(String name) {
    final palette = <Color>[
      DS.info,
      DS.success,
      DS.warning,
      DS.brandPrimary,
      DS.accent,
    ];
    return palette[name.hashCode.abs() % palette.length];
  }
}

class _SimulationEmptyState extends StatelessWidget {
  const _SimulationEmptyState({required this.isLoading});

  final bool isLoading;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isLoading) const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(
              isLoading ? '模拟正在生成中...' : '开始一次学习场景模拟，让角色逐轮讨论这个主题。',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
}

class _RoundDivider extends StatelessWidget {
  const _RoundDivider({required this.round});

  final int round;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            Expanded(
              child: Divider(
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Text(
                '第 $round 轮',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ),
            Expanded(
              child: Divider(
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
          ],
        ),
      );
}
