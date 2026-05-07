# R13-R2A6: Community + Social Independent Audit Report

**Date**: 2026-05-07
**Auditor**: Independent R13 Audit
**Scope**: Community + Social system across Flutter, Go Gateway, Python Engine

---

## Summary Table

| Area | Status | P0 | P1 | P2 | Notes |
|------|--------|----|----|-----|-------|
| Route Registration | PASS | 0 | 0 | 1 | 20+ routes, all registered |
| Feed System | PARTIAL | 1 | 1 | 1 | Missing pagination, isLiked not tracked |
| Comment System | FAIL | 1 | 1 | 0 | Wrong API path, no ownership check in UI |
| Friends System | PASS | 0 | 1 | 0 | Full flow, but friend request push incomplete |
| Groups System | PASS | 0 | 0 | 1 | Comprehensive; group invite push missing |
| Push Notifications | PARTIAL | 1 | 1 | 0 | Like/comment push works; friend request + group push incomplete |
| Accountability Space | PASS | 0 | 0 | 1 | CommitmentCard renders, progress sharing via share cards |
| Edge Cases | PARTIAL | 0 | 2 | 1 | Empty feed OK; no post delete in Flutter; block works |

**Totals**: 3 P0 | 6 P1 | 5 P2

---

## P0 Findings (Blockers)

### P0-01: Comment Bottom Sheet Uses Wrong API Path -- Comments Cannot Load/Create/Delete

**File**: `mobile/lib/features/community/presentation/widgets/comment_bottom_sheet.dart:66,84,102`

The comment bottom sheet makes direct `api.dio` calls to `/posts/{postId}/comments`. Since the API client base URL is `/api/v1/`, these resolve to `/api/v1/posts/{postId}/comments`. However, the Go gateway proxy routes and Python backend both expect the path to be `/api/v1/community/posts/{postId}/comments`.

```dart
// Line 66 - WRONG: missing /community/ prefix
final resp = await api.dio.get('/posts/${widget.postId}/comments');

// Line 84 - WRONG: missing /community/ prefix
await api.dio.post('/posts/${widget.postId}/comments', data: {'content': content});

// Line 102 - WRONG: missing /community/ prefix
await api.dio.delete('/posts/${widget.postId}/comments/$commentId');
```

**Impact**: Comment viewing, creation, and deletion all 404 at the gateway. The entire comment system is non-functional in production.

**Fix**: Change all three paths to `/community/posts/${widget.postId}/comments`.

---

### P0-02: Friend Request Notification Uses NotificationService.create (DB-only) Instead of NotificationPushService.create_and_push (DB + WebSocket + FCM/JPush)

**File**: `backend/app/api/v1/community.py:1153`

When a friend request is sent, the notification is created via `NotificationService.create()`, which only writes to the database. Compare with post likes (line 451-454) and comments (line 526-530), which use `NotificationPushService.create_and_push()` that creates the DB record, pushes via WebSocket, and sends via FCM/JPush device channels.

```python
# Line 1153 - DB-only, no real-time push
await NotificationService.create(
    db,
    data.target_user_id,
    NotificationCreate(
        title="新的好友请求",
        content=f"{sender_name} 向你发来了好友请求",
        type="friend_request",
        data={...},
    ),
)
```

**Impact**: Friend request recipients do not receive real-time push notifications. They must manually check the notification center or friends screen. This is a critical UX gap for a social feature.

**Fix**: Replace with `NotificationPushService(db).create_and_push(...)`.

---

### P0-03: Post Model Missing `isLiked` Field -- Like Toggle Cannot Show Visual State

**Files**:
- `mobile/lib/features/community/data/models/community_models.dart:19-33` (Post model)
- `backend/app/api/v1/community.py:224-240` (_post_to_response)
- `mobile/lib/features/community/presentation/providers/community_providers.dart:34-57` (toggleLike)

The `Post` freezed model has no `isLiked` boolean field. The `_post_to_response` server function does not return `is_liked`. The `toggleLike` method in FeedNotifier only bumps `likeCount` optimistically with no toggle tracking.

```dart
// community_models.dart:19-33 -- no isLiked field
@freezed
class Post with _$Post {
  const factory Post({
    required String id,
    ...
    @JsonKey(name: 'like_count') @Default(0) int likeCount,
    @Default(false) bool isOptimistic,
    // MISSING: @Default(false) bool isLiked,
  }) = _Post;
}
```

```python
# community.py:224-240 -- no is_liked in response
def _post_to_response(post: Post) -> dict:
    return {
        "id": str(post.id),
        ...
        "like_count": post.like_count or 0,
        # MISSING: "is_liked": ...,
    }
```

