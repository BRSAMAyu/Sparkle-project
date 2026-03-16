import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/home/domain/services/emotion_visual_blending_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

final emotionVisualBlendingServiceProvider =
    Provider<EmotionVisualBlendingService>((ref) {
  return EmotionVisualBlendingService();
});

final emotionVisualBlendProvider =
    Provider.family<VisualBlendParams, CognitiveState>((ref, state) {
  final service = ref.watch(emotionVisualBlendingServiceProvider);
  final weatherType = ref.watch(dashboardProvider).weather.type;
  final base = service.calculateBlendParams(state);
  return service.blendWithWeather(base, _mapWeather(weatherType));
});

WeatherCondition _mapWeather(String type) {
  switch (type) {
    case 'sunny':
      return WeatherCondition.sunny;
    case 'cloudy':
      return WeatherCondition.cloudy;
    case 'rainy':
      return WeatherCondition.rainy;
    case 'meteor':
      return WeatherCondition.meteor;
    default:
      return WeatherCondition.sunny;
  }
}
