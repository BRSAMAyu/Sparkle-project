import 'package:flutter/material.dart';
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
      appBar: AppBar(
        title: Text(tool.title),
      ),
      child: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) => SingleChildScrollView(
            padding: const EdgeInsets.all(DS.spacing16),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minHeight: constraints.maxHeight - DS.spacing32,
              ),
              child: tool.embeddedBuilder?.call(request) ??
                  Center(
                    child: Text(
                      '工具暂不可用',
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
