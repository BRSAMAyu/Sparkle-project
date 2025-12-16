import 'package:animations/animations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/screens/splash/splash_screen.dart';
import 'package:sparkle/presentation/screens/auth/login_screen.dart';
import 'package:sparkle/presentation/screens/auth/register_screen.dart';
import 'package:sparkle/presentation/screens/home/home_screen.dart';
import 'package:sparkle/presentation/screens/task/task_list_screen.dart';
import 'package:sparkle/presentation/screens/task/task_detail_screen.dart';
import 'package:sparkle/presentation/screens/task/task_execution_screen.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';
import 'package:sparkle/presentation/screens/plan/sprint_screen.dart';
import 'package:sparkle/presentation/screens/plan/growth_screen.dart';
import 'package:sparkle/presentation/screens/profile/profile_screen.dart';

/// Router configuration provider
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/',
    debugLogDiagnostics: true,
    redirect: (context, state) {
      final isAuthenticated = authState.isAuthenticated;
      final isLoading = authState.isLoading;
      final isOnSplash = state.uri.path == '/';
      final isOnAuth = state.uri.path == '/login' || state.uri.path == '/register';

      // Still loading authentication state
      if (isLoading) {
        return isOnSplash ? null : '/';
      }

      // Not authenticated and not on auth pages
      if (!isAuthenticated && !isOnAuth) {
        return '/login';
      }

      // Authenticated but on auth pages or splash
      if (isAuthenticated && (isOnAuth || isOnSplash)) {
        return '/home';
      }

      return null; // No redirect needed
    },
    routes: [
      // Splash Screen
      GoRoute(
        path: '/',
        name: 'splash',
        builder: (context, state) => const SplashScreen(),
      ),

      // Auth Routes
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        builder: (context, state) => const RegisterScreen(),
      ),

      // Home Routes
      GoRoute(
        path: '/home',
        name: 'home',
        builder: (context, state) => const HomeScreen(),
      ),

      // Task Routes
      GoRoute(
        path: '/tasks',
        name: 'tasks',
        builder: (context, state) => const TaskListScreen(),
      ),
      GoRoute(
        path: '/tasks/:id',
        name: 'taskDetail',
        pageBuilder: (context, state) {
          final taskId = state.pathParameters['id']!;
          return CustomTransitionPage(
            key: state.pageKey,
            child: TaskDetailScreen(taskId: taskId),
            transitionsBuilder: (context, animation, secondaryAnimation, child) {
              return SharedAxisTransition(
                animation: animation,
                secondaryAnimation: secondaryAnimation,
                transitionType: SharedAxisTransitionType.horizontal,
                child: child,
              );
            },
          );
        },
      ),
      GoRoute(
        path: '/tasks/:id/execute',
        name: 'taskExecution',
        pageBuilder: (context, state) {
          return CustomTransitionPage(
            key: state.pageKey,
            child: const TaskExecutionScreen(),
            transitionsBuilder: (context, animation, secondaryAnimation, child) {
              return SharedAxisTransition(
                animation: animation,
                secondaryAnimation: secondaryAnimation,
                transitionType: SharedAxisTransitionType.scaled,
                child: child,
              );
            },
          );
        },
      ),

      // Chat Routes
      GoRoute(
        path: '/chat',
        name: 'chat',
        pageBuilder: (context, state) {
          return CustomTransitionPage(
            key: state.pageKey,
            child: const ChatScreen(),
            transitionsBuilder: (context, animation, secondaryAnimation, child) {
              return FadeThroughTransition(
                animation: animation,
                secondaryAnimation: secondaryAnimation,
                child: child,
              );
            },
          );
        },
      ),

      // Plan Routes
      GoRoute(
        path: '/sprint',
        name: 'sprint',
        builder: (context, state) => const SprintScreen(),
      ),
      GoRoute(
        path: '/growth',
        name: 'growth',
        builder: (context, state) => const GrowthScreen(),
      ),

      // Profile Routes
      GoRoute(
        path: '/profile',
        name: 'profile',
        builder: (context, state) => const ProfileScreen(),
      ),
    ],
  );
});