import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_settings_screen.dart';
import 'package:sparkle/features/user/presentation/screens/account_security_screen.dart';
import 'package:sparkle/features/user/presentation/screens/admin_operations_screen.dart';
import 'package:sparkle/features/user/presentation/screens/delete_account_screen.dart';
import 'package:sparkle/features/user/presentation/screens/edit_profile_screen.dart';
import 'package:sparkle/features/user/presentation/screens/guest_upgrade_screen.dart';
import 'package:sparkle/features/user/presentation/screens/learning_mode_screen.dart';
import 'package:sparkle/features/user/presentation/screens/password_reset_screen.dart';
import 'package:sparkle/features/user/presentation/screens/persona_onboarding_screen.dart';
import 'package:sparkle/features/user/presentation/screens/poster_studio_screen.dart';
import 'package:sparkle/features/user/presentation/screens/security_log_screen.dart';
import 'package:sparkle/features/user/presentation/screens/session_management_screen.dart';
import 'package:sparkle/features/user/presentation/screens/social_accounts_screen.dart';
import 'package:sparkle/features/user/presentation/screens/sync_center_screen.dart';
import 'package:sparkle/features/user/presentation/screens/system_updates_screen.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import 'package:sparkle/features/user/presentation/screens/user_persona_screen.dart';

class UserRoutes {
  static const String profile = '/profile';
  static const String personaOnboarding = '/onboarding/persona';
  static const String editProfile = '/profile/edit';
  static const String settings = '/profile/settings';
  static const String persona = '/profile/persona';
  static const String posterStudio = '/profile/posters';
  static const String systemUpdates = '/profile/system-updates';
  static const String passwordReset = '/profile/password-reset';
  static const String memorySettings = '/profile/memory-settings';
  static const String syncCenter = '/profile/sync-center';
  static const String socialAccounts = '/profile/social-accounts';
  static const String sessionManagement = '/profile/sessions';
  static const String securityLog = '/profile/security-log';
  static const String accountSecurity = '/profile/account-security';
  static const String deleteAccount = '/profile/delete-account';
  static const String guestUpgrade = '/profile/upgrade-guest';
  static const String adminOperations = '/profile/admin-operations';

  static void popOrGo(BuildContext context, {required String fallback}) {
    final navigator = Navigator.of(context);
    if (navigator.canPop()) {
      context.pop();
      return;
    }
    context.go(fallback);
  }

  static void popOrGoProfile(
    BuildContext context, {
    String fallback = profile,
  }) {
    popOrGo(context, fallback: fallback);
  }

  static List<RouteBase> get routes => [
        GoRoute(
          path: editProfile,
          name: 'editProfile',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const EditProfileScreen(),
            ),
          ),
        ),
        GoRoute(
          path: settings,
          name: 'profileSettings',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const UnifiedSettingsScreen(),
            ),
          ),
        ),
        GoRoute(
          path: posterStudio,
          name: 'posterStudio',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const PosterStudioScreen(),
            ),
          ),
        ),
        GoRoute(
          path: persona,
          name: 'profilePersona',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: UserPersonaScreen(
                initialOverrideKey: state.uri.queryParameters['override'],
              ),
            ),
          ),
        ),
        GoRoute(
          path: systemUpdates,
          name: 'systemUpdates',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const SystemUpdatesScreen(),
            ),
          ),
        ),
        GoRoute(
          path: passwordReset,
          name: 'passwordReset',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const PasswordResetScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: memorySettings,
          name: 'profileMemorySettings',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const MemorySettingsScreen(),
          ),
        ),
        GoRoute(
          path: syncCenter,
          name: 'syncCenter',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SyncCenterScreen(),
          ),
        ),
        GoRoute(
          path: socialAccounts,
          name: 'socialAccounts',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SocialAccountsScreen(),
          ),
        ),
        GoRoute(
          path: sessionManagement,
          name: 'sessionManagement',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SessionManagementScreen(),
          ),
        ),
        GoRoute(
          path: securityLog,
          name: 'securityLog',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SecurityLogScreen(),
          ),
        ),
        GoRoute(
          path: accountSecurity,
          name: 'accountSecurity',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const AccountSecurityScreen(),
          ),
        ),
        GoRoute(
          path: deleteAccount,
          name: 'deleteAccount',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const DeleteAccountScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: adminOperations,
          name: 'adminOperations',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const AdminOperationsScreen(),
            ),
          ),
        ),
        GoRoute(
          path: guestUpgrade,
          name: 'guestUpgrade',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const GuestUpgradeScreen(),
            ),
          ),
        ),
        GoRoute(
          path: '/settings/learning-mode',
          name: 'learningMode',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.profile,
              ),
              child: const LearningModeScreen(),
            ),
          ),
        ),
        GoRoute(
          path: personaOnboarding,
          name: 'personaOnboarding',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const PersonaOnboardingScreen(),
          ),
        ),
        // Add more user routes as needed
      ];
}
