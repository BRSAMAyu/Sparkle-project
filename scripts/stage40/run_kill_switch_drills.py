#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.aurora_stage21_kill_switch_service import AuroraStage21KillSwitchService
from app.services.aurora_stage23_kill_switch_service import AuroraStage23KillSwitchService
from app.services.aurora_stage24_policy_kill_switch_service import AuroraStage24PolicyKillSwitchService
from app.services.aurora_stage25_reflection_kill_switch_service import AuroraStage25ReflectionKillSwitchService
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.aurora_stage27_foresight_kill_switch_service import AuroraStage27ForesightKillSwitchService
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService
from app.services.aurora_stage30_metacognition_kill_switch_service import AuroraStage30MetacognitionKillSwitchService
from app.services.aurora_stage31_idiographic_kill_switch_service import AuroraStage31IdiographicKillSwitchService
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService
from app.services.aurora_stage35_kill_switch_service import AuroraStage35KillSwitchService
from app.services.aurora_stage37_llm_safety_kill_switch_service import AuroraStage37LLMSafetyKillSwitchService
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService
from app.services.aurora_stage39_kill_switch_service import AuroraStage39KillSwitchService
from app.services.aurora_doc_context_kill_switch_service import AuroraDocContextKillSwitchService
from app.services.aurora_stage40_calendar_kill_switch_service import AuroraStage40CalendarKillSwitchService
from app.services.aurora_dual_core_router_kill_switch_service import AuroraDualCoreRouterKillSwitchService
from app.core.kill_switch import write_mode as _ks_write_mode
from app.core.cache import cache_service as _cache


