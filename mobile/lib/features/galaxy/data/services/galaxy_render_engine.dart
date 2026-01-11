import 'dart:async';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:sparkle/core/services/performance_service.dart';

class GalaxyRenderSettings {
  const GalaxyRenderSettings({
    required this.renderScale,
    required this.renderFps,
    required this.fieldStrength,
    required this.noiseScale,
    required this.maxBursts,
  });

  final double renderScale;
  final int renderFps;
  final double fieldStrength;
  final double noiseScale;
  final int maxBursts;
}

class GalaxyBurst {
  const GalaxyBurst({
    required this.origin,
    required this.startTime,
    required this.strength,
  });

  final Offset origin; // Normalized (0..1)
  final double startTime; // Seconds
  final double strength;
}

class GalaxyRenderEngine {
  GalaxyRenderEngine({PerformanceService? performanceService})
      : _performanceService = performanceService ?? PerformanceService.instance {
    _applyTier(_performanceService.currentTier.value);
    _tierListener = () => _applyTier(_performanceService.currentTier.value);
    _performanceService.currentTier.addListener(_tierListener);
  }

  final PerformanceService _performanceService;
  late final VoidCallback _tierListener;

  final ValueNotifier<bool> isReady = ValueNotifier(false);
  final ValueNotifier<int> frameTick = ValueNotifier(0);
  final ValueNotifier<GalaxyRenderSettings> settings =
      ValueNotifier(_settingsFromService(PerformanceService.instance));
  final ValueNotifier<String?> fallbackReason = ValueNotifier(null);

  FragmentShader? _fieldShader;
  FragmentShader? _burstShader;
  bool _shaderFailed = false;
  Timer? _frameTimer;
  final List<GalaxyBurst?> _bursts = List<GalaxyBurst?>.filled(4, null);
  int _burstIndex = 0;
  DateTime _startTime = DateTime.now();
  String? _lastLoggedReason;

  Future<void> prewarm() async {
    if (_shaderFailed || isReady.value) return;

    try {
      final fieldProgram =
          await FragmentProgram.fromAsset('shaders/galaxy_field.frag');
      final burstProgram =
          await FragmentProgram.fromAsset('shaders/particle_burst.frag');

      _fieldShader = fieldProgram.fragmentShader();
      _burstShader = burstProgram.fragmentShader();
      _warmUpShaders();
      isReady.value = true;
      fallbackReason.value = null;
      _startTicker();
    } catch (e) {
      _shaderFailed = true;
      isReady.value = false;
      fallbackReason.value = 'prewarm_failed';
      debugPrint('GalaxyRenderEngine prewarm failed: $e');
    }
  }

  void dispose() {
    _frameTimer?.cancel();
    _performanceService.currentTier.removeListener(_tierListener);
    isReady.dispose();
    frameTick.dispose();
    settings.dispose();
    fallbackReason.dispose();
  }

  void addBurst({
    required Offset screenPosition,
    required Size screenSize,
    double strength = 1.0,
  }) {
    if (!isReady.value) return;
    if (screenSize.width <= 0 || screenSize.height <= 0) return;
    final maxBursts = settings.value.maxBursts;
    if (maxBursts <= 0) return;

    final normalized = Offset(
      (screenPosition.dx / screenSize.width).clamp(0.0, 1.0),
      (screenPosition.dy / screenSize.height).clamp(0.0, 1.0),
    );

    final time = _secondsSinceStart();
    final slot = _burstIndex.clamp(0, maxBursts - 1);
    _bursts[slot] = GalaxyBurst(
      origin: normalized,
      startTime: time,
      strength: strength.clamp(0.2, 1.5),
    );
    _burstIndex = (_burstIndex + 1) % maxBursts;
  }

  FragmentShader? get fieldShader => _fieldShader;
  FragmentShader? get burstShader => _burstShader;

  List<GalaxyBurst> get activeBursts =>
      _bursts.whereType<GalaxyBurst>().toList();

  double get timeSeconds => _secondsSinceStart();

  bool get hasShader => !_shaderFailed && isReady.value;
  bool get shaderFailed => _shaderFailed;

  void logFallbackOnce() {
    final reason = fallbackReason.value;
    if (reason == null || reason == _lastLoggedReason) return;
    _lastLoggedReason = reason;
    debugPrint('Galaxy shader fallback: $reason');
  }

  void _startTicker() {
    _frameTimer?.cancel();
    final targetFps = settings.value.renderFps;
    final intervalMs = (1000 / targetFps).round().clamp(12, 1000);
    _frameTimer = Timer.periodic(Duration(milliseconds: intervalMs), (_) {
      frameTick.value++;
    });
  }

  void _applyTier(PerformanceTier tier) {
    settings.value = _settingsFromService(_performanceService);
    final maxBursts = settings.value.maxBursts;
    if (maxBursts < _bursts.length) {
      for (var i = maxBursts; i < _bursts.length; i++) {
        _bursts[i] = null;
      }
      _burstIndex = 0;
    }
    if (isReady.value) {
      _startTicker();
    }
  }

  void _warmUpShaders() {
    final fieldShader = _fieldShader;
    final burstShader = _burstShader;
    if (fieldShader == null || burstShader == null) return;

    final recorder = PictureRecorder();
    final canvas = Canvas(recorder);
    const size = Size(32, 32);

    _setFieldUniforms(fieldShader, size, 0.0);
    canvas.drawRect(const Rect.fromLTWH(0, 0, 32, 32), Paint()..shader = fieldShader);

    _setBurstUniforms(burstShader, size, 0.0);
    canvas.drawRect(const Rect.fromLTWH(0, 0, 32, 32), Paint()..shader = burstShader);

    recorder.endRecording();
  }

  double _secondsSinceStart() {
    final elapsed = DateTime.now().difference(_startTime);
    return elapsed.inMilliseconds / 1000.0;
  }

  void _setFieldUniforms(FragmentShader shader, Size size, double time) {
    shader.setFloat(0, size.width);
    shader.setFloat(1, size.height);
    shader.setFloat(2, time);
    shader.setFloat(3, settings.value.fieldStrength);
    shader.setFloat(4, settings.value.noiseScale);
  }

  void _setBurstUniforms(FragmentShader shader, Size size, double time) {
    shader.setFloat(0, size.width);
    shader.setFloat(1, size.height);
    shader.setFloat(2, time);

    var index = 3;
    for (var i = 0; i < _bursts.length; i++) {
      final burst = _bursts[i];
      if (burst == null) {
        shader.setFloat(index++, 0.0);
        shader.setFloat(index++, 0.0);
        shader.setFloat(index++, 0.0);
        shader.setFloat(index++, 0.0);
        continue;
      }
      shader.setFloat(index++, burst.origin.dx);
      shader.setFloat(index++, burst.origin.dy);
      shader.setFloat(index++, burst.startTime);
      shader.setFloat(index++, burst.strength);
    }
  }

  void applyUniforms({
    required FragmentShader fieldShader,
    required FragmentShader burstShader,
    required Size size,
  }) {
    final time = timeSeconds;
    _setFieldUniforms(fieldShader, size, time);
    _setBurstUniforms(burstShader, size, time);
  }

  static GalaxyRenderSettings _settingsFromService(
    PerformanceService service,
  ) {
    final profile = service.backgroundRenderSettings;
    return GalaxyRenderSettings(
      renderScale: profile.renderScale,
      renderFps: profile.renderFps,
      fieldStrength: profile.fieldStrength,
      noiseScale: profile.noiseScale,
      maxBursts: profile.maxBursts,
    );
  }
}
