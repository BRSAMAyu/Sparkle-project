from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "check_coverage_thresholds.py"
SPEC = importlib.util.spec_from_file_location("check_coverage_thresholds", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_compute_scope_coverage_matches_suffix_paths():
    file_counters = {
        "Users/runner/work/Sparkle-project/backend/app/orchestration/orchestrator.py": (30, 60),
        "backend/app/core/llm_router.py": (20, 40),
    }

    value = MODULE.compute_scope_coverage(file_counters, "backend/app/orchestration")

    assert value == 50.0


def test_parse_go_coverprofile_scopes_counts_statement_hits(tmp_path):
    coverprofile = tmp_path / "coverage.out"
    coverprofile.write_text(
        "mode: set\n"
        "backend/gateway/internal/handler/chat.go:10.1,12.2 2 1\n"
        "backend/gateway/internal/handler/chat.go:14.1,18.2 3 0\n",
        encoding="utf-8",
    )

    counters = MODULE.parse_go_coverprofile_scopes(coverprofile)

    assert counters["backend/gateway/internal/handler/chat.go"] == (2, 5)


def test_parse_python_xml_scopes_aggregates_line_hits(tmp_path):
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(
        """<?xml version="1.0" ?>
<coverage line-rate="0.5">
  <packages>
    <package name="app.orchestration" line-rate="0.5">
      <classes>
        <class name="orchestrator.py" filename="backend/app/orchestration/orchestrator.py" line-rate="0.5">
          <lines>
            <line number="10" hits="1"/>
            <line number="11" hits="0"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
""",
        encoding="utf-8",
    )

    counters = MODULE.parse_python_xml_scopes(coverage_xml)

    assert counters["backend/app/orchestration/orchestrator.py"] == (1, 2)


def test_parse_lcov_scopes_reads_file_sections(tmp_path):
    lcov = tmp_path / "lcov.info"
    lcov.write_text(
        "TN:\n"
        "SF:/workspace/mobile/lib/features/chat/chat_screen.dart\n"
        "LF:10\n"
        "LH:6\n"
        "end_of_record\n",
        encoding="utf-8",
    )

    counters = MODULE.parse_lcov_scopes(lcov)

    assert counters["workspace/mobile/lib/features/chat/chat_screen.dart"] == (6, 10)
