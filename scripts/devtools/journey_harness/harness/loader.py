"""journey 用例加载器：从 scripts/devtools/journey_harness/journeys/*.json 读取。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import JourneySpec, StepSpec

JOURNEY_DIR = Path(__file__).resolve().parent.parent / "journeys"


def load_journey(journey_id: str, journey_dir: Path | None = None) -> JourneySpec:
    """按 id（如 GJ01）加载 journey 定义文件 <id>_*.json。"""
    directory = journey_dir or JOURNEY_DIR
    candidates = sorted(directory.glob(f"{journey_id.upper()}_*.json"))
    if not candidates:
        raise FileNotFoundError(
            f"journey 定义未找到: {journey_id}（在 {directory} 下找 {journey_id.upper()}_*.json）"
        )
    if len(candidates) > 1:
        raise ValueError(
            f"journey id {journey_id} 匹配到多个定义文件: {[c.name for c in candidates]}，请保持 id 唯一"
        )
    return parse_journey(candidates[0])


def parse_journey(path: Path) -> JourneySpec:
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    for key in ("id", "title", "golden_ref", "backends"):
        if key not in raw:
            raise ValueError(f"{path.name}: journey 定义缺少必填字段 {key!r}")
    backends: dict[str, list[StepSpec]] = {}
    for backend_name, steps_raw in raw["backends"].items():
        if not isinstance(steps_raw, list) or not steps_raw:
            raise ValueError(f"{path.name}: backend {backend_name} 的 steps 必须是非空数组")
        backends[backend_name] = [
            StepSpec.from_dict(s, i) for i, s in enumerate(steps_raw)
        ]
    return JourneySpec(
        id=str(raw["id"]),
        title=str(raw["title"]),
        golden_ref=str(raw["golden_ref"]),
        description=str(raw.get("description", "")),
        backends=backends,
        db_asserts=list(raw.get("db_asserts") or []),
        platforms=dict(raw.get("platforms") or {}),
        path=path,
    )


def list_journeys(journey_dir: Path | None = None) -> list[str]:
    directory = journey_dir or JOURNEY_DIR
    return sorted({p.name.split("_", 1)[0] for p in directory.glob("*.json")})