**Impact**: Every time the feed loads, all posts appear with the same "unliked" heart icon. Users cannot see which posts they have already liked. Tapping "like" always increments the count; tapping again increments again (does not truly toggle). The backend correctly toggles, but the UI cannot reflect the state.

**Fix**: (1) Add `is_liked` query in feed endpoint using current_user PostLike existence check. (2) Return `is_liked` in `_post_to_response`. (3) Add `isLiked` field to Flutter Post model. (4) Update `toggleLike` to flip `isLiked` and adjust count directionally. (5) Update FeedPostCard to show filled/outline heart based on `isLiked`.

---

## P1 Findings (Should Fix Before Launch)

### P1-01: Feed Has No Pagination / Infinite Scroll -- Only First 20 Posts Load

**Files**:
- `mobile/lib/features/community/presentation/providers/community_providers.dart:19-32` (refresh loads page 1 only)
- `mobile/lib/features/community/presentation/widgets/feed_tab_content.dart:40-64` (ListView with no load-more)

The `FeedNotifier.refresh()` always fetches page 1. There is no `loadMore()` method. The `FeedTabContent` renders a `ListView.builder` with `posts.length + 1` items but no scroll-detection to trigger loading the next page.

```dart
// community_providers.dart:27 - always page 1
final posts = await _repository.getFeed(scope: _scope);
```

**Impact**: Users with more than 20 posts in their feed cannot scroll to see older posts. No "load more" indicator.

**Fix**: Add `loadMore()` to FeedNotifier that fetches `page + 1` and appends. Add scroll detection in FeedTabContent to trigger it.

---

### P1-02: Comment Delete Button Shown for All Comments -- No Ownership Check in UI

**File**: `mobile/lib/features/community/presentation/widgets/comment_bottom_sheet.dart:184-189`

Every comment in the list renders a delete icon button, regardless of whether the current user authored the comment. The backend correctly checks `if str(comment.user_id) != str(current_user.id): raise 403`, so the delete would fail server-side, but the UI shows the delete button to everyone.

```dart
// Line 184-189 -- no ownership check
trailing: IconButton(
  icon: const Icon(Icons.delete_outline, size: 18),
  onPressed: () => _deleteComment(c['id'] as String),
),
```

**Impact**: Users see a delete button on other users' comments. Tapping it shows a "Failed to delete" error. Confusing UX.

**Fix**: Only show the delete button when `c['user_id'] == currentUserId`. The sheet needs access to the current user ID (e.g., from a provider or auth state).

---

### P1-03: Post Creation Has No Rate Limiting on Backend

**File**: `backend/app/api/v1/community.py:393-413`

The `create_post` endpoint at line 393 has no `@limiter.limit()` decorator. Friend request has `5/minute` (line 1124). User search has `20/minute` (line 1390). But post creation is unlimited.

```python
# Line 393 - no rate limit
@router.post("/posts", summary="发布社区动态", status_code=201)
async def create_post(request: Request, ...):
```

**Impact**: A malicious or buggy client could flood the feed with thousands of posts per minute.

**Fix**: Add `@limiter.limit("10/minute")` or similar to the create_post endpoint.

---

### P1-04: Group Join Notification Uses NotificationService.create (DB-only) -- No Real-Time Push

**File**: `backend/app/services/community_service.py:850`

When a member joins a group, admins are notified via `NotificationService.create()` (DB-only), not `NotificationPushService.create_and_push()`.

```python
# Line 850 - DB-only
await NotificationService.create(
    db,
    admin_id,
    NotificationCreate(title="新成员加入群组", ...),
)
```

**Impact**: Group admins do not receive real-time push when new members join. Must manually check notification center.

**Fix**: Replace with `NotificationPushService(db).create_and_push(...)`.

---

### P1-05: FeedPostCard Comment Fallback Shows "Comments Coming Soon" Instead of Opening Sheet

**File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:176-183`

When `onComment` is null, the fallback shows an `AppFeedback.info` message "Comments coming soon". However, the FeedTabContent always passes `onComment`, so this fallback is dead code. If it were reached, it would mislead the user since comments do exist.

```dart
onTap: onComment ??
    () {
      AppFeedback.info(context, zh ? '评论功能即将上线' : 'Comments coming soon');
    },
