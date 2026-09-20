"""C-05 · Conflict Resolver 注入 Context 与 Clarification（CONTEXT stream）。

把冲突裁决结果变成 ContextPack 的合法注入面：模型/下游能读到
「哪些事实已裁决（winner 是谁、为什么）」和「哪些仍是已知分歧（两边说法、
是否值得追问）」，而不是把冲突原文整段塞进 prompt。

边界纪律（勿越界"修复"）：
- 本模块是**纯消费面**：zero I/O、zero LLM、不重建任何裁决权威。
  resolved 面来自 context_pack 已跑完的 ``MemoryConflictResolver``（M-04 前身
  语义 + V3-FIX-35 supersede 链归因）；unresolved 面来自 M-04
  ``ConflictResolverService.list_unresolved_conflicts``（ask_once 落库行）。
  本模块只做形状转换、materiality 判定与确定性澄清问句生成。
- winner 语义不稀释：resolved 条目恒以 winner 为主句、loser 以「已知分歧/
  已被取代」从句表述，绝不把两侧写成等价备选。
- 确定性：同输入恒同输出（排序、digest 截断、模板文案全部封闭）；
  澄清问句是模板生成，不复读冲突原文，也不复用 M-04 的静态问句常量。
- materiality（卡面：SufficiencyChecker 只对会改变 decision 的冲突提问）：
  只有 **未裁决**（status=pending_user，用户答案才可能改变事实）且
  （UNSAFE_AMBIGUITY 高风险 or 与当前 query 相关）的冲突才 material；
  已裁决事实与 preserve-both（scope 不同、两边都真）永不提问。
"""

from __future__ import annotations

import json
import re
from typing import Any

CONFLICT_RESOLUTION_CONTEXT_VERSION = "context-v3.c05.conflict.v1"

# prompt 注入面预算：避免把冲突文本全部塞进去（卡面 objective）。
# 实测（cl100k，最坏 32 字 CJK digest 满额）：prompt_note ≈ 700-900 tokens、
# 结构化条目只进进程内消费面，不整包进 prompt（to_prompt_payload 有界投影）。
PROMPT_NOTE_MAX_RESOLVED = 3
PROMPT_NOTE_MAX_UNRESOLVED = 2
DIGEST_MAX_CHARS = 32
MATERIAL_QUERY_OVERLAP_MIN = 1
#: context_pack 一次构建最多取回的 M-04 未裁决冲突行数（surfaced_at 最新优先，
#: 由 list_unresolved_conflicts 的 ORDER BY 保证）。
UNRESOLVED_FETCH_LIMIT = 5

#: pack 级 ConflictNote.type 封闭词表（MemoryConflictResolver 产出；测试冻结）。
PACK_NOTE_KINDS = ("preference", "goal", "episodic", "cross_type")

#: resolved 归因短语封闭表——reason code → 人类可读裁决归因。测试逐字冻结。
RESOLUTION_REASON_PHRASES: dict[str, str] = {
    "supersede_chain_head": "用户随后更新过此项，以取代链链头为准",
    "evidence_score": "以证据更强的记录为准",
    "updated_at": "以更新时间较新的记录为准",
    "confidence": "以置信度更高的记录为准",
    "tie_break_latest": "各项持平，以最新记录为准",
    "duplicate_title_overlap": "同名目标重叠，保留证据更强的一条",
    "similar_summary": "内容重复的回忆，保留更完整的一条",
    "goal_in_episodic": "目标与回忆记录重复，保留证据更强的一条",
}
_FALLBACK_REASON_PHRASE = "按冲突裁决规则保留该项"

#: M-04 ConflictCategory 字面值（测试与 app.services.conflict_resolver_service
#: 的枚举逐字对齐；此处不 import 以保持模块 stdlib-pure、零环）。
_CATEGORY_UNSAFE = "UNSAFE_AMBIGUITY"
_CATEGORY_SCOPE = "SCOPE_DIFFERENCE"

#: 澄清问句模板（按类别封闭）。确定性生成，不复读冲突原文。
CLARIFICATION_CATEGORY_STEMS: dict[str, str] = {
    "UNSAFE_AMBIGUITY": "我的记录里有两种相互矛盾的说法，需要你确认现在哪一种符合实际情况",
    "SOURCE_DISAGREEMENT": "你自己提到的和系统记录的情况不一致，需要你确认哪一边是对的",
    "TEMPORAL_CHANGE": "新旧记录的说法不一样，需要你确认现在的实际情况",
    "INFERENCE_CONTRADICTION": "记录里有事实和推断相互矛盾，需要你确认事实层面到底是什么",
}
_CLARIFICATION_FALLBACK_STEM = "有两种不一致的记录，需要你确认哪种符合现在的实际情况"

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+")


