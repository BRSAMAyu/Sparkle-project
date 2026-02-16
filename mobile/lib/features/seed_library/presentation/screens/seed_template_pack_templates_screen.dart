import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/seed_library/data/models/seed_template_model.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_template_provider.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_template_detail_screen.dart';

class SeedTemplatePackTemplatesScreen extends ConsumerWidget {
  const SeedTemplatePackTemplatesScreen({
    required this.pack,
    super.key,
  });

  final SeedTemplatePack pack;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final templatesAsync = ref.watch(seedTemplatesByPackProvider(pack.id));
    return Scaffold(
      appBar: AppBar(
        title: Text(pack.name),
      ),
      body: ContentConstraint(
        child: templatesAsync.when(
          data: (templates) {
            if (templates.isEmpty) {
              return const Center(child: Text('该场景包暂无模板'));
            }
            return ListView.builder(
              padding: const EdgeInsets.all(DS.spacing16),
              itemCount: templates.length,
              itemBuilder: (context, index) {
                final template = templates[index];
                return Card(
                  margin: const EdgeInsets.only(bottom: DS.spacing12),
                  child: ListTile(
                    title: Text(template.name),
                    subtitle: Text(
                      '角色: ${template.templateRole}'
                      '${template.forkedFromTemplateId != null ? ' · Fork' : ''}',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      unawaited(
                        Navigator.push<void>(
                          context,
                          MaterialPageRoute(
                            builder: (_) => SeedTemplateDetailScreen(
                              templateId: template.id,
                              scenarioType: pack.scenarioType,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Center(child: Text('加载失败: $error')),
        ),
      ),
    );
  }
}
