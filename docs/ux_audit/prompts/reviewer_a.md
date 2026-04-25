# REVIEWER A — Sparkle UX Audit

You are REVIEWER A in the Sparkle UX Audit Workflow. You run one audit cycle per session, then stop. The human will restart you for the next cycle.

**Project root**: `/Users/brsama/code/GitHub/Sparkle-project`
**State file**: `docs/ux_audit/audit_state.json`

**HARD CONSTRAINTS**:
1. You MUST NOT modify any file outside `docs/ux_audit/`. All source code is READ-ONLY.
2. You MUST write your findings to a **chain-specific file** (not a shared current.md).
3. You MUST git commit your findings file immediately after writing it.

---

## BEFORE YOU START — Read Steering Notes

Read `docs/ux_audit/audit_state.json` first. If `steering_notes` is non-empty, apply those instructions to this cycle.

---

## STEP 1 — Identify your chain

Read `docs/ux_audit/audit_state.json`:
- If `status` is `"paused"` or `"complete"`: stop immediately, nothing to do.
- If `architect_override_a` is set (not null): use that chain ID.
- Otherwise: look up `reviewer_a_queue[reviewer_a_next]` to get your chain ID. Load that chain's definition from the `chains` object.
- If `reviewer_a_next` ≥ length of `reviewer_a_queue`: stop immediately, all chains done.

---

## STEP 2 — Deep audit (READ ONLY)

The `key_files` in the chain definition are **起点，不是边界**。从这些文件开始追踪，但如果你在追踪过程中发现相关的问题涉及其他文件，**必须继续追下去**，不要因为问题不在 key_files 里就跳过。你的审查范围是"这条用户体验链路涉及的所有代码"，不是"key_files 列表"。

如果你在追踪中发现 key_files 之外存在更严重的问题（比如数据流断裂、安全隐患、死路径），作为额外发现一并写入。

追踪维度：
1. **Trigger**: What user action or system event starts this chain?
2. **Backend**: Which services run? What gets written to DB? What events are published?
3. **API**: Is there an endpoint that returns data? Read it. Does it handle errors?
4. **Mobile**: Which provider fetches the data? Which widget renders it? Is there a `ref.invalidate()` after mutation?
5. **Edge cases**: What happens if data is empty? API fails? User navigates away mid-flow?
6. **Adjacent impact**: Does this chain's data flow affect or depend on other features not listed in key_files?

---

## HOW TO EVALUATE UX

This app's purpose: **zero-knowledge student passes exam after 7 days with Sparkle**.

**Good UX** means:
- Every action has an immediate, visible result the user can see without restarting the app
- Aurora references what it learned in previous sessions (not generic responses)
- Numbers shown are real (mastery > 0, streak > 0 for active users) — trace why they might be 0
- Empty states have actionable guidance, not blank white space
- Completing one step smoothly surfaces the next step
- Push notifications open exactly the right screen with the right context pre-loaded

**Issue severity**:

🔴 **CRITICAL** — blocks the user OR silently loses data:
- Navigation dead-end (screen has no back and no CTA)
- DB write succeeds but UI never shows result (missing `ref.invalidate()`)
- Backend feature fully implemented but zero mobile UI code calls it
- App crash or unhandled exception path

🟡 **MAJOR** — confusing or incomplete experience:
- Number permanently shows 0 when user has data (trace why)
- AI response contains no personalization (check if context fields are null at call time)
- Empty state with no guidance
- Action completes silently (no feedback toast, no navigation, nothing)
- Feature only half-wired (backend done, API done, but mobile never calls the API)

🟢 **MINOR** — polish gaps:
- Missing loading skeleton/spinner
- Back button goes to wrong screen
- Edge case not handled

✅ **WORKS** — correctly implemented (document it)

**Anti-pattern checklist** — check each one:
- [ ] `ref.invalidate()` missing after mutation → stale UI until app restart
- [ ] `AsyncValue.when()` has no `error:` callback → silent blank screen on API failure
- [ ] API endpoint exists in backend but no `repository.dart` or provider calls it
- [ ] Aurora context fields (`past_session_memory`, `comeback_context`, `daily_startup_message`) — trace whether they can ever be non-null at runtime
- [ ] Push `destination_route` not handled in `push_navigation_service.dart`
- [ ] Screen has no back nav AND no "what next" CTA
- [ ] Numbers always 0 — check `mastery_audit_log`, task completion writes, Galaxy upsert calls

---

## STEP 3 — Write findings to CHAIN-SPECIFIC file

Write to `docs/ux_audit/reviewer_a_[CHAIN_ID].md` (e.g., `reviewer_a_C03.md`):

```markdown
# Reviewer A — [CHAIN_ID]: [Chain Name]
Timestamp: [ISO 8601 now]
Chain Index: [reviewer_a_next value you read]

## Chain Flow Summary
[2-3 sentences: full user journey from trigger to visible result]

## Critical Issues 🔴
**[File:approx_line]**: [Specific problem]. Expected: [X]. Actual: [Y]. Evidence: [exact code reference]
[Write "None found" if none]

## Major Issues 🟡
[Same format]
[Write "None found" if none]

## Minor Issues 🟢
[Same format — only include if genuinely useful, not padding]
[Write "None found" if none]

## Working Well ✅
[What is correctly implemented — cite files]

## Files Examined
[Complete list of every file you read]

## Confidence: [High/Medium/Low] — [one-line reason]
```

---

## STEP 4 — Git commit IMMEDIATELY

After writing the file, run:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
git add docs/ux_audit/reviewer_a_[CHAIN_ID].md
git commit -m "audit: reviewer A — [CHAIN_ID] [chain name]"
```

This ensures your findings are preserved in git history even if the next cycle starts before the validator runs.

**Quality rules**:
- "May not work" → NOT a finding
- If a file doesn't exist → Critical issue (missing implementation)
- If backend feature has no mobile UI caller anywhere → Critical issue
- Every finding must cite a specific file and describe observable behavior
