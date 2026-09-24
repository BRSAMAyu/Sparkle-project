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
import 'package:sparkle/features/chat/data/services/chat_cache_service.dart';
import 'package:sparkle/features/chat/presentation/screens/group_chat_screen.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import '../../../../shared/i18n_test_helper.dart';

/// SEARCH-EMPTY（N28-③/④/⑤）：群消息搜索面回归钉。
///
/// 1. 两态区分：未搜过=引导提示；搜了没有=EmptyState.noResults 专用态
///    （禁静默空白）；搜失败=人话错误（禁静默吞错）。
/// 2. 命中可达：点结果关 sheet 后滚动定位到消息上下文（禁 pop-only 死链），
///    并伴随短高亮（品牌色描边容器）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final hiveDir = Directory.systemTemp.createTempSync('wt254_search_hive');
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
      'search sheet distinguishes unsearched hint from zero-hit noResults '
      'state with clear action', (tester) async {
    final repo = _FakeCommunityRepository(
      pages: [_pageOne(), _pageTwo()],
      searchResults: const <MessageInfo>[],
    );
    await _pumpScreen(tester, repo: repo);

    // 列表就绪：最新消息可见，老消息未构建（未滚动）。
    expect(find.text('新消息 0'), findsOneWidget);

    // 打开搜索 sheet：未搜过态=引导提示（不是静默空白）。
    await tester.tap(find.byIcon(Icons.search));
    await tester.pump();
    expect(find.text('输入关键词，回车搜索群消息'), findsOneWidget);

    // 搜一个零命中词：专用无结果态回显关键词+清空搜索。
    await tester.enterText(_searchField(), '不存在的词');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('没有找到与“不存在的词”相关的内容'), findsOneWidget);
    expect(find.text('清空搜索'), findsOneWidget);
    expect(find.text('输入关键词，回车搜索群消息'), findsNothing);

    // clear 钮可达：清词回到未搜过态。
    await tester.tap(find.text('清空搜索'));
    await tester.pump();
    expect(find.text('输入关键词，回车搜索群消息'), findsOneWidget);
    expect(find.text('没有找到与“不存在的词”相关的内容'), findsNothing);
  });

  testWidgets(
      'tapping a search hit closes the sheet, scrolls the message into view '
      'and briefly highlights it (禁 pop-only 死链)', (tester) async {
    final anchor = _message(70, content: '锚点消息正文');
    final repo = _FakeCommunityRepository(
      pages: [_pageOne(), _pageTwo()],
      searchResults: [anchor],
    );
    await _pumpScreen(tester, repo: repo);

    expect(find.text('锚点消息正文'), findsNothing);

    await tester.tap(find.byIcon(Icons.search));
    await tester.pump();
    await tester.enterText(_searchField(), '锚点');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.text('锚点消息正文'), findsOneWidget);

    // 点命中项：关 sheet → 翻页加载（真实 Hive I/O）→ ensureVisible 定位。
    await tester.tap(find.text('锚点消息正文'));
    await tester.pump();

    // 定位断言：目标消息已构建在视口内（此前 findsNothing）。
    expect(
      await _waitUntilFound(tester, find.text('锚点消息正文')),
      isTrue,
      reason: '命中定位未把目标消息滚入视口',
    );
    await tester.pump(const Duration(milliseconds: 300));

    // 短高亮断言：存在品牌色描边的 AnimatedContainer（1.8s 内）。
    final highlighted = tester
        .widgetList<AnimatedContainer>(find.byType(AnimatedContainer))
        .where((container) {
      final decoration = container.decoration as BoxDecoration?;
      return decoration?.border?.top.color.alpha != 0;
    }).toList();
    expect(highlighted, isNotEmpty);
  });

  testWidgets(
      'search failure surfaces a human-readable error instead of silent '
      'blank', (tester) async {
    final repo = _FakeCommunityRepository(
      pages: [_pageOne()],
      searchResults: const <MessageInfo>[],
      searchError: Exception('server down'),
    );
    await _pumpScreen(tester, repo: repo);

    await tester.tap(find.byIcon(Icons.search));
    await tester.pump();
    await tester.enterText(_searchField(), '任意词');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    // 人话错误态：不再静默吞错、也不误报「无结果」。
    expect(find.text('群消息搜索失败，请重试'), findsOneWidget);
    expect(find.text('没有找到与“任意词”相关的内容'), findsNothing);
  });
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

/// 第一页：最新 50 条（newest-first，>= _pageSize 触发 hasMore）。
List<MessageInfo> _pageOne() =>
    List<MessageInfo>.generate(50, _message).reversed.toList();

/// 第二页：更早 30 条（< _pageSize → hasMore=false）。
List<MessageInfo> _pageTwo() => List<MessageInfo>.generate(
      30,
      (i) => _message(50 + i),
    ).reversed.toList();

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

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<String?> getToken() => getAccessToken();

  @override
  Future<bool> isLoggedIn() async => getAccessToken() != null;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeCommunityRepository implements CommunityRepository {
  _FakeCommunityRepository({
    required this.pages,
    required this.searchResults,
    this.searchError,
  });

  final List<List<MessageInfo>> pages;
  final List<MessageInfo> searchResults;
  final Object? searchError;

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
  }) async {
    final error = searchError;
    if (error != null) {
      throw error;
    }
    return searchResults;
  }

  @override
  Future<GroupInfo> getGroup(String groupId) async => _groupInfo();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<void> _pumpScreen(
  WidgetTester tester, {
  required _FakeCommunityRepository repo,
}) async {
  // wt296：GroupChatScreen.initState 读 chatDraftStoreProvider（草稿恢复），
  // 底层依赖 sharedPreferencesProvider，不 override 直接 UnimplementedError。
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        communityRepositoryProvider.overrideWithValue(repo),
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
        sharedPreferencesProvider.overrideWithValue(prefs),
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
  await _waitUntilFound(tester, find.text('新消息 0'));
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
