import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
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
    final tool = ToolRegistry.tryGetById(toolId);
    if (tool == null) {
      return SparklePageScaffold(
        role: SparklePageRole.content,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline_rounded, size: 48, color: DS.error),
              const SizedBox(height: DS.spacing16),
              Text(
                'Tool not found: $toolId',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: DS.spacing16),
              SparkleButton(
                label: 'Go Back',
                onPressed: () {
                  if (context.canPop()) {
                    context.pop();
                  } else {
                    context.go('/home');
                  }
                },
                icon: const Icon(Icons.arrow_back_rounded),
              ),
            ],
          ),
        ),
      );
    }
    final request = ToolLaunchRequest(
      context: launchContext,
      surface: ToolSurface.page,
      taskId: taskId,
    );

    return SparklePageScaffold(
      role: SparklePageRole.content,
      extendBodyBehindAppBar: true,
      child: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      DS.surfacePrimary,
                      Color.alphaBlend(
                        DS.info.withValues(alpha: 0.03),
                        DS.surfaceCanvas,
                      ),
                    ],
                  ),
                ),
              ),
            ),
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
                        I18nService.instance.isChinese ? '${tool.title}暂不可用' : '${tool.title} is currently unavailable',
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
                    DecoratedBox(
                      decoration: BoxDecoration(
                        color: DS.surfaceOverlay.withValues(alpha: 0.9),
                        borderRadius: DS.borderRadius12,
                        border: Border.all(
                          color: DS.border.withValues(alpha: 0.45),
                        ),
                      ),
                      child: SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        onPressed: () {
                          if (context.canPop()) {
                            context.pop();
                          } else {
                            context.go('/home');
                          }
                        },
                        icon: const Icon(Icons.arrow_back_rounded),
                      ),
                    ),
                    const Spacer(),
                    Tooltip(
                      message: I18nService.instance.isChinese ? '工具库' : 'Tool Library',
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: DS.surfaceOverlay.withValues(alpha: 0.9),
                          borderRadius: DS.borderRadius12,
                          border: Border.all(
                            color: DS.border.withValues(alpha: 0.45),
                          ),
                        ),
                        child: SparkleIconButton(
                          variant: ButtonVariant.ghost,
                          onPressed: () {
                            if (context.mounted) {
                              context.push('/tools/library');
                            }
                          },
                          icon: const Icon(Icons.grid_view_rounded),
                        ),
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
