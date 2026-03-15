import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/utils/error_messages.dart';
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

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      if (!_acceptedTos || !_acceptedPrivacy) {
        AppFeedback.info(context, '请先同意用户协议与隐私政策');
        return;
      }
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
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final l10n = AppLocalizations.of(context);

    if (l10n == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    // Listen for errors and show a SnackBar
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.error != null && (previous?.error != next.error)) {
        AppFeedback.error(
          context,
          ErrorMessages.getLocalizedMessage(
            l10n,
            'AUTH_ERROR', // Default error code since AuthState doesn't have errorCode
            next.error,
          ),
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
          onPressed: () => context.go('/login'),
          variant: ButtonVariant.ghost,
        ),
        title: Text(l10n.register),
        elevation: 0,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      ),
      child: SafeArea(
        child: ContentConstraint(
          child: LayoutBuilder(
            builder: (context, constraints) => SingleChildScrollView(
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: const EdgeInsets.all(DS.xl),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: IntrinsicHeight(
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(height: DS.spacing20),
                        Text(
                          l10n.joinSparkle,
                          textAlign: TextAlign.center,
                          style: Theme.of(context)
                              .textTheme
                              .headlineSmall
                              ?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Theme.of(context).colorScheme.secondary,
                              ),
                        ),
                        const SizedBox(height: DS.xxl),
                        TextFormField(
                          controller: _usernameController,
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
                        const SizedBox(height: DS.lg),
                        TextFormField(
                          controller: _emailController,
                          decoration: InputDecoration(
                            labelText: l10n.email,
                            border: const OutlineInputBorder(),
                            prefixIcon: const Icon(Icons.email_outlined),
                          ),
                          keyboardType: TextInputType.emailAddress,
                          validator: (value) {
                            if (value == null ||
                                !RegExp(r'^[^@]+@[^@]+\.[^@]+')
                                    .hasMatch(value)) {
                              return l10n.invalidEmail;
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: DS.lg),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: !_isPasswordVisible,
                          decoration: InputDecoration(
                            labelText: l10n.password,
                            border: const OutlineInputBorder(),
                            prefixIcon: const Icon(Icons.lock_outline),
                            suffixIcon: SparkleIconButton(
                              icon: Icon(
                                _isPasswordVisible
                                    ? Icons.visibility_off
                                    : Icons.visibility,
                              ),
                              onPressed: () => setState(
                                () => _isPasswordVisible = !_isPasswordVisible,
                              ),
                              variant: ButtonVariant.ghost,
                            ),
                          ),
                          validator: (value) {
                            if (value == null || value.length < 6) {
                              return l10n.passwordMinLength;
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: DS.lg),
                        TextFormField(
                          controller: _confirmPasswordController,
                          obscureText: !_isPasswordVisible,
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
                        const SizedBox(height: DS.lg),
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _acceptedTos,
                          onChanged: (value) => setState(
                            () => _acceptedTos = value ?? false,
                          ),
                          title: const Text('我已阅读并同意《用户协议》'),
                          controlAffinity: ListTileControlAffinity.leading,
                        ),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: TextButton(
                            onPressed: () => context.push('/legal/terms'),
                            child: const Text('查看用户协议'),
                          ),
                        ),
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _acceptedPrivacy,
                          onChanged: (value) => setState(
                            () => _acceptedPrivacy = value ?? false,
                          ),
                          title: const Text('我已阅读并同意《隐私政策》'),
                          controlAffinity: ListTileControlAffinity.leading,
                        ),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: TextButton(
                            onPressed: () => context.push('/legal/privacy'),
                            child: const Text('查看隐私政策'),
                          ),
                        ),
                        const SizedBox(height: DS.xl),
                        SparkleButton(
                          label: l10n.register,
                          onPressed: authState.isLoading ? null : _submit,
                          expand: true,
                          loading: authState.isLoading,
                          disabled: authState.isLoading,
                        ),
                        const Spacer(),
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
          ),
        ),
      ),
    );
  }
}
