#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg"}
IGNORED_FILE_NAMES = {".ds_store"}


@dataclass(frozen=True)
class AlbumRule:
    name: str
    scene_tags: tuple[str, ...]
    palette_tags: tuple[str, ...]
    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]
    energy: float
    density: float
    base_gain: float
    loopable: bool
    release_approved: bool
    minimum_duration_seconds: float


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    replaced = re.sub(r"[^a-z0-9]+", "_", lowered)
    return replaced.strip("_") or "track"


def is_ignored_path(path: Path) -> bool:
    return any(
        part.startswith("._") or part.startswith(".") or part.lower() in IGNORED_FILE_NAMES
        for part in path.parts
    )


def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and not is_ignored_path(path)


def load_album_rules(config_path: Path) -> list[AlbumRule]:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    albums = raw.get("albums", [])
    global_minimum_duration_seconds = float(raw.get("minimumDurationSeconds", 75.0))
    rules: list[AlbumRule] = []
    for item in albums:
        rules.append(
            AlbumRule(
                name=item["name"],
                scene_tags=tuple(item.get("sceneTags", [])),
                palette_tags=tuple(item.get("paletteTags", [])),
                include_patterns=tuple(item.get("includePatterns", [])),
                exclude_patterns=tuple(item.get("excludePatterns", [])),
                energy=float(item.get("energy", 0.35)),
                density=float(item.get("density", 0.30)),
                base_gain=float(item.get("baseGain", 0.92)),
                loopable=bool(item.get("loopable", False)),
                release_approved=bool(item.get("releaseApproved", False)),
                minimum_duration_seconds=float(
                    item.get("minimumDurationSeconds", global_minimum_duration_seconds)
                ),
            )
        )
    return rules


def discover_audio_files(library_root: Path, album_rules: list[AlbumRule]) -> dict[AlbumRule, list[Path]]:
    available: dict[AlbumRule, list[Path]] = {}
    for rule in album_rules:
        album_dir = library_root / rule.name
        if not album_dir.exists() or not album_dir.is_dir():
            available[rule] = []
            continue
        files = sorted(path for path in album_dir.rglob("*") if path.is_file() and is_audio_file(path))
        available[rule] = filter_rule_files(files, rule)
    return available


def filter_rule_files(files: list[Path], rule: AlbumRule) -> list[Path]:
    selected: list[Path] = []
    for path in files:
        name = path.name
        if rule.include_patterns and not any(fnmatch.fnmatch(name, pattern) for pattern in rule.include_patterns):
            continue
        if rule.exclude_patterns and any(fnmatch.fnmatch(name, pattern) for pattern in rule.exclude_patterns):
            continue
        selected.append(path)
    return selected


def build_catalog_entries(
    discovered: dict[AlbumRule, list[Path]],
    *,
    output_prefix: str = "audio/bgm/curated",
) -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []
    for rule, files in discovered.items():
        for index, source_path in enumerate(files, start=1):
            duration_seconds = probe_duration_seconds(source_path)
            release_approved = (
                rule.release_approved
                and duration_seconds is not None
                and duration_seconds >= rule.minimum_duration_seconds
            )
            album_slug = slugify(rule.name)
            track_slug = slugify(source_path.stem)
            file_name = f"{album_slug}__{index:02d}_{track_slug}.m4a"
            catalog.append(
                {
                    "id": f"{album_slug}_{track_slug}",
                    "assetPath": f"{output_prefix}/{file_name}",
                    "album": rule.name,
                    "sceneTags": list(rule.scene_tags),
                    "paletteTags": list(rule.palette_tags),
                    "energy": max(0.0, min(1.0, rule.energy)),
                    "density": max(0.0, min(1.0, rule.density)),
                    "baseGain": max(0.1, min(1.2, rule.base_gain)),
                    "loopable": rule.loopable,
                    "releaseApproved": release_approved,
                    "_sourcePath": str(source_path),
                    "_outputFileName": file_name,
                    "_durationSeconds": duration_seconds,
                }
            )
    return catalog


def probe_duration_seconds(path: Path) -> float | None:
    try:
        raw = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def transcode_track(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(destination),
        ],
        check=True,
    )


def write_catalog(entries: list[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = []
    for entry in entries:
        serializable.append(
            {
                key: value
                for key, value in entry.items()
                if not key.startswith("_")
            }
        )
    output_path.write_text(
        json.dumps({"entries": serializable}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_curator(
    *,
    library_root: Path,
    config_path: Path,
    output_dir: Path,
    catalog_out: Path,
    dry_run: bool,
) -> list[dict[str, object]]:
    rules = load_album_rules(config_path)
    discovered = discover_audio_files(library_root, rules)
    entries = build_catalog_entries(discovered)
    if not dry_run:
        for entry in entries:
            if not entry["releaseApproved"]:
                continue
            transcode_track(
                Path(entry["_sourcePath"]),
                output_dir / str(entry["_outputFileName"]),
            )
    write_catalog(entries, catalog_out)
    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Curate BGM albums into app-safe assets and a catalog.")
    parser.add_argument("--library-root", type=Path, default=Path("/Volumes/移动E/Music"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("mobile/assets/audio/bgm/curated"),
    )
    parser.add_argument(
        "--catalog-out",
        type=Path,
        default=Path("mobile/assets/audio/bgm/bgm_catalog.json"),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    entries = run_curator(
        library_root=args.library_root,
        config_path=args.config,
        output_dir=args.output_dir,
        catalog_out=args.catalog_out,
        dry_run=args.dry_run,
    )
    approved_count = sum(1 for entry in entries if entry["releaseApproved"])
    print(f"Curated {len(entries)} tracks across {args.config} ({approved_count} approved for release).")


if __name__ == "__main__":
    main()
