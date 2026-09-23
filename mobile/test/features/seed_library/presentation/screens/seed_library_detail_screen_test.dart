import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

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

/// A-SPEC3 改造 #2（N15/EE-G1+G3）：seed_library_detail_screen.dart:151/:157
/// 直出靶——`Text(state.error!)` 改经 UserFacingError.from 人话化；
/// 重试钮 variant.destructive → outline（恢复性动作不复用破坏样式）。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
      'error view humanizes state.error and retry button is outline, '
      'not destructive', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(null),
          seedLibraryDetailProvider('lib-err').overrideWith(
            (ref) => _StubSeedDetailNotifier(
              SeedLibraryDetailState(error: UiErrorCategory.unknown),
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

    // 直出清零：原始异常文本不入 UI。
    expect(find.textContaining('seed detail blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    // 经 owner 映射：人话 + 稳定码。
    expect(find.textContaining('哎呀，出错了'), findsOneWidget);
    expect(find.textContaining('哎呀，出错了'), findsOneWidget);

    // 重试钮样式归位：outline（非 destructive）。
    final retryButton =
        tester.widget<SparkleButton>(find.byType(SparkleButton));
    expect(retryButton.variant, ButtonVariant.outline);
    expect(find.text('重试'), findsOneWidget);
  });
}
