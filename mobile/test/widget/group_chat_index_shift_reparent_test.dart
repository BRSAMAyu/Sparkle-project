// wt339 · group_chat_screen F-4 同族潜伏债务清偿回归钉。
//
// 背景（wt336 F-4 判例）：reversed 懒加载 ListView 的子项挂常驻 GlobalKey
// 时，消息追加/前缀行进出导致索引整体移位，同键 Element 走
// `inflateWidget → _retakeInactiveElement` 的 GlobalKey 认领路径，在子树
// 形态剧变帧触发 `_elements.contains(element)` 断言崩溃。群聊屏存在同款
// 潜伏模式（`_messageKeys` 常驻键表挂 GroupChatBubble + agent 状态前缀行
// 进出 + 流式气泡进出），wt339 已按同款修法清偿：列表项身份键 = ValueKey
// （findChildIndexCallback 走框架 remap 路径）+ 搜索命中定位改一次性瞬态
// GlobalKey（定位收尾即摘除，含接管守卫）。
//
// 本测试按真机序列驱动完整 GroupChatScreen：
//   Case A：滚动上移填满 viewport+cacheExtent → agent 发送开始（THINKING
//     前缀状态行进 index 0，全部消息索引 +1 移位）→ 流式内容到达（前缀行
//     退出 + 流式气泡进场 merged，子树形态剧变帧）→ 流式完成（气泡退出 +
//     最终 agent 消息进场）。修复前形态下每拍都是认领高危帧。
//   Case B：搜索命中定位连续两次（离屏目标走 jumpTo 逼近 + 瞬态键
//     ensureVisible 全链路，第二次定位触发键替换）。
// 判据：全程无框架异常 + 内容在场——内容断言在形态翻转当场做（reversed
// 懒加载列表会回收离屏条目），收尾以状态层兜底。
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import '../shared/i18n_test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final hiveDir = Directory.systemTemp.createTempSync('wt339_group_hive');
    Hive.init(hiveDir.path);
    _ensureHiveAdapters();
  });

  setUp(() {
    // 群 WS 在 demo 模式下禁用：测试不触网。
    DemoDataService.isDemoMode = true;
  });

  tearDownAll(() async {
    DemoDataService.isDemoMode = false;
    try {
      // 后台缓存写可能在收尾时仍在途：Hive.close 加超时护栏防挂起。
      await Hive.close().timeout(const Duration(seconds: 3));
    } on Object catch (_) {}
  });

  testWidgets(
      'F-4 同族：agent 前缀行进出+流式翻转+收尾 全程无 GlobalKey 框架异常',
      (tester) async {
    final repo = _FakeCommunityRepository(
      pages: [_pageOne(), _pageTwo()],
      searchResults: const <MessageInfo>[],
    );
    final agent = await _pumpHarness(tester, repo: repo);

    // 滚动上移：填满 viewport 并让 cacheExtent 范围内存在已挂载的历史消息
    //（真机崩溃时用户不在列表底部；drag 同时可能触发向上翻页，属真机序列）。
    final listFinder = find.byWidgetPredicate(
      (widget) => widget is ListView && widget.reverse,
      description: 'reversed group chat message list',
    );
    expect(listFinder, findsOneWidget);
    await tester.drag(listFinder, const Offset(0, 300));
    await _settle(tester);

    // 第一拍：agent 发送开始 → THINKING 前缀状态行进入 index 0
    //（itemCount+1，全部消息索引整体移位；修复前=常驻 GlobalKey 认领高危帧）。
    agent.seed(const AgentChatState<MessageInfo>(isSending: true));
    await _settle(tester, 6);
    expect(tester.takeException(), isNull);

    // 第二拍：流式内容到达 → 前缀行退出 + 流式气泡进入 merged
    //（子树形态剧变帧：新气泡渲染分支激活、索引再次移位）。
    agent.seed(
      const AgentChatState<MessageInfo>(
        isSending: true,
        streamingContent: '正在为你整理冲刺要点，请稍候。',
      ),
    );
    await _settle(tester, 6);
    // 内容完整性（翻转当场断言：后续拍列表可能回收离屏条目）。
    expect(find.textContaining('正在为你整理'), findsWidgets);
    expect(tester.takeException(), isNull);

    // 第三拍：流式完成 → 流式气泡退出、最终 agent 消息进场
    //（再一帧移位 + 形态切换；同时 isSending 翻 false）。
    agent.seed(
      AgentChatState<MessageInfo>(
        messages: [
          _agentMessage('已完成整理：本周冲刺要点共三条。'),
        ],
      ),
    );
    await _settle(tester, 6);
    expect(tester.takeException(), isNull);

    // 状态级完整性兜底（widget 可能被懒加载回收，查状态层）。
    expect(agent.state.messages, hasLength(1));
    expect(agent.state.messages.first.content, contains('冲刺要点'));
    expect(find.byType(GroupChatScreen), findsOneWidget);
  });

  testWidgets(
      '搜索命中定位（瞬态键 ensureVisible 全链路）连续两次无框架异常',
      (tester) async {
    final hitA = _message(30, content: '定位甲正文');
    final hitB = _message(40, content: '定位乙正文');
    final repo = _FakeCommunityRepository(
      pages: [_pageOneWithLocateHits()],
      searchResults: [hitA, hitB],
    );
    await _pumpHarness(tester, repo: repo);

    // 离屏目标（页内第 30/40 新）不在构建窗口：定位走 jumpTo 逼近 + 瞬态键
    // context 命中的完整链路。
    expect(find.text('定位甲正文'), findsNothing);

    await tester.tap(find.byIcon(Icons.search));
    await tester.pump();
    await tester.enterText(_searchField(), '定位');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('定位甲正文'), findsOneWidget);

    // 第一次定位：关 sheet → 瞬态键挂载 → 滚动逼近 → ensureVisible。
    // 达靶判据升级（wt359）：不只要求命中树（cacheExtent 内未进视口的
    // 条目也会被 find.text 找到），还要求文本 RenderBox 实际在屏内。
    await tester.tap(find.text('定位甲正文'));
    await _pumpUntilLocateLanded(tester, '定位甲正文');
    _expectOnScreen(tester, '定位甲正文');
    expect(tester.takeException(), isNull);

    // 第二次定位（键替换路径：新键 mount、旧键已摘/接管守卫兜底）。
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(find.byIcon(Icons.search));
    await tester.pump();
    await tester.enterText(_searchField(), '定位');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await tester.tap(find.text('定位乙正文'));
    await _pumpUntilLocateLanded(tester, '定位乙正文');
    _expectOnScreen(tester, '定位乙正文');
    expect(tester.takeException(), isNull);

    // 收尾：ensureVisible 动画（250ms）与高亮 Timer（2s）全部走完，
    // 瞬态键摘除、高亮收敛，全程无框架异常。
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(seconds: 3));
    expect(tester.takeException(), isNull);
    expect(find.byType(GroupChatScreen), findsOneWidget);
  },
      // wt359 诊断：skip 已解除——本卡负责裁定装配 vs 产品缺陷（探针结论见
      // v3-output/WT359-LOCATE-DIAG/REPORT.md）。
      );
}

