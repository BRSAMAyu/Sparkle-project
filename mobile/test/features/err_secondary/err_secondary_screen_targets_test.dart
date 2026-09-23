import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/admin_operations_screen.dart';

import '../../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 抛错仓储：notifier 构造期后台 load* 触发后统一落进 error 态。
class _ThrowingRepository extends SeedLibraryRepository {
  _ThrowingRepository() : super(_NoopApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('seed library blew up');
}

class _StubSeedDetailNotifier extends SeedLibraryDetailNotifier {
  _StubSeedDetailNotifier(SeedLibraryDetailState initial)
      : super(_ThrowingRepository(), 'lib-err') {
    state = initial;
  }
}

SeedLibrary _buildLibrary() => SeedLibrary(
      id: 'lib-err',
      name: 'Err Secondary Lib',
      category: LibraryCategory.custom,
      visibility: LibraryVisibility.public,
      language: 'zh',
      isOfficial: false,
      isFeatured: false,
      usageCount: 0,
      itemCount: 0,
      subscriberCount: 0,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

/// ERR-SECONDARY 批（A-SPEC3 N15 次级域 + 残靶清零）：
/// 1. admin_operations_screen.dart:416 —— 管理面错误卡 `'$error'` 洗文本直出
///    改经 UserFacingError.from 人话化；
/// 2. seed_library_detail_screen.dart:41 —— `_friendlyActionError`
///    replaceFirst('Exception: ', '') 洗文本通道改经 owner。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
      'admin operations error cards humanize via owner — raw dump zeroed '
      '(admin:416 residual target)', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          clientTelemetrySummaryProvider(7).overrideWith(
            (ref) => throw Exception('admin telemetry blew up'),
          ),
          healthCapacityProvider.overrideWith(
            (ref) => throw Exception('admin telemetry blew up'),
          ),
          prometheusAlertsProvider.overrideWith(
            (ref) => throw Exception('admin telemetry blew up'),
          ),
        ],
        child: testMaterialApp(home: const AdminOperationsScreen()),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    // N15 契约：三块错误卡的 raw 异常文本零出现。
    expect(find.textContaining('admin telemetry blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    // 经 owner 出人话 + [ERR-*] 稳定码（三卡同型）。
    expect(find.textContaining('哎呀，出错了'), findsNWidgets(3));
    expect(find.textContaining('[ERR-UNKNOWN]'), findsNWidgets(3));
    // 卡片标题仍在（what+impact 结构保留）。
    expect(find.text('容量面板加载失败'), findsOneWidget);
  });

  testWidgets(
      'seed detail friendly action error goes through owner — wash-text zeroed '
      '(seed_detail:41 residual target)', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          seedLibraryDetailProvider('lib-err').overrideWith(
            (ref) => _StubSeedDetailNotifier(
              SeedLibraryDetailState(library: _buildLibrary()),
            ),
          ),
        ],
        child: testMaterialApp(
          home: const SeedLibraryDetailScreen(libraryId: 'lib-err'),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();

    // 触发 _friendlyActionError 通路：应用种子库 → 仓储抛错 → catch 出提示。
    final applyButton = find.text('应用种子库');
    expect(applyButton, findsOneWidget);
    await tester.ensureVisible(applyButton);
    await tester.tap(applyButton);
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));

    // 旧洗文本契约（replaceFirst('Exception: ') 后直出）不复存在。
    expect(find.textContaining('seed library blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    // 新契约：经 owner 人话化（unknown 类别落 arb 兜底句）。
    expect(find.textContaining('哎呀，出错了'), findsOneWidget);
    expect(find.textContaining('[ERR-UNKNOWN]'), findsOneWidget);
  });
}
