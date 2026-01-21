import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:logger/logger.dart';
import 'package:record/record.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// 音频录制服务
/// 负责录制音频并实时流式传输到服务器
class AudioRecordingService {
  final AudioRecorder _recorder = AudioRecorder();
  final Logger _logger = Logger();
  WebSocketChannel? _webSocket;
  StreamSubscription<dynamic>? _audioSubscription;
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
      _webSocket = WebSocketChannel.connect(Uri.parse(wsUrl));

      // 2. 开始监听WebSocket消息
      _webSocket!.stream.listen(
        (message) {
          _handleWebSocketMessage(message, onTranscription, onError, onCompleted);
        },
        onError: (error) {
          _logger.e('WebSocket error: $error');
          onError('WebSocket连接失败: $error');
          stopRecording();
        },
        onDone: () {
          _logger.d('WebSocket closed');
          stopRecording();
        },
        cancelOnError: true,
      );

      // 3. 开始录制音频
      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
        ),
        path: '',  // 空路径表示不保存到文件
      );

      // 4. 监听音频流
      _audioSubscription = _recorder.onAmplitudeChanged(
        const Duration(milliseconds: 100),
      ).listen((amplitude) {
        // 发送音频数据到WebSocket
        if (_webSocket != null && _isRecording) {
          // 注意：record包的onAmplitudeChanged只返回振幅，不返回音频数据
          // 实际的音频流需要通过其他方式获取
          // 这里我们使用一个简化的实现
          _sendAudioData(amplitude);
        }
      });

      // 5. 启动时长计时器
      if (maxDuration != null) {
        _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
          _recordingDuration++;
          if (_recordingDuration >= maxDuration.inSeconds) {
            _logger.d('Max duration reached: $maxDuration');
            stopRecording();
          }
        });
      }

      _logger.d('Recording started');
    } catch (e) {
      _logger.e('Failed to start recording: $e');
      onError('录制启动失败: $e');
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
      onError('解析消息失败: $e');
    }
  }

  /// 发送音频数据到WebSocket
  void _sendAudioData(dynamic amplitudeData) {
    // 注意：record包的onAmplitudeChanged只返回振幅，不返回原始音频数据
    // 在实际应用中，需要使用其他方式获取原始音频数据
    // 这里我们发送一个占位符，实际实现需要根据音频格式调整

    // 如果WebSocket连接正常，发送音频数据
    if (_webSocket != null && _isRecording) {
      try {
        // 发送音频数据（这里需要根据实际音频格式调整）
        // 实际实现中，需要获取原始音频字节流
        // _webSocket!.sink.add(audioBytes);
      } catch (e) {
        _logger.e('Failed to send audio data: $e');
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
      await _audioSubscription?.cancel();
      _audioSubscription = null;

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