TRANSITIONS = ("off", "shadow", "live", "shadow", "off")
DEFAULT_SPECS = (
    "stage18",
    "stage19",
    "stage21",
    "stage23",
    "stage24",
    "stage25",
    "stage26",
    "stage27",
    "stage28",
    "stage29",
    "stage30",
    "stage31",
    "stage33",
    "stage34",
    "stage35",
    "stage37",
    "stage38",
    "stage39",
    "privacy",
    "doc_context",
    "dual_core_router",
    "stage40-calendar",
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class DrillSpec:
    name: str
    stage: str
    description: str
    mode_keys: tuple[str, ...]
    apply_mode: Callable[[str], Awaitable[dict[str, Any]]]


async def _stage18_apply(mode: str) -> dict[str, str]:
    service = AuroraStage18KillSwitchService()
    return await service.set_flags({key: mode for key in service.BINDINGS})


async def _stage19_apply(mode: str) -> dict[str, str]:
    service = AuroraStage19KillSwitchService()
    return await service.set_flags({key: mode for key in service.BINDINGS})


async def _stage21_apply(mode: str) -> dict[str, str]:
    service = AuroraStage21KillSwitchService()
    return await service.set_flags({key: mode for key in service.BINDINGS})


async def _stage23_apply(mode: str) -> dict[str, Any]:
    service = AuroraStage23KillSwitchService()
    await service.set_mode(mode)
    return await service.get_all()


async def _stage24_apply(mode: str) -> dict[str, Any]:
    service = AuroraStage24PolicyKillSwitchService()
    await service.set_mode(mode)
    return await service.get_all()


async def _stage25_apply(mode: str) -> dict[str, Any]:
    service = AuroraStage25ReflectionKillSwitchService()
    await service.set_mode(mode)
    return await service.get_all()


async def _stage26_apply(mode: str) -> dict[str, str]:
    service = AuroraStage26SceneKillSwitchService()
    await service.set_mode(mode)
    return {"mode": await service.get_mode()}


async def _stage27_apply(mode: str) -> dict[str, str]:
    service = AuroraStage27ForesightKillSwitchService()
    await service.set_mode(mode)
    for feature in service.FEATURE_BINDINGS:
        await service.set_feature_mode(feature, mode)
    return await service.get_all()


async def _stage28_apply(mode: str) -> dict[str, str]:
    service = AuroraStage28TraitsKillSwitchService()
    await service.set_mode(mode)
    await service.set_nlp_mode(mode)
    await service.set_coldstart_mode(mode)
    return {
        "mode": await service.get_mode(),
        "nlp_mode": await service.get_nlp_mode(),
        "coldstart_mode": await service.get_coldstart_mode(),
    }


async def _stage29_apply(mode: str) -> dict[str, str]:
    service = AuroraStage29SRLKillSwitchService()
    if mode == "off":
        await service.set_mode("off")
        await service.set_tracker_mode("off")
        await service.set_bridge_mode("off")
        await service.set_scaffolding_consume_mode("off")
    else:
        await service.set_mode(mode)
        await service.set_tracker_mode(mode)
        await service.set_bridge_mode(mode)
        await service.set_scaffolding_consume_mode(mode)
    return await service.summary()


async def _stage30_apply(mode: str) -> dict[str, str]:
    service = AuroraStage30MetacognitionKillSwitchService()
    await service.set_mode(mode)
    for feature in service.FEATURE_BINDINGS:
        await service.set_feature_mode(feature, mode)
    return {
        "mode": await service.get_mode(),
        "dashboard": await service.get_feature_mode("dashboard"),
        "process_scaffolding": await service.get_feature_mode("process_scaffolding"),
        "fsm_combine": await service.get_feature_mode("fsm_combine"),
    }


async def _stage31_apply(mode: str) -> dict[str, str]:
    service = AuroraStage31IdiographicKillSwitchService()
    await service.set_mode(mode)
    return {"mode": await service.get_mode()}


async def _stage33_apply(mode: str) -> dict[str, str]:
    service = AuroraStage33KillSwitchService()
    await service.set_mode(mode)
    for feature in service.FEATURE_BINDINGS:
        await service.set_feature_mode(feature, mode)
    return await service.summary()


async def _stage34_apply(mode: str) -> dict[str, str]:
    service = AuroraStage34KillSwitchService()
    if mode == "off":
        await service.set_mode("off")
        for feature in service.FEATURE_BINDINGS:
            await service.set_feature_mode(feature, "off")
    else:
        await service.set_mode(mode)
        for feature in service.FEATURE_BINDINGS:
            await service.set_feature_mode(feature, mode)
    return await service.summary()


async def _stage35_apply(mode: str) -> dict[str, str]:
    service = AuroraStage35KillSwitchService()
    await service.set_mode(mode)
    for feature in service.FEATURE_BINDINGS:
        await service.set_feature_mode(feature, mode)
    return await service.summary()


async def _stage37_apply(mode: str) -> dict[str, str]:
    service = AuroraStage37LLMSafetyKillSwitchService()
    await service.set_mode(mode)
    return {"mode": await service.get_mode()}


async def _stage38_apply(mode: str) -> dict[str, str]:
    service = AuroraStage38KillSwitchService()
    await service.set_feature_mode("err_replan", mode)
    await service.set_feature_mode("push_scheduler", mode)
    return await service.summary()


async def _stage39_apply(mode: str) -> dict[str, Any]:
    service = AuroraStage39KillSwitchService()
    if mode == "off":
        await service.set_mode("off")
        for feature in ("scaffolding_prompt", "cogload_route", "galaxy_inject"):
            await service.set_feature_mode(feature, "off")
    else:
        await service.set_mode(mode)
        for feature in ("scaffolding_prompt", "cogload_route", "galaxy_inject"):
            await service.set_feature_mode(feature, mode)
    return await service.summary()


async def _dual_core_router_apply(mode: str) -> dict[str, str]:
    service = AuroraDualCoreRouterKillSwitchService()
    await service.set_mode(mode)
    return await service.summary()


_PRIVACY_BINDING = type(
    "PrivacyBinding",
    (),
    {"stage": "privacy", "feature": "pii_redaction", "redis_key": "aurora:privacy:pii_redaction",
     "settings_attr": "AURORA_PRIVACY_PII_REDACTION_MODE", "fallback_mode": "live"},
)()


async def _privacy_apply(mode: str) -> dict[str, str]:
    redis_client = _cache.redis
    await _ks_write_mode(
        redis_client=redis_client, prefix="sparkle:", binding=_PRIVACY_BINDING, mode=mode,
    )
    return {"pii_redaction_mode": mode}


async def _doc_context_apply(mode: str) -> dict[str, str]:
    service = AuroraDocContextKillSwitchService()
    await service.set_mode(mode)
    return {"mode": await service.get_mode()}


async def _stage40_apply(mode: str) -> dict[str, str]:
    service = AuroraStage40CalendarKillSwitchService()
    await service.set_mode(mode)
    return {"mode": await service.get_mode()}


SPECS = {
    "stage18": DrillSpec(
        name="stage18",
        stage="18",
        description="Aggregator / push policy / push delivery",
        mode_keys=("aggregator_enabled", "push_policy_enabled", "push_delivery_enabled"),
        apply_mode=_stage18_apply,
    ),
    "stage19": DrillSpec(
        name="stage19",
        stage="19",
        description="Working memory / LLM extractor / consolidation",
        mode_keys=("working_memory_enabled", "llm_extractor_enabled", "consolidation_enabled"),
        apply_mode=_stage19_apply,
    ),
    "stage21": DrillSpec(
        name="stage21",
        stage="21",
        description="Skill store / selection / share",
        mode_keys=("skill_store_enabled", "skill_selection_enabled", "skill_share_enabled"),
        apply_mode=_stage21_apply,
    ),
    "stage23": DrillSpec(
        name="stage23",
        stage="23",
        description="Bayesian router mode",
        mode_keys=("bayesian_mode",),
        apply_mode=_stage23_apply,
    ),
    "stage24": DrillSpec(
        name="stage24",
        stage="24",
        description="Policy compiler mode",
        mode_keys=("policy_compiler_mode",),
        apply_mode=_stage24_apply,
    ),
    "stage25": DrillSpec(
        name="stage25",
        stage="25",
        description="Reflection wire mode",
        mode_keys=("reflection_wire_mode",),
        apply_mode=_stage25_apply,
    ),
    "stage26": DrillSpec(
        name="stage26",
        stage="26",
        description="Scene mode",
        mode_keys=("mode",),
        apply_mode=_stage26_apply,
    ),
    "stage27": DrillSpec(
        name="stage27",
        stage="27",
        description="Foresight master + child modes",
        mode_keys=("mode", "attractor", "deviation", "jitai"),
        apply_mode=_stage27_apply,
    ),
    "stage28": DrillSpec(
        name="stage28",
        stage="28",
        description="Traits master + NLP + coldstart",
        mode_keys=("mode", "nlp_mode", "coldstart_mode"),
        apply_mode=_stage28_apply,
    ),
    "stage29": DrillSpec(
        name="stage29",
        stage="29",
        description="SRL master + tracker + bridge + scaffolding",
        mode_keys=("mode", "tracker_mode", "bridge_mode", "scaffolding_consume_mode"),
        apply_mode=_stage29_apply,
    ),
    "stage30": DrillSpec(
        name="stage30",
        stage="30",
        description="Metacognition master + dashboard + process scaffolding + FSM combine",
        mode_keys=("mode", "dashboard", "process_scaffolding", "fsm_combine"),
        apply_mode=_stage30_apply,
    ),
    "stage31": DrillSpec(
        name="stage31",
        stage="31",
        description="Idiographic mode",
        mode_keys=("mode",),
        apply_mode=_stage31_apply,
    ),
    "stage33": DrillSpec(
        name="stage33",
        stage="33",
        description="Stage 33 master + social/srl/wm_prompt/events",
        mode_keys=("mode", "social", "srl", "wm_prompt", "events"),
        apply_mode=_stage33_apply,
    ),
    "stage34": DrillSpec(
        name="stage34",
        stage="34",
        description="Stage 34 master + error_bridge/capsule/journey_subscribers",
        mode_keys=("mode", "error_bridge_mode", "capsule_mode", "journey_subscribers_enabled"),
        apply_mode=_stage34_apply,
    ),
    "stage35": DrillSpec(
        name="stage35",
        stage="35",
        description="Stage 35 master + metacog_router",
        mode_keys=("mode", "metacog_router_mode"),
        apply_mode=_stage35_apply,
    ),
    "stage37": DrillSpec(
        name="stage37",
        stage="37",
        description="LLM safety mode",
        mode_keys=("mode",),
        apply_mode=_stage37_apply,
    ),
    "stage38": DrillSpec(
        name="stage38",
        stage="38",
        description="Stage 38 err_replan + push_scheduler",
        mode_keys=("err_replan_mode", "push_scheduler_mode"),
        apply_mode=_stage38_apply,
    ),
    "stage39": DrillSpec(
        name="stage39",
        stage="39",
        description="Stage 39 master + scaffolding_prompt/cogload_route/galaxy_inject",
        mode_keys=("mode", "scaffolding_prompt_mode", "cogload_route_mode", "galaxy_inject_mode"),
        apply_mode=_stage39_apply,
    ),
    "dual_core_router": DrillSpec(
        name="dual_core_router",
        stage="dual_core_router",
        description="Dual-core router mode",
        mode_keys=("mode",),
        apply_mode=_dual_core_router_apply,
    ),
    "privacy": DrillSpec(
        name="privacy",
        stage="privacy",
        description="PII redaction mode",
        mode_keys=("pii_redaction_mode",),
        apply_mode=_privacy_apply,
    ),
    "doc_context": DrillSpec(
        name="doc_context",
        stage="doc_context",
        description="Document context injection",
        mode_keys=("mode",),
        apply_mode=_doc_context_apply,
    ),
    "stage40-calendar": DrillSpec(
        name="stage40-calendar",
        stage="40",
        description="Calendar prompt mode",
        mode_keys=("mode",),
        apply_mode=_stage40_apply,
    ),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Stage40 kill-switch drill transitions.")
    parser.add_argument(
        "--only",
        action="append",
        dest="only",
        help="Run a single drill spec by name. Can be supplied multiple times.",
    )
    return parser.parse_args()


def _validate_mode(summary: dict[str, Any], expected_mode: str, keys: tuple[str, ...]) -> None:
    mismatches = {
        key: summary.get(key)
        for key in keys
        if str(summary.get(key)) != expected_mode
    }
    if mismatches:
        raise RuntimeError(
            f"mode validation failed for {expected_mode}: {json.dumps(mismatches, ensure_ascii=False, sort_keys=True)}"
        )


async def _run_spec(spec: DrillSpec, audit_file: Path) -> None:
    previous = "bootstrap"
    for mode in TRANSITIONS:
        summary = await spec.apply_mode(mode)
        _validate_mode(summary, mode, spec.mode_keys)
        record = {
            "stage": spec.stage,
            "name": spec.name,
            "description": spec.description,
            "from": previous,
            "to": mode,
            "summary": summary,
            "audited_at": _utcnow_iso(),
        }
        with audit_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"[Stage40 Drill] {spec.name}: {previous} -> {mode}")
        previous = mode


async def _main() -> int:
    args = _parse_args()
    selected = args.only or list(DEFAULT_SPECS)
    unknown = [name for name in selected if name not in SPECS]
    if unknown:
        raise SystemExit(f"unknown drill spec(s): {', '.join(sorted(unknown))}")

    audit_dir = REPO_ROOT / "artifacts" / "stage40"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / "kill_switch_drill_audit.jsonl"
    if not args.only:
        audit_file.write_text("", encoding="utf-8")

    for name in selected:
        await _run_spec(SPECS[name], audit_file)

    print(f"[Stage40 Drill] PASS audit_file={audit_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
