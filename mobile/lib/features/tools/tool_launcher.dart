import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/providers/tool_preferences_provider.dart';
import 'package:sparkle/features/tools/tool_registry.dart';

enum ToolOpenPreference {
  auto,
  page,
  sheet,
}

Future<void> launchTool(
  BuildContext context,
  WidgetRef ref,
  String toolId, {
  required ToolLaunchContext launchContext,
  ToolOpenPreference preference = ToolOpenPreference.auto,
  String? taskId,
  ValueChanged<String>? onTextResult,
}) async {
  final tool = ToolRegistry.getById(toolId);
  final request = ToolLaunchRequest(
    context: launchContext,
    surface: preference == ToolOpenPreference.sheet
        ? ToolSurface.sheet
        : ToolSurface.page,
    taskId: taskId,
    onTextResult: onTextResult,
  );

  unawaited(ref.read(toolPreferencesProvider.notifier).recordRecent(toolId));

  final shouldOpenSheet = switch (preference) {
    ToolOpenPreference.sheet =>
      tool.supportsSheet && tool.embeddedBuilder != null,
    ToolOpenPreference.page => false,
    ToolOpenPreference.auto =>
      launchContext == ToolLaunchContext.taskExecution ||
              launchContext == ToolLaunchContext.chatInput
          ? tool.supportsSheet && tool.embeddedBuilder != null
          : false,
  };

  if (shouldOpenSheet) {
    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (context) => FractionallySizedBox(
        heightFactor: 0.92,
        alignment: Alignment.bottomCenter,
        child: SafeArea(
          top: false,
          child: Padding(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom,
            ),
            child: tool.embeddedBuilder!(
              request.copyWith(surface: ToolSurface.sheet),
            ),
          ),
        ),
      ),
    );
    return;
  }

  final route = tool.routeBuilder?.call(request) ??
      Uri(
        path: '/tools/${tool.id}',
        queryParameters: {
          'context': launchContext.name,
          if (taskId != null && taskId.isNotEmpty) 'taskId': taskId,
        },
      ).toString();

  if (context.mounted) {
    unawaited(context.push(route));
  }
}
