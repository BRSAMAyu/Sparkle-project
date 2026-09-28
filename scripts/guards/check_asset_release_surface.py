#!/usr/bin/env python3
"""Rule V4S04-ASSETS：资产许可账本发布面守卫（可失败）。

权威账本：mobile/assets/asset_ledger.json（由 scripts/devtools/generate_asset_ledger.py
维护；守卫独立重算 sha256，不信任账本自报）。

检查项（任何一条即非零退出）：
  L001 六要素不全     条目缺 author/source/rights(license_id+三权+attribution)/version/sha256/fallback
  L002 哈希漂移       账本 sha256/bytes 与磁盘实际不符
  L003 打包未入账     pubspec 声明目录（含 DPR variant 子目录）中的文件不在账本
  L004 未批准上发布面 打包面出现非 APPROVED 或 ship_in_product=false 的资产
  L005 未知字体       mobile/ 下任何 .ttf/.otf/.ttc/.woff/.woff2 未入账或非已批准开源许可
  L006 目录引用未批准 bgm_catalog.json 中 releaseApproved=true 的条目指向非 APPROVED 资产
  L007 Dart 引用未入账 lib/ 下字符串字面量引用的 assets/ 路径不在账本 APPROVED 集
  L008 越过间接层     assets/ 路径字面量出现在账本 consumers 与 asset_catalog.dart 之外
                       （业务必须经 AssetCatalog asset key 间接层）

反例（历史证据见 v4/evidence/V4-S04/）：向打包目录塞未知许可文件 → L003 红。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

# run_all_rule_guards.sh 会传 REPO_ROOT；本地直跑回退到脚本相对定位。
REPO_ROOT = Path(os.environ.get("REPO_ROOT", Path(__file__).resolve().parents[2]))

ASSETS_ROOT = REPO_ROOT / "mobile" / "assets"
LEDGER_PATH = ASSETS_ROOT / "asset_ledger.json"
PUBSPEC_PATH = REPO_ROOT / "mobile" / "pubspec.yaml"
LIB_ROOT = REPO_ROOT / "mobile" / "lib"
BGM_CATALOG = ASSETS_ROOT / "audio" / "bgm" / "bgm_catalog.json"

DOT_SIDECARS = {".gitkeep", ".DS_Store"}
FONT_EXTS = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
RASTER_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
VARIANT_DIR = re.compile(r"^\d+\.\d+x$")
FONT_LICENSES_KNOWN = {
    "OFL", "Apache_2_0", "IPA", "SIL_OFL", "UFL", "internal_original",
}
REQUIRED_RIGHTS = ("license_id", "commercial_use", "redistribution", "modification", "attribution")
REQUIRED_FIELDS = ("asset_id", "path", "author", "source", "rights", "version", "sha256", "fallback", "status")
ASSET_LITERAL = re.compile(r"['\"](assets/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)['\"]")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_pubspec_declared_dirs_and_fonts() -> tuple[list[str], list[str]]:
    """从 pubspec.yaml 抽取 flutter.assets 目录声明与 flutter.fonts 资产（极简定向解析）。"""
    lines = PUBSPEC_PATH.read_text(encoding="utf-8").splitlines()
    dirs: list[str] = []
    fonts: list[str] = []
    section: str | None = None
    indent_assets = -1
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if stripped.startswith("flutter:") and not section:
            section = "flutter"
            continue
        if stripped == "assets:":
            section, indent_assets = "assets", indent
            continue
        if stripped == "fonts:":
            section, indent_assets = "fonts", indent
            continue
        in_list_block = section in ("assets", "fonts") and (
            indent > indent_assets or stripped.startswith("- ")
        )
        if not in_list_block:
            # 回到其它 flutter 键（如 shaders:/uses-material-design:）→ 退出列表块
            if section in ("assets", "fonts") and indent <= indent_assets:
                section = "flutter"
            continue
        if stripped.startswith("- "):
            value = stripped[2:].strip().split("#", 1)[0].strip()
            if section == "assets":
                dirs.append(value)
            else:
                fonts.append(value)
    return dirs, fonts


def bundled_files(declared_dirs: list[str]) -> list[Path]:
    """Flutter 目录声明只含直接子文件；DPR variant 子目录（2.0x/3.0x…）随主资产打包。"""
    files: list[Path] = []
    for declared in declared_dirs:
        base = REPO_ROOT / "mobile" / declared.rstrip("/")
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if child.is_file() and child.name not in DOT_SIDECARS and not child.name.startswith("._"):
                files.append(child)
            elif child.is_dir() and VARIANT_DIR.match(child.name):
                for variant_file in sorted(child.rglob("*")):
                    if variant_file.is_file() and variant_file.name not in DOT_SIDECARS:
                        files.append(variant_file)
    return files


def load_ledger() -> tuple[dict[str, dict], list[str]]:
    failures: list[str] = []
    if not LEDGER_PATH.exists():
        return {}, ["L000 ledger missing: mobile/assets/asset_ledger.json"]
    data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    index: dict[str, dict] = {}
    for entry in data.get("entries", []):
        asset_id = entry.get("asset_id", "<missing>")
        for field in REQUIRED_FIELDS:
            if field not in entry or entry[field] in ("", None):
                failures.append(f"L001 {asset_id} 六要素缺失: {field}")
        rights = entry.get("rights")
        if not isinstance(rights, dict):
            failures.append(f"L001 {asset_id} rights 非对象")
        else:
            for field in REQUIRED_RIGHTS:
                if field not in rights:
                    failures.append(f"L001 {asset_id} rights 缺 {field}")
        if "status" in entry and entry["status"] not in ("APPROVED", "PROPOSED", "REFERENCE_ONLY"):
            failures.append(f"L001 {asset_id} 非法 status: {entry['status']}")
        index[entry.get("asset_id", "")] = entry
    return index, failures


def scan() -> list[str]:
    failures: list[str] = []
    index, load_failures = load_ledger()
    failures.extend(load_failures)
    if load_failures and not index:
        return failures

    # L002 哈希/字节漂移 + 打包面覆盖
    declared_dirs, declared_fonts = parse_pubspec_declared_dirs_and_fonts()
    bundled = bundled_files(declared_dirs)
    for path in bundled:
        asset_id = path.relative_to(ASSETS_ROOT).as_posix()
        entry = index.get(asset_id)
        if entry is None:
            failures.append(f"L003 打包未入账: {asset_id}")
            continue
        disk = path
        if entry.get("sha256") != sha256_file(disk) or entry.get("bytes") != disk.stat().st_size:
            failures.append(f"L002 哈希漂移: {asset_id}")
        if entry.get("status") != "APPROVED" or entry.get("ship_in_product") is not True:
            failures.append(f"L004 未批准上发布面: {asset_id} status={entry.get('status')}")

    # 账本中标记 ship_in_product=true 的条目必须真实可打包或在账本豁免说明内
    for asset_id, entry in index.items():
        if entry.get("ship_in_product") is True:
            path = REPO_ROOT / str(entry.get("path", ""))
            if not path.exists():
                failures.append(f"L002 账本指向缺失文件: {asset_id}")

    # L005 字体（跳过本地构建缓存目录——它们是 gitignored 的依赖检出/产物，
    # 不属于「入产物面」的仓库声明范围；CI 新检出与 worktree 无这些目录）
    for path in (REPO_ROOT / "mobile").rglob("*"):
        if path.suffix.lower() in FONT_EXTS and path.is_file():
            if any(part in ("build", ".dart_tool", "Pods", ".symlinks", "ephemeral") for part in path.parts):
                continue
            asset_id = (
                path.relative_to(ASSETS_ROOT).as_posix()
                if ASSETS_ROOT in path.parents
                else path.relative_to(REPO_ROOT / "mobile").as_posix()
            )
            entry = index.get(asset_id)
            if entry is None:
                failures.append(f"L005 未知字体未入账: {asset_id}")
            elif entry.get("status") != "APPROVED" or entry.get("rights", {}).get("license_id") not in FONT_LICENSES_KNOWN:
                failures.append(f"L005 字体许可不合规: {asset_id} license={entry.get('rights', {}).get('license_id')}")
    for font_decl in declared_fonts:
        asset_id = font_decl.lstrip("./")
        entry = index.get(asset_id)
        if entry is None:
            failures.append(f"L005 pubspec 字体未入账: {asset_id}")
        elif entry.get("status") != "APPROVED":
            failures.append(f"L005 pubspec 字体未批准: {asset_id}")

    # L006 bgm_catalog 引用一致性
    if BGM_CATALOG.exists():
        catalog = json.loads(BGM_CATALOG.read_text(encoding="utf-8"))
        for item in catalog.get("entries", []):
            if item.get("releaseApproved") is not True:
                continue
            ref = str(item.get("assetPath", ""))
            entry = next(
                (e for e in index.values()
                 if str(e.get("path", "")).endswith(ref) or e.get("asset_id") == ref),
                None,
            )
            if entry is None:
                failures.append(f"L006 目录引用未入账: {ref}")
            elif entry.get("status") != "APPROVED" or entry.get("ship_in_product") is not True:
                failures.append(f"L006 releaseApproved=true 指向未批准资产: {ref} status={entry.get('status')}")

    # L007/L008 Dart 字面量引用
    approved_bundle_paths = {
        str(entry.get("path", "")): asset_id
        for asset_id, entry in index.items()
        if entry.get("status") == "APPROVED" and entry.get("ship_in_product") is True
    }
    consumers_ok: dict[str, set[str]] = {}
    for asset_id, entry in index.items():
        for consumer in entry.get("consumers", []):
            consumers_ok.setdefault(consumer, set()).add(str(entry.get("path", "")))

    for dart in sorted(LIB_ROOT.rglob("*.dart")):
        rel_dart = dart.relative_to(REPO_ROOT).as_posix()
        text = dart.read_text(encoding="utf-8", errors="replace")
        for match in ASSET_LITERAL.finditer(text):
            literal = match.group(1)
            full_rel = f"mobile/{literal}"
            if full_rel not in approved_bundle_paths:
                failures.append(f"L007 Dart 引用未入账/未批准: {rel_dart} -> {literal}")
            elif rel_dart != "mobile/lib/core/assets/asset_catalog.dart" and full_rel not in consumers_ok.get(rel_dart, set()):
                failures.append(f"L008 越过间接层硬编码: {rel_dart} -> {literal}（经 AssetCatalog key 引用）")

    # 占位资源目录之外的 assets 下栅格文件必须入账（含 staging；反例游戏图标/剪图）
    for path in ASSETS_ROOT.rglob("*"):
        if path.suffix.lower() in RASTER_EXTS and path.is_file():
            asset_id = path.relative_to(ASSETS_ROOT).as_posix()
            if asset_id not in index:
                failures.append(f"L003 栅格未入账: {asset_id}")

    return failures


def main() -> int:
    failures = scan()
    if failures:
        print("[Rule V4S04-ASSETS] FAIL")
        for failure in failures:
            print(f"  {failure}")
        print(f"violations={len(failures)}")
        return 1
    index, _ = load_ledger()
    approved = sum(1 for e in index.values() if e.get("status") == "APPROVED")
    proposed = sum(1 for e in index.values() if e.get("status") == "PROPOSED")
    print(
        f"[Rule V4S04-ASSETS] PASS - ledger={len(index)} approved={approved} "
        f"proposed={proposed} (proposed 全部隔离于发布面)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
