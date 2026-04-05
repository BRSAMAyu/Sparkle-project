# Sparkle Phase B Loss Review

> Date: 2026-04-05  
> Scope: required durability-pass memo for the three tracked Phase B dossiers

This memo stays intentionally narrow. It exists to stop repeated reopening of the same benchmark arguments inside Phase B.

## 1. `phase_b_materials_and_weak_spots`

- Current benchmark status: no longer a live loss after the durability pass; `sparkle_phase_b:dashscope_chat` wins this dossier in the latest `benchmark_v1` report.
- Why it was previously vulnerable: the earlier gate/harness stack over-trusted metadata and under-validated whether the rendered plan explicitly grounded itself in the uploaded materials.
- Primary classification: `Phase B issue`
- Action: `defer`
- Decision note: artifact-level validation landed in this pass, and the dossier now clears the benchmark. Do not reopen this scenario inside Phase B unless future human evaluation shows that rendered plans still omit material-specific evidence.

## 2. `phase_b_vague_goal_needs_clarification`

- Current benchmark status: still a loss; the strongest raw baseline wins by being extremely narrow and asking the highest-value clarification with less extra framing.
- Why Sparkle loses: Sparkle Phase B is now correctly withholding the full plan and producing one action plus one unlock question, but it still carries slightly more explanatory overhead than the strongest raw baseline on a dossier where brevity is the product.
- Primary classification: `benchmark issue`
- Action: `fix_now`
- Decision note: the durability pass already tightened next-step-only rendering toward one action plus one question. That is the only immediate fix to take in Phase B. If the dossier still loses after this, do not keep tuning the benchmark or contract; defer any further work to a later authoring-quality pass or human-eval review.

## 3. `phase_b_high_readiness_full_plan`

- Current benchmark status: still not a clear win; the strongest raw baseline remains at least tied and may edge Sparkle depending on score spread.
- Why Sparkle does not clearly win: the raw baseline produces a very clean long-horizon syllabus-mapping framework, while Sparkle Phase B still spends more tokens on structural framing and caveats than on turning the high-readiness dossier into the most compact milestone plan possible.
- Primary classification: `Phase B issue`
- Action: `defer`
- Decision note: this is a plan-authoring quality issue, not a contract or strategy-compiler issue. Do not reopen Phase B to chase this. Revisit only in a later authoring pass if multiple human reviews agree that high-readiness full plans are still over-structured.

## Freeze Rule

- These three dossiers are now frozen as the official Phase B review set.
- Future changes must not be justified by trying to make one benchmark scenario look better in isolation.
- Reopen only if repeated human evaluation shows a mismatch large enough to justify changing the product, not just the benchmark.