Object? _hiveAdaptersGuard;

void _ensureHiveAdapters() {
  if (_hiveAdaptersGuard != null) {
    return;
  }
  _hiveAdaptersGuard = Object();
  ChatCacheService.registerAdapters();
}

MessageInfo _message(int index, {String? content}) => MessageInfo(
      id: 'msg-$index',
      messageType: MessageType.text,
      sender: UserBrief(
        id: 'user-${index % 4}',
        username: 'member${index % 4}',
        nickname: '成员${index % 4}',
        status: UserStatus.online,
      ),
      content: content ?? '新消息 $index',
      createdAt: DateTime(2026, 9, 1, 12).subtract(
        Duration(minutes: index),
      ),
      updatedAt: DateTime(2026, 9, 1, 12).subtract(
        Duration(minutes: index),
      ),
    );

MessageInfo _agentMessage(String content) => MessageInfo(
      id: 'agent-final-1',
      messageType: MessageType.text,
      sender: buildCommunityAgentUser(localizedName: '群聊助手'),
      content: content,
      contentData: const {kAgentMetadataKey: true},
      createdAt: DateTime(2026, 9, 1, 12),
      updatedAt: DateTime(2026, 9, 1, 12),
    );

/// 第一页：最新 50 条（newest-first，>= _pageSize 触发 hasMore）。
List<MessageInfo> _pageOne() =>
    List<MessageInfo>.generate(50, _message).reversed.toList();

