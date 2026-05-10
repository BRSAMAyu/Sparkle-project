# Cross-Layer API Contract Audit: Community & Accountability

**Date**: 2026-05-10
**Scope**: Flutter frontend API calls vs Python backend route definitions
**Files Audited**:
- `mobile/lib/core/network/api_endpoints.dart` (endpoint definitions)
- `mobile/lib/features/community/data/repositories/community_repository.dart`
- `mobile/lib/features/community/data/repositories/accountability_repository.dart`
- `mobile/lib/features/community/data/repositories/community_share_repository.dart`
- `mobile/lib/features/community/data/repositories/community_accountability_repository.dart`
- `backend/app/api/v1/community.py` (prefix: `/community`)
- `backend/app/api/v1/accountability.py` (prefix: `/accountability`)
- `backend/app/api/v1/experience/community_router.py` (prefix: `/experience`)

**Router Registration**:
- community.py -> `/api/v1/community/*`
- accountability.py -> `/api/v1/accountability/*`
- experience/community_router.py -> `/api/v1/experience/*`

---

## Issues Found

### [SEVERITY: P0] Frontend-Backend Mismatch: community/resources response shape incompatible

**Frontend**: `community_share_repository.dart:44` -- GET `/community/resources` (via `ApiEndpoints.communityResources`)
**Backend**: `community.py:4760` -- `@router.get("/resources")` returns `{"resources": [...], "total": N, "offset": N, "limit": N}`
**Issue**: Frontend checks `if (data is! List) return [];` on the response body. The backend returns a **map** with a `resources` key wrapping the list, not a bare list. The frontend will always get an empty list because `data` is a Map, not a List. The `ApiResponseParser.unwrapMap` is NOT called here -- the code directly tests `data is List`.
**Impact**: `fetchSharedResources()` in `CommunityShareRepository` always returns an empty list for real (non-demo) users. The "quality-ranked resources" feature is completely broken in production.

---

### [SEVERITY: P0] Frontend-Backend Mismatch: completeTask endpoint missing

**Frontend**: `community_repository.dart:1030-1031` -- POST `/community/tasks/$taskId/complete`
**Backend**: MISSING -- no route matching `/tasks/{task_id}/complete` exists in community.py. Only `/tasks/{task_id}/claim` (line 3190) exists.
**Issue**: The frontend hardcodes the URL path directly as a string literal (`'/community/tasks/$taskId/complete'`) rather than using `ApiEndpoints`, and the backend has no corresponding route.
**Impact**: Completing a community task will always fail with a 404 error. The "complete task" feature is non-functional.

---

### [SEVERITY: P1] Frontend-Backend Mismatch: unmuteMember HTTP method and URL path differ

**Frontend**: `community_repository.dart:985-988` -- POST `/community/groups/$groupId/members/$userId/unmute`
**Backend**: `community.py:4272` -- DELETE `/community/groups/$groupId/members/$userId/mute`
**Issue**: Two mismatches: (1) Frontend uses POST, backend expects DELETE. (2) Frontend URL ends with `/unmute`, backend URL ends with `/mute`. The unmute action will always fail.
**Impact**: Unmuting a group member is completely non-functional. Moderators cannot lift mutes from the app.

---

### [SEVERITY: P1] Frontend-Backend Mismatch: rejectResource has no backend endpoint

**Frontend**: `community_share_repository.dart:116-130` -- intended POST to `/community/shared-resources/{id}/reject`
**Backend**: MISSING -- no `/shared-resources/{resource_id}/reject` route exists.
**Issue**: The frontend code has a comment acknowledging this: "Server-side endpoint may not exist yet". It falls back to recording the rejection through the event stream only. While this is intentionally a graceful degradation, the rejection never reaches the backend's recommendation engine, so rejected resources may reappear in suggestions.
**Impact**: Resource rejection is not persisted server-side and does not influence future recommendations. Users will keep seeing resources they previously rejected.

---

### [SEVERITY: P2] Frontend-Backend Mismatch: copyFileToMyLibrary uses hardcoded path

**Frontend**: `community_repository.dart:1437-1441` -- POST `/api/v1/community/groups/$groupId/files/$fileId/copy-to-library` (hardcoded full path)
**Backend**: `community.py:2426-2427` -- POST `/groups/{group_id}/files/{file_id}/copy-to-library` (prefix: `/community`)
**Issue**: The frontend hardcodes the full URL path including `/api/v1/community/` rather than using `ApiEndpoints`. While the full resolved path does match the backend's actual route (`/api/v1/community/groups/{groupId}/files/{fileId}/copy-to-library`), this bypasses the ApiEndpoints centralized definition and the `ApiConstants.apiBasePath` prefix. If the API base path changes, this call will break silently. There is also a TODO comment in the code acknowledging this.
**Impact**: Currently functional but fragile. Any change to the API base path or versioning will break this endpoint silently since it is not centralized.

