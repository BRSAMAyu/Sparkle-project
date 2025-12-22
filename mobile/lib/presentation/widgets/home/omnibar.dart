import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/repositories/omnibar_repository.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/app/theme.dart';

/// OmniBar - Project Cockpit Floating Dock
class OmniBar extends ConsumerStatefulWidget {
  const OmniBar({super.key});

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
    if (text.contains('提醒') || text.contains('做') || text.contains('任务')) {
      newIntent = 'TASK';
    } else if (text.contains('烦') || text.contains('想') || text.contains('！')) {
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
      case 'CHAT': context.push('/chat'); break;
      case 'TASK':
        await ref.read(taskListProvider.notifier).refreshTasks();
        await ref.read(dashboardProvider.notifier).refresh();
        break;
      case 'CAPSULE':
        await ref.read(cognitiveProvider.notifier).loadFragments();
        await ref.read(dashboardProvider.notifier).refresh();
        break;
    }
  }

  Color _getIntentColor() {
    switch (_intentType) {
      case 'TASK': return Colors.greenAccent;
      case 'CAPSULE': return Colors.purpleAccent;
      case 'CHAT': return Colors.blueAccent;
      default: return AppColors.textOnDark(context).withOpacity(0.15);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) {
        final color = _getIntentColor();
        return Container(
          height: 56,
          decoration: BoxDecoration(
            color: const Color(0xFF1E1E1E).withOpacity(0.9),
            borderRadius: BorderRadius.circular(28),
            border: Border.all(
              color: color.withOpacity(0.3 + (_glowAnimation.value * 0.4)),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(_glowAnimation.value * 0.2),
                blurRadius: 15,
                spreadRadius: 2,
              ),
            ],
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  onSubmitted: (_) => _submit(),
                  style: TextStyle(color: AppColors.textOnDark(context), fontSize: 15),
                  decoration: InputDecoration(
                    hintText: '告诉我你的想法...',
                    hintStyle: TextStyle(color: AppColors.textOnDark(context).withAlpha(80), fontSize: 14),
                    border: InputBorder.none,
                  ),
                ),
              ),
              if (_isLoading)
                const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
              else
                IconButton(
                  icon: Icon(
                    _intentType == 'CHAT' ? Icons.auto_awesome : Icons.arrow_upward_rounded,
                    color: _intentType != null ? color : AppColors.textOnDark(context).withOpacity(0.7),
                    size: 20,
                  ),
                  onPressed: _submit,
                ),
            ],
          ),
        );
      },
    );
  }
}
