import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/memory/presentation/screens/understanding_screen.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart'
    show kOnboardingCompletedKey;
import 'package:sparkle/features/user/presentation/screens/user_persona_screen.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../../../shared/i18n_test_helper.dart';

/// V4-U03 · 黑话清理与活入口测试。
///
/// 卡面「改黑话为来源/这次/这个目标/忘记」：
/// - UserPersona 活入口的 L1/L2/L3 系统层黑话 → 用户语言；
/// - 记忆操作词：仅此 Goal → 仅这个目标；删除 → 忘记；当前会话中 → 仅这次对话；
/// - UserPersona 活入口有「这次的理解」按钮（复用 /memory/understanding，
///   不复活孤儿界面）；
/// - UnderstandingScreen 顶部有「这次的理解」回执面板（I06 读面接线）。
class _StubReceiptApi implements ApiClient {
  _StubReceiptApi(this.response);

  Object? response;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async =>
      Response<T>(
        requestOptions: RequestOptions(path: path),
        data: response as T,
      );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _EmptyProvenanceRepository implements MemoryProvenanceRepository {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName}');
}

void main() {
  group('l10n 黑话清理（zh）', () {
    final zh = AppLocalizationsZh();

    test('UserPersona 分组标题不再出现 L1/L2/L3 系统层编号', () {
      expect(zh.personaL1Title, '你告诉我的');
      expect(zh.personaL2Title, '我们校准过的');
      expect(zh.personaL3Title, '我观察到的');
      expect(zh.personaL1Title.startsWith('L1'), isFalse);
      expect(zh.personaL2Title.startsWith('L2'), isFalse);
      expect(zh.personaL3Title.startsWith('L3'), isFalse);
    });

    test('记忆操作词：仅这个目标 / 忘记 / 仅这次对话（来源词已在 whyThisSourceTitle）', () {
      expect(zh.understandingActionScope, '仅这个目标');
      expect(zh.understandingActionScope.contains('Goal'), isFalse);
      expect(zh.understandingActionDelete, '忘记');
      expect(zh.understandingScopeSession, '仅这次对话');
      expect(zh.whyThisSourceTitle, '来源');
      // 删除确认链随「忘记」一致。
      expect(zh.understandingDeleteTitle, '忘记这条内容？');
      expect(zh.understandingDeleteBody, contains('忘记'));
      expect(zh.understandingToastDeleted, startsWith('已忘记'));
    });
  });

  group('l10n 黑话清理（en 同步）', () {
    final en = AppLocalizationsEn();

    test('en 与 zh 同步去黑话', () {
      expect(en.personaL1Title.startsWith('L1'), isFalse);
      expect(en.personaL3Title.startsWith('L3'), isFalse);
      expect(en.understandingActionScope, 'Only for this goal');
      expect(en.understandingActionDelete, 'Forget');
      expect(en.understandingScopeSession, 'Only in this conversation');
    });
  });

  testWidgets('UserPersona 活入口有「这次的理解」按钮（复用既有理解面）',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      kOnboardingCompletedKey: true,
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          // 档案面固定为空数据：屏幕直接进内容态（快捷入口卡在页首屏），
          // 不依赖真实网络/鉴权。
          transparentProfileProvider.overrideWith((ref) async => <String, dynamic>{}),
          profileContextProvider.overrideWith((ref) async => <String, dynamic>{}),
          inferredPreferencesProvider
              .overrideWith((ref) async => <Map<String, dynamic>>[]),
          activePoliciesProvider
              .overrideWith((ref) async => <Map<String, dynamic>>[]),
        ],
        child: testMaterialApp(home: const UserPersonaScreen()),
      ),
    );
    // 快捷入口卡在页首屏；分段 pump 规避未决请求的常驻动画。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    // 快捷入口卡在页首屏：系统更新 / 这次的理解 / 记忆设置。
    expect(find.text('这次的理解'), findsOneWidget);
    expect(find.text('记忆设置'), findsOneWidget);
  });

  testWidgets('UnderstandingScreen 顶部接线「这次的理解」回执面板（I06 读面）',
      (tester) async {
    setUpI18nForTesting();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryProvenanceRepositoryProvider
              .overrideWithValue(_EmptyProvenanceRepository()),
          contextReceiptProvider.overrideWith(
            (ref) {
              final notifier = ContextReceiptNotifier(
                _StubReceiptApi({
                  'mode': 'live',
                  'schema_version': 'context_selection_receipt.v1',
                  'receipt': null,
                }),
              );
              unawaited(notifier.load());
              return notifier;
            },
          ),
        ],
        child: testMaterialApp(home: const UnderstandingScreen()),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 150));

    // 回执面板在既有理解面顶部（同一活界面，非第二真源）。
    expect(find.text('这次的理解'), findsOneWidget);
    // live + 无回执 → 诚实空态。
    expect(find.text('这次没有产生理解回执（例如只是简单回答时）。'), findsOneWidget);
  });
}
