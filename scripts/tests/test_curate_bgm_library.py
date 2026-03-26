from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "curate_bgm_library.py"
SPEC = importlib.util.spec_from_file_location("curate_bgm_library", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CurateBgmLibraryTests(unittest.TestCase):
    def test_ignores_hidden_and_sidecar_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            album_root = Path(temp_dir) / "Album A"
            album_root.mkdir(parents=True)
            (album_root / "01 Track.m4a").write_bytes(b"audio")
            (album_root / "._01 Track.m4a").write_bytes(b"junk")
            (album_root / ".DS_Store").write_text("junk", encoding="utf-8")

            rule = MODULE.AlbumRule(
                name="Album A",
                scene_tags=("dashboard",),
                palette_tags=("adaptive",),
                energy=0.3,
                density=0.2,
                base_gain=0.9,
                loopable=True,
                release_approved=False,
            )
            discovered = MODULE.discover_audio_files(Path(temp_dir), [rule])

            self.assertEqual(len(discovered[rule]), 1)
            self.assertEqual(discovered[rule][0].name, "01 Track.m4a")

    def test_whitelist_only_returns_requested_albums(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            requested = Path(temp_dir) / "Requested"
            requested.mkdir(parents=True)
            ignored = Path(temp_dir) / "Ignored"
            ignored.mkdir(parents=True)
            (requested / "keep.m4a").write_bytes(b"ok")
            (ignored / "skip.m4a").write_bytes(b"skip")

            rule = MODULE.AlbumRule(
                name="Requested",
                scene_tags=("chat",),
                palette_tags=("adaptive",),
                energy=0.2,
                density=0.2,
                base_gain=0.9,
                loopable=False,
                release_approved=True,
            )
            discovered = MODULE.discover_audio_files(Path(temp_dir), [rule])

            self.assertEqual([path.name for path in discovered[rule]], ["keep.m4a"])

    def test_build_catalog_entries_preserves_release_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "Album B" / "song.m4a"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"audio")
            rule = MODULE.AlbumRule(
                name="Album B",
                scene_tags=("focus", "minimal"),
                palette_tags=("airy",),
                energy=0.1,
                density=0.1,
                base_gain=0.88,
                loopable=True,
                release_approved=True,
            )
            catalog = MODULE.build_catalog_entries({rule: [source]})

            self.assertEqual(len(catalog), 1)
            entry = catalog[0]
            self.assertEqual(entry["album"], "Album B")
            self.assertEqual(entry["sceneTags"], ["focus", "minimal"])
            self.assertEqual(entry["paletteTags"], ["airy"])
            self.assertTrue(entry["releaseApproved"])
            self.assertTrue(str(entry["assetPath"]).startswith("audio/bgm/curated/"))

    def test_write_catalog_drops_internal_source_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "bgm_catalog.json"
            MODULE.write_catalog(
                [
                    {
                        "id": "sample_track",
                        "assetPath": "audio/bgm/curated/sample_track.m4a",
                        "album": "Album C",
                        "sceneTags": ["dashboard"],
                        "paletteTags": ["adaptive"],
                        "energy": 0.3,
                        "density": 0.2,
                        "baseGain": 0.9,
                        "loopable": False,
                        "releaseApproved": False,
                        "_sourcePath": "/tmp/source.m4a",
                        "_outputFileName": "sample_track.m4a",
                    }
                ],
                out_path,
            )

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["entries"]), 1)
            self.assertNotIn("_sourcePath", payload["entries"][0])
            self.assertFalse(payload["entries"][0]["releaseApproved"])


if __name__ == "__main__":
    unittest.main()
