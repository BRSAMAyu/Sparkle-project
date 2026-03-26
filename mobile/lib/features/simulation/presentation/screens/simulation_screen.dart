import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/presentation/widgets/simulation_chat_bubble.dart';

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
                    },
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: state.isLoading
                  ? null
                  : () => ref.read(simulationProvider.notifier).run(
                        topic: _topicController.text.trim(),
                        scenarioKey: _selectedScenarioKey,
                      ),
              child: Text(state.isLoading ? '生成中...' : '开始模拟'),
            ),
            if (state.isLoading || state.progress > 0) ...[
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: LinearProgressIndicator(value: state.progress.clamp(0.0, 1.0)),
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
