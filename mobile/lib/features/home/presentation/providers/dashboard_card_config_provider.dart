import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';

enum DashboardCardLayoutMode { swipe, grid }

class DashboardCardIds {
  static const String insights = 'insights';
  static const String focus = 'focus';
  static const String calendar = 'calendar';
  static const String tools = 'tools';
  static const String openClaw = 'openclaw';
  static const String streak = 'streak';
  static const String nextActions = 'next_actions';
  static const String curiosity = 'curiosity';
  static const String longTermPlan = 'long_term_plan';
  static const String seedLibrary = 'seed_library';

  static const List<String> all = [
    insights,
    focus,
    calendar,
    tools,
    openClaw,
    streak,
    nextActions,
    curiosity,
    longTermPlan,
    seedLibrary,
  ];

  static const List<String> defaultOrder = [
    insights,
    calendar,
    tools,
    openClaw,
    curiosity,
    seedLibrary,
    longTermPlan,
    nextActions,
    focus,
    streak,
  ];

  static const List<String> legacyDefaultOrder = [
    focus,
    calendar,
    tools,
    streak,
    nextActions,
    curiosity,
    longTermPlan,
    seedLibrary,
  ];

  static const List<String> legacyDefaultVisible = [
    calendar,
    tools,
    curiosity,
    seedLibrary,
    longTermPlan,
  ];

  static const List<String> defaultVisible = [
    insights,
    calendar,
    tools,
    curiosity,
    seedLibrary,
    longTermPlan,
    openClaw,
  ];
}

class DashboardCardConfigState {
  const DashboardCardConfigState({
    required this.visibleCardIds,
    required this.cardOrder,
    required this.layoutMode,
  });

  factory DashboardCardConfigState.defaults() => const DashboardCardConfigState(
        visibleCardIds: DashboardCardIds.defaultVisible,
        cardOrder: DashboardCardIds.defaultOrder,
        layoutMode: DashboardCardLayoutMode.swipe,
      );

  final List<String> visibleCardIds;
  final List<String> cardOrder;
  final DashboardCardLayoutMode layoutMode;

  List<String> get visibleOrderedCards =>
      cardOrder.where(visibleCardIds.contains).toList(growable: false);

  DashboardCardConfigState copyWith({
    List<String>? visibleCardIds,
    List<String>? cardOrder,
    DashboardCardLayoutMode? layoutMode,
  }) =>
      DashboardCardConfigState(
        visibleCardIds: visibleCardIds ?? this.visibleCardIds,
        cardOrder: cardOrder ?? this.cardOrder,
        layoutMode: layoutMode ?? this.layoutMode,
      );

  Map<String, dynamic> toJson() => {
        'visibleCardIds': visibleCardIds,
        'cardOrder': cardOrder,
        'layoutMode': layoutMode.name,
      };

  static DashboardCardConfigState? fromJson(Map<String, dynamic> json) {
    try {
      final visibleIds = (json['visibleCardIds'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .where(DashboardCardIds.all.contains)
          .toList();
      final savedOrder = (json['cardOrder'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .where(DashboardCardIds.all.contains)
          .toList();
      final normalizedSavedOrder = savedOrder.isEmpty
          ? DashboardCardIds.defaultOrder
          : _listEquals(savedOrder, DashboardCardIds.legacyDefaultOrder)
              ? DashboardCardIds.defaultOrder
              : savedOrder;
      final missingIds = DashboardCardIds.all
          .where((cardId) => !normalizedSavedOrder.contains(cardId))
          .toList();
      final cardOrder = [...normalizedSavedOrder, ...missingIds];
      final layoutMode = DashboardCardLayoutMode.values.firstWhere(
        (value) => value.name == json['layoutMode'],
        orElse: () => DashboardCardLayoutMode.swipe,
      );

      final normalizedVisibleIds = visibleIds.isEmpty
          ? DashboardCardIds.defaultVisible
          : _listEquals(visibleIds, DashboardCardIds.legacyDefaultVisible)
              ? DashboardCardIds.defaultVisible
              : visibleIds;

      return DashboardCardConfigState(
        visibleCardIds: normalizedVisibleIds,
        cardOrder: cardOrder,
        layoutMode: layoutMode,
      );
    } catch (_) {
      return null;
    }
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DashboardCardConfigState &&
          runtimeType == other.runtimeType &&
          _listEquals(visibleCardIds, other.visibleCardIds) &&
          _listEquals(cardOrder, other.cardOrder) &&
          layoutMode == other.layoutMode;

  @override
  int get hashCode => Object.hash(
        Object.hashAll(visibleCardIds),
        Object.hashAll(cardOrder),
        layoutMode,
      );

  static bool _listEquals(List<String> left, List<String> right) {
    if (left.length != right.length) return false;
    for (var index = 0; index < left.length; index++) {
      if (left[index] != right[index]) return false;
    }
    return true;
  }
}

class DashboardCardConfigNotifier
    extends PersistentStateNotifier<DashboardCardConfigState> {
  DashboardCardConfigNotifier(super.ref)
      : super(
          namespace: 'dashboard_cards',
          key: 'config',
          defaultValue: DashboardCardConfigState.defaults(),
          toJson: (state) => state.toJson(),
          fromJson: DashboardCardConfigState.fromJson,
        );

  void toggleCardVisibility(String cardId) {
    if (!DashboardCardIds.all.contains(cardId)) return;

    final nextVisible = [...state.visibleCardIds];
    if (nextVisible.contains(cardId)) {
      if (nextVisible.length == 1) return;
      nextVisible.remove(cardId);
    } else {
      nextVisible.add(cardId);
    }

    state = state.copyWith(visibleCardIds: nextVisible);
  }

  void setLayoutMode(DashboardCardLayoutMode mode) {
    state = state.copyWith(layoutMode: mode);
  }

  void reorderCards(int oldIndex, int newIndex) {
    final updatedOrder = [...state.cardOrder];
    if (oldIndex < newIndex) {
      newIndex -= 1;
    }
    final movedCard = updatedOrder.removeAt(oldIndex);
    updatedOrder.insert(newIndex, movedCard);
    state = state.copyWith(cardOrder: updatedOrder);
  }

  void restoreDefaults() {
    state = DashboardCardConfigState.defaults();
  }
}

final dashboardCardConfigProvider = StateNotifierProvider<
    DashboardCardConfigNotifier, DashboardCardConfigState>(
  DashboardCardConfigNotifier.new,
);
