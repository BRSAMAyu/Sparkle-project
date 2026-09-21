"""diffing.py 单测：纯 stdlib PNG 解码/指纹/轻量 diff。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from visual_baseline.diffing import (  # noqa: E402
    PngUnsupportedError,
    compare,
    decode_png_gray,
    diff_manifests,
    fingerprint,
    fingerprint_distance,
)
from visual_baseline.naming import screenshot_name  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _png_factory import make_png, solid, vertical_gradient  # noqa: E402


class TestDecode:
    def test_solid_gray_decode(self, tmp_path: Path):
        p = tmp_path / "s.png"
        make_png(p, 4, 4, solid(4, 4, 100))
        w, h, gray = decode_png_gray(p)
        assert (w, h) == (4, 4)
        assert gray == [100] * 16

    def test_rejects_garbage(self, tmp_path: Path):
        p = tmp_path / "x.png"
        p.write_bytes(b"not a png at all")
        with pytest.raises(PngUnsupportedError):
            decode_png_gray(p)


class TestFingerprint:
    def test_identical_images_zero_distance(self, tmp_path: Path):
        a, b = tmp_path / "a.png", tmp_path / "b.png"
        make_png(a, 32, 32, vertical_gradient(32, 32, 10, 200))
        make_png(b, 32, 32, vertical_gradient(32, 32, 10, 200))
        fp = fingerprint(a)
        assert fp is not None
        assert fingerprint_distance(fp, fingerprint(b)) == pytest.approx(0.0, abs=1e-9)

    def test_similar_images_small_distance(self, tmp_path: Path):
        a, b = tmp_path / "a.png", tmp_path / "b.png"
        make_png(a, 32, 32, vertical_gradient(32, 32, 10, 200))
        make_png(b, 32, 32, vertical_gradient(32, 32, 20, 210))  # 轻微提亮
        assert fingerprint_distance(fingerprint(a), fingerprint(b)) < 0.08

    def test_different_images_large_distance(self, tmp_path: Path):
        a, b = tmp_path / "a.png", tmp_path / "b.png"
        make_png(a, 32, 32, vertical_gradient(32, 32, 0, 255))
        make_png(b, 32, 32, vertical_gradient(32, 32, 255, 0))  # 反相
        assert fingerprint_distance(fingerprint(a), fingerprint(b)) > 0.3


class TestCompare:
    def test_identical_bytes_verdict(self, tmp_path: Path):
        a, b = tmp_path / "a.png", tmp_path / "b.png"
        make_png(a, 16, 16, solid(16, 16, 99))
        b.write_bytes(a.read_bytes())
        r = compare(a, b)
        assert r["verdict"] == "identical"
        assert r["same_bytes"] is True

    def test_similar_verdict(self, tmp_path: Path):
        a, b = tmp_path / "a.png", tmp_path / "b.png"
        make_png(a, 32, 32, vertical_gradient(32, 32, 10, 200))
        make_png(b, 32, 32, vertical_gradient(32, 32, 18, 208))
        r = compare(a, b)
        assert r["verdict"] == "similar"

    def test_different_verdict(self, tmp_path: Path):
        a, b = tmp_path / "a.png", tmp_path / "b.png"
        make_png(a, 32, 32, vertical_gradient(32, 32, 0, 255))
        make_png(b, 32, 32, vertical_gradient(32, 32, 255, 0))
        r = compare(a, b)
        assert r["verdict"] == "different"

    def test_unsupported_png_falls_back_to_metadata(self, tmp_path: Path):
        a, b = tmp_path / "a.png", tmp_path / "b.png"
        make_png(a, 16, 16, solid(16, 16, 99))
        b.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)  # 签名对内容坏
        r = compare(a, b)
        assert r["verdict"] == "unknown"
        assert r["fingerprint"] == "unavailable"


class TestDiffManifests:
    @staticmethod
    def _manifest(tmp_path: Path, sha8: str, content_byte: int, extra_entry=None):
        from visual_baseline.manifest import build_manifest

        d = tmp_path / f"s_{sha8}_{content_byte}"
        d.mkdir()
        name = screenshot_name("home", "main", "demo_data", "android", "412x916@2.6", sha8)
        make_png(d / name, 16, 16, solid(16, 16, content_byte))
        m = build_manifest(d, sha8 + "0" * 32, "android", "412x916@2.6")
        if extra_entry:
            m["entries"].append(extra_entry)
        return m

    def test_alignment_ignores_sha8_and_reports_change(self, tmp_path: Path):
        old = self._manifest(tmp_path, "aaaaaaaa", 50)
        new = self._manifest(tmp_path, "bbbbbbbb", 99)  # 同状态、新构建、内容变了
        report = diff_manifests(old, new)
        assert report["changed"] == ["home__main__demo_data__android__412x916@2.6"]
        assert report["added"] == [] and report["removed"] == []

    def test_added_and_removed(self, tmp_path: Path):
        from visual_baseline.naming import screenshot_name as n

        old = self._manifest(tmp_path, "aaaaaaaa", 50)
        extra = {
            "surface": "chat",
            "state": "history_citations",
            "persona": "demo_data",
            "platform": "android",
            "viewport": "412x916@2.6",
            "sha8": "bbbbbbbb",
            "path": n("chat", "history_citations", "demo_data", "android", "412x916@2.6", "bbbbbbbb"),
            "sha256": "0" * 64,
        }
        new = self._manifest(tmp_path, "bbbbbbbb", 50, extra_entry=extra)
        report = diff_manifests(old, new)
        assert "chat__history_citations__demo_data__android__412x916@2.6" in report["added"]
        assert report["unchanged"] == ["home__main__demo_data__android__412x916@2.6"]
