import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/guest_conversion_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_conversion_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('GuestConversionController / guestConversionVisibleProvider（N40）', () {
    test('访客价值信号触发：记录后派生可见（安全窗口默认成立）', () async {
      final container = await _buildContainer(isGuest: true);

      expect(
        container.read(guestConversionVisibleProvider),
        isFalse,
        reason: '无价值信号前，任何访客都不被转化请求打扰',
      );

      await container
          .read(guestConversionControllerProvider.notifier)
          .recordValueSignal(GuestValueSignal.firstTaskCompleted);

      expect(container.read(guestConversionVisibleProvider), isTrue);
    });

    test('克制红线：进行中任务（inProgress/stuck）不弹，任务结束才可见', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final inProgressTask = _buildTask(TaskStatus.inProgress);

      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          authProvider.overrideWith((ref) => _StaticGuestAuthNotifier()),
          activeTaskProvider.overrideWith((ref) => inProgressTask),
        ],
      );
      addTearDown(container.dispose);

      await container
          .read(guestConversionControllerProvider.notifier)
          .recordValueSignal(GuestValueSignal.firstTaskCompleted);

      expect(
        container.read(guestConversionVisibleProvider),
        isFalse,
        reason: '价值动作当下用户仍在任务流程内，卡不得出现',
      );

      // 任务结束（activeTask 清空）：回到 home 安全窗口后可见
      container.read(activeTaskProvider.notifier).state = null;
      expect(container.read(guestConversionVisibleProvider), isTrue);

      // stuck 同样视为进行中
      container.read(activeTaskProvider.notifier).state =
          _buildTask(TaskStatus.stuck);
      expect(container.read(guestConversionVisibleProvider), isFalse);
    });

    test('一次性标记：点掉后本会话二次价值信号不再弹；注册用户永不可见',
        () async {
      final container = await _buildContainer(isGuest: true);
      final controller = container.read(guestConversionControllerProvider.notifier);

      await controller.recordValueSignal(GuestValueSignal.firstTaskCompleted);
      expect(container.read(guestConversionVisibleProvider), isTrue);

      // 点掉：本会话硬关 + 持久挂起
      await controller.dismissUntilNextValueSignal();
      expect(container.read(guestConversionVisibleProvider), isFalse);

      // 同会话二次价值信号：仍不弹（同会话最多一次）
      await controller.recordValueSignal(GuestValueSignal.firstDiagnosisOutput);
      expect(
        container.read(guestConversionVisibleProvider),
        isFalse,
        reason: '点掉后即使来了新价值信号，本会话内不再出现',
      );

      // 点击注册 CTA 同样是本会话硬关
      final container2 = await _buildContainer(isGuest: true);
      final controller2 =
          container2.read(guestConversionControllerProvider.notifier);
      await controller2.recordValueSignal(GuestValueSignal.firstTaskCompleted);
      expect(container2.read(guestConversionVisibleProvider), isTrue);
      controller2.markConsumedByRegister();
      expect(container2.read(guestConversionVisibleProvider), isFalse);
    });

    test('注册用户：价值信号 no-op，转化钩子零出现（免费闭环零变化）', () async {
      final container = await _buildContainer(isGuest: false);

      await container
          .read(guestConversionControllerProvider.notifier)
          .recordValueSignal(GuestValueSignal.firstTaskCompleted);

      final state = container.read(guestConversionControllerProvider);
      expect(state.signalCount, 0);
      expect(container.read(guestConversionVisibleProvider), isFalse);
    });

    test('持久挂起跨会话生效；下个会话的新价值信号重新武装', () async {
      SharedPreferences.setMockInitialValues({
        'guest_conversion_signal_count': 1,
        'guest_conversion_dismissed_until_next_signal': true,
      });
      final prefs = await SharedPreferences.getInstance();
      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          authProvider.overrideWith((ref) => _StaticGuestAuthNotifier()),
        ],
      );
      addTearDown(container.dispose);

      // 新会话（控制器重建）：历史挂起仍在，不弹
      expect(container.read(guestConversionVisibleProvider), isFalse);

      // 新价值信号：清除挂起，重新正当邀请
      await container
          .read(guestConversionControllerProvider.notifier)
          .recordValueSignal(GuestValueSignal.firstMemoryReferenced);
      expect(container.read(guestConversionVisibleProvider), isTrue);
    });
  });
}

Future<ProviderContainer> _buildContainer({required bool isGuest}) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  final container = ProviderContainer(
    overrides: [
      sharedPreferencesProvider.overrideWithValue(prefs),
      authProvider.overrideWith(
        (ref) => isGuest
            ? _StaticGuestAuthNotifier()
            : _StaticRegisteredAuthNotifier(),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

TaskModel _buildTask(TaskStatus status) {
  final now = DateTime(2026, 9, 22);
  return TaskModel(
    id: 'task-1',
    userId: 'user-1',
    title: '完成一次冲刺任务',
    type: TaskType.learning,
    tags: const ['test'],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 2,
    status: status,
    priority: 1,
    createdAt: now,
    updatedAt: now,
  );
}

UserModel _buildUser({String? registrationSource}) {
  final now = DateTime(2026, 9, 22);
  return UserModel(
    id: '00000000-0000-0000-0000-000000000001',
    username: 'guest_test_user',
    email: 'guest@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    registrationSource: registrationSource,
    createdAt: now,
    updatedAt: now,
  );
}

class _StaticGuestAuthNotifier extends AuthNotifier {
  _StaticGuestAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(registrationSource: 'guest'),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _StaticRegisteredAuthNotifier extends AuthNotifier {
  _StaticRegisteredAuthNotifier()
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(registrationSource: 'email'),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_NoopApiClient(), _MapTokenStorage());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MapTokenStorage implements TokenStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async => _values[key] = value;

  @override
  Future<void> delete(String key) async => _values.remove(key);
}
