# R11/R2A6: Community & Social Experience -- Pre-Launch Audit Report

**Date**: 2026-05-07
**Auditor**: Claude Code (automated deep-audit)
**Scope**: Full-stack community/social features -- Flutter, Go Gateway, Python Engine
**Files Reviewed**: 80+ source files across all three layers

---

## Executive Summary

The community module is **architecturally mature** and well-aligned with the "accountability space" vision. The 3-tab shell (Partners / Feed / Groups) correctly prioritizes accountability over social feed. The accountability hub, commitment cards, partner observation controls, and privacy-preserving cohort intelligence represent genuinely differentiated design.

However, several **P0 gaps** remain that would degrade the cold-start user experience or break core accountability flows in production. The feed subsystem is significantly less mature than the groups/accountability subsystem. There are also missing features (comment system, content reporting UI, push notifications) that exist as backend code but lack Flutter integration.

**Verdict**: Accountability features are **launch-ready** with P0 fixes. Feed/social features need **another iteration**.

---

## 1. Community Home Screen

### Architecture

`CommunityMainScreen` (3-tab flat architecture):
- Tab 0: Partners (default landing) -- accountability hub, partnerships, friends
- Tab 1: Feed -- social posts with filters
- Tab 2: Groups -- study groups and recommendations

### Assessment

**PASS** -- The default tab is "Partners" (伙伴), not "Feed". This correctly implements the accountability-first vision. The subtitle reads "Grow together with partners" (和伙伴一起成长), not a social-media tagline.

**PASS** -- Empty state on Partners tab shows "Find your study partners" with CTA to discover partners, not an empty social feed.

**PASS** -- Tab labels are properly i18n'd via `I18nService.instance.isChinese`.

**PASS** -- FAB (create post button) only appears on Feed tab (index 1), not Partners tab.

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P0-01 | **P0** | No `home` route defined -- `CommunityRoutes.home = '/community'` exists as a constant but is never registered in `routes`. Users navigating to `/community` will 404. | `community_routes.dart:30` |
| COM-P2-01 | P2 | `community.dart` barrel file was not reviewed but referenced -- verify it exports all needed symbols | `community.dart` |

---

## 2. Accountability Features (Vision Alignment)

### CommitmentCard Widget

**PASS** -- `CommitmentCard` widget exists at `widgets/accountability_hub/commitment_card.dart`. It displays:
- Status pill (active/due_soon/completed/violated)
- Summary text (expandable)
- Progress bar with percentage
- Due date and witness names as meta chips
- "Allow partner reminders" toggle (per-commitment boundary)
- Expanded detail section with success criteria, milestones, evidence refs

This is a genuinely well-designed accountability widget that goes beyond social-media "likes."

### Accountability Hub Screen

