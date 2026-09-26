import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/release_flags_provider.dart';

/// V3-FIX-190：/release-flags 契约拉取在测试内快速失败（无网络）
class _ThrowingApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('no network in release flags test');
}

void main() {
  test('contract json decodes frozen five-key contract, defaults fail-closed',
      () {
    final flags = ReleaseFlags.fromContractJson(const <String, dynamic>{
      'shop': true,
      'photon_transfer': false,
      'public_leaderboards': true,
      'public_community': false,
      'visual_elements': true,
      // 未知键忽略（契约前向兼容面）
      'future_flag': true,
    });

    expect(flags.shop, isTrue);
    expect(flags.photonTransfer, isFalse);
    expect(flags.publicLeaderboards, isTrue);
    expect(flags.publicCommunity, isFalse);
    expect(flags.visualElements, isTrue);

    // 缺键 → false（fail-closed，与 backend RELEASE_ENABLE_* 默认同向）
    const empty = ReleaseFlags();
    expect(empty.visualElements, isFalse);
    expect(ReleaseFlags.fromContractJson(const {}).visualElements, isFalse);
    // 非布尔真值不开启（严格 == true 解码）
    expect(
      ReleaseFlags.fromContractJson(
        const {'visual_elements': 'true'},
      ).visualElements,
      isFalse,
    );
  });

  test('ensureLoaded fails closed and retries after failure', () async {
    final container = ProviderContainer(overrides: [
      apiClientProvider.overrideWithValue(_ThrowingApiClient()),
    ]);
    addTearDown(container.dispose);

    final notifier = container.read(releaseFlagsProvider.notifier);
    expect(
      await notifier.ensureLoaded(),
      const ReleaseFlags(),
      reason: '拉取失败保持 fail-closed 全关',
    );

    // 失败后允许重试：换成功路径需重进 provider——这里验证失败态可重复调用
    expect(await notifier.ensureLoaded(), const ReleaseFlags());
  });

  test(
    'seed pins flags for tests (flag-on path)',
    () async {
      final container = ProviderContainer(overrides: [
        apiClientProvider.overrideWithValue(_ThrowingApiClient()),
        releaseFlagsProvider.overrideWith(
          (ref) => ReleaseFlagsNotifier(_ThrowingApiClient())
            ..seed(
              const ReleaseFlags(
                visualElements: true,
                shop: true,
              ),
            ),
        ),
      ],);
      addTearDown(container.dispose);

      final flags =
          await container.read(releaseFlagsProvider.notifier).ensureLoaded();
      expect(flags.visualElements, isTrue);
      expect(flags.shop, isTrue);
    },
  );
}
