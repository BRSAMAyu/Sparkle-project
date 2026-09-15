from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from check_rule_y_inferred_extraction import check_rule_y


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_rule_y_passes_when_write_lane_validates_and_no_other_direct_writes(tmp_path) -> None:
    target = _write(
        tmp_path / "backend/app/services/memory_inferred_write_lane.py",
        "async def write_candidate_to_l1(candidate):\n"
        "    validated = RuleYAdapter.validate(candidate)\n"
        "    if validated is None:\n"
        "        return None\n"
        "    return memory_service.create_episodic_memory(source_lane=SOURCE_LANE)\n",
    )
    _write(tmp_path / "backend/app/services/other.py", "value = 1\n")
    assert check_rule_y(target=target, app_root=tmp_path / "backend/app") == []


def test_rule_y_fails_when_write_lane_skips_validation(tmp_path) -> None:
    target = _write(
        tmp_path / "backend/app/services/memory_inferred_write_lane.py",
        "async def write_candidate_to_l1(candidate):\n"
        "    return memory_service.create_episodic_memory(source_lane=SOURCE_LANE)\n",
    )
    violations = check_rule_y(target=target, app_root=tmp_path / "backend/app")
    assert "RY002" in violations[0]


def test_rule_y_fails_when_other_files_write_inferred_lane_directly(tmp_path) -> None:
    target = _write(
        tmp_path / "backend/app/services/memory_inferred_write_lane.py",
        "async def write_candidate_to_l1(candidate):\n"
        "    validated = RuleYAdapter.validate(candidate)\n"
        "    return memory_service.create_episodic_memory(source_lane=SOURCE_LANE)\n",
    )
    _write(
        tmp_path / "backend/app/services/bad.py",
        "def direct_write():\n"
        "    return memory_service.create_episodic_memory(source_lane='inferred_extraction')\n",
    )
    violations = check_rule_y(target=target, app_root=tmp_path / "backend/app")
    assert any(item.startswith("RY003") for item in violations)


def test_rule_y_allows_target_file_to_hold_the_single_direct_write_site(tmp_path) -> None:
    target = _write(
        tmp_path / "backend/app/services/memory_inferred_write_lane.py",
        "async def write_candidate_to_l1(candidate):\n"
        "    validated = RuleYAdapter.validate(candidate)\n"
        "    if validated is None:\n"
        "        return None\n"
        "    return memory_service.create_episodic_memory(source_lane='inferred_extraction')\n",
    )
    assert check_rule_y(target=target, app_root=tmp_path / "backend/app") == []
