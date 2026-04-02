import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/chat_continuity_banner.dart';
import 'package:sparkle/core/widgets/mirofish_stage_header.dart';
import 'package:sparkle/features/mirofish/presentation/support/mirofish_milestone_service.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/presentation/support/simulation_copy.dart';
import 'package:sparkle/features/simulation/presentation/widgets/simulation_chat_bubble.dart';
import 'package:sparkle/features/theater/theater_routes.dart';

class SimulationScreen extends ConsumerStatefulWidget {
  const SimulationScreen({
    super.key,
    this.initialTopic,
    this.initialScenarioKey,
    this.initialSimulationSessionId,
    this.sourcePredictionId,
    this.sourceRouteId,
    this.sourceRouteTitle,
    this.sourceTargetName,
    this.initialSourceChatSessionId,
  });

  final String? initialTopic;
  final String? initialScenarioKey;
  final String? initialSimulationSessionId;
  final String? sourcePredictionId;
  final String? sourceRouteId;
  final String? sourceRouteTitle;
  final String? sourceTargetName;
  final String? initialSourceChatSessionId;

  @override
  ConsumerState<SimulationScreen> createState() => _SimulationScreenState();
}

enum _SimulationViewMode { setup, active, review }

enum _SimulationBottomTrayMode { hidden, peek, expanded }

class _SimulationScreenState extends ConsumerState<SimulationScreen> {
  static const double _immersiveAutoScrollFollowThreshold = 160;
  static const Map<String, String> _scenarioLabels = simulationScenarioLabels;
  static const Map<String, List<String>> _scenarioParticipantOptions = {
    'study_group': ['优等生', '中等生', '提问者', '总结者', '练习教练'],
    'knowledge_debate': ['正方专家', '反方专家', '主持人', '证据审查员', '追问者'],
    'historical_roleplay': ['历史导师', '关键人物', '时代观察者', '策略顾问', '记录官'],
    'socratic_dialogue': ['苏格拉底', '怀疑者', '拆解者', '应用者'],
    'case_analysis': ['案例导师', '诊断官', '实践派', '反例提出者', '决策记录官'],
    'what_if_path': ['当前路线', '激进路线', '风险观察者', '资源调度者', '验证者'],
    'concept_map_build': ['结构师', '连接者', '提问者', '反例检查员', '桥梁构建者'],
    'error_diagnosis': ['错因分析师', '纠偏教练', '验证者', '题面解构者', '迁移教练'],
  };
  static const Map<String, String> _scenarioDescriptions = {
    'study_group': '围绕一个主题做多角色共学，适合把概念、例题和误区一起讲透。',
    'knowledge_debate': '让不同立场直接碰撞，适合验证观点、证据和边界条件。',
    'historical_roleplay': '带入人物与时代约束，让讨论像真实历史现场一样推进。',
    'socratic_dialogue': '通过连续追问拆解前提，适合澄清模糊概念与推理漏洞。',
    'case_analysis': '围绕具体案例做拆解、诊断和决策，适合实务型主题。',
    'what_if_path': '比较不同学习或行动路线，适合规划、取舍与资源分配。',
    'concept_map_build': '把知识点织成结构图，适合建立全局框架与连接关系。',
    'error_diagnosis': '专注识别错因、纠偏路径与验证方式，适合查漏补缺。',
  };
  static const Map<String, String> _facilitationLabels = {
    'balanced': '平衡推进',
    'debate': '分歧碰撞',
    'guided': '引导拆解',
    'practical': '应用落地',
  };
  static const Map<String, String> _facilitationDescriptions = {
    'balanced': '适合大多数主题，强调多角色平衡推进，不让任何一方压住全场。',
    'debate': '主动放大争议和证据冲突，更适合需要碰撞观点的主题。',
    'guided': '更像导师带讨论，强调澄清前提、逐步拆解和用户可跟上。',
    'practical': '优先讨论行动、验证和现实约束，适合技能与方案推演。',
  };

  String _buildTheaterRoute({
    required String topic,
    String? simulationSessionId,
  }) {
    final query = <String, String>{
      'topic': topic,
      if ((widget.sourcePredictionId ?? '').trim().isNotEmpty)
        'prediction_id': widget.sourcePredictionId!.trim(),
      if ((widget.sourceRouteId ?? '').trim().isNotEmpty)
        'route_id': widget.sourceRouteId!.trim(),
      if ((simulationSessionId ?? '').trim().isNotEmpty)
        'simulation_session_id': simulationSessionId!.trim(),
    };
    return Uri(path: TheaterRoutes.theater, queryParameters: query).toString();
  }

  final _topicController = TextEditingController();
  final _interactionController = TextEditingController();
  final _customParticipantController = TextEditingController();
  final _roundsScrollController = ScrollController();
  final _immersiveScrollController = ScrollController();
  late String _selectedScenarioKey;
  late final ProviderSubscription<SimulationState> _simulationSubscription;
  bool _isPlaybackPaused = false;
  bool _isInsightExpanded = false;
  bool _settingsDrawerOpen = false;
  bool _insightOverlayOpen = false;
  _SimulationBottomTrayMode _bottomTrayMode = _SimulationBottomTrayMode.hidden;
  bool _isGeneratingReport = false;
  int _configuredRoundCount = 5;
  String _facilitationStyle = 'balanced';
  List<String> _selectedParticipantNames = const [];
  bool _showScrollToBottomFab = false;
  List<SimulationParticipantModel>? _pausedParticipants;
  List<SimulationRoundModel>? _pausedRounds;
  String? _pausedInsightSummary;
  String? _pausedInteractionPrompt;
  List<String>? _pausedSuggestedReplies;

