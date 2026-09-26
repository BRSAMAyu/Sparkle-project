"""V3-FIX-296（wt583）: MasteryMergeCRDT 三处契约相悖 — 红→绿固化钉。

wt576 复核（v3-output/WT576-VERIFY/verdicts.md F5 节）三断言全红：

(a) merge_task_status('completed','abandoned') = 'abandoned'
    —— 序表把 abandoned(3) 排在 completed(2) 之上，违背自述
    "most-progressed wins"（学习进度语义里 completed 才是最 progressed
    的终态，abandoned 是中途放弃）。
(b) merge_node(x,x) revision 5 → 6 → 7
    —— ``max(local, remote) + 1`` 把「合并」与「更新」混同，破坏自述
    CRDT 幂等性（merge_node(x, x) 必须恒等于 x）。
(c) remote updated_at (09-09) > local updated_at (09-01) 时 merged
    note 仍是 local 的
    —— ``merged = dict(local)`` 纯 local-wins，违背自述
    "LWW for metadata / updated_at: latest wins"。

模块零外部调用方（仅 merge_mastery 被 gRPC 冲突路径接线；V3-FIX-295 后该
路径改为服务端 CAS，merge_mastery 保留为 max-wins 参考语义与测试锚）。
本文件固化修真后的契约：completed > in_progress > abandoned > pending、
revision 纯 max 幂等、metadata 按 updated_at 真实 LWW（平局归 local）。
"""

from datetime import UTC, datetime
from typing import Any

from app.services.galaxy.crdt_persistence import MasteryMergeCRDT


def _node(
    *,
    mastery: float = 0.5,
    status: str = "in_progress",
    revision: int = 5,
    note: str = "base",
    updated_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "mastery_score": mastery,
        "status": status,
        "revision": revision,
        "note": note,
        "updated_at": updated_at if updated_at is not None else datetime(2026, 9, 1, 12, 0, 0),
    }


# ── (a) 终态序表：completed 必须胜过 abandoned ────────────────────────────


def test_completed_beats_abandoned():
    assert MasteryMergeCRDT.merge_task_status("completed", "abandoned") == "completed"
    assert MasteryMergeCRDT.merge_task_status("abandoned", "completed") == "completed"


def test_status_order_most_progressed_wins():
    # completed > in_progress > abandoned > pending（自述 "most progressed wins"）
    assert MasteryMergeCRDT.merge_task_status("in_progress", "abandoned") == "in_progress"
    assert MasteryMergeCRDT.merge_task_status("abandoned", "in_progress") == "in_progress"
    assert MasteryMergeCRDT.merge_task_status("completed", "in_progress") == "completed"
    assert MasteryMergeCRDT.merge_task_status("in_progress", "pending") == "in_progress"
    assert MasteryMergeCRDT.merge_task_status("completed", "pending") == "completed"


def test_task_status_merge_commutative_and_idempotent():
    statuses = ["pending", "abandoned", "in_progress", "completed"]
    for a in statuses:
        for b in statuses:
            assert MasteryMergeCRDT.merge_task_status(a, b) == MasteryMergeCRDT.merge_task_status(b, a)
            assert MasteryMergeCRDT.merge_task_status(a, b) == MasteryMergeCRDT.merge_task_status(
                MasteryMergeCRDT.merge_task_status(a, b), b
            )


# ── (b) merge_node 幂等：merge_node(x, x) 恒等于 x ────────────────────────


def test_merge_node_with_itself_is_idempotent():
    x = _node(revision=5)
    once = MasteryMergeCRDT.merge_node(x, dict(x))
    assert once["revision"] == 5, "merge_node(x, x) 不得推进 revision（幂等 CRDT）"
    twice = MasteryMergeCRDT.merge_node(once, once)
    assert twice["revision"] == 5, "重复合并仍须保持 revision=5"
    assert twice == dict(x)


def test_merge_node_revision_is_pure_max():
    local = _node(revision=3)
    remote = _node(revision=9)
    merged = MasteryMergeCRDT.merge_node(local, remote)
    assert merged["revision"] == 9
    # 交换律：max 不依赖参数序
    assert MasteryMergeCRDT.merge_node(remote, local)["revision"] == 9


# ── (c) metadata 真实 LWW：updated_at 新者胜 ─────────────────────────────


def test_remote_newer_metadata_wins():
    local = _node(note="local", updated_at=datetime(2026, 9, 1, 12, 0, 0))
    remote = _node(note="remote", updated_at=datetime(2026, 9, 9, 8, 0, 0))
    merged = MasteryMergeCRDT.merge_node(local, remote)
    assert merged["note"] == "remote", "remote updated_at 更新时 metadata 须取 remote（LWW）"
    assert merged["updated_at"] == remote["updated_at"]


def test_local_newer_metadata_wins():
    local = _node(note="local", updated_at=datetime(2026, 9, 9, 8, 0, 0))
    remote = _node(note="remote", updated_at=datetime(2026, 9, 1, 12, 0, 0))
    merged = MasteryMergeCRDT.merge_node(local, remote)
    assert merged["note"] == "local"
    assert merged["updated_at"] == local["updated_at"]


def test_lww_ties_resolve_to_local_deterministically():
    ts = datetime(2026, 9, 5, 0, 0, 0)
    local = _node(note="local", updated_at=ts)
    remote = _node(note="remote", updated_at=ts)
    merged = MasteryMergeCRDT.merge_node(local, remote)
    assert merged["note"] == "local"


def test_lww_survives_iso_string_timestamps():
    local = _node(note="local", updated_at="2026-09-01T12:00:00")
    remote = _node(note="remote", updated_at="2026-09-09T08:00:00")
    merged = MasteryMergeCRDT.merge_node(local, remote)
    assert merged["note"] == "remote"


def test_missing_updated_at_falls_back_to_present_side():
    local = _node(note="local", updated_at=None)
    remote = _node(note="remote", updated_at=datetime(2026, 9, 9, 8, 0, 0))
    assert MasteryMergeCRDT.merge_node(local, remote)["note"] == "remote"
    local = _node(note="local", updated_at=datetime(2026, 9, 9, 8, 0, 0))
    remote = _node(note="remote", updated_at=None)
    assert MasteryMergeCRDT.merge_node(local, remote)["note"] == "local"


# ── 合成语义：metadata LWW 不得侵蚀 max-wins 掌握度 / most-progressed 状态 ─


def test_older_metadata_side_with_higher_mastery_still_wins_mastery():
    local = _node(mastery=0.9, status="in_progress", revision=2, note="local", updated_at=datetime(2026, 9, 9))
    remote = _node(mastery=0.2, status="completed", revision=7, note="remote", updated_at=datetime(2026, 9, 1))
    merged = MasteryMergeCRDT.merge_node(local, remote)
    assert merged["mastery_score"] == 0.9
    assert merged["status"] == "completed"
    assert merged["revision"] == 7
    assert merged["note"] == "local"  # local updated_at 更新 → metadata 归 local


def test_utc_aware_and_naive_timestamps_comparable():
    local = _node(note="local", updated_at=datetime(2026, 9, 9, 8, 0, 0))
    remote = _node(note="remote", updated_at=datetime(2026, 9, 9, 8, 0, 0, tzinfo=UTC))
    merged = MasteryMergeCRDT.merge_node(local, remote)
    assert merged["note"] in {"local", "remote"}  # 等价时刻：不抛异常即可，平局归 local
    assert merged["note"] == "local"
