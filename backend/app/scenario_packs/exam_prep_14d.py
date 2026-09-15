"""Built-in exam prep scenario pack."""

from __future__ import annotations

from pathlib import Path

from app.scenario_packs.registry import load_pack_manifest

EXAM_PREP_14D_PACK_ID = "exam_prep_14d@v1.0"
EXAM_PREP_14D_MANIFEST_FILENAME = "exam_prep_14d_v1_0.json"
EXAM_PREP_14D_MANIFEST_PATH = Path(__file__).with_name(EXAM_PREP_14D_MANIFEST_FILENAME)


def load_exam_prep_14d_manifest():
    """Load the built-in 14-day exam prep scenario pack."""

    return load_pack_manifest(EXAM_PREP_14D_MANIFEST_PATH)
