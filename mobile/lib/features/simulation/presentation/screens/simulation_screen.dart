import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/presentation/widgets/simulation_chat_bubble.dart';
import 'package:sparkle/features/theater/theater_routes.dart';

class SimulationScreen extends ConsumerStatefulWidget {
  const SimulationScreen({super.key});

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
  String _selectedScenarioKey = 'study_group';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        ref.read(simulationProvider.notifier).loadRecommendedSeeds(
              scenarioKey: _selectedScenarioKey,
              silent: true,
            ),
      );
    });
  }

  @override
  void dispose() {
    _topicController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(simulationProvider);
    final session = state.session;
    final participants = session?.participants ?? state.liveParticipants;
    final rounds = session?.rounds ?? state.liveRounds;
    final insightSummary = session?.insightSummary ??
        state.liveInsightSummary ??
        (state.isLoading ? '模拟进行中，新的轮次会实时出现在下方。' : null);

    return Scaffold(
      appBar: AppBar(title: const Text('学习场景模拟')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _topicController,
              decoration: const InputDecoration(
                labelText: '输入一个知识点或主题',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _selectedScenarioKey,
              decoration: const InputDecoration(
                labelText: '选择场景',
                border: OutlineInputBorder(),
              ),
              items: _scenarioLabels.entries
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
                      if (value == null) return;
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
            ),
            const SizedBox(height: 16),
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
            const SizedBox(height: 12),
            FilledButton(
              onPressed: state.isLoading
                  ? null
                  : () => unawaited(
                        ref.read(simulationProvider.notifier).run(
                              topic: _topicController.text.trim(),
                              scenarioKey: _selectedScenarioKey,
                            ),
                      ),
              child: Text(state.isLoading ? '生成中...' : '开始模拟'),
            ),
            if (state.isLoading || state.progress > 0) ...[
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: LinearProgressIndicator(
                  value: state.progress.clamp(0.0, 1.0),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                state.engineState == null
                    ? '正在准备模拟...'
                    : '当前状态：${state.engineState}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (state.error != null) ...[
              const SizedBox(height: 12),
              Text(
                state.error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 16),
            if (participants.isNotEmpty) ...[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: participants
                    .map(
                      (participant) => Chip(
                        label: Text(
                          _participantLabel(participant),
                        ),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 16),
            ],
            if (insightSummary != null) ...[
              Text(
                insightSummary,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 16),
            ],
            if (rounds.isNotEmpty)
              Expanded(
                child: ListView(
                  children: rounds
                      .map(
                        (round) => SimulationChatBubble(
                          speaker: round.speaker,
                          message: round.message,
                        ),
                      )
                      .toList(),
                ),
              ),
          ],
        ),
      ),
    );
  }

  String _participantLabel(SimulationParticipantModel participant) {
    if ((participant.source ?? '') == 'knowledge_graph' &&
        (participant.sourceNodeName ?? '').isNotEmpty) {
      return '${participant.name} · 图谱角色';
    }
    return participant.name;
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

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              '为你推荐',
              style: Theme.of(context).textTheme.titleMedium,
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
          (seed) => Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    seed.topic,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 6),
                  Text(seed.context),
                  const SizedBox(height: 8),
                  Text(
                    seed.tensionPoint,
                    style: Theme.of(context).textTheme.bodySmall,
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
                  Align(
                    alignment: Alignment.centerRight,
                    child: Wrap(
                      spacing: 8,
                      children: [
                        OutlinedButton(
                          onPressed: () => onOpenTheater(seed),
                          child: const Text('推演剧场'),
                        ),
                        FilledButton(
                          onPressed: () => onStartSeed(seed),
                          child: const Text('一键开始'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
