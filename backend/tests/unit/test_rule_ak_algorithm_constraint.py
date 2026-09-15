from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.stage26.check_rule_ak_algorithm_constraint import scan_for_rule_ak_violations


def test_rule_ak_guard_detects_kmeans_usage() -> None:
    violations = scan_for_rule_ak_violations("from sklearn.cluster import KMeans\n")
    assert violations


def test_rule_ak_guard_detects_specify_k_usage() -> None:
    violations = scan_for_rule_ak_violations("algorithm = 'specify_k'\n")
    assert violations


def test_rule_ak_guard_accepts_scene_service_source() -> None:
    source = (REPO_ROOT / "backend" / "app" / "services" / "scene_consolidation_service.py").read_text(encoding="utf-8")
    violations = scan_for_rule_ak_violations(source)

    assert violations == []
