# WT339 · group_chat_screen 同款潜伏 GlobalKey 模式清偿 — REPORT

- **Worker**: wt339
- **基线**: main `450437c0`（worktree `../Sparkle-sysrev/wt339-groupchat-key`，branch `wt339-groupchat-key`）
- **档位**: LIGHT（无模拟器/Gradle/浏览器；定向 flutter test 受 swap 门约束，见 §四）
- **卡面**: wt336 F-4 收尾时登记的在册债务——group_chat_screen 与 chat_screen 修复前同构的「reversed 懒加载列表子项挂常驻 GlobalKey」潜伏模式

## 一、考古结论（同款模式的具体位置与形态）

`mobile/lib/features/chat/presentation/screens/group_chat_screen.dart`（修复前坐标）：

| 位置 | 形态 |
|---|---|
| :57 | `final Map<String, GlobalKey> _messageKeys` 常驻键表 |
| :140-141 | `_messageKeyFor(id) => _messageKeys.putIfAbsent(id, GlobalKey.new)`（itemBuilder 内懒建） |
| :598-604 | `ListView.builder` + `reverse: true` + `shrinkWrap: true`（懒加载 reversed 列表） |
| :604 | `itemCount = mergedMessages.length + (showAgentStatus ? 1 : 0)` —— **agent THINKING 前缀状态行进 index 0，进出即全量索引移位**（与 chat 域 F-4 的前缀行触发器同构，群聊自身就有该触发器，不需要长建议翻转也能移位） |
| :623 | `GroupChatBubble(key: _messageKeyFor(message.id))` —— 每条消息常驻 GlobalKey 挂 reversed 列表子项 |
| :595 | `_pruneMessageKeys(mergedMessages)` build 内修剪键表 |
| :1087 | `_messageKeys[messageId]?.currentContext` 供搜索命中定位 `Scrollable.ensureVisible` |

与 wt336 判例的差异仅两点：①群聊消息不经 StructuredSuggestionBody（暂无长建议触发器）；②定位入口是「搜索 sheet 点命中」（任意时刻动作，且目标可能未翻页加载，带 jumpTo 逼近重试链）。风险形态本身（常驻键×reversed 懒加载×索引移位→`inflateWidget → _retakeInactiveElement` 认领路径）完全一致；流式气泡（`_buildStreamingAgentMessage`，每帧新 id）与 agent 前缀行进出都是天然移位帧。该屏 :229（转发对话框）与 :1259（搜索结果列表）两处 ListView 无键表，不属病灶。

## 二、修法移植（对齐 wt336 chat_screen 判例，逐形制等价）

1. **列表项常驻身份键 → `ValueKey<String>`**：itemBuilder 处 `key: (_locateTargetMessageId == message.id && _locateTargetKey != null) ? _locateTargetKey : ValueKey<String>(message.id)`——仅当本帧为搜索命中定位目标时才挂瞬态 GlobalKey。
2. **`ListView.builder` → `ListView.custom` + `SliverChildBuilderDelegate`**（childCount + `findChildIndexCallback`）：新增 `_findChildIndexForKey`，按键（ValueKey=id / GlobalKey=瞬态定位键）返回该消息在**当前**列表坐标（含 agent 前缀行 +1 偏移；mergedMessages 新→旧序，index 0 = reversed 底部）的索引——索引移位帧框架走 performRebuild 的 **remap 路径**原位搬移 Element，消灭认领分支；瞬态定位键也被同一 callback 覆盖 remap。
3. **搜索命中定位改一次性瞬态键**：字段 `_locateTargetKey`/`_locateTargetMessageId` 替代常驻键表；`_locateSearchHit` 挂新键（重复触发直接替换，旧键条目下一帧回挂 ValueKey 走正常摘除）；`_revealMessage` 命中 context → `Scrollable.ensureVisible`（duration 250ms/curve/alignment=0.22 逐位不变）→ 动画完 `_clearLocateTarget` 摘键；**接管守卫**=链路入口与收尾均校验 `_locateTargetKey != expectedKey` / `_locateTargetMessageId != messageId` 即退出——顺带修掉旧形态下「旧定位链路凭常驻键仍能命中 context、与新定位双向拉扯滚动」的残余竞态。jumpTo 逼近重试（≤12 次）链语义保持。
4. 删除 `_messageKeys`/`_messageKeyFor`/`_pruneMessageKeys`（build 内键表修剪随之消失）。

未重构群聊其他行为：高亮 Timer（2s 收敛）、翻页加载、`_scheduleScrollToLatest`、composer 草稿链全部原样；未碰 chat_screen.dart（wt336 刚改完）、后端、l10n。

## 三、回归测试（与 chat_long_suggestion_reparent_test 同款形制）

