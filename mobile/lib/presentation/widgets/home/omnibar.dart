import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/repositories/omnibar_repository.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/settings_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';

/// OmniBar - Project Cockpit Floating Dock
class OmniBar extends ConsumerStatefulWidget {
  const OmniBar({super.key, this.hintText});
  final String? hintText;

  @override
  ConsumerState<OmniBar> createState() => _OmniBarState();
}

class _OmniBarState extends ConsumerState<OmniBar> with SingleTickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _isLoading = false;
  String? _intentType; // 'TASK', 'CAPSULE', 'CHAT'

  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _glowAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );

    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final text = _controller.text.toLowerCase();
    String? newIntent;
    // Bilingual support for keywords
    if (text.contains('提醒') || text.contains('做') || text.contains('任务') || 
        text.contains('task') || text.contains('remind') || text.contains('todo')) {
      newIntent = 'TASK';
    } else if (text.contains('烦') || text.contains('想') || text.contains('！') ||
               text.contains('feel') || text.contains('think')) {
      newIntent = 'CAPSULE';
    } else if (text.length > 10) {
      newIntent = 'CHAT';
    }

    if (newIntent != _intentType) {
      setState(() => _intentType = newIntent);
      if (newIntent != null) {
        _glowController.forward(from: 0);
      } else {
        _glowController.reverse();
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _glowController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() => _isLoading = true);

    try {
      final result = await ref.read(omniBarRepositoryProvider).dispatch(text);
      if (mounted) {
        await _handleResult(result);
        _controller.clear();
        _focusNode.unfocus();
        setState(() => _intentType = null);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('发送失败: $e'), backgroundColor: AppDesignTokens.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleResult(Map<String, dynamic> result) async {
    final type = result['action_type'] as String?;
    switch (type) {
      case 'CHAT': context.push('/chat');
      case 'TASK':
        await ref.read(taskListProvider.notifier).refreshTasks();
        await ref.read(dashboardProvider.notifier).refresh();
      case 'CAPSULE':
        await ref.read(cognitiveProvider.notifier).loadFragments();
        await ref.read(dashboardProvider.notifier).refresh();
    }
  }

  Color _getIntentColor() {
    switch (_intentType) {
      case 'TASK': return DS.successAccent;
      case 'CAPSULE': return Colors.purpleAccent;
      case 'CHAT': return DS.brandPrimaryAccent;
      default: return AppColors.textOnDark(context).withValues(alpha: 0.15);
    }
  }

  @override
  Widget build(BuildContext context) {
    final enterToSend = ref.watch(enterToSendProvider);
    
    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) {
        final color = _getIntentColor();
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.8),
            borderRadius: BorderRadius.circular(32),
            border: Border.all(
              color: color.withValues(alpha: 0.3 + _glowAnimation.value * 0.4),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: color.withValues(alpha: 0.2 * _glowAnimation.value),
                blurRadius: 12,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  onSubmitted: enterToSend ? (_) => _submit() : null,
                  style: TextStyle(color: AppColors.textOnDark(context), fontSize: 15),
                  decoration: InputDecoration(
                    hintText: _isListening 
                        ? 'Listening...' 
                        : (widget.hintText ?? 'Tell me what you think...'),
                    hintStyle: TextStyle(
                      color: _isListening 
                          ? AppDesignTokens.primaryBase 
                          : AppColors.textOnDark(context).withAlpha(80), 
                      fontSize: 14,
                    ),
                    border: InputBorder.none,
                  ),
                ),
              ),
              if (_isLoading)
                const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
              else if (_controller.text.isEmpty && !_isListening)
                 IconButton(
                  icon: const Icon(Icons.mic, color: AppDesignTokens.primaryBase),
                  onPressed: _toggleListening,
                  tooltip: '语音输入',
                )
              else
                IconButton(
                  icon: Icon(
                    _isListening 
                        ? Icons.stop_circle_outlined 
                        : (_intentType == 'CHAT' ? Icons.auto_awesome : Icons.arrow_upward_rounded),
                    color: _isListening 
                        ? DS.errorAccent 
                        : (_intentType != null ? color : AppColors.textOnDark(context).withValues(alpha: 0.7)),
                    size: 20,
                  ),
                  onPressed: _isListening ? _toggleListening : _submit,
                ),
            ],
          ),
        );
      },
    );
  }

  bool _isListening = false;

  void _toggleListening() {
    setState(() {
      _isListening = !_isListening;
    });

    if (_isListening) {
      _glowController.repeat(reverse: true);
      // Feature: Implement WebSocket audio streaming
      // See: lib/core/services/websocket_service.dart
      // For UI demo, simulate text input after 2 seconds
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted && _isListening) {
          setState(() {
            _isListening = false;
            _controller.text = '创建一个复习离散数学的计划';
            _onTextChanged();
            _glowController.stop();
            _glowController.reset();
            _glowController.forward();
          });
        }
      });
    } else {
      _glowController.stop();
      _glowController.reset();
    }
  }
}
