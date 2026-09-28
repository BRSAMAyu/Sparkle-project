"""V4-S04 像素资产 DPR/NN 策略守卫的单元测试（可失败反例钉死）。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from test_asset_release_guard import load_guard, make_entry, write_png


class PixelDprPolicyGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        write_png(self.root / "mobile/assets/placeholders/placeholder_pixel_block.png", 8, 8)
        write_png(self.root / "mobile/assets/placeholders/2.0x/placeholder_pixel_block.png", 16, 16)
        self.guard = load_guard("check_pixel_dpr_policy")
        self._saved = {name: getattr(self.guard, name) for name in (
            "REPO_ROOT", "ASSETS_ROOT", "LEDGER_PATH", "GENERATOR_PATH")}
        self.addCleanup(self._restore_guard)
        self.guard.REPO_ROOT = self.root
        self.guard.ASSETS_ROOT = self.root / "mobile/assets"
        self.guard.LEDGER_PATH = self.root / "mobile/assets/asset_ledger.json"
        self.guard.GENERATOR_PATH = self.root / "scripts/devtools/generate_placeholder_sprites.py"

    def _restore_guard(self) -> None:
        for name, value in self._saved.items():
            setattr(self.guard, name, value)

    def write_ledger(self, entries: list[dict]) -> None:
        (self.root / "mobile/assets/asset_ledger.json").write_text(
            json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8"
        )

    def base_entries(self) -> list[dict]:
        return [
            make_entry(self.root, "mobile/assets/placeholders/placeholder_pixel_block.png",
                       kind="placeholder_sprite", dpr_policy="nearest_neighbor_runtime",
                       consumers=["mobile/lib/core/assets/asset_catalog.dart"]),
            make_entry(self.root, "mobile/assets/placeholders/2.0x/placeholder_pixel_block.png",
                       kind="placeholder_sprite_variant", dpr_policy="native_multi_dpr",
                       extra={"dpr_variant_of": "placeholders/placeholder_pixel_block.png",
                              "dpr_factor": 2.0}),
        ]

    def consumer_file(self, *, with_nn: bool = True) -> None:
        target = self.root / "mobile/lib/core/assets/asset_catalog.dart"
        target.parent.mkdir(parents=True, exist_ok=True)
        body = "Image.asset(path, filterQuality: FilterQuality.none)" if with_nn else "Image.asset(path)"
        target.write_text(body, encoding="utf-8")

    def test_green_fixture_passes(self) -> None:
        self.consumer_file()
        self.write_ledger(self.base_entries())
        self.assertEqual(self.guard.scan(), [])

    def test_pixel_entry_without_policy_blocks_P001(self) -> None:
        self.consumer_file()
        entries = self.base_entries()
        entries[0].pop("dpr_policy")
        self.write_ledger(entries)
        failures = self.guard.scan()
        self.assertTrue(any(f.startswith("P001") for f in failures), failures)

    def test_variant_not_integer_multiple_blocks_P002(self) -> None:
        self.consumer_file()
        write_png(self.root / "mobile/assets/placeholders/2.0x/placeholder_pixel_block.png", 15, 15)
        self.write_ledger(self.base_entries())
        failures = self.guard.scan()
        self.assertTrue(
            any(f.startswith("P002") and "整数倍" in f for f in failures), failures
        )

    def test_nn_consumer_without_filter_quality_blocks_P003(self) -> None:
        self.consumer_file(with_nn=False)
        self.write_ledger(self.base_entries())
        failures = self.guard.scan()
        self.assertTrue(
            any(f.startswith("P003") and "FilterQuality.none" in f for f in failures), failures
        )

    def test_real_repo_scan_is_green(self) -> None:
        """真实仓全量扫（含 P005 占位生成可复现）必须绿。"""
        for name, value in self._saved.items():
            setattr(self.guard, name, value)
        self.assertEqual(self.guard.scan(), [])


if __name__ == "__main__":
    unittest.main()
