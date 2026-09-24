// F-4（wt324 证据包 blocker）· 复现测试。
//
// 真机形态：首次长编号列表回复渲染即崩（`'_elements.contains(element)':
// is not true`，framework.dart `_InactiveElements.remove`，GlobalKey
// reparent 冲突形态；错误边界兜住进程但该条回复内容丢失）。
//
// 本测试按真机序列驱动 ChatScreen：滚动上移（填满 viewport + cacheExtent）
// → 追加 GENERATING 占位回复 → 同一消息翻转为「已完成的长编号列表」
// （StructuredSuggestionBody 分支激活、子树形态/高度剧变）→ 继续追加消息
// 触发 reversed 懒加载列表的索引整体移位。消息列表项当前挂的是
// GlobalKey（chat_screen `_messageKeyFor`），索引移位即走
// `inflateWidget → _retakeInactiveElement` 的 GlobalKey 认领路径。
//
// 红测判据：整条序列任何一帧不得产生框架异常（红=框架 GlobalKey 崩溃
// 被复现；绿=修复后序列干净走完且结构化渲染在场）。
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/structured_suggestion_body.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';

import '../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _QuietDashboardRepository extends DashboardRepository {
  _QuietDashboardRepository() : super(_NoopApiClient());

  @override
  Future<Map<String, dynamic>> getDashboardStatus() async => const {};

  @override
  Future<Map<String, dynamic>> getGrowthDashboard() async => const {};

  @override
  Future<Map<String, dynamic>> getPredictiveDashboard() async => const {};
}

class _QuietDashboardNotifier extends DashboardNotifier {
  _QuietDashboardNotifier() : super(_QuietDashboardRepository());

  @override
  Future<void> refresh() async {}
}

class _QuietPlanRepository extends PlanRepository {
  _QuietPlanRepository() : super(_NoopApiClient());

  @override
  Future<List<PlanModel>> getPlans({PlanType? type, bool? isActive}) async =>
      const [];

  @override
  Future<List<PlanModel>> getActivePlans() async => const [];
}

class _QuietDailyStartupRepository extends AuroraDailyStartupRepository {
  _QuietDailyStartupRepository() : super(_NoopApiClient());

  @override
  Future<AuroraComebackContext> getComebackContext() async =>
      const AuroraComebackContext.empty();

  @override
  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    throw StateError('daily startup disabled for F-4 test');
  }
}

class _QuietAuroraStatusNotifier extends AuroraStatusNotifier {
  _QuietAuroraStatusNotifier() : super(_NoopApiClient());

  @override
  Future<void> refresh({String? conversationId}) async {}

  @override
  void startPeriodicRefresh({String? conversationId}) {}

  @override
  void stopPeriodicRefresh() {}
}

class _FakeChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();
  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;
  @override
  void dispose() {}
  @override
  Future<List<Map<String, dynamic>>> getRecentConversations() async => [];
}

/// 可控 ChatNotifier：按真机时序种植/替换单条消息（保持其余原序）。
class _F4ChatNotifier extends ChatNotifier {
  _F4ChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}

  void seedMessages(List<ChatMessageModel> messages) {
    state = state.copyWith(messages: messages);
  }

  /// 追加到列表尾（= 视觉底部 = reversed 列表 index 0，真机时序）。
  void appendMessage(ChatMessageModel message) {
    state = state.copyWith(messages: [...state.messages, message]);
  }

  /// 原位替换（模拟流式完成：aiStatus 翻转 + 内容从占位变长列表）。
  void replaceMessage(ChatMessageModel message) {
    state = state.copyWith(
      messages: [
        for (final m in state.messages)
          if (m.id == message.id) message else m,
      ],
    );
  }
}

ChatMessageModel _msg(
  String id,
  MessageRole role,
  String content, {
  String? aiStatus,
}) =>
    ChatMessageModel(
      id: id,
      conversationId: 'f4-session',
      content: content,
      role: role,
      createdAt: DateTime.now(),
      aiStatus: aiStatus,
    );

/// >500 字符、无围栏、≥2 条编号项 —— StructuredSuggestionBody 分支激活形态
/// （wt324 复现 prompt 同款）。
String _longNumberedList({int items = 10}) {
  final buffer = StringBuffer('我为你整理了一份分步计划：\n');
  for (var i = 1; i <= items; i++) {
    buffer.writeln(
        '$i. 第 $i 步：请把今天剩余时间按 45 分钟一个番茄段拆分，先回顾'
        '核心概念，再做针对性练习，最后记录错因与下一步行动。');
  }
  return buffer.toString();
}

