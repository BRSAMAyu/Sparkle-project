import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sensory_navigation_observer.dart';
import 'package:sparkle/core/navigation/shell_navigation.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/calendar/calendar.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/cognitive/cognitive.dart';
import 'package:sparkle/features/community/community.dart';
import 'package:sparkle/features/documents/documents.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/features/focus/focus.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/goal/goal.dart';
import 'package:sparkle/features/home/home.dart';
import 'package:sparkle/features/insights/insights.dart';
import 'package:sparkle/features/memory/memory.dart';
import 'package:sparkle/features/notification_center/notification_center.dart';
import 'package:sparkle/features/openclaw/openclaw.dart';
import 'package:sparkle/features/photon/photon_routes.dart';
import 'package:sparkle/features/plan/plan.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/reviews/reviews.dart';
import 'package:sparkle/features/seed_library/seed_library_routes.dart';
import 'package:sparkle/features/shop/shop_routes.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/splash/splash.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/theater/theater_routes.dart';
import 'package:sparkle/features/tools/tools.dart';
import 'package:sparkle/features/translation/translation.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/user.dart';
import 'package:sparkle/features/visual_elements/visual_elements_routes.dart';

/// Router configuration provider
final routerProvider = Provider<GoRouter>((ref) {
  final navigationObserver = SensoryNavigationObserver();

  final routerRefreshNotifier = ValueNotifier<int>(0);

  ref
    ..listen<AuthState>(
      authProvider,
      (_, next) {
        routerRefreshNotifier.value++;
      },
    )
    ..listen<bool>(
      onboardingCompletedProvider,
      (_, __) {
        routerRefreshNotifier.value++;
      },
    )
    ..onDispose(routerRefreshNotifier.dispose);

  return GoRouter(
    navigatorKey: navigatorKey, // Set the global navigator key
    initialLocation: '/',
    debugLogDiagnostics: true,
    observers: [navigationObserver],
    refreshListenable: routerRefreshNotifier,
    redirect: (context, state) {
      final authState = ref.read(authProvider);

      final isAuthenticated = authState.isAuthenticated;
      final isLoading = authState.isLoading;
      final isOnSplash = state.uri.path == '/';
      final publicAuthPaths = {
        '/login',
        '/register',
        '/forgot-password',
        '/reset-password',
        '/legal/terms',
        '/legal/privacy',
      };
      final isOnAuth = publicAuthPaths.contains(state.uri.path);
      final isOnPersonaOnboarding =
          state.uri.path == UserRoutes.personaOnboarding ||
              state.uri.path.startsWith('${UserRoutes.personaOnboarding}/');
      final isOnModelingChat =
          state.uri.path == UserRoutes.modelingChat ||
              state.uri.path.startsWith('${UserRoutes.modelingChat}/');
      final onboardingCompleted = ref.read(onboardingCompletedProvider);
      final isGuestUser = authState.user?.registrationSource == 'guest';

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

      if (isAuthenticated &&
          !isGuestUser &&
          !onboardingCompleted &&
          !isOnPersonaOnboarding &&
          !isOnModelingChat) {
        return UserRoutes.personaOnboarding;
      }

      if (isAuthenticated &&
          (onboardingCompleted || isGuestUser) &&
          isOnPersonaOnboarding) {
        return '/home';
      }

      return null; // No redirect needed
    },
    routes: [
      // Root shell route for tab navigation
      StatefulShellRoute.indexedStack(
        pageBuilder: (context, state, navigationShell) =>
            buildColdStartTransitionPage(
          state: state,
          child: MainNavigationShell(
            navigationShell: navigationShell,
          ),
        ),
        branches: [
          // Branch 0: Home / Dashboard
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/home',
                pageBuilder: (context, state) => NoTransitionPage<void>(
                  key: state.pageKey,
                  child: const SceneAudioScope(
                    policy: SceneAudioPolicy(
                      track: BgmTrack.dashboard,
                    ),
                    child: DashboardScreen(),
                  ),
                ),
              ),
              ...PlanRoutes.shellRoutes,
            ],
          ),
          // Branch 1: Galaxy
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/galaxy',
                pageBuilder: (context, state) => NoTransitionPage<void>(
                  key: state.pageKey,
                  child: SceneAudioScope(
                    policy: ExperienceProfiles.focusImmersive.audioPolicy(
                      trackOverride: BgmTrack.galaxy,
                    ),
                    child: GalaxyScreen(
                      initialFocusNodeId:
                          state.uri.queryParameters['focus_node_id'],
                      initialMasteryDelta: double.tryParse(
                        state.uri.queryParameters['mastery_delta'] ?? '',
                      ),
                      initialPackId: state.uri.queryParameters['pack_id'],
                    ),
                  ),
                ),
              ),
            ],
          ),
          // Branch 2: Chat
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/chat',
                pageBuilder: (context, state) {
                  final extra = state.extra;
                  final extraMap = extra is Map<String, dynamic> ? extra : null;
                  final initialAiMessage =
                      extraMap?['initial_ai_message'] as String?;
                  final initialUserMessage =
                      extraMap?['initial_user_message'] as String?;
                  final fromModelingComplete =
                      (extraMap?['from_modeling_complete'] as bool?) ?? false;
                  final modelingOutput =
                      extraMap?['modeling_output'] as Map<String, dynamic>?;
                  final extraInitialContext =
                      extraMap?['initial_context'] is Map
                          ? Map<String, dynamic>.from(
                              extraMap!['initial_context'] as Map,
                            )
                          : null;
                  final auroraCorrection = extraMap?['aurora_correction'] is Map
                      ? Map<String, dynamic>.from(
                          extraMap!['aurora_correction'] as Map,
                        )
                      : null;
                  final initialContext = <String, dynamic>{
                    ...?extraInitialContext,
                    if (auroraCorrection != null)
                      'aurora_correction': auroraCorrection,
                    if (state.uri.queryParameters['review_node'] != null)
                      'review_node': state.uri.queryParameters['review_node'],
                    if (state.uri.queryParameters['node_label'] != null)
                      'node_label': state.uri.queryParameters['node_label'],
                    if (double.tryParse(
                          state.uri.queryParameters['mastery'] ?? '',
                        ) !=
                        null)
                      'mastery': double.parse(
                        state.uri.queryParameters['mastery']!,
                      ),
                    if (int.tryParse(
                          state.uri.queryParameters['study_count'] ?? '',
                        ) !=
                        null)
                      'study_count': int.parse(
                        state.uri.queryParameters['study_count']!,
                      ),
                    if (int.tryParse(
                          state.uri.queryParameters['related_error_count'] ??
                              '',
                        ) !=
                        null)
                      'related_error_count': int.parse(
                        state.uri.queryParameters['related_error_count']!,
                      ),
                  };
                  return buildColdStartTransitionPage(
                    state: state,
                    child: SceneAudioScope(
                      policy: ExperienceProfiles.assistantFlow.audioPolicy(),
                      child: ChatScreen(
                        initialPrompt: state.uri.queryParameters['prompt'],
                        initialChatMode: state.uri.queryParameters['chat_mode'],
                        initialConversationId:
                            state.uri.queryParameters['session_id'],
                        initialAiMessage: initialAiMessage,
                        initialUserMessage: initialUserMessage,
                        fromModelingComplete: fromModelingComplete,
                        modelingOutput: modelingOutput,
                        initialExtraContext:
                            initialContext.isEmpty ? null : initialContext,
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
          // Branch 3: Community
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/community',
                pageBuilder: (context, state) => NoTransitionPage<void>(
                  key: state.pageKey,
                  child: SceneAudioScope(
                    policy: ExperienceProfiles.socialWarm.audioPolicy(
                      trackOverride: BgmTrack.community,
                    ),
                    child: const CommunityMainScreen(),
                  ),
                ),
              ),
            ],
          ),
          // Branch 4: Profile
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                pageBuilder: (context, state) => NoTransitionPage<void>(
                  key: state.pageKey,
                  child: SceneAudioScope(
                    policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                      trackOverride: BgmTrack.profile,
                    ),
                    child: const ProfileScreen(),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
      // Splash and auth routes (at root level, outside shell)
      ...SplashRoutes.routes,
      ...AuthRoutes.routes,
      // Other feature routes (at root level, outside shell)
      ...OpenClawRoutes.routes,
      ...HomeRoutes.routes,
      ...TaskRoutes.routes,
      ...PlanRoutes.routes,
      ...InsightsRoutes.routes,
      ...SimulationRoutes.routes,
      ...TheaterRoutes.routes,
      ...ReportRoutes.routes,
      ...FocusRoutes.routes,
      ...CalendarRoutes.routes,
      ...ChatRoutes.routes,
      ...ErrorBookRoutes.routes,
      ...ReviewRoutes.routes,
      ...GalaxyRoutes.routes,
      ...GoalRoutes.routes,
      ...CognitiveRoutes.routes,
      ...CommunityRoutes.routes,
      ...DocumentLibraryRoutes.routes,
      ...UserRoutes.routes,
      ...MemoryRoutes.routes,
      ...AchievementRoutes.routes,
      ...NotificationCenterRoutes.routes,
      ...PhotonRoutes.routes,
      ...TranslationRoutes.routes,
      ...SeedLibraryRoutes.routes,
      ...ToolsRoutes.routes,
      ...VisualElementsRoutes.routes,
      ...ShopRoutes.routes,
    ],
  );
});
