import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_list_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

/// SEARCH-EMPTY（N18/N28-③）：种子库硬编码英文清偿 + 搜索零命中专用态回归钉。
///
/// 原空态把英文四句直接怼在 UI 上（'No seed libraries match this filter' 等），
/// 且「搜了没有」「没搜过」「筛了没有」三态混用——本钉保证：
/// 1. 任何空态不再出现英文直出；
/// 2. 搜过零命中走 EmptyState.noResults（回显关键词+清空搜索）；
/// 3. 没搜过的空库态维持「还没有创建种子库」。
void main() {
  setUp(setUpI18nForTesting);

  Future<void> pumpScreen(
    WidgetTester tester, {
    required _FakeSeedLibraryRepository repo,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [seedLibraryRepositoryProvider.overrideWithValue(repo)],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const SeedLibraryListScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
  }

  void expectNoHardcodedEnglish(WidgetTester tester) {
    expect(find.textContaining('No seed libraries match'), findsNothing);
    expect(
      find.textContaining('Try clearing a filter or broadening'),
      findsNothing,
    );
    expect(
      find.textContaining('Create the first seed library'),
      findsNothing,
    );
    expect(find.text('Clear filters'), findsNothing);
    expect(find.text('Create seed library'), findsNothing);
  }

  testWidgets(
      'search zero-hit shows noResults state with keyword echo and clear '
      'action; empty library stays localized', (tester) async {
    await pumpScreen(tester, repo: _FakeSeedLibraryRepository());

    // 没搜过 + 无筛选：空库态（本地化），无英文直出。
    expect(find.text('还没有创建种子库'), findsOneWidget);
    expectNoHardcodedEnglish(tester);

    // 搜一个必然零命中的词（服务端替身对任何 search 都回空页）。
    await tester.enterText(find.byType(TextField), '外星科技');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 200));

    // 搜了没有：专用无结果态回显关键词 + 清空搜索，空库态退场。
    expect(find.text('没有找到与“外星科技”相关的内容'), findsOneWidget);
    expect(find.text('清空搜索'), findsOneWidget);
    expect(find.text('还没有创建种子库'), findsNothing);
    expectNoHardcodedEnglish(tester);

    // clear 钮可达：清词回到搜过之前（空库态回归）。
    await tester.tap(find.text('清空搜索'));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('还没有创建种子库'), findsOneWidget);
    expect(find.text('没有找到与“外星科技”相关的内容'), findsNothing);
  });
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 空库替身：无 search 返回空页（空库态），有 search 也返回空页（零命中态）。
class _FakeSeedLibraryRepository extends SeedLibraryRepository {
  _FakeSeedLibraryRepository() : super(_UnusedApiClient());

  @override
  Future<PaginatedResponse<SeedLibrary>> listLibraries({
    LibraryCategory? category,
    LibraryVisibility? visibility,
    String? language,
    bool? isOfficial,
    bool? isFeatured,
    String? search,
    int page = 1,
    int pageSize = 20,
    String? sortBy,
    String? sortOrder,
  }) async =>
      PaginatedResponse<SeedLibrary>(
        items: const <SeedLibrary>[],
        total: 0,
        page: page,
        pageSize: pageSize,
        totalPages: 0,
      );
}
