import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/shell_navigation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/release_flags_provider.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

import '../../shared/i18n_test_helper.dart';

/// V3-FIX-247 · 启动期 visual-elements warm refresh 旗闸机检。
///
/// 行为裁决：MainNavigationShell._scheduleVisualElementWarmRefresh 在 shell
/// 建立后 1200ms 对空缓存发起 visualElementProvider.refresh()（/visual-elements
/// 全量 + /unlocked + /config 三发）——后端 /visual-elements 组注册级闸
/// RELEASE_ENABLE_VISUAL_ELEMENTS 默认 False→403 FEATURE_DISABLED，启动即产
/// 三发注定 403 的请求（V3-FIX-190 同族消费面，wt523 台账顺带登记）。
/// 修法范式与 FIX-190 同制：旗 off/unavailable（fail-closed）即不发网络请求
/// （短路），旗 on 照常 warm refresh（防 rollout 误伤）；缓存兜底语义
/// （isLoading/非空即跳过）保持不动。
///
/// 形制先例：mindfulness_provider_test 的 FIX-190 flags 用例（recording 仓库
/// 桩测 + seed 钉旗）× widget 泵真实 shell（主仓无 StatefulNavigationShell
/// 泵制先例，走最小 StatefulShellRoute.indexedStack 两分支挂真 shell）。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
    'flags unavailable fail-closed skips startup visual-elements warm refresh',
    (tester) async {
      final recorder = _RecordingVisualElementNotifier();
      final container = ProviderContainer(
        overrides: [
          // /release-flags 拉取面在测试内快速失败（无网络）→ fail-closed 保持关
          apiClientProvider.overrideWithValue(_ThrowingApiClient()),
          visualElementProvider.overrideWith((ref) => recorder),
        ],
      );
      addTearDown(container.dispose);

      await _pumpShell(tester, container);

      expect(
        recorder.refreshCalls,
        isEmpty,
        reason: 'release flag visual_elements off/unavailable（fail-closed）时'
            '启动期不得再发注定 403 的 /visual-elements warm refresh',
      );
    },
  );

  // 邻域守卫：旗开（visual_elements=true）时启动期 warm refresh 必须照发——
  // 短路只许关闸噪声，不许误伤 rollout 后的正常预热。
  testWidgets(
    'flag on proceeds with startup warm refresh',
    (tester) async {
      final recorder = _RecordingVisualElementNotifier();
      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(_ThrowingApiClient()),
          visualElementProvider.overrideWith((ref) => recorder),
          releaseFlagsProvider.overrideWith(
            (ref) => ReleaseFlagsNotifier(_ThrowingApiClient())
              ..seed(const ReleaseFlags(visualElements: true)),
          ),
        ],
      );
      addTearDown(container.dispose);

      await _pumpShell(tester, container);

      expect(
        recorder.refreshCalls,
        ['refresh'],
        reason: '旗开时 warm refresh 照常（rollout 后预热行为不变）',
      );
    },
  );

  // 缓存兜底语义回归：已有缓存（isLoading/非空）时旗开也不得重复刷——
  // 旗闸只加在 refresh 调用前，原 state 短路链保持首道闸。
  testWidgets(
    'cached/loading state still skips warm refresh even flag on',
    (tester) async {
      final recorder = _RecordingVisualElementNotifier();
      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(_ThrowingApiClient()),
          visualElementProvider.overrideWith((ref) => recorder),
          releaseFlagsProvider.overrideWith(
            (ref) => ReleaseFlagsNotifier(_ThrowingApiClient())
              ..seed(const ReleaseFlags(visualElements: true)),
          ),
        ],
      );
      addTearDown(container.dispose);
      // 预置 loading 态（warm refresh 原有跳过条件）
      recorder.state = VisualElementState.loading();

      await _pumpShell(tester, container);

      expect(
        recorder.refreshCalls,
        isEmpty,
        reason: '缓存兜底语义不破坏：isLoading 态下 warm refresh 仍跳过',
      );
    },
  );
}

/// 泵真实 shell 并越过 warm refresh 的 1200ms 启动延迟 + 异步缝隙。
Future<void> _pumpShell(
  WidgetTester tester,
  ProviderContainer container,
) async {
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(routerConfig: _buildRouter()),
    ),
  );
  // 首帧后 post-frame 调度 Future.delayed(1200ms) → 到点触发旗判定与 refresh
  await tester.pump(const Duration(milliseconds: 1200));
  await tester.pump();
  await tester.pump();
}

GoRouter _buildRouter() => GoRouter(
      initialLocation: '/home',
      routes: [
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) =>
              MainNavigationShell(navigationShell: navigationShell),
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/home',
                  builder: (context, state) =>
                      const Scaffold(body: SizedBox.shrink()),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/galaxy',
                  builder: (context, state) =>
                      const Scaffold(body: SizedBox.shrink()),
                ),
              ],
            ),
          ],
        ),
      ],
    );

/// V3-FIX-190/247：无网络的死桩——任何未 override 的网络面即失败
class _ThrowingApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('no network in shell flag gate test');
}

/// V3-FIX-247：记录 refresh() 调用的桩通知器（不发网络）
class _RecordingVisualElementNotifier extends VisualElementNotifier {
  _RecordingVisualElementNotifier() : super(_ThrowingApiClient());

  final List<String> refreshCalls = <String>[];

  @override
  Future<void> refresh() async {
    refreshCalls.add('refresh');
  }
}
