import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/graphite_surfaces.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/insights/presentation/widgets/learning_path_dialog.dart';

class LearningPathScreen extends ConsumerWidget {
  const LearningPathScreen({
    required this.nodeId,
    required this.nodeName,
    super.key,
  });

  final String nodeId;
  final String nodeName;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(
          nodeName.isNotEmpty ? nodeName : context.l10n.learningPathTitle,
          style: TextStyle(color: DS.textPrimary),
        ),
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: IconThemeData(color: DS.textPrimary),
      ),
      body: SafeArea(
        child: LearningPathDialog(
          targetNodeId: nodeId,
          targetNodeName: nodeName,
        ),
      ),
    );
  }
}
