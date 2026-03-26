import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/services/sensory_feedback_service.dart';
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
  });

  final String? initialTopic;
  final String? initialScenarioKey;

  @override
  ConsumerState<SimulationScreen> createState() => _SimulationScreenState();
}

class _SimulationScreenState extends ConsumerState<SimulationScreen> {
  static const Map<String, String> _scenarioLabels = {
    'study_group': '虚拟学习小组',
    'knowledge_debate': '知识辩论',
    'historical_roleplay': '历史角色扮演',
    'socratic_dialogue': '苏格拉底式对话',
  };

  final _topicController = TextEditingController();
  final _roundsScrollController = ScrollController();
  late String _selectedScenarioKey;
  late final ProviderSubscription<SimulationState> _simulationSubscription;
  bool _isPlaybackPaused = false;
  List<SimulationParticipantModel>? _pausedParticipants;
  List<SimulationRoundModel>? _pausedRounds;
  String? _pausedInsightSummary;

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
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          _scrollToLatestRound();
        }

        final previousParticipantCount = previous?.liveParticipants.length ?? 0;
        final nextParticipantCount = next.liveParticipants.length;
        if (nextParticipantCount > previousParticipantCount && !_isPlaybackPaused) {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
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
    final participants =
        _isPlaybackPaused ? (_pausedParticipants ?? liveParticipants) : liveParticipants;
    final rounds = _isPlaybackPaused ? (_pausedRounds ?? liveRounds) : liveRounds;
    final insightSummary = _isPlaybackPaused
        ? (_pausedInsightSummary ?? liveInsightSummary)
        : liveInsightSummary;
    final roundCount = rounds.length;
    final expectedRounds = _expectedRoundsForScenario(
      session?.scenarioKey ?? _selectedScenarioKey,
    );

    return Scaffold(
      appBar: AppBar(title: const Text('学习场景模拟')),
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Theme.of(context)
                  .colorScheme
                  .surfaceContainerHighest
                  .withValues(alpha: 0.42),
              Theme.of(context).scaffoldBackgroundColor,
            ],
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _SimulationComposer(
                topicController: _topicController,
                selectedScenarioKey: _selectedScenarioKey,
                scenarioLabels: _scenarioLabels,
                state: state,
                onScenarioSelected: (value) {
                  setState(() => _selectedScenarioKey = value);
                  unawaited(
                    ref.read(simulationProvider.notifier).loadRecommendedSeeds(
                          scenarioKey: value,
                          silent: true,
                        ),
                  );
                },
                onRun: () => unawaited(_runSimulation()),
              ),
              const SizedBox(height: 14),
              _RecommendedSeedSection(
                seeds: state.recommendedSeeds,
                isLoading: state.isLoadingRecommendations,
                scenarioLabels: _scenarioLabels,
                onRefresh: () => unawaited(
                  ref.read(simulationProvider.notifier).loadRecommendedSeeds(
                        scenarioKey: _selectedScenarioKey,
                      ),
                ),
                onStartSeed: (seed) {
                  setState(() => _selectedScenarioKey = seed.suggestedScenario);
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
              if (state.isLoading || state.progress > 0)
                _SimulationProgressHeader(
                  progress: state.progress,
                  engineState: state.engineState,
                  roundCount: roundCount,
                  expectedRounds: expectedRounds,
                  isPaused: _isPlaybackPaused,
                  hasBufferedUpdates: _isPlaybackPaused &&
                      (liveRounds.length > rounds.length ||
                          liveParticipants.length > participants.length),
                  onTogglePause: _togglePlaybackPause,
                ),
              if (state.error != null) ...[
                const SizedBox(height: 12),
                Text(
                  state.error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              if (participants.isNotEmpty) ...[
                const SizedBox(height: 14),
                _ParticipantStrip(participants: participants),
              ],
              if (insightSummary != null && insightSummary.isNotEmpty) ...[
                const SizedBox(height: 14),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  padding: const EdgeInsets.all(14),
                  child: Text(
                    insightSummary,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          height: 1.45,
                        ),
                  ),
                ),
              ],
              const SizedBox(height: 14),
              Expanded(
                child: GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  padding: const EdgeInsets.all(14),
                  child: rounds.isEmpty
                      ? _SimulationEmptyState(isLoading: state.isLoading)
                      : ListView.separated(
                          controller: _roundsScrollController,
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
                              message: round.message,
                              round: round.round,
                            );
                          },
                        ),
                ),
              ),
              if (session != null && session.insightSummary.isNotEmpty) ...[
                const SizedBox(height: 14),
                _SimulationInsightFooter(
                  session: session,
                  onOpenTheater: () => context.push(
                    '${TheaterRoutes.theater}?topic=${Uri.encodeComponent(session.topic)}',
                  ),
                  onOpenReport: () => context.push(
                    ReportRoutes.learningReport,
                    extra: _buildSimulationReport(session),
                  ),
                  onShare: () => unawaited(_shareSession(session)),
                ),
              ],
            ],
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
    final liveInsightSummary = session?.insightSummary ?? state.liveInsightSummary;
    setState(() {
      _isPlaybackPaused = !_isPlaybackPaused;
      if (_isPlaybackPaused) {
        _pausedParticipants = List<SimulationParticipantModel>.from(liveParticipants);
        _pausedRounds = List<SimulationRoundModel>.from(liveRounds);
        _pausedInsightSummary = liveInsightSummary;
      } else {
        _pausedParticipants = null;
        _pausedRounds = null;
        _pausedInsightSummary = null;
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '把一个知识点变成现场讨论',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              '选择场景后，AI 会像一个正在进行的对话剧场一样，逐轮展开不同角色的观点。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: topicController,
              decoration: const InputDecoration(
                labelText: '输入一个知识点或主题',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: selectedScenarioKey,
              decoration: const InputDecoration(
                labelText: '选择场景',
                border: OutlineInputBorder(),
              ),
              items: scenarioLabels.entries
                  .map(
                    (entry) => DropdownMenuItem<String>(
                      value: entry.key,
                      child: Text(entry.value),
                    ),
                  )
                  .toList(),
              onChanged: state.isLoading
                  ? null
                  : (value) {
                      if (value != null) {
                        onScenarioSelected(value);
                      }
                    },
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: state.isLoading ? null : onRun,
              icon: const Icon(Icons.play_circle_outline_rounded),
              label: Text(state.isLoading ? '模拟进行中...' : '开始模拟'),
            ),
          ],
        ),
      );
}

