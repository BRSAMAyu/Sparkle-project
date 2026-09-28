#!/usr/bin/env python3
"""V4-S04 资产许可账本生成/校验工具。

两个模式：
  --scaffold  扫描 mobile/assets，对账本缺失文件补条目（默认 PROPOSED/unknown，
              权利字段留空 → 守卫会红，强制人工补全后才能上发布面）。
  --verify    重算全部条目 sha256 与字节数，与账本比对，漂移即非零退出。

账本权威文件：mobile/assets/asset_ledger.json。
存量文件的作者/来源/权利按本脚本 CURATION 表如实入账：
- audio/ui、audio/ambient、images/noise_texture、bgm_catalog.json
  → internal_original（仓内 initial-commit 程序产出/团队制作，无外部署名记录）
- audio/bgm/curated/*.m4a → 商业古典录音，权利未知 → PROPOSED，ship_in_product=false
- icons/Gemini_Generated_Image_*.png → AI 生成（Gemini），权利未确认 → PROPOSED
- placeholders/* → 本仓脚本程序生成 → internal_original APPROVED
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_ROOT = REPO_ROOT / "mobile" / "assets"
LEDGER_PATH = ASSETS_ROOT / "asset_ledger.json"
LEDGER_VERSION = 1

PROVENANCE_INITIAL_COMMIT = (
    "repo-initial-commit 1722e6dc (2026-09 clean-slate); "
    "feature-coherent batch naming; no external attribution record in repo"
)

GENERIC_RIGHTS_APPROVED = {
    "license_id": "internal_original",
    "commercial_use": True,
    "redistribution": True,
    "modification": True,
    "attribution": "Sparkle team",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def entry_for(path: Path, *, kind: str, purpose: str, status: str,
              dpr_policy: str, fallback: str, source: str, author: str,
              rights: dict | None, version: str, consumer_files: list[str] | None = None,
              provenance: str = "", ship: bool | None = None) -> dict[str, object]:
    approved = status == "APPROVED"
    data = path.read_bytes()
    entry: dict[str, object] = {
        "asset_id": path.relative_to(ASSETS_ROOT).as_posix(),
        "path": rel(path),
        "kind": kind,
        "purpose": purpose,
        "author": author,
        "source": source,
        "rights": rights if rights is not None else {
            "license_id": "unknown",
            "commercial_use": False,
            "redistribution": False,
            "modification": False,
            "attribution": "",
        },
        "version": version,
        "sha256": sha256_file(path),
        "bytes": len(data),
        "fallback": fallback,
        "status": status,
        "ship_in_product": approved if ship is None else ship,
        "dpr_policy": dpr_policy,
    }
    if consumer_files:
        entry["consumers"] = consumer_files
    if provenance:
        entry["provenance_note"] = provenance
    return entry


def curated_entry(path: Path) -> dict[str, object]:
    name = path.stem
    base: dict[str, object] = {
        "asset_id": path.relative_to(ASSETS_ROOT).as_posix(),
        "path": rel(path),
        "kind": "bgm_track",
        "purpose": "bgm candidate (curated classical recording)",
        "author": "unverified: performer/label identified from filename only",
        "source": "commercial_recording_filename_evidence (no license document in repo)",
        "rights": {
            "license_id": "unknown",
            "commercial_use": False,
            "redistribution": False,
            "modification": False,
            "attribution": "",
        },
        "version": "0.0.0",
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "fallback": "silent",
        "status": "PROPOSED",
        "ship_in_product": False,
        "dpr_policy": "not_applicable_audio",
        "provenance_note": (
            "commercial classical recording staged under assets/audio/bgm/curated/; "
            "kept out of pubspec bundle (subdirectory not declared); pending license evidence"
        ),
    }
    _ = name
    return base


def gemini_icon_entry(path: Path) -> dict[str, object]:
    return entry_for(
        path,
        kind="icon",
        purpose="app icon candidate (AI generated, unreviewed)",
        status="PROPOSED",
        dpr_policy="full_resolution",
        fallback="placeholder_pixel_block",
        source="ai_generated_gemini (filename evidence; prompt/seed not archived)",
        author="unverified: AI generation, team review pending",
        rights=None,
        version="0.0.0",
        provenance=(
            "moved out of declared bundle dir assets/icons/ into assets/staging/ "
            "by V4-S04; must stay PROPOSED until rights review"
        ),
        ship=False,
    )


def build_curation() -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []

    ui_names = [
        "achievement_common", "achievement_epic", "achievement_legendary",
        "achievement_rare", "ai_start", "button1", "button2", "card_flip",
        "checkin", "complete", "confirm", "dialog_open", "drag_drop",
        "drag_start", "error", "focus_complete", "message_send", "nav",
        "off", "on", "select", "sheet_open", "star_unlock", "streak",
        "success", "tap", "toggle", "warning",
    ]
    for name in ui_names:
        path = ASSETS_ROOT / "audio" / "ui" / f"{name}.ogg"
        entries.append(entry_for(
            path, kind="sfx", purpose=f"ui sound effect: {name}",
            status="APPROVED", dpr_policy="not_applicable_audio",
            fallback="silent", source="internal_original", author="Sparkle team",
            rights=GENERIC_RIGHTS_APPROVED, version="1.0.0",
            provenance=PROVENANCE_INITIAL_COMMIT,
        ))

    for name in ("cafe", "ocean_waves", "piano", "rain", "white_noise"):
        path = ASSETS_ROOT / "audio" / "ambient" / f"{name}.ogg"
        entries.append(entry_for(
            path, kind="ambient", purpose=f"ambient loop: {name}",
            status="APPROVED", dpr_policy="not_applicable_audio",
            fallback="silent", source="internal_original", author="Sparkle team",
            rights=GENERIC_RIGHTS_APPROVED, version="1.0.0",
            provenance=PROVENANCE_INITIAL_COMMIT,
        ))

    catalog_path = ASSETS_ROOT / "audio" / "bgm" / "bgm_catalog.json"
    entries.append(entry_for(
        catalog_path, kind="config", purpose="bgm catalog manifest (data)",
        status="APPROVED", dpr_policy="not_applicable_data",
        fallback="empty_catalog_silent",
        source="internal_original", author="Sparkle team",
        rights=GENERIC_RIGHTS_APPROVED, version="1.1.0",
        consumer_files=["mobile/lib/core/services/bgm_service.dart"],
        provenance=(
            "V4-S04: releaseApproved flipped to false for all bgm/curated entries "
            "(unlicensed commercial recordings); guard enforces ledger agreement"
        ),
    ))

    for path in sorted((ASSETS_ROOT / "audio" / "bgm" / "curated").glob("*.m4a")):
        entries.append(curated_entry(path))

    staging = ASSETS_ROOT / "staging"
    for path in sorted(staging.glob("*.png")):
        entries.append(gemini_icon_entry(path))

    noise = ASSETS_ROOT / "images" / "noise_texture.png"
    entries.append(entry_for(
        noise, kind="image", purpose="material noise overlay texture",
        status="APPROVED", dpr_policy="full_resolution",
        fallback="procedural_shader_noise",
        source="internal_original", author="Sparkle team",
        rights=GENERIC_RIGHTS_APPROVED, version="1.0.0",
        consumer_files=["mobile/lib/core/design/materials.dart"],
        provenance=PROVENANCE_INITIAL_COMMIT,
    ))

    placeholder_main = ASSETS_ROOT / "placeholders" / "placeholder_pixel_block.png"
    entries.append(entry_for(
        placeholder_main, kind="placeholder_sprite",
        purpose="programmatic minimal pixel-block fallback for PROPOSED slots",
        status="APPROVED", dpr_policy="nearest_neighbor_runtime",
        fallback="self",
        source="internal_original (generated)",
        author="Sparkle team",
        rights=GENERIC_RIGHTS_APPROVED,
        version="1.0.0",
        consumer_files=["mobile/lib/core/assets/asset_catalog.dart"],
        provenance=(
            "generated by scripts/devtools/generate_placeholder_sprites.py; "
            "NN integer-multiple DPR variants 2.0x/3.0x"
        ),
    ))
    for dpr in ("2.0x", "3.0x"):
        variant = ASSETS_ROOT / "placeholders" / dpr / "placeholder_pixel_block.png"
        entry = entry_for(
            variant, kind="placeholder_sprite_variant",
            purpose=f"nearest-neighbor DPR variant {dpr} of placeholder_pixel_block",
            status="APPROVED", dpr_policy="native_multi_dpr",
            fallback="placeholder_pixel_block_1x",
            source="internal_original (generated)",
            author="Sparkle team",
            rights=GENERIC_RIGHTS_APPROVED,
            version="1.0.0",
        )
        entry["dpr_variant_of"] = "placeholders/placeholder_pixel_block.png"
        entry["dpr_factor"] = float(dpr.rstrip("x"))
        entries.append(entry)

    return entries


def load_ledger() -> dict:
    if not LEDGER_PATH.exists():
        return {"schema_version": LEDGER_VERSION, "entries": []}
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def save_ledger(data: dict) -> None:
    LEDGER_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def index_by_id(data: dict) -> dict[str, dict]:
    return {entry["asset_id"]: entry for entry in data.get("entries", [])}


def asset_files() -> list[Path]:
    skip_names = {".gitkeep", ".DS_Store"}
    return sorted(
        path
        for path in ASSETS_ROOT.rglob("*")
        if path.is_file()
        and path.name not in skip_names
        and not path.name.startswith("._")
        and path != LEDGER_PATH
    )


def scaffold() -> int:
    data = load_ledger()
    data.setdefault("schema_version", LEDGER_VERSION)
    index = index_by_id(data)
    added = 0
    for path in asset_files():
        asset_id = path.relative_to(ASSETS_ROOT).as_posix()
        if asset_id in index:
            continue
        data["entries"].append(entry_for(
            path, kind="unclassified", purpose="TODO: classify",
            status="PROPOSED", dpr_policy="not_applicable_data",
            fallback="TODO", source="unknown", author="unknown",
            rights=None, version="0.0.0",
        ))
        added += 1
    save_ledger(data)
    print(f"scaffold: +{added} new PROPOSED entries, total {len(data['entries'])}")
    return 0


def verify() -> int:
    data = load_ledger()
    index = index_by_id(data)
    failures: list[str] = []
    covered: set[str] = set()
    for path in asset_files():
        asset_id = path.relative_to(ASSETS_ROOT).as_posix()
        covered.add(asset_id)
        entry = index.get(asset_id)
        if entry is None:
            failures.append(f"UNLEDGERED {asset_id}")
            continue
        if entry.get("sha256") != sha256_file(path):
            failures.append(f"HASH_DRIFT {asset_id}")
        if entry.get("bytes") != path.stat().st_size:
            failures.append(f"SIZE_DRIFT {asset_id}")
    for asset_id in index:
        if asset_id not in covered:
            failures.append(f"GHOST_ENTRY {asset_id} (file missing)")
    if failures:
        print("[asset-ledger] FAIL")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"[asset-ledger] PASS - {len(index)} entries verified (hash+size+coverage)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scaffold", action="store_true", help="add missing entries as PROPOSED")
    parser.add_argument("--rebuild", action="store_true", help="rebuild ledger from curation table")
    parser.add_argument("--verify", action="store_true", help="verify hashes and coverage")
    args = parser.parse_args()
    if args.rebuild:
        data = {
            "schema_version": LEDGER_VERSION,
            "policy": {
                "ledger_is_authority": True,
                "release_surface_rule": (
                    "only APPROVED + ship_in_product entries may be referenced by "
                    "pubspec-declared bundle dirs, font declarations, or bundled configs"
                ),
                "proposed_rule": "PROPOSED assets resolve to generated placeholders at runtime",
            },
            "entries": build_curation(),
        }
        save_ledger(data)
        print(f"rebuild: {len(data['entries'])} entries")
        return 0
    if args.scaffold:
        return scaffold()
    if args.verify:
        return verify()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
