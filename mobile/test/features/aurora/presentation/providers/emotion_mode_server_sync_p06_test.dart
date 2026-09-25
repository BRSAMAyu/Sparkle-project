import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/aurora/presentation/providers/emotion_state_provider.dart';

/// P-06 多设备一致性：Aurora 刺激档（aurora_stimulation_mode）以服务端为
/// 权威——本地缓存只是首帧投影，加载后显式拉取服务端档位并采纳。
class _FakeApiClient implements ApiClient {
  _FakeApiClient(this.serverPrefs);

  Map<String, dynamic> serverPrefs;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path == ApiEndpoints.auroraPreferences) {
      return Response<T>(
        data: serverPrefs as T,
        requestOptions: RequestOptions(path: path),
      );
    }
    throw UnimplementedError(path);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('server stimulation mode overrides stale local cache on load',
      () async {
    SharedPreferences.setMockInitialValues({
      kEmotionAdaptiveModeKey: 'always_normal', // 本地缓存过期（另一设备已改 low）
    });

    final notifier = EmotionStateNotifier(
      apiClient: _FakeApiClient(<String, dynamic>{
        'preferences': <String, dynamic>{'aurora_stimulation_mode': 'low'},
      }),
    );
    // _loadMode 为 fire-and-forget；等待微任务队列排空（本地读 + 服务端拉取）。
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);

    expect(
        notifier.state.mode,
        EmotionAdaptiveMode.alwaysLow,
        reason: '服务端权威：本地过期缓存被服务端档位收敛',
      );
    final stored = await SharedPreferences.getInstance();
    expect(
      stored.getString(kEmotionAdaptiveModeKey),
      'always_low',
      reason: '投影收敛后回写本地缓存（下次首帧一致）',
    );
  });

  test('server failure keeps local projection (honest, no fabricated mode)',
      () async {
    SharedPreferences.setMockInitialValues({
      kEmotionAdaptiveModeKey: 'always_low',
    });

    final notifier = EmotionStateNotifier(
      apiClient: _FakeApiClient(<String, dynamic>{}),
    );
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);

    expect(
        notifier.state.mode,
        EmotionAdaptiveMode.alwaysLow,
        reason: '服务端 payload 缺档位键 → 不做任何改写',
      );
  });
}
