import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/auth/auth.dart';

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

class AuthRoutes {
  static List<RouteBase> get routes => [
        GoRoute(
          path: '/login',
          name: 'login',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const LoginScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: '/register',
          name: 'register',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const RegisterScreen(),
            ),
          ),
        ),
        GoRoute(
          path: '/forgot-password',
          name: 'forgotPassword',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const ForgotPasswordScreen(),
            ),
          ),
        ),
        GoRoute(
          path: '/reset-password',
          name: 'resetPassword',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: ResetPasswordScreen(
                initialToken: state.uri.queryParameters['token'],
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/legal/terms',
          name: 'legalTerms',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy.silent,
              child: LegalDocumentScreen(documentType: 'terms'),
            ),
          ),
        ),
        GoRoute(
          path: '/legal/privacy',
          name: 'legalPrivacy',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy.silent,
              child: LegalDocumentScreen(documentType: 'privacy'),
            ),
          ),
        ),
      ];
}