/// 定位用第一页：第 30/40 新的两条替换为专属命中正文（页内即达，
/// `_scrollToMessage` 不必翻页，直击 jumpTo 逼近+瞬态键链路）。
List<MessageInfo> _pageOneWithLocateHits() {
  final messages = List<MessageInfo>.generate(50, _message);
  messages[30] = _message(30, content: '定位甲正文');
  messages[40] = _message(40, content: '定位乙正文');
  return messages.reversed.toList();
}

/// 第二页：更早 30 条（< _pageSize → hasMore=false）。
List<MessageInfo> _pageTwo() => List<MessageInfo>.generate(
      30,
      (i) => _message(50 + i),
    ).reversed.toList();

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<String?> getToken() => getAccessToken();

  @override
  Future<bool> isLoggedIn() async => (await getAccessToken()) != null;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeChatRepository extends Fake implements ChatRepository {}

/// 可控群聊 agent 通知器：测试按真机时序直种 AgentChatState
///（前缀行/流式/收尾三拍），不经网络链路。
class _DriveGroupAgentNotifier extends GroupAgentChatNotifier {
  _DriveGroupAgentNotifier(super.repository, super.ref, super.groupId);

  void seed(AgentChatState<MessageInfo> next) {
    // 走 copyWith 形态整体替换四字段（copyWith 对 ''/false 语义即覆盖），
    // 与 F-4 红测 _F4ChatNotifier.seedMessages 同形，避开
    // use_setters_to_change_properties lint。
    state = state.copyWith(
      isSending: next.isSending,
      streamingContent: next.streamingContent,
      messages: next.messages,
      error: next.error,
    );
  }
}

class _FakeCommunityRepository implements CommunityRepository {
  _FakeCommunityRepository({
    required this.pages,
    required this.searchResults,
  });

  final List<List<MessageInfo>> pages;
  final List<MessageInfo> searchResults;

  @override
  Future<List<MessageInfo>> getMessages(
    String groupId, {
    String? beforeId,
    int limit = 50,
  }) async {
    if (beforeId == null) {
      return pages.first;
    }
    return pages.length > 1 ? pages[1] : const <MessageInfo>[];
  }

  @override
  Future<List<MessageInfo>> searchGroupMessages(
    String groupId,
    String keyword, {
    int limit = 50,
  }) async =>
      searchResults;

