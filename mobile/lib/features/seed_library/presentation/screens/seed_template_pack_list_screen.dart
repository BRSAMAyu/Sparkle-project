import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/seed_library/data/models/seed_template_model.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_template_provider.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_template_pack_templates_screen.dart';

class SeedTemplatePackListScreen extends ConsumerStatefulWidget {
  const SeedTemplatePackListScreen({super.key});

  @override
  ConsumerState<SeedTemplatePackListScreen> createState() =>
      _SeedTemplatePackListScreenState();
}

class _SeedTemplatePackListScreenState
    extends ConsumerState<SeedTemplatePackListScreen> {
  String? _scenarioType;

  @override
  Widget build(BuildContext context) {
    final packsAsync = ref.watch(seedTemplatePacksProvider(_scenarioType));

    return Scaffold(
      appBar: AppBar(
        title: const Text('种子模板场景包'),
      ),
      body: ContentConstraint(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                DS.spacing12,
                DS.spacing16,
                DS.spacing8,
              ),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _filterChip(label: '全部', value: null),
                    _filterChip(label: '学习规划', value: 'study_plan'),
                    _filterChip(label: '深度解析', value: 'deep_analysis'),
                    _filterChip(label: '写作', value: 'writing'),
                  ],
                ),
              ),
            ),
            Expanded(
              child: packsAsync.when(
                data: (packs) {
                  if (packs.isEmpty) {
                    return const Center(child: Text('暂无可用模板包'));
                  }
                  return ListView.builder(
                    padding: const EdgeInsets.all(DS.spacing16),
                    itemCount: packs.length,
                    itemBuilder: (context, index) {
                      final pack = packs[index];
                      return _packCard(context, pack);
                    },
                  );
                },
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (error, _) => Center(
                  child: Text(
                    '加载失败: $error',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _packCard(BuildContext context, SeedTemplatePack pack) => Card(
        margin: const EdgeInsets.only(bottom: DS.spacing12),
        child: ListTile(
          contentPadding: const EdgeInsets.all(DS.spacing12),
          title: Text(pack.name),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (pack.description != null && pack.description!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: DS.spacing4),
                  child: Text(
                    pack.description!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing6,
                runSpacing: DS.spacing6,
                children: [
                  Chip(
                    label: Text(_scenarioLabel(pack.scenarioType)),
                    visualDensity: VisualDensity.compact,
                  ),
                  Chip(
                    label: Text(pack.visibility),
                    visualDensity: VisualDensity.compact,
                  ),
                  if (pack.qualityScore != null)
                    Chip(
                      label:
                          Text('质量 ${pack.qualityScore!.toStringAsFixed(1)}'),
                      visualDensity: VisualDensity.compact,
                    ),
                ],
              ),
            ],
          ),
          trailing: const Icon(Icons.chevron_right),
          onTap: () {
            unawaited(
              Navigator.push<void>(
                context,
                MaterialPageRoute(
                  builder: (_) => SeedTemplatePackTemplatesScreen(pack: pack),
                ),
              ),
            );
          },
        ),
      );

  Widget _filterChip({required String label, required String? value}) {
    final selected = _scenarioType == value;
    return Padding(
      padding: const EdgeInsets.only(right: DS.spacing8),
      child: ChoiceChip(
        selected: selected,
        label: Text(label),
        onSelected: (_) => setState(() => _scenarioType = value),
      ),
    );
  }
}

String _scenarioLabel(String scenarioType) {
  switch (scenarioType) {
    case 'study_plan':
      return '学习规划';
    case 'deep_analysis':
      return '深度解析';
    case 'writing':
      return '写作';
    default:
      return scenarioType;
  }
}
