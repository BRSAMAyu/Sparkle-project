import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_draft_review_models.dart';
import 'package:sparkle/features/galaxy/data/repositories/galaxy_draft_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_draft_review_provider.dart';
import 'package:sparkle/features/galaxy/presentation/screens/galaxy_draft_review_screen.dart';

import '../../../shared/i18n_test_helper.dart';

/// V25 回归：「审核知识星」页（误触「现在审核」进入的真实路径）。
///
/// 缺陷现场（B-04 第三棒，leg3_galaxy_step3.png）：
/// 1. 进入即崩 `Unsupported operation: Cannot remove from a fixed-length list`
///    （_ReviewActionBar 对 `toList(growable: false)` 产物 removeLast）；
/// 2. 同页双溢出 164/138px（_DraftReviewCard 固定内容超过 Expanded 牌堆可用高度，
///    前后两张卡各报一条）。
void main() {
  setUp(setUpI18nForTesting);

  Widget wrap(ProviderContainer container, Widget home) => UncontrolledProviderScope(
        container: container,
        // 需挂 DS 主题，否则 SparkleThemeExtension 未注册，构建即抛断言。
        child: testMaterialApp(theme: AppThemes.lightTheme, home: home),
      );

  testWidgets(
    'V25: entering draft review screen must not throw fixed-length list error',
    (tester) async {
      // 大 surface：排除溢出干扰，单独回归崩溃。
      await tester.binding.setSurfaceSize(const Size(800, 1200));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final container = ProviderContainer(
        overrides: [
          galaxyDraftReviewProvider.overrideWith(
            (ref) => GalaxyDraftReviewNotifier(_FakeDraftRepository(_batch())),
          ),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        wrap(
          container,
          const GalaxyDraftReviewScreen(initialBatchId: 'batch-v25'),
        ),
      );
      // frame 1: loading 骨架；frame 2: 数据到达后完整构建（崩溃点）。
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(
        tester.takeException(),
        isNull,
        reason:
            '进入「审核知识星」页不得抛 '
            '`Cannot remove from a fixed-length list`（V25：'
            '_ReviewActionBar 对固定长 list 调 removeLast）',
      );
      expect(find.text('第 1 / 2 颗'), findsOneWidget);
      expect(find.text('通过'), findsOneWidget);
      expect(find.text('跳过'), findsOneWidget);
      expect(
        find.textContaining('Oops, something went wrong'),
        findsNothing,
      );
    },
  );

  testWidgets(
    'V25: draft review deck must not RenderFlex-overflow on small screens',
    (tester) async {
      // 小屏手机（360x640 逻辑像素）+ 长描述 + 相似度横幅：复现现场双溢出。
      tester.view.physicalSize = const Size(1080, 1920);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(tester.view.reset);

      final container = ProviderContainer(
        overrides: [
          galaxyDraftReviewProvider.overrideWith(
            (ref) => GalaxyDraftReviewNotifier(
              _FakeDraftRepository(_batch(longDescription: true)),
            ),
          ),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        wrap(
          container,
          const GalaxyDraftReviewScreen(initialBatchId: 'batch-v25'),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      final exception = tester.takeException();
      expect(
        exception,
        isNull,
        reason:
            '审核牌堆在 360x640 小屏上不得 RenderFlex 溢出'
            '（现场为 BOTTOM OVERFLOWED BY 164/138 PIXELS 双条纹，V25）；'
            '实际异常：$exception',
      );
    },
  );

  testWidgets(
    'V25: full review flow (approve twice) reaches completion without error',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(800, 1200));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final container = ProviderContainer(
        overrides: [
          galaxyDraftReviewProvider.overrideWith(
            (ref) => GalaxyDraftReviewNotifier(_FakeDraftRepository(_batch())),
          ),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        wrap(
          container,
          const GalaxyDraftReviewScreen(initialBatchId: 'batch-v25'),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      await tester.tap(find.text('通过'));
      await tester.pump(const Duration(milliseconds: 320));
      expect(find.text('第 2 / 2 颗'), findsOneWidget);

      await tester.tap(find.text('通过'));
      await tester.pump(const Duration(milliseconds: 320));

      expect(tester.takeException(), isNull);
      expect(find.text('准备把它们送进你的星图'), findsOneWidget);
    },
  );
}

GalaxyDraftBatch _batch({bool longDescription = false}) {
  final description = longDescription
      ? '操作系统在进程、线程与协程之间调度 CPU 时间，公平性与吞吐量彼此制约。'
          '轮转调度以时间片换取响应速度，最短作业优先依赖对突发时长的预测，'
          '而抢占式内核随时可以中断低优先级工作，让高优先级任务立即运行。'
          '理解这些权衡是掌握并发编程与系统性能调优的第一步，也是面试高频考点。'
      : 'How the operating system decides which process gets CPU time.';
  return GalaxyDraftBatch(
    id: 'batch-v25',
    documentId: 'doc-v25',
    documentName: '命题逻辑与谓词逻辑小结.md',
    createdAt: DateTime(2026, 9, 21),
    drafts: [
      GalaxyDraftNode(
        id: 'draft-1',
        proposedName: '进程调度',
        proposedDescription: description,
        excerpts: const [
          'Round-robin scheduling improves responsiveness by assigning each runnable process a small time slice before the CPU rotates.',
          'Shortest-job-first minimizes average waiting time but depends on predicting future burst length.',
          'Preemption lets the kernel interrupt a running process so higher-priority work can run immediately.',
        ],
        similarity: const GalaxyDraftSimilarity(
          existingNodeId: 'existing-os',
          existingNodeName: 'OS 概念基础',
          similarityPercent: 87,
        ),
      ),
      const GalaxyDraftNode(
        id: 'draft-2',
        proposedName: '死锁',
        proposedDescription:
            'Conditions that cause processes to wait on one another forever.',
        excerpts: [
          'A deadlock requires mutual exclusion, hold-and-wait, no preemption, and circular wait.',
        ],
      ),
    ],
  );
}

class _FakeDraftRepository extends GalaxyDraftRepository {
  _FakeDraftRepository(this._batch) : super(Dio());

  final GalaxyDraftBatch _batch;

  @override
  Future<List<GalaxyDraftBatch>> listPendingDrafts() async => [_batch];
}
