# Audit Fix Work Log

**Started**: 2026-05-10
**Executor**: Claude (main agent)
**Scope**: Fix all P0/P1/P2/P3 issues from community_accountability audit reports

---

## Phase 1: P0 Fixes (9 issues)

### P0-01: JWT in WebSocket URL (Security)
- **File**: `mobile/lib/features/community/data/services/community_websocket_service.dart`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-02: Go query references non-existent `community_posts` table
- **File**: `backend/gateway/internal/service/community_query.go`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-03: `isLikedByMe` always false — Redis sets never written
- **File**: `backend/gateway/internal/service/community_command.go` + `community_query.go`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-04: Feed endpoint unauthenticated
- **File**: `backend/gateway/internal/api/v1/community.go`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-05: PII leak in Redis event stream
- **File**: `backend/app/services/social_signal_bridge.py`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-06: `/community/resources` response shape mismatch
- **File**: `mobile/lib/features/community/data/repositories/community_share_repository.dart`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-07: Privacy budget engine ephemeral
- **File**: `backend/app/services/community_signal_bridge.py` + `backend/app/signals/privacy_community_intelligence.py`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-08: Partnership unique constraint doesn't cover reverse
- **File**: `backend/app/models/accountability.py`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

### P0-09: Unbounded N+1 achievement queries
- **File**: `backend/app/services/accountability_achievement_service.py`
- **Status**: PENDING
- **Investigation**: Not started
- **Fix**: Not started
- **Commit**: N/A

---

## Phase 2: P1 Fixes (27 issues)

### Go/DB P1 (7 issues)
- [ ] P1-Go-01: LikePost always publishes event on duplicate like
- [ ] P1-Go-02: posts.like_count nullable, never updated
- [ ] P1-Go-03: Missing index on posts.created_at
- [ ] P1-Go-04: Partnership unique constraint bidirectional
- [ ] P1-Go-05: GetPost query requires created_at match
- [ ] P1-Go-06: friendshipstatus enum missing REJECTED/CANCELLED
- [ ] P1-Go-07: handlePostLiked read-modify-write race condition

### Python P1 (12 issues)
- [ ] P1-Py-01: _check_perfect_month uses UTC, not user timezone
- [ ] P1-Py-02: Streak calculation inconsistency
- [ ] P1-Py-03: _is_first_partnership logic wrong
- [ ] P1-Py-04: award_achievement bypasses _unlock_achievement
- [ ] P1-Py-05: datetime.utcnow() deprecated
- [ ] P1-Py-06: Friendship reverse-pending canonical ordering
- [ ] P1-Py-07: SocialSignalEventConsumer lacks DLQ
- [ ] P1-Py-08: N+1 privacy check queries
- [ ] P1-Py-09: Celery tasks asyncio.run() with sync context
- [ ] P1-Py-10: Missing pagination in group checkin reminders
- [ ] P1-Py-11: Privacy budget double-spend
- [ ] P1-Py-12: Remaining epsilon calculation wrong

### Flutter P1 (5 issues)
- [ ] P1-Fl-01: Hardcoded Chinese in accountability_detail_screen
- [ ] P1-Fl-02: Null crash in _FriendTile
- [ ] P1-Fl-03: Null crash in _PartnershipCard
- [ ] P1-Fl-04: create_post_screen isChinese bypass
- [ ] P1-Fl-05: community_main_screen isChinese bypass

### Cross-Layer P1 (3 issues)
- [ ] P1-CL-01: unmuteMember method+path mismatch
- [ ] P1-CL-02: rejectResource no backend endpoint
- [ ] P1-CL-03: getModerationSettings no GET route

---

## Phase 3: P2 Fixes (42 issues)
*(To be detailed as work progresses)*

## Phase 4: P3 Fixes (28 issues)
*(To be detailed as work progresses)*

---

## Additional Issues Found During Fix
*(To be populated as new issues are discovered)*

---

## Verification Log
*(Independent Opus agent verification results)*
