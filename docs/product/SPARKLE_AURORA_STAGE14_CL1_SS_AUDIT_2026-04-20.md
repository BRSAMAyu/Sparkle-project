# SPARKLE Aurora Stage 14 WS-CL1-SS-AUDIT (2026-04-20)

> **Workstream**: `WS-CL1-SS-AUDIT`
> **Compression under review**: `state_{tool_category or 'general'}`
> **Verdict**: `blocking`

## 1. Exact Code Fact

The current source-state builder remains:

```python
return f"state_{record.tool_category or 'general'}"
```

That means the learner sees only category-level state identity plus the `general` fallback.

## 2. Production Paths Affected

This compressed state currently feeds:

1. `ToolPreferenceRouter.update_learner_from_history()`
2. `RouterNode` route exploration when persistent learner state is available

## 3. Why The Compression Is Too Lossy

The current encoding drops several distinctions that matter for any truthful Stage 15 wire-on claim:

1. workflow position:
   - opening-plan step vs refinement step collapse into the same `state_plan`
2. tool sequence:
   - a route after prior tool success/failure is not distinguishable from a cold-start route in the same category
3. user intent inside one category:
   - retrieval, diagnosis, summary, and status lookup can all collapse into one category bucket
4. temporal context:
   - recent friction / repetition / recovery state is not present in the source key
5. cross-category transition meaning:
   - the learner cannot represent how one state led into another; it only sees isolated category buckets

## 4. Why This Is `blocking`

Stage 15 wire-on is supposed to be a bounded but still honest front-door read path.

At the current compression level, the system can only support a very narrow claim:

> "within one coarse tool category, we may have learned a preferred tool."

That is materially weaker than a safe routing claim about user context or workflow understanding.

Because the current code and product language do **not** yet encode that stricter claim boundary, shipping a wire-on path now would risk overstating what the learner actually knows.

## 5. Conditional Caveat

This verdict is blocking for the current Stage 15 entry.

It is **not** a permanent constitutional ban.

If a future Stage 15 design is explicitly narrowed to:

1. within-category preference only
2. no stronger product claim than that
3. clear user-facing caveat text

then Chief Architect may choose to revisit the verdict through a new amendment doc.

That narrowing has **not** been designed or accepted in Stage 14, so this audit remains `blocking`.

## 6. Stage 15 Consequence

Because `WS-CL1-SCALE` stays green but this audit is `blocking`, Stage 14 locks:

- `Path A-blocked`

Wire-on remains deferred until source-state redesign or an explicitly narrowed Stage 15 claim is accepted.
