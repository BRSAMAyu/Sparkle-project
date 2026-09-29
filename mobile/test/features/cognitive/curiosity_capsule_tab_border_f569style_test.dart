import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/capsule_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/curiosity_capsule_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// V4-G05 R1-C2 补钉：tab 选中指示「tint 填充 + 全强度描边」的回退保护。
///
/// R1 亲跑 M2（撤描边）后既有 21/21 全绿——tab 边界修复当时零 widget 钉：
/// capsuleAccent@0.14 tint 对 s2 底四风格仅 1.16–1.32:1（<3:1 图形阈值），
/// 边界对比由全强度描边承载。本钉直接断言 TabBar.indicator 的
/// BoxDecoration：tint 填充保留 + border 全强度 capsuleAccent——
/// 任一回退（删 border / 填充改全强度）在此变红。
class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeCapsuleRepository extends CapsuleRepository {
  _FakeCapsuleRepository() : super(_UnusedApiClient());
}

class _StaticCapsuleNotifier extends CapsuleNotifier {
  _StaticCapsuleNotifier(this._value) : super(_FakeCapsuleRepository()) {
    state = AsyncValue.data(_value);
  }

  final List<CuriosityCapsuleModel> _value;

  @override
  Future<void> fetchTodayCapsules() async {
    state = AsyncValue.data(_value);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
    I18nService.instance.updateLocale(
      const Locale('zh'),
      AppLocalizationsZh(),
    );
  });
  tearDown(I18nService.instance.reset);

  testWidgets('G05R1-C2 tab 选中指示 = tint@0.14 填充 + capsuleAccent 全强度描边', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/capsule',
      routes: [
        GoRoute(
          path: '/capsule',
          builder: (_, __) => const CuriosityCapsuleScreen(),
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          capsuleProvider.overrideWith(
            (ref) => _StaticCapsuleNotifier([
              CuriosityCapsuleModel(
                id: 'cap-1',
                title: 'capsule',
                content: 'content',
                isRead: false,
                createdAt: DateTime(2026, 3, 15),
              ),
            ]),
          ),
        ],
        child: MaterialApp.router(
          routerConfig: router,
          theme: ThemeData.light().copyWith(
            extensions: [SparkleThemeExtension.light()],
          ),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );
    // 屏内含常驻动效（pumpAndSettle 会超时），固定泵次推进首帧+入场动画。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 700));

    final tabBar = tester.widget<TabBar>(find.byType(TabBar));
    final indicator = tabBar.indicator;
    expect(indicator, isA<BoxDecoration>());
    final decoration = indicator as BoxDecoration;
    // tint 填充：capsuleAccent@0.14（回退成全强度填充会压标签墨 → 红）。
    expect(decoration.color, DS.capsuleAccent.withValues(alpha: 0.14));
    // 全强度描边：边界对比由 border 承载（R1-C2 主张——删 border 即红）。
    expect(decoration.border, isNotNull);
    expect(
      decoration.border!.top.color,
      DS.capsuleAccent.withValues(alpha: 1.0),
    );
  });
}
