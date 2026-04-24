import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

class ModelingChatScreen extends ConsumerStatefulWidget {
  const ModelingChatScreen({
    this.postOnboardingMessage,
    super.key,
  });

  final String? postOnboardingMessage;

  @override
  ConsumerState<ModelingChatScreen> createState() => _ModelingChatScreenState();
}

class _ModelingChatScreenState extends ConsumerState<ModelingChatScreen> {
  final TextEditingController _inputController = TextEditingController();
  final List<_ModelingMessage> _messages = <_ModelingMessage>[];
  String? _conversationId;
  bool _loading = false;
  bool _completed = false;
  int _assistantTurns = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_sendModelingTurn('_onboarding_start_'));
    });
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: const Text('让我更了解你（约2分钟）'),
        actions: [
          TextButton(
            onPressed: _loading ? null : () => unawaited(_skip()),
            child: const Text('跳过'),
          ),
        ],
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(DS.spacing16),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final message = _messages[index];
                  final isUser = message.isUser;
                  return Align(
                    alignment:
                        isUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: DS.spacing12),
                      padding: const EdgeInsets.all(DS.spacing12),
                      constraints: const BoxConstraints(maxWidth: 520),
                      decoration: BoxDecoration(
                        color: isUser ? DS.primaryBase : DS.surfaceSecondary,
                        borderRadius: DS.borderRadius16,
                      ),
                      child: Text(
                        message.text,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: isUser
                                  ? DS.brandPrimaryConst
                                  : DS.textPrimary,
                              height: 1.45,
                            ),
                      ),
                    ),
                  );
                },
              ),
            ),
            if (_completed)
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  DS.spacing16,
                  0,
                  DS.spacing16,
                  DS.spacing16,
                ),
                child: SparkleButton(
                  label: '进入主界面',
                  onPressed: _finish,
                ),
              )
            else
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _inputController,
                          enabled: !_loading,
                          onSubmitted: (_) => _handleSubmit(),
                          decoration: const InputDecoration(
                            hintText: '输入你的回答…',
                          ),
                        ),
                      ),
                      const SizedBox(width: DS.spacing8),
                      SparkleIconButton(
                        variant: ButtonVariant.primary,
                        icon: _loading
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.send_rounded),
                        onPressed: _loading ? null : _handleSubmit,
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleSubmit() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _loading) {
      return;
    }
    _inputController.clear();
    setState(() {
      _messages.add(_ModelingMessage(text: text, isUser: true));
    });
    await _sendModelingTurn(text);
  }

  Future<void> _sendModelingTurn(String message) async {
    setState(() => _loading = true);
    try {
      final response = await ref.read(chatRepositoryProvider).sendMessage(
        message,
        conversationId: _conversationId,
        extraContext: const {'mode': 'onboarding_modeling'},
      );
      if (!mounted) return;
      setState(() {
        _conversationId = response.conversationId;
        _messages.add(_ModelingMessage(text: response.message, isUser: false));
        _assistantTurns += 1;
        _completed =
            _assistantTurns >= 4 || response.message.contains('等你开始规划的时候');
      });
      if (_completed) {
        ref.invalidate(profileContextProvider);
      }
    } catch (error) {
      if (!mounted) return;
      AppFeedback.error(context, '建模对话暂时失败：$error');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _skip() async {
    setState(() => _loading = true);
    try {
      await ref.read(chatRepositoryProvider).sendMessage(
        '_onboarding_skip_',
        conversationId: _conversationId,
        extraContext: const {
          'mode': 'onboarding_modeling',
          'skip': true,
        },
      );
      if (!mounted) return;
      await _finish();
    } catch (error) {
      if (!mounted) return;
      AppFeedback.error(context, '暂时无法跳过：$error');
      setState(() => _loading = false);
    }
  }

  Future<void> _finish() async {
    await ref.read(onboardingCompletedProvider.notifier).setCompleted(true);
    ref.invalidate(profileContextProvider);
    if (!mounted) return;
    final firstMessage = widget.postOnboardingMessage?.trim();
    if (firstMessage != null && firstMessage.isNotEmpty) {
      context.go('/chat', extra: {'initial_ai_message': firstMessage});
    } else {
      context.go('/home');
    }
  }
}

class _ModelingMessage {
  const _ModelingMessage({
    required this.text,
    required this.isUser,
  });

  final String text;
  final bool isUser;
}
