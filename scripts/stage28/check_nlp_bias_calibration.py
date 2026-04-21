#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.traits_bias_calibration import CALIBRATION_SAMPLES  # noqa: E402
from app.services.traits_nlp_observer_service import TraitsNlpObserverService  # noqa: E402


async def _run() -> int:
    assert len(CALIBRATION_SAMPLES) >= 5, "need at least 5 calibration samples"
    result = await TraitsNlpObserverService(db=None).validate_bias_calibration()  # type: ignore[arg-type]
    if not result["passed"]:
        raise AssertionError(f"bias calibration failed: {result}")
    print(f"Bias calibration check passed: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