  @override
  void initState() {
    super.initState();
    _selectedScenarioKey = widget.initialScenarioKey ?? 'study_group';
    _applyScenarioDefaults(_selectedScenarioKey, resetParticipants: true);
    _immersiveScrollController.addListener(_handleImmersiveScroll);
    _simulationSubscription = ref.listenManual<SimulationState>(
      simulationProvider,
      (previous, next) {
        final previousRoundCount = previous?.liveRounds.length ?? 0;
        final nextRoundCount = next.liveRounds.length;
        if (nextRoundCount > previousRoundCount && !_isPlaybackPaused) {
          final shouldAutoScroll = !_hasPendingUserInteraction(next);
          if (shouldAutoScroll) {
            unawaited(
              SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
            );
            _scrollToLatestRound();
          } else {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted) {
                _handleImmersiveScroll();
              }
            });
          }
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
        if ((nextSession?.topic ?? '').isNotEmpty &&
            _topicController.text.trim().isEmpty) {
          _topicController.text = nextSession!.topic;
        }
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
      if ((widget.initialSimulationSessionId ?? '').trim().isNotEmpty) {
        unawaited(
          ref.read(simulationProvider.notifier).restoreSession(
                widget.initialSimulationSessionId!.trim(),
              ),
        );
      } else if ((widget.initialTopic ?? '').trim().isNotEmpty) {
        unawaited(
          ref.read(simulationProvider.notifier).run(
                topic: widget.initialTopic!.trim(),
                scenarioKey: _selectedScenarioKey,
                plannedRoundCount: _configuredRoundCount,
                participantNames: _selectedParticipantNames,
                facilitationStyle: _facilitationStyle,
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
    _customParticipantController.dispose();
    _roundsScrollController.dispose();
    _immersiveScrollController
      ..removeListener(_handleImmersiveScroll)
      ..dispose();
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
    final expectedRounds = _expectedRoundsForScenario(
      session?.scenarioKey ?? _selectedScenarioKey,
    );
    final runtimePlannedRoundCount =
        session?.plannedRoundCount ?? state.livePlannedRoundCount;
    final plannedRoundCount = runtimePlannedRoundCount > 0
        ? runtimePlannedRoundCount
        : math.max(_configuredRoundCount, expectedRounds);
    final viewMode = _resolveViewMode(session);
    final activeSpeaker = rounds.isEmpty ? null : rounds.last.speaker;

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
                child: viewMode == _SimulationViewMode.setup
                    ? _buildSetupLayout(
                        context: context,
                        constraints: constraints,
                        safeBottom: safeBottom,
                        state: state,
                        timelineHeight: timelineHeight,
                        participants: participants,
                        rounds: rounds,
                        session: session,
                        interactionPrompt: interactionPrompt,
                        suggestedReplies: suggestedReplies,
                        pendingInteraction: pendingInteraction,
                        insightSummary: insightSummary,
                        plannedRoundCount: plannedRoundCount,
                        activeSpeaker: activeSpeaker,
                        liveParticipants: liveParticipants,
                        liveRounds: liveRounds,
                      )
                    : _buildImmersiveLayout(
                        context: context,
                        safeBottom: safeBottom,
                        state: state,
                        session: session,
                        participants: participants,
                        rounds: rounds,
                        interactionPrompt: interactionPrompt,
                        suggestedReplies: suggestedReplies,
                        pendingInteraction: pendingInteraction,
                        insightSummary: insightSummary,
                        plannedRoundCount: plannedRoundCount,
                        activeSpeaker: activeSpeaker,
                        viewMode: viewMode,
                      ),
              );
            },
          ),
        ),
      ),
    );
  }

  _SimulationViewMode _resolveViewMode(SimulationSessionModel? session) {
    if (session == null) {
      return _SimulationViewMode.setup;
    }
    final normalizedState = session.state.toUpperCase();
    if (normalizedState == 'COMPLETED') {
      return _SimulationViewMode.review;
    }
    return _SimulationViewMode.active;
  }

  void _handleScenarioSelected(String value) {
    setState(() {
      _selectedScenarioKey = value;
      _applyScenarioDefaults(value, resetParticipants: true);
    });
    unawaited(
      ref.read(simulationProvider.notifier).loadRecommendedSeeds(
            scenarioKey: value,
            silent: true,
          ),
    );
  }

  void _startSeed(SimulationSeedModel seed) {
    setState(() {
      _selectedScenarioKey = seed.suggestedScenario;
      _applyScenarioDefaults(seed.suggestedScenario, resetParticipants: true);
      if (seed.suggestedExperts.isNotEmpty) {
        _selectedParticipantNames = seed.suggestedExperts
            .map((item) => item.trim())
            .where((item) => item.isNotEmpty)
            .take(6)
            .toList(growable: false);
      }
      _settingsDrawerOpen = false;
      _insightOverlayOpen = false;
      _bottomTrayMode = _SimulationBottomTrayMode.hidden;
      _isPlaybackPaused = false;
    });
    _topicController.text = seed.topic;
    unawaited(
      ref.read(simulationProvider.notifier).run(
            topic: seed.topic,
            scenarioKey: seed.suggestedScenario,
            plannedRoundCount: _configuredRoundCount,
            participantNames: _selectedParticipantNames,
            facilitationStyle: _facilitationStyle,
          ),
    );
  }

  void _applyScenarioDefaults(
    String scenarioKey, {
    required bool resetParticipants,
  }) {
    final maxRounds = _maxRoundsForScenario(scenarioKey);
    final suggestedRounds = _suggestedRoundCountForScenario(scenarioKey);
    _configuredRoundCount = _configuredRoundCount.clamp(3, maxRounds);
    if (_configuredRoundCount == 0 ||
        resetParticipants ||
        _configuredRoundCount > maxRounds) {
      _configuredRoundCount = suggestedRounds.clamp(3, maxRounds);
    }
    if (resetParticipants || _selectedParticipantNames.isEmpty) {
      _selectedParticipantNames = _defaultParticipantNamesForScenario(
        scenarioKey,
      );
    }
  }

  int _suggestedRoundCountForScenario(String scenarioKey) {
    switch (scenarioKey) {
      case 'knowledge_debate':
      case 'case_analysis':
        return 8;
      case 'historical_roleplay':
      case 'error_diagnosis':
        return 9;
      case 'what_if_path':
      case 'concept_map_build':
        return 8;
      case 'socratic_dialogue':
        return 7;
      default:
        return 8;
    }
  }

  int _maxRoundsForScenario(String scenarioKey) {
    switch (scenarioKey) {
      case 'case_analysis':
      case 'knowledge_debate':
        return 12;
      case 'historical_roleplay':
      case 'error_diagnosis':
        return 12;
      case 'what_if_path':
      case 'concept_map_build':
        return 10;
      case 'socratic_dialogue':
        return 9;
      default:
        return 10;
    }
  }

  List<String> _participantOptionsForScenario(String scenarioKey) =>
      _scenarioParticipantOptions[scenarioKey] ?? const ['学习伙伴', '提问者', '总结者'];

  List<String> _defaultParticipantNamesForScenario(String scenarioKey) =>
      _participantOptionsForScenario(scenarioKey)
          .take(scenarioKey == 'socratic_dialogue' ? 2 : 4)
          .toList(growable: false);

  void _toggleParticipantSelection(String name) {
    final trimmed = name.trim();
    if (trimmed.isEmpty) {
      return;
    }
    setState(() {
      final next = List<String>.from(_selectedParticipantNames);
      if (next.contains(trimmed)) {
        if (next.length <= 1) {
          return;
        }
        next.remove(trimmed);
      } else if (next.length < 6) {
        next.add(trimmed);
      }
      _selectedParticipantNames = next;
    });
  }

  void _addCustomParticipant(String name) {
    final trimmed = name.trim();
    if (trimmed.isEmpty) {
      return;
    }
    if (_selectedParticipantNames.contains(trimmed)) {
      _customParticipantController.clear();
      return;
    }
    if (_selectedParticipantNames.length >= 6) {
      return;
    }
    setState(() {
      _selectedParticipantNames = [
        ..._selectedParticipantNames,
        trimmed,
      ];
    });
    _customParticipantController.clear();
  }

  Widget? _buildTheaterBridgeBanner(SimulationSessionModel? session) {
    final routeId = (widget.sourceRouteId ?? '').trim();
    final predictionId = (widget.sourcePredictionId ?? '').trim();
    if (routeId.isEmpty || predictionId.isEmpty) {
      return null;
    }
    final routeTitle = (widget.sourceRouteTitle ?? '').trim();
    final targetName = (widget.sourceTargetName ?? '').trim();
    final topic = session?.topic ?? _topicController.text.trim();
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.alt_route_rounded,
            color: Theme.of(context).colorScheme.primary,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  routeTitle.isNotEmpty ? '正在验证路径「$routeTitle」' : '正在验证一条推演路径',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  targetName.isNotEmpty
                      ? '这轮模拟来自知识剧场，目标是 $targetName。你可以随时带着当前进度回到剧场继续采纳或校准。'
                      : '这轮模拟来自知识剧场，当前上下文会和原推演保持关联。',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.4,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          FilledButton.tonal(
            onPressed: () => context.push(
              _buildTheaterRoute(
                topic: topic.isEmpty ? (widget.initialTopic ?? '当前模拟') : topic,
                simulationSessionId: session?.id,
              ),
            ),
            child: const Text('回到剧场'),
          ),
        ],
      ),
    );
  }

  Widget _buildSetupLayout({
    required BuildContext context,
    required BoxConstraints constraints,
    required double safeBottom,
    required SimulationState state,
    required double timelineHeight,
    required List<SimulationParticipantModel> participants,
    required List<SimulationRoundModel> rounds,
    required SimulationSessionModel? session,
    required String? interactionPrompt,
    required List<String> suggestedReplies,
    required SimulationInteractionModel? pendingInteraction,
    required String? insightSummary,
    required int plannedRoundCount,
    required String? activeSpeaker,
    required List<SimulationParticipantModel> liveParticipants,
    required List<SimulationRoundModel> liveRounds,
  }) =>
      SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: EdgeInsets.fromLTRB(16, 16, 16, safeBottom + 20),
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minHeight: math.max(0, constraints.maxHeight - 16),
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
                  kind: ChatContinuityKind.journey,
                  subtitle: '这一轮模拟承接了你刚才的探索流程。你可以随时带着上下文回到原对话，继续追问判断和下一步行动。',
                ),
                const SizedBox(height: 14),
              ],
              if (_buildTheaterBridgeBanner(session)
                  case final bridgeBanner?) ...[
                bridgeBanner,
                const SizedBox(height: 14),
              ],
              _SimulationComposer(
                topicController: _topicController,
                selectedScenarioKey: _selectedScenarioKey,
                scenarioLabels: _scenarioLabels,
                state: state,
                onScenarioSelected: _handleScenarioSelected,
                onRun: () => unawaited(_runSimulation()),
              ),
              const SizedBox(height: 14),
              _SimulationCompactSetupPanel(
                topicController: _topicController,
                customParticipantController: _customParticipantController,
                selectedScenarioKey: _selectedScenarioKey,
                scenarioLabels: _scenarioLabels,
                scenarioDescriptions: _scenarioDescriptions,
                isLoading: state.isLoading,
                facilitationStyle: _facilitationStyle,
                facilitationLabels: _facilitationLabels,
                facilitationDescriptions: _facilitationDescriptions,
                plannedRoundCount: _configuredRoundCount,
                maxRoundCount: _maxRoundsForScenario(_selectedScenarioKey),
                selectedParticipantNames: _selectedParticipantNames,
                availableParticipantNames:
                    _participantOptionsForScenario(_selectedScenarioKey),
                isHistoricalRoleplay:
                    _selectedScenarioKey == 'historical_roleplay',
                onScenarioSelected: _handleScenarioSelected,
                onFacilitationStyleSelected: (value) {
                  setState(() => _facilitationStyle = value);
                },
                onRoundCountChanged: (value) {
                  setState(() => _configuredRoundCount = value);
                },
                onParticipantToggled: _toggleParticipantSelection,
                onCustomParticipantAdded: _addCustomParticipant,
                onResetParticipants: () {
                  setState(() {
                    _selectedParticipantNames =
                        _defaultParticipantNamesForScenario(
                      _selectedScenarioKey,
                    );
                  });
                },
                onRun: () => unawaited(_runSimulation()),
              ),
              const SizedBox(height: 14),
              _RecommendedSeedStrip(
                seeds: state.recommendedSeeds,
                isLoading: state.isLoadingRecommendations,
                scenarioLabels: _scenarioLabels,
                onRefresh: () => unawaited(
                  ref.read(simulationProvider.notifier).loadRecommendedSeeds(
                        scenarioKey: _selectedScenarioKey,
                      ),
                ),
                onStartSeed: _startSeed,
                onOpenTheater: (seed) => context.push(
                  _buildTheaterRoute(topic: seed.topic),
                ),
              ),
              if (session != null) ...[
                const SizedBox(height: 14),
                _SimulationStatusCard(
                  progress: state.progress,
                  engineState: state.engineState,
                  roundCount: rounds.length,
                  expectedRounds: plannedRoundCount,
                  isRunning: state.isLoading || state.progress > 0,
                  isPaused: _isPlaybackPaused,
                  hasBufferedUpdates: _isPlaybackPaused &&
                      (liveRounds.length > rounds.length ||
                          liveParticipants.length > participants.length),
                  participants: participants,
                  activeSpeaker: activeSpeaker,
                  onTogglePause: _togglePlaybackPause,
                ),
              ],
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
                activeSpeaker: activeSpeaker,
                isLoading: state.isLoading,
                topic: _topicController.text.trim(),
                controller: _roundsScrollController,
                height: timelineHeight,
              ),
              if ((interactionPrompt?.isNotEmpty ?? false) &&
                  (suggestedReplies.isNotEmpty ||
                      (pendingInteraction?.options.isNotEmpty ?? false))) ...[
                const SizedBox(height: 14),
                _SimulationInteractionCard(
                  prompt: interactionPrompt!,
                  interactionType: pendingInteraction?.interactionType ??
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
              if ((insightSummary?.isNotEmpty ?? false) || session != null) ...[
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
                            _buildTheaterRoute(
                              topic: session.topic,
                              simulationSessionId: session.id,
                            ),
                          ),
                  onOpenReport: session == null
                      ? null
                      : () => unawaited(
                            _openGeneratedLearningReport(session),
                          ),
                  onShare: session == null
                      ? null
                      : () => unawaited(_shareSession(session)),
                  isGeneratingReport: _isGeneratingReport,
                ),
              ],
            ],
          ),
        ),
      );

  Widget _buildImmersiveLayout({
    required BuildContext context,
    required double safeBottom,
    required SimulationState state,
    required SimulationSessionModel? session,
    required List<SimulationParticipantModel> participants,
    required List<SimulationRoundModel> rounds,
    required String? interactionPrompt,
    required List<String> suggestedReplies,
    required SimulationInteractionModel? pendingInteraction,
    required String? insightSummary,
    required int plannedRoundCount,
    required String? activeSpeaker,
    required _SimulationViewMode viewMode,
  }) {
    final topic = _topicController.text.trim().isEmpty
        ? session?.topic ?? '当前模拟'
        : _topicController.text.trim();
    final scenarioLabel =
        _scenarioLabels[session?.scenarioKey ?? _selectedScenarioKey] ??
            localizeSimulationScenario(
              session?.scenarioKey ?? _selectedScenarioKey,
            );
    final hasInteraction = (interactionPrompt?.isNotEmpty ?? false) &&
        (suggestedReplies.isNotEmpty ||
            (pendingInteraction?.options.isNotEmpty ?? false));
    final hasInsight = (insightSummary?.isNotEmpty ?? false) || session != null;
    final effectiveTrayMode = hasInteraction
        ? (_bottomTrayMode == _SimulationBottomTrayMode.hidden
            ? _SimulationBottomTrayMode.expanded
            : _bottomTrayMode)
        : _SimulationBottomTrayMode.hidden;
    final runtimeFacilitationStyle = session?.facilitationStyle ??
        state.liveFacilitationStyle ??
        _facilitationStyle;
    final setupPanel = _SimulationCompactSetupPanel(
      topicController: _topicController,
      customParticipantController: _customParticipantController,
      selectedScenarioKey: _selectedScenarioKey,
      scenarioLabels: _scenarioLabels,
      scenarioDescriptions: _scenarioDescriptions,
      isLoading: state.isLoading,
      facilitationStyle: runtimeFacilitationStyle,
      facilitationLabels: _facilitationLabels,
      facilitationDescriptions: _facilitationDescriptions,
      plannedRoundCount: _configuredRoundCount,
      maxRoundCount: _maxRoundsForScenario(_selectedScenarioKey),
      selectedParticipantNames: _selectedParticipantNames,
      availableParticipantNames: _participantOptionsForScenario(
        _selectedScenarioKey,
      ),
      isHistoricalRoleplay: _selectedScenarioKey == 'historical_roleplay',
      onScenarioSelected: _handleScenarioSelected,
      onFacilitationStyleSelected: (value) {
        setState(() => _facilitationStyle = value);
      },
      onRoundCountChanged: (value) {
        setState(() => _configuredRoundCount = value);
      },
      onParticipantToggled: _toggleParticipantSelection,
      onCustomParticipantAdded: _addCustomParticipant,
      onResetParticipants: () {
        setState(() {
          _selectedParticipantNames =
              _defaultParticipantNamesForScenario(_selectedScenarioKey);
        });
      },
      onRun: () => unawaited(_runSimulation()),
    );
    return Stack(
      children: [
        CustomScrollView(
          controller: _immersiveScrollController,
          physics: const AlwaysScrollableScrollPhysics(),
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          slivers: [
            SliverPadding(
              padding: EdgeInsets.fromLTRB(16, 12, 16, safeBottom + 18),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.card,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                    child: _SimulationImmersiveTopBar(
                      topic: topic,
                      scenarioLabel: scenarioLabel,
                      roundCount: rounds.length,
                      expectedRounds: plannedRoundCount,
                      engineState: state.engineState,
                      activeSpeaker: activeSpeaker,
                      participantCount: participants.length,
                      facilitationLabel:
                          _facilitationLabels[runtimeFacilitationStyle] ??
                              '平衡推进',
                      isPaused: _isPlaybackPaused,
                      isReview: viewMode == _SimulationViewMode.review,
                      hasInsight: hasInsight,
                      settingsOpen: _settingsDrawerOpen,
                      insightOpen: _insightOverlayOpen,
                      onTogglePause: viewMode == _SimulationViewMode.review
                          ? null
                          : _togglePlaybackPause,
                      onToggleSettings: () {
                        setState(
                          () => _settingsDrawerOpen = !_settingsDrawerOpen,
                        );
                      },
                      onToggleInsight: hasInsight
                          ? () {
                              setState(
                                () =>
                                    _insightOverlayOpen = !_insightOverlayOpen,
                              );
                            }
                          : null,
                    ),
                  ),
                  if (_buildTheaterBridgeBanner(session)
                      case final bridgeBanner?)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: bridgeBanner,
                    ),
                  if (state.error != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: _InlineErrorBanner(message: state.error!),
                    ),
                  if (_settingsDrawerOpen)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: setupPanel,
                    ),
                  if (participants.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: SizedBox(
                        height: 38,
                        child: ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemCount: participants.length,
                          separatorBuilder: (_, __) => const SizedBox(width: 8),
                          itemBuilder: (context, index) {
                            final participant = participants[index];
                            return _SimulationMiniParticipantPill(
                              participant: participant,
                              isActive: participant.name == activeSpeaker,
                            );
                          },
                        ),
                      ),
                    ),
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: _SimulationTimelineCard(
                      rounds: rounds,
                      participants: participants,
                      activeSpeaker: activeSpeaker,
                      isLoading: state.isLoading,
                      topic: topic,
                      controller: _roundsScrollController,
                      immersive: true,
                      showParticipantSnapshot: false,
                      embedInParentScroll: true,
                    ),
                  ),
                  if (hasInteraction)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: _SimulationInlineInteractionSection(
                        mode: effectiveTrayMode,
                        prompt: interactionPrompt!,
                        onExpand: () => setState(
                          () => _bottomTrayMode =
                              _SimulationBottomTrayMode.expanded,
                        ),
                        onCollapse: () => setState(
                          () =>
                              _bottomTrayMode = _SimulationBottomTrayMode.peek,
                        ),
                        child: _SimulationInteractionCard(
                          prompt: interactionPrompt,
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
                      ),
                    ),
                  if (hasInsight)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: _SimulationInsightTray(
                        summary: insightSummary ?? '',
                        expanded: _isInsightExpanded ||
                            _insightOverlayOpen ||
                            viewMode == _SimulationViewMode.review,
                        onToggleExpanded: () {
                          setState(() {
                            _isInsightExpanded = !_isInsightExpanded;
                            _insightOverlayOpen = _isInsightExpanded;
                          });
                        },
                        session: session,
                        onOpenTheater: session == null
                            ? null
                            : () => context.push(
                                  _buildTheaterRoute(
                                    topic: session.topic,
                                    simulationSessionId: session.id,
                                  ),
                                ),
                        onOpenReport: session == null
                            ? null
                            : () => unawaited(
                                  _openGeneratedLearningReport(session),
                                ),
                        onShare: session == null
                            ? null
                            : () => unawaited(_shareSession(session)),
                        isGeneratingReport: _isGeneratingReport,
                      ),
                    ),
                ]),
              ),
            ),
          ],
        ),
        Positioned(
          right: 16,
          bottom: safeBottom + 20,
          child: AnimatedSlide(
            duration: DS.durationNormal,
            offset: _showScrollToBottomFab ? Offset.zero : const Offset(0, 1.5),
            child: AnimatedOpacity(
              duration: DS.durationNormal,
              opacity: _showScrollToBottomFab ? 1 : 0,
              child: IgnorePointer(
                ignoring: !_showScrollToBottomFab,
                child: FloatingActionButton.small(
                  heroTag: 'simulation-scroll-to-bottom',
                  onPressed: _jumpToBottom,
                  child: const Icon(Icons.south_rounded),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _runSimulation() async {
    final topic = _topicController.text.trim();
    if (topic.isEmpty) {
      return;
    }
    setState(() {
      _isPlaybackPaused = false;
      _settingsDrawerOpen = false;
      _insightOverlayOpen = false;
      _bottomTrayMode = _SimulationBottomTrayMode.expanded;
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
          plannedRoundCount: _configuredRoundCount,
          participantNames: _selectedParticipantNames,
          facilitationStyle: _facilitationStyle,
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
      _scrollToLatestRound(forceImmersive: true);
    }
  }

  void _scrollToLatestRound({bool forceImmersive = false}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      if (_immersiveScrollController.hasClients &&
          (forceImmersive || _shouldFollowImmersiveFeed())) {
        unawaited(
          _immersiveScrollController.animateTo(
            _immersiveScrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 320),
            curve: Curves.easeOutCubic,
          ),
        );
      }
      if (_roundsScrollController.hasClients) {
        unawaited(
          _roundsScrollController.animateTo(
            _roundsScrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 320),
            curve: Curves.easeOutCubic,
          ),
        );
      }
    });
  }

  bool _shouldFollowImmersiveFeed() {
    if (!_immersiveScrollController.hasClients) {
      return false;
    }
    final position = _immersiveScrollController.position;
    if (!position.hasContentDimensions) {
      return false;
    }
    if (position.maxScrollExtent <= 0) {
      return true;
    }
    final distanceToBottom = position.maxScrollExtent - position.pixels;
    return distanceToBottom <= _immersiveAutoScrollFollowThreshold;
  }

  bool _hasPendingUserInteraction(SimulationState state) =>
      state.activeInteraction != null ||
      (state.liveInteractionPrompt?.trim().isNotEmpty ?? false);

  void _handleImmersiveScroll() {
    if (!_immersiveScrollController.hasClients) {
      return;
    }
    final distanceToBottom =
        _immersiveScrollController.position.maxScrollExtent -
            _immersiveScrollController.position.pixels;
    final shouldShow = distanceToBottom > 120;
    if (shouldShow != _showScrollToBottomFab && mounted) {
      setState(() => _showScrollToBottomFab = shouldShow);
    }
  }

  void _jumpToBottom() {
    if (_immersiveScrollController.hasClients) {
      unawaited(
        _immersiveScrollController.animateTo(
          _immersiveScrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 260),
          curve: Curves.easeOutCubic,
        ),
      );
    }
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

  Future<void> _openGeneratedLearningReport(
    SimulationSessionModel session,
  ) async {
    if (_isGeneratingReport) {
      return;
    }
    setState(() => _isGeneratingReport = true);
    try {
      final response = await ref.read(apiClientProvider).post<dynamic>(
        ApiEndpoints.learningReportsGenerate,
        data: <String, dynamic>{
          'section_limit': 5,
          'trigger_source': 'simulation',
        },
      );
      final data = response.data;
      if (data is! Map<String, dynamic>) {
        throw Exception('学习报告返回格式异常');
      }
      final report = LearningReport.fromJson(data);
      if (!mounted) {
        return;
      }
      await context.push(
        ReportRoutes.learningReport,
        extra: _mergeSimulationContextIntoReport(
          session: session,
          report: report,
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('生成学习报告失败：$e'),
          backgroundColor: Theme.of(context).colorScheme.error,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isGeneratingReport = false);
      }
    }
  }

  LearningReport _mergeSimulationContextIntoReport({
    required SimulationSessionModel session,
    required LearningReport report,
  }) {
    final simulationBridgeMarkdown = [
      '# 仿真桥接摘要',
      '',
      '主题：${session.topic}',
      '场景：${_scenarioLabels[session.scenarioKey] ?? localizeSimulationScenario(session.scenarioKey)}',
      '参与者：${session.participants.map((item) => item.name).join('、')}',
      '总轮次：${session.rounds.length} 轮',
      '',
      '## 来自本次模拟的关键洞察',
      '- ${localizeSimulationText(session.insightSummary)}',
      '',
      report.markdown.trim(),
    ].join('\n');
    return LearningReport(
      reportId: report.reportId,
      markdown: simulationBridgeMarkdown,
      sections: <String>[
        '仿真桥接',
        ...report.sections.where((item) => item != '仿真桥接'),
      ],
      mastery: report.mastery,
      patterns: report.patterns,
      timeline: report.timeline,
      diagnosisCards: report.diagnosisCards,
      actionCards: report.actionCards,
      trendOverview: report.trendOverview,
      triggerSummary: report.triggerSummary ??
          const LearningReportTriggerSummary(
            mode: 'simulation_bridge',
            title: '已从学习模拟沉淀为正式报告',
            summary: '先看模拟里暴露出的分歧，再结合完整报告安排下一步。',
          ),
    );
  }

  Future<void> _shareSession(SimulationSessionModel session) async {
    await share_plus.SharePlus.instance.share(
      share_plus.ShareParams(
        text:
            '学习场景模拟\n主题：${session.topic}\n场景：${_scenarioLabels[session.scenarioKey] ?? localizeSimulationScenario(session.scenarioKey)}\n洞察：${localizeSimulationText(session.insightSummary)}',
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
        subtitle: _scenarioLabels[session.scenarioKey] ??
            localizeSimulationScenario(session.scenarioKey),
        description: localizeSimulationText(session.insightSummary),
        metadata: <String, dynamic>{
          'active_plans': session.rounds.length,
          'unlocked_achievements': session.participants.length,
          'flame_brightness':
              session.participants.map((item) => item.name).take(3).join('、'),
        },
        shareMessage:
            '我刚在 Sparkle 跑了一场学习仿真：${session.topic}\n场景：${_scenarioLabels[session.scenarioKey] ?? localizeSimulationScenario(session.scenarioKey)}\n洞察：${localizeSimulationText(session.insightSummary)}',
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
        unawaited(_showSimulationShareSheet(session));
      },
    );
  }

  Future<void> _continueInChat(String reply) async {
    final normalizedReply = reply.trim();
    if (normalizedReply.isEmpty) {
      return;
    }
    final state = ref.read(simulationProvider);
    final session = state.session;
    final topic = (session?.topic ?? _topicController.text.trim()).trim();
    final scenarioLabel =
        _scenarioLabels[session?.scenarioKey ?? _selectedScenarioKey] ??
            localizeSimulationScenario(
              session?.scenarioKey ?? _selectedScenarioKey,
            );
    final currentPrompt = session?.pendingInteraction?.prompt ??
        session?.interactionPrompt ??
        state.liveInteractionPrompt;
    final prompt = [
      if (topic.isNotEmpty) '继续刚才的学习模拟。',
      if (topic.isNotEmpty) '主题：$topic',
      if (scenarioLabel.trim().isNotEmpty) '场景：$scenarioLabel',
      if ((currentPrompt ?? '').trim().isNotEmpty)
        '当前问题：${localizeSimulationText(currentPrompt!)}',
      '我的回应：$normalizedReply',
    ].join('\n');
    final query = <String, String>{
      'prompt': prompt.isEmpty ? normalizedReply : prompt,
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
    final ok = await ref.read(simulationProvider.notifier).continueSimulation(
          normalized,
          plannedRoundCount: _configuredRoundCount,
        );
    if (ok) {
      _interactionController.clear();
    }
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
  Widget build(BuildContext context) {
    final activeLabel = scenarioLabels[selectedScenarioKey] ??
        localizeSimulationScenario(selectedScenarioKey);
    return MirofishStageHeader(
      icon: Icons.groups_rounded,
      eyebrow: '学习场景模拟',
      title: '开始这场学习模拟',
      subtitle: '先选讨论场景，再输入一个你想推开的主题。开始后会自动收束成沉浸式讨论界面。',
      metrics: <MirofishStageMetric>[
        MirofishStageMetric(
          label: '当前场景',
          value: activeLabel,
          accent: DS.info,
          icon: Icons.theater_comedy_rounded,
        ),
        MirofishStageMetric(
          label: '当前目标',
          value: topicController.text.trim().isEmpty
              ? '等待输入'
              : topicController.text.trim(),
          accent: DS.warning,
          icon: Icons.flag_rounded,
        ),
        MirofishStageMetric(
          label: '互动方式',
          value: '角色讨论 + 你来接话',
          accent: DS.success,
          icon: Icons.touch_app_rounded,
        ),
      ],
      primaryLabel: state.isLoading ? '模拟进行中...' : '开始这场模拟',
      onPrimaryTap: state.isLoading ? null : onRun,
      accent: DS.info,
      footer: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
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
                label: Text(
                  state.isLoading ? '模拟进行中...' : '开始这场模拟',
                ),
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
      child: LayoutBuilder(
        builder: (context, constraints) {
          final cardWidth = math.min(
            236.0,
            math.max(196.0, constraints.maxWidth * 0.72),
          );
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '推荐场景',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                  ),
                  TextButton.icon(
                    onPressed: onRefresh,
                    icon: const Icon(Icons.refresh_rounded),
                    label: Text(seeds.isEmpty ? '生成' : '刷新'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                seeds.isEmpty
                    ? '还没有推荐种子，你可以先手动输入主题开始。'
                    : '先挑一个最顺手的起点，开始后推荐卡会自动收起，不打断正式讨论。',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              if (seeds.isNotEmpty) ...[
                const SizedBox(height: 12),
                SizedBox(
                  height: 194,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: seeds.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 10),
                    itemBuilder: (context, index) => SizedBox(
                      width: cardWidth,
                      child: _RecommendedSeedCard(
                        seed: seeds[index],
                        scenarioLabel:
                            scenarioLabels[seeds[index].suggestedScenario] ??
                                localizeSimulationScenario(
                                  seeds[index].suggestedScenario,
                                ),
                        onStart: () => onStartSeed(seeds[index]),
                        onOpenTheater: () => onOpenTheater(seeds[index]),
                      ),
                    ),
                  ),
                ),
              ],
            ],
          );
        },
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
        padding: const EdgeInsets.all(12),
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
              localizeSimulationText(seed.context),
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
                  Chip(
                    label: Text(
                      localizeSimulationRoleHint(seed.suggestedExperts.first),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              localizeSimulationText(seed.tensionPoint),
              maxLines: 2,
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
                  child: const Text('开始模拟'),
                ),
                OutlinedButton(
                  onPressed: onOpenTheater,
                  child: const Text('去推演'),
                ),
              ],
            ),
          ],
        ),
      );
}

