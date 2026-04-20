# SPARKLE Aurora Stage 16 Extract Dry-Run Report (2026-04-20)

> Workstream: `WS-MWL-EXTRACT`
> Purpose: freeze the bounded extractor behavior and its pre-wire precision evidence.

## 1. Extractor Boundary

Stage 16 ships a deliberately narrow rule-based extractor.

It will only emit a candidate when the user turn contains:

1. a first-person / recent-context signal
2. a concrete action or schedule signal
3. no banned trait / personality / permanent-self inference language

This is intentionally stricter than a “capture everything interesting” design, because Stage 16 is optimizing for trustworthy precision, not recall.

## 2. Frozen Cold Dataset

Fixture:

- `backend/tests/fixtures/memory_inferred_cold_dataset.json`

Composition:

- positives: `8`
- negatives: `4`

## 3. Verification Command

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_memory_inferred_write_lane.py::test_memory_inferred_extractor_precision_fixture \
  -q
```

## 4. Result

- predicted positives: `8`
- true positives: `8`
- false positives: `0`
- frozen precision: `1.00`

This exceeds the Stage 16 dispatch target `>= 0.90` and stays well above the Path C kill threshold `< 0.85`.

## 5. Caveat

This is an internal cold dataset report, not a substitute for the one-week operational gray window required before Stage 17 Path A can claim live readiness.

It also does not widen the extractor claim beyond Stage 16's bounded schema:

1. no free-form LLM memory writeback
2. no trait / preference / mastery inference
3. no downstream decision-path consumption

## 6. Verdict

`WS-MWL-EXTRACT` is engineering-green.

Operational release confidence still depends on the later gray-window observation.
