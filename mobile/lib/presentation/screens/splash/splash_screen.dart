import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Listen to the auth state changes.
    // This is robust against the initial state being loading.
    ref.listen<AuthState>(authProvider, (previous, next) {
      // Wait for the initial loading to be complete
      if (previous?.isLoading == true && next.isLoading == false) {
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
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Placeholder for Sparkle Logo/Animation
            Icon(
              Icons.whatshot, // Represents the "flame"
              size: 80,
              color: Color(0xFFFF6B35), // Sparkle primary color
            ),
            SizedBox(height: 20),
            Text(
              'Sparkle',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1A237E), // Sparkle secondary color
              ),
            ),
            SizedBox(height: 40),
            CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