class _SimulationImmersiveTopBar extends StatelessWidget {
  const _SimulationImmersiveTopBar({
    required this.topic,
    required this.scenarioLabel,
    required this.roundCount,
    required this.expectedRounds,
    required this.engineState,
    required this.activeSpeaker,
    required this.participantCount,
    required this.facilitationLabel,
    required this.isPaused,
    required this.isReview,
    required this.hasInsight,
    required this.settingsOpen,
    required this.insightOpen,
    required this.onToggleSettings,
    this.onTogglePause,
    this.onToggleInsight,
  });

  final String topic;
  final String scenarioLabel;
  final int roundCount;
  final int expectedRounds;
  final String? engineState;
  final String? activeSpeaker;
  final int participantCount;
  final String facilitationLabel;
  final bool isPaused;
  final bool isReview;
  final bool hasInsight;
  final bool settingsOpen;
  final bool insightOpen;
  final VoidCallback onToggleSettings;
  final VoidCallback? onTogglePause;
  final VoidCallback? onToggleInsight;

  @override
  Widget build(BuildContext context) {
    final titleStyle = Theme.of(context).textTheme.titleSmall?.copyWith(
          fontWeight: FontWeight.w800,
        );
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 680;
        final actionRow = Wrap(
          alignment: WrapAlignment.end,
          spacing: 8,
          runSpacing: 8,
          children: [
            if (!isReview)
              IconButton.filledTonal(
                tooltip: isPaused ? '继续模拟' : '暂停模拟',
                onPressed: onTogglePause,
                icon: Icon(
                  isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
                ),
              ),
            if (hasInsight)
              FilledButton.tonalIcon(
                onPressed: onToggleInsight,
                icon: Icon(
                  insightOpen
                      ? Icons.lightbulb_outline_rounded
                      : (isReview
                          ? Icons.insights_rounded
                          : Icons.lightbulb_circle_rounded),
                ),
                label: Text(insightOpen ? '收起洞察' : '查看洞察'),
              ),
            FilledButton.tonalIcon(
              onPressed: onToggleSettings,
              icon: Icon(
                settingsOpen ? Icons.expand_less_rounded : Icons.tune_rounded,
              ),
              label: Text(settingsOpen ? '收起设置' : '模拟设置'),
            ),
          ],
        );
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              topic,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: titleStyle,
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _StatusBadge(
                  icon: Icons.theater_comedy_rounded,
                  label: scenarioLabel,
                ),
                _StatusBadge(
                  icon: Icons.forum_rounded,
                  label:
                      '${math.max(1, roundCount)}/${math.max(expectedRounds, roundCount)} 轮',
                ),
                _StatusBadge(
                  icon: Icons.groups_rounded,
                  label: '$participantCount 角色',
                ),
                _StatusBadge(
                  icon: Icons.tune_rounded,
                  label: facilitationLabel,
                ),
                if ((activeSpeaker ?? '').isNotEmpty)
                  _StatusBadge(
                    icon: Icons.mic_rounded,
                    label: localizeSimulationText(activeSpeaker!),
                  ),
                if ((engineState ?? '').isNotEmpty)
                  _StatusBadge(
                    icon: Icons.memory_rounded,
                    label: localizeSimulationEngineState(engineState),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            if (compact)
              actionRow
            else
              Align(
                alignment: Alignment.centerRight,
                child: actionRow,
              ),
          ],
        );
      },
    );
  }
}

