import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum InterventionEventType {
  gateDenied,
  overlayShown,
  overlayAction,
}

class InterventionEvent {
  final InterventionEventType type;
  final DateTime timestamp;
  final Map<String, dynamic> data;

  InterventionEvent({
    required this.type,
    DateTime? timestamp,
    Map<String, dynamic>? data,
  })  : timestamp = timestamp ?? DateTime.now(),
        data = data ?? {};
}

class InterventionEventService {
  final List<InterventionEvent> _buffer = [];
  final StreamController<InterventionEvent> _controller =
      StreamController<InterventionEvent>.broadcast();

  Stream<InterventionEvent> get events => _controller.stream;
  List<InterventionEvent> get snapshot => List.unmodifiable(_buffer);

  void record(InterventionEvent event) {
    _buffer.add(event);
    if (_buffer.length > 200) {
      _buffer.removeRange(0, 50);
    }
    debugPrint(
      '[InterventionEvent] ${event.type.name} ${event.data}',
    );
    _controller.add(event);
  }

  void dispose() {
    _controller.close();
  }
}

final interventionEventServiceProvider =
    Provider<InterventionEventService>((ref) {
  final service = InterventionEventService();
  ref.onDispose(service.dispose);
  return service;
});
