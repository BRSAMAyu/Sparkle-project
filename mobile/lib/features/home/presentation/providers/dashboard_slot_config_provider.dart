import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';

/// Top-level slot identifiers for the customizable dashboard surface.
///
/// These represent the *outer* sections rendered on `dashboard_screen.dart`
/// (Command Center, Task Board, Workspace Cards, etc.). The *inner* cards
/// inside the Workspace Cards slot are managed by `DashboardCardConfigState`
/// in `dashboard_card_config_provider.dart`.
class DashboardSlotIds {
  static const String dailyBriefing = 'daily_briefing';
  static const String metricsRow = 'metrics_row';
  static const String commandCenter = 'command_center';
  static const String understanding = 'understanding';

  static const String returnCaseFile = 'return_case_file';
  static const String goalDetailSnapshot = 'goal_detail_snapshot';
  static const String multiGoalDashboard = 'multi_goal_dashboard';
  static const String taskBoard = 'task_board';
  static const String examSprint = 'exam_sprint';

  static const String dashboardUpdates = 'dashboard_updates';
  static const String growthQuality = 'growth_quality';
  static const String weeklyNarrative = 'weekly_narrative';

  static const String community = 'community';
  static const String achievementProgress = 'achievement_progress';
  static const String learningHeatmap = 'learning_heatmap';

  static const String workspaceCards = 'workspace_cards';

  static const List<String> all = [
    dailyBriefing,
    metricsRow,
    commandCenter,
    returnCaseFile,
    goalDetailSnapshot,
    multiGoalDashboard,
    taskBoard,
    examSprint,
    dashboardUpdates,
    growthQuality,
    weeklyNarrative,
    community,
    achievementProgress,
    learningHeatmap,
    workspaceCards,
  ];

  /// Default ordering — story (status/briefing) first, then plan, then
  /// workspace, finally community/achievements at the bottom.
  static const List<String> defaultOrder = [
    dailyBriefing,
    commandCenter,
    multiGoalDashboard,
    taskBoard,
    workspaceCards,
    metricsRow,
    returnCaseFile,
    goalDetailSnapshot,
    examSprint,
    dashboardUpdates,
    growthQuality,
    weeklyNarrative,
    community,
    achievementProgress,
    learningHeatmap,
  ];

  /// First-run default: every registered slot is visible so existing
  /// users (and brand-new ones) get the full surface. The clutter
  /// problem is solved by *collapsing* low-glance slots out of the box
  /// (see `defaultCollapsed`), not by hiding things they may not
  /// realize exist yet.
  static List<String> get defaultVisible => List<String>.unmodifiable(all);

  /// "Lean view" — opt-in only, surfaced via the edit sheet's
  /// `Lean view` button. Reduces the dashboard to its 5 highest-signal
  /// slots; everything else stays in the user's order list and can be
  /// re-enabled with one tap.
  static const List<String> leanVisible = [
    dailyBriefing,
    commandCenter,
    multiGoalDashboard,
    taskBoard,
    workspaceCards,
  ];

  /// Default-collapsed set: high-volume / low-glanceable slots ship
  /// collapsed (~64px header each) so the first-run scroll feels
  /// intentional but every registered slot is still discoverable.
  /// Together with `defaultVisible = all`, this means new users see
  /// 5 expanded high-signal slots and 11 collapsed headers — far less
  /// noisy than the previous "all expanded" default, but no slot is
  /// silently hidden.
  static const List<String> defaultCollapsed = [
    metricsRow,
    returnCaseFile,
    goalDetailSnapshot,
    examSprint,
    dashboardUpdates,
    growthQuality,
    weeklyNarrative,
    community,
    achievementProgress,
    learningHeatmap,
  ];
}

class DashboardSlotConfigState {
  const DashboardSlotConfigState({
    required this.visibleSlotIds,
    required this.slotOrder,
    required this.collapsedSlotIds,
  });

  factory DashboardSlotConfigState.defaults() => DashboardSlotConfigState(
        visibleSlotIds: DashboardSlotIds.defaultVisible,
        slotOrder: DashboardSlotIds.defaultOrder,
        collapsedSlotIds: DashboardSlotIds.defaultCollapsed,
      );

  final List<String> visibleSlotIds;
  final List<String> slotOrder;
  final List<String> collapsedSlotIds;

  List<String> get visibleOrderedSlots =>
      slotOrder.where(visibleSlotIds.contains).toList(growable: false);

  bool isVisible(String slotId) => visibleSlotIds.contains(slotId);

  bool isCollapsed(String slotId) => collapsedSlotIds.contains(slotId);

  DashboardSlotConfigState copyWith({
    List<String>? visibleSlotIds,
    List<String>? slotOrder,
    List<String>? collapsedSlotIds,
  }) =>
      DashboardSlotConfigState(
        visibleSlotIds: visibleSlotIds ?? this.visibleSlotIds,
        slotOrder: slotOrder ?? this.slotOrder,
        collapsedSlotIds: collapsedSlotIds ?? this.collapsedSlotIds,
      );