class _SimulationInlineInteractionSection extends StatelessWidget {
  const _SimulationInlineInteractionSection({
    required this.mode,
    required this.prompt,
    required this.child,
    required this.onExpand,
    required this.onCollapse,
  });

  final _SimulationBottomTrayMode mode;
  final String prompt;
  final Widget child;
  final VoidCallback onExpand;
  final VoidCallback onCollapse;

  @override
  Widget build(BuildContext context) {
    if (mode == _SimulationBottomTrayMode.peek) {
      return GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: InkWell(
          onTap: onExpand,
          borderRadius: BorderRadius.circular(18),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.chat_bubble_outline_rounded),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '轮到你回应',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      localizeSimulationText(prompt),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.4,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              const Icon(Icons.expand_more_rounded),
            ],
          ),
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
              Expanded(
                child: Text(
                  '你的回应区',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
              TextButton.icon(
                onPressed: onCollapse,
                icon: const Icon(Icons.expand_less_rounded),
                label: const Text('收起'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}

class _InlineErrorBanner extends StatelessWidget {
  const _InlineErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: scheme.errorContainer.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline_rounded, color: scheme.error),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: scheme.error,
                    fontWeight: FontWeight.w700,
                    height: 1.4,
                  ),
            ),
          ),
        ],
      ),
    );
  }
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

  Color _interactionAccent(String? raw) {
    switch (raw) {
      case 'challenge':
        return DS.warning;
      case 'forced_choice':
      case 'vote':
        return DS.brandPrimary;
      default:
        return DS.info;
    }
  }

  IconData _interactionIcon(String? raw) {
    switch (raw) {
      case 'challenge':
        return Icons.bolt_rounded;
      case 'forced_choice':
      case 'vote':
        return Icons.rule_rounded;
      default:
        return Icons.record_voice_over_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final accent = _interactionAccent(interactionType);
    final localizedPrompt = localizeSimulationText(prompt);
    final localizedSuggestedReplies = suggestedReplies
        .map(localizeSimulationText)
        .where((item) => item.trim().isNotEmpty)
        .toList();
    final localizedOptions = options
        .map(localizeSimulationText)
        .where((item) => item.trim().isNotEmpty)
        .toList();
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: accent.withValues(alpha: 0.18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  _interactionIcon(interactionType),
                  color: accent,
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
            '先给出你的判断，下一轮才会真正围绕你的想法继续展开。',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
          ),
          const SizedBox(height: 10),
          Text(
            localizedPrompt,
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
          if (localizedOptions.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: localizedOptions
                  .take(4)
                  .map(
                    (option) => Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: accent.withValues(alpha: 0.14),
                        ),
                      ),
                      child: Text(
                        option,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: accent,
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: localizedSuggestedReplies
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
                label: Text(isSubmitting ? '提交中...' : '提交我的判断'),
              ),
              if (localizedSuggestedReplies.isNotEmpty)
                OutlinedButton.icon(
                  onPressed: isSubmitting
                      ? null
                      : () {
                          final draft = textController.text.trim();
                          onContinueInChat(
                            draft.isNotEmpty
                                ? draft
                                : localizedSuggestedReplies.first,
                          );
                        },
                  icon: const Icon(Icons.chat_bubble_outline_rounded),
                  label: const Text('带回聊天继续'),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            '建议先在这里接住一轮，让角色回应你的判断；如果你想回到主对话，也可以把这一步带回聊天继续。',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
        ],
      ),
    );
  }

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

