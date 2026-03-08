import 'package:flutter/material.dart';

enum ToolCategory {
  input,
  study,
  efficiency,
  cognition,
}

enum ToolLaunchContext {
  home,
  taskExecution,
  chatInput,
  toolLibrary,
}

enum ToolSurface {
  page,
  sheet,
}

class ToolLaunchRequest {
  const ToolLaunchRequest({
    required this.context,
    required this.surface,
    this.taskId,
    this.onTextResult,
  });

  final ToolLaunchContext context;
  final ToolSurface surface;
  final String? taskId;
  final ValueChanged<String>? onTextResult;

  ToolLaunchRequest copyWith({
    ToolLaunchContext? context,
    ToolSurface? surface,
    String? taskId,
    ValueChanged<String>? onTextResult,
  }) =>
      ToolLaunchRequest(
        context: context ?? this.context,
        surface: surface ?? this.surface,
        taskId: taskId ?? this.taskId,
        onTextResult: onTextResult ?? this.onTextResult,
      );
}

typedef EmbeddedToolBuilder = Widget Function(ToolLaunchRequest request);
typedef ToolRouteBuilder = String Function(ToolLaunchRequest request);

class ToolDefinition {
  const ToolDefinition({
    required this.id,
    required this.title,
    required this.icon,
    required this.category,
    required this.defaultOrder,
    required this.supportedContexts,
    this.description,
    this.searchTerms = const <String>[],
    this.canPin = true,
    this.supportsStandalone = true,
    this.supportsSheet = false,
    this.showInTaskQuickPanel = false,
    this.routeBuilder,
    this.embeddedBuilder,
  });

  final String id;
  final String title;
  final String? description;
  final IconData icon;
  final ToolCategory category;
  final int defaultOrder;
  final List<String> searchTerms;
  final bool canPin;
  final bool supportsStandalone;
  final bool supportsSheet;
  final bool showInTaskQuickPanel;
  final Set<ToolLaunchContext> supportedContexts;
  final ToolRouteBuilder? routeBuilder;
  final EmbeddedToolBuilder? embeddedBuilder;

  bool get isRouteBased => routeBuilder != null && embeddedBuilder == null;

  bool supportsContext(ToolLaunchContext context) =>
      supportedContexts.contains(context);
}
