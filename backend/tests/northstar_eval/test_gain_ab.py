"""NORTHSTAR · GAIN-EVAL 场景包与消融接线守卫（pytest 断言面，零 LLM 调用）。

钉住 GAIN-EVAL 卡验收：
- **场景包**：20 场景下限、三类别构成（memory/profile/baseline）、judge
  契约完整性（deterministic=expect_groups / llm=rubric）、依赖类场景必须带
  probe_terms（装配探针依赖）——坏包 load_pack 直接拒；
- **消融接线（真实装配链 dry-run）**：每类别抽 1 例，经生产装配链
  （chat.get_user_context → ContextPackBuilder.build → build_system_prompt）
  装配 4 臂提示词，硬断言：臂 A 含种子事实、B-MEM（记忆召回源置空杠杆）
  不含、C-PROF（画像 fail-soft 分支）保留记忆/消除画像、E-NOPACK（真实总
  开关 USE_CONTEXT_PACK=False）全消、baseline 上 B-MEM 与 A 逐字节相同；
- **开关探针**：ENABLE_DOCUMENT_CONTEXT_INJECTION=False（真实向量/文档检索
  总开关）与 AURORA_STAGE39_GALAXY_INJECT_MODE=off（真实星图注入开关）的
  进程内传播验证。

红线：本文件不发起任何 LLM 网络请求（--dry-run 路径无 provider 调用）；
评测全部在进程内 SQLite（--database-url 默认 :memory:），生产 DB/Redis 零
接触；杠杆只在测试进程内生效。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.northstar_eval.gain_ab import (
    CATEGORY_VOCAB,
    GAIN_POSITIVE_THRESHOLD,
    MIN_PER_CATEGORY,
    MIN_SCENARIOS,
    PROMPT_ARMS,
    check_differentiators,
    load_pack,
    pack_composition,
)

PACK_PATH = Path(__file__).resolve().parent / "gain_scenarios.json"

# 每类别抽 1 例的快速接线面（--ids 供 gain_ab --dry-run 使用）
GUARD_IDS = "mem-01-exam-date,prof-01-weak-logic,base-01-group-def"


@pytest.fixture(scope="module")
def pack() -> dict:
    return load_pack(PACK_PATH)


def test_pack_meets_floors_and_categories(pack: dict) -> None:
    composition = pack_composition(pack)
    assert composition["scenario_count"] >= MIN_SCENARIOS
    for cat, floor in MIN_PER_CATEGORY.items():
        assert composition["categories"][cat] >= floor, f"{cat} 场景不足 {floor}"
    assert set(composition["categories"]) == set(CATEGORY_VOCAB)
    # 判分构成申报面：确定性优先（llm 只允许规则不可判的风格/定制类）
    assert composition["judge_kinds"]["deterministic"] >= composition["judge_kinds"]["llm"]


def test_pack_judge_and_probe_integrity(pack: dict) -> None:
    for sc in pack["scenarios"]:
        judge = sc["judge"]
        if judge["kind"] == "deterministic":
            assert judge["expect_groups"], f"{sc['id']} 缺 expect_groups"
        else:
            assert judge.get("rubric"), f"{sc['id']} llm judge 缺 rubric"
        assert sc.get("scoring_note"), f"{sc['id']} 缺 scoring_note（判分要点申报面）"
        if sc["category"] in ("memory", "profile"):
            assert sc.get("probe_terms"), f"{sc['id']} 依赖类场景缺 probe_terms"
            assert sc.get("seed"), f"{sc['id']} 依赖类场景缺 seed"
        else:
            assert not (sc.get("seed") or {}), f"{sc['id']} baseline 场景必须零种子"


def test_gate_constants_frozen() -> None:
    # 冻结门槛（防事后合理化）：正增益 ≥ +0.15
    assert GAIN_POSITIVE_THRESHOLD == 0.15


def test_differentiator_math_on_synthetic_arms(pack: dict) -> None:
    """接线断言数学：合成 4 臂装配结果上方向正确（绿/红两向）。"""
    by_id = {s["id"]: s for s in pack["scenarios"]}
    scenario = by_id["mem-01-exam-date"]
    term = scenario["probe_terms"][0]

    def arms_with(a: str, b: str, c: str, e: str) -> dict:
        return {
            "A": {
                "prompt": a,
                "prompt_sha256": __import__("hashlib").sha256(a.encode()).hexdigest(),
                "prompt_chars": len(a),
                "assembly_error": None,
            },
            "B-MEM": {
                "prompt": b,
                "prompt_sha256": __import__("hashlib").sha256(b.encode()).hexdigest(),
                "prompt_chars": len(b),
                "assembly_error": None,
            },
            "C-PROF": {
                "prompt": c,
                "prompt_sha256": __import__("hashlib").sha256(c.encode()).hexdigest(),
                "prompt_chars": len(c),
                "assembly_error": None,
            },
            "E-NOPACK": {
                "prompt": e,
                "prompt_sha256": __import__("hashlib").sha256(e.encode()).hexdigest(),
                "prompt_chars": len(e),
                "assembly_error": None,
            },
        }

    good = arms_with(f"x {term} y", "x y", f"x {term} y", "x y")
    assert check_differentiators(scenario, good) == []

    bad = arms_with("x y", "x y", f"x {term} y", "x y")  # A 丢事实
    failures = check_differentiators(scenario, bad)
    assert any(f["check"] == "A:contains_fact" for f in failures)

    leak = arms_with(f"x {term} y", f"x {term} y", f"x {term} y", "x y")  # B-MEM 未切干净
    failures = check_differentiators(scenario, leak)
    assert any(f["check"] == "B-MEM:fact_removed" for f in failures)


def test_dry_run_real_chain_wiring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """真实装配链接线守卫：每类别 1 例 × 4 臂 dry-run，断言全绿 + 探针 PASS。"""
    from tests.northstar_eval import gain_ab

    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    rc = gain_ab.main(
        [
            "--dry-run",
            "--ids",
            GUARD_IDS,
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    runs = sorted(tmp_path.glob("gain_ab_run_*.json"))
    assert len(runs) == 1
    payload = json.loads(runs[0].read_text(encoding="utf-8"))
    assert payload["schema"] == "sparkle.northstar_eval.gain_ab.run.v1"
    assert payload["differentiator_failures"] == []
    assert payload["switch_probes"]["D-VEC"]["pass"] is True
    assert payload["switch_probes"]["G-GALAXY"]["pass"] is True
    arms = payload["per_scenario"][0]["arms"]
    assert set(arms) == set(PROMPT_ARMS)
