import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';

class CalendarState {
  CalendarState({this.events = const [], this.isLoading = false});
  final List<CalendarEventModel> events;
  final bool isLoading;
}

class CalendarNotifier extends StateNotifier<CalendarState> {
  CalendarNotifier(this._repository) : super(CalendarState()) {
    loadEvents();
  }
  final CalendarRepository _repository;

  Future<void> loadEvents() async {
    state = CalendarState(events: state.events, isLoading: true);
    final events = await _repository.getEvents();
    state = CalendarState(events: events);
  }

  Future<void> addEvent(CalendarEventModel event) async {
    await _repository.addEvent(event);
    loadEvents();
  }

  Future<void> updateEvent(CalendarEventModel event) async {
    await _repository.updateEvent(event);
    loadEvents();
  }

  Future<void> deleteEvent(String id) async {
    await _repository.deleteEvent(id);
    loadEvents();
  }

  List<CalendarEventModel> getEventsForDay(DateTime day) =>
      state.events.where((event) => isSameDay(event.startTime, day)).toList();

  bool isSameDay(DateTime? a, DateTime? b) {
    if (a == null || b == null) return false;
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }
}

final calendarProvider =
    StateNotifierProvider<CalendarNotifier, CalendarState>((ref) {
  final repository = ref.watch(calendarRepositoryProvider);
  return CalendarNotifier(repository);
});
