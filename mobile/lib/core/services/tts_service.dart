import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

/// Service that reads the ttsEnabled accessibility flag and initializes
/// FlutterTts accordingly.  Consumers call [speak] which is a no-op when
/// TTS is disabled.
class TtsService {
  TtsService({required this.enabled}) {
    if (enabled) {
      _tts = FlutterTts();
      unawaited(_tts!.setLanguage('en-US'));
      unawaited(_tts!.setSpeechRate(0.5));
      unawaited(_tts!.setVolume(1.0));
      unawaited(_tts!.setPitch(1.0));
    }
  }

  final bool enabled;
  FlutterTts? _tts;

  Future<void> speak(String text) async {
    if (!enabled || _tts == null) return;
    await _tts!.speak(text);
  }

  Future<void> stop() async {
    await _tts?.stop();
  }

  void dispose() {
    _tts?.stop();
    _tts = null;
  }
}

/// Provider that re-initializes TtsService when ttsEnabled changes.
final ttsServiceProvider = Provider<TtsService>((ref) {
  final accessibility = ref.watch(accessibilitySettingsProvider);
  final enabled = accessibility.isLoaded && accessibility.ttsEnabled;
  return TtsService(enabled: enabled);
});
