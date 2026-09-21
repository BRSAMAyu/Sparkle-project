import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/features/task/data/repositories/action_proposal_repository.dart';
import 'package:sparkle/features/task/presentation/widgets/pending_proposal_section.dart';
import 'package:sparkle/shared/widgets/action_proposal/proposal_card_models.dart';

import '../../../shared/i18n_test_helper.dart';

/// U-04 · 双挂载一致性（chat payload 路由 vs task proposal 收件箱）
/// + 两条挂载路径的幂等键透传断言（GJ06/GJ07）.
void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });
  tearDown(tearDownI18n);

  const proposalPayload = <String, dynamic>{
    'proposal_id': 'prop-shared-1',
    'status': 'awaiting_user',
    'ownership': 'hybrid',
    'title': '把第 3 章错题整理成复习卡',
    'summary': 'Sparkle 已整理好结构，等你确认后执行',
  };

  Widget host({required Widget child, List<Override> overrides = const []}) =>
      ProviderScope(
        overrides: overrides,
        child: testMaterialApp(
          theme: ThemeData.light()
              .copyWith(extensions: [SparkleThemeExtension.light()]),
          home: Scaffold(
            body: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: child,
              ),
            ),
          ),
        ),
      );

  /// task 挂载的假收件箱：记录命令调用（测试夹具，非生产行为）。
  late _RecordingRepository repository;

  ActionProposalCardData projectionData() => ActionProposalCardData.fromChatPayload(
        <String, dynamic>{...proposalPayload, 'status': 'awaiting_user'},
      );

  testWidgets('chat 挂载：action_proposal payload 渲染统一卡片，确认经 onWidgetAction 透传幂等键',
      (tester) async {
    final widgetActions = <MapEntry<String, Map<String, dynamic>>>[];
    await tester.pumpWidget(host(
      child: ActionCard(
        action: WidgetPayload(type: 'action_proposal', data: proposalPayload),
        onWidgetAction: (type, payload) async {
          widgetActions.add(MapEntry(type, payload));
        },
      ),
    ));
    await tester.pump();

    // GJ07：无需读日志即知轮到谁——ownership + turn line 直接可见。
    expect(find.text('一起做'), findsOneWidget);
    expect(find.text('等你确认'), findsOneWidget);
    expect(find.text('把第 3 章错题整理成复习卡'), findsOneWidget);

    await tester.tap(find.text('确认，就这样做'));
    await tester.pumpAndSettle();

    expect(widgetActions, hasLength(1));
    expect(widgetActions.single.key, 'action_proposal_approve');
    expect(widgetActions.single.value['proposal_id'], 'prop-shared-1');
    expect(
      widgetActions.single.value['idempotency_key'],
      'u04:prop-shared-1:approve',
    );
  });

  testWidgets('task 挂载：收件箱数据渲染同一张卡片，确认经 repository 透传同一幂等键',
      (tester) async {
    repository = _RecordingRepository([projectionData()]);
    await tester.pumpWidget(host(
      child: const PendingProposalSection(taskId: 'task-7'),
      overrides: [
        actionProposalRepositoryProvider.overrideWithValue(repository),
      ],
    ));
    await tester.pump();
    await tester.pumpAndSettle();

    // 与 chat 挂载一致的 ownership / 状态 / 标题。
    expect(find.text('一起做'), findsOneWidget);
    expect(find.text('等你确认'), findsOneWidget);
    expect(find.text('把第 3 章错题整理成复习卡'), findsOneWidget);

    await tester.tap(find.text('确认，就这样做'));
    await tester.pumpAndSettle();

    expect(repository.approveCalls, hasLength(1));
    expect(
      repository.approveCalls.single,
      'u04:prop-shared-1:approve',
      reason: '同一 proposal 在两条挂载路径的幂等键必须一致（X-09 语义透传）',
    );
  });

  testWidgets('task 挂载：命令后刷新收件箱，proposal 消失即卡片移除', (tester) async {
    repository = _RecordingRepository([projectionData()]);
    await tester.pumpWidget(host(
      child: const PendingProposalSection(taskId: 'task-7'),
      overrides: [
        actionProposalRepositoryProvider.overrideWithValue(repository),
      ],
    ));
    await tester.pumpAndSettle();
    expect(find.text('等你确认'), findsOneWidget);

    await tester.tap(find.text('先不用'));
    await tester.pumpAndSettle();

    expect(repository.rejectCalls, hasLength(1));
    expect(repository.fetches >= 2, isTrue,
        reason: '命令后应 invalidate 收件箱并重取（刷新后卡片移除）');
  });

  testWidgets('task 挂载：收件箱为空时不渲染任何卡片', (tester) async {
    repository = _RecordingRepository(const <ActionProposalCardData>[]);
    await tester.pumpWidget(host(
      child: const PendingProposalSection(taskId: 'task-7'),
      overrides: [
        actionProposalRepositoryProvider.overrideWithValue(repository),
      ],
    ));
    await tester.pumpAndSettle();

    expect(find.text('等你确认'), findsNothing);
    expect(find.text('确认，就这样做'), findsNothing);
  });
}

class _RecordingRepository implements ActionProposalRepository {
  _RecordingRepository(this.pending);

  /// 收件箱返回值；空列表表示命令已被服务端受理（卡片应消失）。
  List<ActionProposalCardData> pending;
  int fetches = 0;
  final List<String> approveCalls = <String>[];
  final List<String> rejectCalls = <String>[];
  final List<String> cancelCalls = <String>[];

  @override
  Future<List<ActionProposalCardData>> listForSubject(
    String subjectId, {
    String? status,
  }) async {
    fetches += 1;
    return pending;
  }

  @override
  Future<Map<String, dynamic>?> approve(
    String proposalId,
    String idempotencyKey,
  ) async {
    approveCalls.add(idempotencyKey);
    pending = const <ActionProposalCardData>[];
    return const <String, dynamic>{'already_committed': false};
  }

  @override
  Future<Map<String, dynamic>?> reject(
    String proposalId,
    String idempotencyKey,
  ) async {
    rejectCalls.add(idempotencyKey);
    pending = const <ActionProposalCardData>[];
    return const <String, dynamic>{};
  }

  @override
  Future<Map<String, dynamic>?> cancel(
    String proposalId,
    String idempotencyKey,
  ) async {
    cancelCalls.add(idempotencyKey);
    pending = const <ActionProposalCardData>[];
    return const <String, dynamic>{};
  }
}