def digest_text(text: str, max_chars: int = DIGEST_MAX_CHARS) -> str:
    """确定性 digest：折叠空白 + 截断。摘要注入面统一走这里（防 token 失控）。"""
    collapsed = " ".join(str(text or "").split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 1].rstrip() + "…"


def _pref_display(value: Any) -> str:
    if isinstance(value, dict) and set(value.keys()) == {"value"}:
        return str(value.get("value"))
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)


def build_record_index(
    preferences: list[Any],
    goals: list[Any],
    episodes: list[Any],
) -> dict[str, dict[str, Any]]:
    """record_id → 展示描述符（display/confidence/kind）。

    纯读取：input 是 context_pack 已裁决的 record 对象，本函数不参与裁决。
    """
    index: dict[str, dict[str, Any]] = {}
    for record in preferences:
        index[str(record.id)] = {
            "kind": "preference",
            "display": digest_text(_pref_display(getattr(record, "pref_value", None))),
            "confidence": getattr(record, "confidence", None),
        }
    for goal in goals:
        index[str(goal.id)] = {
            "kind": "goal",
            "display": digest_text(getattr(goal, "title", "")),
            "confidence": getattr(goal, "evidence_score", None),
        }
    for episode in episodes:
        index[str(episode.id)] = {
            "kind": "episodic",
            "display": digest_text(getattr(episode, "summary", "")),
            "confidence": getattr(episode, "evidence_score", None),
        }
    return index


def attribution_phrase(reason: str) -> str:
    return RESOLUTION_REASON_PHRASES.get(reason, _FALLBACK_REASON_PHRASE)


