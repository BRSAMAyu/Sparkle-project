#!/usr/bin/env python3
"""Unit tests for the UX component-convention ratchet guard (U-01).

Run:  python3 -m unittest scripts.tests.test_ux_component_convention -v
(or directly: python3 scripts/tests/test_ux_component_convention.py)
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().parents[1] / "guards" / "check_ux_component_convention.py"
_spec = importlib.util.spec_from_file_location("ux_component_convention", GUARD_PATH)
guard = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("ux_component_convention", guard)
_spec.loader.exec_module(guard)


class CodeLineFilterTest(unittest.TestCase):
    def test_comments_do_not_count(self):
        text = "\n".join(
            [
                "// ElevatedButton( in a comment",
                "/* TextButton( block",
                " * FilledButton( javadoc",
                "final w = ElevatedButton(onPressed: null, child: null);",
            ]
        )
        counts = guard.count_file_lines_text(text)
        self.assertEqual(counts["rawButton"], 1)

    def test_token_style_fontsize_not_matched_but_literal_is(self):
        text = "fontSize: DS.fontSizeSm, // fine\nfontSize: 13,\n"
        # fontSize ratchet lives in the other guard; here colorLiteral matters.
        self.assertEqual(guard.count_file_lines_text(text)["colorLiteral"], 0)

    def test_color_literal_counted(self):
        # Note: inline (trailing) comments stay on their code line and count,
        # mirroring check_ui_design_tokens_ratchet.py; only full comment lines
        # are skipped.
        text = "static const c = Color(0xFF123456);\n// Color(0xFFFFFFFF in comment"
        self.assertEqual(guard.count_file_lines_text(text)["colorLiteral"], 1)


class PatternTest(unittest.TestCase):
    def test_raw_button_variants(self):
        text = "\n".join(
            [
                "ElevatedButton(onPressed: f, child: a),",
                "FilledButton(onPressed: f),",
                "OutlinedButton(onPressed: f),",
                "TextButton(onPressed: f),",
                "SparkleButton(label: 'x'),",  # owner — not counted
                "IconButton(icon: i),",  # E3-allowed — not counted
            ]
        )
        self.assertEqual(guard.count_file_lines_text(text)["rawButton"], 4)

    def test_parallel_class_detection(self):
        text = "\n".join(
            [
                "class _StatusPill extends StatelessWidget {",
                "class _MemoryPanelLoadingSkeleton extends StatefulWidget {",
                "class GalaxyErrorDialog extends StatelessWidget {",
                "class _Helper extends StatelessWidget {",  # not chip/pill family
                "class ChatBubble extends StatefulWidget {",  # no family keyword match (Bubble not in list)
            ]
        )
        self.assertEqual(guard.count_file_lines_text(text)["parallelClass"], 3)

    def test_chip_variants_and_owner(self):
        text = "\n".join(
            [
                "FilterChip(selected: s, onSelected: f),",
                "ChoiceChip(label: l),",
                "RawChip(label: l),",
                "SemanticPill(label: l),",  # owner
                "TaskPill(label: l),",  # owner
            ]
        )
        self.assertEqual(guard.count_file_lines_text(text)["rawChip"], 3)


class RatchetDiffTest(unittest.TestCase):
    def test_new_file_violates(self):
        baseline: dict = {}
        current = {"a.dart": {"rawButton": 1, "rawSpinner": 0, "rawChip": 0, "parallelClass": 0, "colorLiteral": 0}}
        violations = _diff(baseline, current)
        self.assertEqual(len(violations), 1)
        self.assertIn("NEW FILE", violations[0])

    def test_count_increase_violates_and_decrease_passes(self):
        baseline = {"a.dart": {"rawButton": 2, "rawSpinner": 1, "rawChip": 0, "parallelClass": 0, "colorLiteral": 0}}
        raised = {"a.dart": {"rawButton": 3, "rawSpinner": 1, "rawChip": 0, "parallelClass": 0, "colorLiteral": 0}}
        lowered = {"a.dart": {"rawButton": 1, "rawSpinner": 0, "rawChip": 0, "parallelClass": 0, "colorLiteral": 0}}
        self.assertEqual(len(_diff(baseline, raised)), 1)
        self.assertEqual(_diff(baseline, lowered), [])


def _diff(baseline, current):
    """Mirror of main()'s violation diff, kept small for tests."""
    violations = []
    for rel, c in sorted(current.items()):
        b = baseline.get(rel)
        if b is None:
            violations.append(f"NEW FILE {rel}")
            continue
        for name in guard.PATTERNS:
            if c.get(name, 0) > b.get(name, 0):
                violations.append(f"{rel}: {name} raised")
    return violations


class BaselineFileTest(unittest.TestCase):
    def test_baseline_json_matches_schema(self):
        data = json.loads(guard.BASELINE_PATH.read_text(encoding="utf-8"))
        self.assertIn("comment", data)
        self.assertIn("files", data)
        for rel, counts in data["files"].items():
            self.assertTrue(rel.startswith("mobile/lib/"), rel)
            self.assertTrue(set(counts) <= set(guard.PATTERNS), rel)

    def test_scan_roots_exist(self):
        for rel in guard.SCAN_ROOTS:
            self.assertTrue((guard.MOBILE_LIB / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
