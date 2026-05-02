# Sparkle Live Acceptance Issues — 2026-05-02

> Status: Collected during simulator-based live testing session  
> Priority: P0 (blocking) → P1 (important) → P2 (improvement)  
> Updated continuously as new issues are discovered

---

## P0: Performance — All Pages Load Extremely Slowly / Timeout

**Symptom**: Every page navigation takes very long to load. Task detail page doesn't navigate correctly. Connection timeouts happen frequently. Pages show retry-only error with NO back/exit button.

**Fix Plan**:
1. Investigate Redis timeout issues (consumer group spam was flooding Redis)
2. Add back/exit buttons to ALL error/retry pages
3. Optimize API response times
4. Fix task navigation routing

---

## P0: Aurora AI Chat Pipeline Stuck

**Symptom**: Chat shows "等待发送" then "加载今日再来". Aurora lamp keeps loading. Cannot have any AI conversation.

**Root Cause**: Redis timeouts causing 502 errors on aurora/control-surface and WebSocket keepalive failures. Consumer group spam was flooding Redis.

**Status**: Redis consumer groups created. Need to verify chat works now.

**Fix Plan**:
1. ✅ Created missing Redis consumer groups (galaxy_sse_bridge, achievement_consumer, etc.)
2. Verify WebSocket → gRPC → LLM chain works end-to-end
3. If DeepSeek key is expired, ensure fallback to working provider

---

## P0: All Error Pages Need Exit/Back Buttons

**Symptom**: When a page fails to load, only shows "Retry" button with no way to go back. User gets trapped.

**Fix Plan**: Audit all error states and add back/exit navigation to every error screen.

---

## P1: Chat Aurora Banners — No Dismiss + Bottom Overflow (FIXING)

**Status**: ✅ Code fixed, pending hot reload
- Added dismiss X button to ChatWorkingMemoryPanel
- Added dismiss X button to StatusAwarenessBar  
- Reduced deep expansion max height from 62% to 45% of screen
- Both widgets now hide when dismissed

---

## P1: Knowledge Graph — Junk Test Nodes (FIXED)

**Status**: ✅ FIXED
- Deleted 225 "并发测试节点-*" concurrent test nodes from DB
- Remaining: 291 legitimate knowledge nodes

---

## P1: Knowledge Graph — All Gray Colors in Main View (FIXED)

**Status**: ✅ Code fixed, pending hot reload
- `_nodeCanvasColor()` now blends sector base color with mastery indication
- Low-mastery nodes show sector color at 35% opacity instead of pure gray

---

## P1: Home Quick Actions — English in Chinese Mode (FIXING)

**Status**: ✅ Code fixed, pending hot reload
- Replaced all hardcoded English strings in intent_prediction_provider.dart with `I18nService.instance.isChinese` pattern
- Covers: Create Task, Start Focus, View Calendar, Curiosity Capsule, Send to AI, Note Idea, etc.

---

## P1: Home Page — Too Many Items, Misaligned Widths

**Symptom**: Home page has too many widgets stacked vertically with inconsistent horizontal widths.

**Fix Plan**: Standardize card widths, group related items.

---

## P1: Home Page — 今日总览 Won't Collapse + Has Garbled Text

**Symptom**: 
1. "今日总览" takes up large space even in collapsed state
2. Shows garbled text ("??") in the summary text (e.g. "??重点动作")

**Fix Plan**:
1. True collapse: show only 1-2 line summary when collapsed
2. Fix the garbled text / encoding issue in summary rendering

---

## P1: Home Page — Customizable Widget Layout

**User Request**: All home page widgets should be user-configurable (show/hide, reorder).

**Status**: Feature request — Phase 2 sprint

---

## P1: Seed Library — Skill Marketplace Not Working

**Symptom**: Skills and packs cannot be displayed. Marketplace shows nothing.

---

## P1: Community System — Wrong Default Page + Navigation Traps

**Symptom**: 
1. Community entry lands on "问责空间" instead of social feed
2. Feed page has no back button — user gets stuck
3. Friends page needs polish

**User Request**: Community should be a main-level tab with proper navigation.

---

## P1: Accountability Partner System Broken

