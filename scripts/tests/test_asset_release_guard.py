"""V4-S04 资产许可账本发布面守卫的单元测试（可失败反例钉死）。"""
from __future__ import annotations

import importlib.util
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def load_guard(name: str):
    path = SCRIPTS_DIR / "guards" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_png(path: Path, width: int, height: int) -> None:
    row = b"\x00" + b"\xff\x00\x00\xff" * width
    raw = row * height

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def sha256_of(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_entry(root: Path, rel_path: str, *, status: str = "APPROVED",
               ship: bool = True, kind: str = "image",
               dpr_policy: str = "full_resolution",
               consumers: list[str] | None = None,
               license_id: str = "internal_original",
               extra: dict | None = None) -> dict:
    path = root / rel_path
    entry: dict = {
        "asset_id": Path(rel_path).relative_to("mobile/assets").as_posix()
        if rel_path.startswith("mobile/assets/")
        else rel_path,
        "path": rel_path,
        "kind": kind,
        "purpose": "test",
        "author": "Sparkle team",
        "source": "internal_original",
        "rights": {
            "license_id": license_id,
            "commercial_use": True,
            "redistribution": True,
            "modification": True,
            "attribution": "Sparkle team",
        },
        "version": "1.0.0",
        "sha256": sha256_of(path),
        "bytes": path.stat().st_size,
        "fallback": "silent",
        "status": status,
        "ship_in_product": ship,
        "dpr_policy": dpr_policy,
    }
    if consumers:
        entry["consumers"] = consumers
    if extra:
        entry.update(extra)
    return entry


class AssetReleaseSurfaceGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        # 夹具仓结构
        write_png(root / "mobile/assets/images/noise.png", 4, 4)
        write_png(root / "mobile/assets/placeholders/placeholder_pixel_block.png", 8, 8)
        write_png(root / "mobile/assets/placeholders/2.0x/placeholder_pixel_block.png", 16, 16)
        (root / "mobile/lib/core/assets").mkdir(parents=True, exist_ok=True)
        (root / "mobile/lib/core/assets/asset_catalog.dart").write_text(
            "// catalog\n'assets/placeholders/placeholder_pixel_block.png',\n",
            encoding="utf-8",
        )
        (root / "mobile/pubspec.yaml").write_text(
            "flutter:\n"
            "  assets:\n"
            "    - assets/images/\n"
            "    - assets/placeholders/\n",
            encoding="utf-8",
        )
        entries = [
            make_entry(root, "mobile/assets/images/noise.png", consumers=["mobile/lib/core/design/materials.dart"]),
            make_entry(root, "mobile/assets/placeholders/placeholder_pixel_block.png",
                       kind="placeholder_sprite", dpr_policy="nearest_neighbor_runtime",
                       consumers=["mobile/lib/core/assets/asset_catalog.dart"]),
            make_entry(root, "mobile/assets/placeholders/2.0x/placeholder_pixel_block.png",
                       kind="placeholder_sprite_variant", dpr_policy="native_multi_dpr",
                       extra={"dpr_variant_of": "placeholders/placeholder_pixel_block.png", "dpr_factor": 2.0}),
        ]
        (root / "mobile/assets/asset_ledger.json").write_text(
            json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8"
        )
        # 挂载守卫到夹具仓
        self.guard = load_guard("check_asset_release_surface")
        self.addCleanup(self._restore_guard)
        self._saved = {name: getattr(self.guard, name) for name in (
            "REPO_ROOT", "ASSETS_ROOT", "LEDGER_PATH", "PUBSPEC_PATH", "LIB_ROOT", "BGM_CATALOG")}
        self.guard.REPO_ROOT = root
        self.guard.ASSETS_ROOT = root / "mobile/assets"
        self.guard.LEDGER_PATH = root / "mobile/assets/asset_ledger.json"
        self.guard.PUBSPEC_PATH = root / "mobile/pubspec.yaml"
        self.guard.LIB_ROOT = root / "mobile/lib"
        self.guard.BGM_CATALOG = root / "mobile/assets/audio/bgm/bgm_catalog.json"
        self.root = root

    def _restore_guard(self) -> None:
        for name, value in self._saved.items():
            setattr(self.guard, name, value)

    def rewrite_ledger(self, entries: list[dict]) -> None:
        (self.root / "mobile/assets/asset_ledger.json").write_text(
            json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8"
        )

    def current_entries(self) -> list[dict]:
        return json.loads((self.root / "mobile/assets/asset_ledger.json").read_text())["entries"]

    def test_same_indent_list_items_still_parsed(self) -> None:
        """S04-R1 C1：同缩进 `- ` 列表项（合法 YAML 风格）必须仍被解析——
        否则该风格 pubspec 下 L003 面对 bundle 目录静默失明。删去
        in_list_block 的 `or stripped.startswith("- ")` 分支本测试红。"""
        (self.root / "mobile/pubspec.yaml").write_text(
            "flutter:\n"
            "  assets:\n"
            "  - assets/images/\n"
            "  - assets/placeholders/\n",
            encoding="utf-8",
        )
        dirs, fonts = self.guard.parse_pubspec_declared_dirs_and_fonts()
        self.assertEqual(dirs, ["assets/images/", "assets/placeholders/"])
        self.assertEqual(fonts, [])

    def test_green_fixture_has_no_violations(self) -> None:
        self.assertEqual(self.guard.scan(), [])

    def test_unledgered_file_in_bundle_dir_blocks_L003(self) -> None:
        (self.root / "mobile/assets/images/game_icon.png").write_bytes(b"unknown-license")
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L003") and "game_icon.png" in f for f in failures), failures)

    def test_proposed_status_on_release_surface_blocks_L004(self) -> None:
        write_png(self.root / "mobile/assets/images/suspect.png", 4, 4)
        entries = self.current_entries()
        entries.append(make_entry(self.root, "mobile/assets/images/suspect.png",
                                  status="PROPOSED", ship=False,
                                  license_id="unknown"))
        self.rewrite_ledger(entries)
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L004") and "suspect.png" in f for f in failures), failures)

    def test_hash_drift_blocks_L002(self) -> None:
        with (self.root / "mobile/assets/images/noise.png").open("ab") as handle:
            handle.write(b"tampered")
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L002") and "noise.png" in f for f in failures), failures)

    def test_unknown_font_file_blocks_L005(self) -> None:
        (self.root / "mobile/assets/fonts").mkdir(parents=True, exist_ok=True)
        (self.root / "mobile/assets/fonts/MysteryFont.ttf").write_bytes(b"ttf")
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L005") and "MysteryFont.ttf" in f for f in failures), failures)

    def test_bgm_catalog_release_approved_pointing_to_proposed_blocks_L006(self) -> None:
        catalog_dir = self.root / "mobile/assets/audio/bgm/curated"
        catalog_dir.mkdir(parents=True, exist_ok=True)
        write_png(catalog_dir / "commercial.m4a", 2, 2)  # 任意字节
        entries = self.current_entries()
        entries.append(make_entry(self.root, "mobile/assets/audio/bgm/curated/commercial.m4a",
                                  status="PROPOSED", ship=False, kind="bgm_track",
                                  dpr_policy="not_applicable_audio",
                                  license_id="unknown"))
        self.rewrite_ledger(entries)
        (self.root / "mobile/assets/audio/bgm/bgm_catalog.json").write_text(json.dumps({
            "entries": [{"id": "x", "assetPath": "audio/bgm/curated/commercial.m4a",
                         "releaseApproved": True}]
        }), encoding="utf-8")
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L006") for f in failures), failures)

    def test_hardcoded_reference_outside_catalog_and_consumers_blocks_L008(self) -> None:
        (self.root / "mobile/lib/core/design").mkdir(parents=True, exist_ok=True)
        (self.root / "mobile/lib/core/design/materials.dart").write_text(
            "// consumer\n'assets/placeholders/placeholder_pixel_block.png',\n",
            encoding="utf-8",
        )
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L008") and "materials.dart" in f for f in failures), failures)

    def test_dart_reference_to_unledgered_path_blocks_L007(self) -> None:
        (self.root / "mobile/lib/core/design").mkdir(parents=True, exist_ok=True)
        (self.root / "mobile/lib/core/design/rogue.dart").write_text(
            "// rogue\n'assets/images/ghost.png',\n", encoding="utf-8"
        )
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L007") and "ghost.png" in f for f in failures), failures)

    def test_missing_ledger_blocks_L000(self) -> None:
        (self.root / "mobile/assets/asset_ledger.json").unlink()
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("L000") for f in failures), failures)


if __name__ == "__main__":
    unittest.main()
