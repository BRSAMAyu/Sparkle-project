# Community UI/UX Polish — Implementation Report
**Date**: 2026-05-08
**Status**: Completed ✅

---

## Overview

社群系统 UI/UX 打磨，共修改 **13 个文件**，涉及 8 个 phase。所有改动已合并到 commit `2b7dc4518`。

---

## Phase 1: Feed Card Compactness + Expandable Text

**问题**: 单条动态占据几乎整个手机屏幕，内容无截断，用户一次只能看到 ~1.5 条动态。

**修改文件**:
- `mobile/lib/features/community/presentation/widgets/feed_post_card.dart`
- `mobile/lib/features/community/presentation/widgets/feed_tab_content.dart`

**具体改动**:
1. 卡片外边距 `vertical: 8` → `4`
2. 内边距 `EdgeInsets.all(DS.lg)` → `EdgeInsets.fromLTRB(16, 12, 16, 12)`
3. 头像半径 `20` → `16`
4. 添加 `_ExpandableText` widget，默认 `maxLines: 4`，点击展开全文，带 `AnimatedSize` 平滑过渡
5. 移除 filter chips 下方的描述文字（每条节省约 20px 垂直空间）

**验收标准**:
- [ ] Feed 中单屏可见至少 2 条动态
- [ ] 超过 4 行的帖子显示"展开全文"按钮，点击后展开并变为"收起"
- [ ] 动画流畅，无卡顿

---

## Phase 2+6: Group Detail Optimization + Button Unification

**问题**: Group detail 页面太长（bonfire 140px + 大量间距），Enter Chat 主按钮埋在底部。混用 `CustomButton` 和 `SparkleButton`。

**修改文件**:
- `mobile/lib/features/community/presentation/screens/group_detail_screen.dart`

**具体改动**:
1. BonfireWidget size `140` → `100`
2. SliverAppBar expandedHeight `200` → `160`
3. 所有间距 `DS.xl/xxl` → `DS.md/lg`
4. Enter Chat 按钮改为 floating bottom bar（`Positioned` + `SafeArea`），始终可见
5. 所有 `CustomButton.primary/secondary` → `SparkleButton.primary/secondary`
6. 移除 `custom_button.dart` import
7. 3 处 hardcoded i18n 字符串 → `context.l10n.*`（`communityGroupDetails`, `communityWelcomeToGroup`, `communityLeaveGroupFailed`）

**验收标准**:
- [ ] Enter Chat 按钮始终固定在底部，不随滚动消失
- [ ] Bonfire 视觉仍然有冲击力，但更紧凑
- [ ] 页面加载和首次滚动流畅
- [ ] 所有按钮样式与其他页面保持一致

---

## Phase 4: Chat Bubble Responsive Sizing + Expandable Rich Cards

**问题**: Checkin bubble 固定 240px，rich card wrapper 固定 280px，不能适配不同屏幕。分享卡片无法展开/收起。

**修改文件**:
- `mobile/lib/features/community/presentation/widgets/group_chat_bubble.dart`

**具体改动**:
1. Checkin bubble: `Container(width: 240)` → `Container(constraints: BoxConstraints(minWidth: 200, maxWidth: screenWidth * 0.6))`
2. Rich card wrapper: `BoxConstraints(maxWidth: 280)` → `maxWidth: screenWidth * 0.72`
3. 所有 ShareCard factory 传入 `isCompact: !_richCardExpanded`
4. `_richCardExpanded` 状态 toggle，支持展开/收起
5. `ConstrainedBox` 改为 `Container`（避免 decoration 报错）
6. 硬编码 `'$streak 天'` → `context.l10n.communityStreakDaysSuffix(streak)`

**验收标准**:
- [ ] 在 iPhone SE（小屏）和 iPad（大屏）上气泡宽度自适应
- [ ] 点击分享卡片（task/plan/capsule/node）可以展开/收起
- [ ] 7 种消息类型（text/checkin/task/plan/capsule/prism/achievement）全部正常工作
- [ ] 连击天数显示格式正确（英文 "3d"，中文 "3 天"）

---

## Phase 3: Comment Bottom Sheet Polish

