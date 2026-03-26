import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:share_plus/share_plus.dart' as share_plus;
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/features/theater/presentation/providers/theater_provider.dart';
import 'package:sparkle/features/theater/presentation/widgets/knowledge_theater_graph.dart';

class KnowledgeTheaterScreen extends ConsumerStatefulWidget {
  const KnowledgeTheaterScreen({
    super.key,
    this.initialTopic,
    this.initialTargetNodeId,
  });

  final String? initialTopic;
  final String? initialTargetNodeId;

  @override
  ConsumerState<KnowledgeTheaterScreen> createState() =>
      _KnowledgeTheaterScreenState();
}

class _KnowledgeTheaterScreenState
    extends ConsumerState<KnowledgeTheaterScreen> {
  late final TextEditingController _topicController;

  @override
  void initState() {
    super.initState();
    _topicController = TextEditingController(text: widget.initialTopic ?? '');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if ((widget.initialTopic ?? '').trim().isNotEmpty) {
        unawaited(
          ref.read(theaterProvider.notifier).generatePrediction(
                topic: widget.initialTopic!.trim(),
                targetNodeId: widget.initialTargetNodeId,
              ),
        );
      }
    });
  }

  @override
  void dispose() {
    _topicController.dispose();
    ref.read(theaterProvider.notifier).clearOverlay();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(theaterProvider);
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
            const []);

    return Scaffold(
      appBar: AppBar(
        title: const Text('知识推演剧场'),
        actions: [
          IconButton(
            onPressed: state.snapshot == null ? null : _shareSnapshotSummary,
            icon: const Icon(Icons.share_outlined),
          ),
          IconButton(
            onPressed:
                state.snapshot != null ? () => context.go('/galaxy') : null,
            icon: const Icon(Icons.auto_graph_rounded),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              _buildComposer(state),
              const SizedBox(height: 16),
              Expanded(
                child: prediction == null
                    ? _EmptyState(isLoading: state.isLoading)
                    : ListView(
                        children: [
                          KnowledgeTheaterGraph(
                            nodes: prediction.graphNodes,
                            edges: prediction.graphEdges,
                            focusNodeIds: focusNodeIds,
                          ),
                          if (timeline.isNotEmpty) ...[
                            const SizedBox(height: 16),
                            Text(
                              '推演时间轴',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            Slider(
                              max: (timeline.length - 1).toDouble(),
                              divisions: timeline.length - 1,
                              value: timelineIndex.toDouble(),
                              label: timeline[timelineIndex].label,
                              onChanged: (value) => ref
                                  .read(theaterProvider.notifier)
                                  .setTimelineIndex(value.round()),
                            ),
                          ],
                          const SizedBox(height: 16),
                          _RouteSection(
                            routes: prediction.paths,
                            selectedRouteId: route?.id,
                            onSelect: (routeId) => ref
                                .read(theaterProvider.notifier)
                                .selectRoute(routeId),
                            onAdopt: route == null
                                ? null
                                : () => unawaited(
                                      ref
                                          .read(theaterProvider.notifier)
                                          .adoptSelectedRoute(),
                                    ),
                            isAdopting: state.isAdopting,
                            adoptionResult: state.adoptionResult,
                          ),
                          if (route != null) ...[
                            const SizedBox(height: 18),
                            _WhatIfSection(
                              route: route,
                              result: state.whatIfResult,
                              onRun: (nodeId) => unawaited(
                                ref
                                    .read(theaterProvider.notifier)
                                    .runWhatIfForStep(nodeId),
                              ),
                            ),
                          ],
                          const SizedBox(height: 18),
                          _DiscussionSection(turns: prediction.discussionTurns),
                          const SizedBox(height: 18),
                          _SnapshotSection(
                            snapshot: state.snapshot,
                            isSaving: state.isSavingSnapshot,
                            onSave: () => unawaited(
                              ref.read(theaterProvider.notifier).saveSnapshot(),
                            ),
                          ),
                          if (state.accuracySummary != null) ...[
                            const SizedBox(height: 18),
                            _AccuracyCard(summary: state.accuracySummary!),
                          ],
                          if (state.error != null) ...[
                            const SizedBox(height: 18),
                            Text(
                              state.error!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                          ],
                        ],
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildComposer(TheaterState state) => Row(
        children: [
          Expanded(
            child: TextField(
              controller: _topicController,
              decoration: const InputDecoration(
                labelText: '输入学习目标或知识主题',
                border: OutlineInputBorder(),
              ),
            ),
          ),
          const SizedBox(width: 12),
          FilledButton(
            onPressed: state.isLoading
                ? null
                : () => unawaited(
                      ref.read(theaterProvider.notifier).generatePrediction(
                            topic: _topicController.text.trim(),
                            targetNodeId: widget.initialTargetNodeId,
                          ),
                    ),
            child: Text(state.isLoading ? '推演中' : '开始推演'),
          ),
        ],
      );

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
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.isLoading});

  final bool isLoading;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isLoading) const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(
              isLoading ? '正在推演学习路径...' : '输入一个目标，查看多条学习路径与专家讨论。',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
}

class _RouteSection extends StatelessWidget {
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
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('路径推演', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...routes.map(
            (route) => Card(
              color: route.id == selectedRouteId
                  ? Theme.of(context).colorScheme.primaryContainer
                  : null,
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                onTap: () => onSelect(route.id),
                title: Text(route.title),
                subtitle: Text(
                  '${route.summary}\n完成率 ${(route.estimatedCompletionRate * 100).round()}% · '
                  '掌握度 ${route.estimatedMastery.round()}%',
                ),
                isThreeLine: true,
                trailing: route.id == selectedRouteId
                    ? FilledButton(
                        onPressed: isAdopting ? null : onAdopt,
                        child: Text(isAdopting ? '采纳中' : '采纳'),
                      )
                    : null,
              ),
            ),
          ),
          if (adoptionResult != null) Text('已创建计划：${adoptionResult!.planName}'),
        ],
      );
}

class _WhatIfSection extends StatelessWidget {
  const _WhatIfSection({
    required this.route,
    required this.result,
    required this.onRun,
  });

  final TheaterPathOption route;
  final TheaterWhatIfResult? result;
  final ValueChanged<String> onRun;

  @override
  Widget build(BuildContext context) {
    final candidateStep = route.steps.firstWhere(
      (step) => step.riskLevel != 'low',
      orElse: () => route.steps.first,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('如果……会怎样', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () => onRun(candidateStep.nodeId),
          icon: const Icon(Icons.alt_route),
          label: Text('如果跳过 ${candidateStep.nodeName}'),
        ),
        if (result != null) ...[
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '掌握度 ${result!.predictedMastery.round()}% · 完成率 ${(result!.predictedCompletionRate * 100).round()}%',
                  ),
                  const SizedBox(height: 8),
                  ...result!.consequences.map((item) => Text('• $item')),
                  const SizedBox(height: 8),
                  Text(result!.suggestion),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _DiscussionSection extends StatelessWidget {
  const _DiscussionSection({required this.turns});

  final List<TheaterDiscussionTurn> turns;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('专家圆桌', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...turns.map(
            (turn) => Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ListTile(
                title: Text(turn.displayName),
                subtitle: Text(turn.content),
              ),
            ),
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
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('快照', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Row(
            children: [
              FilledButton.tonal(
                onPressed: isSaving ? null : onSave,
                child: Text(isSaving ? '保存中' : '保存快照'),
              ),
              const SizedBox(width: 12),
              if (snapshot != null)
                Expanded(
                  child: Text(
                    '已保存：${snapshot!.title}',
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
          ),
        ],
      );
}

class _AccuracyCard extends StatelessWidget {
  const _AccuracyCard({required this.summary});

  final TheaterAccuracySummary summary;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('预测校准', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              Text(
                '预测 ${(summary.predictedCompletionRate * 100).round()}% / ${summary.predictedMastery.round()}%，'
                ' 实际 ${(summary.actualCompletionRate * 100).round()}% / ${summary.actualMastery.round()}%',
              ),
              const SizedBox(height: 6),
              Text('准确度 ${(summary.accuracyScore * 100).round()}%'),
            ],
          ),
        ),
      );
}
