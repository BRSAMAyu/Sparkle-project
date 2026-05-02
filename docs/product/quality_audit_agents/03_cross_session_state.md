# Quality Audit Agent Report: 03_cross_session_state

Agent ID: a04f43012bf74f64c

I'll conduct a thorough audit of cross-session continuity and long-term state stability in Sparkle. Let me start by locating and reading all the relevant files.

---

Good, I've located all the files. Now let me read them all in parallel.

---

Now let me find the actual comeback context implementation (the test references `AuroraRuntimeV1Service.get_comeback_context`).

---

Now let me look at the Flutter-side state management more carefully -- particularly what happens on logout and app lifecycle transitions.

---

Now let me check the auth provider for logout invalidation logic.

---

Let me check for the contradiction handling in memory and see if there are memory cleanup/bloom mechanisms.

---

Let me check the memory consolidation and evolution services for bloat prevention.

---

Now I have a comprehensive picture. Let me compile the full audit report.

---

---

# Cross-Session Continuity and Long-Term State Stability Audit Report

## DIMENSION 1: Cross-Session Continuity Quality

### 1. Comeback Context Depth

**Rating: EXCELLENT**

**Evidence:**

The comeback system in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/runtime_v1/service.py` (`get_comeback_context`, lines 308-500) implements genuinely different experience tiers:

- **Tier 1: silent_resume** (under 30 minutes) -- Returns `message=""` and `should_show_message=False`. No nudge at all. The user just picks up where they left off. This is correct: an active session within 30 minutes should feel completely seamless.

- **Tier 2: light_resume** (30 minutes to 8 hours) -- Builds a specific message like `"继续上次的「函数极限」。上次 Aurora 问的是：「那你想先从函数极限还是导数开始？」"`. This references the ACTUAL topic from the last chat session, not a generic placeholder. The `_latest_chat_continuity` method (line 2148) loads the most recent chat session, extracts the topic summary from real messages, and finds the latest unanswered assistant question.

- **Tier 3: personalized_return** (short gaps with plan context) -- Includes time-of-day greeting, plan status, calendar awareness, and a specific "30-minute保底版" suggestion tied to the user's actual next task.

- **Tier 4: checkpoint_debrief** (3+ days) -- The message at line 2401-2408 is notably warm: `"你已经 {days_away} 天没来了，我保留着上次的进度。你的{plan_label}还剩 {days_str}，最近最适合重新捡起来的是「{focus}」。{still_time}——如果累了，{light_restart_suggestion}"`. It references the specific subject, specific task focus, and acknowledges the user might be tired.

**Strengths:**
- Activity detection uses `UserActivityService.get_last_real_activity_at`, which checks task completions, chat messages, AND focus sessions -- not just login timestamps (confirmed by test lines 232-264 that verify it uses task completion, chat messages, and focus sessions over login).
- The `unfinished_items` list (line 2314) surfaces up to 3 concrete resume paths: pending core session, unanswered question, and next task. This is not a generic "welcome back" -- it is a personalized set of action buttons.
- The `_comeback_light_restart_suggestion` (line 2381) always references the user's actual next task, never a generic placeholder.

**Minor gap:** The >3-day message does not explicitly reference specific past conversations by topic name beyond what the latest chat session provides. It leans heavily on plan/task context. A user who was away for 14 days might appreciate a mention like "上次我们聊到你对 TCP 滑动窗口比较困惑" -- but this is a refinement, not a flaw.

---

### 2. Checkpoint Personalization Depth

**Rating: EXCELLENT**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/checkpoint_nudge_service.py`:**

- **Specific progress references**: The `_progress_facts` method (line 492) generates concrete facts: `"完成了 7/10 个任务"`, `"当前完成率 70%，原本预期 85%"`, `"最需要留意的是「TCP 流量控制」"`. These are drawn from actual task data, not templates.

- **Narrative deduplication**: The `_too_similar_to_history` method (line 656) uses `SequenceMatcher` with a 0.7 threshold against the last 12 checkpoint openings. The `_checkpoint_opening` method (line 590) generates multiple draft variants (continuity, progress_delta, unclosed_question, open_thread, minimal_debrief) and picks the first one that is not too similar to previous openings. If ALL drafts are too similar, it appends a meta-acknowledgment: `"这次我会换一个聚焦点，只问最必要的部分。"` with variant label `"{variant}_deduped"`. This is sophisticated -- it would genuinely prevent "this week you worked hard" from repeating 8 weeks in a row.