void main() {
  setUp(setUpI18nForTesting);

  Future<_F4ChatNotifier> pumpHarness(WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();
    final fakeChatRepo = _FakeChatRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          chatProvider.overrideWith(
            (ref) => _F4ChatNotifier(fakeChatRepo, ref),
          ),
          planRepositoryProvider.overrideWithValue(_QuietPlanRepository()),
          openClawConnectionProvider.overrideWith(
            (ref) => OpenClawConnectionService(),
          ),
          dashboardProvider.overrideWith((ref) => _QuietDashboardNotifier()),
          examSprintDashboardProvider.overrideWith((ref) async => null),
          auroraDailyStartupRepositoryProvider.overrideWithValue(
            _QuietDailyStartupRepository(),
          ),
          auroraStatusProvider.overrideWith(
            (ref) => _QuietAuroraStatusNotifier(),
          ),
        ],
        child: testMaterialApp(home: const ChatScreen()),
      ),
    );
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    return tester.state<ConsumerState>(find.byType(ChatScreen))
        .ref.read(chatProvider.notifier) as _F4ChatNotifier;
  }

  Future<void> settle(WidgetTester tester, [int frames = 10]) async {
    for (var i = 0; i < frames; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
  }

  testWidgets(
      'F-4 长编号列表回复：流式占位→结构化翻转→索引移位 全程无 GlobalKey 框架异常',
      (WidgetTester tester) async {
    final notifier = await pumpHarness(tester);

    notifier.seedMessages([
      _msg('m1', MessageRole.user, '帮我制定期末复习计划'),
      _msg('m2', MessageRole.assistant, '好的，先从操作系统开始。'),
      _msg('m3', MessageRole.user, '数据结构也要覆盖'),
      _msg('m4', MessageRole.assistant,
          '明白。我会把数据结构的树与图部分安排在第二周。',),
      _msg('m5', MessageRole.user, '时间很紧，只有两周'),
      _msg('m6', MessageRole.assistant, '那就压缩基础回顾，直接进入真题训练。'),
    ]);
    await settle(tester);

    // 滚动上移：填满 viewport 并让 cacheExtent 范围内存在已挂载的历史消息
    // （真机崩溃时用户不在列表底部）。
    final listFinder = find.byWidgetPredicate(
      (widget) => widget is ListView && widget.reverse,
      description: 'reversed chat message list',
    );
    expect(listFinder, findsOneWidget);
    await tester.drag(listFinder, const Offset(0, 300));
    await settle(tester);

    // 第一拍：流式占位回复进场（GENERATING，走 markdown 分支）。
    notifier.appendMessage(_msg('m7', MessageRole.assistant, '正在生成…',
        aiStatus: 'GENERATING',),);
    await settle(tester, 6);
    expect(tester.takeException(), isNull);

    // 第二拍：同一消息流式完成 → 内容翻转为长编号列表
    // （StructuredSuggestionBody 分支激活，子树形态/高度剧变）。
    notifier.replaceMessage(
      _msg('m7', MessageRole.assistant, _longNumberedList()),
    );
    await settle(tester, 6);

    // 第三拍：继续对话 → 列表尾部继续追加，历史消息索引整体移位
    // （GlobalKey 认领路径的高危帧）。
    notifier.appendMessage(_msg('m8', MessageRole.user, '收到，开始执行'));
    await settle(tester, 6);
    notifier.appendMessage(_msg('m9', MessageRole.assistant,
        '第一步已经为你排好了。',),);
    await settle(tester, 6);

    final exception = tester.takeException();
    expect(
      exception,
      isNull,
      reason: 'F-4：长建议结构化渲染不得触发框架异常（真机为 '
          '`_elements.contains(element)` GlobalKey reparent 崩溃），'
          '实际：$exception',
    );

    // 内容完整性：结构化渲染在场、编号条目可见（错误边界兜底=内容丢失，同样算失败形态）。
    expect(find.byType(StructuredSuggestionBody), findsOneWidget);
    expect(find.textContaining('第 1 步'), findsWidgets);
    expect(find.byType(ChatScreen), findsOneWidget);
  });
}
