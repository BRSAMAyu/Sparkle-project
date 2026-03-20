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
      appBar: null,
      child: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            Positioned.fill(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  DS.spacing12,
                  DS.spacing12,
                  DS.spacing12,
                  DS.spacing16,
                ),
                child: tool.embeddedBuilder?.call(request) ??
                    Center(
                      child: Text(
                        '${tool.title}暂不可用',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                    ),
              ),
            ),
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  DS.spacing12,
                  DS.spacing4,
                  DS.spacing12,
                  0,
                ),
                child: Row(
                  children: [
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      onPressed: () => context.pop(),
                      icon: const Icon(Icons.arrow_back_rounded),
                    ),
                    const Spacer(),
                    Tooltip(
                      message: '工具库',
                      child: SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        onPressed: () => context.push('/tools/library'),
                        icon: const Icon(Icons.grid_view_rounded),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
