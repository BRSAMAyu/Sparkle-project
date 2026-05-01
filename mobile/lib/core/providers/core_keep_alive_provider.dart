import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/features/aurora/presentation/providers/aurora_preferences_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';

/// Registry of app-level providers that intentionally stay alive across tab
/// switches. These providers use Riverpod's non-autoDispose constructors,
/// which is the manual equivalent of `keepAlive: true` for this codebase.
final coreKeepAliveProvidersProvider = Provider<List<ProviderOrFamily>>(
  (ref) => [
    authProvider,
    currentUserProvider,
    profileContextProvider,
    auroraStatusProvider,
    auroraPreferencesProvider,
    chatRepositoryProvider,
    chatProvider,
    planListProvider,
    activePlanProvider,
    themeManagerProvider,
    bgmServiceProvider,
  ],
);
