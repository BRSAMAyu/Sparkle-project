import 'dart:async';

import 'package:flutter/gestures.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/app_usage_service.dart';

enum PassiveSignalType {
  appForeground,
  appBackground,
  userInteraction,
  idle,
  sessionStart,
  sessionEnd,
}

class PassiveSignal {

  PassiveSignal({
    required this.type,
    DateTime? timestamp,
    Map<String, dynamic>? data,
  })  : timestamp = timestamp ?? DateTime.now(),
        data = data ?? {};
  final PassiveSignalType type;
  final DateTime timestamp;
  final Map<String, dynamic> data;
}

class PassiveSignalService with WidgetsBindingObserver {
  PassiveSignalService(this._appUsageService);

  final AppUsageService _appUsageService;
  final StreamController<PassiveSignal> _controller =
      StreamController<PassiveSignal>.broadcast();

  Timer? _idleTimer;
  DateTime? _sessionStartAt;
  bool _isForeground = true;

  Stream<PassiveSignal> get signals => _controller.stream;

  void start({Duration idleTimeout = const Duration(seconds: 20)}) {
    WidgetsBinding.instance.addObserver(this);
    _isForeground = WidgetsBinding.instance.lifecycleState ==
        AppLifecycleState.resumed;
    _emitSessionStart();
    _resetIdleTimer(idleTimeout);
    GestureBinding.instance.pointerRouter.addGlobalRoute(_handlePointerEvent);
  }

  void stop() {
    WidgetsBinding.instance.removeObserver(this);
    GestureBinding.instance.pointerRouter.removeGlobalRoute(_handlePointerEvent);
    _idleTimer?.cancel();
  }

  void recordUserInteraction() {
    _controller.add(PassiveSignal(type: PassiveSignalType.userInteraction));
  }

  void _handlePointerEvent(PointerEvent event) {
    if (event is PointerDownEvent) {
      recordUserInteraction();
      _resetIdleTimer(const Duration(seconds: 20));
    }
  }

  void _resetIdleTimer(Duration idleTimeout) {
    _idleTimer?.cancel();
    _idleTimer = Timer(idleTimeout, () {
      _controller.add(
        PassiveSignal(
          type: PassiveSignalType.idle,
          data: {'idle_for_s': idleTimeout.inSeconds},
        ),
      );
    });
  }

  void _emitSessionStart() {
    _sessionStartAt ??= DateTime.now();
    _controller.add(PassiveSignal(type: PassiveSignalType.sessionStart));
  }

  void _emitSessionEnd() {
    if (_sessionStartAt == null) return;
    final duration = DateTime.now().difference(_sessionStartAt!);
    _controller.add(
      PassiveSignal(
        type: PassiveSignalType.sessionEnd,
        data: {'duration_ms': duration.inMilliseconds},
      ),
    );
    _sessionStartAt = null;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _isForeground = true;
      _emitSessionStart();
      _controller.add(PassiveSignal(type: PassiveSignalType.appForeground));
      _captureForegroundApp();
      _resetIdleTimer(const Duration(seconds: 20));
    } else if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      _isForeground = false;
      _emitSessionEnd();
      _controller.add(PassiveSignal(type: PassiveSignalType.appBackground));
    }
  }

  Future<void> _captureForegroundApp() async {
    final app = await _appUsageService.getCurrentForegroundApp();
    if (app == null) return;
    final category = await _appUsageService.classifyApp(app);
    _controller.add(
      PassiveSignal(
        type: PassiveSignalType.appForeground,
        data: {
          'app': app,
          'category': category.name,
          'is_foreground': _isForeground,
        },
      ),
    );
  }

  void dispose() {
    stop();
    _controller.close();
  }
}

final passiveSignalServiceProvider = Provider<PassiveSignalService>((ref) {
  final appUsageService = ref.watch(appUsageServiceProvider);
  final service = PassiveSignalService(appUsageService);
  ref.onDispose(service.dispose);
  return service;
});
