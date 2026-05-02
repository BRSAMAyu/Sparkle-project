import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_hub_view.dart';

class GroupListScreen extends StatelessWidget {
  const GroupListScreen({super.key});

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(I18nService.instance.isChinese ? '社群中心' : 'Community'),
        centerTitle: true,
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.search),
            onPressed: () => context.push('/community/groups/discover'),
          ),
        ],
      ),
      floatingActionButton: SparkleButton.primary(
        label: I18nService.instance.isChinese ? '创建社群' : 'Create Group',
        icon: const Icon(Icons.add),
        onPressed: () => context.push('/community/groups/create'),
      ),
      child: const ContentConstraint(
        child: GroupsHubView(),
      ),
    );
}
