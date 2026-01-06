import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/user.dart';
import 'package:sparkle/presentation/screens/cognitive/curiosity_capsule_screen.dart';
import 'package:sparkle/presentation/screens/cognitive/pattern_list_screen.dart';
import 'package:sparkle/presentation/screens/community/community_main_screen.dart';
import 'package:sparkle/presentation/screens/community/create_group_screen.dart';
import 'package:sparkle/presentation/screens/community/friends_screen.dart';
import 'package:sparkle/presentation/screens/community/group_detail_screen.dart';
import 'package:sparkle/presentation/screens/community/group_list_screen.dart';
import 'package:sparkle/presentation/screens/community/group_search_screen.dart';
import 'package:sparkle/presentation/screens/community/group_tasks_screen.dart';
import 'package:sparkle/presentation/screens/focus/focus_main_screen.dart';
import 'package:sparkle/presentation/screens/focus/mindfulness_mode_screen.dart';
import 'package:sparkle/presentation/screens/home/home_screen.dart';
import 'package:sparkle/presentation/screens/insights/learning_forecast_screen.dart';
import 'package:sparkle/presentation/screens/plan/growth_screen.dart';
import 'package:sparkle/presentation/screens/plan/plan_create_screen.dart';
import 'package:sparkle/presentation/screens/plan/plan_detail_screen.dart';
import 'package:sparkle/presentation/screens/plan/plan_edit_screen.dart';
import 'package:sparkle/presentation/screens/plan/sprint_screen.dart';
import 'package:sparkle/presentation/screens/splash/splash_screen.dart';
import 'package:sparkle/presentation/screens/stats/calendar_stats_screen.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Helper to build pages with transitions
Page<dynamic> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionsBuilder: (context, animation, secondaryAnimation, child) =>
          SharedAxisTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        transitionType: type,
        child: child,
      ),
    );

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
      // Splash Screen
      GoRoute(
        path: '/',
        name: 'splash',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SplashScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),

      // Auth Routes
      GoRoute(
        path: '/login',
        name: 'login',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const LoginScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const RegisterScreen(),
        ),
      ),

      // Home Routes
      GoRoute(
        path: '/home',
        name: 'home',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const HomeScreen(),
          type: SharedAxisTransitionType.scaled, // Fade/Scale in for Home
        ),
      ),

      // Task Routes
      ...TaskRoutes.routes,

      // Plan Routes
      GoRoute(
        path: '/plans/new',
        name: 'createPlan',
        pageBuilder: (context, state) {
          final planType = state.uri.queryParameters['type'];
          return _buildTransitionPage(
            state: state,
            child: PlanCreateScreen(planType: planType),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),
      GoRoute(
        path: '/plans/:id',
        name: 'planDetail',
        pageBuilder: (context, state) {
          final planId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: PlanDetailScreen(planId: planId),
          );
        },
      ),
      GoRoute(
        path: '/plans/:id/edit',
        name: 'editPlan',
        pageBuilder: (context, state) {
          final planId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: PlanEditScreen(planId: planId),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),

      // Insights Routes
      GoRoute(
        path: '/learning/forecast',
        name: 'learningForecast',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const LearningForecastScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),

      // Focus Routes
      GoRoute(
        path: '/focus',
        name: 'focus',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const FocusMainScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
      GoRoute(
        path: '/focus/mindfulness',
        name: 'mindfulness',
        pageBuilder: (context, state) {
          final task = state.extra as TaskModel;
          return _buildTransitionPage(
            state: state,
            child: MindfulnessModeScreen(task: task),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),

      // Calendar Stats Route
      GoRoute(
        path: '/calendar-stats',
        name: 'calendarStats',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const CalendarStatsScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),

      // Chat Routes
      ...ChatRoutes.routes,

      // Error Book Routes
      GoRoute(
        path: '/errors',
        name: 'errors',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const ErrorListScreen(),
        ),
      ),
      GoRoute(
        path: '/errors/new',
        name: 'addError',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const AddErrorScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
      GoRoute(
        path: '/errors/:id',
        name: 'errorDetail',
        pageBuilder: (context, state) {
          final errorId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: ErrorDetailScreen(errorId: errorId),
          );
        },
      ),
      GoRoute(
        path: '/review',
        name: 'review',
        pageBuilder: (context, state) {
          final modeCode = state.uri.queryParameters['mode'] ?? 'today';
          final subjectCode = state.uri.queryParameters['subject'];

          final mode = ReviewMode.values.firstWhere(
            (m) => m.code == modeCode,
            orElse: () => ReviewMode.today,
          );

          return _buildTransitionPage(
            state: state,
            child: ReviewScreen(mode: mode, subjectCode: subjectCode),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),

      // Plan Routes
      GoRoute(
        path:
            '/plans', // Alias for sprint for now or a main plan screen if created
        name: 'plans',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SprintScreen(),
        ),
      ),
      GoRoute(
        path: '/sprint',
        name: 'sprint',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SprintScreen(),
        ),
      ),
      GoRoute(
        path: '/growth',
        name: 'growth',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GrowthScreen(),
        ),
      ),

      // Profile Routes
      GoRoute(
        path: '/community',
        builder: (context, state) => const CommunityMainScreen(),
      ),
      GoRoute(
        path: '/settings/learning-mode',
        name: 'learningMode',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const LearningModeScreen(),
        ),
      ),

      // Galaxy Routes
      ...GalaxyRoutes.routes,

      // Cognitive Routes
      GoRoute(
        path: '/cognitive/patterns',
        name: 'patternList',
        pageBuilder: (context, state) {
          final highlightId = state.uri.queryParameters['highlight'];
          return _buildTransitionPage(
            state: state,
            child: PatternListScreen(highlightId: highlightId),
          );
        },
      ),
      GoRoute(
        path: '/curiosity-capsule',
        name: 'curiosityCapsule',
        pageBuilder: (context, state) {
          final highlightId = state.uri.queryParameters['highlight'];
          return _buildTransitionPage(
            state: state,
            child: CuriosityCapsuleScreen(highlightId: highlightId),
          );
        },
      ),

      // Community Routes
      GoRoute(
        path: '/community/friends',
        name: 'friends',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const FriendsScreen(),
        ),
      ),
      GoRoute(
        path: '/community/groups',
        name: 'groups',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GroupListScreen(),
        ),
      ),
      GoRoute(
        path: '/community/groups/search',
        name: 'groupSearch',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GroupSearchScreen(),
        ),
      ),
      GoRoute(
        path: '/community/groups/create',
        name: 'createGroup',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const CreateGroupScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
      GoRoute(
        path: '/community/groups/:id',
        name: 'groupDetail',
        pageBuilder: (context, state) {
          final groupId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: GroupDetailScreen(groupId: groupId),
          );
        },
      ),
      GoRoute(
        path: '/community/groups/:id/tasks',
        name: 'groupTasks',
        pageBuilder: (context, state) {
          final groupId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: GroupTasksScreen(groupId: groupId),
          );
        },
      ),
    ],
  );
});
