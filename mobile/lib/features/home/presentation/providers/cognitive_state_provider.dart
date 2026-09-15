import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/home/domain/services/emotion_visual_blending_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

/// Lightweight cognitive state derived from dashboard signals.
final cognitiveStateProvider = Provider<CognitiveState>((ref) {
  final dashboard = ref.watch(dashboardProvider);
  final status = (dashboard.cognitive.status).toLowerCase();

  if (status.contains('focus')) return CognitiveState.focus;
  if (status.contains('tired') || status.contains('fatigue')) {
    return CognitiveState.tired;
  }
  if (status.contains('excite') || status.contains('energy')) {
    return CognitiveState.excited;
  }
  if (status.contains('joy') || status.contains('happy')) {
    return CognitiveState.joyful;
  }
  if (status.contains('calm')) return CognitiveState.calm;

  if (dashboard.sprint != null) return CognitiveState.focus;
  if (dashboard.flame.todayFocusMinutes >= 90) {
    return CognitiveState.focus;
  }

  final now = TimeOfDay.now();
  final isLate = now.hour >= 22 || now.hour < 6;
  if (isLate) return CognitiveState.tired;

  if (dashboard.flame.brightness >= 0.8) {
    return CognitiveState.excited;
  }

  return CognitiveState.calm;
});