**PASS** -- `AccountabilityHubScreen` provides a full dashboard:
- Header metrics (commitments count, partner progress count, helpable count)
- My Commitments section (horizontal scroll)
- Partner Progress section (circular progress + today's status)
- Shared Goals section (progress bar + member chips)
- Needs Attention section (squad risks + helpable partners)
- Strategy section (adaptive recommendations)
- Secondary entry points (feed, friends, groups)

### Partner Observation

**PASS** -- `PartnerObservationSettings` widget provides granular opt-out:
- Toggle: "Allow observation" (master switch)
- Checkbox: "See my study time"
- Checkbox: "See specific task content"
- Checkbox: "See my emotional / energy state"

**PASS** -- `PartnerObservationControl` handles per-reminder accept/decline/later/too-frequent with undoable feedback.

### Accountability Detail Screen (Partner Workspace)

**PASS** -- `AccountabilityDetailScreen` provides a full partner workspace:
- Partner dashboard with heatmap
- Achievement badges
- Quick actions (check-in, nudge, share progress)
- End partnership option
- Statistics (streak days, check-in counts)

### Partners Tab (Default Landing)

**PASS** -- `PartnersTab` surfaces:
1. CommunityAccountabilityHubCard (top)
2. Active partnerships list (avatar, name, goal, streak, check-in status)
3. Hub sections: My Commitments, Partner Progress, Needs Attention, Encourage
4. Friends list (first 5 with "View all")
5. Empty state with "Discover partners" CTA

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P1-01 | **P1** | CommitmentCard width is hardcoded to 304px -- will clip on narrow devices or waste space on tablets | `commitment_card.dart:38` |
| COM-P1-02 | **P1** | `_PartnerAvatar` uses `isOnline` parameter but maps it from `partnerCheckedInToday` which is NOT the same as online status. Green dot misrepresents online presence. | `partners_tab.dart:196-199` |
| COM-P2-02 | P2 | No commitment creation flow visible -- hub shows commitments but there is no explicit "Create Commitment" button/screen in the routes | Routes audit |

---

## 3. Groups

### Group Types

Proto defines three types: `SQUAD` (long-term study team), `SPRINT` (short-term sprint), `OFFICIAL` (official course/exam group).

### Group Detail Screen

**PASS** -- `GroupDetailScreen` provides:
- Collapsible SliverAppBar with hero avatar
- Sprint countdown timer (days remaining)
- BonfireWidget (flame level visualization)
- Stats row (members/flame power/today check-ins)
- Description, focus tags, announcement
- Member actions (enter chat, tasks, members, knowledge base)
- Non-member: join button
- Admin: edit announcement dialog
- Leave group with confirmation dialog
- Two tabs: Overview + Knowledge Base

### Group Discovery

**PASS** -- `GroupDiscoverScreen` provides:
- Search bar with keyword filtering
- Sort options (hot/latest/random)
- Type filter (squad/sprint)
- Tag-based filtering (from DB `get_public_tags`)
- AI-powered recommendations (horizontal scroll cards)
- Recommendation feedback system (calibration prompts + insight cards)
- Activity score display per group

### Group Knowledge Base

**PASS** -- Python backend has full `GroupKnowledgeService`:
- Knowledge base document management with trust levels (member/verified/official)
- Collaborative galaxy projection (document + knowledge node graph)
- Polar position layout for galaxy visualization
- Quality scoring, citation/download counts, average ratings

### Group Tasks

**PASS** -- `GroupTaskService` provides:
- Task creation (admin/owner only)
- Task claiming (creates personal task copy, links via GroupTaskClaim)
- Task completion (triggered from personal task completion, uses SAVEPOINT + row-level locking)
- Sprint progress sync to personal plans

### Group Messaging

**PASS** -- `GroupMessageService` is comprehensive:
- Send/edit/revoke messages
- Reply-to and thread support
- Mention validation (must be group member)
- Slow mode enforcement
- Keyword filter via `ModerationService`
- Reaction system (emoji reactions)
- Read receipts (`GroupMessageRead`)
- Message search
- System messages
- Visibility controls (`_is_visible_to` for self-only messages)

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P1-03 | **P1** | Group chat route uses hardcoded `/chat/group/${groupId}` but there is no registration of this route in `CommunityRoutes`. Depends on a separate chat routing module being correctly wired. | `group_detail_screen.dart:365` |
| COM-P1-04 | **P1** | Sprint groups show `deadline` in detail but there is no "sprint completed" celebration or auto-archival flow visible. Dead sprint groups will persist indefinitely. | `group_detail_screen.dart` |
| COM-P2-03 | P2 | Group creation screen imports exist but the flow is not audited -- verify it properly sets `GroupType`, `max_members`, and `join_requires_approval` | `create_group_screen.dart` |
| COM-P2-04 | P2 | `Official` group type (OFFICIAL=3) is defined in proto but no UI for creating or discovering official groups exists | Proto + Flutter |

---

## 4. Friends & Partners

### Friend Request Flow

**PASS** -- Full flow exists:
- Send friend request with match reason
- "Mutual liking" auto-accept (if reverse pending request exists)
- Accept/decline with feedback
- Privacy-respecting search (`SearchVisibility`: everyone/friends/nobody)
- Block check before request

### Friend Recommendations

**PASS** -- Sophisticated recommendation system:
- Two strategies: `compatibility` and `complementary`
- Match score with percentage display
- Match reasons list (explanation)
- Privacy notice prominently displayed
- Calibration prompts for feedback collection
- Feedback insight cards showing recent feedback stats
- Recommendation feedback system with multi-dimensional scoring (relevance, explanation, actionability, etc.)
- Can invite accountability partner directly from recommendation card

### Accountability Partner Invitation

**PASS** -- From friend recommendation, users can:
- Invite as accountability partner with goal text
- Set check-in cadence (1/2/3/7 days)
- Automatic conflict detection ("already has core partner")
- Resolution routing on conflict

### Partner Matching (Similar Goals)

**PASS** -- `find_users_with_similar_goals()` in Python:
- Embedding-based title similarity (cosine)
- Fallback to lexical similarity (SequenceMatcher + token overlap)
- Type match scoring
- Time window overlap scoring
- Combined formula: title_vector_sim * 0.5 + type_match * 0.3 + time_overlap * 0.2
- Mutual friends count for each candidate

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P0-02 | **P0** | `_handleDeleteFriend` and `_handleBlockUser` methods exist in `_MyFriendsTab` but `_showFriendContextMenu` is **never called** from any UI element. Users cannot access block/delete functionality -- the long-press/menu trigger is missing. | `friends_screen.dart:120-208` |
| COM-P2-05 | P2 | `FriendsHubView` widget is imported but not audited -- verify it properly handles empty state and loading | `friends_hub_view.dart` |

---

## 5. Posts & Content

### Post Creation

**PARTIAL** -- `CreatePostScreen` supports:
- Text content (8 lines, auto-focus)
- Topic/hashtag (optional, prefixed with #)
- Image picker (from gallery)
- Location picker (**stub** -- shows "Mock Location" and "under development" message)
- Optimistic posting with loading indicator

### Post Feed

**PARTIAL** -- `FeedTabContent` supports:
- Filter chips: Global Feed / My Squad / Goal Mates / Following
- Scope-based filtering with descriptions
- `FeedPostCard` with avatar, username, timeago, content, image, like count, topic tag
- Optimistic like toggle
- Empty state with "Share a post" CTA
- Error state with retry

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P0-03 | **P0** | Comment button in `FeedPostCard` renders but has **no `onTap` handler**. The comment system does not exist in either Go or Flutter. The DB `posts` table has `comment_count` column but no comment CRUD API. | `feed_post_card.dart:170-173` |
| COM-P0-04 | **P0** | Feed data comes entirely from Redis cache (`CommunityQueryService.GetGlobalFeed`). There is **no fallback to DB** when Redis cache misses. On cache miss, posts silently disappear. The `community_sync.go` worker populates Redis, but any sync delay = empty feed. | `community_query.go:36-77` |
| COM-P1-05 | **P1** | Like toggle uses optimistic update but **does not track user's like state**. The `Post` model has `likeCount` but no `isLikedByMe` boolean. Users cannot see which posts they've already liked. | `community_providers.dart:34-57` |
| COM-P1-06 | **P1** | Post `topic` field is a plain string, not a reference to a topics table. There is no topic validation, suggestion, or trending topics feature. Topics are just hashtags with no semantic meaning. | `create_post_screen.dart:134` |
| COM-P1-07 | **P1** | Image URL in `CreatePostScreen` sends local file path (`_selectedImage!.path`) to `addPostOptimistically`. There is no image upload to storage service before post creation. Images will not render for other users. | `create_post_screen.dart:60` |
| COM-P2-06 | P2 | Location picker is a stub -- shows mock data. This feature is incomplete. | `create_post_screen.dart:42-48` |
| COM-P2-07 | P2 | No post deletion UI -- Go has `DeletePost` command but Flutter has no delete button on posts | `community_command.go:204` |

---

## 6. Achievement Integration

### Social Celebration

**PARTIAL** -- Python `CommunitySignalBridge.broadcast_achievement_unlock()`:
- Publishes achievement unlock event to Redis channel `community:achievements`
- Includes achievement_id, title, rarity
- Event bus event `community.achievement_unlocked`

**GAP** -- No Flutter widget subscribes to `community:achievements` Redis channel or renders achievement celebrations in the community feed.

### Group Milestones

**PARTIAL** -- Group model has `total_tasks_completed`, `total_flame_power`, `today_checkin_count` but no milestone/celebration triggers exist.

### Group Streaks

**PASS** -- `GroupMember` has `checkin_streak` field. Check-in service calculates streak correctly (consecutive days).

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P1-08 | **P1** | Achievement unlocks are broadcast but **never consumed** by Flutter. No real-time achievement celebration appears in community. | `community_signal_bridge.py:532-572` |
| COM-P2-08 | P2 | No group-level achievement system -- individual achievements don't aggregate into group milestones | -- |

---

## 7. Real-time Features

### Community WebSocket

**PASS** -- `CommunityWebSocketService` provides:
- Group channel WebSocket connection
- Personal channel WebSocket connection
- Exponential backoff reconnection (base 1s, max 30s, 10 attempts)
- Message deduplication (1000-message ID cache)
- ACK system with nonce-based callbacks
- Typing indicator support
- Connection state streaming (disconnected/connecting/connected/reconnecting/error/failed)

### Online Status

**PARTIAL** -- Partners tab shows green dot for "checked in today" but this is NOT actual online status. There is no WebSocket-based online/presence tracking.

### Push Notifications

**GAP** -- No push notification integration exists for community events (new messages, friend requests, accountability invites, check-in reminders). The notification service is referenced but community-specific notifications are not wired.

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P0-05 | **P0** | No push notifications for community events. Users will miss friend requests, accountability invitations, group messages, and check-in reminders when the app is backgrounded. This breaks the accountability loop. | -- |
| COM-P1-09 | **P1** | No real online/presence system. Green dot on partner avatars represents "checked in today", not actual online status. Users may be misled. | `partners_tab.dart:727-735` |
| COM-P2-09 | P2 | Community WebSocket service exists but group chat screen integration was not audited -- verify it properly connects to group WS and renders real-time messages | `community_websocket_service.dart` |

---

## 8. Privacy & Safety

### Content Moderation

**PASS** -- Python `ModerationService` in `community_advanced_service.py` provides:
- Keyword filter enforcement on group messages
- Message reporting system (`MessageReport` model, `ReportStatus` enum)
- Report review workflow (`MessageReportReview` schema)
- Resource quality scoring with auto-hide (`CommunityResourceScorer`)
- Misleading resource flagging (`flag_misleading`)

### Block/Report User

**PASS** -- Full block system:
- `UserBlockService` with block/unblock/list operations
- Auto-remove friendship on block
- Auto-end accountability partnerships on block
- Block check in friend request, private message, and user search flows
- `BlockedUsersScreen` in Flutter for managing blocked users

### Privacy Settings

**PASS** -- User search visibility control:
- `SearchVisibility` enum (everyone/friends/nobody)
- `UserSearchService.search_users()` respects privacy settings
- `update_searchability()` and `get_user_searchability()` API

### Community Intelligence Privacy

**PASS** -- `CommunitySignalBridge` implements:
- Differential privacy with epsilon budget
- Daily privacy budget tracking (`PrivacyBudgetLedger`)
- Minimum cohort size (k=5) enforcement
- Contributor opt-out filtering
- Aurora sanitization (strips names, emails, raw content)
- Kill switch integration (`AuroraStage33KillSwitchService`)

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P1-10 | **P1** | Message report UI exists in Python (models, schemas, service) but **no Flutter UI** for reporting messages. Users cannot flag inappropriate content from the app. | -- |
| COM-P2-10 | P2 | No content moderation for feed posts -- keyword filter only applies to group messages, not to the public feed | `community_service.py:1556-1559` |

---

## 9. Proto Contract

### Status

The proto `community_service.proto` is **marked deprecated** with comment: "Sparkle community features are served by REST/gateway CQRS. This proto is retained only as compatibility documentation."

This means community features use REST API through the Go gateway, not gRPC. The Go gateway has:
- `POST /community/posts` (create post)
- `POST /community/posts/:id/like` (like post)
- `GET /community/feed` (get feed, no auth required)

**GAP** -- The Go community handler only covers posts/feed/likes. All group, friend, message, checkin, accountability, and privacy operations go through Python REST API directly, not through the Go gateway. This bypasses the gateway's auth, rate limiting, and caching layers.

### Issues

| ID | Severity | Issue | Location |
|----|----------|-------|----------|
| COM-P1-11 | **P1** | Most community APIs (groups, friends, messages, checkins) bypass Go gateway and go directly to Python REST. This skips auth middleware, rate limiting, and caching at the gateway layer. Architecture should route all external API calls through Go. | Architecture |
| COM-P2-11 | P2 | Feed endpoint `GET /community/feed` has no auth middleware -- any unauthenticated user can read posts | `community.go:31` |

---

## Summary of Issues

### P0 (Must Fix Before Launch)

| ID | Issue | Impact |
|----|-------|--------|
| COM-P0-01 | No `/community` home route registered | Users landing on community tab get 404 |
| COM-P0-02 | Friend context menu (block/delete) never triggered from UI | Users cannot block or delete friends |
| COM-P0-03 | Comment button non-functional, no comment system | Core social interaction missing |
| COM-P0-04 | Feed has no DB fallback -- Redis cache miss = empty feed | Feed silently breaks on cache issues |
| COM-P0-05 | No push notifications for community events | Accountability loop broken when app is backgrounded |

### P1 (Should Fix Before Launch)

| ID | Issue | Impact |
|----|-------|--------|
| COM-P1-01 | CommitmentCard hardcoded 304px width | Layout issues on narrow/wide devices |
| COM-P1-02 | Green dot shows "checked in" not "online" | Misleading online presence indicator |
| COM-P1-03 | Group chat route depends on external routing module | Potential 404 if chat routes not wired |
| COM-P1-04 | No sprint completion celebration or auto-archive | Dead sprint groups persist |
| COM-P1-05 | No `isLikedByMe` state on posts | Users can't tell which posts they liked |
| COM-P1-06 | Topic is plain string, no validation or trending | Low-quality topic experience |
| COM-P1-07 | Image sends local path, no upload to storage | Images don't render for other users |
| COM-P1-08 | Achievement broadcasts never consumed by Flutter | No social celebration visible |
| COM-P1-09 | No real online/presence system | Misleading status indicators |
| COM-P1-10 | No report message UI in Flutter | Users can't flag inappropriate content |
| COM-P1-11 | Community APIs bypass Go gateway | Missing auth, rate limiting, caching |

### P2 (Post-Launch)

| ID | Issue |
|----|-------|
| COM-P2-01 | Verify community.dart barrel exports |
| COM-P2-02 | No explicit commitment creation flow |
| COM-P2-03 | Group creation screen not audited |
| COM-P2-04 | No UI for official groups |
| COM-P2-05 | FriendsHubView not audited |
| COM-P2-06 | Location picker is a stub |
| COM-P2-07 | No post deletion UI |
| COM-P2-08 | No group-level achievements |
| COM-P2-09 | Group chat WS integration not verified |
| COM-P2-10 | No content moderation on feed posts |
| COM-P2-11 | Feed endpoint lacks auth |

---

## Vision Alignment Assessment

### "Accountability Space" (问责空间) vs Social Feed

**Score: 8/10**

The implementation correctly prioritizes accountability over social features:
1. Default tab is Partners, not Feed
2. CommitmentCard with progress, witnesses, success criteria
3. Partner observation with granular opt-out
4. Streak tracking and check-in status
5. "Needs Attention" and "Encourage" sections
6. Privacy-preserving cohort intelligence
7. Accountability invitation flow with goal and cadence

Deductions:
- Feed tab still has standard social-media mechanics (likes, posts with images)
- Comment system (non-functional) would make it more social
- No "witness progress" interaction model -- just like/comment buttons

### Recommendations for Vision Alignment

1. Replace the "like" button with "witness" (见证) interaction on accountability posts
2. Add "progress share" as a first-class post type (not just text/image)
3. Make the feed filterable by "partner updates only" as the default scope
4. Add commitment checkpoint reminders (not just daily check-in)

---

## Backend Quality Assessment

### Python Community Service

**Score: 9/10** -- Exceptionally thorough. The `community_service.py` file is ~3200 lines covering:
- Friendship lifecycle (with auto-accept on mutual interest)
- Full group CRUD with RBAC (owner/admin/member)
- Group messaging with slow mode, keyword filter, thread support
- Check-in system with flame reward calculation
- Group tasks with personal task sync
- Private messaging with block enforcement
- User blocking with auto-friendship/partnership cleanup
- User search with privacy filtering
- Resource quality scoring with auto-hide
- Similar goal pursuers with embedding-based matching

### Go Gateway Community Handler

**Score: 4/10** -- Minimal. Only posts/feed/likes. Outbox pattern is correctly implemented but the handler coverage is thin compared to what Python provides.

### Flutter Community Module

**Score: 7/10** -- Good architecture with proper separation of concerns. The providers, repositories, and screens follow Riverpod patterns well. Missing: comment system, image upload, push notification integration, report UI.

---

## File Index

### Flutter (80 files)
- Routes: `mobile/lib/features/community/community_routes.dart`
- Main screen: `mobile/lib/features/community/presentation/screens/community_main_screen.dart`
- Partners tab: `mobile/lib/features/community/presentation/widgets/partners_tab.dart`
- Feed tab: `mobile/lib/features/community/presentation/widgets/feed_tab_content.dart`
- Groups tab: `mobile/lib/features/community/presentation/widgets/groups_tab.dart`
- Accountability hub: `mobile/lib/features/community/presentation/pages/accountability_hub_screen.dart`
- Accountability detail: `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
- Commitment card: `mobile/lib/features/community/presentation/widgets/accountability_hub/commitment_card.dart`
- Partner observation: `mobile/lib/features/community/presentation/widgets/accountability_hub/partner_observation_settings.dart`
- WS service: `mobile/lib/features/community/data/services/community_websocket_service.dart`
- Friends screen: `mobile/lib/features/community/presentation/screens/friends_screen.dart`
- Group detail: `mobile/lib/features/community/presentation/screens/group_detail_screen.dart`
- Group discover: `mobile/lib/features/community/presentation/screens/group_discover_screen.dart`
- Feed post card: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart`
- Create post: `mobile/lib/features/community/presentation/screens/create_post_screen.dart`

### Go Gateway (7 files)
- Handler: `backend/gateway/internal/api/v1/community.go`
- Command: `backend/gateway/internal/service/community_command.go`
- Query: `backend/gateway/internal/service/community_query.go`
- Sync worker: `backend/gateway/internal/worker/community_sync.go`

### Python (12 files)
- Community service: `backend/app/services/community_service.py`
- Advanced service: `backend/app/services/community_advanced_service.py`
- Signal bridge: `backend/app/services/community_signal_bridge.py`
- Signal collector: `backend/app/services/community_signal_collector.py`
- Strategy service: `backend/app/services/community_strategy_service.py`
- REST router: `backend/app/api/v1/community.py`
- Experience router: `backend/app/api/v1/experience/community_router.py`
- Models: `backend/app/models/community.py`
- Privacy: `backend/app/models/community_privacy.py`
- Schemas: `backend/app/schemas/community.py`
- Signals: `backend/app/signals/community_signal.py`
- Community loops: `backend/app/signals/community_loops.py`

### Proto
- `proto/community_service.proto` (deprecated, documentation-only)
