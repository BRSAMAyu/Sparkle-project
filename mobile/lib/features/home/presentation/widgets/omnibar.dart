import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/home/data/repositories/omnibar_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

/// OmniBar - Project Cockpit Floating Dock
class OmniBar extends ConsumerStatefulWidget {
  const OmniBar({super.key, this.hintText});
  final String? hintText;

  @override
  ConsumerState<OmniBar> createState() => _OmniBarState();
}

class _OmniBarState extends ConsumerState<OmniBar>
    with SingleTickerProviderStateMixin {
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
    if (text.contains('提醒') ||
        text.contains('做') ||
        text.contains('任务') ||
        text.contains('task') ||
        text.contains('remind') ||
        text.contains('todo')) {
      newIntent = 'TASK';
    } else if (text.contains('烦') ||
        text.contains('想') ||
        text.contains('！') ||
        text.contains('feel') ||
        text.contains('think')) {
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
          SnackBar(content: Text('发送失败: $e'), backgroundColor: DS.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleResult(Map<String, dynamic> result) async {
    final type = result['action_type'] as String?;
    switch (type) {
      case 'CHAT':
        context.push('/chat');
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
      case 'TASK':
        return DS.successAccent;
      case 'CAPSULE':
        return Colors.purpleAccent;
      case 'CHAT':
        return DS.brandPrimaryAccent;
      default:
        return DS.textSecondary.withValues(alpha: 0.15);
    }
  }

  @override
  Widget build(BuildContext context) {
    final enterToSend = ref.watch(enterToSendProvider);

    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) {
        final color = _getIntentColor();
        
        // Base neoGlass material
        final material = AppMaterials.neoGlass.copyWith(
           // Higher opacity for floating dock
           backgroundColor: context.sparkleColors.surfacePrimary.withValues(alpha: 0.1),
           // Dynamic border based on glow
           borderColor: color.withValues(alpha: 0.3 + _glowAnimation.value * 0.4),
           borderWidth: 1.5,
           // Dynamic shadow/glow
           shadows: [
              BoxShadow(
                color: color.withValues(alpha: 0.2 * _glowAnimation.value),
                blurRadius: 12,
                spreadRadius: 2,
              ),
              ...context.sparkleShadows.medium,
           ],
        );

        return MaterialStyler(
          material: material,
          borderRadius: BorderRadius.circular(32),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  onSubmitted: enterToSend ? (_) => _submit() : null,
                  style: context.sparkleTypography.bodyLarge.copyWith(
                    color: DS.textPrimary,
                  ),
                  decoration: InputDecoration(
                    hintText: _isListening
                        ? 'Listening...'
                        : (widget.hintText ?? 'Tell me what you think...'),
                    hintStyle: context.sparkleTypography.bodyLarge.copyWith(
                      color: _isListening
                          ? DS.brandPrimary
                          : DS.textSecondary.withValues(alpha: 0.5),
                    ),
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.zero,
                  ),
                  cursorColor: DS.brandPrimary,
                ),
              ),
              if (_isLoading)
                Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
                      ),),
                )
              else if (_controller.text.isEmpty && !_isListening)
                IconButton(
                  icon: Icon(Icons.mic, color: DS.brandPrimary),
                  onPressed: _toggleListening,
                  tooltip: '语音输入',
                )
              else
                IconButton(
                  icon: Icon(
                    _isListening
                        ? Icons.stop_circle_outlined
                        : (_intentType == 'CHAT'
                            ? Icons.auto_awesome
                            : Icons.arrow_upward_rounded),
                    color: _isListening
                        ? DS.error
                        : (_intentType != null
                            ? color
                            : DS.textSecondary.withValues(alpha: 0.7)),
                    size: 24,
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
