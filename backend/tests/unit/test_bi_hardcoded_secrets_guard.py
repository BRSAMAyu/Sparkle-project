"""Regression test for ISSUE-20260503-0432-L3: BI hardcoded secrets guard
must be registered in manifest, executable, catch real secrets, and avoid
false positives.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GUARD_SCRIPT = REPO_ROOT / "scripts" / "guards" / "check_rule_bi_hardcoded_secrets.py"
MANIFEST = REPO_ROOT / "scripts" / "rule_guard_manifest.tsv"


class TestBIHardcodedSecretsGuard:

    def test_bi_entry_in_manifest(self):
        """Manifest must contain BI rule entry."""
        content = MANIFEST.read_text()
        assert "\nBI\t" in content, \
            f"BI entry not found in manifest"

    def test_bi_script_exists_and_executable(self):
        """Guard script must exist."""
        assert GUARD_SCRIPT.exists(), f"Guard script missing: {GUARD_SCRIPT}"

    def test_bi_script_syntax_valid(self):
        """Guard script must have valid Python syntax."""
        result = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile(r'{GUARD_SCRIPT}', doraise=True)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_bi_pass_on_clean_codebase(self):
        """BI guard must pass (exit 0) on the current clean codebase."""
        result = subprocess.run(
            [sys.executable, str(GUARD_SCRIPT)],
            capture_output=True, text=True,
            env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
        )
        assert result.returncode == 0, f"BI guard failed on clean codebase:\n{result.stdout}"

    def test_bi_detects_openai_key(self):
        """BI guard must detect a hardcoded OpenAI API key."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=REPO_ROOT / "backend" / "app", delete=False
        ) as f:
            f.write('api_key = "sk-proj-1234567890abcdef1234567890abcdef"\n')
            tmp_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(GUARD_SCRIPT)],
                capture_output=True, text=True,
                env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
            )
            assert result.returncode == 1, "BI guard should exit 1 on detected secret"
            assert "OpenAI API key" in result.stdout
        finally:
            os.unlink(tmp_path)

    def test_bi_detects_github_token(self):
        """BI guard must detect a hardcoded GitHub token."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=REPO_ROOT / "backend" / "app", delete=False
        ) as f:
            f.write('GITHUB_TOKEN = "ghp_1234567890abcdef1234567890abcdef12345678"\n')
            tmp_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(GUARD_SCRIPT)],
                capture_output=True, text=True,
                env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
            )
            assert result.returncode == 1, "BI guard should exit 1 on GitHub token"
            assert "GitHub" in result.stdout
        finally:
            os.unlink(tmp_path)

    def test_bi_detects_hardcoded_password(self):
        """BI guard must detect a hardcoded password assignment."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=REPO_ROOT / "backend" / "app", delete=False
        ) as f:
            f.write('password = "super_secret_production_password"\n')
            tmp_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(GUARD_SCRIPT)],
                capture_output=True, text=True,
                env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
            )
            assert result.returncode == 1
            assert "password" in result.stdout.lower()
        finally:
            os.unlink(tmp_path)

    def test_bi_skips_safe_placeholders(self):
        """BI guard must not flag known safe placeholder values."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=REPO_ROOT / "backend" / "app", delete=False
        ) as f:
            f.write('API_KEY = "your_api_key_here"\n')
            f.write('PASSWORD = "changeme"\n')
            f.write('token = "demo_token"\n')
            f.write('SECRET = ""\n')
            tmp_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(GUARD_SCRIPT)],
                capture_output=True, text=True,
                env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
            )
            assert result.returncode == 0, \
                f"BI guard should pass on safe placeholders, got:\n{result.stdout}"
        finally:
            os.unlink(tmp_path)

    def test_bi_skips_type_annotations(self):
        """BI guard must skip type annotations like `password: str = ""`."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=REPO_ROOT / "backend" / "app", delete=False
        ) as f:
            f.write('password: str = ""\n')
            f.write('token: String = ""\n')
            f.write('class Foo:\n')
            f.write('    api_key: str = ""\n')
            tmp_path = f.name
        try:
            result = subprocess.run(
                [sys.executable, str(GUARD_SCRIPT)],
                capture_output=True, text=True,
                env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
            )
            assert result.returncode == 0, \
                f"BI guard should skip type annotations, got:\n{result.stdout}"
        finally:
            os.unlink(tmp_path)
