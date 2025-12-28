import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Listen to the auth state changes.
    // This is robust against the initial state being loading.
    ref.listen<AuthState>(authProvider, (previous, next) {
      // Wait for the initial loading to be complete
      if ((previous?.isLoading ?? false) && next.isLoading == false) {
        if (next.isAuthenticated) {
          // User is logged in, go to home
          // Using replace to prevent going back to splash screen
          context.replace('/home');
        } else {
          // User is not logged in, go to login
          context.replace('/login');
        }
      }
    });

    // The UI to show while the check is in progress.
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Placeholder for Sparkle Logo/Animation
            Icon(
              Icons.whatshot, // Represents the "flame"
              size: 80,
              color: DS.brandPrimaryConst, // Sparkle primary color
            ),
            const SizedBox(height: 20),
            Text(
              'Sparkle',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.secondary,
              ),
            ),
            const SizedBox(height: 40),
            const CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
