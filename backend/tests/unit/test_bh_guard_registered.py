"""Regression test for ISSUE-20260503-0432-L1: BH meta-learning safety guard
must be registered in rule_guard_manifest.tsv so it runs in CI.
"""

import os
import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MANIFEST_PATH = os.path.join(REPO_ROOT, "scripts", "rule_guard_manifest.tsv")
BH_SCRIPT_REL = "scripts/guards/check_rule_bh_meta_learning_safety.py"


class TestBHGuardRegisteredInManifest:

    def test_bh_entry_exists_in_manifest(self):
        """BH must be listed in the manifest (was the missing entry)."""
        with open(MANIFEST_PATH) as f:
            lines = f.readlines()

        bh_entries = [line for line in lines if line.startswith("BH\t")]
        assert len(bh_entries) == 1, (
            f"Expected exactly 1 BH entry in manifest, found {len(bh_entries)}"
        )

    def test_bh_command_points_to_correct_script(self):
        """BH entry must reference the correct guard script."""
        with open(MANIFEST_PATH) as f:
            lines = f.readlines()

        bh_entries = [line for line in lines if line.startswith("BH\t")]
        assert bh_entries, "BH entry not found in manifest"

        command = bh_entries[0].split("\t", 1)[1].strip()
        assert BH_SCRIPT_REL in command, (
            f"BH command does not reference {BH_SCRIPT_REL}: {command}"
        )

    def test_bh_guard_script_exists(self):
        """The BH guard script must exist on disk."""
        script_path = os.path.join(REPO_ROOT, BH_SCRIPT_REL)
        assert os.path.isfile(script_path), f"BH script not found: {script_path}"

    def test_bh_guard_script_returns_zero(self):
        """The BH guard script must execute successfully (exit code 0)."""
        import subprocess
        script_path = os.path.join(REPO_ROOT, BH_SCRIPT_REL)
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"BH guard script exited with {result.returncode}: {result.stderr}"
        )
        assert "PASS" in result.stdout
