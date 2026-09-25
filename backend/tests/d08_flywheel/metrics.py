"""D-08 · raw → paired/dashboard 确定性指标计算（纯函数；模型 judge 零使用）。

纪律与 A-08 同源：summary/dashboard 的每个数字都从 raw 记录程序化复算；
判据全部确定性规则（无模型评分）；口径冻结在 ``D08_METRICS_VERSION``。

三类核心判定（全部纯函数、可单测）：

1. **paired result**：同臂 Day0 vs Day3/Day7 逐面配对差（understanding 五维 /
   memory / intervention / outcome / personalization）；
2. **adaptation 因果链**：事件（Day1/Day4）→ 服务读侧证据 → 与 no_feedback
   臂同日探针的行为差分，三段齐备才 ``established``；行为真的变了才
   ``behavior_changed``；
3. **无效/无效力个性化台账**：applied 但零差分的 patch、把匹配分带差的纠正、
   记忆否认后旧偏好仍被注入——保留不筛（验收红线）。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from tests.d08_flywheel.protocol import (
    D08_SPEC_VERSION,
    FLYWHEEL_ARMS,
    PROBE_DAYS,
    STALE_KEY,
    build_population,
)

__all__ = [
    "D08_METRICS_VERSION",
    "adaptation_chains",
    "extract_invalid_personalization",
    "build_persona_paired",
    "summarize_population",
]

D08_METRICS_VERSION = "d08_flywheel_metrics.v1"

_DIMENSIONS = ("coverage", "correctness", "scope_precision", "freshness", "utility")

_MATCH_SCORE = {"primary": 1.0, "secondary": 0.5, "wrong": 0.0}


# ---------------------------------------------------------------------------
# 1. adaptation 因果链（事件 → 读侧证据 → 行为差分）
# ---------------------------------------------------------------------------


def _probes_by_day(records: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(r["sim_day"]): r for r in records if r.get("kind") == "probe"}


def _events(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if r.get("kind") == "event"]


def _journey_face(probe: dict[str, Any]) -> dict[str, Any]:
    return ((probe.get("faces") or {}).get("intervention") or {}).get("journey") or {}


def _chat_face(probe: dict[str, Any]) -> dict[str, Any]:
    return ((probe.get("faces") or {}).get("intervention") or {}).get("chat") or {}


def adaptation_chains(
    *,
    events: list[dict[str, Any]],
    flywheel_probes: list[dict[str, Any]],
    control_probes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """从 raw 事件与双臂探针提取 adaptation 因果链（每事件类一条候选链）。

    ``established`` = 事件 + 服务读侧证据齐备；``behavior_changed`` = 与
    no_feedback 臂同日探针相比行为真的变了（差分判据，配对因果）。
    """
    fly = _probes_by_day(flywheel_probes)
    ctl = _probes_by_day(control_probes)
    chains: list[dict[str, Any]] = []

    def _behavior_diff(day: int, face: str, field: str) -> tuple[bool, Any, Any]:
        f_probe = fly.get(day) or {}
        c_probe = ctl.get(day) or {}
        getter = _journey_face if face == "journey" else _chat_face
        after = getter(f_probe).get(field)
        before = getter(c_probe).get(field)
        return (after != before), before, after

    for event in events:
        etype = event.get("event_type")
        if etype == "journey_correction":
            correction_id = event.get("correction_id")
            if not correction_id:
                continue  # skipped 事件（诊断与真值一致，未落纠正）不进链
            read_evidence: dict[str, Any] | None = None
            for day in PROBE_DAYS:
                if day <= int(event.get("sim_day") or 0):
                    continue
                jf = _journey_face(fly.get(day) or {})
                if correction_id in (jf.get("applied_correction_ids") or []) or jf.get(
                    "adjusted_by_correction"
                ):
                    read_evidence = {
                        "probe_day": day,
                        "applied_correction_ids": list(jf.get("applied_correction_ids") or []),
                        "adjusted_by_correction": bool(jf.get("adjusted_by_correction")),
                        "active_corrections": int(jf.get("active_corrections") or 0),
                    }
                    break
            chain: dict[str, Any] = {
                "chain_type": "journey_correction",
                "event": event,
                "read_evidence": read_evidence,
                "established": read_evidence is not None,
            }
            if read_evidence is not None:
                day = int(read_evidence["probe_day"])
                changed, before, after = _behavior_diff(day, "journey", "friction_type")
                chain["behavior_changed"] = bool(changed)
                chain["behavior_before_no_feedback"] = before
                chain["behavior_after_flywheel"] = after
                chain["probe_day"] = day
            else:
                chain["behavior_changed"] = False
            chains.append(chain)
        elif etype == "patch_proposal" and event.get("patch_id"):
            patch_id = str(event["patch_id"])
            confirmed = (event.get("confirmation") or {}).get("state") == "active"
            read_evidence = None
            for day in PROBE_DAYS:
                if day <= int(event.get("sim_day") or 0):
                    continue
                cf = _chat_face(fly.get(day) or {})
                if patch_id in (cf.get("applied_patch_ids") or []):
                    read_evidence = {
                        "probe_day": day,
                        "applied_patch_ids": list(cf.get("applied_patch_ids") or []),
                        "patch_moves": list(cf.get("patch_moves") or []),
                    }
                    break
            # applied_patch_ids 只含 active（effective）patch——读侧证据本身
            # 即证明 patch 已激活并被决策输入真实消费。
            chain = {
                "chain_type": "policy_patch",
                "event": event,
                "confirmed_active": confirmed,
                "read_evidence": read_evidence,
                "established": read_evidence is not None,
            }
            if read_evidence is not None:
                day = int(read_evidence["probe_day"])
                changed, before, after = _behavior_diff(day, "chat", "selected")
                chain["behavior_changed"] = bool(changed)
                chain["behavior_before_no_feedback"] = before
                chain["behavior_after_flywheel"] = after
                chain["probe_day"] = day
            else:
                chain["behavior_changed"] = False
            chains.append(chain)
        elif etype == "memory_reference_outcome" and event.get("outcome") == "denied":
            read_evidence = None
            for day in PROBE_DAYS:
                if day <= int(event.get("sim_day") or 0):
                    continue
                pack = (((fly.get(day) or {}).get("faces") or {}).get("memory") or {}).get("pack") or {}
                ctl_pack = (((ctl.get(day) or {}).get("faces") or {}).get("memory") or {}).get("pack") or {}
                read_evidence = {
                    "probe_day": day,
                    "flywheel_stale_surfaced": bool(pack.get("stale_surfaced")),
                    "no_feedback_stale_surfaced": bool(ctl_pack.get("stale_surfaced")),
                    "flywheel_stale_row": pack.get("stale_row"),
                }
                break
            chain = {
                "chain_type": "memory_quieter",
                "event": event,
                "read_evidence": read_evidence,
                "established": read_evidence is not None,
            }
            if read_evidence is not None:
                day = int(read_evidence["probe_day"])
                pack = (((fly.get(day) or {}).get("faces") or {}).get("memory") or {}).get("pack") or {}
                ctl_pack = (((ctl.get(day) or {}).get("faces") or {}).get("memory") or {}).get("pack") or {}
                changed = bool(pack.get("stale_surfaced")) != bool(ctl_pack.get("stale_surfaced")) or (
                    pack.get("stale_position") != ctl_pack.get("stale_position")
                )
                chain["behavior_changed"] = bool(changed)
                chain["behavior_before_no_feedback"] = {
                    "stale_surfaced": bool(ctl_pack.get("stale_surfaced")),
                    "stale_position": ctl_pack.get("stale_position"),
                }
                chain["behavior_after_flywheel"] = {
                    "stale_surfaced": bool(pack.get("stale_surfaced")),
                    "stale_position": pack.get("stale_position"),
                }
                chain["probe_day"] = day
            else:
                chain["behavior_changed"] = False
            chains.append(chain)
    return chains


def extract_invalid_personalization(
    *,
    events: list[dict[str, Any]],
    flywheel_probes: list[dict[str, Any]],
    control_probes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """无效/无效力个性化台账（保留不剪；逐条可引用到 raw 行）。"""
    fly = _probes_by_day(flywheel_probes)
    ctl = _probes_by_day(control_probes)
    invalid: list[dict[str, Any]] = []
    chains = adaptation_chains(
        events=events, flywheel_probes=flywheel_probes, control_probes=control_probes
    )
    for chain in chains:
        if chain["chain_type"] == "policy_patch" and chain.get("established") and not chain.get(
            "behavior_changed"
        ):
            invalid.append(
                {
                    "kind": "ineffective_patch",
                    "patch_id": (chain.get("event") or {}).get("patch_id"),
                    "probe_day": chain.get("probe_day"),
                    "note": "patch 已激活并被决策输入读取，但被选干预与无反馈对照相同（改序不改局）",
                }
            )
        if chain["chain_type"] == "memory_quieter" and chain.get("established") and not chain.get(
            "behavior_changed"
        ):
            invalid.append(
                {
                    "kind": "memory_not_quieter",
                    "pref_key": STALE_KEY,
                    "probe_day": chain.get("probe_day"),
                    "note": "旧偏好被否认后仍以同位注入——记忆未变安静",
                }
            )
        if chain["chain_type"] == "journey_correction" and chain.get("behavior_changed"):
            day = int(chain.get("probe_day") or 0)
            f_probe = fly.get(day) or {}
            c_probe = ctl.get(day) or {}
            fw_score = _journey_match_score(f_probe)
            ctl_score = _journey_match_score(c_probe)
            if fw_score is not None and ctl_score is not None and fw_score < ctl_score:
                invalid.append(
                    {
                        "kind": "harmful_correction_differential",
                        "probe_day": day,
                        "flywheel_match": fw_score,
                        "no_feedback_match": ctl_score,
                        "note": "纠正垫后使旅程面匹配分低于无反馈对照（有害适应，保留）",
                    }
                )
    for chain in chains:
        if chain["chain_type"] == "journey_correction" and not chain.get("established"):
            invalid.append(
                {
                    "kind": "correction_not_read",
                    "correction_id": (chain.get("event") or {}).get("correction_id"),
                    "note": "纠正落库但后续探针未见读侧证据（freshness 窗口外或无 act 出口）",
                }
            )
    # patch 已激活但从未被任何后续探针的决策输入消费（chat 结构性不可服务
    # 的 tag 上 prefer patch 无权发力——A-08 V3-FIX-51 同族）。
    for event in events:
        if event.get("event_type") != "patch_proposal" or not event.get("patch_id"):
            continue
        patch_id = str(event["patch_id"])
        applied_anywhere = any(
            patch_id in (_chat_face(fly.get(day) or {}).get("applied_patch_ids") or [])
            for day in PROBE_DAYS
            if day > int(event.get("sim_day") or 0)
        )
        if (event.get("confirmation") or {}).get("state") == "active" and not applied_anywhere:
            invalid.append(
                {
                    "kind": "patch_never_applied",
                    "patch_id": patch_id,
                    "prefer_intervention": event.get("prefer_intervention"),
                    "note": "patch 已激活但后续探针零消费（chat 面对该 tag 结构性 no_action）",
                }
            )
    return invalid


def _journey_match_score(probe: dict[str, Any]) -> float | None:
    """旅程面自身干预对真值的规则分（raw 探针面携带 journey_match）。"""
    value = ((probe.get("faces") or {}).get("intervention") or {}).get("journey_match")
    return _MATCH_SCORE.get(str(value)) if value is not None else None


# ---------------------------------------------------------------------------
# 2. paired result（同臂 Day0 vs Day3/7 逐面配对差）
# ---------------------------------------------------------------------------


def _dim_delta(day0: dict[str, Any], day7: dict[str, Any]) -> str:
    s0, s7 = day0.get("status"), day7.get("status")
    v7 = day7.get("value")
    tail = f"({v7})" if s7 == "ok" else ""
    return f"{s0}->{s7}{tail}"


def build_persona_paired(
    *,
    persona_id: str,
    flywheel_records: list[dict[str, Any]],
    control_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """一个 persona 的 Day0/3/7 配对结果 + adaptation 链 + 无效台账。"""
    fly = _probes_by_day(flywheel_records)
    ctl_records = control_records or []
    probe0 = fly.get(PROBE_DAYS[0]) or {}
    probe3 = fly.get(PROBE_DAYS[1]) or {}
    probe7 = fly.get(PROBE_DAYS[2]) or {}

    faces: dict[str, Any] = {}
    dims0 = ((probe0.get("faces") or {}).get("understanding") or {}).get("dimensions") or {}
    dims3 = ((probe3.get("faces") or {}).get("understanding") or {}).get("dimensions") or {}
    dims7 = ((probe7.get("faces") or {}).get("understanding") or {}).get("dimensions") or {}
    faces["understanding"] = {
        dim: {
            "day0": dims0.get(dim),
            "day3": dims3.get(dim),
            "day7": dims7.get(dim),
            "delta_day7_vs_day0": _dim_delta(dims0.get(dim) or {}, dims7.get(dim) or {}),
        }
        for dim in _DIMENSIONS
    }

    def _memory_of(probe: dict[str, Any]) -> dict[str, Any]:
        face = (probe.get("faces") or {}).get("memory") or {}
        pack = face.get("pack") or {}
        return {
            "surfaced_count": pack.get("surfaced_count"),
            "stale_surfaced": pack.get("stale_surfaced"),
            "stale_position": pack.get("stale_position"),
            "stale_confidence": (pack.get("stale_row") or {}).get("confidence"),
            "reference_denied_total": ((face.get("reference_outcomes") or {}).get("denied")),
            "retractions": face.get("retractions"),
        }

    m0, m3, m7 = _memory_of(probe0), _memory_of(probe3), _memory_of(probe7)
    faces["memory"] = {
        "day0": m0,
        "day3": m3,
        "day7": m7,
        "delta_day7_vs_day0": {
            "stale_surfaced": _bool_delta(m0.get("stale_surfaced"), m7.get("stale_surfaced")),
            "stale_confidence": _num_delta(m0.get("stale_confidence"), m7.get("stale_confidence")),
        },
    }

    def _intervention_of(probe: dict[str, Any]) -> dict[str, Any]:
        face = (probe.get("faces") or {}).get("intervention") or {}
        return {
            "chat_selected": _chat_face(probe).get("selected"),
            "journey_friction": _journey_face(probe).get("friction_type"),
            "journey_intervention": _journey_face(probe).get("intervention"),
            "followed": (face.get("followed") or {}).get("intervention"),
            "followed_surface": (face.get("followed") or {}).get("surface"),
            "match_class": face.get("match_class"),
            "journey_adjusted_by_correction": _journey_face(probe).get("adjusted_by_correction"),
            "chat_applied_patch_ids": list(_chat_face(probe).get("applied_patch_ids") or []),
        }

    i0, i3, i7 = _intervention_of(probe0), _intervention_of(probe3), _intervention_of(probe7)
    faces["intervention"] = {
        "day0": i0,
        "day3": i3,
        "day7": i7,
        "delta_day7_vs_day0": {
            "match_class": _str_delta(i0.get("match_class"), i7.get("match_class")),
            "followed": _str_delta(i0.get("followed"), i7.get("followed")),
        },
    }

    def _outcome_of(probe: dict[str, Any]) -> dict[str, Any]:
        return {"associations_total": ((probe.get("faces") or {}).get("outcome") or {}).get("associations_total")}

    o0, o3, o7 = _outcome_of(probe0), _outcome_of(probe3), _outcome_of(probe7)
    faces["outcome"] = {
        "day0": o0,
        "day3": o3,
        "day7": o7,
        "delta_day7_vs_day0": (o7.get("associations_total") or 0) - (o0.get("associations_total") or 0),
    }

    def _personalization_of(probe: dict[str, Any]) -> dict[str, Any]:
        face = (probe.get("faces") or {}).get("personalization") or {}
        return {
            "active_patches": face.get("active_patches"),
            "corrections_filed": face.get("corrections_filed"),
            "journey_active_corrections": _journey_face(probe).get("active_corrections"),
        }

    p0, p3, p7 = _personalization_of(probe0), _personalization_of(probe3), _personalization_of(probe7)
    faces["personalization"] = {
        "day0": p0,
        "day3": p3,
        "day7": p7,
        "delta_day7_vs_day0": {
            "active_patches": _num_delta(p0.get("active_patches"), p7.get("active_patches")),
            "corrections_filed": _num_delta(p0.get("corrections_filed"), p7.get("corrections_filed")),
        },
    }

    events = _events(flywheel_records)
    chains = adaptation_chains(
        events=events,
        flywheel_probes=flywheel_records,
        control_probes=ctl_records,
    )
    invalid = extract_invalid_personalization(
        events=events,
        flywheel_probes=flywheel_records,
        control_probes=ctl_records,
    )
    # 对照侵入（over-personalization 护栏）。
    intrusions = {
        arm: [
            int(r.get("sim_day") or 0)
            for r in (flywheel_records if arm == "flywheel" else ctl_records)
            if r.get("kind") == "control" and r.get("control_intrusion")
        ]
        for arm in FLYWHEEL_ARMS
    }
    established = [c for c in chains if c.get("established")]
    changed = [c for c in established if c.get("behavior_changed")]
    return {
        "persona_id": persona_id,
        "faces": faces,
        "adaptation_chains": chains,
        "acceptance": {
            "passed": bool(changed),
            "via": [c["chain_type"] for c in changed],
            "established_count": len(established),
        },
        "invalid_personalization": invalid,
        "control_intrusions": intrusions,
    }


# ---------------------------------------------------------------------------
# 3. population summary + dashboard（全由 raw 程序化复算）
# ---------------------------------------------------------------------------


def summarize_population(raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """全人口 dashboard 载荷（配对表 + 链 + 无效台账 + 护栏）。"""
    per_persona: dict[str, Any] = {}
    by_persona_arm: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for arm in FLYWHEEL_ARMS:
        for r in raw.get(arm, []):
            by_persona_arm[str(r.get("persona"))][arm].append(r)
    for spec in build_population():
        pid = spec.persona_id
        per_persona[pid] = build_persona_paired(
            persona_id=pid,
            flywheel_records=by_persona_arm[pid]["flywheel"],
            control_records=by_persona_arm[pid]["no_feedback"],
        )

    passed = [pid for pid, p in per_persona.items() if p["acceptance"]["passed"]]
    invalid_total = sum(len(p["invalid_personalization"]) for p in per_persona.values())
    chain_counts: dict[str, int] = {}
    for p in per_persona.values():
        for c in p["adaptation_chains"]:
            if c.get("established") and c.get("behavior_changed"):
                chain_counts[c["chain_type"]] = chain_counts.get(c["chain_type"], 0) + 1

    # fleet 级五维 Day0 vs Day7（各维状态迁移计数，程序化聚合）。
    dim_transitions: dict[str, dict[str, int]] = {dim: defaultdict(int) for dim in _DIMENSIONS}
    match_day0: list[float] = []
    match_day7: list[float] = []
    for p in per_persona.values():
        for dim in _DIMENSIONS:
            d0 = p["faces"]["understanding"][dim]["day0"] or {}
            d7 = p["faces"]["understanding"][dim]["day7"] or {}
            dim_transitions[dim][f"{d0.get('status')}->{d7.get('status')}"] += 1
        mc0 = p["faces"]["intervention"]["day0"].get("match_class")
        mc7 = p["faces"]["intervention"]["day7"].get("match_class")
        if mc0 in _MATCH_SCORE:
            match_day0.append(_MATCH_SCORE[mc0])
        if mc7 in _MATCH_SCORE:
            match_day7.append(_MATCH_SCORE[mc7])

    return {
        "spec_version": D08_SPEC_VERSION,
        "metrics_version": D08_METRICS_VERSION,
        "population": [s.persona_id for s in build_population()],
        "acceptance": {
            "personas_passed": len(passed),
            "personas_total": len(per_persona),
            "passed_ids": passed,
            "chain_type_counts": chain_counts,
        },
        "invalid_personalization_total": invalid_total,
        "fleet": {
            "understanding_dim_status_transitions_day0_to_day7": {
                dim: dict(transitions) for dim, transitions in dim_transitions.items()
            },
            "followed_match_mean_day0": _mean(match_day0),
            "followed_match_mean_day7": _mean(match_day7),
        },
        "per_persona": per_persona,
        "notes": {
            "determinism": "全部数字由 raw 程序化复算；模型 judge 0 次",
            "invalid_kept": "无效/有害个性化保留在 per_persona.invalid_personalization，不筛除",
        },
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _bool_delta(before: Any, after: Any) -> str:
    return f"{bool(before)}->{bool(after)}"


def _num_delta(before: Any, after: Any) -> float | int | None:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return round(after - before, 4)
    return None


def _str_delta(before: Any, after: Any) -> str | None:
    if before is None and after is None:
        return None
    return f"{before}->{after}"
