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
  Timer? _durationTimer;
  int _recordingDuration = 0;
  Completer<void>? _recordingCompleter;

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
    _recordingDuration = 0;
    _recordingCompleter = Completer<void>();

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
          stopRecording();
        },
        onDone: () {
          _logger.d('WebSocket closed');
          stopRecording();
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
          stopRecording();
        },
        onDone: () {
          _logger.d('Audio stream ended');
          // Send stop signal to server
          _sendStopSignal();
          onCompleted();
          stopRecording();
        },
        cancelOnError: true,
      );

      // 5. 启动时长计时器
      if (maxDuration != null) {
        _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
          _recordingDuration++;
          if (_recordingDuration >= maxDuration.inSeconds) {
            _logger.d('Max duration reached: $maxDuration');
            _sendStopSignal();
            stopRecording();
          }
        });
      }

      _logger.d('Recording started successfully');
    } catch (e) {
      _logger.e('Failed to start recording: $e');
      onError(I18nService.instance.l10n.chatAudioStartFailed(e.toString()));
      stopRecording();
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
              onCompleted();
              stopRecording();
            }

          case 'error':
            final error = data['content'] as String?;
            if (error != null) {
              _logger.e('Transcription error: $error');
              onError(error);
              stopRecording();
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
    if (_webSocket != null) {
      try {
        _webSocket!.sink.add('STOP');
      } catch (e) {
        _logger.e('Failed to send STOP signal: $e');
      }
    }
  }

  /// 停止录制
  Future<void> stopRecording() async {
    if (!_isRecording) {
      return;
    }

    _isRecording = false;

    try {
      // 停止录制
      await _recorder.stop();

      // 取消订阅
      await _audioStreamSubscription?.cancel();
      _audioStreamSubscription = null;

      // 关闭WebSocket
      if (_webSocket != null) {
        await _webSocket!.sink.close();
        _webSocket = null;
      }

      // 停止计时器
      _durationTimer?.cancel();
      _durationTimer = null;

      // 完成录制
      if (!_recordingCompleter!.isCompleted) {
        _recordingCompleter!.complete();
      }

      _logger.d('Recording stopped');
    } catch (e) {
      _logger.e('Failed to stop recording: $e');
      if (!_recordingCompleter!.isCompleted) {
        _recordingCompleter!.completeError(e);
      }
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
}
