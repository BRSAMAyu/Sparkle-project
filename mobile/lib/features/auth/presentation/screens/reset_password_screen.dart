import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class ResetPasswordScreen extends ConsumerStatefulWidget {
  const ResetPasswordScreen({super.key, this.initialToken});

  final String? initialToken;

  @override
  ConsumerState<ResetPasswordScreen> createState() =>
      _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _tokenController;
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void initState() {
    super.initState();
    _tokenController = TextEditingController(text: widget.initialToken ?? '');
  }

  @override
  void dispose() {
    _tokenController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));

    try {
      final message =
          await ref.read(authProvider.notifier).resetPasswordWithToken(
                _tokenController.text.trim(),
                _passwordController.text,
              );
      if (!mounted) return;
      AppFeedback.success(context, message);
      context.go('/login');
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return SparklePageScaffold(
      role: SparklePageRole.auth,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/login'),
        ),
        title: Text(context.l10n.authResetPassword),
        centerTitle: true,
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.spacing24),
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SparkleStaggerItem(
                    index: 0,
                    child: Text(
                      '请输入邮件中的重置码，并设置一个新的登录密码。',
                    ),
                  ),
                  const SizedBox(height: DS.spacing24),
                  SparkleStaggerItem(
                    index: 1,
                    child: TextFormField(
                    controller: _tokenController,
                    decoration: const InputDecoration(
                      labelText: context.l10n.authResetCode,
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.mark_email_read_outlined),
                    ),
                    validator: (value) =>
                        (value == null || value.trim().isEmpty)
                            ? '请输入重置码'
                            : null,
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  SparkleStaggerItem(
                    index: 2,
                    child: TextFormField(
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    decoration: InputDecoration(
                      labelText: context.l10n.authNewPassword,
                      border: const OutlineInputBorder(),
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        icon: Icon(
                          _obscurePassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                        ),
                        onPressed: () {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            ),
                          );
                          setState(() => _obscurePassword = !_obscurePassword);
                        },
                      ),
                    ),
                    validator: (value) {
                      if (value == null || value.length < 6) {
                        return '密码至少需要 6 位';
                      }
                      return null;
                    },
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  SparkleStaggerItem(
                    index: 3,
                    child: TextFormField(
                    controller: _confirmPasswordController,
                    obscureText: _obscureConfirmPassword,
                    decoration: InputDecoration(
                      labelText: context.l10n.authConfirmNewPassword,
                      border: const OutlineInputBorder(),
                      prefixIcon: const Icon(Icons.lock_person_outlined),
                      suffixIcon: SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        icon: Icon(
                          _obscureConfirmPassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                        ),
                        onPressed: () {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            ),
                          );
                          setState(
                            () => _obscureConfirmPassword =
                                !_obscureConfirmPassword,
                          );
                        },
                      ),
                    ),
                    validator: (value) {
                      if (value != _passwordController.text) {
                        return '两次输入的密码不一致';
                      }
                      return null;
                    },
                    ),
                  ),
                  const SizedBox(height: DS.spacing24),
                  SparkleStaggerItem(
                    index: 4,
                    child: SparkleButton(
                      label: context.l10n.authConfirmReset,
                      onPressed: authState.isLoading ? null : _submit,
                      loading: authState.isLoading,
                      disabled: authState.isLoading,
                      expand: true,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
