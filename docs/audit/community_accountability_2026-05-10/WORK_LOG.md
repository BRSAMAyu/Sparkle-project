# Audit Fix Work Log

**Started**: 2026-05-10
**Executor**: Claude (main agent)
**Scope**: Fix all P0/P1/P2/P3 issues from community_accountability audit reports

---

## Phase 1: P0 Fixes — ALL COMPLETE ✅

| # | Issue | Status | Commit |
|---|-------|--------|--------|
| P0-01 | JWT in WebSocket URL | ✅ Fixed — moved to Authorization header | `17959ea` |
| P0-02 | `community_posts` table name | ✅ Fixed — changed to `posts` | `27dbd8b` |
| P0-03 | `isLikedByMe` always false | ✅ Fixed — added SADD/SREM for post:likes | `27dbd8b` |
| P0-04 | Feed endpoint unauthenticated | ❌ FALSE ALARM — dead code; proxy routes have auth | N/A |
| P0-05 | PII leak in event stream | ✅ Fixed — removed target_name, consumer resolves from DB | `f504392` |
| P0-06 | resources response mismatch | ✅ Fixed — handles both List and Map responses | `f504392` |
| P0-07 | Privacy budget ephemeral | ✅ Fixed — documented DB-backed path as authoritative | `f04c0d9` |
| P0-08 | Partnership unique constraint | ✅ Fixed — added LEAST/GREATEST partial unique index | `aa8676d` |
| P0-09 | N+1 achievement queries | ✅ Fixed — single query + Python group-by | `aa8676d` |
| Extra | SQL injection (raw SQL) | ✅ Fixed — ORM update with soft-delete filter | `8aea70e` |
| Extra | completeTask endpoint missing | ✅ Fixed — added POST /tasks/{id}/complete | `8aea70e` |

**Verified**: All P0 fixes independently verified by Opus agent — 10/10 PASS

---

## Phase 2: P1 Fixes — IN PROGRESS

### Go/DB P1
- [x] P1-Go-01: LikePost duplicate event → check RowsAffected — `877cd95`
- [ ] P1-Go-02: posts.like_count nullable → add DEFAULT 0 NOT NULL (schema change)
- [ ] P1-Go-03: Missing index on posts.created_at (schema change)
- [x] P1-Go-04: Partnership bidirectional constraint → done in P0-08
- [x] P1-Go-05: GetPost created_at query → removed from WHERE — `877cd95`
- [ ] P1-Go-06: friendshipstatus enum missing REJECTED/CANCELLED (schema change)
- [ ] P1-Go-07: like count race condition → needs Lua script

### Python P1
- [ ] P1-Py-01: _check_perfect_month timezone (complex, needs careful testing)
- [ ] P1-Py-02: Streak calculation inconsistency (needs unification)
- [x] P1-Py-03: _is_first_partnership logic → check achievement record — `ac046b5`
- [ ] P1-Py-04: award_achievement notification type (minor)
- [x] P1-Py-05: datetime.utcnow() → _utcnow() — `ac046b5`
- [ ] P1-Py-06: Friendship canonical ordering (low risk)
- [ ] P1-Py-07: SocialSignalEventConsumer DLQ (infrastructure)
- [ ] P1-Py-08: N+1 privacy check queries (batch optimization)
- [ ] P1-Py-09: Celery asyncio.run() (needs verification)
- [ ] P1-Py-10: Missing pagination in reminders
- [x] P1-Py-11: Privacy budget double-spend → fixed in P0-07 commit
- [x] P1-Py-12: Remaining epsilon calc → fixed in P0-07 commit

### Flutter P1
- [ ] P1-Fl-01: Hardcoded Chinese in accountability_detail_screen (i18n migration)
- [x] P1-Fl-02: Null crash _FriendTile → empty guard — `b44d598`
- [x] P1-Fl-03: Null crash _PartnershipCard + wrong goal → fixed — `b44d598`
- [ ] P1-Fl-04: create_post_screen isChinese bypass (i18n migration)
- [ ] P1-Fl-05: community_main_screen isChinese bypass (i18n migration)

### Cross-Layer P1
- [x] P1-CL-01: unmute method+path → DELETE + /mute — `cc2c394`
- [x] P1-CL-02: rejectResource endpoint → added backend route — `cc2c394`
- [x] P1-CL-03: moderation GET route → added — `cc2c394`

---

## Phase 3: P2 Fixes (42 issues) — PENDING
## Phase 4: P3 Fixes (28 issues) — PENDING

---

## Additional Issues Found
- P0-04 (Feed auth) was a FALSE ALARM — CommunityHandler is dead code
- Partnership UniqueConstraint lacks soft-delete filter (noted by Opus verifier)

## Verification Log
- P0 fixes: Opus agent verified 10/10 PASS at commit `17959ea`
