"""journey 用例加载器：从 scripts/devtools/journey_harness/journeys/*.json 读取。

persona 统一（B-03 work#2）：journey 定义可声明 `"persona": "<id>"`，指向
v3/05_metrics_eval/persona_library.json 的 persona id（P01..P10）。loader 在加载期
即校验并解析完整 persona（未知 id = ValueError，加载失败=诚实失败，不吞）；
runner 把解析结果记入 run_manifest.persona（persona 可追溯）与 journey_definition
快照。persona 库路径可用环境变量 JOURNEY_PERSONA_LIBRARY 覆盖（测试注入用）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import JourneySpec, StepSpec

JOURNEY_DIR = Path(__file__).resolve().parent.parent / "journeys"
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PERSONA_LIBRARY = REPO_ROOT / "v3" / "05_metrics_eval" / "persona_library.json"


def persona_library_path() -> Path:
    override = os.environ.get("JOURNEY_PERSONA_LIBRARY", "")
    return Path(override) if override else DEFAULT_PERSONA_LIBRARY


def load_persona_library(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """读 persona library 为 {id: persona}。文件缺失/形状不对 = 明确报错，不静默。"""
    library = path or persona_library_path()
    if not library.exists():
        raise FileNotFoundError(f"persona library 不存在: {library}")
    raw = json.loads(library.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"persona library 形状应为 list: {library}")
    out: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict) or not item.get("id"):
            raise ValueError(f"persona library 存在缺 id 的条目: {library}")
        out[str(item["id"])] = item
    return out


def resolve_persona(persona_id: str, library: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if persona_id not in library:
        raise ValueError(
            f"未知 persona id {persona_id!r}（persona_library 可用: {sorted(library)}）；"
            f"journey 声明的 persona 必须来自 v3/05_metrics_eval/persona_library.json"
        )
    return library[persona_id]


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


def parse_journey(path: Path, persona_library: dict[str, dict[str, Any]] | None = None) -> JourneySpec:
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
    persona_raw = str(raw.get("persona") or "").strip()
    persona: dict[str, Any] = {}
    if persona_raw:
        persona = resolve_persona(
            persona_raw, persona_library if persona_library is not None else load_persona_library()
        )
    return JourneySpec(
        id=str(raw["id"]),
        title=str(raw["title"]),
        golden_ref=str(raw["golden_ref"]),
        description=str(raw.get("description", "")),
        backends=backends,
        db_asserts=list(raw.get("db_asserts") or []),
        platforms=dict(raw.get("platforms") or {}),
        persona=persona,
        path=path,
    )


def list_journeys(journey_dir: Path | None = None) -> list[str]:
    directory = journey_dir or JOURNEY_DIR
    return sorted({p.name.split("_", 1)[0] for p in directory.glob("*.json")})
