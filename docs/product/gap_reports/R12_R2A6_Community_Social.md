# R12 / R2A6 — Community_Social 二次深度审查
**Date**: 2026-05-15
**Scope**: Community + Social
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: Accountability features are solid, but feed is still trailing. The accountability-first vision holds up well with the default "Partners" tab.

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 1 |
| P1 (important gap, ship with plan) | 7 |
| P2 (nice to have, post-launch) | 0 |
| Verified working | 4 |

---

## R11 P0 验证
- **COM-P0-01 (No /community home route)**: **FIXED**. The route `'/community'` is properly registered in the `StatefulShellBranch` in `mobile/lib/app/routes.dart`.
- **COM-P0-02 (Friend context menu missing)**: **FIXED**. `_showFriendContextMenu` is now properly wired up to `onFriendLongPress` in `_MyFriendsTab`.
- **COM-P0-03 (Comment button non-functional)**: **MITIGATED (downgraded to P1)**. The comment button in `FeedPostCard` now has an `onTap` handler that shows a "Comments coming soon" snackbar, preventing it from appearing broken, though the core feature is still missing.
- **COM-P0-04 (Feed has no DB fallback)**: **FIXED**. `CommunityQueryService.GetGlobalFeed` in `backend/gateway/internal/service/community_query.go` now correctly implements a fallback `fetchPostsFromDB(ctx, missedIDs)` for cache misses, preventing silent feed failure.
- **COM-P0-05 (No push notifications)**: **STILL EXISTS**. Maintained as P0.

---

## P0 Findings (Must Fix Before Launch)

### P0-1: Missing Push Notifications for Community Events
**File**: `backend/app/services/community_service.py` / `backend/app/services/community_signal_bridge.py`
**Lines**: Global
**Problem**: There is still no integration with the notification service for critical community events (friend requests, accountability invitations, group messages, check-in reminders). 
**Evidence**: Searching for notification integration within community services yields no results.
**Expected**: `CommunitySignalBridge` or `CommunityService` should trigger push notifications via the Notification service so users are alerted when the app is backgrounded.
**Fix recommendation**: Wire up `notification_service.py` calls in the Python engine when these social events occur.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: Misleading Online Presence Indicator
**File**: `mobile/lib/features/community/presentation/widgets/partners_tab.dart`
**Lines**: 201
**Problem**: The UI passes `partnerCheckedIn` to the `isOnline` property of the `_PartnerAvatar`. Green dot represents "checked in today", not actual online WebSocket presence.
**Evidence**: `isOnline: partnerCheckedIn,`
**Expected**: Online status should be driven by a real-time presence system or renamed/recolored to mean "checked in".
**Fix recommendation**: Create a distinct visual indicator for "checked in" (e.g., a flame or checkmark icon) instead of using the universal green dot `isOnline` metaphor.

### P1-2: Local Image Paths in Post Creation
**File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart`
**Lines**: 60
**Problem**: When creating a post, the local file path (`_selectedImage!.path`) is sent directly to the `addPostOptimistically` provider. There is no intermediary upload to a storage service (like MinIO).
**Evidence**: `_selectedImage != null ? [_selectedImage!.path] : [],`
**Expected**: Images must be uploaded to a storage service and their remote URLs included in the post creation API call.
**Fix recommendation**: Integrate a storage service upload step before calling the post creation provider.

### P1-3: Missing isLikedByMe State on Posts
**File**: `backend/gateway/internal/service/community_query.go`
**Lines**: 11-20
**Problem**: The `PostView` struct returned by the Go Gateway only includes `LikeCount int`. It does not calculate or return an `IsLikedByMe bool` for the requesting user.
**Evidence**: `type PostView struct { ID string, UserID string, Content string, ImageURLs []string, Topic string, LikeCount int, CreatedAt time.Time, User UserView }`
**Expected**: Users need to see which posts they have liked so the UI can reflect the correct toggle state.
**Fix recommendation**: Update the Go Gateway's `GetGlobalFeed` DB fallback query to LEFT JOIN on a likes table and return `is_liked_by_me` in the `PostView`.

### P1-4: Post Topic is a Plain String
**File**: `backend/gateway/internal/service/community_query.go` / `create_post_screen.dart`
**Lines**: Global
**Problem**: Post topics are handled as plain strings without validation, reference to a topics table, or trending logic. 
**Evidence**: `_topicController.text.trim()` is passed directly.
**Expected**: Topics should be structured entities to support discovery and filtering.
**Fix recommendation**: Implement a minimal Topics entity or validation to standardize hashtags.

### P1-5: Missing Social Celebration UI (Achievements)
**File**: `mobile/lib/features/community/`
**Lines**: Global
**Problem**: While the Python backend broadcasts `community:achievements` via Redis, no Flutter widget or provider subscribes to this channel.
**Evidence**: `community:achievements` is completely absent from the Flutter codebase.
**Expected**: A social celebration feed or banner should display when partners unlock achievements.
**Fix recommendation**: Create a WebSocket or Server-Sent Events listener in Flutter for the `community:achievements` channel.

### P1-6: Content Reporting UI is Missing
**File**: `mobile/lib/features/community/presentation/`
**Lines**: Global
**Problem**: The data models and repository methods (`reportMessage`) for content moderation exist in Flutter, but there is no UI element to trigger a report.
**Evidence**: `reportMessage` is never called from any presentation widget.
**Expected**: Users must have a way to flag inappropriate content from posts or messages.
**Fix recommendation**: Add a "Report" option to the post and message context menus.

### P1-7: Community APIs Bypass Go Gateway
**File**: `backend/gateway/internal/api/v1/community.go`
**Lines**: Global
**Problem**: The Go Gateway only handles `/community/posts` and `/community/feed`. All other community APIs (groups, friends, messages, accountability) bypass the gateway and go directly to Python, skipping auth, caching, and rate limiting layers.
**Expected**: All external API traffic must route through the Go Gateway as per the architecture rules.
**Fix recommendation**: Implement reverse proxy routes or direct handlers in the Go Gateway for all missing community endpoints.

---

## P2 Findings (Post-Launch)
- Addressed in previous audits, focusing on P0/P1 for launch parity.

---

## Verified Working (Strengths)

### V-1: Accountability-First Vision
- **Verification**: The default tab on `/community` is "Partners", focusing on accountability, check-ins, and shared goals. The `CommitmentCard` widget is well-designed.
- **Verdict**: PASS

### V-2: Redis-to-DB Feed Fallback
- **Verification**: The `CommunityQueryService` now explicitly queries PostgreSQL if a post is missing from the Redis cache and re-caches it.
- **Verdict**: PASS

### V-3: Group Chat Routing
- **Verification**: Legacy chat routes are correctly mapped in `mobile/lib/features/chat/chat_routes.dart` (e.g., `/community/groups/:id/chat -> /chat/group/:id`).
- **Verdict**: PASS

### V-4: Privacy and Block Systems
- **Verification**: Full block system exists in both Flutter (BlockedUsersScreen) and Python backend (ModerationService), ensuring blocked users cannot interact.
- **Verdict**: PASS

---

## Cross-Route Integration Issues
- **Chat vs Community**: The separation of Chat and Community features requires careful routing. The current legacy route redirection works but feels brittle.

---

## Code Quality Observations
- **Strong backend logic**: The Python backend's `community_service.py` is exceptionally thorough (3000+ lines covering complex RBAC, differential privacy, matching algorithms).
- **Incomplete frontend implementation**: The Flutter UI and Go Gateway are lagging behind the Python backend's capabilities, leaving many "ghost features" (code exists but cannot be used by a user).