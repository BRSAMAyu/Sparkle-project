import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/repositories/omnibar_repository.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';

/// OmniBar - The unified input for v2.3
///
/// All interactions enter through this component:
/// - Tasks: Creates task and refreshes list
/// - Capsules: Captures thought into cognitive prism
/// - Chat: Opens full chat screen
class OmniBar extends ConsumerStatefulWidget {
  const OmniBar({super.key});

  @override
  ConsumerState<OmniBar> createState() => _OmniBarState();
}

class _OmniBarState extends ConsumerState<OmniBar>
    with SingleTickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _isLoading = false;
  String? _lastActionType;

  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
    _glowAnimation = Tween<double>(begin: 0.3, end: 0.8).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );
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

    setState(() {
      _isLoading = true;
      _lastActionType = null;
    });

    try {
      final result = await ref.read(omniBarRepositoryProvider).dispatch(text);
      if (mounted) {
        await _handleResult(result);
        _controller.clear();
        _focusNode.unfocus();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('发送失败: $e'),
            backgroundColor: AppDesignTokens.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleResult(Map<String, dynamic> result) async {
    final type = result['action_type'] as String?;
    final data = result['data'] as Map<String, dynamic>?;

    setState(() {
      _lastActionType = type;
    });

    switch (type) {
      case 'CHAT':
        // Navigate to chat
        context.push('/chat');
        break;

      case 'TASK':
        // Show success with glow animation
        _glowController.forward().then((_) => _glowController.reverse());

        // Refresh task list and dashboard
        await ref.read(taskListProvider.notifier).refreshTasks();
        await ref.read(dashboardProvider.notifier).refresh();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Row(
                children: [
                  const Icon(Icons.check_circle, color: Colors.white, size: 20),
                  const SizedBox(width: 8),
                  Text('任务已创建: ${data?['title'] ?? ''}'),
                ],
              ),
              backgroundColor: AppDesignTokens.success,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          );
        }
        break;

      case 'CAPSULE':
        // Show purple glow for capsule
        _glowController.forward().then((_) => _glowController.reverse());

        // Refresh cognitive data
        await ref.read(cognitiveProvider.notifier).loadFragments();
        await ref.read(dashboardProvider.notifier).refresh();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Row(
                children: [
                  Icon(Icons.diamond_outlined, color: Colors.white, size: 20),
                  SizedBox(width: 8),
                  Text('已捕获到认知棱镜'),
                ],
              ),
              backgroundColor: AppDesignTokens.prismPurple,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          );
        }
        break;
    }
  }

  Color _getGlowColor() {
    switch (_lastActionType) {
      case 'TASK':
        return AppDesignTokens.success;
      case 'CAPSULE':
        return AppDesignTokens.prismPurple;
      default:
        return AppDesignTokens.primaryBase;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) {
        final glowColor = _getGlowColor();

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: AppDesignTokens.glassBackground,
            borderRadius: BorderRadius.circular(30),
            border: Border.all(
              color: _lastActionType != null
                  ? glowColor.withAlpha((_glowAnimation.value * 255).toInt())
                  : AppDesignTokens.glassBorder,
              width: _lastActionType != null ? 1.5 : 1,
            ),
            boxShadow: _lastActionType != null
                ? [
                    BoxShadow(
                      color: glowColor.withAlpha(
                        (_glowAnimation.value * 100).toInt(),
                      ),
                      blurRadius: 20,
                      spreadRadius: 2,
                    ),
                  ]
                : [
                    BoxShadow(
                      color: Colors.black.withAlpha(25),
                      blurRadius: 10,
                      offset: const Offset(0, 5),
                    ),
                  ],
          ),
          child: Row(
            children: [
              // Input field
              Expanded(
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  onSubmitted: (_) => _submit(),
                  style: const TextStyle(color: Colors.white, fontSize: 15),
                  decoration: InputDecoration(
                    hintText: '想做什么？或是随便聊聊...',
                    border: InputBorder.none,
                    hintStyle: TextStyle(
                      color: Colors.white.withAlpha(100),
                      fontSize: 15,
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 4),
                    isDense: true,
                  ),
                ),
              ),

              const SizedBox(width: 8),

              // Send button
              if (_isLoading)
                const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white70),
                  ),
                )
              else
                GestureDetector(
                  onTap: _submit,
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppDesignTokens.primaryBase,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.arrow_upward_rounded,
                      color: Colors.white,
                      size: 18,
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
