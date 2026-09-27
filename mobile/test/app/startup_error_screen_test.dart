import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/main.dart';

import '../shared/i18n_test_helper.dart';

/// V3-FIX-370：bootstrap 失败屏人话化 + 重试 + 复制诊断。
///
/// 红测钉住三件事：
/// 1. 失败屏只出「类别人话」（wt673 uiErrorMessage 体系）+ 重试入口；
/// 2. 原始异常文本与堆栈不得直出用户面（技术信息泄露）；
/// 3. 「复制诊断信息」只放类名/时间戳/类别码，不放原始堆栈。
void main() {
  final binding = TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);

  group('StartupErrorScreen（V3-FIX-370）', () {
    testWidgets('失败屏出类别人话+重试入口，且不泄露原始异常与堆栈', (tester) async {
      var retryCount = 0;
      await tester.pumpWidget(
        testMaterialApp(
          home: StartupErrorScreen(
            error: const _FakeStartupFailure(),
            onRetry: () async => retryCount++,
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 300));

      // 人话标题 + 类别文案（network 类 → 既有 errorNetworkDetail 词条 + ERR 码）。
      expect(find.text('应用启动遇到问题'), findsOneWidget);
      expect(find.textContaining('请检查您的网络连接'), findsOneWidget);
      expect(find.textContaining('[ERR-NET]'), findsOneWidget);

      // 重试入口在。
      expect(find.text('重试'), findsOneWidget);

      // 原始异常 toString 细节、类名、堆栈行号形态均不得直出。
      expect(find.textContaining('SECRET-INTERNAL-DETAIL'), findsNothing);
      expect(find.textContaining('_FakeStartupFailure'), findsNothing);
      expect(find.textContaining('#0'), findsNothing);
      expect(find.textContaining('main.dart'), findsNothing);

      // 未点重试前回调不被触发。
      expect(retryCount, 0);
    });

    testWidgets('重试走回调；重试再失败仍停留人话屏（按新错误重分类）且不泄堆栈', (tester) async {
      var calls = 0;
      await tester.pumpWidget(
        testMaterialApp(
          home: StartupErrorScreen(
            error: const _FakeStartupFailure(),
            onRetry: () async {
              calls++;
              throw const _FakeTimeoutFailure();
            },
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 300));

      await tester.tap(find.text('重试'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(calls, 1);
      // 屏仍在：标题仍在，且按新错误重分类为 timeout 人话。
      expect(find.text('应用启动遇到问题'), findsOneWidget);
      expect(find.textContaining('请求处理时间过长'), findsOneWidget);
      expect(find.textContaining('[ERR-TIMEOUT]'), findsOneWidget);
      expect(find.textContaining('TimeoutException-marker'), findsNothing);
      expect(find.textContaining('#0'), findsNothing);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('复制诊断信息：剪贴板只有类名/时间戳/类别，无堆栈无原始异常', (tester) async {
      String? clipboardText;
      binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        (call) async {
          if (call.method == 'Clipboard.setData') {
            clipboardText = (call.arguments as Map<Object?, Object?>)['text']
                as String?;
          }
          return null;
        },
      );
      addTearDown(() {
        binding.defaultBinaryMessenger.setMockMethodCallHandler(
          SystemChannels.platform,
          null,
        );
      });

      await tester.pumpWidget(
        testMaterialApp(
          home: StartupErrorScreen(
            error: const _FakeStartupFailure(),
            onRetry: () async {},
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 300));

      await tester.tap(find.text('复制诊断信息'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(clipboardText, isNotNull);
      // 类名 + 时间戳 + 类别码在场。
      expect(clipboardText, contains('errorType: _FakeStartupFailure'));
      expect(clipboardText, contains('time: 2'));
      expect(clipboardText, contains('category: network'));
      // 原始堆栈与异常细节不得入剪贴板。
      expect(clipboardText, isNot(contains('SECRET-INTERNAL-DETAIL')));
      expect(clipboardText, isNot(contains('#0')));
      expect(clipboardText, isNot(contains('main.dart')));
    });
  });
}

/// 假启动失败：toString 带网络关键词（归 network 类）+ 内部细节标记。
class _FakeStartupFailure implements Exception {
  const _FakeStartupFailure();

  @override
  String toString() =>
      'FakeSocketException: SECRET-INTERNAL-DETAIL leaked (fake)';
}

/// 假重试失败：toString 带超时关键词（归 timeout 类）。
class _FakeTimeoutFailure implements Exception {
  const _FakeTimeoutFailure();

  @override
  String toString() => 'TimeoutException-marker after 30000ms (fake)';
}
