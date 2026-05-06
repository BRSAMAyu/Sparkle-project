import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/auth/auth.dart';

class AuthRoutes {
  static List<RouteBase> get routes => [
        GoRoute(
          path: '/login',
          name: 'login',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const LoginScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: '/register',
          name: 'register',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const RegisterScreen(),
          ),
        ),
        GoRoute(
          path: '/forgot-password',
          name: 'forgotPassword',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const ForgotPasswordScreen(),
          ),
        ),
        GoRoute(
          path: '/reset-password',
          name: 'resetPassword',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: ResetPasswordScreen(
              initialToken: state.uri.queryParameters['token'],
            ),
          ),
        ),
        GoRoute(
          path: '/legal/terms',
          name: 'legalTerms',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const LegalDocumentScreen(documentType: 'terms'),
          ),
        ),
        GoRoute(
          path: '/legal/privacy',
          name: 'legalPrivacy',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const LegalDocumentScreen(documentType: 'privacy'),
          ),
        ),
      ];
}
