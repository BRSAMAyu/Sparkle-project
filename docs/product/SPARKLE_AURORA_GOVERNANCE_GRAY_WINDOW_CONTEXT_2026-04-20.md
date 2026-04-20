# SPARKLE Aurora Governance Gray Window Context Addendum (2026-04-20)

> Purpose: adapt Aurora's gray-window governance to pre-launch products without weakening the discipline that gray observation is a real gate.
> Status: governance addendum
> Scope: Stage 17 and any later Aurora stage that cites a gray window as an entry condition

---

## 1. Why This Addendum Exists

Aurora inherited its gray-window rule from a live-product context:

- real user traffic
- real revoke behavior
- real long-tail language distribution
- real operational load

Sparkle is currently **pre-launch**. Requiring a 7-day production gray window before any pre-launch stage can proceed creates a physically impossible gate and turns governance into dead text.

This addendum does **not** weaken the gray-window principle. It contextualizes it.

---

## 2. Gray Window Context Classes

Every Aurora stage that names a gray window must explicitly choose one and only one of the following contexts:

| Context | Gray Window Form | Minimum Requirement |
| --- | --- | --- |
| `Live` | Production Gray Window (`PGW`) | at least 7 natural days |
| `Pre-launch` | Simulated Gray Window (`SGW`) | at least 12 hours wall-clock + 44 frozen personas + at least 360 sessions + at least 4000 turns + 5-worker cap |
| `Skipped` | Explicit skip path | deferred-validation list plus explicit risk acknowledgement |

### 2.1 Live

Use `PGW` when the product has real user traffic.

Required evidence:

- real write counts
- real precision spot checks
- real Rule-governance exceptions
- real revoke and toggle behavior

### 2.2 Pre-launch

Use `SGW` when the product has **no real users yet but the system is runnable end-to-end**.

Required evidence:

- persona-driven synthetic sessions
- adversarial rule-boundary pressure
- independent audit scoring
- backpressure and revoke simulation

### 2.3 Skipped

`Skipped` is allowed only when the user explicitly accepts delayed validation risk.

Required evidence:

- a deferred-validation list in handoff Section 6
- an explicit acknowledgement record such as `SPARKLE_SKIP_GRAY_WINDOW_ACK=<SHA256(user_identity||timestamp)>`
- a mandatory follow-up run once the product has real users

Document-only statements are not enough for `Skipped`.

---

## 3. Current Sparkle Classification

Current Sparkle classification for Stage 16 -> Stage 17:

- context: `Pre-launch`
- current real-user count: `0`
- required gate form: `SGW`

This classification must be stated explicitly in the stage dispatch or handoff. It may not be assumed implicitly.

---

## 4. What SGW Can And Cannot Replace

SGW is a substitute for three of the four intended gray-window protections:

| Protection Goal | SGW Coverage |
| --- | --- |
| cold-dataset distribution bias | yes |
| Rule-boundary edge violations | yes |
| revoke / kill-switch technical correctness | yes |
| async backpressure under sustained load | yes |
| real user acceptance / offense / trust response | no |

The missing dimension is real user mindshare and acceptance:

- whether users feel inferred memory is intrusive
- when and why users choose revoke
- real acceptance of `AI 自动记忆`
- long-tail drift over weeks of actual use

These must be explicitly deferred until real-user traffic exists.

---

## 5. Governance Constraints

### 5.1 No Silent Self-Exception

This addendum is proposed and approved by the Chief Architect because the previous live-only gray-window rule was inapplicable in a pre-launch environment.

Once real users exist, Sparkle must compare `SGW -> PGW` gap and verify that the deferred validation items stayed within the declared limits of this addendum.

If the first `SGW -> PGW` comparison shows a gap greater than `20%` on any shared metric, the governance rule must be reopened and the exception audited.

### 5.2 Frozen Method Before Measurement

Any SGW run must freeze the following before execution:

- persona coverage schema
- adversarial-agent prompt contract
- audit-agent scoring protocol
- hard/soft violation thresholds
- report format and acceptance thresholds

No scoring prompt or threshold may be modified after the SGW run starts.

### 5.3 Stage-Local Engineering Risks Still Need Their Own Answers

SGW does not replace stage-design decisions.

For Stage 17 specifically, the following were already resolved in the dispatch and remain required independently of SGW:

- Rule Z HMAC boundary
- `WS-SOC-NAMESPACE`
- `social_context` isolation from `community_context`
- Router A/B prompt influence check
- Accountability health audit
- `RouterContextReader` as a temporary implementation of the future `SocialContextProvider` interface, with Stage 18 obligated to swap in the Aggregator-backed provider

---

## 6. Entry-Gate Rule

For any stage running under `Pre-launch` context:

1. the stage may not start implementation until `SGW` is green
2. the `SGW` report artifact must exist on disk
3. the user must explicitly declare `SGW passed`

For Stage 17 specifically, the SGW evidence must be:

- `docs/product/SPARKLE_AURORA_STAGE16_SGW_FRAMEWORK_2026-04-20.md`
- `docs/product/SPARKLE_AURORA_STAGE16_SGW_REPORT_2026-04-2X.md`

---

## 7. Closeout Rule

If `inferred_extraction` writes exist under a stage that required `SGW`, the stage closeout is incomplete unless the matching `SGW` report artifact exists and is referenced from the handoff.

This is a governance requirement even if technical CI enforcement is added later.

---

## 8. Sparkle Stage 17 Consequence

Stage 17 no longer waits for a physically impossible 7-day production gray window.

Instead, it waits for:

1. Stage 16 `SGW` completion
2. `Hard violation = 0`
3. `Soft violation rate < 5%`
4. user declaration that `SGW` passed

Stage 17 engineering remains blocked until those four conditions are met.
