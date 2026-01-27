import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Calendar preview panel state
class CalendarPreviewState {
  const CalendarPreviewState({
    this.selectedDate,
    this.isExpanded = false,
  });

  final DateTime? selectedDate;
  final bool isExpanded;

  CalendarPreviewState copyWith({
    DateTime? selectedDate,
    bool? isExpanded,
  }) =>
      CalendarPreviewState(
        selectedDate: selectedDate ?? this.selectedDate,
        isExpanded: isExpanded ?? this.isExpanded,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CalendarPreviewState &&
          runtimeType == other.runtimeType &&
          selectedDate == other.selectedDate &&
          isExpanded == other.isExpanded;

  @override
  int get hashCode => selectedDate.hashCode ^ isExpanded.hashCode;
}

/// Calendar preview panel notifier
class CalendarPreviewNotifier extends StateNotifier<CalendarPreviewState> {
  CalendarPreviewNotifier() : super(const CalendarPreviewState());

  /// Select a date and expand the panel
  /// If the same date is selected again, toggle the expanded state
  void selectDate(DateTime date) {
    final normalizedDate = DateTime(date.year, date.month, date.day);

    if (state.selectedDate != null &&
        _isSameDay(state.selectedDate!, normalizedDate)) {
      // Same date selected - toggle expanded state
      state = state.copyWith(isExpanded: !state.isExpanded);
    } else {
      // Different date - select and expand
      state = CalendarPreviewState(
        selectedDate: normalizedDate,
        isExpanded: true,
      );
    }
  }

  /// Toggle the expanded state
  void toggleExpanded() {
    state = state.copyWith(isExpanded: !state.isExpanded);
  }

  /// Collapse the panel
  void collapse() {
    state = const CalendarPreviewState();
  }

  /// Check if two dates are the same day (ignoring time)
  bool _isSameDay(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;
}

/// Provider for calendar preview panel state
final calendarPreviewProvider =
    StateNotifierProvider<CalendarPreviewNotifier, CalendarPreviewState>((ref) => CalendarPreviewNotifier());
