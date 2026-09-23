import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/cognitive/data/models/curiosity_capsule_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/capsule_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/capsule/capsule_detail_screen.dart';

import '../../../../../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 抛错仓储：stub notifier 不应触达真实数据源。
class _ThrowingRepository extends CapsuleRepository {
  _ThrowingRepository() : super(_NoopApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('capsule detail blew up');
}

/// 详情 notifier 桩：初始态直给目标胶囊，fetchDetail 空转。
class _StubCapsuleDetailNotifier extends CapsuleDetailNotifier {
  _StubCapsuleDetailNotifier(CuriosityCapsuleModel capsule)
      : super(_ThrowingRepository()) {
    state = AsyncValue.data(capsule);
  }

  @override
  Future<void> fetchDetail(String id) async {}
}

CuriosityCapsuleModel _capsule({required bool isFavorite}) =>
    CuriosityCapsuleModel(
      id: 'cap-1',
      title: '测试胶囊',
      content: '胶囊正文',
      isRead: true,
      createdAt: DateTime(2026, 9, 22),
      isFavorite: isFavorite,
    );

Future<void> _pumpDetail(WidgetTester tester, CuriosityCapsuleModel capsule) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        capsuleDetailProvider('cap-1').overrideWith(
          (ref) => _StubCapsuleDetailNotifier(capsule),
        ),
      ],
      child: testMaterialApp(
        home: const CapsuleDetailScreen(capsuleId: 'cap-1'),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

/// CAPSULE-VARIANT（wt250）：收藏激活态语义判定——
/// 收藏是品牌强调（positive marking），不是删除类破坏动作；
/// destructive 档只保留给删除/移除类操作。
/// 激活（isFavorite）→ primary（品牌实心强调档）；
/// 未激活 → ghost（中性软档）。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
    'favorited capsule renders favorite action with primary variant '
    '(brand emphasis, not destructive)',
    (tester) async {
      await _pumpDetail(tester, _capsule(isFavorite: true));

      final actionButton = tester.widget<SparkleIconButton>(
        find.ancestor(
          of: find.byIcon(Icons.favorite),
          matching: find.byType(SparkleIconButton),
        ),
      );
      expect(actionButton.variant, ButtonVariant.primary);
      expect(actionButton.variant, isNot(ButtonVariant.destructive));
    },
  );

  testWidgets(
    'unfavorited capsule renders favorite action with ghost variant',
    (tester) async {
      await _pumpDetail(tester, _capsule(isFavorite: false));

      final actionButton = tester.widget<SparkleIconButton>(
        find.ancestor(
          of: find.byIcon(Icons.favorite_border),
          matching: find.byType(SparkleIconButton),
        ),
      );
      expect(actionButton.variant, ButtonVariant.ghost);
    },
  );
}
