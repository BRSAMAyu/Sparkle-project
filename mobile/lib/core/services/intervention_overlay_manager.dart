import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/models/intervention.dart';
import 'package:sparkle/core/services/intervention_event_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/widgets/intervention_overlay.dart';

class InterventionOverlayManager {
  InterventionOverlayManager(this._events);

  final InterventionEventService _events;
  OverlayEntry? _entry;
  InterventionPushMessage? _payload;
  ValueChanged<String>? _actionHandler;

  bool get isShowing => _entry != null;

  void show(InterventionPushMessage payload, {ValueChanged<String>? onAction}) {
    if (payload.level == InterventionLevel.silent) {
      return;
    }
    final overlayState = navigatorKey.currentState?.overlay;
    if (overlayState == null) {
      return;
    }

    if (_entry != null) {
      return;
    }
    _payload = payload;
    _actionHandler = onAction;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_entry != null) return;
      _entry = OverlayEntry(
        builder: (context) => Material(
          type: MaterialType.transparency,
          child: InterventionOverlay(
            intervention: payload,
            onAction: _handleAction,
            onDismiss: () => _handleAction('dismissed'),
          ),
        ),
      );
      overlayState.insert(_entry!);
      _events.record(
        InterventionEvent(
          type: InterventionEventType.overlayShown,
          data: {'intervention_id': payload.interventionId},
        ),
      );
    });
  }

  void _handleAction(String action) {
    if (_payload == null) return;
    _events.record(
      InterventionEvent(
        type: InterventionEventType.overlayAction,
        data: {'action': action, 'intervention_id': _payload!.interventionId},
      ),
    );
    _actionHandler?.call(action);
    hide();
  }

  void hide() {
    _entry?.remove();
    _entry = null;
    _payload = null;
    _actionHandler = null;
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
