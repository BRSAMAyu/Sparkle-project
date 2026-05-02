# Sparkle Live Acceptance Issues — 2026-05-02

> Status: Collected during simulator-based live testing session
> Priority: P0 (blocking) → P1 (important) → P2 (improvement)

---

## P0: Aurora AI Chat Pipeline NOT Working

**Symptom**: Chat page shows "等待发送" (waiting to send), then "加载今日再来" (loading today), Aurora lamp keeps loading. The entire AI chat system is stuck. Cannot have any AI conversation.

**Impact**: Core value proposition broken. Users cannot interact with AI at all.

**Root Cause Investigation**: 
- DeepSeek API key expired (`****505f is invalid`)
- Dashscope fallback may not be properly configured
- Need to verify: WebSocket connection to Go Gateway → gRPC to Python Agent → LLM service chain

**Fix Plan**: 
1. Verify API key configuration (both DeepSeek and Dashscope/Qwen)
2. Check LLM service routing and fallback logic
3. Verify WebSocket → gRPC pipeline end-to-end
4. Test with working API key

---

## P0: Chat Page Aurora Banners — No Dismiss + Bottom Overflow

**Symptom**: 
- "Aurora当前记住" and "Aurora稍后再聊" banners permanently occupy screen space with no close/dismiss button
- "稍后再聊" causes bottom overflow when expanded

**Fix Plan**:
1. Add dismiss/close button (X) to both banners
2. Store dismissed state in provider/preferences
3. Fix bottom overflow in "稍后再聊" expanded state with proper scrolling/clamping

---

## P1: Knowledge Graph — Junk Test Nodes (FIXED)

**Status**: ✅ FIXED
- Deleted 225 "并发测试节点-*" concurrent test nodes from DB
- Remaining: 291 legitimate knowledge nodes

---

## P1: Knowledge Graph — All Gray Colors in Main View (FIXED)

**Status**: ✅ FIXED
- Root cause: Main view used `galaxyMasteryNodeColor()` (mastery-based, gray for low mastery) while minimap used `SectorConfig.resolveNodeBaseColor()` (sector-based, colorful)
- Fix: `_nodeCanvasColor()` now blends sector base color with mastery indication instead of replacing with gray

---

## P1: Home Page — Too Many Items, Misaligned Widths

**Symptom**: Home page has too many widgets stacked vertically with inconsistent horizontal widths, causing ragged, unattractive layout.

**Fix Plan**:
1. Standardize card widths (all cards same width with consistent horizontal padding)
2. Group related items
3. Consider collapsible sections

---

## P1: Home Page — "今日总览" Doesn't Collapse Properly

**Symptom**: "今日总览" (Today's Overview) takes up large space even in collapsed state. Expand/collapse doesn't significantly reduce occupied space.

**Fix Plan**:
1. True collapse: show only a summary header when collapsed (1-2 lines)
2. Animate expand/collapse with AnimatedSize or AnimatedCrossFade
3. Persist collapse state in preferences

---

## P1: Home Page — Quick Actions Show English in Chinese Mode

**Symptom**: Quick action buttons show "Create Task", "Start Focus", "View Calendar" instead of Chinese equivalents like "好奇心胶囊", "日记日历" etc.

**Fix Plan**:
1. Find the quick action button definitions in home screen
2. Replace hardcoded English strings with l10n keys
3. Add proper Chinese translations to app_zh.arb

---

## P1: Home Page — Customizable Widget Layout (Feature Request)

**Symptom**: User wants to customize which widgets appear on home page and their order, like a configurable card deck.

**Fix Plan**: 
- Create a `HomeLayoutProvider` with drag-to-reorder and toggle visibility
- Store layout preferences in SharedPreferences/secure storage
- This is a larger feature — schedule for Phase 2 sprint

---

## P1: Seed Library — Skill Marketplace Not Working

**Symptom**: Skill Marketplace shows nothing. Skills and packs cannot be displayed correctly.

**Fix Plan**:
1. Check marketplace API endpoints through gateway
2. Verify seed data exists for skills/packs
3. Check Flutter provider/repository for marketplace data

---

## P1: Community System — Wrong Default Page + Navigation Traps

**Symptom**: 
- Community entry lands on "问责空间" (Accountability) instead of the social feed (好友/群/动态)
- Once in feed page, there's no back/exit button — user gets stuck
- Friends page is usable but needs polish

**Fix Plan**:
1. Change community entry to land on social feed tab
2. Add back navigation button to feed page
3. Consider making community a main-level tab

---

## P1: Accountability Partner System Not Working

**Symptom**: Shows "伙伴工作台加载失败" (Partner workspace load failed). Demo data is not realistic and coverage is too narrow.

**Fix Plan**:
1. Check accountability API endpoint and gateway routing
2. Create more realistic demo partner data
3. Verify the partner workflow end-to-end

---

## P1: "Sparkle懂我" Feature Not Working

**Symptom**: The "Sparkle Understands Me" feature on dashboard doesn't function.

**Fix Plan**:
1. Find the feature's API endpoint and provider
2. Check if route is registered in Go gateway
3. Verify data flow

---

## P2: Demo Data Quality

**Symptom**: Demo/mock data feels unrealistic and covers too narrow a range.

**Fix Plan**:
1. Enrich seed data with more diverse, realistic content
2. Cover all major feature areas
3. Add Chinese language content where appropriate

---

## Summary

| # | Issue | Priority | Status |
|---|-------|----------|--------|
| 1 | Aurora AI Chat Pipeline stuck | **P0** | Investigating |
| 2 | Chat Aurora banners no dismiss + overflow | **P0** | Pending |
| 3 | KG junk test nodes | P1 | ✅ Fixed |
| 4 | KG all-gray colors | P1 | ✅ Fixed |
| 5 | Home page clutter + misalignment | P1 | Pending |
| 6 | 今日总览 won't collapse | P1 | Pending |
| 7 | Quick actions English in Chinese mode | P1 | Pending |
| 8 | Home customizable layout | P1 | Phase 2 |
| 9 | Skill Marketplace broken | P1 | Pending |
| 10 | Community wrong default page + trapped | P1 | Pending |
| 11 | Accountability Partner broken | P1 | Pending |
| 12 | Sparkle懂我 not working | P1 | Pending |
| 13 | Demo data quality | P2 | Pending |
