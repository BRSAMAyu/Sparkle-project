#!/usr/bin/env python3
"""Apply wt685 V3-FIX-361 confidence-qualitative copy to both arb files.

PRODUCT_LANGUAGE: raw "0.73 confidence" / 「置信度 0.73」 is banned; recommended
「我还不太确定」/「我比较确定」 with the number kept as expandable detail.
Shape: qualitative band word first, percent in parentheses as detail.

Bands follow the backend canonical cutoffs in
`backend/app/orchestration/ux_envelope.py::_confidence_band`
(high >= 0.8, medium >= 0.55, else low) — see
mobile/lib/core/extensions/confidence_band.dart for the Dart mirror.

Key names unchanged (只改值不改键名); placeholder schemas evolve
({value}Object → band+percent) exactly where the ledger anticipated
调用点传值逻辑 changes. One new key `confidenceWithBand` (band+percent select)
serves the two faces whose existing keys carry no percent placeholder:
plan_review_card's percent line and memory detail's composed value.

Run from repo root: python3 scripts/devtools/apply_wt685_confidence_qualitative.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BAND_ZH = "{band, select, high{我比较确定} medium{有一定把握} low{我还不太确定} other{把握}}（{percent}%）"
BAND_EN = (
    "{band, select, high{I'm fairly confident} medium{I'm somewhat confident} "
    "low{I'm not quite sure yet} other{Confidence}} ({percent}%)"
)

VALUES_ZH = {
    "sourceExplanationConfidence": BAND_ZH,
    "intentConfidenceLabel": BAND_ZH,
    "personaConfidence": BAND_ZH,
    "systemUpdatesConfidence": BAND_ZH,
    "planReviewConfidenceTitle": "把握有多大",
    "memoryConfidence": "把握程度",
    "memoryConfidenceValue": "把握程度：{value}",
    "memoryCorrectionLowerConfidence": "别太信这条",
    "confidenceWithBand": BAND_ZH,
}
VALUES_EN = {
    "sourceExplanationConfidence": BAND_EN,
    "intentConfidenceLabel": BAND_EN,
    "personaConfidence": BAND_EN,
    "systemUpdatesConfidence": BAND_EN,
    "planReviewConfidenceTitle": "How confident I am",
    "memoryConfidence": "Confidence",
    "memoryConfidenceValue": "Confidence: {value}",
    "memoryCorrectionLowerConfidence": "Not so sure about this",
    "confidenceWithBand": BAND_EN,
}
BAND_PERCENT_META = {
    "placeholders": {
        "band": {"type": "String"},
        "percent": {"type": "int"},
    }
}
# keys gaining/keeping an explicit @placeholders block (insertion order: band, percent)
META_KEYS = {
    "sourceExplanationConfidence": BAND_PERCENT_META,
    "intentConfidenceLabel": BAND_PERCENT_META,
    "personaConfidence": BAND_PERCENT_META,
    "systemUpdatesConfidence": BAND_PERCENT_META,
    "confidenceWithBand": BAND_PERCENT_META,
}


def apply(arb_path: Path, values: dict[str, str]) -> None:
    data = json.loads(arb_path.read_text(encoding="utf-8"))
    for k, v in values.items():
        data[k] = v
    for k, meta in META_KEYS.items():
        data[f"@{k}"] = meta
    ordered = {k: data[k] for k in data}
    arb_path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{arb_path}: {len(values)} values ensured, {len(META_KEYS)} placeholder schemas set")


def main() -> int:
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    apply(repo / "mobile/lib/l10n/app_zh.arb", VALUES_ZH)
    apply(repo / "mobile/lib/l10n/app_en.arb", VALUES_EN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
