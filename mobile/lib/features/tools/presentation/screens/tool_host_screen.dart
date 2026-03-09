import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/tool_registry.dart';

class ToolHostScreen extends StatelessWidget {
  const ToolHostScreen({
    required this.toolId,
    required this.launchContext,
    super.key,
    this.taskId,
  });

  final String toolId;
  final ToolLaunchContext launchContext;
  final String? taskId;

  @override
  Widget build(BuildContext context) {
    final tool = ToolRegistry.getById(toolId);
    final request = ToolLaunchRequest(
      context: launchContext,
      surface: ToolSurface.page,
      taskId: taskId,
    );

    return SparklePageScaffold(
      role: SparklePageRole.content,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        title: const SizedBox.shrink(),
        actions: [
          IconButton(
            tooltip: '工具库',
            onPressed: () => context.push('/tools/library'),
            icon: const Icon(Icons.grid_view_rounded),
          ),
        ],
      ),
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) => Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              DS.spacing8,
              DS.spacing16,
              DS.spacing24,
            ),
            child: SizedBox(
              height: constraints.maxHeight,
              child: tool.embeddedBuilder?.call(request) ??
                  Center(
                    child: Text(
                      '${tool.title}暂不可用',
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ),
            ),
          ),
        ),
      ),
    );
  }
}
