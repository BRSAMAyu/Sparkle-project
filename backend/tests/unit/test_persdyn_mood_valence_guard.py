from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _violates_single_factor_mood_guard(source: str) -> bool:
    tree = ast.parse(source)
    other_dims = {"study_pace", "completion_rate", "engagement_level", "plan_adherence"}
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            strings = {
                child.value
                for child in ast.walk(node)
                if isinstance(child, ast.Constant) and isinstance(child.value, str)
            }
            if "mood_valence" in strings and not (strings & other_dims):
                return True
    return False


def test_persdyn_mood_valence_guard_script_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "stage32" / "check_sqam_persdyn_sm1_mood.py"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_persdyn_mood_valence_guard_flags_single_factor_branch() -> None:
    source = """
if profile.get("mood_valence", 0) < 0.2:
    return "escalate"
"""

    assert _violates_single_factor_mood_guard(source) is True