---

### [SEVERITY: P2] Frontend-Backend Mismatch: community/resources sort param mismatch potential

**Frontend**: `community_share_repository.dart:26` -- sends `sort` param with default `'quality'`
**Backend**: `community.py:4762` -- accepts `sort` param with default `'quality'`, valid values: `quality | recent`
**Issue**: The sort parameter values align, but the frontend also sends a `limit` query parameter directly. The backend accepts `limit` and `offset`. No direct mismatch exists, but the `resource_type` filter on the frontend sends a raw string, while the backend expects a `SharedResourceTypeEnum` value. If the frontend sends a string that doesn't match an enum value, FastAPI will return a 422 validation error.
**Impact**: Low risk if frontend always sends valid enum values. However, any typo or unsupported resource type will cause a hard failure.

---

## Verified Contracts (Matching)

The following frontend-backend pairs were verified as correctly matching in method, path, and general request/response shape:

### Community - Feed & Posts
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `getFeed()` | GET | `/community/feed` | `community.py:276` | MATCH |
| `createPost()` | POST | `/community/posts` | `community.py:412` (201) | MATCH |
| `likePost()` | POST | `/community/posts/{id}/like` | `community.py:437` | MATCH |
| `deletePost()` | DELETE | `/community/posts/{id}` | `community.py:572` | MATCH |

### Community - Friends
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `getFriends()` | GET | `/community/friends` | `community.py:1269` | MATCH |
| `getPendingRequests()` | GET | `/community/friends/pending` | `community.py:1330` | MATCH |
| `sendFriendRequest()` | POST | `/community/friends/request` | `community.py:1169` | MATCH |
| `respondToRequest()` | POST | `/community/friends/respond` | `community.py:1219` | MATCH |
| `getFriendRecommendations()` | GET | `/community/friends/recommendations` | `community.py:1588` | MATCH |
| `sendFriendRecommendationFeedback()` | POST | `/community/friends/recommendations/feedback` | `community.py:1611` | MATCH |
| `getFriendProfile()` | GET | `/community/friends/{id}/profile` | `community.py:1342` | MATCH |
| `searchUsers()` | GET | `/community/users/search` | `community.py:1449` | MATCH |
| `deleteFriend()` | DELETE | `/community/friends/{id}` | `community.py:1250` | MATCH |
| `blockUser()` | POST | `/community/users/block` | `community.py:1488` | MATCH |
| `unblockUser()` | DELETE | `/community/users/block/{id}` | `community.py:1511` | MATCH |
| `getBlockedUsers()` | GET | `/community/users/blocked` | `community.py:1524` | MATCH |
| `getPrivacySettings()` | GET | `/community/users/privacy` | `community.py:1577` | MATCH |
| `updatePrivacySettings()` | PUT | `/community/users/privacy` | `community.py:1556` | MATCH |

### Community - Recommendation Feedback
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `getRecommendationFeedbackPrompts()` | GET | `/community/recommendations/feedback/prompts` | `community.py:1623` | MATCH |
| `getRecommendationFeedbackInsights()` | GET | `/community/recommendations/feedback/insights` | `community.py:1645` | MATCH |

### Community - Groups
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `getMyGroups()` | GET | `/community/groups` | `community.py:2154` | MATCH |
| `getGroup()` | GET | `/community/groups/{id}` | `community.py:1938` | MATCH |
| `createGroup()` | POST | `/community/groups` | `community.py:1755` | MATCH |
| `joinGroup()` | POST | `/community/groups/{id}/join` | `community.py:1948` | MATCH |
| `leaveGroup()` | POST | `/community/groups/{id}/leave` | `community.py:1974` | MATCH |
| `getGroupMembers()` | GET | `/community/groups/{id}/members` | `community.py:2044` | MATCH |
| `kickMember()` | POST | `/community/groups/{gid}/members/{uid}/kick` | `community.py:2059` | MATCH |
| `promoteMember()` | POST | `/community/groups/{gid}/members/{uid}/promote` | `community.py:2086` | MATCH |
| `demoteMember()` | POST | `/community/groups/{gid}/members/{uid}/demote` | `community.py:2114` | MATCH |
| `transferOwnership()` | POST | `/community/groups/{gid}/members/{uid}/transfer-ownership` | `community.py:2142` | MATCH |
| `searchGroups()` | GET | `/community/groups/search` | `community.py:1772` | MATCH |
| `getGroupDirectory()` | GET | `/community/groups/directory` | `community.py:1827` | MATCH |
| `getGroupRecommendations()` | GET | `/community/groups/recommendations` | `community.py:1906` | MATCH |
| `sendGroupRecommendationFeedback()` | POST | `/community/groups/recommendations/feedback` | `community.py:1925` | MATCH |
| `updateAnnouncement()` | PUT | `/community/groups/{id}/announcement` | `community.py:4177` | MATCH |
| `getModerationSettings()` | GET | `/community/groups/{id}/moderation` | N/A (PUT only) | SEE NOTE |
| `updateModerationSettings()` | PUT | `/community/groups/{id}/moderation` | `community.py:4206` | MATCH |