新增 `mobile/test/widget/group_chat_index_shift_reparent_test.dart`（两 case，按真机序列驱动完整 GroupChatScreen，harness 复用 group_chat_search_locate_test 的静默夹具：demo 模式禁 WS + fake CommunityRepository + 真 Hive 临时目录）：

- **Case A（reparent 族回归）**：滚动上移填满 viewport+cacheExtent（drag 可触向上翻页）→ 第一拍 agent 发送开始（THINKING 前缀行进 index 0，全量索引 +1 移位）→ 第二拍流式内容到达（前缀行退出+流式气泡进场 merged，子树形态剧变帧，内容断言当场做）→ 第三拍流式完成（气泡退出+最终 agent 消息进场，`isSending` 翻 false）。每拍 `takeException` 为 null + 状态层完整性兜底（懒加载会回收离屏条目）。
- **Case B（瞬态定位全链路）**：离屏命中（页内第 30/40 新）→ 搜索 sheet 点命中 → 瞬态键挂载 → jumpTo 逼近 + context 命中 ensureVisible → 目标在视口断言；连续第二次定位（键替换/守卫路径）同样达靶；收尾 pump 完动画（250ms）与高亮 Timer（2s）后无框架异常。

**执行状态：DEFERRED** — 开工至收工 `sysctl vm.swapusage` free 全程 731.94M < 1.2G 门限（单批 flutter test 实测吃 ~700M），纪律禁止开跑。红转绿补跑命令（swap 窗口由主会话统一开）：

```bash
cd mobile && flutter test test/widget/group_chat_index_shift_reparent_test.dart \
  test/features/chat/presentation/screens/group_chat_search_locate_test.dart --concurrency=1
```

（search_locate_test 一并补跑：它端到端覆盖定位+高亮路径，是对本次瞬态键移植的直接回归钉。）

## 四、验证与环境

- **守卫**：`bash scripts/run_all_rule_guards.sh` → **83 条全过，exit 0**。
- **analyze 门**：`check_flutter_analyze_gate.py` → **E0/W15/I598，与 main 基线逐位一致，零漂移**。过程自纠 4 处本测试新增 lint（UNNECESSARY_NULL_COMPARISON 改 await 形、UNNECESSARY_IMPORT ×2 收敛到 chat.dart barrel、USE_SETTERS_TO_CHANGE_PROPERTIES 改 copyWith 同形）。另：`flutter pub get` 曾重排 gitignored 链路外的 l10n 三生成文件（wt336 同款坑），已当即 `git checkout --` 还原，未入提交。
- **mypy**：本卡未动 backend，基线不推高（天然满足）。
- **gen 三件套**：主仓只读 `cp -RL` 拷入 worktree（mobile/backend app/backend gateway）。

## 五、合并核对表（精确文件+行段；本卡 worktree 坐标）

| 文件 | 行段 | 内容 |
|---|---|---|
| `mobile/lib/features/chat/presentation/screens/group_chat_screen.dart` | :55-66 | 字段注释重写 + `_messageKeys` → `_locateTargetKey`/`_locateTargetMessageId` |
| 同上 | :133-137 | 删 `_pruneMessageKeys`/`_messageKeyFor` |
| 同上 | :596-701 | `ListView.builder` → `ListView.custom` + delegate（childCount/findChildIndexCallback）；气泡键 ValueKey+瞬态覆盖 |
| 同上 | :1057-1077 | `_locateSearchHit` 挂瞬态键 |
| 同上 | :1103-1145 | `_findChildIndexForKey` 新 helper + `_clearLocateTarget` 收尾（接管守卫） |
| 同上 | :1157-1185 | `_revealMessage` 改瞬态键 context + 链路接管守卫（ensureVisible 参数逐位不变） |
| `mobile/test/widget/group_chat_index_shift_reparent_test.dart` | 全新文件 | 两 case 回归钉 |

**未碰**：`chat_screen.dart`、chat 域其他文件、galaxy、后端全部、l10n、群聊其他行为面。

## 六、定级与收工

- **定级：PARTIAL** — 静态修复与回归测试在库、守卫/analyze 全绿，但红转绿执行证据受 swap 门缺失（与 wt336 F-4 交付同型；该卡红测已在 09-24 swap 窗口 46/46 补跑转绿，先例成立）。swap 窗口补跑两文件绿后本债正式闭环。
- [x] 守卫 83 exit 0
- [x] analyze 门零漂移
- [x] mypy 不涉及
- [x] REPORT.md + changes.patch commit 进分支
- [x] /tmp 自产清理（analyze machine dump）
- [ ] 删 worktree `mobile/build`、`.dart_tool`（收工执行）
