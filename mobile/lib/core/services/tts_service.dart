import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:sparkle/core/services/audio_focus_controller.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

/// Service that reads the ttsEnabled accessibility flag and initializes
/// FlutterTts accordingly.  Consumers call [speak] which is a no-op when
/// TTS is disabled.
///
/// V4-S02：TTS 播放接入音频焦点状态机——speak 前登记 TTS 抢占
/// （USER_PLAYING → DUCKED_BY_TTS：环境床压低不消除，「TTS可duck/暂停环境
/// 床」）；stop/完成/出错后解除。本服务不持有环境床，只消费焦点裁决面。
class TtsService {
  TtsService({required this.enabled}) {
    if (enabled) {
      _tts = FlutterTts();
      unawaited(_tts!.setLanguage('en-US'));
      unawaited(_tts!.setSpeechRate(0.5));
      unawaited(_tts!.setVolume(1.0));
      unawaited(_tts!.setPitch(1.0));
      // flutter_tts 4.x 的 handler 注册返回 void（非 Future）。
      _tts!.setCompletionHandler(_finishTtsTurn);
      _tts!.setErrorHandler((_) => _finishTtsTurn);
      _tts!.setCancelHandler(_finishTtsTurn);
    }
  }

  final bool enabled;
  FlutterTts? _tts;
  bool _ttsTurnActive = false;

  Future<void> speak(String text) async {
    if (!enabled || _tts == null) return;
    AudioFocusController.instance.beginTts();
    _ttsTurnActive = true;
    try {
      await _tts!.speak(text);
    } catch (_) {
      _finishTtsTurn();
    }
  }

  Future<void> stop() async {
    await _tts?.stop();
    _finishTtsTurn();
  }

  /// 一次 TTS 说话回合结束（完成/取消/出错/手动停止）→ 解除焦点抢占。
  void _finishTtsTurn() {
    if (!_ttsTurnActive) return;
    _ttsTurnActive = false;
    AudioFocusController.instance.endTts();
  }

  void dispose() {
    _finishTtsTurn();
    unawaited(_tts?.stop());
    _tts = null;
  }
}

/// Provider that re-initializes TtsService when ttsEnabled changes.
final ttsServiceProvider = Provider<TtsService>((ref) {
  final accessibility = ref.watch(accessibilitySettingsProvider);
  final enabled = accessibility.isLoaded && accessibility.ttsEnabled;
  return TtsService(enabled: enabled);
});
