# WT336 · mobile blocker 簇 F-4 + F-8 — REPORT

- **Worker**: wt336（wt327 阵亡后原卡面重派，卡面一字未减）
- **基线**: main `24f2a245`（worktree `../Sparkle-sysrev/wt336-mobile-blockers`，branch `wt336-mobile-blockers`）
- **档位**: LIGHT（无模拟器/Gradle/浏览器；定向 flutter test 全程受 swap 门约束，见 §四）

## 一、F-4（blocker）：chat 长建议回复渲染崩溃 — 根因 + 修复

### 1.1 静态根因分析（framework 源码级实证）

wt324 附录 B 的崩溃栈 `_InactiveElements.remove ← Element._retakeInactiveElement ← Element.inflateWidget ← SingleChildRenderObjectElement.mount/updateChild` 是 **GlobalKey 认领（retake）路径**。逐帧核对 Flutter 3.41.3 framework 源码（本机 SDK，非推测）：

- 崩溃点 `framework.dart:2168` 的 `assert(_elements.contains(element))` 位于 `_InactiveElements.remove`，唯一由 `_retakeInactiveElement` 触发的失败形态是：**同帧内一个 GlobalKey 的新槽位 inflate 发生时，旧槽位上的同键 Element 尚未按框架预期的簿记状态进入 inactive 列表**（即"同键双挂/认领竞态"族崩溃）。
- 消息列表的键策略：`chat_screen.dart` 旧代码给**每条消息**持一个常驻 GlobalKey（`_messageKeys` map + `_messageKeyFor(id)`，挂在 itemBuilder 返回的 `Column` 上），而该 Column 是 **reversed 懒加载 ListView（`cacheExtent: 600`）的子项**——这是 Flutter 文档明示的高危形态：懒加载 sliver 子项按索引复用/回收，索引在每次消息追加、前缀行（状态/推理/流式气泡）进出时**整体移位**，每次移位都让同键 Element 走一次 deactivate→retake→activate 的"传送带"。
- 纯索引移位本身被框架的升序处理顺序保护（逐槽 deactivate 先于认领）；**压垮保护的是 wt315 新增的 StructuredSuggestionBody 分支**：`chat_bubble.dart:1083-1122` 在「流式完成 + 内容>500 字符 + 具列表结构」的同一帧翻转渲染分支（SparkleMarkdown→StructuredSuggestionBody 的 Column），消息子树高度/形态剧变 → LayoutBuilder 延迟布局 + sliver 窗口/cacheExtent 重算与索引移位叠加，认领时序脱离升序保护假设 → 首条长编号列表回复即触发（wt324 两次独立复现）。
- 结论：**根因=懒加载 reversed 列表子项上的常驻 GlobalKey；StructuredSuggestionBody 只是改变子树形态的触发器**。与卡面已知线索一致（structured_suggestion_body.dart 本身无 GlobalKey，碰撞在消息列表层）。

### 1.2 修复（按卡面指定方向「改用 ValueKey/localKey + 消除跨分支 reparent」）

`mobile/lib/features/chat/presentation/screens/chat_screen.dart`：

1. **列表项常驻身份键 GlobalKey → ValueKey<String>**（itemBuilder 处，原 :1832）：局部键不存在跨槽认领语义，崩溃路径按构造消除。
2. **新增 `findChildIndexCallback`（`_findChildIndexForKey`）**：`ListView.builder` → `ListView.custom` + `SliverChildBuilderDelegate`。按键找位让框架在索引移位帧走 performRebuild 的 **remap 路径**（framework sliver.dart 源码实证：按键 remap 的子项由 `updateChild` 原位搬移，根本不进 inflateWidget 的认领分支）——消息子树跨移位原位复用，顺带消除旧形态下每次追加造成的全局 deactivate/remount 抖动。瞬态定位键（GlobalKey）也被同一 callback 覆盖 remap，杜绝"定位期间恰好开跑新一轮流式"的残余竞态。
3. **「按已读位置定位」改为一次性瞬态 GlobalKey**（`_restoreTargetKey`/`_restoreTargetMessageId`）：只挂目标消息一项、定位动画 `.then` 后立即摘除（会话快速切换有接管守卫）。任意时刻至多一个 GlobalKey 在树上且唯一，无双挂可能。行为与旧实现逐位等价（同 `Scrollable.ensureVisible`，duration/curve/alignment=0.22 不变；context 为 null 时同样回落 `_scrollToBottom()`）。
4. 删除 `_messageKeys`/`_messageKeyFor`/`_pruneMessageKeys`。

### 1.3 复现测试（红测）

新增 `mobile/test/widget/chat_long_suggestion_reparent_test.dart`：按真机序列驱动完整 ChatScreen（复用 chat_scroll_test 的静默 provider harness）——滚动上移填满 viewport+cacheExtent → 追加 GENERATING 占位回复 → 原位翻转为 >500 字符长编号列表（结构化分支激活）→ 继续追加消息制造索引移位帧。判据=全程无框架异常 + StructuredSuggestionBody 在场 + 条目文本可见（错误边界兜底=内容丢失形态，同样判失败）。