**Note on `getModerationSettings`**: Frontend calls GET `/community/groups/{id}/moderation`. Backend only has a PUT route at `community.py:4206`. No GET route exists for moderation settings. The frontend call will get a 405 Method Not Allowed.

### Community - Group Messages
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `sendMessage()` | POST | `/community/groups/{id}/messages` | `community.py:2164` | MATCH |
| `getMessages()` | GET | `/community/groups/{id}/messages` | `community.py:2215` | MATCH |
| `revokeGroupMessage()` | POST | `/community/groups/{gid}/messages/{mid}/revoke` | `community.py:2699` | MATCH |
| `editGroupMessage()` | PATCH | `/community/groups/{gid}/messages/{mid}` | `community.py:2676` | MATCH |
| `updateGroupReaction()` | POST | `/community/groups/{gid}/messages/{mid}/reactions` | `community.py:2720` | MATCH |
| `getThreadMessages()` | GET | `/community/groups/{gid}/threads/{tid}` | `community.py:2745` | MATCH |
| `searchGroupMessages()` | GET | `/community/groups/{id}/messages/search` | `community.py:2762` | MATCH |
| `markGroupMessagesRead()` | POST | `/community/groups/{id}/messages/read` | `community.py:2236` | MATCH |

### Community - Private Messages
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `getPrivateMessages()` | GET | `/community/friends/{id}/messages` | `community.py:2831` | MATCH |
| `sendPrivateMessage()` | POST | `/community/messages` | `community.py:2782` | MATCH |
| `revokePrivateMessage()` | POST | `/community/messages/{id}/revoke` | `community.py:2878` | MATCH |
| `editPrivateMessage()` | PATCH | `/community/messages/{id}` | `community.py:2853` | MATCH |
| `updatePrivateReaction()` | POST | `/community/messages/{id}/reactions` | `community.py:2903` | MATCH |
| `searchPrivateMessages()` | GET | `/community/friends/{id}/messages/search` | `community.py:2931` | MATCH |

### Community - Tasks & Checkin
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `checkin()` | POST | `/community/checkin` | `community.py:3042` | MATCH |
| `getGroupTasks()` | GET | `/community/groups/{id}/tasks` | `community.py:3144` | MATCH |
| `createGroupTask()` | POST | `/community/groups/{id}/tasks` | `community.py:3087` | MATCH |
| `claimTask()` | POST | `/community/tasks/{id}/claim` | `community.py:3190` | MATCH |
| `getFlameStatus()` | GET | `/community/groups/{id}/flame` | `community.py:3207` | MATCH |
| `updateStatus()` | PUT | `/community/status` | `community.py:2966` | MATCH |

### Community - Shared Resources
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `shareResource()` (CommunityRepository) | POST | `/community/share` | `community.py:3277` | MATCH |
| `adoptSharedResource()` (CommunityRepository) | POST | `/community/shared-resources/{id}/adopt` | `community.py:3713` | MATCH |
| `getGroupResources()` | GET | `/community/groups/{id}/resources` | `community.py:3469` | MATCH |
| `shareResource()` (ShareRepository) | POST | `/community/share` | `community.py:3277` | MATCH |
| `adoptResource()` (ShareRepository) | POST | `/community/shared-resources/{id}/adopt` | `community.py:3713` | MATCH |

### Community - Files
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `getGroupFiles()` | GET | `/community/groups/{id}/files` | `community.py:2395` | MATCH |
| `shareFileToGroup()` | POST | `/community/groups/{gid}/files/{fid}/share` | `community.py:2338` | MATCH |
| `updateGroupFilePermissions()` | PUT | `/community/groups/{gid}/files/{fid}/permissions` | `community.py:2621` | MATCH |
| `getGroupFileCategories()` | GET | `/community/groups/{id}/files/categories` | `community.py:2661` | MATCH |

### Community - Moderation
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `muteMember()` | POST | `/community/groups/{gid}/members/{uid}/mute` | `community.py:4240` | MATCH |
| `warnMember()` | POST | `/community/groups/{gid}/members/{uid}/warn` | `community.py:4290` | MATCH |
| `getPendingReports()` | GET | `/community/groups/{id}/reports` | `community.py:4349` | MATCH |
| `reviewReport()` | PUT | `/community/reports/{id}` | `community.py:4388` | MATCH |

