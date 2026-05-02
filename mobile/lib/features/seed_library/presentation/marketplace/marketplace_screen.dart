import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_models.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_provider.dart';

class MarketplaceScreen extends ConsumerWidget {
  const MarketplaceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(marketplaceProvider);
    final notifier = ref.read(marketplaceProvider.notifier);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: const Text('Skill Marketplace'),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.refresh_rounded),
            onPressed: notifier.refresh,
          ),
        ],
      ),
      child: ContentConstraint(
        child: DefaultTabController(
          length: 2,
          child: Column(
            children: [
              const TabBar(
                tabs: [
                  Tab(icon: Icon(Icons.psychology_alt_rounded), text: 'Skills'),
                  Tab(icon: Icon(Icons.inventory_2_outlined), text: 'Packs'),
                ],
              ),
              if (state.isLoading &&
                  state.skills.isEmpty &&
                  state.packs.isEmpty)
                Expanded(
                  child: Center(
                    child: LoadingIndicator.circular(showText: true),
                  ),
                )
              else if (state.error != null)
                Expanded(
                  child: CustomErrorWidget.page(
                    context: context,
                    message: state.error!,
                    onRetry: notifier.refresh,
                  ),
                )
              else
                Expanded(
                  child: TabBarView(
                    children: [
                      _SkillList(skills: state.skills),
                      _PackList(packs: state.packs),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SkillList extends ConsumerWidget {
  const _SkillList({required this.skills});

  final List<MarketplaceSkillCard> skills;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (skills.isEmpty) {
      return const Center(child: Text('No active marketplace skills yet.'));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(DS.spacing16),
      itemBuilder: (context, index) => _SkillTile(skill: skills[index]),
      separatorBuilder: (_, __) => const SizedBox(height: DS.spacing12),
      itemCount: skills.length,
    );
  }
}

class _PackList extends StatelessWidget {
  const _PackList({required this.packs});

  final List<MarketplacePackCard> packs;

  @override
  Widget build(BuildContext context) {
    if (packs.isEmpty) {
      return const Center(child: Text('No active domain packs yet.'));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(DS.spacing16),
      itemBuilder: (context, index) => _PackTile(pack: packs[index]),
      separatorBuilder: (_, __) => const SizedBox(height: DS.spacing12),
      itemCount: packs.length,
    );
  }
}

class _SkillTile extends ConsumerWidget {
  const _SkillTile({required this.skill});

  final MarketplaceSkillCard skill;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(DS.radius12),
          onTap: () => unawaited(_showSkillPreview(context, ref)),
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.psychology_alt_rounded),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Text(
                        skill.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    _ScorePill(score: skill.qualityScore),
                  ],
                ),
                if (skill.description.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing8),
                  Text(
                    skill.description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
                const SizedBox(height: DS.spacing12),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    _MetaChip(
                      icon: Icons.verified_outlined,
                      label: 'G${skill.evidenceGrade}',
                    ),
                    _MetaChip(
                      icon: Icons.trending_up_rounded,
                      label: '${(skill.successRate * 100).round()}%',
                    ),
                    if (skill.domain.isNotEmpty)
                      _MetaChip(
                        icon: Icons.category_outlined,
                        label: skill.domain,
                      ),
                    _MetaChip(
                      icon: Icons.people_outline,
                      label: '${skill.adoptionCount}',
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );

  Future<void> _showSkillPreview(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(marketplaceProvider.notifier);
    final preview = await notifier.previewSkill(skill.skillId);
    if (!context.mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => _PreviewDialog(
        title: skill.name,
        preview: preview,
        primaryLabel: 'Adopt skill',
      ),
    );
    if (confirmed != true) return;
    await notifier.adoptSkill(skill.skillId, preview: preview);
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${skill.name} adopted')),
    );
  }
}

class _PackTile extends ConsumerWidget {
  const _PackTile({required this.pack});

  final MarketplacePackCard pack;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(DS.radius12),
          onTap: () => unawaited(_showPackPreview(context, ref)),
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.inventory_2_outlined),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Text(
                        pack.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    _ScorePill(score: pack.qualityScore),
                  ],
                ),
                if (pack.description.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing8),
                  Text(
                    pack.description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                const SizedBox(height: DS.spacing12),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    if (pack.domain.isNotEmpty)
                      _MetaChip(
                        icon: Icons.category_outlined,
                        label: pack.domain,
                      ),
                    _MetaChip(
                      icon: Icons.psychology_alt_outlined,
                      label: '${pack.skillIds.length}',
                    ),
                    _MetaChip(
                      icon: Icons.people_outline,
                      label: '${pack.adoptionCount}',
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );

  Future<void> _showPackPreview(BuildContext context, WidgetRef ref) async {
    final notifier = ref.read(marketplaceProvider.notifier);
    final preview = await notifier.previewPack(pack.packId);
    if (!context.mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => _PreviewDialog(
        title: pack.name,
        preview: preview,
        primaryLabel: 'Adopt pack',
      ),
    );
    if (confirmed != true) return;
    await notifier.adoptPack(pack.packId, preview: preview);
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${pack.name} adopted')),
    );
  }
}

class _PreviewDialog extends StatelessWidget {
  const _PreviewDialog({
    required this.title,
    required this.preview,
    required this.primaryLabel,
  });

  final String title;
  final MarketplacePreview preview;
  final String primaryLabel;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(title, maxLines: 2, overflow: TextOverflow.ellipsis),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: preview.willAffect
                    .map(
                      (item) => _MetaChip(
                        icon: Icons.bolt_outlined,
                        label: item,
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: DS.spacing16),
              Row(
                children: [
                  const Icon(Icons.verified_user_outlined, size: DS.iconSizeSm),
                  const SizedBox(width: DS.spacing8),
                  Text('Quality ${preview.qualityScore.toStringAsFixed(2)}'),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              if (preview.payload['expected_outcome'] != null)
                Text(preview.payload['expected_outcome'].toString()),
              if (preview.payload['trace_policy'] != null) ...[
                const SizedBox(height: DS.spacing12),
                Text(
                  preview.payload['trace_policy'].toString(),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).pop(true),
            icon: const Icon(Icons.check_circle_outline),
            label: Text(primaryLabel),
          ),
        ],
      );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Chip(
        avatar: Icon(icon, size: DS.iconSizeXs),
        label: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis),
        visualDensity: VisualDensity.compact,
      );
}

class _ScorePill extends StatelessWidget {
  const _ScorePill({required this.score});

  final double score;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.success.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(DS.radius8),
        ),
        child: Text(
          score.toStringAsFixed(2),
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: DS.success,
                fontWeight: DS.fontWeightBold,
              ),
        ),
      );
}