**执行状态：DEFERRED** — 本机 swap free 全程 931-1043M（门限 1.2G，单批 flutter test 实测吃 ~700M，纪律禁止开跑）。红测脚本在握、修复在握，swap 门一开即可 `flutter test test/widget/chat_long_suggestion_reparent_test.dart --concurrency=1` 补跑红转绿。**故 F-4 本卡交付定级 PARTIAL（根因分析+防御性修复在库，红转绿执行证据缺）**。

## 二、F-8（minor→major）：首屏双主 CTA 视觉竞争

- `mobile/lib/features/home/presentation/widgets/onboarding_resume_card.dart`（J-02 卡，:79-90）：CTA `SparkleButton.primary` → **`SparkleButton.ghost`**（10% 表面色 tonal + brandPrimary 文字，全部既有令牌，零新色值；可点性与 persona 跳转语义不变）。cockpit「和 AI 定目标」保持 `SparkleButton.primary`（today_cockpit_card.dart:147，其注释即"全页唯一 Primary Action"，且其自身次级动作用 ghost :158——本改动使 J-02 与既有档位体系对齐）。
- 锁定测试：`onboarding_resume_card_test.dart` 首例追加「卡内零 primary 变体 + 恰一个 ghost 变体」断言，防视觉权重回升。

## 三、合并态复验清单（精确文件+行段；供主会话与 wt335 合并核对）

| 文件 | 行段（本卡坐标） | 内容 |
|---|---|---|
| `mobile/lib/features/chat/presentation/screens/chat_screen.dart` | :213-222 | 字段：`_messageKeys`→`_restoreTargetKey`/`_restoreTargetMessageId` |
| 同上 | :823 | 删 `_pruneMessageKeys(messages)` 调用 |
| 同上 | :849-933 | `_restoreReadPositionForConversation` 瞬态键挂载/摘除；`_findChildIndexForKey` 新 helper |
| 同上 | :1721-1746 | `ListView.builder`→`ListView.custom` + delegate（childCount/findChildIndexCallback） |
| 同上 | :1902-1909 | 列表项键：ValueKey + 瞬态定位键覆盖 |
| 同上 | :2296-2310 | delegate 收口（childCount + findChildIndexCallback） |
| `mobile/lib/features/home/presentation/widgets/onboarding_resume_card.dart` | :79-90 | primary→ghost |
| `mobile/test/features/home/presentation/widgets/onboarding_resume_card_test.dart` | :7、:85-103 | ghost 锁定断言 + import |
| `mobile/test/widget/chat_long_suggestion_reparent_test.dart` | 全新文件 | F-4 复现测试 |

**未碰**（对并行卡无碰撞）：`today_cockpit_card.dart`、`dashboard_screen.dart`、`routes.dart`、chat_mode 枚举、galaxy、后端全部。wt335 的 F-6（`today_cockpit_card.dart:316` 等调用点）与本卡零交集。

## 四、验证与环境

- **守卫**：`bash scripts/run_all_rule_guards.sh` → **83 条全过，exit 0**。
- **analyze 门**：`check_flutter_analyze_gate.py` → **E0/W15/I598，与 main 基线逐位一致，零漂移**（过程中 dart fix --apply 意外重排了 gitignored 链路外的 l10n 三个生成文件，已当即 `git checkout --` 还原，未入提交）。
- **mypy**：本卡未动 backend，基线 1615 天然不推高。
- **flutter test**：受 16GB 内存纪律 swap 门（free≥1.2G）约束，开工至收工全程 931-1043M 未开 → 定向批（F-4 复现测试 + chat_scroll_test + onboarding_resume_card_test + chat_area_budget_test）DEFERRED。修复不含行为语义变更（ensureVisible 参数逐位保持；键策略变更由静态分析+框架源码推演背书），但**红转绿执行证据缺失，F-4 判 PARTIAL**。
- **gen 三件套**：主仓只读 `cp -RL` 拷入 worktree（mobile/backend app/backend gateway）。

## 五、后续（超本卡范围，登记舰队池）

1. **group_chat_screen.dart:55-57,140-141 同款常驻 GlobalKey 模式**（群聊命中定位），与 chat_screen 修复前同构——群聊消息不经 StructuredSuggestionBody 故暂无触发器，属同族潜伏债务，建议独立卡按同方案（ValueKey + findChildIndexCallback + 按需瞬态键）处理；其搜索跳转是会话中任意时刻动作，瞬态键窗口设计需单独论证，不宜顺手改。
2. F-4 补跑红转绿后，可将「懒加载列表禁常驻 GlobalKey」写进 lint/守卫或 review checklist（本次三处 GlobalKey 病灶中两处在 chat 域）。

## 六、收工清单

- [x] 守卫 83 exit 0
- [x] analyze 门零漂移
- [x] mypy 不涉及
- [x] REPORT.md + changes.patch commit 进分支
- [ ] 删 worktree `mobile/build`、`.dart_tool`（收工执行）
- [ ] /tmp 自产文件清理（guards 日志、analyze 中间文件）
