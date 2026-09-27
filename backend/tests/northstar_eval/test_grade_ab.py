"""NORTHSTAR · GRADE-AB 题包与双档装配守卫（pytest 断言面，零 LLM 调用）。

钉住 GRADE-AB 卡验收：
- **题包**：100 题下限、schema/枚举/语义互锁（load_pack 有坏即拒）、
  对错分布与边界例在场（partial/slip/blank）；
- **双档路由解析**：档 A=PRO→dashscope_reason（qwen3.7-plus 思考，$0.0012/1k）、
  档 B=STANDARD→dashscope_standard_thinking（qwen3.8-flash，$0.00025/1k、
  wire enable_thinking=false——与假设 A env 切换后的生产 wire 行为一致）；
  成本锚点比 = 0.2083（-79%，B-QWEN §4 预期）；
- **判卷提示词装配**：100 题全量可渲染、两臂同文（A/B 单变量=模型档位）；
- **对照判定数学**：build_report 的 gate ①(≤3pp)/②(≤2pp) 在合成判定上方向正确
  （全一致→pass，注入分歧超限→reject），分歧清单落名。

红线：本文件不发起任何网络请求；live 路径（grade_arm_live）不在测试面内。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.northstar_eval.grade_ab import (
    GATE_ERROR_TYPE_PP,
    GATE_PARSE_RATE_PP,
    MIN_PACK_QUESTIONS,
    build_messages,
    build_report,
    load_pack,
    pack_composition,
    resolve_arm,
)

PACK_PATH = Path(__file__).resolve().parent / "grade_ab_pack.json"


@pytest.fixture(scope="module")
def pack() -> dict:
    return load_pack(PACK_PATH)


@pytest.fixture(autouse=True)
def _deterministic_router_world(monkeypatch):
    """钉死双档解析的确定性世界（E-06 同款坑；test-only 零产品码，wt603）。

    本文件的路由断言（A=PRO→dashscope_reason、B=STANDARD→dashscope_standard_thinking、
    成本锚点 0.2083）编码的是「LLM_PROVIDER=qwen 默认置首 + 无 LLM_TIER_* 覆盖 + 无 key
    注册」的世界。host .env 若带 `LLM_TIER_PRO=dashscope_standard_thinking,glm_4_7_pro`
    （B-QWEN 假设 A 的运维切换位，合法产品面），select_model(force_tier=PRO) 会按覆盖链
    解析 → A 臂漂移成 dashscope_standard_thinking——主仓合并态 2 红、无 .env 的 worktree
    绿，正是这一未声明环境依赖（冷启动 _model_health 空表无关：未记录 key 恒 healthy，
    PRO 链候选恒非空，deepseek_chat 兜底支路不触发）。

    与 tests/unit/test_llm_router_free_tier.py `_deterministic_env` 同配方：清空
    settings 的 *_API_KEY/LLM_TIER_*、钉 LLM_PROVIDER=qwen（docstring 已申报的假设 A
    前提），重建一次性 LLMRouter 并 monkeypatch 交换模块单例——零共享单例态污染，
    测试后自动还原；不删任何断言，只把未声明的环境前提变成显式钉死。
    """
    import app.core.llm_router as llm_router_module
    from app.config import settings

    for k in [k for k in vars(settings) if k.endswith("_API_KEY") or k.startswith("LLM_TIER_")]:
        monkeypatch.setattr(settings, k, "")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "qwen")
    monkeypatch.setattr(llm_router_module, "llm_router", llm_router_module.LLMRouter())


def test_pack_meets_floor_and_split(pack: dict) -> None:
    composition = pack_composition(pack)
    assert composition["question_count"] >= MIN_PACK_QUESTIONS
    # 对错各半 + 部分正确边界（卡面要求：对错各半 + 边界例）
    assert composition["verdicts"] == {"correct": 50, "wrong": 44, "partial": 6}
    # 边界例三类齐备：部分正确 / 笔误 / 空白
    assert composition["boundaries"] == {"None": 84, "partial": 6, "slip": 6, "blank": 4}
    # 学科点分布：离散数学七大域，图论最重（与 JOURNEY NS-001 同科同弱点）
    assert set(composition["domains"]) == {
        "数理逻辑",
        "集合论",
        "二元关系",
        "函数与基数",
        "图论",
        "组合数学",
        "代数系统",
    }
    assert composition["domains"]["图论"] == 22
    # 全部题目自拟置信度申报为 high（诚实申报：无 medium 存疑题入包）
    assert composition["author_confidence"] == {"high": 100}


def test_pack_semantic_interlocks(pack: dict) -> None:
    for q in pack["questions"]:
        gold = q["gold"]
        if gold["verdict"] == "correct":
            assert gold["error_type"] == "none", q["id"]
        if q["student_answer"] == "":
            assert gold["error_type"] == "blank", q["id"]
        if q["qtype"] == "single_choice":
            assert q["standard_answer"] in q["choices"], q["id"]


def test_arm_resolution_matches_bqwen_hypothesis_a() -> None:
    arm_a = resolve_arm("PRO")
    arm_b = resolve_arm("STANDARD")
    assert arm_a["model_key"] == "dashscope_reason"
    assert arm_a["model_name"] == "qwen3.7-plus"
    assert arm_a["cost_per_1k_usd"] == pytest.approx(0.0012)
    # PRO 层不注入思考参数（provider 默认思考开）——现役判卷档 wire 行为
    assert arm_a["thinking_wire"] == "not-injected(provider-default-thinking-on)"
    assert arm_b["model_key"] == "dashscope_standard_thinking"
    assert arm_b["model_name"] == "qwen3.8-flash"
    assert arm_b["cost_per_1k_usd"] == pytest.approx(0.00025)
    # 档 B wire 注入 enable_thinking=false：与 LLM_TIER_PRO=dashscope_standard_thinking
    # 切换后的生产行为一致（wire 键于 config.tier=standard）
    assert arm_b["extra_body"] == {"enable_thinking": False}
    # B-QWEN §4 预期：$0.00025/$0.0012 ≈ 0.2083（-79%）
    ratio = arm_b["cost_per_1k_usd"] / arm_a["cost_per_1k_usd"]
    assert ratio == pytest.approx(0.2083, abs=1e-3)


def test_prompt_assembly_identical_across_arms(pack: dict) -> None:
    """两臂逐字节同提示词——A/B 单变量=模型档位（评测有效性前提）。"""
    for q in pack["questions"]:
        messages = build_messages(q)
        assert len(messages) == 2
        assert messages[0]["role"] == "system" and messages[1]["role"] == "user"
        # 判卷契约输入面：题干/标准答案/学生作答/置信度全进提示词
        user_payload = json.loads(messages[1]["content"].removeprefix("请判卷：\n"))
        assert user_payload["题干"] == q["stem"]
        assert user_payload["标准答案"] == q["standard_answer"]
        assert user_payload["学生自报置信度"] == q["student_confidence"]


def _synthetic_runs(
    verdicts_a: list[str],
    verdicts_b: list[str],
    etypes: list[str],
    etypes_b: list[str] | None = None,
) -> dict:
    questions = [
        {"id": f"T{i:02d}", "gold": {"verdict": verdicts_a[i], "error_type": etypes[i]}} for i in range(len(verdicts_a))
    ]
    # verdict 判定命中=与金标同词；B 臂错误类型可按参数制造分歧（gate ① 的输入）
    etypes_arm_b = etypes_b if etypes_b is not None else etypes

    def _entries(verdicts: list[str], arm_etypes: list[str]) -> list[dict]:
        return [
            {
                "id": f"T{i:02d}",
                "latency_ms": 100,
                "est_prompt_tokens": 10,
                "est_completion_tokens": 5,
                "est_cost_usd": 0.001,
                "parse_ok": True,
                "judgement": {
                    "verdict": verdicts[i],
                    "score": 1.0,
                    "error_type": arm_etypes[i],
                    "brief": "",
                    "enum_valid": True,
                },
            }
            for i in range(len(verdicts))
        ]

    return questions, {"A": _entries(verdicts_a, etypes), "B": _entries(verdicts_b, etypes_arm_b)}


def test_report_gate_pass_when_arms_agree() -> None:
    verdicts = ["correct", "wrong"] * 5
    etypes = ["none", "calculation"] * 5
    questions, runs = _synthetic_runs(verdicts, verdicts, etypes)
    pack = {"questions": [{**q, "domain": "d", "qtype": "judge", "boundary": None} for q in questions]}
    report = build_report(pack, runs)
    assert report["gate"]["evaluated"] is True
    assert report["gate"]["adoption_signal"] == "pass"
    assert report["summary"]["delta"]["error_type_match_diff_pp"] == 0
    assert report["summary"]["delta"]["mutual_verdict_agree_rate"] == 1.0
    assert report["disagreements"] == []


def test_report_gate_rejects_over_threshold_divergence() -> None:
    verdicts = ["correct", "wrong"] * 5
    etypes = ["none", "calculation"] * 5
    # B 臂在 3/10 题上错标错误类型（none→knowledge 等）→ vs 金标命中率差 30pp > 3pp 阈
    etypes_b = [
        "knowledge",
        "calculation",
        "knowledge",
        "wrong_placeholder",
        "knowledge",
        "none",
        "calculation",
        "none",
        "calculation",
        "none",
    ]
    etypes_b = [e if e != "wrong_placeholder" else "careless" for e in etypes_b]
    questions, runs = _synthetic_runs(verdicts, verdicts, etypes, etypes_b)
    pack = {"questions": [{**q, "domain": "d", "qtype": "judge", "boundary": None} for q in questions]}
    report = build_report(pack, runs)
    assert report["gate"]["evaluated"] is True
    assert report["gate"]["gate_1_error_type_pp"]["actual"] > GATE_ERROR_TYPE_PP
    assert report["gate"]["adoption_signal"] == "reject"
    assert len(report["disagreements"]) >= 3


def test_gate_thresholds_frozen() -> None:
    assert GATE_ERROR_TYPE_PP == 3.0
    assert GATE_PARSE_RATE_PP == 2.0


def test_cli_dry_run_end_to_end(tmp_path, capsys) -> None:
    """卡面验收命令的等价面：无 key 全链装配 + 骨架落盘。

    key 在场性是环境依赖面（主仓 .env 有真实 key、worktree 没有）——
    按 fleet env 依赖测试惯例钉死为无 key 世界（记忆: env-dependent-test-pitfall）。
    wt603：该钉死由模块级 `_deterministic_router_world` 真正落实（含 LLM_TIER_*/
    LLM_PROVIDER 面——此前仅申报未实现，主仓 .env 的 LLM_TIER_PRO 曾致 A 臂漂移红）。
    """
    from app.config import settings as app_settings
    from tests.northstar_eval.grade_ab import main

    rc = main(["--dry-run", "--out-dir", str(tmp_path)])
    assert rc == 0
    out_files = list(tmp_path.glob("grade_ab_run_*.json"))
    assert len(out_files) == 1
    payload = json.loads(out_files[0].read_text(encoding="utf-8"))
    assert payload["schema"] == "sparkle.northstar_eval.grade_ab.run.v1"
    assert payload["meta"]["mode"] == "dry-run"
    assert payload["meta"]["question_count"] == 100
    assert payload["meta"]["arms"]["A"]["model_key"] == "dashscope_reason"
    assert payload["meta"]["arms"]["B"]["model_key"] == "dashscope_standard_thinking"
    assert len(payload["per_question"]) == 100
    # 诚实红线（环境无关的确定性面）：key 只以布尔在场，材料绝不落盘。
    # 「无 key 世界」覆盖由 worktree 无 .env 环境证明（卡收工报告）；主仓
    # 有真实 key 时在场性=True 是正确行为，不做环境依赖断言。
    raw = out_files[0].read_text(encoding="utf-8")
    assert isinstance(payload["meta"]["arms"]["A"]["api_key_present"], bool)
    for attr in ("DASHSCOPE_API_KEY", "LLM_API_KEY"):
        val = getattr(app_settings, attr, "") or ""
        if val:
            assert val not in raw, f"{attr} material leaked into evidence"
    assert "adoption_signal" in payload["gate"] and payload["gate"]["adoption_signal"] == "not-evaluated"
    _ = capsys  # 装配打印进 captured 输出，不 assert 文案
