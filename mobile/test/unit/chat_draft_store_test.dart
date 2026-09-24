import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/chat/data/services/chat_draft_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, String>{});
  });

  Future<ChatDraftStore> freshStore() async =>
      ChatDraftStore(await SharedPreferences.getInstance());

  group('N46 草稿保存（save / scheduleSave 防抖）', () {
    test('save 即时落盘，load 读回原文', () async {
      final store = await freshStore();
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-1',
        userId: 'user-1',
        text: '帮我规划期末复习',
      );
      final loaded = await store.load(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-1',
        userId: 'user-1',
      );
      expect(loaded, '帮我规划期末复习');
    });

    test('scheduleSave 防抖窗口后落盘，窗口内多次输入只写最后一次', () async {
      final store = await freshStore();
      // 模拟连续两次输入事件：防抖后仅最后文本落盘。
      store
        ..scheduleSave(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-1',
          userId: 'user-1',
          text: '第一版',
        )
        ..scheduleSave(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-1',
          userId: 'user-1',
          text: '帮我规划期末复习（最终版）',
        );
      // 防抖窗口内尚不可见。
      final immediate = await store.load(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-1',
        userId: 'user-1',
      );
      expect(immediate, isNull);
      await Future<void>.delayed(ChatDraftStore.debounceDelay * 3);
      final loaded = await store.load(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-1',
        userId: 'user-1',
      );
      expect(loaded, '帮我规划期末复习（最终版）');
    });
  });

  group('N46 草稿恢复（跨实例 / 键隔离）', () {
    test('新实例（模拟进程重启）可恢复上一实例保存的草稿', () async {
      final first = await freshStore();
      await first.save(
        scope: ChatDraftScope.privateChat,
        conversationId: 'friend-9',
        userId: 'user-1',
        text: '重启前没发出去的问题',
      );
      final second = await freshStore();
      final restored = await second.load(
        scope: ChatDraftScope.privateChat,
        conversationId: 'friend-9',
        userId: 'user-1',
      );
      expect(restored, '重启前没发出去的问题');
    });

    test('conversationId 为空落 _new 兜底键；userId 不同互不可见', () async {
      final store = await freshStore();
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: '',
        userId: 'user-1',
        text: '新会话草稿',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: ChatDraftStore.newConversationKey,
          userId: 'user-1',
        ),
        '新会话草稿',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: '',
          userId: 'user-2',
        ),
        isNull,
      );
    });
  });

  group('N46 草稿清除（发送成功 / 会话删除）', () {
    test('clear 删除草稿；读回为 null', () async {
      final store = await freshStore();
      await store.save(
        scope: ChatDraftScope.groupChat,
        conversationId: 'group-1',
        userId: 'user-1',
        text: '退群前草稿',
      );
      await store.clear(
        scope: ChatDraftScope.groupChat,
        conversationId: 'group-1',
        userId: 'user-1',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.groupChat,
          conversationId: 'group-1',
          userId: 'user-1',
        ),
        isNull,
      );
    });

    test('输入被清空（发送成功路径）经 scheduleSave 空文本清除已有草稿', () async {
      final store = await freshStore();
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-2',
        userId: 'user-1',
        text: '即将发送的内容',
      );
      // 输入框 clear() 后 listener 上报空文本。
      store.scheduleSave(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-2',
        userId: 'user-1',
        text: '',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-2',
          userId: 'user-1',
        ),
        isNull,
      );
    });

    test('flush 空文本同样清除（dispose 于空输入时无害）', () async {
      final store = await freshStore();
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-3',
        userId: 'user-1',
        text: '旧草稿',
      );
      await store.flush(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-3',
        userId: 'user-1',
        text: '  ',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-3',
          userId: 'user-1',
        ),
        isNull,
      );
    });
  });

  group('N46 容量上界（单草稿 4KB / 总量 100 条 LRU）', () {
    test('超 4096 字节截断保头部，且切在码点边界（CJK 3 字节）', () async {
      final store = await freshStore();
      // 1366 个 3 字节 CJK 字符 = 4098 字节，超界且 4096 落在字符头部。
      final oversized = '啊' * 1366;
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-big',
        userId: 'user-1',
        text: oversized,
      );
      final loaded = await store.load(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-big',
        userId: 'user-1',
      );
      expect(loaded, isNotNull);
      expect(utf8.encode(loaded!).length, lessThanOrEqualTo(4096));
      expect(loaded, '啊' * 1365);
    });

    test('ASCII 超长同样截断到 4096 字节', () async {
      final store = await freshStore();
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-ascii',
        userId: 'user-1',
        text: 'a' * 5000,
      );
      final loaded = await store.load(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-ascii',
        userId: 'user-1',
      );
      expect(loaded, 'a' * 4096);
    });

    test('总量 100 条：第 101 条写入淘汰最久未用者', () async {
      final store = await freshStore();
      for (var i = 1; i <= ChatDraftStore.maxEntries; i++) {
        await store.save(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-$i',
          userId: 'user-1',
          text: '草稿 $i',
        );
      }
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-101',
        userId: 'user-1',
        text: '草稿 101',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-1',
          userId: 'user-1',
        ),
        isNull,
        reason: '最久未用的 conv-1 应被 LRU 淘汰',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-2',
          userId: 'user-1',
        ),
        '草稿 2',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-101',
          userId: 'user-1',
        ),
        '草稿 101',
      );
    });

    test('load 触碰刷新 LRU 位次：刚读过的键不被下次溢出淘汰', () async {
      final store = await freshStore();
      for (var i = 1; i <= ChatDraftStore.maxEntries; i++) {
        await store.save(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-$i',
          userId: 'user-1',
          text: '草稿 $i',
        );
      }
      // 读 conv-1 → 位次刷新为最新；再写 conv-101 应淘汰 conv-2。
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-1',
          userId: 'user-1',
        ),
        '草稿 1',
      );
      await store.save(
        scope: ChatDraftScope.chat,
        conversationId: 'conv-101',
        userId: 'user-1',
        text: '草稿 101',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-1',
          userId: 'user-1',
        ),
        '草稿 1',
        reason: '被读取刷新过的 conv-1 不应淘汰',
      );
      expect(
        await store.load(
          scope: ChatDraftScope.chat,
          conversationId: 'conv-2',
          userId: 'user-1',
        ),
        isNull,
        reason: '未触碰的 conv-2 成为 LRU 淘汰对象',
      );
    });
  });
}
