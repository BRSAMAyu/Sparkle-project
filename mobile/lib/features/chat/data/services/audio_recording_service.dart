import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'package:record/record.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// 音频录制服务
/// 负责录制音频并实时流式传输到服务器
class AudioRecordingService {
  final AudioRecorder _recorder = AudioRecorder();
  final Logger _logger = Logger();
  WebSocketChannel? _webSocket;
  StreamSubscription<Uint8List>? _audioStreamSubscription;
  bool _isRecording = false;
  bool _isStopping = false;
  bool _stopSignalSent = false;
  Timer? _durationTimer;
  int _recordingDuration = 0;
  Completer<void>? _recordingCompleter;
  Completer<void>? _serverCompletionCompleter;

  /// 开始录制音频并连接到WebSocket
  Future<void> startRecording({
    required String wsUrl,
    required String authToken,
    required void Function(String text) onTranscription,
    required void Function(String error) onError,
    required void Function() onCompleted,
    Duration? maxDuration,
  }) async {
    if (_isRecording) {
      _logger.w('Already recording');
      return;
    }

    _isRecording = true;
    _isStopping = false;
    _stopSignalSent = false;
    _recordingDuration = 0;
    _recordingCompleter = Completer<void>();
    _serverCompletionCompleter = Completer<void>();

    try {
      // 1. 连接WebSocket
      _logger.d('Connecting to WebSocket: $wsUrl');

      // Prepare WebSocket with token as query param
      // Flutter's IOWebSocketChannel doesn't support custom headers,
      // so we pass the token via query parameter
      final uri = Uri.parse('$wsUrl?token=$authToken');
      final channel = IOWebSocketChannel.connect(
        uri,
      );

      _webSocket = channel;

      // 2. 开始监听WebSocket消息
      _webSocket!.stream.listen(
        (message) {
          _handleWebSocketMessage(message, onTranscription, onError, onCompleted);
        },
        onError: (Object error) {
          _logger.e('WebSocket error: $error');
          onError(
            I18nService.instance.l10n.chatAudioWsConnectFailed(
              error.toString(),
            ),
          );
          unawaited(stopRecording());
        },
        onDone: () {
          _logger.d('WebSocket closed');
          _completeServerCompletion();
          unawaited(_cleanupSession());
        },
        cancelOnError: true,
      );

      // 3. 开始录制音频流 - 使用 startStream 获取原始 PCM 数据
      const config = RecordConfig(
        encoder: AudioEncoder.pcm16bits, // 获取原始 PCM 数据
        sampleRate: 16000,               // 16kHz，服务端会封装为智谱 ASR 兼容 WAV
        numChannels: 1,                   // 单声道
      );

      final audioStream = await _recorder.startStream(config);

      // 4. 监听音频数据流并实时发送
      _audioStreamSubscription = audioStream.listen(
        (audioData) {
          if (_webSocket != null && _isRecording) {
            _sendAudioData(audioData);
          }
        },
        onError: (Object error) {
          _logger.e('Audio stream error: $error');
          onError(
            I18nService.instance.l10n.chatAudioRecordFailed(
              error.toString(),
            ),
          );
          unawaited(stopRecording());
        },
        onDone: () {
          _logger.d('Audio stream ended');
          // Send stop signal to server
          _sendStopSignal();
          onCompleted();
          unawaited(stopRecording());
        },
        cancelOnError: true,
      );

      // 5. 启动时长计时器
      if (maxDuration != null) {
        _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
          _recordingDuration++;
          if (_recordingDuration >= maxDuration.inSeconds) {
            _logger.d('Max duration reached: $maxDuration');
            unawaited(stopRecording());
          }
        });
      }

