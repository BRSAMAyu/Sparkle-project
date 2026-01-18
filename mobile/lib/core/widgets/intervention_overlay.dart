import 'dart:ui';

import 'package:flutter/material.dart';

class InterventionOverlayPayload {
  final String title;
  final String body;
  final String primaryActionText;
  final String? secondaryActionText;

  InterventionOverlayPayload({
    required this.title,
    required this.body,
    required this.primaryActionText,
    this.secondaryActionText,
  });
}

class InterventionOverlay extends StatelessWidget {
  final InterventionOverlayPayload payload;
  final VoidCallback onPrimary;
  final VoidCallback onSecondary;
  final VoidCallback onDismiss;

  const InterventionOverlay({
    super.key,
    required this.payload,
    required this.onPrimary,
    required this.onSecondary,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onDismiss,
      child: Container(
        color: Colors.black.withOpacity(0.35),
        child: Center(
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 28),
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.white.withOpacity(0.15),
                    Colors.white.withOpacity(0.05),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.white.withOpacity(0.2),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.2),
                    blurRadius: 24,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              child: GestureDetector(
                onTap: () {},
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      payload.title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      payload.body,
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            height: 1.4,
                          ),
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: onPrimary,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      child: Text(payload.primaryActionText),
                    ),
                    if (payload.secondaryActionText != null) ...[
                      const SizedBox(height: 10),
                      TextButton(
                        onPressed: onSecondary,
                        child: Text(payload.secondaryActionText!),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