```

**Impact**: Low risk (dead code path), but misleading if ever triggered. Should be removed or changed.

**Fix**: Remove the fallback; always require `onComment`. If it can be null, show nothing or disable the button.

---

### P1-06: No Post Delete Functionality in Flutter Client

**Files**:
- `backend/gateway/internal/handler/proxy_routes.go:525` -- DELETE `/posts/:post_id` is registered
- `backend/app/api/v1/community.py` -- no DELETE handler for posts
- Flutter -- no delete button or menu on FeedPostCard

The Go gateway registers `community.DELETE("/posts/:post_id", h.proxyWithHeaders)` at line 525, and `community.PATCH("/posts/:post_id", h.proxyWithHeaders)` at line 526. However, the Python backend has no `@router.delete("/posts/{post_id}")` handler. There is also no delete option in the Flutter FeedPostCard.

**Impact**: Users cannot delete their own posts. Posts persist forever unless manually removed from DB.

**Fix**: (1) Add `delete_post` and `update_post` handlers in `backend/app/api/v1/community.py`. (2) Add a "more" menu on FeedPostCard with delete option for own posts.

---

## P2 Findings (Nice to Fix)

### P2-01: FeedPostCard Has No Share Button

**File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart`

The feed post card has Like and Comment action buttons but no Share button. The backend has a `/community/share` endpoint and a `ShareResourceSheet` widget exists. There is no way to share a feed post.

**Fix**: Add a share action to the FeedPostCard action row.

---

### P2-02: /community Route Is a Branch Path but /community/feed Is a Flat Route -- Navigation Inconsistency

**Files**:
- `mobile/lib/app/routes.dart:286` -- `/community` is the shell branch path
- `mobile/lib/features/community/community_routes.dart:54` -- `/community/feed` is a flat GoRoute

The main shell has `/community` as a StatefulShellBranch with `CommunityMainScreen`. But `CommunityRoutes.routes` also registers `/community/feed` as a standalone flat route using the root navigator. If a user navigates to `/community/feed`, they leave the shell and lose bottom navigation.

**Impact**: Users navigating to `/community/feed` (e.g., from accountability hub at line 478 of accountability_hub_screen.dart) will lose bottom navigation bar.

**Fix**: Either remove the `/community/feed` flat route (the shell branch already shows the feed tab) or ensure all navigations to community use the shell branch `/community`.

---

### P2-03: Post Image Only Shows First Image

**File**: `mobile/lib/features/community/presentation/widgets/feed_post_card.dart:146-155`

When `post.imageUrls` has multiple images, only the first is shown:

```dart
if (post.imageUrls != null && post.imageUrls!.isNotEmpty)
  SparkleNetworkImage(
    imageUrl: post.imageUrls!.first, // only first image
```

**Fix**: Render a horizontal scrollable image carousel when multiple images exist.

---

### P2-04: CreatePostScreen Image Upload Passes Local File Path as URL

