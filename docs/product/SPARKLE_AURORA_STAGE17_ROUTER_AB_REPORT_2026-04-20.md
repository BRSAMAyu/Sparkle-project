# SPARKLE Aurora Stage 17 Router A/B Report (2026-04-20)

> Status: engineering-closeout source audit
> Method note: this is a source-based prompt-influence audit, not a live LLM behavior benchmark.

## 1. Scope

Stage 17 keeps `social_context` inside the prompt-render path only. No deterministic router branch may consume `recent_person_mentions`, `person_mention`, or other Rule Z social facts as a routing signal.

## 2. Paired Cold-Start Audit

- paired cases audited: 30
- baseline intent distribution (synthetic cold-start prompts): `{'plan': 16, 'review': 14}`
- with-social intent distribution: `{'plan': 16, 'review': 14}`
- inferred KL divergence: `0.00`

Inference basis:

1. `backend/app/routing/` has `0` routing-branch hits for `recent_person_mentions|person_mention`.
2. `RouterContextReader` appears only in its provider implementation path and not inside router branching code.
3. `social_context` rendering remains behind default-OFF feature flags.

## 3. Prompt Payload Budget

- sample serialized `FrozenSocialSnapshot` tokens: `71`
- Stage 17 dispatch hard budget: `<= 200`
- result: `pass`

## 4. Codebase Audit

- `RouterContextReader` hits under `backend/app`: `1`
- provider/self hits:
  - backend/app/routing/router_context_reader.py:16:class RouterContextReader(SocialContextProvider):
- non-provider hits:
  - none
- forbidden routing-branch hits:
  - none

## 5. Conclusion

Stage 17 remains within its intended boundary: social snapshot data is a bounded prompt-context surface, not a routing decision signal. The zero-KL result above is an engineering inference from code-path equivalence, not a claim about unconstrained LLM behavior. A live model-based prompt-drift benchmark stays deferred until Stage 18/19 brings the stronger Aggregator-backed provider path and any future Sufficiency Judge obligations into scope.