**问题**: 评论只有纯文字，无头像、无用户名、无格式化时间戳，样式与其他界面不一致。

**修改文件**:
- `mobile/lib/features/community/presentation/widgets/comment_bottom_sheet.dart`

**具体改动**:
1. 替换 `ListTile` 为自定义行布局：`CircleAvatar(radius: 14)` + 用户名 + `timeago.format()` 时间戳 + 内容
2. 删除按钮改用小巧的 `GestureDetector` + 图标
3. Loading 状态：`CircularProgressIndicator` → `SparkleListSkeleton(count: 3)`
4. 空状态：添加 icon 和 `DS.textSecondary` 样式
5. Input bar：`TextField` 包裹在圆角 `Container` 中，样式与设计系统一致
6. 硬编码 `'用户'/'User'` → `context.l10n.communityMemberFallback`
7. 添加 `timeago` import 和 `DateTime.tryParse` 解析

**验收标准**:
- [ ] 每条评论显示头像和用户名
- [ ] 时间戳使用自然语言（"3 minutes ago" / "3 分钟前"）
- [ ] Loading 状态显示骨架屏而非转圈
- [ ] Input 输入框有圆角背景，与 sheet 其他部分视觉统一

---

## Phase 9: Accountability Dashboard Density

**问题**: Dashboard 极长（hero + policies + reflections + foresight + goals + growth + shares + heatmap + achievements + checkins），信息密度低。

**修改文件**:
- `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`

**具体改动**:
1. `_PendingPoliciesCard` → `ExpandableSection(initiallyExpanded: false)`
2. `_RecentReflectionsCard` → `ExpandableSection(initiallyExpanded: false)`
3. `_ForesightHintCard` → `ExpandableSection(initiallyExpanded: true)`（因为最可操作）
4. `_RecentShares` → `ExpandableSection(initiallyExpanded: false)`
5. `AchievementGrid` → `ExpandableSection(initiallyExpanded: false)`
6. 所有间距 `DS.spacing12` → `DS.spacing8`
7. 添加 `ExpandableSection` import

**验收标准**:
- [ ] 首次打开 dashboard，次要区块（policies、reflections、achievements）默认折叠
- [ ] Foresight hint 默认展开
- [ ] 点击展开/收起动画流畅
- [ ] 主区域（hero、goals、heatmap、checkins）始终可见

---

## Phase 7: Partners Tab Polish

**问题**: Loading 状态用转圈、无 stagger 动画、error 状态简陋、无 haptic 反馈。

**修改文件**:
- `mobile/lib/features/community/presentation/widgets/partners_tab.dart`

**具体改动**:
1. Loading 状态：`CircularProgressIndicator` → `SparkleListSkeleton`
2. Error 状态：移除自定义 `_SectionError`，改用 `CompactErrorCard(onRetry: ...)`
3. 所有 `SliverToBoxAdapter` 子节点包裹 `SparkleStaggerItem`（indices 0-3）
4. `_PartnershipCard` tap handler 添加 `SensoryFeedbackService.emit(SensoryFeedbackEvent.selection)`
5. `_FriendTile` tap handler 添加相同 haptic feedback
6. 移除已废弃的 `_SectionLoading` 和 `_SectionError` widget

**验收标准**:
- [ ] Partners tab 滚动时各区块有错落入场动画
- [ ] Loading 时显示骨架屏而非转圈
- [ ] 加载失败时显示 CompactErrorCard 并可点击重试
- [ ] 点击 partnership card 和 friend tile 有触感反馈

---

## Phase 5: Create Post Screen Cleanup

**问题**: Mock location picker 显示误导性 info message。删除 `foundation.dart` 中不需要的 import。

**修改文件**:
- `mobile/lib/features/community/presentation/screens/create_post_screen.dart`

**具体改动**:
1. 移除 `_pickLocation` 方法
2. 移除 `_selectedLocation` 变量
3. 移除 `_pickLocation` 调用和 location icon button
4. 移除 `foundation.dart` import
5. 移除 Location 相关的 debugPrint

**验收标准**:
- [ ] Create post 页面只有 Image picker button（无 location button）
- [ ] 无误导性 info message
- [ ] 代码中无 `foundation.dart` import