class _SimulationCompactSetupPanel extends StatelessWidget {
  const _SimulationCompactSetupPanel({
    required this.topicController,
    required this.customParticipantController,
    required this.selectedScenarioKey,
    required this.scenarioLabels,
    required this.scenarioDescriptions,
    required this.isLoading,
    required this.facilitationStyle,
    required this.facilitationLabels,
    required this.facilitationDescriptions,
    required this.plannedRoundCount,
    required this.maxRoundCount,
    required this.selectedParticipantNames,
    required this.availableParticipantNames,
    required this.isHistoricalRoleplay,
    required this.onScenarioSelected,
    required this.onFacilitationStyleSelected,
    required this.onRoundCountChanged,
    required this.onParticipantToggled,
    required this.onCustomParticipantAdded,
    required this.onResetParticipants,
    required this.onRun,
  });

  final TextEditingController topicController;
  final TextEditingController customParticipantController;
  final String selectedScenarioKey;
  final Map<String, String> scenarioLabels;
  final Map<String, String> scenarioDescriptions;
  final bool isLoading;
  final String facilitationStyle;
  final Map<String, String> facilitationLabels;
  final Map<String, String> facilitationDescriptions;
  final int plannedRoundCount;
  final int maxRoundCount;
  final List<String> selectedParticipantNames;
  final List<String> availableParticipantNames;
  final bool isHistoricalRoleplay;
  final ValueChanged<String> onScenarioSelected;
  final ValueChanged<String> onFacilitationStyleSelected;
  final ValueChanged<int> onRoundCountChanged;
  final ValueChanged<String> onParticipantToggled;
  final ValueChanged<String> onCustomParticipantAdded;
  final VoidCallback onResetParticipants;
  final VoidCallback onRun;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '调整这场模拟',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              '这里可以完整调整主题、场景、轮数、展开方式和参与角色，开始后讨论会按这套设置运行。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: topicController,
              textInputAction: TextInputAction.go,
              onSubmitted: (_) {
                if (!isLoading) {
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
                      onSelected: isLoading
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
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context)
                    .colorScheme
                    .surfaceContainerHighest
                    .withValues(alpha: 0.72),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Text(
                scenarioDescriptions[selectedScenarioKey] ??
                    '调整场景后，讨论的角色关系与推进方式也会一起变化。',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '讨论轮数',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
                _StatusBadge(
                  icon: Icons.timelapse_rounded,
                  label: '$plannedRoundCount / $maxRoundCount 轮',
                ),
              ],
            ),
            const SizedBox(height: 8),
            Slider(
              value: plannedRoundCount.toDouble(),
              min: 3,
              max: maxRoundCount.toDouble(),
              divisions: math.max(0, maxRoundCount - 3),
              label: '$plannedRoundCount 轮',
              onChanged: (value) => onRoundCountChanged(value.round()),
            ),
            const SizedBox(height: 8),
            Text(
              '展开方式',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: facilitationLabels.entries.map((entry) {
                final selected = facilitationStyle == entry.key;
                return ChoiceChip(
                  label: Text(entry.value),
                  selected: selected,
                  onSelected: isLoading
                      ? null
                      : (value) {
                          if (value) {
                            onFacilitationStyleSelected(entry.key);
                          }
                        },
                );
              }).toList(),
            ),
            const SizedBox(height: 8),
            Text(
              facilitationDescriptions[facilitationStyle] ?? '让讨论更贴合当前主题。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '参与角色',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
                TextButton.icon(
                  onPressed: isLoading ? null : onResetParticipants,
                  icon: const Icon(Icons.restart_alt_rounded),
                  label: const Text('恢复推荐'),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              '你可以明确指定想邀请谁参与这场讨论。至少保留 1 位，最多 6 位角色。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: availableParticipantNames.map((name) {
                final selected = selectedParticipantNames.contains(name);
                return FilterChip(
                  label: Text(name),
                  selected: selected,
                  onSelected:
                      isLoading ? null : (_) => onParticipantToggled(name),
                );
              }).toList(),
            ),
            if (isHistoricalRoleplay) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: customParticipantController,
                      textInputAction: TextInputAction.done,
                      onSubmitted: onCustomParticipantAdded,
                      decoration: const InputDecoration(
                        labelText: '自定义历史人物',
                        hintText: '例如：张居正 / 俾斯麦',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  FilledButton.tonalIcon(
                    onPressed: () => onCustomParticipantAdded(
                      customParticipantController.text,
                    ),
                    icon: const Icon(Icons.add_rounded),
                    label: const Text('添加'),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 10),
            Text(
              selectedParticipantNames.isEmpty
                  ? '当前将按系统默认角色运行。'
                  : '当前参与：${selectedParticipantNames.join('、')}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.icon(
                onPressed: isLoading ? null : onRun,
                icon: const Icon(Icons.refresh_rounded),
                label: Text(isLoading ? '模拟进行中...' : '重新开始这场模拟'),
              ),
            ),
          ],
        ),
      );
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
                        localizeSimulationEngineState(engineState),
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
                if ((activeSpeaker ?? '').isNotEmpty)
                  _StatusBadge(
                    icon: Icons.mic_rounded,
                    label: '当前焦点：$activeSpeaker',
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
    this.height,
    this.immersive = false,
    this.showParticipantSnapshot = true,
    this.embedInParentScroll = false,
  });

  final List<SimulationRoundModel> rounds;
  final List<SimulationParticipantModel> participants;
  final String? activeSpeaker;
  final bool isLoading;
  final String topic;
  final ScrollController controller;
  final double? height;
  final bool immersive;
  final bool showParticipantSnapshot;
  final bool embedInParentScroll;

  @override
  Widget build(BuildContext context) {
    final participantByName = <String, SimulationParticipantModel>{
      for (final participant in participants) participant.name: participant,
    };
    final timelineList = rounds.isEmpty
        ? _SimulationEmptyState(isLoading: isLoading)
        : embedInParentScroll
            ? Column(
                children: [
                  for (var index = 0; index < rounds.length; index++) ...[
                    if (index > 0)
                      _RoundDivider(
                        round: rounds[index - 1].round,
                      ),
                    SimulationChatBubble(
                      key: ValueKey(
                        '${rounds[index].round}-${rounds[index].speaker}-${rounds[index].message}',
                      ),
                      speaker: rounds[index].speaker,
                      participant: participantByName[rounds[index].speaker],
                      message: rounds[index].message,
                      round: rounds[index].round,
                      replyToSpeaker: rounds[index].replyToSpeaker,
                      turnGoal: rounds[index].turnGoal,
                      isSpotlighted: rounds[index].speaker == activeSpeaker &&
                          index == rounds.length - 1,
                    ),
                  ],
                ],
              )
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
                    isSpotlighted: round.speaker == activeSpeaker &&
                        index == rounds.length - 1,
                  );
                },
              );
    if (immersive && embedInParentScroll) {
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
                        '沉浸讨论流',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        topic.isEmpty
                            ? '开始后会实时出现每一轮讨论。'
                            : activeSpeaker == null
                                ? '主题：$topic'
                                : '主题：$topic · 当前发言 ${localizeSimulationText(activeSpeaker!)}',
                        maxLines: 2,
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
            const SizedBox(height: 12),
            timelineList,
          ],
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
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      immersive ? '沉浸讨论流' : '当前讨论流',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      topic.isEmpty
                          ? '开始后会实时出现每一轮讨论。'
                          : activeSpeaker == null
                              ? '主题：$topic'
                              : immersive
                                  ? '当前焦点：${localizeSimulationText(activeSpeaker!)}'
                                  : '主题：$topic · 当前发言 ${localizeSimulationText(activeSpeaker!)}',
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
          if (showParticipantSnapshot && participants.isNotEmpty) ...[
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
          if (embedInParentScroll)
            timelineList
          else
            SizedBox(
              height: height ?? 320,
              child: timelineList,
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
    this.isGeneratingReport = false,
  });

  final String summary;
  final bool expanded;
  final VoidCallback onToggleExpanded;
  final SimulationSessionModel? session;
  final bool isGeneratingReport;
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
                          localizeSimulationText(previewText),
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
                  onPressed: isGeneratingReport ? null : onOpenReport,
                  icon: isGeneratingReport
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.article_outlined),
                  label: Text(isGeneratingReport ? '生成中...' : '生成学习报告'),
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
      points
          .add('开场重点：${localizeSimulationText(session.rounds.first.message)}');
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

class _SimulationMiniParticipantPill extends StatelessWidget {
  const _SimulationMiniParticipantPill({
    required this.participant,
    this.isActive = false,
  });

  final SimulationParticipantModel participant;
  final bool isActive;

  @override
  Widget build(BuildContext context) {
    final accent = _accentForName(participant.name);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: isActive ? 0.14 : 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: accent.withValues(alpha: isActive ? 0.28 : 0.14),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(
            radius: 10,
            backgroundColor: accent.withValues(alpha: 0.12),
            child: Text(
              participant.name.isEmpty ? '?' : participant.name[0],
              style: TextStyle(
                fontSize: 10,
                color: accent,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            participant.name,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: accent,
                  fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
                ),
          ),
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
    final localizedRoleHint = localizeSimulationRoleHint(participant.roleHint);
    final localizedStance = localizeSimulationStance(participant.stance);
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
          if (localizedRoleHint.isNotEmpty || localizedStance.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              [
                if (localizedRoleHint.isNotEmpty) localizedRoleHint,
                if (localizedStance.isNotEmpty) localizedStance,
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
