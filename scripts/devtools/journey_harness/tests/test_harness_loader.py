"""journey harness loader/render 单测（B-03 基线，纯静态、无活栈依赖）。

运行：
    pytest scripts/devtools/journey_harness/tests/test_harness_loader.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS_DIR))

from harness.loader import (  # noqa: E402
    JOURNEY_DIR,
    load_journey,
    load_persona_library,
    list_journeys,
    parse_journey,
)
from harness.runner import _render_args  # noqa: E402


def test_list_journeys_contains_baseline_set() -> None:
    names = set(list_journeys())
    assert {"GJ01", "GJ01S", "GJ04", "GJ08"} <= names


def test_gj01_persona_resolved_from_library() -> None:
    journey = load_journey("GJ01")
    # persona 统一（work#2）：声明即解析，manifest 可追溯
    assert journey.persona.get("id") == "P04"
    assert journey.persona.get("goal"), "persona 必须带 goal（persona_library 契约）"


def test_gj04_persona_p01() -> None:
    journey = load_journey("GJ04")
    assert journey.persona.get("id") == "P01"


def test_gj01s_shell_has_no_persona_semantics() -> None:
    journey = load_journey("GJ01S")
    assert journey.persona == {}


def test_unknown_persona_fails_at_load_time(tmp_path: Path) -> None:
    spec = {
        "id": "GJXX",
        "title": "t",
        "golden_ref": "g",
        "persona": "P999",
        "backends": {"api": [{"name": "s", "action": "api_register", "args": {}}]},
    }
    path = tmp_path / "GJXX_bad_persona.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="P999"):
        parse_journey(path)


def test_persona_library_missing_file_is_explicit_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_persona_library(tmp_path / "no_such_library.json")


def test_real_persona_library_shape() -> None:
    """真实 persona library（v3/05_metrics_eval/persona_library.json）契约钉。"""
    library = load_persona_library()
    assert len(library) >= 10
    for pid, persona in library.items():
        assert pid == persona.get("id")
        assert persona.get("name") and persona.get("goal"), f"persona {pid} 缺 name/goal"


def test_steps_for_unknown_backend_is_explicit_keyerror() -> None:
    journey = load_journey("GJ01S")
    with pytest.raises(KeyError):
        journey.steps_for("macos")  # GJ01S 未声明 macos backend


def test_journey_dir_is_repo_relative() -> None:
    assert (JOURNEY_DIR / "GJ01S_web_app_shell.json").exists()


def test_render_args_run_tokens() -> None:
    args = {
        "username": "jh_g01_%RUN%",
        "email": "jh_g01_%RUN%@sparkle-journey.example.com",
        "session": "g04_%RUN_ID%",
        "nested": ["a_%RUN%", {"b": "%RUN%"}],
        "untouched": 7,
    }
    # %RUN% = run_id 去掉分隔符后的末 12 位字母数字
    run_id = "gj01_api_20260927_101010_a1b2c3d4e5f6"
    out = _render_args(args, run_id)
    assert out["username"] == "jh_g01_a1b2c3d4e5f6"
    assert out["email"] == "jh_g01_a1b2c3d4e5f6@sparkle-journey.example.com"
    assert out["session"] == f"g04_{run_id}"
    assert out["nested"][0] == "a_a1b2c3d4e5f6"
    assert out["nested"][1] == {"b": "a1b2c3d4e5f6"}
    assert out["untouched"] == 7
    # 同一 run 内多次渲染结果一致（persona/账号隔离的确定性基础）
    assert _render_args(args, run_id) == out
