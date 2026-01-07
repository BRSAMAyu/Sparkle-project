import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/community/community.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/features/focus/focus.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/plan/plan.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/user.dart';
import 'package:sparkle/features/calendar/calendar.dart';
import 'package:sparkle/features/cognitive/cognitive.dart';
import 'package:sparkle/features/home/home.dart';
import 'package:sparkle/features/insights/insights.dart';
import 'package:sparkle/features/splash/splash.dart';

/// Router configuration provider
final routerProvider = Provider<GoRouter>((ref) {
  // Create a notifier to sync auth state with GoRouter without rebuilding the router itself
  final authStateNotifier = ValueNotifier<AuthState>(ref.read(authProvider));

  // Update the notifier when auth state changes
  ref
    ..listen<AuthState>(
      authProvider,
      (_, next) {
        authStateNotifier.value = next;
      },
    )
    // Dispose the notifier when the provider is disposed
    ..onDispose(authStateNotifier.dispose);

  return GoRouter(
    navigatorKey: navigatorKey, // Set the global navigator key
    initialLocation: '/',
    debugLogDiagnostics: true,
    refreshListenable: authStateNotifier,
    redirect: (context, state) {
      // Access the latest value from the notifier
      final authState = authStateNotifier.value;

      final isAuthenticated = authState.isAuthenticated;
      final isLoading = authState.isLoading;
      final isOnSplash = state.uri.path == '/';
      final isOnAuth =
          state.uri.path == '/login' || state.uri.path == '/register';

      // Still loading authentication state
      if (isLoading) {
        // If we are already on an auth page, let the page handle the loading UI
        if (isOnAuth) return null;

        return isOnSplash ? null : '/';
      }

      // Not authenticated and trying to access protected routes
      if (!isAuthenticated && !isOnAuth) {
        return '/login';
      }

      // Authenticated but trying to access auth pages or splash
      if (isAuthenticated && (isOnAuth || isOnSplash)) {
        return '/home';
      }

      return null; // No redirect needed
    },
    routes: [
      ...SplashRoutes.routes,
      ...AuthRoutes.routes,
      ...HomeRoutes.routes,
      ...TaskRoutes.routes,
      ...PlanRoutes.routes,
      ...InsightsRoutes.routes,
      ...FocusRoutes.routes,
      ...CalendarRoutes.routes,
      ...ChatRoutes.routes,
      ...ErrorBookRoutes.routes,
      ...GalaxyRoutes.routes,
      ...CognitiveRoutes.routes,
      ...CommunityRoutes.routes,
      ...UserRoutes.routes,
    ],
  );
});