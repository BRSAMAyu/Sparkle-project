import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/chat/data/services/audio_recording_service.dart';

/// 语音输入按钮组件
/// 点击开始/结束录音；长按仍可快速按住说话。
class VoiceInputButton extends ConsumerStatefulWidget {
  const VoiceInputButton({
    required this.onTranscription,
    required this.onError,
    super.key,
    this.onRecordingStarted,
    this.onRecordingStopped,
    this.size = 48,
  });
  final void Function(String text) onTranscription;
  final void Function(String error) onError;
  final VoidCallback? onRecordingStarted;
  final VoidCallback? onRecordingStopped;
  final double size;

  @override
  ConsumerState<VoiceInputButton> createState() => _VoiceInputButtonState();
}

class _VoiceInputButtonState extends ConsumerState<VoiceInputButton>
    with SingleTickerProviderStateMixin {
  final AudioRecordingService _recordingService = AudioRecordingService();
  bool _isRecording = false;
  bool _isProcessing = false;
  int _recordingDuration = 0;
  Timer? _durationTimer;
  AnimationController? _animationController;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
  }

  @override
  void dispose() {
    _durationTimer?.cancel();
    _animationController?.dispose();
    _recordingService.dispose();
    super.dispose();
  }

  /// 检查麦克风权限
  Future<bool> _checkPermissions() async {
    final status = await Permission.microphone.request();
    if (status.isGranted) {
      return true;
    }
    if (status.isPermanentlyDenied || status.isRestricted || status.isDenied) {
      if (mounted) {
        await _showPermissionDialog();
      }
    }
    return false;
  }

  /// 显示权限申请对话框
  Future<void> _showPermissionDialog() => showAppPermissionDialog(
      context,
      permission: AppPermissionKind.microphone,
    );

  /// 开始录音
  Future<void> _startRecording() async {
    if (_isRecording) return;

    // 检查权限
    final hasPermission = await _checkPermissions();
    if (!hasPermission) {
      widget.onError(context.l10n.voiceInputNoPermission);
      return;
    }

    setState(() {
      _isRecording = true;
      _isProcessing = false;
      _recordingDuration = 0;
    });

    _animationController?.forward();

    // 启动时长计时器
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        setState(() {
          _recordingDuration++;
        });
      }
    });

    // 获取WebSocket URL和认证令牌
    final wsUrl = '${ApiConstants.wsBaseUrl}${ApiConstants.wsStt}';
    final authToken = await ref.read(authRepositoryProvider).getAccessToken();

    if (authToken == null) {
      if (mounted) {
        setState(() {
          _isRecording = false;
          _isProcessing = false;
        });
        _animationController?.reverse();
        widget.onError(context.l10n.voiceInputLoginRequired);
      }
      return;
    }

    try {
      await _recordingService.startRecording(
        wsUrl: wsUrl,
        authToken: authToken,
        onTranscription: (text) {
          if (mounted) {
            setState(() {
              _isProcessing = false;
            });
            // 实时更新父组件的文本
            widget.onTranscription(text);
          }
        },
        onError: (error) {
          if (mounted) {
            setState(() {
              _isRecording = false;
              _isProcessing = false;
            });
            _animationController?.reverse();
            widget.onError(error);
          }
        },
        onCompleted: () {
          if (mounted) {
            setState(() {
              _isRecording = false;
              _isProcessing = false;
            });
            _animationController?.reverse();
            widget.onRecordingStopped?.call();
          }
        },
        maxDuration: const Duration(seconds: 30), // 智谱 ASR 单次最长 30 秒
      );

      widget.onRecordingStarted?.call();
    } catch (e) {
      if (mounted) {
        setState(() {
          _isRecording = false;
          _isProcessing = false;
        });
        _animationController?.reverse();
        widget.onError(context.l10n.voiceInputStartFailed(e.toString()));
      }
    }
  }

  /// 停止录音
  Future<void> _stopRecording() async {
    if (!_isRecording || _isProcessing) return;

    setState(() {
      _isProcessing = true;
    });

    await _recordingService.stopRecording();

    _durationTimer?.cancel();
    _durationTimer = null;

    if (mounted) {
      setState(() {
        _isRecording = false;
        _isProcessing = false;
      });
      _animationController?.reverse();
      widget.onRecordingStopped?.call();
    }
  }

  /// 取消录音
  Future<void> _cancelRecording() async {
    if (!_isRecording) return;

    await _recordingService.cancelRecording();

    _durationTimer?.cancel();
    _durationTimer = null;

    if (mounted) {
      setState(() {
        _isRecording = false;
        _isProcessing = false;
      });
      _animationController?.reverse();
      widget.onRecordingStopped?.call();
    }
  }

  /// 格式化时长显示
  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final secs = seconds % 60;
    return "${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return GestureDetector(
      onTap: () {
        if (_isRecording) {
          unawaited(_stopRecording());
        } else {
          unawaited(_startRecording());
        }
      },
      onLongPressStart: (_) => _startRecording(),
      onLongPressEnd: (_) => _stopRecording(),
      onLongPressCancel: _cancelRecording,
      child: AnimatedBuilder(
        animation: _animationController!,
        builder: (context, child) {
          final scale = 1.0 + (_animationController?.value ?? 0) * 0.1;
          return Transform.scale(
            scale: scale,
            child: child,
          );
        },
        child: Container(
          width: widget.size,
          height: widget.size,
          decoration: BoxDecoration(
            color: _isRecording
                ? DS.brandPrimary
                : (isDark ? DS.neutral800 : DS.neutral200),
            shape: BoxShape.circle,
            boxShadow: _isRecording
                ? [
                    BoxShadow(
                      color: DS.brandPrimary.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Center(
            child: _buildButtonContent(isDark: isDark),
          ),
        ),
      ),
    );
  }

  Widget _buildButtonContent({required bool isDark}) {
    final idleIconColor =
        isDark ? DS.textSecondary.withValues(alpha: 0.92) : DS.neutral600;
    // 根据按钮尺寸动态调整图标大小
    final iconSize = (widget.size * 0.42).clamp(16.0, 28.0);
    final progressSize = (widget.size * 0.46).clamp(18.0, 26.0);
    final fontSize = (widget.size * 0.17).clamp(6.0, 10.0);

    if (_isProcessing) {
      return SizedBox(
        width: progressSize,
        height: progressSize,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: DS.brandPrimaryConst,
        ),
      );
    }

    if (_isRecording) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.mic,
            color: DS.textOnPrimary,
            size: iconSize,
          ),
          Text(
            _formatDuration(_recordingDuration),
            style: TextStyle(
              fontSize: fontSize,
              color: DS.textOnPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      );
    }

    return Icon(
      Icons.mic_none,
      color: idleIconColor,
      size: iconSize,
    );
  }
}