**File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart:58-61`

The image picker returns a local `XFile.path`, but `addPostOptimistically` passes it as `imageUrls`. The backend expects URLs, not local file paths.

```dart
await ref.read(feedProvider.notifier).addPostOptimistically(
  content,
  _selectedImage != null ? [_selectedImage!.path] : [], // local path, not URL
  _topicController.text.trim(),
);
```

**Impact**: Optimistic post shows the image locally, but after refresh, the image is broken because the backend received a file path, not a URL.

**Fix**: Upload the image to the file server first, then pass the resulting URL.

---

### P2-05: CreatePostScreen Location Picker Is Hardcoded Mock

**File**: `mobile/lib/features/community/presentation/screens/create_post_screen.dart:38-48`

The location picker is explicitly mocked:

```dart
setState(() {
  _selectedLocation = I18nService.instance.isChinese ? '模拟位置' : 'Mock Location';
});
AppFeedback.info(context, 'Location picker is under development...');
```

**Impact**: Location feature is non-functional. Minor since it is optional.

---

## Verified Working

### Route Registration
- `/community` registered as StatefulShellBranch (routes.dart:282-297) -- bottom tab navigation
- 20+ community sub-routes registered in CommunityRoutes (community_routes.dart:52-383)
- All routes registered in GoRouter via `...CommunityRoutes.routes` (routes.dart:338)
- Go gateway proxy routes comprehensive (proxy_routes.go:438-563): friends, groups, feed, posts, comments, messages, files, tasks, encryption, moderation, reports, favorites, broadcast, offline queue
- Deep links supported via GoRoute path parameters (groupDetail, userProfile, accountabilityDetail)
- Community events stream wired to shell navigation (shell_navigation.dart:109-138)

### Feed System
- Feed loads from Python backend via Go proxy (community.py:269-389)
- Feed supports scope filtering: global, squad, goal_mates, following (community.py:318-363)
- Pull-to-refresh working (FeedTabContent uses SparkleRefreshIndicator)
- Empty state with placeholder and "Share a post" CTA (feed_tab_content.dart:156-192)
- Error state with retry button (feed_tab_content.dart:68-86)
- Optimistic post creation with loading indicator (community_providers.dart:60-110)
- Blocked users filtered from feed (community.py:364-375)
- Soft-delete guard on posts (community.py:286)

### Comment System (Backend)
- List comments: GET `/community/posts/{post_id}/comments` (community.py:469-491)
- Create comment: POST `/community/posts/{post_id}/comments` with comment_count increment (community.py:494-548)
- Delete comment: DELETE with ownership check `str(comment.user_id) != str(current_user.id)` (community.py:551-580)
- Comment creation triggers push notification to post author (community.py:524-540)

### Post Interactions
- Like toggle with real toggle logic (existing = unlike, else = like) (community.py:417-464)
- Like triggers push notification to post author via NotificationPushService (community.py:448-462)
- Like count incremented/decremented atomically (community.py:439-443)

### Friends System
- Full friend lifecycle: send request, accept, reject, delete (community_repository.dart)
- Friend context menu: long-press shows delete friend + block user options (friends_screen.dart:121-209)
- Blocked users screen accessible from context menu (CommunityRoutes.blockedUsers)
- Friend recommendations with strategy selection (compatibility/complementary) (friends_screen.dart:571-716)
- Accountability invite flow from recommendations (friends_screen.dart:886-969)
- Pending requests include both friend requests and accountability partnership invites (friends_screen.dart:356-569)
- Friend request rate limited: 5/minute (community.py:1124)

### Groups System
- Group creation, detail, members, files, tasks, moderation screens all exist
- Group search, discover, and directory with sorting
- Group join/leave with role management (kick, promote, demote, transfer ownership)
- Group messages with threads, reactions, search, read tracking
- Group recommendations with feedback (community_repository.dart:314-414)
- Group flame status and check-in system
- Group file sharing with permissions
- Shared resources with adoption

### Push Notifications
- NotificationPushService supports WebSocket + FCM + JPush (notification_push_service.py:28-177)
- Post like notification: working (community.py:448-462)
- Post comment notification: working (community.py:524-540)
- Group message reply notification: working (community_service.py:1648-1679)
- Group message like notification: working (community_service.py:1844-1873)

### Accountability Space
- CommitmentCard renders with progress bar, status pill, witnesses, due date, success criteria, milestones, evidence (commitment_card.dart)
- Partner reminder toggle wired (commitment_card.dart:111-122)
- Accountability hub screen with heat map and partner observation
- Progress sharing via share cards: plan, task, achievement, capsule, learning report, knowledge node
- Accountability partnership CRUD with invite flow

### Edge Cases
- Empty feed: placeholder with action (feed_tab_content.dart:156-192)
- Blocked user content: filtered from feed via SQL query (community.py:364-375)
- Friend request rate limiting: 5/minute (community.py:1124)
- User search rate limiting: 20/minute (community.py:1390)
- Block user rate limiting: 10/hour (community.py:1429)
- Error/retry states on feed, friends, pending requests

---

## File Index

| File | Role |
|------|------|
| `mobile/lib/features/community/community_routes.dart` | GoRouter route definitions |
| `mobile/lib/app/routes.dart` | Main router with shell branch |
| `mobile/lib/core/navigation/shell_navigation.dart` | Bottom nav shell with community events |
| `mobile/lib/features/community/presentation/screens/community_main_screen.dart` | 3-tab community screen |
| `mobile/lib/features/community/presentation/widgets/feed_tab_content.dart` | Feed tab with filters |
| `mobile/lib/features/community/presentation/widgets/feed_post_card.dart` | Post card widget |
| `mobile/lib/features/community/presentation/widgets/comment_bottom_sheet.dart` | Comment bottom sheet |
| `mobile/lib/features/community/presentation/providers/community_providers.dart` | Feed state management |
| `mobile/lib/features/community/data/repositories/community_repository.dart` | API client methods |
| `mobile/lib/features/community/data/models/community_models.dart` | Post model |
| `mobile/lib/features/community/presentation/screens/friends_screen.dart` | Friends + requests + recommendations |
| `mobile/lib/features/community/presentation/screens/create_post_screen.dart` | Post creation |
| `mobile/lib/features/community/presentation/widgets/accountability_hub/commitment_card.dart` | Commitment card |
| `backend/gateway/internal/handler/proxy_routes.go` | Go proxy routes (438-563) |
| `backend/app/api/v1/community.py` | Python community REST handlers |
| `backend/app/services/community_service.py` | Python community business logic |
| `backend/app/services/notification_push_service.py` | Push notification service |
| `backend/app/models/community.py` | Post, PostLike, PostComment, UserBlock models |