### Community - Other
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `addFavorite()` | POST | `/community/favorites` | `community.py:4420` | MATCH |
| `getFavorites()` | GET | `/community/favorites` | `community.py:4459` | MATCH |
| `removeFavorite()` | DELETE | `/community/favorites/{id}` | `community.py:4502` | MATCH |
| `forwardMessage()` | POST | `/community/messages/forward` | `community.py:4518` | MATCH |
| `reportMessage()` | POST | `/community/reports` | `community.py:4319` | MATCH |
| `createBroadcast()` | POST | `/community/broadcast` | `community.py:4545` | MATCH |
| `getPendingOfflineMessages()` | GET | `/community/offline/pending` | `community.py:4646` | MATCH |
| `getFailedOfflineMessages()` | GET | `/community/offline/failed` | `community.py:4671` | MATCH |
| `retryOfflineMessages()` | POST | `/community/offline/retry` | `community.py:4696` | MATCH |
| `registerEncryptionKey()` | POST | `/community/encryption/keys` | `community.py:4113` | MATCH |
| `getUserPublicKeys()` | GET | `/community/encryption/keys/user/{id}` | `community.py:4139` | MATCH |
| `revokeEncryptionKey()` | DELETE | `/community/encryption/keys/{id}` | `community.py:4161` | MATCH |
| `similarGoalPursuers()` | GET | `/community/goals/{id}/similar-pursuers` | `community.py:4872` | MATCH |

### Accountability
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `requestPartnership()` | POST | `/accountability/request` | `accountability.py:874` (201) | MATCH |
| `respondToPartnership()` | POST | `/accountability/{id}/respond` | `accountability.py:982` | MATCH |
| `getMyPartnerships()` | GET | `/accountability/mine` | `accountability.py:1038` | MATCH |
| `getOverview()` | GET | `/accountability/overview` | `accountability.py:1074` | MATCH |
| `getDashboard()` | GET | `/accountability/{id}/dashboard` | `accountability.py:1118` | MATCH |
| `dailyCheckin()` | POST | `/accountability/{id}/checkin` | `accountability.py:1377` (201) | MATCH |
| `getStats()` | GET | `/accountability/{id}/stats` | `accountability.py:1519` | MATCH |
| `getTimeline()` | GET | `/accountability/{id}/timeline` | `accountability.py:1534` | MATCH |
| `getHeatmap()` | GET | `/accountability/{id}/heatmap` | `accountability.py:1550` | MATCH |
| `likeCheckin()` | POST | `/accountability/checkin/{id}/like` | `accountability.py:1569` | MATCH |
| `encourageCheckin()` | POST | `/accountability/checkin/{id}/encourage` | `accountability.py:1608` | MATCH |
| `endPartnership()` | DELETE | `/accountability/{id}` | `accountability.py:1337` (204) | MATCH |
| `nudgePartner()` | POST | `/accountability/{id}/nudge` | `accountability.py:1154` | MATCH |
| `dismissInAppHint()` | POST | `/accountability/hints/{id}/dismiss` | `accountability.py:1312` | MATCH |
| `getAchievements()` | GET | `/accountability/achievements` | `accountability.py:1650` | MATCH |
| `getPartnershipAchievements()` | GET | `/accountability/{id}/achievements` | `accountability.py:1697` | MATCH |

### Community Accountability (Experience)
| Frontend Method | Method | Endpoint | Backend Route | Status |
|---|---|---|---|---|
| `getHub()` | GET | `/experience/community-accountability` | `experience/community_router.py:162` | MATCH |

---

## Additional Issues Found During Audit

### [SEVERITY: P1] Frontend-Backend Mismatch: getModerationSettings has no backend GET route

**Frontend**: `community_repository.dart:1004-1016` -- GET `/community/groups/{id}/moderation`
**Backend**: `community.py:4206` -- PUT `/community/groups/{id}/moderation` (only PUT, no GET)
**Issue**: The frontend calls GET to fetch moderation settings, but the backend only exposes a PUT endpoint for updating them. There is no GET handler.
**Impact**: Loading group moderation settings will fail with a 405 Method Not Allowed. Moderators cannot view current moderation settings from the app.

---

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| P0 | 2 | Completely broken features: resource quality list returns empty; task complete returns 404 |
| P1 | 3 | Non-functional features: unmute wrong method+path; reject resource no backend; moderation GET missing |
| P2 | 2 | Fragile/best-effort: hardcoded API path; sort param enum mismatch risk |
| **Total** | **7** | |

**Overall**: 100+ API contracts verified across community and accountability modules. 7 issues found, 2 are P0 (production-breaking), 3 are P1 (feature-breaking), 2 are P2 (fragile/degraded).