      _logger.d('Recording started successfully');
    } catch (e) {
        _logger.e('Failed to start recording: $e');
      onError(I18nService.instance.l10n.chatAudioStartFailed(e.toString()));
      await _cleanupSession();
    }
  }

  /// 处理WebSocket消息
  void _handleWebSocketMessage(
    dynamic message,
    void Function(String text) onTranscription,
    void Function(String error) onError,
    void Function() onCompleted,
  ) {
    try {
      if (message is String) {
        final data = jsonDecode(message) as Map<String, dynamic>;
        final type = data['type'] as String?;

        switch (type) {
          case 'transcription':
            final text = data['text'] as String?;
            if (text != null && text.isNotEmpty) {
              _logger.d('Received transcription: $text');
              onTranscription(text);
            }

          case 'status':
            final content = data['content'] as String?;
            if (content == 'completed') {
              _logger.d('Transcription completed');
              _completeServerCompletion();
              onCompleted();
              unawaited(_cleanupSession());
            }

          case 'error':
            final error = data['content'] as String?;
            if (error != null) {
              _logger.e('Transcription error: $error');
              _completeServerCompletion();
              onError(error);
              unawaited(_cleanupSession());
            }

          default:
            _logger.d('Unknown message type: $type');
        }
      }
    } catch (e) {
      _logger.e('Failed to parse WebSocket message: $e');
      onError(I18nService.instance.l10n.chatAudioParseFailed(e.toString()));
    }
  }

  /// 发送音频数据到WebSocket
  void _sendAudioData(Uint8List audioData) {
    if (_webSocket != null && _isRecording) {
      try {
        // 直接发送 PCM 二进制数据
        _webSocket!.sink.add(audioData);
      } catch (e) {
        _logger.e('Failed to send audio data: $e');
      }
    }
  }

  /// 发送停止信号
  void _sendStopSignal() {
    if (_webSocket != null && !_stopSignalSent) {
      try {
        _stopSignalSent = true;
        _webSocket!.sink.add('STOP');
      } catch (e) {
        _logger.e('Failed to send STOP signal: $e');
      }
    }
  }

  /// 停止录制
  Future<void> stopRecording() async {
    if (!_isRecording && !_isStopping) {
      return;
    }

    if (_isStopping) {
      final completer = _recordingCompleter;
      if (completer != null) {
        await completer.future;
      }
      return;
    }

    _isStopping = true;

    try {
      try {
        await _recorder.stop();
      } catch (e) {
        _logger.d('Recorder stop skipped/failed: $e');
      }
      await _audioStreamSubscription?.cancel();
      _audioStreamSubscription = null;

      _sendStopSignal();

      final completion = _serverCompletionCompleter;
      if (completion != null && !completion.isCompleted) {
        try {
          await completion.future.timeout(const Duration(seconds: 2));
        } on TimeoutException {
          _logger.w('Timed out waiting for final transcription acknowledgement');
        }
      }
    } catch (e) {
      _logger.e('Failed to stop recording: $e');
    } finally {
      await _cleanupSession();
    }
  }

  /// 取消录制
  Future<void> cancelRecording() async {
    await stopRecording();
  }

  /// 获取录制时长（秒）
  int get recordingDuration => _recordingDuration;

  /// 是否正在录制
  bool get isRecording => _isRecording;

  /// 清理资源
  Future<void> dispose() async {
    await stopRecording();
    await _recorder.dispose();
  }

  void _completeServerCompletion() {
    final completer = _serverCompletionCompleter;
    if (completer != null && !completer.isCompleted) {
      completer.complete();
    }
  }

  Future<void> _cleanupSession() async {
    if (_recordingCompleter == null || _recordingCompleter!.isCompleted) {
      _isRecording = false;
      _isStopping = false;
      return;
    }

    try {
      _isRecording = false;

      _durationTimer?.cancel();
      _durationTimer = null;

      await _audioStreamSubscription?.cancel();
      _audioStreamSubscription = null;

      if (_webSocket != null) {
        await _webSocket!.sink.close();
        _webSocket = null;
      }

      _logger.d('Recording stopped');
      _recordingCompleter?.complete();
    } catch (e) {
      _logger.e('Failed during recording cleanup: $e');
      final completer = _recordingCompleter;
      if (completer != null && !completer.isCompleted) {
        completer.completeError(e);
      }
    } finally {
      _recordingCompleter = null;
      _serverCompletionCompleter = null;
      _isStopping = false;
      _stopSignalSent = false;
    }
  }
}
