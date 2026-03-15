import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() =>
      _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    try {
      final message = await ref
          .read(authProvider.notifier)
          .forgotPassword(_emailController.text.trim());
      if (!mounted) return;
      AppFeedback.success(context, message);
      context.go('/reset-password');
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
        title: const Text('忘记密码'),
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
                  Text(
                    '输入注册邮箱，我们会发送一封包含重置码的邮件给你。',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: DS.spacing24),
                  TextFormField(
                    controller: _emailController,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(
                      labelText: '邮箱',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                    validator: (value) {
                      if (value == null ||
                          !RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value)) {
                        return '请输入有效邮箱';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: DS.spacing24),
                  SparkleButton(
                    label: '发送重置邮件',
                    onPressed: authState.isLoading ? null : _submit,
                    loading: authState.isLoading,
                    disabled: authState.isLoading,
                    expand: true,
                  ),
                  const SizedBox(height: DS.spacing12),
                  SparkleButton.ghost(
                    label: '我已经有重置码',
                    onPressed: () => context.go('/reset-password'),
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