- **Open threads from previous sessions**: The `_open_runtime_threads` method (line 430) loads up to 12 previous `AuroraStateSnapshot` objects from the database, extracts informational tensions with non-resolved status, and latent threads. It deduplicates and returns up to 3 threads. These are then used in question generation (line 536: `"上次留下的「{open_threads[0]}」，现在更像解决了、还卡着，还是暂时不重要了？"`). This is specific thread carry-forward.

- **Unclosed questions**: The `_unclosed_questions` method (line 463) actually parses assistant messages to extract question fragments (lines after question marks), and surfaces these in the next checkpoint: `"上次我问到「{unclosed_questions[0]}」，后来你实际试了一下吗？"`.

**Strengths:**
- The question plan (`_checkpoint_question_plan`, line 509) is adaptive: it prioritizes continuity questions first, then bottleneck questions if behind, then minimum-viable-step questions if the gap is large. Only if none apply does it fall to a generic "keep or adjust".
- The debrief flow (`CheckpointDebriefService`, line 787) carries forward the full debrief context from the nudge into a structured Redis-backed Q&A session with a 1-hour TTL.

---

### 3. Core Session Resume Quality

**Rating: GOOD**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/core_session.py`:**

- **Resume token mechanism**: Sessions use opaque tokens (`acs_{uuid}`) that rotate on every interaction (`_refresh_resume_token`, line 604). When a user pauses (`pause_session`, line 507), they get the message: `"好，我们先暂停在这里。回来时我会从这次校准继续，不会让你重讲一遍。"`. When they resume (`_resume_session_from_token`, line 575), the message is: `"我们从刚才暂停的地方继续。你不用重讲，我还保留着前面的判断。"`. This explicitly addresses continuity anxiety.

- **Session expiry handling**: `_build_expired_summary` (line 642) produces genuinely useful summaries: `"上次我们围绕「{scope}」聊了 {turns} 轮，但会话已经超过可恢复时间。我保留这段摘要供你回看，不会把未确认内容直接写入长期判断。"`. This is careful -- it tells the user what was preserved and what was NOT committed. The expired session message (line 633) is also good: `"上次的深度对话已结束。你可以看看我们停在了哪里，也可以重新开始一次短校准。"`.

- **Graceful degradation**: When a resume token is invalid, `_resume_session_from_token` falls back to loading the last session by user ID (line 569). If the last session is expired, it returns it anyway so the user can at least see what happened. If nothing exists, it raises `LookupError`.

- **Redis-only storage**: All session state is in Redis with a 30-minute max TTL (`SESSION_TTL_SECONDS = 30 * 60`). This is a design trade-off: sessions are intentionally ephemeral. The idle TTL is 10 minutes.

**Gaps:**
- When Redis restarts, all sessions disappear without warning. The `load` method (line 303) returns `None` if Redis returns nothing, and the `from_dict` deserialization catches exceptions silently. There is no persistence-to-disk or recovery mechanism. A Redis restart mid-session would feel like the conversation vanished.
- The session limit of 6 user turns and 12 Aurora messages (lines 44-45) means some sessions may feel truncated if a user has complex calibration needs. However, the `_finalize_session` always produces a `CalibrationResult`, so the session never just "ends" -- it always has a structured outcome.

---

## DIMENSION 2: Long-Term State Stability

### 4. Provider State Management

**Rating: ADEQUATE**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/providers/core_keep_alive_provider.dart` and `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/session_refresh_service.dart`:**

- **KeepAlive list vs. session-bound list**: There are TWO separate registries. `core_keep_alive_provider.dart` lists 10 providers (auth, profile, aurora status, chat, plans, theme, BGM). `session_refresh_service.dart` lists 30 providers in `sessionBoundProvidersProvider`. The keep-alive providers survive tab switches; the session-bound providers get invalidated on login/logout/session-refresh.

- **Logout invalidation**: The `logout()` method in `auth_provider.dart` (line 559) calls `SessionRefreshService.refreshSessionBoundProviders(_ref)` which iterates all 30 session-bound providers and invalidates each one. This is thorough -- it covers dashboard, chat, tasks, plans, calendar, community, achievements, leaderboard, focus statistics, galaxy, and profile contexts.

