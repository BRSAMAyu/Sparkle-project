"""NORTHSTAR · real_drive 纯逻辑单测（无网络、无栈依赖；pytest 收集可过）。

覆盖面：证据 schema 稳定键、脱敏/截断、WS 事件聚合的判定辅助、
GP-07/GP-04 启发式判定、galaxy 对账 diff、11 检查点词表完整性。
真实网络调用一律不打（纪律：LIGHT / 不烧 LLM）。
"""

from __future__ import annotations

import json

from tests.northstar_eval.real_drive import (
    CHECKPOINT_API_VOCAB,
    CHECKPOINT_ALWAYS_UNSUPPORTED,
    StepEvidence,
    _slug,
    diff_galaxy_nodes,
    gen_password,
    judge_memory_recall,
    judge_personalization,
    redact,
    truncate_text,
)

# ---------------------------------------------------------------------------
# 证据 schema / 工具函数
# ---------------------------------------------------------------------------


def test_step_evidence_payload_stable_keys() -> None:
    step = StepEvidence(run_id="R1", step_id="B1", phase="day0", name="probe", checkpoints=("CP-00",))
    step.finish("pass", ["ok"])
    payload = step.to_payload()
    assert set(payload) == {
        "schema",
        "run_id",
        "step_id",
        "phase",
        "name",
        "started_at",
        "finished_at",
        "request",
        "response",
        "verdict",
        "checkpoints",
        "notes",
    }
    assert payload["verdict"] == "pass"
    assert payload["finished_at"]  # finish() 盖时间戳


def test_step_evidence_rejects_unknown_verdict() -> None:
    step = StepEvidence(run_id="R1", step_id="X", phase="p", name="n")
    step.finish("excellent")  # 非法 verdict 必须诚实降级为 blocked
    assert step.verdict == "blocked"


def test_truncate_text_dict_and_str() -> None:
    big = {"k": "v" * 9000}
    out = truncate_text(big, 100)
    assert isinstance(out, dict) and out["_truncated"] is True
    long_str = truncate_text("x" * 500, 10)
    assert long_str.startswith("x" * 10) and "truncated" in long_str
    assert truncate_text(42, 10) == 42  # 非字符串原样


def test_redact_masks_credentials() -> None:
    body = {"password": "hunter2-secret", "access_token": "jwt-value", "username": "u"}
    masked = redact(body)
    assert masked["password"].startswith("sha256:")
    assert masked["access_token"].startswith("sha256:")
    assert masked["username"] == "u"
    assert "hunter2" not in json.dumps(masked)


def test_slug_safe() -> None:
    assert _slug("exam-sprint intake (7-day backbone)") == "exam-sprint-intake--7-day-backbone"
    assert len(_slug("x" * 200)) <= 60


def test_gen_password_strength() -> None:
    pwd = gen_password()
    assert len(pwd) == 18
    assert any(c.isdigit() for c in pwd) and any(c.isalpha() for c in pwd)


# ---------------------------------------------------------------------------
# 启发式判定（GP-04 / GP-07）
# ---------------------------------------------------------------------------


def test_judge_memory_recall_positive() -> None:
    followup = "不对。你上次说的那条是错的：偶数度数不保证连通，你之前问的两个不交三角形就是反例；欧拉回路还要图连通。"
    verdict, markers = judge_memory_recall("correction", followup)
    assert verdict == "pass"
    assert any("上次" in m or "之前" in m for m in markers)


def test_judge_memory_recall_topic_without_memory_is_blocked() -> None:
    followup = "偶数度数不能推出连通性，欧拉回路要求连通且所有顶点偶度。"
    verdict, _ = judge_memory_recall("", followup)
    assert verdict == "blocked"  # 主题命中但无记忆指称 → 不能记 pass


def test_judge_memory_recall_empty_is_blocked() -> None:
    assert judge_memory_recall("", "")[0] == "blocked"


def test_judge_memory_recall_anti_recall_is_fail() -> None:
    # 「记得」出现在让步从句里（只记得任务历史）→ 语义是失忆，必须 fail（防关键词误报）
    followup = "你提到的具体薄弱点我这里没有完整记录，只记得你刚完成 Day1 的复习任务。欧拉回路需要连通且偶度。"
    verdict, markers = judge_memory_recall("correction", followup)
    assert verdict == "fail"
    assert any("没有完整记录" in m for m in markers)


def test_judge_personalization_anti_recall_is_fail() -> None:
    answer = "我这里没有完整记录，只记得你刚完成 Day1 数理逻辑 I 的复习。图论里最容易混淆的是欧拉回路。"
    verdict, markers = judge_personalization(answer)
    assert verdict == "fail"
    assert any("没有完整记录" in m for m in markers)


def test_judge_personalization_levels() -> None:
    rich = "针对你的图论弱点：你提到过总分不清欧拉回路和哈密顿回路，你的掌握度也低。"
    assert judge_personalization(rich)[0] == "pass"
    assert judge_personalization("欧拉回路是")[0] == "blocked"
    assert judge_personalization("这是一个通用回答。")[0] == "fail"
    assert judge_personalization("")[0] == "blocked"


# ---------------------------------------------------------------------------
# GP-03 galaxy 对账 diff
# ---------------------------------------------------------------------------


def test_diff_galaxy_nodes_mastery_changes_and_additions() -> None:
    before = {"nodes": [{"id": "n1", "mastery": 0.2}, {"id": "n2", "mastery": 0.5}]}
    after = {"nodes": [{"id": "n1", "mastery": 0.35}, {"id": "n2", "mastery": 0.5}, {"id": "n3", "mastery": 0.0}]}
    diff = diff_galaxy_nodes(before, after)
    assert diff["added_nodes"] == ["n3"]
    assert diff["mastery_changes"] == {"n1": {"before": 0.2, "after": 0.35}}
    assert (diff["before_count"], diff["after_count"]) == (2, 3)


def test_diff_galaxy_nodes_empty_graphs() -> None:
    diff = diff_galaxy_nodes({}, {})
    assert diff["added_nodes"] == [] and diff["before_count"] == 0


# ---------------------------------------------------------------------------
# 检查点词表完整性（冻结面回归）
# ---------------------------------------------------------------------------


def test_checkpoint_api_vocab_complete_and_unsupported_frozen() -> None:
    assert len(CHECKPOINT_API_VOCAB) == 11
    ids = {row.split(" ")[0] for row in CHECKPOINT_API_VOCAB}
    assert ids == {f"CP-{i:02d}" for i in range(0, 9)} | {"CP-98", "CP-99"}
    assert set(CHECKPOINT_ALWAYS_UNSUPPORTED) == {
        "CP-98 daily cognitive load self-report",
        "CP-99 full mock exam wall clock at or below budget",
    }
