"""B-04 baseline manifest：生成/加载/校验。

manifest 是基线的唯一事实源（截图 PNG 本身不入 git）：
- 记录每张截图的 canonical 命名字段 + 相对路径 + sha256 + bytes + captured_at；
- ``verify`` 以 sha256 复验截图目录与 manifest 的一致性（缺失/多余/篡改）。

schema_version=1 字段::

    {
      "schema_version": 1,
      "kind": "visual-baseline-manifest",
      "build_sha": "<40hex>",
      "generated_at": "<UTC ISO8601>",
      "device": {"platform": "android", "model": "...", "viewport": "412x916@2.6"},
      "backend": {"gateway_url": "...", "engine_url": "..."},
      "entries": [ {entry...}, ... ]
    }
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .naming import SCREENSHOT_SUFFIX, parse_filename

MANIFEST_KIND = "visual-baseline-manifest"
SCHEMA_VERSION = 1


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_entry(png_path: Path, screens_root: Path) -> dict:
    """从一张 canonical 命名的 PNG 构造 manifest 条目。

    - 文件即事实源：字段由文件名解析（不合法即抛 NamingError）；
    - ``path`` 为相对 screens_root 的 POSIX 相对路径。
    """
    fields = parse_filename(png_path.name)
    rel = png_path.relative_to(screens_root).as_posix()
    stat = png_path.stat()
    return {
        **fields,
        "file": png_path.name,
        "path": rel,
        "sha256": sha256_file(png_path),
        "bytes": stat.st_size,
        "captured_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }


def build_manifest(
    screens_dir: str | Path,
    build_sha: str,
    platform: str,
    viewport: str,
    model: str = "",
    gateway_url: str = "",
    engine_url: str = "",
) -> dict:
    """扫描截图目录，返回 manifest dict（entries 按 path 排序）。"""
    root = Path(screens_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"screens dir not found: {root}")
    pngs = sorted(root.rglob(f"*{SCREENSHOT_SUFFIX}"))
    entries = [build_entry(p, root) for p in pngs]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "build_sha": build_sha,
        "generated_at": utc_now_iso(),
        "device": {"platform": platform, "model": model, "viewport": viewport},
        "backend": {"gateway_url": gateway_url, "engine_url": engine_url},
        "entries": entries,
    }


def write_manifest(manifest: dict, out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return out


def load_manifest(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest_schema(data)
    return data


def validate_manifest_schema(data: dict) -> None:
    """宽松 schema 校验：kind/版本/关键字段存在且 entries 结构可解析。"""
    if data.get("kind") != MANIFEST_KIND:
        raise ValueError(f"manifest kind mismatch: {data.get('kind')!r}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version: {data.get('schema_version')!r}"
        )
    for key in ("build_sha", "generated_at", "device", "entries"):
        if key not in data:
            raise ValueError(f"manifest missing required key: {key!r}")
    required_entry_keys = {
        "surface",
        "state",
        "persona",
        "platform",
        "viewport",
        "sha8",
        "path",
        "sha256",
    }
    for i, entry in enumerate(data["entries"]):
        missing = required_entry_keys - set(entry)
        if missing:
            raise ValueError(f"entries[{i}] missing keys: {sorted(missing)}")


def verify_screens(screens_dir: str | Path, manifest: dict) -> dict:
    """复验截图目录 vs manifest。

    返回 ``{"ok": bool, "missing": [...], "extra": [...], "hash_mismatch": [...],
    "renamed": [...]}``；``ok=False`` 时 CLI 以非零码退出（失败必须可见）。
    """
    root = Path(screens_dir)
    actual = {
        p.relative_to(root).as_posix(): p for p in root.rglob(f"*{SCREENSHOT_SUFFIX}")
    }
    expected = {e["path"]: e for e in manifest["entries"]}

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))

    hash_mismatch: list[str] = []
    renamed: list[str] = []
    expected_by_hash = {e["sha256"]: e["path"] for e in expected.values()}
    for rel in sorted(set(actual) & set(expected)):
        if sha256_file(actual[rel]) != expected[rel]["sha256"]:
            hash_mismatch.append(rel)

    for rel in extra:
        got = sha256_file(actual[rel])
        if got in expected_by_hash:
            renamed.append(f"{expected_by_hash[got]} -> {rel}")

    ok = not (missing or extra or hash_mismatch)
    return {
        "ok": ok,
        "missing": missing,
        "extra": extra,
        "hash_mismatch": hash_mismatch,
        "renamed": renamed,
    }