- **Missing from keep-alive**: Several STATEFUL providers that seem important for cross-tab persistence are NOT in the keep-alive list: `taskListProvider`, `calendarProvider`, `unifiedCalendarProvider`, `dashboardProvider`, `focusStatisticsProvider`, `achievementProvider`, `streakHistoryProvider`, `leaderboardProvider`, `galaxyProvider`. These would lose state on tab switch and need to re-fetch. Whether this is intentional (fresh data on tab switch) or an oversight depends on UX intent, but it means the user may see loading spinners when switching tabs.

- **App background-to-foreground**: There is NO centralized `WidgetsBindingObserver` for app lifecycle state. The `session_refresh_service.dart` only exposes a static method (`refreshSessionBoundProviders`) that is called explicitly on login/logout. The only lifecycle observer is `_BgmLifecycleObserver` in `bgm_service.dart` which only handles BGM pause/resume. There is no mechanism to refresh stale data when the app comes back from background. This means a user who backgrounds the app for 30 minutes and returns might see stale task lists, stale plan progress, and stale calendar data until they manually pull-to-refresh or navigate away and back.

---

### 5. Aurora State Persistence

**Rating: ADEQUATE**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/core_session.py` and `/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/runtime_v1/service.py`:**

- **TTL/eviction strategy**: Core sessions use `SESSION_TTL_SECONDS = 30 * 60` (30 minutes max) and `IDLE_TTL_SECONDS = 10 * 60` (10 minutes idle). Runtime state uses `AURORA_RUNTIME_STATE_TTL_SECONDS = 24 * 60 * 60` (24 hours). Debrief sessions use `DEBRIEF_SESSION_TTL_SECONDS = 60 * 60` (1 hour). These are all Redis TTL-based, so stale data is automatically evicted. This is appropriate.

- **Redis restart behavior**: When Redis is unavailable, the system degrades gracefully. The `AuroraCoreSessionStore.load` method (line 303) returns `None` if Redis is `None` or the key does not exist. The `get_comeback_context` method uses `self.redis` checks at entry and falls back to None. The `_persist_runtime_state` method (line 2442 in service.py) logs a warning if Redis write fails but does not crash. However, there is NO recovery mechanism -- if Redis restarts, all runtime state, all resume tokens, all debrief sessions, all self-model state, and all inference claims are lost. The system would start from a blank slate.

- **Partially corrupted state**: The `from_dict` class method on `AuroraCoreSession` (line 206) uses `.get()` with defaults for every field, so partially missing data would be filled with defaults rather than causing errors. The `load` method (line 303) catches all exceptions and returns `None`. This is defensive but means a corrupted session is silently discarded rather than repaired.

- **No persistence layer**: There is no write-through to a durable store (PostgreSQL). The `AuroraStateSnapshot` model exists (used by checkpoint_nudge_service), but core session state is purely Redis-volatile. The self model (30-day TTL) would also be lost.

**Mitigation in practice**: The comeback context system (`get_comeback_context`) does NOT depend on Redis runtime state -- it rebuilds from PostgreSQL (plans, tasks, chat messages). So a Redis restart would lose the fine-grained runtime state but not the fundamental ability to welcome the user back with context. The checkpoint snapshots stored in PostgreSQL provide a partial recovery path.

---

### 6. Memory Quality Over Time

**Rating: GOOD**

**Evidence from `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/memory_service.py` and related services:**

- **Memory bloat prevention**: 
  - Preferences use version-based replacement: `upsert_preference` (line 86) creates a new version and marks the old one as `replaced_by_id`. The `list_preference_records` method (line 626) returns only the latest version per key. Old versions remain in the database but are not loaded into context.
  - Goals have explicit lifecycle: `INACTIVE_GOAL_STATUSES = {"completed", "archived", "cancelled"}` and `expires_at` timestamps. `list_active_goals` (line 523) filters by status and expiry.
  - Episodic memories have soft-delete (`deleted_at`, `retracted_at`, `revoked_at`), but there is NO automatic pruning or consolidation limit. The `list_recent_episodic` (line 678) loads up to `limit` memories, but the database itself can grow unboundedly. The `WorkingMemoryConsolidationService` consolidates working memory entries into LTM, but this adds memories rather than pruning them.
  - There is no explicit memory cap or per-user quota visible in the service code.

- **Relevance and recency ranking**: 
  - Episodic memories are loaded with `order_by(EpisodicMemory.occurred_at.desc()).limit(limit)` -- purely recency-based, not relevance-based. There is an `importance_score` field and a `confidence` field, but `list_recent_episodic` does not use them for ordering.
  - Preferences use `version.desc()` ordering, always returning the latest.
  - There is no semantic search or relevance scoring at retrieval time in the memory service itself (embeddings exist but are used for vector search in other services).

- **Contradiction handling**: 
  - The system handles contradictions through the `apply_correction` method (line 1039). When a user says "that's wrong", the system offers three actions: `reject` (retract), `no_longer_applicable` (retract), and `lower_confidence` (decrement by 0.1). Each correction increments `correction_count`.
  - The `record_memory_reference_outcome` method (line 1134) tracks whether a memory was "accepted", "corrected", "ignored", or "denied" when it was surfaced to the user. Accepted memories get +0.03 confidence; denied/corrected memories get -0.1 confidence. This creates a natural decay for contradicted memories.
  - However, there is NO automatic contradiction DETECTION. The system does not proactively check if a new memory contradicts an existing one. It relies entirely on the user or the LLM to notice and trigger a correction. If the user says "I prefer deep explanations" and later says "I prefer concise answers", both memories would coexist unless explicitly corrected.

  - The `MemoryEvolutionService` tracks changes and their impact but does not arbitrate contradictions.

---

## Summary Rating Table

| Area | Rating | Key Strength | Key Gap |
|------|--------|-------------|---------|
| 1. Comeback context depth | **EXCELLENT** | 4 genuinely different tiers with specific task/topic references | Long-absence messages could reference past conversation topics beyond just plan/task |
| 2. Checkpoint personalization | **EXCELLENT** | SequenceMatcher dedup, open thread carry-forward, adaptive question plan | None significant |
| 3. Session resume quality | **GOOD** | Rotating tokens, explicit continuity messages, structured expiry summaries | No Redis persistence/recovery; Redis restart = all sessions lost |
| 4. Provider state management | **ADEQUATE** | Thorough logout invalidation (30 providers), explicit keep-alive registry | No app background-to-foreground refresh; many stateful providers not in keep-alive |
| 5. Aurora state persistence | **ADEQUATE** | TTL-based eviction, graceful degradation on Redis failure, defensive deserialization | No durability layer; Redis restart loses all runtime state, self-model, resume tokens |
| 6. Memory quality over time | **GOOD** | Version-based preference replacement, confidence decay on denial, explicit correction mechanisms | No automatic contradiction detection; no memory bloat cap; episodic retrieval is recency-only, not relevance-ranked |

## Key Files Audited

- `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/aurora/test_comeback_context.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/runtime_v1/service.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/context_builder.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/checkpoint_nudge_service.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/core_session.py`
- `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/providers/core_keep_alive_provider.dart`
- `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/session_refresh_service.dart`
- `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/auth/presentation/providers/auth_provider.dart`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/memory_service.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/working_memory_consolidation_service.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/memory_evolution_service.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/memory_jobs.py`

## Top 3 Recommendations

1. **Add app background-to-foreground state refresh**: The Flutter app has no centralized lifecycle observer that refreshes stale provider data on resume. A user who backgrounds the app for 30+ minutes returns to potentially stale task lists, plan progress, and calendar. A single `WidgetsBindingObserver` in the root widget that calls `SessionRefreshService.refreshSessionBoundProviders` on `AppLifecycleState.resumed` would close this gap.

2. **Add memory contradiction detection**: When a new episodic memory is written, the system should check if it semantically contradicts an existing memory (using the embedding field that already exists). Even a simple same-subject check would catch "I prefer X" vs. "I prefer not-X" cases. The correction infrastructure is already excellent; what is missing is the trigger.

3. **Add minimal durability for core session state**: The Aurora core session state is valuable enough that losing it all on a Redis restart is a meaningful continuity break. A periodic write-through of session state to PostgreSQL (even just for paused sessions) would provide a recovery path. The `AuroraStateSnapshot` model already exists as a precedent for this pattern.