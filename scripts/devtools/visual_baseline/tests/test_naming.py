"""naming.py 单测：canonical 截图命名规范。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from visual_baseline.naming import (  # noqa: E402
    NamingError,
    build_sha8,
    parse_filename,
    screenshot_name,
)


NAME = "home__main__demo_data__android__412x916@2.6__aced25a2.png"


class TestScreenshotName:
    def test_canonical_roundtrip(self):
        fields = parse_filename(NAME)
        assert fields == {
            "surface": "home",
            "state": "main",
            "persona": "demo_data",
            "platform": "android",
            "viewport": "412x916@2.6",
            "sha8": "aced25a2",
        }

    def test_make_and_parse_roundtrip(self):
        name = screenshot_name("galaxy", "tree_expanded", "demo_data", "web", "1440x900@2.0", "01234567")
        assert parse_filename(name)["surface"] == "galaxy"
        assert name.endswith(".png")

    def test_viewport_without_density_allowed(self):
        name = screenshot_name("home", "main", "guest", "ios", "412x916", "ffffffff")
        assert parse_filename(name)["viewport"] == "412x916"

    def test_rejects_unknown_surface(self):
        with pytest.raises(NamingError):
            screenshot_name("dashboard", "main", "demo_data", "android", "412x916@2.6", "aced25a2")

    def test_rejects_unknown_persona(self):
        with pytest.raises(NamingError):
            screenshot_name("home", "main", "admin", "android", "412x916@2.6", "aced25a2")

    def test_rejects_unknown_platform(self):
        with pytest.raises(NamingError):
            screenshot_name("home", "main", "demo_data", "linux", "412x916@2.6", "aced25a2")

    def test_rejects_uppercase_state(self):
        with pytest.raises(NamingError):
            screenshot_name("home", "Main", "demo_data", "android", "412x916@2.6", "aced25a2")

    def test_rejects_segment_with_double_underscore(self):
        with pytest.raises(NamingError):
            screenshot_name("home", "ma__in", "demo_data", "android", "412x916@2.6", "aced25a2")

    def test_rejects_segment_leading_underscore(self):
        with pytest.raises(NamingError):
            screenshot_name("home", "_main", "demo_data", "android", "412x916@2.6", "aced25a2")

    def test_rejects_bad_sha8(self):
        with pytest.raises(NamingError):
            screenshot_name("home", "main", "demo_data", "android", "412x916@2.6", "XYZ")

    def test_rejects_bad_viewport(self):
        with pytest.raises(NamingError):
            screenshot_name("home", "main", "demo_data", "android", "412-by-916", "aced25a2")

    def test_rejects_non_png(self):
        with pytest.raises(NamingError):
            parse_filename("home__main__demo_data__android__412x916@2.6__aced25a2.jpg")

    def test_rejects_wrong_part_count(self):
        with pytest.raises(NamingError):
            parse_filename("home__main__demo_data__android__aced25a2.png")


class TestBuildSha8:
    def test_takes_first_eight(self):
        assert build_sha8("aced25a2" + "0" * 32) == "aced25a2"

    def test_uppercase_normalized(self):
        assert build_sha8("ACED25A2FF") == "aced25a2"

    def test_rejects_garbage(self):
        with pytest.raises(NamingError):
            build_sha8("not-a-sha")
