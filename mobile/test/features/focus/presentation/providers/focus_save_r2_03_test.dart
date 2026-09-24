import 'dart:convert';
import 'dart:ui' show Locale;

import 'package:connectivity_plus_platform_interface/connectivity_plus_platform_interface.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/focus/data/repositories/focus_repository.dart';
import 'package:sparkle/features/focus/data/services/prediction_service.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

// R2-03 regression tests: a focus session must never be reported as saved
// (offline or otherwise) when nothing was persisted, and a failed save must
// keep the recoverable snapshot instead of destroying it.

/// Stub that fails loudly if any method is actually invoked.
class _StubFocusRepository implements FocusRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not expected');
}

class _StubPredictionService implements PredictionService {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not expected');
}

class _StubTaskRepository implements TaskRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not expected');
}

class _StubEventStream implements AppEventStreamService {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not expected');
}

class _StubPredictionAttribution implements PredictionAttributionService {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not expected');
}

class _StubVisualElementRepository implements VisualElementRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not expected');
}

final Provider<Ref> _refProvider = Provider<Ref>((ref) => ref);

/// Silent connectivity platform: FocusStatistics.build() subscribes to
/// connectivity changes; provide one that never emits events in tests.
class _SilentConnectivityPlatform extends ConnectivityPlatform {
  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged =>
      const Stream<Object?>.empty() as Stream<List<ConnectivityResult>>;

  @override
  Future<List<ConnectivityResult>> checkConnectivity() async =>
      <ConnectivityResult>[ConnectivityResult.none];
}

void _mockConnectivity() {
  ConnectivityPlatform.instance = _SilentConnectivityPlatform();
}

ProviderContainer _makeContainer() => ProviderContainer(
    overrides: [
      focusRepositoryProvider.overrideWithValue(_StubFocusRepository()),
      // Prediction attribution only needs "no current user" to no-op.
      currentUserProvider.overrideWithValue(null),
    ],
  );

MindfulnessNotifier _makeMindfulnessNotifier(Ref ref) => MindfulnessNotifier(
    ref,
    _StubPredictionService(),
    _StubTaskRepository(),
    _StubEventStream(),
    _StubPredictionAttribution(),
    _StubVisualElementRepository(),
  );

Future<void> _seedActiveSessionSnapshot() async {
  // Same payload shape as MindfulnessNotifier._persistSession(): an active
  // session started one hour ago, i.e. what a previously failed save left
  // behind for recovery.
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(
    'mindfulness.active_session',
    jsonEncode(<String, dynamic>{
      'isActive': true,
      'startTime':
          DateTime.now().subtract(const Duration(hours: 1)).toIso8601String(),
      'elapsedSeconds': 3600,
      'interruptionCount': 0,
      'interruptions': <dynamic>[],
      'isDNDEnabled': false,
      'isPaused': false,
      'accumulatedPausedSeconds': 0,
      'translationRequestCount': 0,
      'lastTranslationGranularity': 'word',
    }),
  );
}

void main() {
  setUpAll(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues(<String, String>{});
    _mockConnectivity();
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
  });

  test(
      'R2-03: saveSession throws (instead of returning a fake offline-save) '
      'when the local focus repository is unavailable', () async {
    final container = _makeContainer();
    addTearDown(container.dispose);

    final notifier = container.read(focusStatisticsProvider.notifier);

    await expectLater(
      notifier.saveSession(
        startTime: DateTime.now().subtract(const Duration(minutes: 25)),
        endTime: DateTime.now(),
        durationMinutes: 25,
        focusType: 'mindfulness',
      ),
      throwsA(
        isA<StateError>().having(
          (e) => e.message,
          'message',
          contains('NOT saved'),
        ),
      ),
    );
  });

  test(
      'R2-03: mindfulness stop() keeps the persisted snapshot and stays '
      'recoverable when saving fails', () async {
    await _seedActiveSessionSnapshot();

    final container = _makeContainer();
    addTearDown(container.dispose);
    final ref = container.read(_refProvider);

    final notifier = _makeMindfulnessNotifier(ref);
    addTearDown(notifier.dispose);
    // Constructor restores the seeded snapshot.
    await Future<void>.delayed(Duration.zero);

    expect(notifier.state.isActive, isTrue,
        reason: 'session snapshot should be restored on construction',);

    final result = await notifier.stop();

    expect(result.savedLocally, isFalse,
        reason: 'nothing was persisted — must not report an offline save',);
    expect(result.message, contains('保存失败'));

    expect(notifier.state.isActive, isTrue,
        reason: 'session must stay alive so the user can retry stop()',);
    final prefs = await SharedPreferences.getInstance();
    expect(
      prefs.getString('mindfulness.active_session'),
      isNotNull,
      reason: 'the recoverable snapshot must survive a failed save',
    );
  });
}