  Map<String, dynamic> toJson() => {
        'visibleSlotIds': visibleSlotIds,
        'slotOrder': slotOrder,
        'collapsedSlotIds': collapsedSlotIds,
      };

  static DashboardSlotConfigState? fromJson(Map<String, dynamic> json) {
    try {
      final visibleIds = (json['visibleSlotIds'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .where(DashboardSlotIds.all.contains)
          .toList();
      final savedOrder = (json['slotOrder'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .where(DashboardSlotIds.all.contains)
          .toList();
      final collapsedIds =
          (json['collapsedSlotIds'] as List<dynamic>? ?? const [])
              .map((item) => item.toString())
              .where(DashboardSlotIds.all.contains)
              .toList();

      // Append any slot ids that were added to the registry after this
      // user persisted their config so new features stay discoverable.
      final missingIds = DashboardSlotIds.all
          .where((slotId) => !savedOrder.contains(slotId))
          .toList();
      final slotOrder = [
        ...savedOrder.isEmpty ? DashboardSlotIds.defaultOrder : savedOrder,
        ...missingIds,
      ];

      return DashboardSlotConfigState(
        visibleSlotIds:
            visibleIds.isEmpty ? DashboardSlotIds.defaultVisible : visibleIds,
        slotOrder: slotOrder,
        collapsedSlotIds: collapsedIds,
      );
    } catch (_) {
      return null;
    }
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DashboardSlotConfigState &&
          runtimeType == other.runtimeType &&
          _listEquals(visibleSlotIds, other.visibleSlotIds) &&
          _listEquals(slotOrder, other.slotOrder) &&
          _listEquals(collapsedSlotIds, other.collapsedSlotIds);

  @override
  int get hashCode => Object.hash(
        Object.hashAll(visibleSlotIds),
        Object.hashAll(slotOrder),
        Object.hashAll(collapsedSlotIds),
      );

  static bool _listEquals(List<String> left, List<String> right) {
    if (left.length != right.length) return false;
    for (var index = 0; index < left.length; index++) {
      if (left[index] != right[index]) return false;
    }
    return true;
  }
}

class DashboardSlotConfigNotifier
    extends PersistentStateNotifier<DashboardSlotConfigState> {
  DashboardSlotConfigNotifier(super.ref)
      : super(
          namespace: 'dashboard_slots',
          key: 'config',
          defaultValue: DashboardSlotConfigState.defaults(),
          toJson: (state) => state.toJson(),
          fromJson: DashboardSlotConfigState.fromJson,
        );

  void toggleSlotVisibility(String slotId) {
    if (!DashboardSlotIds.all.contains(slotId)) return;

    final next = [...state.visibleSlotIds];
    if (next.contains(slotId)) {
      // Allow hiding everything — the empty state surface explains how to
      // bring slots back via the edit sheet.
      next.remove(slotId);
    } else {
      next.add(slotId);
    }
    state = state.copyWith(visibleSlotIds: next);
  }

  void toggleSlotCollapsed(String slotId) {
    if (!DashboardSlotIds.all.contains(slotId)) return;

    final next = [...state.collapsedSlotIds];
    if (next.contains(slotId)) {
      next.remove(slotId);
    } else {
      next.add(slotId);
    }
    state = state.copyWith(collapsedSlotIds: next);
  }

  void setSlotCollapsed(String slotId, {required bool collapsed}) {
    if (!DashboardSlotIds.all.contains(slotId)) return;

    final isCurrentlyCollapsed = state.collapsedSlotIds.contains(slotId);
    if (collapsed == isCurrentlyCollapsed) return;

    final next = [...state.collapsedSlotIds];
    if (collapsed) {
      next.add(slotId);
    } else {
      next.remove(slotId);
    }
    state = state.copyWith(collapsedSlotIds: next);
  }

  void reorderSlots(int oldIndex, int newIndex) {
    final updatedOrder = [...state.slotOrder];
    if (oldIndex < newIndex) {
      newIndex -= 1;
    }
    final moved = updatedOrder.removeAt(oldIndex);
    updatedOrder.insert(newIndex, moved);
    state = state.copyWith(slotOrder: updatedOrder);
  }

  void restoreDefaults() {
    state = DashboardSlotConfigState.defaults();
  }

  /// Snap to the curated 5-slot lean view (opt-in only — surfaced via
  /// the edit sheet's "Lean view" button). Preserves slotOrder and
  /// collapsedSlotIds so users can flip back without losing their
  /// arrangement.
  void resetToLeanView() {
    state = state.copyWith(
      visibleSlotIds: DashboardSlotIds.leanVisible,
    );
  }
}

final dashboardSlotConfigProvider = StateNotifierProvider<
    DashboardSlotConfigNotifier, DashboardSlotConfigState>(
  DashboardSlotConfigNotifier.new,
);
