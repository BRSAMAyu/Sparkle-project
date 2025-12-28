import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Redirection logic moved to GoRouter's redirect function in routes.dart
    // This component now only serves as a visual placeholder during initialization.

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
