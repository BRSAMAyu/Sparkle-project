import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _isPasswordVisible = false;
  bool _acceptedTos = false;
  bool _acceptedPrivacy = false;

  /// N25（A-SPEC5 v1.5）校验三段制：未提交前不提前报错（disabled），
  /// 首次提交失败后转即时校验（onUserInteraction），提交时全量兜底。
  AutovalidateMode _autovalidateMode = AutovalidateMode.disabled;

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  void _submit() {
    // O3（J-01 桌面实测）：键盘 done 与按钮双通道同帧触发时，register 已
    // 把 isLoading 置真（provider 内同步置位），此处直接吞掉第二次提交，
    // 防 W-4 同款双 POST。
    if (ref.read(authProvider).isLoading) return;
    if (_formKey.currentState!.validate()) {
      if (!_acceptedTos || !_acceptedPrivacy) {
        AppFeedback.info(
            context, AppLocalizations.of(context)!.authTermsRequired,);
        return;
      }
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
      unawaited(
        ref.read(authProvider.notifier).register(
              _usernameController.text.trim(),
              _emailController.text.trim(),
              _passwordController.text.trim(),
              acceptedTos: _acceptedTos,
              acceptedPrivacy: _acceptedPrivacy,
              agreedLocale: Localizations.localeOf(context).toLanguageTag(),
            ),
      );
    } else if (_autovalidateMode != AutovalidateMode.onUserInteraction) {
      // N25 三段制：首次提交失败后，输入/失焦即校验，改错即时消错。
      setState(() => _autovalidateMode = AutovalidateMode.onUserInteraction);
    }
  }

  _PasswordStrength _passwordStrength(String password) {
    var score = 0;
    if (password.length >= 6) score++;
    if (password.length >= 10) score++;
    if (RegExp('[A-Z]').hasMatch(password)) score++;
    if (RegExp('[0-9]').hasMatch(password)) score++;
    if (RegExp(r'[!@#$%^&*(),.?":{}|<>]').hasMatch(password)) score++;
    if (score <= 1) return _PasswordStrength.weak;
    if (score <= 3) return _PasswordStrength.fair;
    return _PasswordStrength.strong;
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final l10n = AppLocalizations.of(context);

    if (l10n == null) {
      return const Scaffold(
        body: Center(child: LoadingIndicator()),
      );
    }

    // Listen for errors and show a SnackBar
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.error != null && (previous?.error != next.error)) {
        final failure = next.failure;
        // N15/N16（A-SPEC3）：error 字段已类型化——优先读 failure 自带的
        // 服务端人话；无 failure 时经 error_lexicon owner 按类别出 arb 词条，
        // 不再经 ErrorMessages 对原始异常串做文本嗅探。
        AppFeedback.error(
          context,
          failure?.userMessage ?? uiErrorMessage(l10n, next.error!),
        );
      }
      // Successful registration is handled by router redirect
    });

    return SparklePageScaffold(
      role: SparklePageRole.auth,
      safeArea: false,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          // A11Y-BATCH6A：甲式单节点（semanticLabel 直挂按钮）。
          semanticLabel: l10n.back,
          onPressed: () => context.go('/login'),
          variant: ButtonVariant.ghost,
        ),
        title: Text(l10n.register),
        elevation: 0,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      ),
      child: SafeArea(
        child: ContentConstraint(
          // A-5: the previous ConstrainedBox+IntrinsicHeight+Spacer structure
          // overflowed by 14px on 420dpi phones (the stripes covered the
          // Register button and the "already have an account" link) because
          // InputDecorator's intrinsic height under-reports the real layout
          // height, and IntrinsicHeight pinned the Column to that
          // under-reported size so the scroll view never scrolled. A plain
          // scrollable Column (no intrinsic pass, no flex children) always
          // scrolls and can never overflow; the footer link simply follows
          // the form instead of being pinned to the viewport bottom.
          child: SingleChildScrollView(
            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
            padding: const EdgeInsets.all(DS.xl),
            child: Form(
              key: _formKey,
              autovalidateMode: _autovalidateMode,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: DS.spacing20),
                  SparkleStaggerItem(
                    index: 0,
                    child: Text(
                      l10n.joinSparkle,
                      textAlign: TextAlign.center,
                      style:
                          Theme.of(context).textTheme.headlineSmall?.copyWith(
                                fontWeight: DS.fontWeightBold,
                                color: Theme.of(context).colorScheme.secondary,
                              ),
                    ),
                  ),
                  const SizedBox(height: DS.xxl),
                  SparkleStaggerItem(
                    index: 1,
                    child: TextFormField(
                      controller: _usernameController,
                      autofillHints: const [AutofillHints.username],
                      // O3：与登录屏 W-4 同款键盘链——前置字段 next 逐段推进，
                      // 末字段 done 显式提交；桌面 Enter 不再零响应。
                      textInputAction: TextInputAction.next,
                      onFieldSubmitted: (_) =>
                          FocusScope.of(context).nextFocus(),
                      decoration: InputDecoration(
                        labelText: l10n.username,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.person_outline),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return l10n.pleaseEnterUsername;
                        }
                        if (value.length < 3) {
                          return l10n.usernameMinLength;
                        }
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(height: DS.lg),
                  SparkleStaggerItem(
                    index: 2,
                    child: TextFormField(
                      controller: _emailController,
                      autofillHints: const [AutofillHints.email],
                      textInputAction: TextInputAction.next,
                      onFieldSubmitted: (_) =>
                          FocusScope.of(context).nextFocus(),
                      decoration: InputDecoration(
                        labelText: l10n.email,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.email_outlined),
                      ),
                      keyboardType: TextInputType.emailAddress,
                      validator: (value) {
                        if (value == null ||
                            !RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value)) {
                          return l10n.invalidEmail;
                        }
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(height: DS.lg),
                  SparkleStaggerItem(
                    index: 3,
                    child: TextFormField(
                      controller: _passwordController,
                      autofillHints: const [AutofillHints.newPassword],
                      obscureText: !_isPasswordVisible,
                      obscuringCharacter: '●',
                      style: const TextStyle(letterSpacing: 0),
                      textInputAction: TextInputAction.next,
                      onFieldSubmitted: (_) =>
                          FocusScope.of(context).nextFocus(),
                      decoration: InputDecoration(
                        labelText: l10n.password,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          // A11Y-BATCH6A：乙式单节点（tooltip + Icon
                          // semanticLabel 同键），两态钮按当前态命名。
                          tooltip: _isPasswordVisible
                              ? l10n.authHidePassword
                              : l10n.authShowPassword,
                          icon: Icon(
                            _isPasswordVisible
                                ? Icons.visibility
                                : Icons.visibility_off,
                            semanticLabel: _isPasswordVisible
                                ? l10n.authHidePassword
                                : l10n.authShowPassword,
                          ),
                          onPressed: () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.selection,
                              ),
                            );
                            setState(
                              () => _isPasswordVisible = !_isPasswordVisible,
                            );
                          },
                        ),
                      ),
                      validator: (value) {
                        if (value == null || value.length < 6) {
                          return l10n.passwordMinLength;
                        }
                        return null;
                      },
                    ),
                  ),
                  ValueListenableBuilder<TextEditingValue>(
                    valueListenable: _passwordController,
                    builder: (context, value, _) {
                      final password = value.text;
                      if (password.isEmpty) return const SizedBox.shrink();
                      final strength = _passwordStrength(password);
                      final zh = AppLocalizations.of(context)!;
                      return Padding(
                        padding: const EdgeInsets.only(top: DS.spacing8),
                        child: Row(
                          children: [
                            Expanded(
                              child: ClipRRect(
                                borderRadius: DS.borderRadius4,
                                child: LinearProgressIndicator(
                                  value: strength.progress,
                                  backgroundColor: DS.neutral200,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                    strength.color,
                                  ),
                                  minHeight: 4,
                                ),
                              ),
                            ),
                            const SizedBox(width: DS.spacing8),
                            Text(
                              strength.label(zh),
                              style: TextStyle(
                                fontSize: 12,
                                color: strength.color,
                                fontWeight: DS.fontWeightMedium,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: DS.lg),
                  SparkleStaggerItem(
                    index: 4,
                    child: TextFormField(
                      controller: _confirmPasswordController,
                      autofillHints: const [AutofillHints.newPassword],
                      obscureText: !_isPasswordVisible,
                      obscuringCharacter: '●',
                      style: const TextStyle(letterSpacing: 0),
                      // O3：末字段 done 显式提交（桌面 Enter 主手势），
                      // 零响应零反馈即缺陷。
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: l10n.confirmPassword,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.lock_person_outlined),
                      ),
                      validator: (value) {
                        if (value != _passwordController.text) {
                          return l10n.passwordsDoNotMatch;
                        }
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(height: DS.lg),
                  SparkleStaggerItem(
                    index: 5,
                    child: CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _acceptedTos,
                      onChanged: (value) {
                        unawaited(
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          ),
                        );
                        setState(() => _acceptedTos = value ?? false);
                      },
                      title: Text(context.l10n.authAgreeTerms),
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                  ),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      onPressed: () => context.push('/legal/terms'),
                      child: Text(context.l10n.authViewTerms),
                    ),
                  ),
                  SparkleStaggerItem(
                    index: 6,
                    child: CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: _acceptedPrivacy,
                      onChanged: (value) {
                        unawaited(
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          ),
                        );
                        setState(() => _acceptedPrivacy = value ?? false);
                      },
                      title: Text(context.l10n.authAgreePrivacy),
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                  ),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      onPressed: () => context.push('/legal/privacy'),
                      child: Text(context.l10n.authViewPrivacy),
                    ),
                  ),
                  const SizedBox(height: DS.xl),
                  SparkleStaggerItem(
                    index: 7,
                    child: SparkleButton(
                      label: l10n.register,
                      onPressed: authState.isLoading ? null : _submit,
                      expand: true,
                      loading: authState.isLoading,
                      disabled: authState.isLoading,
                    ),
                  ),
                  // A-5: fixed gap replaces the Spacer() — a flex
                  // child requires a bounded box (the removed
                  // IntrinsicHeight) and reintroduces the overflow.
                  const SizedBox(height: DS.xxl),
                  SparkleButton.ghost(
                    label: l10n.hasAccount,
                    onPressed: () => context.go('/login'),
                  ),
                  const SizedBox(height: DS.spacing12),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

enum _PasswordStrength {
  weak,
  fair,
  strong;

  double get progress => switch (this) {
        _PasswordStrength.weak => 0.33,
        _PasswordStrength.fair => 0.66,
        _PasswordStrength.strong => 1.0,
      };

  Color get color => switch (this) {
        _PasswordStrength.weak => DS.error,
        _PasswordStrength.fair => DS.warning,
        _PasswordStrength.strong => DS.success,
      };

  String label(AppLocalizations l10n) => switch (this) {
        _PasswordStrength.weak => l10n.authPasswordWeak,
        _PasswordStrength.fair => l10n.authPasswordFair,
        _PasswordStrength.strong => l10n.authPasswordStrong,
      };
}