class _SimulationProgressHeader extends StatelessWidget {
  const _SimulationProgressHeader({
    required this.progress,
    required this.engineState,
    required this.roundCount,
    required this.expectedRounds,
    required this.isPaused,
    required this.hasBufferedUpdates,
    required this.onTogglePause,
  });

  final double progress;
  final String? engineState;
  final int roundCount;
  final int expectedRounds;
  final bool isPaused;
  final bool hasBufferedUpdates;
  final VoidCallback onTogglePause;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    roundCount > 0
                        ? '正在第 $roundCount/$expectedRounds 轮...'
                        : '正在召集参与者...',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: onTogglePause,
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
                value: progress.clamp(0.0, 1.0),
                minHeight: 8,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              engineState == null ? '准备中' : '当前状态：$engineState',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            if (isPaused) ...[
              const SizedBox(height: 8),
              Text(
                hasBufferedUpdates
                    ? '已暂停前台播放，后台仍在继续生成。点击继续可追上最新轮次。'
                    : '已暂停前台播放，你可以先回看已生成的讨论。',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ],
        ),
      );
}

class _ParticipantStrip extends StatelessWidget {
  const _ParticipantStrip({required this.participants});

  final List<SimulationParticipantModel> participants;

  @override
  Widget build(BuildContext context) => SizedBox(
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
            );
          },
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

class _AnimatedParticipantChip extends StatefulWidget {
  const _AnimatedParticipantChip({
    required this.participant,
    required this.accent,
  });

  final SimulationParticipantModel participant;
  final Color accent;

  @override
  State<_AnimatedParticipantChip> createState() => _AnimatedParticipantChipState();
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
              color: Theme.of(context)
                  .colorScheme
                  .surfaceContainerHighest
                  .withValues(alpha: 0.72),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircleAvatar(
                  radius: 12,
                  backgroundColor: widget.accent.withValues(alpha: 0.14),
                  child: Text(
                    widget.participant.name.isEmpty ? '?' : widget.participant.name[0],
                    style: TextStyle(
                      fontSize: 11,
                      color: widget.accent,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(widget.participant.name),
              ],
            ),
          ),
        ),
      );
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

class _SimulationInsightFooter extends StatelessWidget {
  const _SimulationInsightFooter({
    required this.session,
    required this.onOpenTheater,
    required this.onOpenReport,
    required this.onShare,
  });

  final SimulationSessionModel session;
  final VoidCallback onOpenTheater;
  final VoidCallback onOpenReport;
  final VoidCallback onShare;

  @override
  Widget build(BuildContext context) {
    final bulletPoints = _buildBulletPoints(session);
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '洞察总结',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            session.insightSummary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  height: 1.45,
                ),
          ),
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
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.tonalIcon(
                onPressed: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  onOpenReport();
                },
                icon: const Icon(Icons.article_outlined),
                label: const Text('生成学习报告'),
              ),
              FilledButton.tonalIcon(
                onPressed: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  onOpenTheater();
                },
                icon: const Icon(Icons.auto_graph_rounded),
                label: const Text('以此推演'),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                  );
                  onShare();
                },
                icon: const Icon(Icons.share_outlined),
                label: const Text('分享洞察'),
              ),
            ],
          ),
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

class _RecommendedSeedSection extends StatelessWidget {
  const _RecommendedSeedSection({
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
    if (seeds.isEmpty) {
      return OutlinedButton.icon(
        onPressed: onRefresh,
        icon: const Icon(Icons.auto_awesome),
        label: const Text('生成推荐场景'),
      );
    }

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '为你推荐',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: onRefresh,
                icon: const Icon(Icons.refresh),
                label: const Text('刷新'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...seeds.map(
            (seed) => Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    seed.topic,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(seed.context),
                  const SizedBox(height: 8),
                  Text(
                    seed.tensionPoint,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      Chip(
                        label: Text(
                          scenarioLabels[seed.suggestedScenario] ??
                              seed.suggestedScenario,
                        ),
                      ),
                      ...seed.suggestedExperts.map(
                        (expert) => Chip(label: Text(expert)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      FilledButton.tonal(
                        onPressed: () => onStartSeed(seed),
                        child: const Text('开始'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        onPressed: () => onOpenTheater(seed),
                        child: const Text('转为推演'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
