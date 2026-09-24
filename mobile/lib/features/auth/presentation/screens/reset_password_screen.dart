import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';

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

  /// N25（A-SPEC5 v1.5）校验三段制：未提交前不提前报错（disabled），
  /// 首次提交失败后转即时校验（onUserInteraction），提交时全量兜底。
  AutovalidateMode _autovalidateMode = AutovalidateMode.disabled;

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
    if (!_formKey.currentState!.validate()) {
      if (_autovalidateMode != AutovalidateMode.onUserInteraction) {
        // N25 三段制：首次提交失败后，输入/失焦即校验，改错即时消错。
        setState(() => _autovalidateMode = AutovalidateMode.onUserInteraction);
      }
      return;
    }
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
      AppFeedback.error(context, UserFacingError.from(e));
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
          // A11Y-BATCH6A：甲式单节点（semanticLabel 直挂按钮）。
          semanticLabel: context.l10n.back,
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
              autovalidateMode: _autovalidateMode,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SparkleStaggerItem(
                    index: 0,
                    child: Text(
                      context.l10n.authResetPasswordInstructions,
                    ),
                  ),
                  const SizedBox(height: DS.spacing24),
                  SparkleStaggerItem(
                    index: 1,
                    child: TextFormField(
                      controller: _tokenController,
                      decoration: InputDecoration(
                        labelText: context.l10n.authResetCode,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.mark_email_read_outlined),
                      ),
                      validator: (value) =>
                          (value == null || value.trim().isEmpty)
                              ? context.l10n.authResetCodeRequired
                              : null,
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  SparkleStaggerItem(
                    index: 2,
                    child: TextFormField(
                      controller: _passwordController,
                      autofillHints: const [AutofillHints.newPassword],
                      obscureText: _obscurePassword,
                      decoration: InputDecoration(
                        labelText: context.l10n.authNewPassword,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          // A11Y-BATCH6A：乙式单节点（tooltip + Icon
                          // semanticLabel 同键），两态钮按当前态命名。
                          tooltip: _obscurePassword
                              ? context.l10n.authShowPassword
                              : context.l10n.authHidePassword,
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                            semanticLabel: _obscurePassword
                                ? context.l10n.authShowPassword
                                : context.l10n.authHidePassword,
                          ),
                          onPressed: () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.selection,
                              ),
                            );
                            setState(
                                () => _obscurePassword = !_obscurePassword,);
                          },
                        ),
                      ),
                      validator: (value) {
                        if (value == null || value.length < 6) {
                          return context.l10n.authPasswordMinLength;
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
                      autofillHints: const [AutofillHints.newPassword],
                      obscureText: _obscureConfirmPassword,
                      decoration: InputDecoration(
                        labelText: context.l10n.authConfirmNewPassword,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.lock_person_outlined),
                        suffixIcon: IconButton(
                          // A11Y-BATCH6A：乙式单节点，两态钮按当前态命名。
                          tooltip: _obscureConfirmPassword
                              ? context.l10n.authShowConfirmPassword
                              : context.l10n.authHideConfirmPassword,
                          icon: Icon(
                            _obscureConfirmPassword
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                            semanticLabel: _obscureConfirmPassword
                                ? context.l10n.authShowConfirmPassword
                                : context.l10n.authHideConfirmPassword,
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
                          return context.l10n.authPasswordsDoNotMatch;
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