  @override
  Future<GroupInfo> getGroup(String groupId) async => _groupInfo();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

GroupInfo _groupInfo() => GroupInfo(
      id: 'g1',
      name: '冲刺群',
      type: GroupType.squad,
      focusTags: const ['协作'],
      memberCount: 4,
      totalFlamePower: 12,
      todayCheckinCount: 0,
      totalTasksCompleted: 0,
      maxMembers: 50,
      isPublic: true,
      joinRequiresApproval: false,
      createdAt: DateTime(2026, 8),
      updatedAt: DateTime(2026, 8),
    );

Future<_DriveGroupAgentNotifier> _pumpHarness(
  WidgetTester tester, {
  required _FakeCommunityRepository repo,
}) async {
  // wt296：GroupChatScreen.initState 读 chatDraftStoreProvider（草稿恢复），
  // 底层依赖 sharedPreferencesProvider，不 override 直接 UnimplementedError。
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  final fakeChatRepo = _FakeChatRepository();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        communityRepositoryProvider.overrideWithValue(repo),
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
        sharedPreferencesProvider.overrideWithValue(prefs),
        chatRepositoryProvider.overrideWithValue(fakeChatRepo),
        groupChatAgentProvider.overrideWith(
          (ref, groupId) =>
              _DriveGroupAgentNotifier(fakeChatRepo, ref, groupId),
        ),
      ],
      child: testMaterialApp(
        theme: AppThemes.lightTheme,
        home: const GroupChatScreen(groupId: 'g1'),
      ),
    ),
  );
  await tester.pump();
  // 首帧数据经真实 Hive I/O（缓存读写）落地：runAsync 让真实异步走完，
  // 再 pump 出帧——等待最新消息渲染即列表就绪。
  expect(
    await _waitUntilFound(tester, find.text('新消息 0')),
    isTrue,
    reason: '群聊消息列表未就绪',
  );
  final screenState = tester.state<ConsumerState>(
    find.byType(GroupChatScreen),
  );
  return screenState.ref.read(groupChatAgentProvider('g1').notifier)
      as _DriveGroupAgentNotifier;
}

Finder _searchField() => find.byKey(const ValueKey('group-chat-search-field'));

/// 等待 finder 命中（真实异步 I/O + 帧泵交替推进），超时返回 false。
Future<bool> _waitUntilFound(WidgetTester tester, Finder finder) async {
  final deadline = DateTime.now().add(const Duration(seconds: 6));
  while (DateTime.now().isBefore(deadline)) {
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 40)),
    );
    await tester.pump(const Duration(milliseconds: 50));
    if (finder.evaluate().isNotEmpty) {
      await tester.pump(const Duration(milliseconds: 100));
      return true;
    }
  }
  return false;
}

Future<void> _settle(WidgetTester tester, [int frames = 10]) async {
  for (var i = 0; i < frames; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

/// 定位达靶有界轮询（wt359 装配修复版）。原帮手两个装配缺陷（裁定在案）：
/// 1. 「先查后泵」：tap 后首查即命中仍在退场动画中的搜索 sheet 结果
///    ListTile（与列表气泡同文），零帧假绿且逼近链被饿死；
/// 2. 未排除 sheet：sheet 命中项与列表气泡同文，sheet 未关时任何命中
///    判定都可能是假阳性。
/// 现约定：每轮先泵一帧（一帧=endOfFrame 逼近链一次重试预算）；sheet 未
/// 完全关闭不认命中。24 帧覆盖 sheet 退场（~3 帧）+ 逼近链 13 次有界重试
/// + ensureVisible 250ms（~5 帧）仍有余量；产品链路 12 次重试放弃后多泵
/// 不会进场，故这是有界收敛预算而非掩败等待。
Future<void> _pumpUntilLocateLanded(
  WidgetTester tester,
  String text, {
  int maxFrames = 24,
}) async {
  for (var i = 0; i < maxFrames; i++) {
    await tester.pump(const Duration(milliseconds: 50));
    final sheetOpen = _searchField().evaluate().isNotEmpty;
    if (!sheetOpen && find.text(text).evaluate().isNotEmpty) {
      return;
    }
  }
}

/// 真实达靶断言：目标文本的 RenderBox 必须实际在屏内（不只是已构建——
/// cacheExtent 内的离屏条目同样能被 find.text 命中）。
void _expectOnScreen(WidgetTester tester, String text) {
  expect(
    find.text(text),
    findsOneWidget,
    reason: '定位后目标消息未在列表中构建',
  );
  final rect = tester.getRect(find.text(text));
  final screenHeight =
      tester.view.physicalSize.height / tester.view.devicePixelRatio;
  expect(
    rect.top,
    greaterThanOrEqualTo(0),
    reason: '定位达靶但目标仍在视口上方（未滚入）',
  );
  expect(
    rect.bottom,
    lessThanOrEqualTo(screenHeight),
    reason: '定位达靶但目标仍在视口下方（未滚入）',
  );
}