def _tokens(text: str) -> set[str]:
    """确定性相关性 token：ASCII 词元 + CJK 二元组（连续汉字按 bigram 切——
    整句匹配会让「晚上能学多久」与「我晚上能学习」零重叠，中文 query 相关性
    门控失效）。"""
    tokens: set[str] = set()
    for run in _TOKEN_RE.findall(str(text or "").lower()):
        if run.isascii() or len(run) == 1:
            tokens.add(run)
        else:
            tokens.update(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def assess_materiality(
    *,
    status: str,
    category: str,
    query_text: str | None,
    side_texts: list[str],
) -> dict[str, Any]:
    """决定「是否值得问」的确定性规则（只对会改变 decision 的冲突提问）。

    - 已裁决（任何终态）→ 永不提问：提问不改变任何事实。
    - SCOPE_DIFFERENCE → 永不提问：两边都真（preserve-both），无「改写决策」
      的二选一。
    - UNSAFE_AMBIGUITY → material：M-04 对高风险分歧 refuse-to-pick，继续
      决策风险大（CONFLICT_RESOLVER.md §4/§5）。
    - 其余未裁决 → 与当前 query 存在 token 重叠才 material（与本轮决策相关，
      用户答案才可能改变本轮 decision）；无关冲突静默不问（降 clarification
      率 = 卡面验收）。
    """
    if status != "pending_user":
        return {"material": False, "reason_code": "already_resolved"}
    if category == _CATEGORY_SCOPE:
        return {"material": False, "reason_code": "both_sides_valid_different_scope"}
    if category == _CATEGORY_UNSAFE:
        return {"material": True, "reason_code": "unsafe_ambiguity_high_risk"}
    query_tokens = _tokens(query_text or "")
    if query_tokens:
        side_tokens: set[str] = set()
        for text in side_texts:
            side_tokens |= _tokens(text)
        overlap = query_tokens & side_tokens
        if len(overlap) >= MATERIAL_QUERY_OVERLAP_MIN:
            return {
                "material": True,
                "reason_code": "query_relevant",
                "overlap_tokens": sorted(overlap)[:8],
            }
        return {"material": False, "reason_code": "not_query_relevant"}
    # 无 query 上下文（如后台构建）：仅 UNSAFE_AMBIGUITY 已放行，其余不问。
    return {"material": False, "reason_code": "no_query_context"}


def build_clarification_question(
    *,
    category: str,
    left_digest: str,
    right_digest: str,
) -> str:
    """确定性澄清问句：类别模板 + 双侧 labeled digest + 封闭选项结构。

    不复读冲突原文（stem 是模板文本、digest 是归一截断），也不是 M-04 落库
    的静态问句常量（两条记录对同一件事的说法不一致……）。
    """
    stem = CLARIFICATION_CATEGORY_STEMS.get(category, _CLARIFICATION_FALLBACK_STEM)
    return f"{stem}。A：{left_digest}；B：{right_digest}。" "请回复 A 或 B（如果都不对，直接告诉我实际情况即可）。"


def serialize_unresolved_for_context(
    row: Any,
    query_text: str | None,
) -> dict[str, Any]:
    """M-04 UnresolvedConflict 行 → 注入面条目（纯函数，鸭子类型零依赖）。

    category 缺省时按 UNSAFE_AMBIGUITY 处理：M-04 ask_once 只在平级 tie
    （UNSAFE_AMBIGUITY）触发，语义一致；旧行缺 clarification payload 时不失真。
    """
    left_payload = row.left_payload if isinstance(row.left_payload, dict) else {}
    clarification = left_payload.get("clarification")
    clarification = clarification if isinstance(clarification, dict) else {}
    category = str(clarification.get("conflict_category") or _CATEGORY_UNSAFE)

    left_summary = str(row.left_summary or "")
    right_summary = str(row.right_summary or "")
    left_digest = digest_text(left_summary)
    right_digest = digest_text(right_summary)

    materiality = assess_materiality(
        status=str(row.status or ""),
        category=category,
        query_text=query_text,
        side_texts=[left_summary, right_summary],
    )
    material = bool(materiality["material"])

    entry: dict[str, Any] = {
        "conflict_id": str(row.id),
        "conflict_key": str(row.conflict_key or ""),
        "status": str(row.status or ""),
        "category": category,
        "left": {
            "record_id": str(row.left_record_id) if row.left_record_id else None,
            "digest": left_digest,
            "lane": str(row.left_lane or ""),
        },
        "right": {
            "record_id": str(row.right_record_id) if row.right_record_id else None,
            "digest": right_digest,
            "lane": str(row.right_lane or ""),
        },
        "surfaced_at": row.surfaced_at.isoformat() if getattr(row, "surfaced_at", None) else None,
        "ask_if_material": material,
        "materiality": materiality,
        "clarification_question": (
            build_clarification_question(
                category=category,
                left_digest=left_digest,
                right_digest=right_digest,
            )
            if material
            else None
        ),
    }
    return entry


def _display_key(kind: str, key: str) -> str:
    # episodic/cross_type 的 note key 是 uuid/hash —— 对人不可读，降级为类目词。
    if kind in {"episodic", "cross_type"}:
        return {"episodic": "一段回忆", "cross_type": "目标与回忆"}[kind]
    return key


def _kind_label(kind: str) -> str:
    return {"preference": "偏好", "goal": "目标", "episodic": "回忆", "cross_type": "交叉记录"}.get(
        kind,
        "记录",
    )


def _resolved_fact_entry(note: dict[str, Any], record_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    kind = str(note.get("type") or "")
    reason = str(note.get("reason") or "")
    winner_ids = [str(item) for item in (note.get("winners") or [])]
    loser_ids = [str(item) for item in (note.get("suppressed") or [])]
    winner = winner_ids[0] if winner_ids else ""
    winner_info = record_index.get(winner) or {}
    loser_displays = [record_index[loser]["display"] for loser in loser_ids if loser in record_index]
    return {
        "kind": kind,
        "key": str(note.get("key") or ""),
        "winner_id": winner,
        "winner_display": winner_info.get("display") or None,
        "loser_ids": loser_ids,
        "loser_displays": loser_displays,
        "reason_code": reason,
        "attribution": attribution_phrase(reason),
        "confidence": winner_info.get("confidence"),
        "ref": {"type": "pack_conflict_note", "kind": kind, "key": str(note.get("key") or ""), "winner_id": winner},
    }


def _resolved_fact_line(entry: dict[str, Any]) -> str:
    winner_display = entry.get("winner_display")
    if not winner_display:
        return ""
    losers = "、".join(f"「{display}」" for display in entry.get("loser_displays", [])[:2])
    loser_clause = f"；{losers}为已知分歧，不再采用" if losers else ""
    return (
        f"- {_kind_label(entry['kind'])}「{_display_key(entry['kind'], entry['key'])}」："
        f"以「{winner_display}」为准（{entry['attribution']}）{loser_clause}。"
    )


def _unresolved_line(entry: dict[str, Any]) -> str:
    left = entry["left"]["digest"]
    right = entry["right"]["digest"]
    if entry.get("ask_if_material"):
        return (
            f"- 待确认：「{left}」与「{right}」两种说法不一致，" "回答相关问题时先向用户确认选哪种（ask_if_material）。"
        )
    return f"- 已知分歧（未裁决，暂不作为事实使用）：「{left}」与「{right}」说法不一致。"


def build_conflict_resolution_context(
    *,
    conflict_notes: list[dict[str, Any]],
    record_index: dict[str, dict[str, Any]],
    unresolved_rows: list[Any] | None = None,
    query_text: str | None = None,
) -> dict[str, Any]:
    """组装注入面 payload（context_pack 的唯一调用面；纯函数）。

    返回 dict（ContextPack.conflict_resolution / to_prompt_context 直接承载）：
    resolved_facts（winner 归因）+ unresolved_conflicts（已知分歧 +
    ask-if-material）+ resolution_refs（卡面 work 3）+ prompt_note（有界
    可解释文本）。
    """
    resolved_facts = [
        _resolved_fact_entry(note, record_index)
        for note in conflict_notes
        if str(note.get("type") or "") in PACK_NOTE_KINDS
    ]
    # 有界注入：只带「发生了真实裁决」的条目进 prompt 面（有败者才有归因价值）。
    prompt_resolved = [entry for entry in resolved_facts if entry["loser_ids"]][:PROMPT_NOTE_MAX_RESOLVED]

    unresolved_entries = [serialize_unresolved_for_context(row, query_text) for row in list(unresolved_rows or [])]
    material_entries = [entry for entry in unresolved_entries if entry["ask_if_material"]]

    resolution_refs: list[dict[str, Any]] = [
        {
            "scope": "resolved",
            "kind": entry["kind"],
            "key": entry["key"],
            "winner_id": entry["winner_id"],
            "loser_ids": entry["loser_ids"],
            "reason_code": entry["reason_code"],
        }
        for entry in resolved_facts
        if entry["winner_id"]
    ]
    resolution_refs.extend(
        {
            "scope": "unresolved",
            "conflict_id": entry["conflict_id"],
            "conflict_key": entry["conflict_key"],
            "category": entry["category"],
        }
        for entry in unresolved_entries
    )

    lines: list[str] = []
    for entry in prompt_resolved:
        line = _resolved_fact_line(entry)
        if line:
            lines.append(line)
    for entry in material_entries[:PROMPT_NOTE_MAX_UNRESOLVED]:
        lines.append(_unresolved_line(entry))
    # 非 material 的未决冲突不占 prompt 预算：聚合为一行（不带 digest），
    # 只保留「存在已知分歧、暂不作为事实使用」的语义；明细走进程内结构化面。
    non_material_count = len(unresolved_entries) - len(material_entries)
    if non_material_count > 0:
        lines.append(f"- 另有 {non_material_count} 条已知分歧与本轮问题无关，暂不作为事实使用。")
    prompt_note = "\n".join(lines)

    return {
        "version": CONFLICT_RESOLUTION_CONTEXT_VERSION,
        "resolved_facts": resolved_facts,
        "unresolved_conflicts": unresolved_entries,
        "ask_if_material": bool(material_entries),
        "material_conflict_ids": [entry["conflict_id"] for entry in material_entries],
        "resolution_refs": resolution_refs,
        "prompt_note": prompt_note,
    }


def to_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """prompt 面有界投影（ContextPack.to_prompt_context 唯一出口）。

    结构化条目（resolved_facts/unresolved_conflicts/refs）只供进程内消费面
    （SufficiencyChecker/Planner/遥测），**不整包序列化进 prompt**——最坏满额
    实测 >10k tokens，违背卡面「避免把冲突文本全部塞进去」。prompt 只带：
    版本、ask-if-material 旗标、material 冲突 id、有界 prompt_note 文本。
    """
    if not isinstance(payload, dict):
        return {}
    return {
        "version": payload.get("version") or CONFLICT_RESOLUTION_CONTEXT_VERSION,
        "ask_if_material": bool(payload.get("ask_if_material")),
        "material_conflict_ids": list(payload.get("material_conflict_ids") or []),
        "prompt_note": str(payload.get("prompt_note") or ""),
    }


def select_material_clarification(
    conflict_resolution: dict[str, Any] | None,
) -> tuple[str | None, str | None, str | None]:
    """One Best Question：material 冲突里选**一个**生成问句（确定性序）。

    优先级：UNSAFE_AMBIGUITY（高风险）→ surfacing 时间新者。返回
    (question, conflict_id, category)；无 material 冲突 → (None, None, None)。
    SufficiencyChecker 只经此函数消费，materiality 判定不在这里重复发明。
    """
    if not isinstance(conflict_resolution, dict) or not conflict_resolution.get("ask_if_material"):
        return None, None, None
    candidates = [
        entry
        for entry in (conflict_resolution.get("unresolved_conflicts") or [])
        if isinstance(entry, dict) and entry.get("ask_if_material") and entry.get("clarification_question")
    ]
    if not candidates:
        return None, None, None
    # 稳定双排序：先时间新→旧，再稳定按优先级分组——同组内保持最新在前。
    candidates.sort(key=lambda entry: str(entry.get("surfaced_at") or ""), reverse=True)
    candidates.sort(key=lambda entry: 0 if entry.get("category") == _CATEGORY_UNSAFE else 1)
    chosen = candidates[0]
    return (
        str(chosen["clarification_question"]),
        str(chosen.get("conflict_id") or "") or None,
        str(chosen.get("category") or "") or None,
    )
