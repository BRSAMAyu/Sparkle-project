"""V4-I06 · 上下文选择观测 → ``context_selection_receipt.v1`` 回执装配（纯函数）。

本模块是合同词表（``app.core.context_selection_receipt``）与装配点之间的**纯转换
层**：输入 = 装配面已有的观测对象，输出 = 契约回执。零 I/O、零业务推理——只做
归因收敛与词表映射。两个生产者：

- ``assemble_pack_receipt``：ContextPackBuilder.build（chat/plan_review/context_focus
  共用的上下文契约装配点；角色 ``chat_context``）——输入 = M-03 PrefilterResult、
  最终 surfaced 集、M-05 selfcheck 内部档、冲突裁决 suppressed 面、deny-quiet 面、
  I02 效用门 metadata 若开。

  候选归因判定序（首个命中生效；全部确定性）：

      prefilter 拒用（M-03 映射表）
        > surfaced（selected）
        > M-05 selfcheck 降档（duplicate / utility_gate_rejected）
        > 冲突裁决 suppressed（conflicts_confirmed_preference）
        > deny-quiet（permission_denied —— 用户已说不许用）
        > 其余合法但未进面（budget_exhausted —— 排名/预算/语义门选择压力）

  归因缺口（上游某级丢弃候选但无 attributable 面）按 budget_exhausted 兜底并在
  note 标 ``unattributed_downstream``——候选集覆盖被扫描全集，不产生悬空缺失。

- ``assemble_resume_view_receipt``（FIX-567 · V3-FIX-567）：EpisodeResumeView 聚合
  面（角色 ``resume_view``）——B05 §2「receipt 在 resume view 返回之前」。输入 =
  聚合真实读到的权威锚（goal/task 行版本 token + memory epoch）；候选集 = 视图
  依据权威（task:// + goal://，selected；聚合无拒用机制，无 rejected 候选——
  不臆造归因）。ref scheme 均在 ``ACTION_SOURCE_REF_SCHEMES`` 封闭集内且可被
  ``verify_source_ref`` join 真源（tasks/goals 表属主校验）。
"""

from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID

from app.core.context_selection_receipt import (
    CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION,
    SELECTOR_VERSION_CONTEXT_PACK,
    ContextSelectionReceipt,
    ReceiptBudget,
    ReceiptCandidate,
    ReceiptInputVersions,
    apply_utility_gate_metadata,
    memory_ref,
    new_receipt_id,
    rejection_reason_code,
)
from app.services.memory_retrieval_prefilter import PrefilterResult

_UNATTRIBUTED_NOTE = "unattributed_downstream"


def _pref_ref(kind: str, record: Any) -> str | None:
    """记录 → memory 真源 ref（preference 以 pref_key 为可解析锚，其余用 id）；
    无任何可解析锚 → None（调用方跳过——不可解析的记录不构造悬空 ref）。"""
    if kind == "preference":
        pref_key = str(getattr(record, "pref_key", "") or "").strip()
        if pref_key:
            return memory_ref("preference", pref_key)
    item_id = str(getattr(record, "id", "") or "").strip()
    if not item_id:
        return None
    return memory_ref(kind, item_id)


def _record_identifiers(record: Any) -> set[str]:
    """M-03 ``Rejection.record_id`` 的可能取值（_record_id：id → entry_id → pref_key）。"""
    identifiers: set[str] = set()
    for attr in ("id", "entry_id", "pref_key"):
        value = getattr(record, attr, None)
        if value is not None:
            identifiers.add(str(value))
    return identifiers


