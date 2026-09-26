import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/screens/persona_onboarding_screen.dart';

import '../../shared/i18n_test_helper.dart';

/// V13-MAJORS M-01 连带面：onboarding 提交原先只有 try/finally——服务端
/// 慢/超时（V13 实测 30s receive timeout）后按钮原地复活，用户对成败
/// 零反馈。本卡加 catch-UI：可见错误文案 + 重试动作。本测试钉住：
/// 提交抛错时必须出现「这一步暂时没有完成…」反馈条，且重试会再次提交。
void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
  });
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('submit failure surfaces visible feedback with retry',
      (tester) async {
    final failingRepo = _FailingUserRepository();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          userRepositoryProvider.overrideWithValue(failingRepo),
        ],
        child: testMaterialApp(home: const PersonaOnboardingScreen()),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    // 走到最后一步（5 步引导）。Stepper 的隐藏步控件仍留在树里，逐个尝试
    // 直到 currentStep 推进到 4（最后一步的按钮文案为「完成」）。
    int currentStep() =>
        tester.widgetList<Stepper>(find.byType(Stepper)).first.currentStep;
    var guard = 0;
    while (currentStep() < 4 && guard < 24) {
      final candidates = find.text('下一步');
      final before = currentStep();
      final tappable = candidates.hitTestable();
      final tappableCount = tester.widgetList(tappable).length;
      for (var i = 0; i < tappableCount; i++) {
        await tester.tap(tappable.at(i), warnIfMissed: false);
        await tester.pump(const Duration(milliseconds: 50));
        if (currentStep() > before) {
          // 等步进切换动画结束，否则新步按钮尚未可点。
          await tester.pump(const Duration(milliseconds: 400));
          break;
        }
      }
      guard += 1;
    }
    expect(currentStep(), 4);
    expect(find.text('完成'), findsWidgets);

    // 最后一步的按钮可能被 Stepper 滚出视口，先拖到可见再点。
    for (var d = 0; d < 8; d++) {
      if (tester.widgetList(find.text('完成').hitTestable()).isNotEmpty) {
        break;
      }
      await tester.drag(find.byType(Stepper), const Offset(0, -150));
      await tester.pump(const Duration(milliseconds: 200));
    }

    // 提交 → 仓库抛超时错误 → 必须有可见反馈。
    await tester.tap(find.text('完成').hitTestable().first, warnIfMissed: false);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(failingRepo.calls, 1);
    expect(find.textContaining('这一步暂时没有完成'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);

    // 重试动作会再次提交。
    await tester.tap(find.text('重试'), warnIfMissed: false);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(failingRepo.calls, 2);
    expect(tester.takeException(), isNull);
  });
}

class _FailingUserRepository extends UserRepository {
  _FailingUserRepository() : super(_UnusedApiClient());

  int calls = 0;

  @override
  Future<String?> submitOnboarding(Map<String, dynamic> payload) async {
    calls += 1;
    throw DioException(
      requestOptions: RequestOptions(path: '/profile/onboarding'),
      type: DioExceptionType.receiveTimeout,
    );
  }
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
