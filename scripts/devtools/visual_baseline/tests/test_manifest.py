"""manifest.py 单测：manifest 生成/加载/校验。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from visual_baseline.manifest import (  # noqa: E402
    build_entry,
    build_manifest,
    load_manifest,
    sha256_file,
    validate_manifest_schema,
    verify_screens,
    write_manifest,
)
from visual_baseline.naming import screenshot_name  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _png_factory import make_png, solid  # noqa: E402


BUILD_SHA = "aced25a2" + "b" * 32
NAME_A = screenshot_name("home", "main", "demo_data", "android", "412x916@2.6", "aced25a2")
NAME_B = screenshot_name("galaxy", "tree_expanded", "demo_data", "android", "412x916@2.6", "aced25a2")


@pytest.fixture()
def screens(tmp_path: Path) -> Path:
    d = tmp_path / "screenshots"
    d.mkdir()
    make_png(d / NAME_A, 16, 16, solid(16, 16, 200))
    make_png(d / NAME_B, 16, 16, solid(16, 16, 30))
    return d


def test_build_entry_fields(screens: Path):
    entry = build_entry(screens / NAME_A, screens)
    assert entry["surface"] == "home"
    assert entry["state"] == "main"
    assert entry["persona"] == "demo_data"
    assert entry["platform"] == "android"
    assert entry["viewport"] == "412x916@2.6"
    assert entry["sha8"] == "aced25a2"
    assert entry["path"] == NAME_A
    assert entry["sha256"] == sha256_file(screens / NAME_A)
    assert entry["bytes"] > 0
    assert entry["captured_at"].endswith("Z")


def test_build_manifest_sorted_entries(screens: Path):
    m = build_manifest(screens, BUILD_SHA, "android", "412x916@2.6", model="AVD", gateway_url="http://g", engine_url="http://e")
    assert m["kind"] == "visual-baseline-manifest"
    assert m["schema_version"] == 1
    assert m["build_sha"] == BUILD_SHA
    assert m["device"] == {"platform": "android", "model": "AVD", "viewport": "412x916@2.6"}
    assert m["backend"]["gateway_url"] == "http://g"
    paths = [e["path"] for e in m["entries"]]
    assert paths == sorted(paths)
    assert len(m["entries"]) == 2


def test_write_and_load_roundtrip(screens: Path, tmp_path: Path):
    m = build_manifest(screens, BUILD_SHA, "android", "412x916@2.6")
    out = write_manifest(m, tmp_path / "manifest.json")
    loaded = load_manifest(out)
    assert loaded == m


def test_load_manifest_rejects_wrong_kind(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"kind": "other", "schema_version": 1}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(p)


def test_validate_rejects_entry_missing_keys():
    with pytest.raises(ValueError):
        validate_manifest_schema(
            {
                "kind": "visual-baseline-manifest",
                "schema_version": 1,
                "build_sha": BUILD_SHA,
                "generated_at": "2026-09-21T00:00:00Z",
                "device": {},
                "entries": [{"path": "x.png"}],
            }
        )


def test_verify_ok(screens: Path):
    m = build_manifest(screens, BUILD_SHA, "android", "412x916@2.6")
    report = verify_screens(screens, m)
    assert report["ok"] is True
    assert report["missing"] == [] and report["extra"] == [] and report["hash_mismatch"] == []


def test_verify_detects_missing(screens: Path):
    m = build_manifest(screens, BUILD_SHA, "android", "412x916@2.6")
    (screens / NAME_A).unlink()
    report = verify_screens(screens, m)
    assert report["ok"] is False
    assert report["missing"] == [NAME_A]


def test_verify_detects_extra_and_renamed(screens: Path):
    m = build_manifest(screens, BUILD_SHA, "android", "412x916@2.6")
    (screens / NAME_A).rename(screens / "renamed.png")
    report = verify_screens(screens, m)
    assert report["ok"] is False
    assert report["extra"] == ["renamed.png"]
    assert report["missing"] == [NAME_A]
    assert report["renamed"] == [f"{NAME_A} -> renamed.png"]


def test_verify_detects_tampered_content(screens: Path):
    m = build_manifest(screens, BUILD_SHA, "android", "412x916@2.6")
    make_png(screens / NAME_A, 16, 16, solid(16, 16, 1))  # 同名不同内容
    report = verify_screens(screens, m)
    assert report["ok"] is False
    assert report["hash_mismatch"] == [NAME_A]