def assemble_pack_receipt(
    *,
    user_id: UUID,
    selection_role: str = "chat_context",
    decision_id: str | None = None,
    prefilter_results: dict[str, PrefilterResult],
    input_records: dict[str, list[Any]],
    surfaced_pref_keys: Iterable[str] = (),
    surfaced_goal_ids: Iterable[str] = (),
    surfaced_episodic_ids: Iterable[str] = (),
    ranked_pref_keys: Iterable[str] = (),
    ranked_goal_ids: Iterable[str] = (),
    ranked_episodic_ids: Iterable[str] = (),
    selfcheck_internal: list[dict[str, Any]] | None = None,
    conflicts: list[dict[str, Any]] | None = None,
    deny_quieted_keys: Iterable[str] = (),
    memory_epoch: int | None = None,
    gate_payload: dict[str, Any] | None = None,
    clarifications_used: int = 0,
) -> ContextSelectionReceipt:
    """从 build 面观测拼装回执（纯函数；候选集 = 被扫描全集，逐条归因）。"""
    section_kind = {"preferences": "preference", "goals": "goal", "episodic": "episodic"}

    surfaced: dict[str, str] = {}
    for key in surfaced_pref_keys:
        surfaced[memory_ref("preference", str(key))] = "selected"
    for identifier in surfaced_goal_ids:
        surfaced[memory_ref("goal", str(identifier))] = "selected"
    for identifier in surfaced_episodic_ids:
        surfaced[memory_ref("episodic", str(identifier))] = "selected"

    ranked: set[str] = set()
    ranked.update(memory_ref("preference", str(key)) for key in ranked_pref_keys)
    ranked.update(memory_ref("goal", str(identifier)) for identifier in ranked_goal_ids)
    ranked.update(memory_ref("episodic", str(identifier)) for identifier in ranked_episodic_ids)

    # M-05 selfcheck 降档：item_id + section → ref；reason 原样留给映射表。
    # （M-05 internal_only_entries 键名为 "id"/"section"/"reason"。）
    selfcheck_refs: dict[str, str] = {}
    for entry in selfcheck_internal or []:
        if not isinstance(entry, dict):
            continue
        section = str(entry.get("section") or "").strip()
        item_id = str(entry.get("id") or entry.get("item_id") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        kind = section_kind.get(section, section)
        if item_id:
            selfcheck_refs[memory_ref(kind, item_id)] = reason or "selfcheck:internal"

    # 冲突裁决 suppressed（M-04/裁决面）→ conflicts_confirmed_preference。
    suppressed_refs: set[str] = set()
    id_to_ref: dict[str, str] = {}
    for section, records in input_records.items():
        kind = section_kind.get(section, section)
        for record in records:
            ref = _pref_ref(kind, record)
            if ref is None:
                continue
            for identifier in _record_identifiers(record):
                id_to_ref[f"{section}:{identifier}"] = ref
    for note in conflicts or []:
        if not isinstance(note, dict):
            continue
        note_type = str(note.get("type") or "").strip()
        section = {"preference": "preferences", "goal": "goals", "episodic": "episodic"}.get(note_type, note_type)
        for identifier in note.get("suppressed") or []:
            ref = id_to_ref.get(f"{section}:{identifier}") or id_to_ref.get(f":{identifier}")
            if ref:
                suppressed_refs.add(ref)

    deny_keys = {memory_ref("preference", str(key)) for key in deny_quieted_keys}

    # 逐条归因（候选集 = 被扫描全集）。
    candidates: list[ReceiptCandidate] = []
    scanned = 0
    for section, records in input_records.items():
        kind = section_kind.get(section, section)
        rejections_by_id: dict[str, str] = {}
        result = prefilter_results.get(section)
        if result is not None:
            for rejection in result.rejections:
                rejections_by_id[str(rejection.record_id)] = rejection.reason
        for record in records:
            ref = _pref_ref(kind, record)
            if ref is None:
                continue  # 不可解析锚：不构造悬空 ref，也不计入扫描面
            scanned += 1
            if ref in surfaced:
                candidates.append(ReceiptCandidate(ref=ref, status="selected", reason_code=None, note=None))
                continue
            identifiers = _record_identifiers(record)
            rejection_reason = next((rejections_by_id[key] for key in identifiers if key in rejections_by_id), None)
            if rejection_reason is not None:
                candidates.append(
                    ReceiptCandidate(
                        ref=ref,
                        status="rejected",
                        reason_code=rejection_reason_code(rejection_reason),
                        note=None,
                    )
                )
                continue
            if ref in selfcheck_refs:
                candidates.append(
                    ReceiptCandidate(
                        ref=ref,
                        status="rejected",
                        reason_code=rejection_reason_code(selfcheck_refs[ref]),
                        note=None,
                    )
                )
                continue
            if ref in suppressed_refs:
                candidates.append(
                    ReceiptCandidate(
                        ref=ref,
                        status="rejected",
                        reason_code="conflicts_confirmed_preference",
                        note=None,
                    )
                )
                continue
            if ref in deny_keys:
                candidates.append(
                    ReceiptCandidate(
                        ref=ref,
                        status="rejected",
                        reason_code="permission_denied",
                        note="deny_quiet_window",
                    )
                )
                continue
            if ref in ranked:
                candidates.append(
                    ReceiptCandidate(
                        ref=ref,
                        status="rejected",
                        reason_code="budget_exhausted",
                        note=None,
                    )
                )
                continue
            # 归因缺口：合法候选被下游（语义门/跨类型裁决等）丢弃但无 attributable
            # 面——诚实兜底 + note 标记（metadata-only），不悬空、不臆造原因。
            candidates.append(
                ReceiptCandidate(
                    ref=ref,
                    status="rejected",
                    reason_code="budget_exhausted",
                    note=_UNATTRIBUTED_NOTE,
                )
            )

    # I02 效用门接口点：门开时其 metadata 覆盖同 id 候选（见合同/卡要点 3）。
    candidates = apply_utility_gate_metadata(candidates=candidates, gate_payload=gate_payload)

    selected_count = sum(1 for candidate in candidates if candidate.status == "selected")
    return ContextSelectionReceipt(
        schema_version=CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION,
        receipt_id=new_receipt_id(),
        selection_role=selection_role,
        decision_id=decision_id,
        input_versions=ReceiptInputVersions(
            # 本装配面未读 goal/task/policy 权威版本 → null（不得以 ""/0 冒充已读）。
            memory_epoch=memory_epoch,
            goal_version=None,
            task_version=None,
            policy_version=None,
            selector_version=SELECTOR_VERSION_CONTEXT_PACK,
        ),
        candidates=candidates,
        budget=ReceiptBudget(
            # 本装配面无独立整数选中上限（token 预算裁剪为准）——candidate_scan_limit
            # 记录实际扫描数，selected_max 记录本轮实际选中数（如实读数，非配置值）。
            candidate_scan_limit=scanned,
            selected_max=selected_count,
            clarifications_used=clarifications_used,
        ),
        why_now=None,  # chat 装配面无任务级 why-now 语义（Aurora proposal 面拥有）
    )


#: selector 实现版本（resume view 生产者：EpisodeResumeView 聚合面，FIX-567）。
SELECTOR_VERSION_RESUME_VIEW = "episode_resume.v4-f567.v1"


def assemble_resume_view_receipt(
    *,
    user_id: UUID,
    goal_id: str,
    task_id: str,
    goal_version: str | None,
    task_version: str | None,
    memory_epoch: int | None,
) -> ContextSelectionReceipt:
    """EpisodeResumeView 聚合观测 → ``resume_view`` 角色回执（纯函数；FIX-567）。

    合同 §2 产生时机「resume view 返回之前」的装配面。字段纪律：

    - ``selection_role="resume_view"``（封闭词表成员；U01 消费面
      ``episode_resume_provider`` 以此角色门判定接续依据——chat_context 角色回执
      不得冒充接续依据，归因错置）；
    - 候选集 = 视图依据权威锚：``task://<task_id>`` + ``goal://<goal_id>``
      （selected；两 ref 均在 ACTION_SOURCE_REF_SCHEMES 封闭集内且
      ``verify_source_ref`` 可 join tasks/goals 真源）。聚合面无拒用机制——
      不产生 rejected 候选、不臆造归因；
    - ``input_versions``：goal/task 版本 token = 真实读到行的 ``version_token``
      （null = 该权威未读到，不冒充）；memory_epoch = 聚合真实读值；
      ``policy_version=None``（本面未读 policy 权威）；
    - ``why_now=None``：视图的 why-now（task 字段位投影）随视图本体交付；回执级
      why-now（「为什么现在做这次选择」）在本面无 Aurora 决策参与 → null
      （合同 null 语义，与 pack 装配面同口径）。
    """
    task_ref = f"task://{str(task_id).strip()}"
    goal_ref = f"goal://{str(goal_id).strip()}"
    candidates = [
        ReceiptCandidate(ref=task_ref, status="selected", reason_code=None, note=None),
        ReceiptCandidate(ref=goal_ref, status="selected", reason_code=None, note=None),
    ]
    return ContextSelectionReceipt(
        schema_version=CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION,
        receipt_id=new_receipt_id(),
        selection_role="resume_view",
        decision_id=None,
        input_versions=ReceiptInputVersions(
            memory_epoch=memory_epoch,
            goal_version=goal_version,
            task_version=task_version,
            policy_version=None,
            selector_version=SELECTOR_VERSION_RESUME_VIEW,
        ),
        candidates=candidates,
        # 无独立整数选中上限——如实读数：扫描面 = 依据权威全集，选中数 = 实际
        # selected 数（与 pack 装配面 candidate_scan_limit=实际扫描数同口径）。
        budget=ReceiptBudget(
            candidate_scan_limit=len(candidates),
            selected_max=len(candidates),
            clarifications_used=0,
        ),
        why_now=None,
    )


__all__ = ["assemble_pack_receipt", "assemble_resume_view_receipt"]
