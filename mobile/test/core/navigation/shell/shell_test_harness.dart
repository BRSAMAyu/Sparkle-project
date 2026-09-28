import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/tokens_v2/pixel_preview_theme.dart';
import 'package:sparkle/core/navigation/shell_navigation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

import '../../../shared/i18n_test_helper.dart';

export '../../../shared/i18n_test_helper.dart'
    show setUpI18nForTesting, tearDownI18n, testMaterialApp;

/// V4-F04 · Shell 测试公共泵制。
///
/// 形制沿用 shell_warm_refresh_flag_gate_test 的先例：真 shell
/// （MainNavigationShell）+ 最小 StatefulShellRoute.indexedStack 路由；
/// 分支合同镜像 app/routes.dart 五分支真实 route ID（/home /galaxy
/// /chat /community /profile）与 home 分支嵌套子路由（/plans/:id，
/// 镜像 PlanRoutes.shellRoutes），不造第二路由权威——路由合同本体
/// 在测试中零改动，仅以占位屏承载布局断言。
///
/// 网络面一律死桩（apiClient 抛错 + visualElement 记录桩），shell 的
/// 启动期 warm refresh（1200ms）在泵制内冲刷，避免悬挂定时器。

/// V3-FIX-190/247：无网络的死桩——任何未 override 的网络面即失败。
class ThrowingShellApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('no network in shell test');
}

/// 记录 refresh() 调用的桩通知器（不发网络）。
class RecordingVisualElementNotifier extends VisualElementNotifier {
  RecordingVisualElementNotifier() : super(ThrowingShellApiClient());

  final List<String> refreshCalls = <String>[];

  @override
  Future<void> refresh() async {
    refreshCalls.add('refresh');
  }
}

/// home 分支占位内容（默认含错误探针：验收「主操作和错误可见」的
/// shell 级错误面代理——shell 布局不得把它推出视口）。
class ShellHomePlaceholder extends StatelessWidget {
  const ShellHomePlaceholder({this.bottomWidget, super.key});

  /// 置底控件（键盘测试用：置底 TextField 验证 inset 消费）。
  final Widget? bottomWidget;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Column(
          children: [
            Container(
              key: const ValueKey('shell_error_probe'),
              color: Theme.of(context).colorScheme.error,
              padding: const EdgeInsets.all(16),
              child: const Text('ERROR_PROBE'),
            ),
            const Text('HOME_ROOT_MARKER'),
            const Expanded(child: SizedBox.shrink()),
            if (bottomWidget != null) bottomWidget!,
          ],
        ),
      );
}

class ShellGalaxyPlaceholder extends StatelessWidget {
  const ShellGalaxyPlaceholder({super.key});

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: Text('GALAXY_PLACEHOLDER')));
}

class ShellChatPlaceholder extends StatelessWidget {
  const ShellChatPlaceholder({super.key});

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: Text('CHAT_PLACEHOLDER')));
}

class ShellCommunityPlaceholder extends StatelessWidget {
  const ShellCommunityPlaceholder({super.key});

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: Text('COMMUNITY_PLACEHOLDER')));
}

class ShellProfilePlaceholder extends StatelessWidget {
  const ShellProfilePlaceholder({super.key});

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: Text('PROFILE_PLACEHOLDER')));
}

/// home 分支嵌套子路由占位（镜像 /plans/:id 深链对象）。
class ShellPlanDetailPlaceholder extends StatelessWidget {
  const ShellPlanDetailPlaceholder({required this.planId, super.key});

  final String planId;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(child: Text('PLAN_PLACEHOLDER:$planId')),
      );
}

/// 五分支路由（镜像真实合同 ID；嵌套 /plans/:id 镜像 PlanRoutes）。
GoRouter buildShellTestRouter({
  String initialLocation = '/home',
  Widget? homeBottomWidget,
}) =>
    GoRouter(
      initialLocation: initialLocation,
      routes: [
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) =>
              MainNavigationShell(navigationShell: navigationShell),
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/home',
                  builder: (context, state) => ShellHomePlaceholder(
                    bottomWidget: homeBottomWidget,
                  ),
                ),
                GoRoute(
                  path: '/plans/:id',
                  builder: (context, state) => ShellPlanDetailPlaceholder(
                    planId: state.pathParameters['id'] ?? '',
                  ),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/galaxy',
                  builder: (context, state) => const ShellGalaxyPlaceholder(),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/chat',
                  builder: (context, state) => const ShellChatPlaceholder(),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/community',
                  builder: (context, state) =>
                      const ShellCommunityPlaceholder(),
                ),
              ],
            ),
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/profile',
                  builder: (context, state) => const ShellProfilePlaceholder(),
                ),
              ],
            ),
          ],
        ),
      ],
    );

/// 泵制真 shell（含尺寸/文本缩放/未读计数/pixel preview 档注入）。
///
/// [router] 缺省时按参数自建；传入时用调用方持有的 router（供
/// popRoute/go 断言）。返回容器供断言面使用；容器与 view 覆写的清理
/// 经 addTearDown 注册。
Future<ProviderContainer> pumpShellHarness(
  WidgetTester tester, {
  Size size = const Size(360, 800),
  double devicePixelRatio = 1.0,
  double textScale = 1.0,
  int unreadCount = 0,
  bool pixelPreview = false,
  String initialLocation = '/home',
  Widget? homeBottomWidget,
  GoRouter? router,
}) async {
  tester.view.physicalSize = size * devicePixelRatio;
  tester.view.devicePixelRatio = devicePixelRatio;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

  final container = ProviderContainer(
    overrides: [
      apiClientProvider.overrideWithValue(ThrowingShellApiClient()),
      visualElementProvider
          .overrideWith((ref) => RecordingVisualElementNotifier()),
    ],
  );

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: testMaterialApp(
        routerConfig: router ??
            buildShellTestRouter(
              initialLocation: initialLocation,
              homeBottomWidget: homeBottomWidget,
            ),
        theme: pixelPreview
            ? ThemeData(
                colorScheme: ColorScheme.fromSeed(
                  seedColor: const Color(0xFF3E6652),
                ),
                extensions: [
                  PixelProfileTheme.forProfile(PixelPreviewProfile.paperDay),
                ],
              )
            : null,
      ),
    ),
  );

  // 未读计数（IR-G2/N24 badge 上游）在首帧后经 StateNotifier 直写。
  if (unreadCount > 0) {
    container.read(unreadMessageCountProvider.notifier).state = unreadCount;
    await tester.pump();
  }

  // 冲刷 shell 的 post-frame 监听与 1200ms warm refresh 定时器。
  await tester.pump(const Duration(milliseconds: 1300));
  await tester.pump();
  return container;
}
