import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isPasswordVisible = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _submit() {
    if (_formKey.currentState!.validate()) {
      ref.read(authProvider.notifier).login(
            _usernameController.text.trim(),
            _passwordController.text.trim(),
          );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    // Listen for errors and show a SnackBar
    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.error != null && (previous?.error != next.error)) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.error!),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
      // Successful login is handled by router redirect
    });

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.xl),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 60),
                // Logo and Welcome
                Icon(
                  Icons.whatshot_outlined,
                  size: 60,
                  color: DS.brandPrimaryConst,
                ),
                const SizedBox(height: DS.lg),
                Text(
                  'Welcome Back to Sparkle',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.secondary,
                      ),
                ),
                const SizedBox(height: DS.sm),
                Text(
                  'Ignite your learning potential.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: DS.xxxl),

                // Username field
                TextFormField(
                  controller: _usernameController,
                  decoration: const InputDecoration(
                    labelText: 'Username or Email',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.person_outline),
                  ),
                  validator: (value) =>
                      value!.isEmpty ? 'Please enter your username or email' : null,
                ),
                const SizedBox(height: DS.lg),

                // Password field
                TextFormField(
                  controller: _passwordController,
                  obscureText: !_isPasswordVisible,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    border: const OutlineInputBorder(),
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      icon: Icon(_isPasswordVisible
                          ? Icons.visibility_off
                          : Icons.visibility,),
                      onPressed: () =>
                          setState(() => _isPasswordVisible = !_isPasswordVisible),
                    ),
                  ),
                  validator: (value) =>
                      value!.isEmpty ? 'Please enter your password' : null,
                ),
                const SizedBox(height: DS.xl),

                // Login Button
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: DS.brandPrimary,
                    foregroundColor: DS.brandPrimary,
                  ),
                  onPressed: authState.isLoading ? null : _submit,
                  child: authState.isLoading
                      ? SizedBox(
                          height: 24,
                          width: 24,
                          child: CircularProgressIndicator(strokeWidth: 2, color: DS.brandPrimary),
                        )
                      : const Text('Login'),
                ),
                
                const SizedBox(height: DS.xl),
                Row(
                  children: [
                    const Expanded(child: Divider()),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Text('OR', style: TextStyle(color: DS.brandPrimary)),
                    ),
                    const Expanded(child: Divider()),
                  ],
                ),
                const SizedBox(height: DS.xl),

                // Social Login Buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _SocialLoginButton(
                      icon: Icons.g_mobiledata_rounded, // Use a generic icon or custom asset
                      label: 'Google',
                      onTap: () {
                        // Mock Google Login
                        ref.read(authProvider.notifier).socialLogin(
                          provider: 'google',
                          token: 'mock-google-token-123',
                          nickname: 'Google User',
                        );
                      },
                    ),
                    _SocialLoginButton(
                      icon: Icons.apple_rounded, 
                      label: 'Apple',
                      onTap: () {
                        // Mock Apple Login
                        ref.read(authProvider.notifier).socialLogin(
                          provider: 'apple',
                          token: 'mock-apple-token-123',
                          nickname: 'Apple User',
                        );
                      },
                    ),
                    _SocialLoginButton(
                      icon: Icons.wechat_rounded, // Assuming Material Icons has WeChat or similar
                      label: 'WeChat',
                      onTap: () {
                        // Mock WeChat Login
                        ref.read(authProvider.notifier).socialLogin(
                          provider: 'wechat',
                          token: 'mock-wechat-token-123',
                          nickname: 'WeChat User',
                        );
                      },
                    ),
                  ],
                ),

                const SizedBox(height: DS.lg),

                // Register Link
                TextButton(
                  onPressed: () => context.go('/register'),
                  child: const Text("Don't have an account? Register"),
                ),
                
                const SizedBox(height: DS.sm),
                
                // Guest Mode
                TextButton(
                  onPressed: () {
                    ref.read(authProvider.notifier).loginAsGuest();
                  },
                  child: Text(
                    'Continue as Guest',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.outline,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SocialLoginButton extends StatelessWidget {

  const _SocialLoginButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: colorScheme.surface,
          border: Border.all(color: colorScheme.outline.withValues(alpha: 0.2)),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.05),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Icon(
          icon, 
          size: 32, 
          color: colorScheme.onSurface,
        ),
      ),
    );
  }
}
