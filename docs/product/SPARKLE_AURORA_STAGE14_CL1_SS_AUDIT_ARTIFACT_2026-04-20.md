# SPARKLE Aurora Stage 14 WS-CL1-SS-AUDIT Artifact (2026-04-20)

> **Workstream**: `WS-CL1-SS-AUDIT`
> **Purpose**: lock the audit question, criteria, and Stage 15 consequence before the docs-only verdict is written.

## 1. Exact Compression Under Review

The only source-state compression under review is:

```python
state_{tool_category or 'general'}
```

This is the current `ToolPreferenceRouter._build_history_source(...)` contract.

## 2. Production Paths Using It Today

The compressed state currently affects:

1. `ToolPreferenceRouter.update_learner_from_history()`
2. `RouterNode` candidate re-ranking when tool-preference learning is active

It does **not** yet drive a user-visible decision path.

## 3. Blocking vs Non-Blocking Criteria

`blocking` means:

1. the current compression destroys information required for the bounded Stage 15 wire-on claim
2. a truthful Stage 15 claim would overstate what the learner actually learned

`non-blocking` means:

1. the bounded Stage 15 claim can be kept truthful at the current granularity
2. the remaining lossiness can be carried as a caveat rather than a merge-blocking redesign

## 4. Stage 15 Consequence Lock

If the verdict is `blocking`:

1. Stage 15 becomes `Path A-blocked`
2. source-state redesign must happen before any wire-on design

If the verdict is `non-blocking`:

1. Stage 15 may continue only with a claim strictly bounded to within-category tool preference
2. the caveat must remain explicit in the Stage 15 entry doc

## 5. Boundary Lock

This WS writes **no runtime code**.

Allowed:

1. code-path audit
2. architecture verdict
3. Stage 15 implication text

Not allowed:

1. source-state redesign
2. learner retraining changes
3. shadow-runtime code