**Symptom**: Shows "伙伴工作台加载失败". The naming changed from "责任伙伴" to "问走" which is wrong.

**Fix Plan**:
1. Fix naming back to "责任伙伴"
2. Fix API endpoint
3. Create realistic demo data

---

## P1: Sparkle懂我 Not Working

**Symptom**: Feature on dashboard doesn't function.

---

## P1: Learning Profile / 画像 — Stuck Loading

**Symptom**: Profile page shows permanent loading state, can't enter. The profile editing is a simple form, not the interactive modeling we designed.

---

## P1: Weekly Story / 本周故事 — Not Working

**Symptom**: Cannot be used correctly.

---

## P1: Notification Settings — Can't Collapse

**Symptom**: In personal settings, notification settings displays all content expanded with no collapse option. Wastes space.

---

## P1: Tools Library — All English Names

**Symptom**: 
1. Tool quick-access names are all in English (should be bilingual)
2. Settings button is labeled "计划谬误" (wrong label)
3. Tool library entries are all English
4. All tools must actually work

---

## P1: Learning Simulation — Not Working

**Symptom**: Learning scene simulation is non-functional. Task AI assistant and guide also don't work.

---

## P1: Multi-Goal Dashboard — Large Space, Can't Collapse

**Symptom**: Shows 3 goals but takes up too much space with no collapse option.

---

## P1: Learning Profile and Related Cards — Take Too Much Space

**User Suggestion**: Working memory, planning, achievement summary, active skills, participation status, foresight hints — these are all feedback-type displays that should be compressed into a secondary page or grouped together instead of flat-expanded in the settings page.

---

## P2: Demo Data Quality

**Symptom**: Demo data is unrealistic and covers too narrow a range.

---

## P2: Poster Workshop — Yellow Lines Under Text

**Symptom**: All generated text has ugly yellow double-lines underneath. Middle section looks bad.

---

## P2: Achievement System — No Achievements Visible

**Symptom**: No achievements visible. Should have system-provided default data.

---

## P2: Learning Materials Library — Not Usable

**Symptom**: Learning materials library is non-functional.

---

## P2: Cognitive Analysis / Pattern Reading — No Content

**Symptom**: Pattern reading shows no content.

---

## P2: System Updates and Memory Settings — No Real Data

**Symptom**: No real data visible in system updates or memory settings.

---

## Summary Table

| # | Issue | Priority | Status |
|---|-------|----------|--------|
| 1 | Performance / slow loading / timeouts | **P0** | Investigating |
| 2 | Aurora AI Chat Pipeline stuck | **P0** | Redis fixed, verifying |
| 3 | All error pages need exit buttons | **P0** | Pending |
| 4 | Chat Aurora banner dismiss + overflow | P1 | ✅ Code fixed |
| 5 | KG junk test nodes | P1 | ✅ Fixed |
| 6 | KG all-gray colors | P1 | ✅ Code fixed |
| 7 | Quick actions English in Chinese mode | P1 | ✅ Code fixed |
| 8 | Home page clutter + misalignment | P1 | Pending |
| 9 | 今日总览 won't collapse + garbled text | P1 | Pending |
| 10 | Home customizable layout | P1 | Phase 2 |
| 11 | Skill Marketplace broken | P1 | Pending |
| 12 | Community wrong default + trapped | P1 | Pending |
| 13 | Accountability Partner broken | P1 | Pending |
| 14 | Sparkle懂我 not working | P1 | Pending |
| 15 | Profile/画像 stuck loading | P1 | Pending |
| 16 | 本周故事 not working | P1 | Pending |
| 17 | Notification settings can't collapse | P1 | Pending |
| 18 | Tools Library all English + wrong labels | P1 | Pending |
| 19 | Learning simulation not working | P1 | Pending |
| 20 | Multi-goal dashboard too large | P1 | Pending |
| 21 | Feedback cards take too much space | P1 | Pending |
| 22 | Demo data quality | P2 | Pending |
| 23 | Poster workshop yellow lines | P2 | Pending |
| 24 | Achievement system empty | P2 | Pending |
| 25 | Learning materials not usable | P2 | Pending |
| 26 | Pattern reading no content | P2 | Pending |
| 27 | System updates no data | P2 | Pending |
