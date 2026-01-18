import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/intervention_event_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/widgets/intervention_overlay.dart';

class InterventionOverlayManager {
  InterventionOverlayManager(this._events);

  final InterventionEventService _events;
  OverlayEntry? _entry;
  InterventionOverlayPayload? _payload;

  bool get isShowing => _entry != null;

  void show(InterventionOverlayPayload payload) {
    final overlayState = navigatorKey.currentState?.overlay;
    if (overlayState == null) {
      return;
    }

    if (_entry != null) {
      return;
    }
    _payload = payload;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_entry != null) return;
      _entry = OverlayEntry(
        builder: (context) => Material(
          type: MaterialType.transparency,
          child: InterventionOverlay(
            payload: payload,
            onPrimary: () => _handleAction('primary'),
            onSecondary: () => _handleAction('secondary'),
            onDismiss: () => _handleAction('dismissed'),
          ),
        ),
      );
      overlayState.insert(_entry!);
      _events.record(
        InterventionEvent(
          type: InterventionEventType.overlayShown,
          data: {'title': payload.title},
        ),
      );
    });
  }

  void _handleAction(String action) {
    if (_payload == null) return;
    _events.record(
      InterventionEvent(
        type: InterventionEventType.overlayAction,
        data: {'action': action, 'title': _payload!.title},
      ),
    );
    hide();
  }

  void hide() {
    _entry?.remove();
    _entry = null;
    _payload = null;
  }

  void dispose() {
    hide();
  }
}

final interventionOverlayManagerProvider =
    Provider<InterventionOverlayManager>((ref) {
  final events = ref.watch(interventionEventServiceProvider);
  final manager = InterventionOverlayManager(events);
  ref.onDispose(manager.dispose);
  return manager;
});
