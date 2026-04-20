# SPARKLE Aurora Stage 19 LLM Extract Dry-Run Report (2026-04-21)

This artifact records the Stage 19 dry-run posture for the first LLM extractor landing.

## Locked conclusions

1. The extractor is defaulted to dry-run.
2. Output is JSON-only and bounded by the `InferredEpisodicCandidate` contract.
3. Rule Y validation remains the hard accept/reject layer.
4. Precision is evaluated on a frozen cold-start fixture in CI because Stage 19 does not depend on live model availability inside repository tests.

## Implementation constraints

1. Default model string: `claude-haiku-4-5`
2. Single-call budget: `<= 200` tokens
3. Per-session budget: `<= 2000` tokens
4. Forbidden topics: emotion, motivation, personality, cross-user inference

## Notes

The engineering dry-run path is intentionally conservative. A candidate may be discarded for malformed structure even if the semantic guess is plausible; that behavior is accepted because Stage 19 optimizes for governed precision over recall.
