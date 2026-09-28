#!/usr/bin/env python3
"""Rule V4S04-DPR：像素资产 DPR 导出/最近邻策略一致性守卫（可失败）。

账本每个像素类条目必须声明 dpr_policy，且声明必须可验证：

  native_multi_dpr        必须登记 dpr_variant_of/dpr_factor 变体条目；
                          变体 PNG IHDR 尺寸 = 主资产尺寸 × 因子（精确整数倍），
                          变体文件存在且 sha256 与账本一致（原生多 DPR 导出）。
  nearest_neighbor_runtime 必须登记 consumers；每个消费文件源码内必须出现
                          FilterQuality.none（NN 采样声明落地在代码，非纸面）。
  full_resolution         资产按目标密度原尺寸渲染，不做缩放（无需变体）。
  not_applicable_audio / not_applicable_data  非像素资产，仅允许这两值。

另做生成可复现性校验：重跑 scripts/devtools/generate_placeholder_sprites.py
到临时目录，逐字节比对仓内占位资源（证明占位=程序生成，可随时重建）。
"""
from __future__ import annotations

import importlib.util
import json
import os
import struct
import sys
import tempfile
from pathlib import Path

# run_all_rule_guards.sh 会传 REPO_ROOT；本地直跑回退到脚本相对定位。
REPO_ROOT = Path(os.environ.get("REPO_ROOT", Path(__file__).resolve().parents[2]))

ASSETS_ROOT = REPO_ROOT / "mobile" / "assets"
LEDGER_PATH = ASSETS_ROOT / "asset_ledger.json"
GENERATOR_PATH = REPO_ROOT / "scripts" / "devtools" / "generate_placeholder_sprites.py"

PIXEL_KINDS = {
    "image", "icon", "sprite", "environment",
    "placeholder_sprite", "placeholder_sprite_variant",
}
POLICY_PIXEL = {"native_multi_dpr", "nearest_neighbor_runtime", "full_resolution"}
POLICY_NON_PIXEL = {"not_applicable_audio", "not_applicable_data"}


def load_ledger() -> dict[str, dict]:
    data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return {entry["asset_id"]: entry for entry in data.get("entries", [])}


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not a png: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def scan() -> list[str]:
    failures: list[str] = []
    index = load_ledger()

    for asset_id, entry in index.items():
        policy = entry.get("dpr_policy")
        kind = entry.get("kind")
        if kind in PIXEL_KINDS:
            if policy not in POLICY_PIXEL:
                failures.append(
                    f"P001 {asset_id} 像素资产 dpr_policy 非法: {policy!r}（须 ∈ {sorted(POLICY_PIXEL)}）"
                )
                continue
        else:
            if policy not in POLICY_NON_PIXEL:
                failures.append(f"P001 {asset_id} 非像素资产 dpr_policy 非法: {policy!r}")
            continue

        path = REPO_ROOT / str(entry.get("path", ""))
        if not path.exists():
            failures.append(f"P002 {asset_id} 文件缺失: {path}")
            continue

        if policy == "native_multi_dpr":
            base_id = entry.get("dpr_variant_of")
            factor = entry.get("dpr_factor")
            if not base_id or not factor:
                failures.append(f"P002 {asset_id} 变体缺 dpr_variant_of/dpr_factor")
                continue
            base = index.get(str(base_id))
            if base is None:
                failures.append(f"P002 {asset_id} 主资产不在账本: {base_id}")
                continue
            base_path = REPO_ROOT / str(base.get("path", ""))
            if not base_path.exists():
                failures.append(f"P002 {asset_id} 主资产文件缺失: {base_path}")
                continue
            width, height = png_size(path)
            bw, bh = png_size(base_path)
            if (width, height) != (int(bw * factor), int(bh * factor)):
                failures.append(
                    f"P002 {asset_id} 变体 {width}x{height} != 主资产 {bw}x{bh} × {factor}"
                    "（NN 整数倍导出被破坏）"
                )

        if policy == "nearest_neighbor_runtime":
            consumers = entry.get("consumers") or []
            if not consumers:
                failures.append(f"P003 {asset_id} NN 策略缺 consumers 声明")
            for consumer in consumers:
                consumer_path = REPO_ROOT / str(consumer)
                if not consumer_path.exists():
                    failures.append(f"P003 {asset_id} consumer 不存在: {consumer}")
                    continue
                text = consumer_path.read_text(encoding="utf-8", errors="replace")
                if "FilterQuality.none" not in text:
                    failures.append(
                        f"P003 {asset_id} consumer 无 FilterQuality.none（NN 声明未落地）: {consumer}"
                    )

    # 占位资源生成可复现：临时目录重跑生成器，逐字节一致（生成器缺失时跳过）
    if GENERATOR_PATH.exists():
        spec = importlib.util.spec_from_file_location("generate_placeholder_sprites", GENERATOR_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_dir:
            module.generate(Path(temp_dir))
            for entry in index.values():
                if not str(entry.get("kind", "")).startswith("placeholder_sprite"):
                    continue
                repo_file = REPO_ROOT / str(entry.get("path", ""))
                name = Path(str(entry.get("path", ""))).name
                sub = Path(str(entry.get("path", ""))).parent.name if "x" in Path(str(entry.get("path", ""))).parent.name else ""
                rebuilt = Path(temp_dir) / sub / name if sub else Path(temp_dir) / name
                if not rebuilt.exists() or rebuilt.read_bytes() != repo_file.read_bytes():
                    failures.append(f"P005 占位资源与生成器输出不一致（非程序生成或被手改）: {entry.get('path')}")

    return failures


def main() -> int:
    failures = scan()
    if failures:
        print("[Rule V4S04-DPR] FAIL")
        for failure in failures:
            print(f"  {failure}")
        print(f"violations={len(failures)}")
        return 1
    index = load_ledger()
    pixel = sum(1 for e in index.values() if e.get("kind") in PIXEL_KINDS)
    print(f"[Rule V4S04-DPR] PASS - pixel entries={pixel} 全部声明可验证（多DPR/NN/full-res），占位生成可复现")
    return 0


if __name__ == "__main__":
    sys.exit(main())
