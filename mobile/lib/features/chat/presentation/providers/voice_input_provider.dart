import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/features/chat/data/services/audio_recording_service.dart';

/// 语音输入状态
enum VoiceInputState {
  idle,        // 空闲状态
  recording,   // 正在录音
  processing,  // 正在处理
  completed,   // 完成
  error,       // 错误
}

/// 语音输入Provider
class VoiceInputNotifier extends StateNotifier<VoiceInputState> {
  final AudioRecordingService _recordingService;
  final Logger _logger;
  Timer? _durationTimer;
  int _recordingDuration = 0;
  String _currentTranscription = "";
  String _errorMessage = "";

  VoiceInputNotifier()
      : _recordingService = AudioRecordingService(),
        _logger = Logger(),
        super(VoiceInputState.idle);

  /// 检查麦克风权限
  Future<bool> checkPermissions() async {
    final status = await Permission.microphone.request();
    if (status.isPermanentlyDenied) {
      return false;
    }
    return status.isGranted;
  }

  /// 开始录音
  Future<void> startRecording({
    required String wsUrl,
    required String authToken,
    required void Function(String text) onTranscription,
    required void Function(String error) onError,
    Duration? maxDuration,
  }) async {
    if (state == VoiceInputState.recording) {
      _logger.w("Already recording");
      return;
    }

    // 检查权限
    final hasPermission = await checkPermissions();
    if (!hasPermission) {
      _errorMessage = "没有麦克风权限";
      state = VoiceInputState.error;
      onError(_errorMessage);
      return;
    }

    // 重置状态
    _recordingDuration = 0;
    _currentTranscription = "";
    _errorMessage = "";

    state = VoiceInputState.recording;

    // 启动时长计时器
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      _recordingDuration++;
      if (maxDuration != null && _recordingDuration >= maxDuration.inSeconds) {
        stopRecording();
      }
    });

    try {
      await _recordingService.startRecording(
        wsUrl: wsUrl,
        authToken: authToken,
        onTranscription: (text) {
          _currentTranscription = text;
          state = VoiceInputState.processing;
          onTranscription(text);
        },
        onError: (error) {
          _errorMessage = error;
          state = VoiceInputState.error;
          onError(error);
        },
        onCompleted: () {
          state = VoiceInputState.completed;
        },
        maxDuration: maxDuration,
      );
    } catch (e) {
      _errorMessage = "启动录音失败: $e";
      state = VoiceInputState.error;
      onError(_errorMessage);
    }
  }

  /// 停止录音
  Future<void> stopRecording() async {
    if (state != VoiceInputState.recording) {
      return;
    }

    await _recordingService.stopRecording();
    _durationTimer?.cancel();
    _durationTimer = null;

    if (_currentTranscription.isNotEmpty) {
      state = VoiceInputState.completed;
    } else {
      state = VoiceInputState.idle;
    }
  }

  /// 取消录音
  Future<void> cancelRecording() async {
    await _recordingService.cancelRecording();
    _durationTimer?.cancel();
    _durationTimer = null;
    _currentTranscription = "";
    state = VoiceInputState.idle;
  }

  /// 重置状态
  void reset() {
    _durationTimer?.cancel();
    _durationTimer = null;
    _recordingDuration = 0;
    _currentTranscription = "";
    _errorMessage = "";
    state = VoiceInputState.idle;
  }

  /// 获取录音时长
  int get recordingDuration => _recordingDuration;

  /// 获取当前转写文本
  String get currentTranscription => _currentTranscription;

  /// 获取错误消息
  String get errorMessage => _errorMessage;

  /// 是否正在录音
  bool get isRecording => state == VoiceInputState.recording;

  /// 是否正在处理
  bool get isProcessing => state == VoiceInputState.processing;

  /// 是否有错误
  bool get hasError => state == VoiceInputState.error;

  /// 清理资源
  Future<void> dispose() async {
    _durationTimer?.cancel();
    await _recordingService.dispose();
    super.dispose();
  }
}

/// 语音输入Provider
final voiceInputProvider =
    StateNotifierProvider<VoiceInputNotifier, VoiceInputState>((ref) {
  return VoiceInputNotifier();
});
