"""SIDECAR-JOURNEY · 旅程层 pytest 包装：把 sidecar_journey 纳入回归可跑集合。

脚本本体：tests/northstar_eval/sidecar_journey.py（引擎直调 + 全桩化，无 .env / 无真实 LLM）。
真实 LLM 冒烟不在此覆盖（诚实边界见 sidecar_journey.MOCK_BOUNDARIES 与本卡 REPORT）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.northstar_eval.sidecar_journey import MOCK_BOUNDARIES, run_journey


@pytest.mark.asyncio
async def test_sidecar_journey_three_turn_path_passes(tmp_path: Path) -> None:
    summary = await run_journey(out_dir=tmp_path)

    assert summary["verdict"] == "pass", summary["steps"]
    # 任务卡三条断言点（旅程层逐一就地断言后在此复钉）
    assert summary["assertion_points"] == {
        "A1_no_reopening_on_second_turn": True,
        "A2_sidecar_mounted_exactly_once": True,
        "A3_return_question_answered_and_session_continued": True,
    }
    # 证据结构契约：三轮齐备且各自 pass，诚实边界随证据落盘
    step_ids = [step["step_id"] for step in summary["steps"]]
    assert step_ids == ["T1", "T2", "T3"]
    assert all(step["verdict"] == "pass" for step in summary["steps"])
    assert summary["mock_boundaries"] == list(MOCK_BOUNDARIES)
    assert (tmp_path / "evidence.json").exists()
