import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/group_knowledge_base_view.dart';

class GroupFilesScreen extends ConsumerWidget {
  const GroupFilesScreen({required this.groupId, super.key});

  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final group = ref.watch(groupDetailProvider(groupId)).valueOrNull;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(I18nService.instance.isChinese ? '群知识库' : 'Group Knowledge Base'),
      ),
      child: ContentConstraint(
        child: GroupKnowledgeBaseView(
          groupId: groupId,
          currentUserRole: group?.myRole,
        ),
      ),
    );
  }
}
