import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/notification_center/data/repositories/notification_center_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// P-06：统一通知设置 —— 服务端权威、多设备一致、本地只读投影。
///
/// 断言面：
/// 1. 服务端 payload 投影（daily_cap / stimulation_mode 清洗与缺省）；
/// 2. 更新采纳**服务端响应**（不是本地 optimistic 值）——失败回滚；
/// 3. 显式同步（refresh）后，另一设备投影读到先写入的服务端状态。
class _FakeServer {
  Map<String, dynamic> serverState = <String, dynamic>{
    'enable_system': true,
    'enable_interventions': true,
    'disabled_types': <String>[],
    'notification_level': 'standard',
    'quiet_hours_enabled': false,
    'quiet_hours_start': '22:00',
    'quiet_hours_end': '08:00',
    'daily_cap': 3,
    'daily_cap_source': 'default',
    'stimulation_mode': 'auto',
  };
  Exception? nextError;
  Map<String, dynamic>? lastUpdate;

  Map<String, dynamic> get() {
    if (nextError != null) {
      throw nextError!;
    }
    return Map<String, dynamic>.of(serverState);
  }

  Map<String, dynamic> update(Map<String, dynamic> updates) {
    if (nextError != null) {
      throw nextError!;
    }
    lastUpdate = updates;
    serverState = <String, dynamic>{...serverState, ...updates};
    // 服务端契约：source 由服务端推导（显式携带 daily_cap 即视为用户设置），
    // 客户端不上报 source。
    if (updates.containsKey('daily_cap')) {
      serverState['daily_cap_source'] = 'user';
    }
    return Map<String, dynamic>.of(serverState);
  }
}

class _FakeRepository implements NotificationCenterRepository {
  _FakeRepository(this._server);

  final _FakeServer _server;

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #getPreferences) {
      return Future<Map<String, dynamic>>.value(_server.get());
    }
    if (invocation.memberName == #updatePreferences) {
      final updates =
          invocation.positionalArguments.first as Map<String, dynamic>;
      return Future<Map<String, dynamic>>.value(_server.update(updates));
    }
    return null;
  }
}

class _UnusedRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class _UnusedAuthRepository implements AuthRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class _StaticAuthNotifier extends AuthNotifier {
  _StaticAuthNotifier(AuthState initialState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = initialState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000001',
      username: 'p06_user',
      email: 'p06@example.com',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

Future<ProviderContainer> _loggedInContainer(_FakeServer server) async {
  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith(
        (ref) => _StaticAuthNotifier(
          AuthState(isAuthenticated: true, user: _buildUser()),
        ),
      ),
      notificationCenterRepositoryProvider.overrideWithValue(
        _FakeRepository(server),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('P-06 unified notification settings projection', () {
    test('model sanitizes server payload (cap bounds, mode aliases)', () {
      final settings = NotificationPreferenceSettings.fromJson({
        'daily_cap': 99,
        'daily_cap_source': 'user',
        'stimulation_mode': 'LOW',
      });

      expect(settings.dailyCap, 20, reason: 'cap 越界收敛到上限');
      expect(settings.dailyCapSource, 'user');
      expect(settings.stimulationMode, 'low', reason: '档位大小写容错');
      expect(settings.isLoaded, isTrue);
    });

    test('model falls back to server defaults when keys absent', () {
      final settings = NotificationPreferenceSettings.fromJson({
        'notification_level': 'standard',
      });

      expect(settings.dailyCap, 3);
      expect(settings.dailyCapSource, 'default');
      expect(settings.stimulationMode, 'auto');
    });

    test('toJson only sends user-set daily cap', () {
      const untouched = NotificationPreferenceSettings();
      expect(
        untouched.toJson().containsKey('daily_cap'),
        isFalse,
        reason: '基线投影不回写 cap（服务端 default 不被设备覆盖）',
      );

      final userSet = untouched.copyWith(dailyCap: 0, dailyCapSource: 'user');
      expect(
        userSet.toJson()['daily_cap'],
        0,
        reason: '0 = 用户关停，必须原样上报',
      );
    });

    test('zero cap projects user-off state', () {
      final settings = NotificationPreferenceSettings.fromJson({
        'daily_cap': 0,
        'daily_cap_source': 'user',
      });
      expect(settings.dailyCap, 0, reason: '关停投影不被清洗成缺省值');
    });

    testWidgets(
        'update adopts server response and another device refresh converges',
        (tester) async {
      final server = _FakeServer();
      final container = await _loggedInContainer(server);

      // 设备 A：写入 cap=1 + low 档。
      await container
          .read(notificationPreferenceSettingsProvider.notifier)
          .updatePreferences(dailyCap: 1, stimulationMode: 'low');
      expect(server.lastUpdate?['daily_cap'], 1);
      expect(server.lastUpdate?['stimulation_mode'], 'low');
      final deviceA = container.read(notificationPreferenceSettingsProvider);
      expect(deviceA.dailyCap, 1);
      expect(deviceA.stimulationMode, 'low');

      // 设备 B（同一服务端状态的另一个投影）：显式同步后读到 A 的写入。
      await container
          .read(notificationPreferenceSettingsProvider.notifier)
          .refresh();
      final deviceB = container.read(notificationPreferenceSettingsProvider);
      expect(deviceB.dailyCap, 1);
      expect(deviceB.dailyCapSource, 'user');
      expect(deviceB.stimulationMode, 'low');
    });

    testWidgets('failed update rolls back to previous projection',
        (tester) async {
      final server = _FakeServer();
      final container = await _loggedInContainer(server);
      final notifier = container
          .read(notificationPreferenceSettingsProvider.notifier);
      await notifier.updatePreferences(dailyCap: 2);
      final before = container.read(notificationPreferenceSettingsProvider);

      server.nextError = Exception('network down');
      await expectLater(
        notifier.updatePreferences(dailyCap: 5),
        throwsA(isA<Exception>()),
      );

      expect(
        container.read(notificationPreferenceSettingsProvider).dailyCap,
        before.dailyCap,
        reason: '失败回滚：本地不残留 optimistic 值（只读投影语义）',
      );
    });
  });
}
