/// V3-FIX-376 补完 · B-04-L-01 pin — demo 模式下 experience 孪生理解快照
/// 不得以错误态裸露。
///
/// V3-FIX-376（wt686）只门控了 home 面的 `understandingSnapshotProvider`
/// （features/home/.../understanding_snapshot_provider.dart），但 golden home
/// 首屏回执卡 `UnderstandingSnapshotCard`（features/experience/.../widgets/）
/// 实际消费 experience 孪生 provider（features/experience/.../
/// experience_provider.dart，`FutureProvider.autoDispose` → repository），
/// wt693 重采实拍 demo 首屏「ⓘ 加载失败」仍在（B-04 ledger L-01 补记）。
///
/// 本测试把 wt693 的临时探针固化为正式回归：demo 契约 = demo 数据永不失败，
/// demo 态下该 provider 必须解析为内建空快照（卡片空态承载），repository
/// 不得被触碰；非 demo 路径零改动（不受本测试约束）。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/experience/data/experience_repository.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart';
import 'package:sparkle/features/experience/presentation/widgets/understanding_snapshot_card.dart';

/// 一触即炸的 ApiClient 替身：任何仓库调用都抛 StateError。
/// 既是 demo 环境无后端的确定性模拟（对应 wt693 实拍 DioException 400），
/// 也是「demo 分支不得触碰 repository」的守卫。
class _ExplodingApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw StateError('demo 契约：demo 模式下理解快照不得触碰 repository');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  ProviderContainer demoContainer() => ProviderContainer(
        overrides: [
          experienceRepositoryProvider.overrideWithValue(
            ExperienceRepository(_ExplodingApiClient()),
          ),
        ],
      );

  test('demo 模式：experience 理解快照解析为空快照而非 AsyncError（L-01）',
      () async {
    DemoDataService.isDemoMode = true;
    final container = demoContainer();
    addTearDown(container.dispose);

    final snapshot = await container.read(understandingSnapshotProvider.future);

    expect(snapshot.summary, isEmpty,
        reason: 'demo 占位 = 内建空快照，由卡片空态承载（V3-FIX-376 补完）',);
    expect(snapshot.evidence, isEmpty);
    expect(snapshot.memoryClaims, isEmpty);
    expect(snapshot.openQuestions, isEmpty);
  });

  testWidgets('demo 模式：UnderstandingSnapshotCard 不渲染 CompactErrorCard',
      (tester) async {
    DemoDataService.isDemoMode = true;
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: demoContainer(),
        child: const MaterialApp(home: Scaffold(body: UnderstandingSnapshotCard())),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byType(CompactErrorCard),
      findsNothing,
      reason: 'demo 首屏回执卡不得裸露「加载失败 轻触重试」（B-04-L-01）',
    );
    // 空快照由卡片空态承载：回执标题与兜底叙事可见（数据态而非骨架/错误态）。
    final titleOrFallback = find.byWidgetPredicate(
      (w) =>
          w is Text &&
          ((w.data?.contains('What Sparkle understands') ?? false) ||
              (w.data?.contains('Sparkle 对你的理解') ?? false) ||
              (w.data?.contains('调整今天的陪跑方式') ?? false)),
      description: '回执标题或空态兜底叙事',
    );
    expect(titleOrFallback, findsWidgets,
        reason: 'demo 空快照应落在卡片数据态空态，而非 loading 骨架',);
  });
}
