from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import stage28.check_rule_am_confidence_cap as rule_am


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _validator_source() -> str:
    return """
from pydantic import BaseModel, field_validator

class BigFiveDimension(BaseModel):
    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value):
        numeric = float(value)
        if numeric < 0.0 or numeric > 0.3:
            raise ValueError("trait confidence must be within [0, 0.3]")
        return round(numeric, 4)
"""


def test_rule_am_passes_for_validator_and_safe_call_sites(tmp_path, monkeypatch) -> None:
    target = _write(tmp_path / "backend/app/core/user_insight_state.py", _validator_source())
    safe_call = _write(
        tmp_path / "backend/app/services/traits_service.py",
        "def build():\n    confidence = min(0.1, 0.05)\n    return BigFiveDimension(confidence=confidence)\n",
    )
    monkeypatch.setattr(rule_am, "TARGET", target)
    monkeypatch.setattr(rule_am, "SCAN_ROOTS", [tmp_path / "backend/app"])
    assert rule_am.check_rule_am() == []


def test_rule_am_fails_when_validator_is_missing(tmp_path, monkeypatch) -> None:
    target = _write(tmp_path / "backend/app/core/user_insight_state.py", "class BigFiveDimension: pass\n")
    _write(tmp_path / "backend/app/services/traits_service.py", "def build():\n    return BigFiveDimension(confidence=0.2)\n")
    monkeypatch.setattr(rule_am, "TARGET", target)
    monkeypatch.setattr(rule_am, "SCAN_ROOTS", [tmp_path / "backend/app"])
    violations = rule_am.check_rule_am()
    assert any(item.startswith("AM001") for item in violations)


def test_rule_am_fails_on_constant_confidence_above_cap(tmp_path, monkeypatch) -> None:
    target = _write(tmp_path / "backend/app/core/user_insight_state.py", _validator_source())
    _write(tmp_path / "backend/app/services/traits_service.py", "def build():\n    return BigFiveDimension(confidence=0.31)\n")
    monkeypatch.setattr(rule_am, "TARGET", target)
    monkeypatch.setattr(rule_am, "SCAN_ROOTS", [tmp_path / "backend/app"])
    violations = rule_am.check_rule_am()
    assert any(item.startswith("AM002") for item in violations)


def test_rule_am_fails_on_unbounded_dynamic_confidence_without_marker(tmp_path, monkeypatch) -> None:
    target = _write(tmp_path / "backend/app/core/user_insight_state.py", _validator_source())
    _write(
        tmp_path / "backend/app/services/traits_service.py",
        "def build(raw):\n    confidence = raw\n    return BigFiveDimension(confidence=confidence)\n",
    )
    monkeypatch.setattr(rule_am, "TARGET", target)
    monkeypatch.setattr(rule_am, "SCAN_ROOTS", [tmp_path / "backend/app"])
    violations = rule_am.check_rule_am()
    assert any(item.startswith("AM002") for item in violations)
