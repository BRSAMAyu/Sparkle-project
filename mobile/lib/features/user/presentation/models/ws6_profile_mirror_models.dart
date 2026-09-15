import 'package:flutter/material.dart';

enum Ws6ProfileVisibility {
  visible,
  mediated,
  hidden,
}

class Ws6MirrorDimensionModel {
  const Ws6MirrorDimensionModel({
    required this.key,
    required this.label,
    required this.value,
    required this.subtitle,
    required this.sourceLabel,
    required this.visibility,
    required this.canEditDirectly,
    required this.canRevert,
  });

  final String key;
  final String label;
  final double value;
  final String subtitle;
  final String sourceLabel;
  final Ws6ProfileVisibility visibility;
  final bool canEditDirectly;
  final bool canRevert;
}

class Ws6MirrorBarModel {
  const Ws6MirrorBarModel({
    required this.enabled,
    required this.presenceLabel,
    required this.presenceValue,
    required this.dimensions,
    required this.bindingNotes,
  });

  factory Ws6MirrorBarModel.inert({
    String presenceLabel = 'ambient',
    List<String> bindingNotes = const <String>[],
  }) =>
      Ws6MirrorBarModel(
        enabled: false,
        presenceLabel: presenceLabel,
        presenceValue: 0.0,
        dimensions: const <Ws6MirrorDimensionModel>[],
        bindingNotes: List<String>.unmodifiable(bindingNotes),
      );

  final bool enabled;
  final String presenceLabel;
  final double presenceValue;
  final List<Ws6MirrorDimensionModel> dimensions;
  final List<String> bindingNotes;
}

class Ws6TransparentProfileItemModel {
  const Ws6TransparentProfileItemModel({
    required this.key,
    required this.label,
    required this.summary,
    required this.projectionPolicy,
    required this.visibility,
    required this.canEditDirectly,
    required this.canRevert,
    required this.evidenceSummary,
    this.supportsExamModeOnly = false,
  });

  final String key;
  final String label;
  final String summary;
  final String projectionPolicy;
  final Ws6ProfileVisibility visibility;
  final bool canEditDirectly;
  final bool canRevert;
  final String evidenceSummary;
  final bool supportsExamModeOnly;
}

class Ws6ProfileRevertActionModel {
  const Ws6ProfileRevertActionModel({
    required this.key,
    required this.label,
    required this.currentSummary,
    required this.suggestedSummary,
    required this.reason,
    required this.projectionPolicy,
    required this.requiresDialogue,
  });

  final String key;
  final String label;
  final String currentSummary;
  final String suggestedSummary;
  final String reason;
  final String projectionPolicy;
  final bool requiresDialogue;
}

class Ws6ProfileCorrectionHistoryItemModel {
  const Ws6ProfileCorrectionHistoryItemModel({
    required this.id,
    required this.targetId,
    required this.fieldName,
    required this.action,
    required this.summary,
    required this.createdAtLabel,
    required this.canUndo,
  });

  final String id;
  final String targetId;
  final String fieldName;
  final String action;
  final String summary;
  final String createdAtLabel;
  final bool canUndo;
}

class Ws6TransparentProfileViewModel {
  const Ws6TransparentProfileViewModel({
    required this.enabled,
    required this.summary,
    required this.mirrorBar,
    required this.visibleItems,
    required this.mediatedItems,
    required this.hiddenItemCount,
    required this.revertActions,
    required this.recentCorrections,
    required this.calibrationPosture,
    required this.unknowns,
    required this.bindingNotes,
  });

  factory Ws6TransparentProfileViewModel.inert({
    String summary = 'WS6 profile surface is gated off.',
    List<String> bindingNotes = const <String>[],
  }) =>
      Ws6TransparentProfileViewModel(
        enabled: false,
        summary: summary,
        mirrorBar: Ws6MirrorBarModel.inert(bindingNotes: bindingNotes),
        visibleItems: const <Ws6TransparentProfileItemModel>[],
        mediatedItems: const <Ws6TransparentProfileItemModel>[],
        hiddenItemCount: 0,
        revertActions: const <Ws6ProfileRevertActionModel>[],
        recentCorrections: const <Ws6ProfileCorrectionHistoryItemModel>[],
        calibrationPosture: '',
        unknowns: const <String>[],
        bindingNotes: List<String>.unmodifiable(bindingNotes),
      );

  final bool enabled;
  final String summary;
  final Ws6MirrorBarModel mirrorBar;
  final List<Ws6TransparentProfileItemModel> visibleItems;
  final List<Ws6TransparentProfileItemModel> mediatedItems;
  final int hiddenItemCount;
  final List<Ws6ProfileRevertActionModel> revertActions;
  final List<Ws6ProfileCorrectionHistoryItemModel> recentCorrections;
  final String calibrationPosture;
  final List<String> unknowns;
  final List<String> bindingNotes;

  Ws6TransparentProfileViewModel copyWithBindingNotes(List<String> notes) =>
      Ws6TransparentProfileViewModel(
        enabled: enabled,
        summary: summary,
        mirrorBar: mirrorBar,
        visibleItems: visibleItems,
        mediatedItems: mediatedItems,
        hiddenItemCount: hiddenItemCount,
        revertActions: revertActions,
        recentCorrections: recentCorrections,
        calibrationPosture: calibrationPosture,
        unknowns: unknowns,
        bindingNotes: List<String>.unmodifiable(notes),
      );
}

Color ws6VisibilityColor(Ws6ProfileVisibility visibility) {
  switch (visibility) {
    case Ws6ProfileVisibility.visible:
      return const Color(0xFF78D1C0);
    case Ws6ProfileVisibility.mediated:
      return const Color(0xFFF2B45D);
    case Ws6ProfileVisibility.hidden:
      return const Color(0xFF8D8FA6);
  }
}
