import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/calendar_event_model.dart';
import 'package:sparkle/data/repositories/calendar_repository.dart';

class CalendarState {
  final List<CalendarEventModel> events;
  final bool isLoading;
  
  CalendarState({this.events = const [], this.isLoading = false});
}

class CalendarNotifier extends StateNotifier<CalendarState> {
  final CalendarRepository _repository;
  
  CalendarNotifier(this._repository) : super(CalendarState()) {
    loadEvents();
  }
  
  Future<void> loadEvents() async {
    state = CalendarState(events: state.events, isLoading: true);
    final events = await _repository.getEvents();
    state = CalendarState(events: events, isLoading: false);
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
  
  List<CalendarEventModel> getEventsForDay(DateTime day) {
    return state.events.where((event) {
      return isSameDay(event.startTime, day);
    }).toList();
  }
  
  bool isSameDay(DateTime? a, DateTime? b) {
    if (a == null || b == null) return false;
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }
}

final calendarProvider = StateNotifierProvider<CalendarNotifier, CalendarState>((ref) {
  final repository = ref.watch(calendarRepositoryProvider);
  return CalendarNotifier(repository);
});
