"""仿真/真实数据区分契约 + run 失败语义 单测（B-03 红线，静态可证部分）。

红线（本卡执行纪律）：模拟器产出的数据必须可区分于真实数据（schema/标记层面）。
真实驱动证据 schema 的权威在 backend/tests/northstar_eval/real_drive.py
（sparkle.northstar.real-drive.*.v1），本套测试读其源码字符串对账（不 import、
不触碰其运行态），确保 simulator schema 家族与 real-drive 家族永远互斥。

运行：
    pytest scripts/devtools/journey_harness/tests/test_harness_markers.py -q
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = HARNESS_DIR.parents[2]
sys.path.insert(0, str(HARNESS_DIR))

from harness.evidence import EvidenceCollector  # noqa: E402
from harness.models import (  # noqa: E402
    CLOCK_WALL,
    LANE_NONUI,
    LANE_UI,
    SIM_RUN_SCHEMA,
    SIM_STEP_SCHEMA,
    RunManifest,
)
from harness.runner import run_journey  # noqa: E402

REAL_DRIVE_PY = REPO_ROOT / "backend" / "tests" / "northstar_eval" / "real_drive.py"


def _make_manifest(backend: str = "web") -> RunManifest:
    return RunManifest(
        journey_id="GJ01",
        backend=backend,
        run_id="gj01_web_t",
        started_at="2026-09-27T00:00:00+00:00",
    )


def test_manifest_carries_simulator_schema_and_lane() -> None:
    payload = _make_manifest("web").to_dict()
    assert payload["schema"] == SIM_RUN_SCHEMA == "sparkle.journey.simulator.run.v1"
    assert payload["lane"] == LANE_UI
    assert payload["clock"] == CLOCK_WALL


def test_lane_marking_ui_vs_nonui() -> None:
    assert LANE_UI == "simulator-ui"
    assert LANE_NONUI == "simulator-nonui"
    # runner 对 api lane 的落点在 test_api_run_failure…（真实 run_journey 路径）里验证


def test_clock_ratchet_controlled_advance_unsupported() -> None:
    """受控时钟裁决钉：产品无时钟 seam（real_drive.py 时间语义裁决方案 c）。

    若有人要在 harness 里实现受控时钟推进，必须先推翻该裁决并改本测试——
    不允许静默引入伪造时间戳的"时钟"。
    """
    assert CLOCK_WALL["mode"] == "wall"
    assert CLOCK_WALL["controlled_advance"] == "unsupported"
    assert "clock seam" in CLOCK_WALL["reason"]


def test_simulator_schema_distinct_from_real_drive_schema() -> None:
    """对账 real_drive.py 源码里的权威 schema 字符串（只读，不 import）。"""
    if not REAL_DRIVE_PY.exists():
        pytest.skip(f"real_drive.py 不在本树: {REAL_DRIVE_PY}")
    text = REAL_DRIVE_PY.read_text(encoding="utf-8")
    real_step = re.search(r'SCHEMA_STEP\s*=\s*"([^"]+)"', text)
    real_run = re.search(r'SCHEMA_RUN\s*=\s*"([^"]+)"', text)
    assert real_step and real_run, "real_drive.py schema 常量形状变化，需人工对账"
    assert SIM_STEP_SCHEMA != real_step.group(1)
    assert SIM_RUN_SCHEMA != real_run.group(1)
    assert "simulator" in SIM_STEP_SCHEMA and "simulator" in SIM_RUN_SCHEMA
    assert "real-drive" in real_step.group(1)


def test_api_run_unreachable_gateway_is_honest_fail(tmp_path: Path) -> None:
    """「网关不可达」必须= FAIL 落盘，绝不 PASS（验收第 2 条；无需活栈）。"""
    manifest = run_journey(
        journey_id="GJ01",
        backend="api",
        evidence_root=tmp_path,
        driver_config={"gateway": "http://127.0.0.1:9"},  # discard 端口，连接拒绝
    )
    assert manifest.ok is False
    assert manifest.lane == LANE_NONUI
    assert manifest.schema == SIM_RUN_SCHEMA
    assert manifest.persona.get("id") == "P04"  # GJ01 persona 进 manifest
    start_fails = [s for s in manifest.steps if s.name == "driver_start" and not s.ok]
    assert start_fails, "driver.start 失败必须落 FAIL 步骤"
    # 全部产物落盘在 run 目录
    run_dir = tmp_path / manifest.run_id
    assert (run_dir / "run_manifest.json").exists()
    assert (run_dir / "steps.json").exists()
    assert (run_dir / "journey_definition.json").exists()


def test_steps_json_envelope_marks_simulator_schema(tmp_path: Path) -> None:
    manifest = _make_manifest()
    manifest.ok = False
    from harness.models import StepResult

    manifest.steps.append(StepResult(name="s1", action="sleep", ok=True, detail="d", duration_ms=1))
    evidence = EvidenceCollector(tmp_path, manifest.run_id)
    path = evidence.write_steps(manifest)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == SIM_STEP_SCHEMA
    assert payload["run_id"] == manifest.run_id
    assert payload["lane"] == manifest.lane
    assert payload["steps"][0]["name"] == "s1"


def test_cli_failure_exits_nonzero(tmp_path: Path) -> None:
    """端到端验收钉：失败 run 的进程退出码非零（run_journey.py CLI）。"""
    proc = subprocess.run(
        [
            sys.executable,
            str(HARNESS_DIR / "run_journey.py"),
            "--journey", "GJ01",
            "--backend", "api",
            "--gateway", "http://127.0.0.1:9",
            "--evidence-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0, f"失败 run 退出码必须非零，stdout={proc.stdout[-500:]}"
