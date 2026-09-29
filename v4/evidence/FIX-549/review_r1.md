# V3-FIX-549 独立审查 Receipt（R1，2026-09-29）

审查人：R1（未参与实现）。仓库：wtF549（BRSAMAyu/Sparkle-project 工作树），分支 `fix/v4/f549-hive-close-hang`；被审修码 `94fe68a2`，被审头 `7a6e67c7`，base `834651a7`。审查全程未改产品/测试码，未 push；探针式还原一律 cp 备份法（未用 `git checkout --`），结束后 `git status` 干净、被审头不变。

## VERDICT: PASS

七靶全部亲验吻合，无阻塞发现。

## 七靶核验结果

1. **三连跑对照亲复验**：修后 index_shift 套件 ×3，exit 0 ×3，tearDownAll 均 00:01→00:01、护栏 0/3（与自报一致）。cp 备份法还原修码为 base（3 lib + 测试文件共 4 处——测试文件引用 `chatCacheServiceProvider`，不随还原则无法编译，与实现方 `git stash` 整体还原语义等价）→ 复跑 ×3，护栏 3/3 打满（00:02→00:05 / 00:01→00:04 / 00:02→00:05）= 悬挂确定性复现；cp 还原修码后复跑 0/3，还原后逐文件 cmp == HEAD。
2. **裁决①排除理由复核**：亲读 pub-cache 源码。fake_async 1.3.3 `fake_async.dart:70` `_microtasks` 为实例私有 Queue，`:188` scheduleMicrotask 区处理器仅入队，`:198/:241/:248` 仅 flushMicrotasks/elapse/run 排空，FakeAsync 随 test 结束被弃 → 在途写续延永不执行。hive 2.2.3 `storage_backend_vm.dart:219` close()→`syncReadWrite(_closeInternal)`；`read_write_sync.dart:30-42` syncReadWrite 链在 previousWriteTask，未完结写 completer 使 close 永久等待。探针 saveGroupMessages enter 永无 exit ×2 轮与机理自洽——选项① flush 钩子 await 的正是同批死 future，排除成立，③必要性成立。
3. **生产零语义变化**：`ChatCacheService` 工厂单例（chat_cache_service.dart:7,16）；provider 默认 `Provider((ref) => ChatCacheService())` 同走工厂 → 同一 `_instance`；其余直接构造点（auth_provider.dart:94）同实例。`late final _ref.read` 一次性读取、非 watch 无订阅耦合；首次访问在 `_initialize`（构造函数内 unawaited 启动，此时构造已完成、`_ref` 已初始化，PrivateChatNotifier 中 late 声明先于 `_ref` 亦因延迟求值合法）。notifier 重建时同 container 同实例。零语义差异成立。
4. **替身语义对齐**：`_InMemoryChatCacheService implements ChatCacheService`，编译器强制全接口（11 实例方法），签名漂移不可能（analyze 零 issue 佐证）。逐方法比对：group/private save/get（take(100) 截断、返回副本）、clearAllCache、pending enqueue/get/remove（nonce 空忽略、JSON 往返）均与真实现调用方可观测语义一致。notifier 缓存调用链未动，缓存写路径仍被行使（写入内存 map）；被删 2 行仅为过时注释，断言零删除，无既有断言依赖 Hive 持久化——非假绿。
5. **红线**：两套件 tearDownAll 块 byte 级一致（cmp 相同，MD5 b6193bc1bede82ca9bd7b17f38a3650b）；`git diff 834651a7..7a6e67c7 -- mobile/test/widget/group_chat_search_locate_test.dart` 为 0 字节；numstat 测试文件 115+/2−（删除为注释）；search_locate 重跑 +3 绿、护栏照旧触发（维持现状=红线本意）。
6. **回归与工具链**：批1 exit 0（+44），批2 exit 0（+25），共 69 绿；`flutter analyze --no-pub` exit 0 No issues found。（批1 日志含 `10.0.2.2:8080` 环境件，已登记既有，不判失败。）
7. **mutation 独立**：保留 lib 修码、仅移除 harness override（真单例回归）→ 护栏 2/2 打满（00:02→00:05 ×2）= 悬挂复现；证明修效 precisely 来自缝隙 override（③构造性消除直接反证成立）。还原后测试文件 cmp == HEAD。

## 编号发现（无阻塞）

1. INFO — mobile/test/widget/group_chat_index_shift_reparent_test.dart:433 — mutation A 须 4 文件整体还原（测试文件依赖新 provider，仅还原 3 处 lib 无法编译）；与实现方 stash 语义等价，不影响裁决。
2. LOW — mobile/test/widget/group_chat_index_shift_reparent_test.dart:328 — 替身 `enqueuePending*` 在 nonce 空时跳过记录，真实现会先开箱再判空（多一个空箱跟踪副作用）；对调用方可观测行为无差（getPending 均为空），测试未触此分支。
3. INFO — mobile/test/widget/group_chat_index_shift_reparent_test.dart:442 — 替身为每 harness 新实例，套件内跨测试缓存不再持久（真 Hive 单例会跨 test 残留）；两测试均经 `_waitUntilFound` 有界等待、断言不依赖跨测试缓存态，3/3 绿佐证无掩蔽。
4. LOW — mobile/lib/features/community/presentation/providers/community_provider.dart:911/1814 — `late final _ref.read` 理论边角：notifier 销毁后才首次触碰 `_cacheService` 将抛 ref 已处置错（原实现无此面）；现网首次访问均在构造期 `_initialize` 内，无此路径。

## 审查命令与 exit code 清单

| # | 命令（wtF549/mobile 下除注明外） | exit | 结果 |
|---|---|---|---|
| 1 | flutter test test/widget/group_chat_index_shift_reparent_test.dart（修后 ×3） | 0,0,0 | +2 绿，tearDownAll 00:01→00:01 ×3，护栏 0/3 |
| 2 | cp 还原 base 4 文件 + 逐文件 `git show 834651a7:<path> \| cmp -` | 0×4 | OK1–OK4，还原 == base |
| 3 | 同 #1（base 版 ×3） | 0,0,0 | 护栏 3/3 打满（00:02→00:05 / 00:01→00:04 / 00:02→00:05） |
| 4 | cp 还原 head 4 文件 + cmp == 7a6e67c7 | 0 | 树干净，== 被审头 |
| 5 | Edit 移除 override 一处（cp 备份 preMutB）后同 #1（×2） | 0,0 | 护栏 2/2 打满；cp 还原后 cmp == HEAD |
| 6 | flutter test token_refresh/unread_count/community_provider/community_agent 四文件 | 0 | +44 |
| 7 | flutter test community_provider/community_remaining_closure/h9_ui_sync/j3_frontend_closure 四文件 | 0 | +25 |
| 8 | flutter analyze --no-pub | 0 | No issues found |
| 9 | flutter test test/features/chat/presentation/screens/group_chat_search_locate_test.dart | 0 | +3 绿，护栏照旧（文件零改动） |
| 10 | cmp 两套件 tearDownAll 块；git diff --numstat；git diff -- search_locate | 0 | byte 级一致；2−均注释；search_locate diff 空 |

receipt 提交：见本文件所在 commit（仅含本文件）。