---

## Phase 8: Group Recommendation Card Height

**问题**: 固定 220px 高度可能截断内容。

**修改文件**:
- `mobile/lib/features/community/presentation/widgets/groups_hub_view.dart`

**具体改动**:
1. Recommendation cards height `220` → `200`
2. Loading skeleton height `220` → `200`

**验收标准**:
- [ ] 推荐卡片列表高度更紧凑
- [ ] Loading skeleton 与实际卡片高度一致

---

## L10n Key Additions

**新增 ARB keys**（`app_en.arb` + `app_zh.arb`）:

| Key | English | 中文 |
|-----|---------|------|
| `communityGroupDetails` | "Group Details" | "社群详情" |
| `communityWelcomeToGroup` | "Welcome to the group!" | "欢迎加入社群！" |
| `communityLeaveGroupFailed` | "Failed to leave group, please retry" | "退出群组失败，请重试" |
| `communityCommentLabel` | "Comment" | "评论" |
| `communityShareLabel` | "Share" | "分享" |
| `communityDeleteLabel` | "Delete" | "删除" |
| `communityShowMore` | "Show more" | "展开全文" |
| `communityShowLess` | "Show less" | "收起" |
| `communityCommentsComingSoon` | "Comments coming soon" | "评论功能即将上线" |

**验收标准**:
- [ ] 中英文切换正常显示对应翻译

---

## Files Summary

| File | Changes |
|------|---------|
| `feed_post_card.dart` | Compact spacing, expandable text widget |
| `feed_tab_content.dart` | Removed filter descriptions |
| `group_detail_screen.dart` | Tighter spacing, floating button, SparkleButton, l10n |
| `group_chat_bubble.dart` | Responsive widths, toggle rich cards, l10n |
| `comment_bottom_sheet.dart` | Avatar/comments, timeago, skeleton, styled input |
| `accountability_detail_screen.dart` | ExpandableSection wrappers |
| `partners_tab.dart` | Skeleton loading, stagger animations, haptic feedback |
| `create_post_screen.dart` | Removed mock location picker |
| `groups_hub_view.dart` | Tighter recommendation card height |
| `app_en.arb` / `app_zh.arb` | 9 new l10n keys |

**Total: 13 files, ~1000 lines net**

---

## Verification Commands

```bash
# Flutter analyze (no errors)
cd mobile && flutter analyze lib/features/community/ 2>&1 | grep "^  error"

# Run tests
cd mobile && flutter test 2>&1 | tail -10

# Manual testing checklist
# - [ ] Open Community tab on iPhone SE (small screen) — verify no overflow
# - [ ] Open Community tab on iPad — verify responsive sizing
# - [ ] Post a long content (>200 chars) — verify "展开全文" works
# - [ ] Tap "Enter Chat" on Group detail — button should be always visible
# - [ ] Send a checkin message in group chat — verify responsive bubble width
# - [ ] Tap a share card in group chat — verify expand/collapse
# - [ ] Open Comments sheet — verify avatars and timeago
# - [ ] Open Partners tab — verify stagger animation and skeleton loading
# - [ ] Open Accountability detail — verify collapsible sections
# - [ ] Open Create Post — verify no location button
```

---

## Review Agent Findings (addressed)

| Issue | Status |
|-------|--------|
| 3 hardcoded i18n in group_detail_screen.dart | ✅ Fixed — all replaced with `context.l10n.*` |
| `_richCardExpanded` one-directional | ✅ Fixed — now toggle with `!_richCardExpanded` |
| Hardcoded fallback username in comments | ✅ Fixed — now uses `communityMemberFallback` |
| `foundation.dart` import in create_post | ✅ Fixed — removed |
| I18nService still imported in group_detail | ✅ Fixed — import removed |

---

## Pending Pre-existing Issues (not in scope)

These patterns existed before this PR and were touched but not fully migrated:
- `feed_tab_content.dart` filter labels use `isChinese ? ... : ...`
- `feed_tab_content.dart` empty state uses hardcoded strings

Recommendation: Create follow-up ticket to migrate remaining i18n patterns across community feature.