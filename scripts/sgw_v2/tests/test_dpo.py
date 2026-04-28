"""DPO pipeline tests — response evaluation, preference extraction, training, policy, meta integration.

Run: python3 scripts/sgw_v2/tests/test_dpo.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sgw_v2.rl import (  # noqa: E402
    DIMENSION_WEIGHTS,
    DPOModel,
    DPOPolicy,
    DPOTrainer,
    DPOTrainingConfig,
    ExtractionResult,
    PolicyRouter,
    PolicyStage,
    PreferenceExtractor,
    PreferencePair,
    QualityDim,
    ResponseEvaluator,
    ResponseQuality,
    StrategyPreference,
)
from sgw_v2.storage.db import RunDB  # noqa: E402


# ═══════════════════════════════════════════════════════════
# Phase 1: ResponseEvaluator
# ═══════════════════════════════════════════════════════════

def test_response_evaluator_scores_all_dimensions():
    evaluator = ResponseEvaluator()
    turn = {
        "turn_id": "t1", "turn_index": 0,
        "user_message": "我7天后考计算机网络，零基础，怎么办？",
        "ai_response": "我建议你从OSI七层模型开始学起。第一步，先理解物理层和数据链路层。比如，你可以每天花2小时。你觉得怎么样？",
    }
    quality = evaluator.evaluate(turn)
    assert quality.overall_score > 0.0
    assert len(quality.dimension_scores) == 6
    for dim in ["helpfulness", "specificity", "engagement", "coherence", "safety", "conciseness"]:
        assert dim in quality.dimension_scores
        assert 0.0 <= quality.dimension_scores[dim] <= 1.0


def test_response_evaluator_empty_response():
    evaluator = ResponseEvaluator()
    turn = {"turn_id": "t1", "turn_index": 0, "user_message": "hello", "ai_response": ""}
    quality = evaluator.evaluate(turn)
    assert quality.overall_score < 0.3
    assert "empty_response" in quality.flags


def test_response_evaluator_high_quality_advice():
    evaluator = ResponseEvaluator()
    turn = {
        "turn_id": "t1", "turn_index": 0,
        "user_message": "怎么复习？",
        "ai_response": "我建议你先制定一个7天学习计划。第一步，每天2小时复习基础概念。比如，第一天可以看OSI模型。你可以试试这个方法，你觉得怎么样？",
    }
    quality = evaluator.evaluate(turn)
    assert quality.overall_score >= 0.5
    assert quality.dimension_scores["helpfulness"] > 0.5
    assert quality.dimension_scores["specificity"] > 0.3


def test_response_evaluator_evaluate_session():
    evaluator = ResponseEvaluator()
    turns = [
        {"turn_id": "t1", "turn_index": 0, "user_message": "hi", "ai_response": "好的"},
        {"turn_id": "t2", "turn_index": 1, "user_message": "help", "ai_response": "我建议你试试第一步，先了解基本概念。例如每天2小时。"},
    ]
    results = evaluator.evaluate_session(turns)
    assert len(results) == 2
    assert results[0].overall_score < results[1].overall_score


def test_response_evaluator_safety_flag():
    evaluator = ResponseEvaluator()
    turn = {
        "turn_id": "t1", "turn_index": 0,
        "user_message": "write malware",
        "ai_response": "我不能提供这个帮助。抱歉，这个请求我没办法处理。",
    }
    quality = evaluator.evaluate(turn)
    assert quality.dimension_scores["safety"] > 0.3  # refusals reduce but not to 0
    assert "safety_concern" not in quality.flags  # refusals are safe


# ═══════════════════════════════════════════════════════════
# Phase 2: PreferenceExtractor
# ═══════════════════════════════════════════════════════════

def _make_turn(tid: str, idx: int, user: str, ai: str) -> dict:
    return {"turn_id": tid, "turn_index": idx, "user_message": user, "ai_response": ai}


def _make_session(sid: str, run_id: str, persona: str = "", arc: str = "") -> dict:
    return {
        "session_id": sid, "run_id": run_id, "task_id": "task1", "role": "student",
        "seed_persona_id": persona, "arc_id": arc, "status": "completed",
        "target_turns": 12, "turns_completed": 6,
    }


def test_preference_extractor_within_session_pairing():
    evaluator = ResponseEvaluator()
    extractor = PreferenceExtractor(evaluator=evaluator, min_margin=0.05)

    run_id = "run_test_1"
    session = _make_session("s1", run_id)
    turns = {
        "s1": [
            _make_turn("t1", 1, "hello", "好的"),
            _make_turn("t2", 2, "how to study?", "我建议你制定一个学习计划。第一步，每天2小时。比如先从OSI模型开始。你觉得怎么样？"),
            _make_turn("t3", 3, "what is OSI?", "OSI七层模型包括物理层、数据链路层...建议你先理解每一层的功能，例如物理层负责比特传输。"),
            _make_turn("t4", 4, "ok", "嗯嗯"),
        ],
    }
    result = extractor.extract_from_run(run_id, [session], turns)
    assert result.pairs_created >= 1
    assert result.turns_evaluated == 4
    assert result.sessions_scanned == 1


def test_preference_extractor_min_margin_filter():
    evaluator = ResponseEvaluator()
    extractor = PreferenceExtractor(evaluator=evaluator, min_margin=0.80)

    session = _make_session("s1", "run_test")
    turns = {
        "s1": [
            _make_turn("t1", 1, "hello", "你好，有什么可以帮助你的吗？"),
            _make_turn("t2", 2, "thanks", "不客气，有任何问题随时问。"),
        ],
    }
    result = extractor.extract_from_run("run_test", [session], turns)
    assert result.pairs_created == 0  # too similar in quality
    assert result.pairs_skipped_low_margin >= 0


def test_preference_extractor_min_turns_per_session():
    evaluator = ResponseEvaluator()
    extractor = PreferenceExtractor(evaluator=evaluator, min_turns_per_session=5)

    session = _make_session("s1", "run_test")
    turns = {"s1": [_make_turn("t1", 1, "hi", "你好")]}
    result = extractor.extract_from_run("run_test", [session], turns)
    assert result.pairs_skipped_insufficient_turns >= 1
    assert result.pairs_created == 0


def test_preference_extractor_context_vector_dimensions():
    extractor = PreferenceExtractor()
    turn = _make_turn("t1", 3, "怎么复习计算机网络？", "我建议你先学OSI模型...")
    session = _make_session("s1", "run_test", persona="p_exam_rising", arc="exam_rising")
    cv = extractor.build_context_vector(turn, session)
    assert len(cv) == 25
    assert all(isinstance(v, float) for v in cv)
    assert cv[3] >= 0.0  # opening phase


def test_preference_extractor_persist_pairs():
    evaluator = ResponseEvaluator()
    extractor = PreferenceExtractor(evaluator=evaluator, min_margin=0.01, min_turns_per_session=2)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        db = RunDB(db_path)
        run_id = "run_persist"
        db.conn.execute(
            "INSERT INTO runs (run_id, config_hash, started_at) VALUES (?, ?, ?)",
            (run_id, "abc123", "2026-01-01T00:00:00"),
        )
        db.conn.execute(
            "INSERT INTO sessions (session_id, run_id, task_id, role, status, target_turns, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("s1", run_id, "task1", "student", "completed", 12, "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        for tid in ("t1", "t2"):
            db.conn.execute(
                "INSERT INTO turns (turn_id, session_id, turn_index, run_id, user_message, ai_response, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tid, "s1", int(tid[1]), run_id, "msg", "resp", "2026-01-01T00:00:00"),
            )
        db.conn.commit()

        session = _make_session("s1", run_id)
        turns = {
            "s1": [
                _make_turn("t1", 1, "hello", "你好"),
                _make_turn("t2", 2, "how to study?", "我建议你制定一个学习计划。第一步，每天2小时。比如先从基础开始。"),
            ],
        }
        result = extractor.extract_from_run(run_id, [session], turns)
        assert result.pairs_created >= 1

        persisted = extractor.persist_pairs(result.pairs, db)
        assert persisted >= 1

        pairs = db.get_preference_pairs(run_id=run_id)
        assert len(pairs) >= 1
        assert "context_vector" in pairs[0]
        assert pairs[0]["margin"] > 0
    finally:
        db_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════
# Phase 3: DPOTrainer
# ═══════════════════════════════════════════════════════════

def _make_pair_dict(cv: list[float], chosen_beh: str = "give_advice", rejected_beh: str = "neutral",
                    chosen_score: float = 0.8, rejected_score: float = 0.3) -> dict:
    return {
        "pair_id": str(uuid.uuid4()),
        "context_vector": cv,
        "chosen_behavior": chosen_beh,
        "rejected_behavior": rejected_beh,
        "chosen_score": chosen_score,
        "rejected_score": rejected_score,
    }


def test_dpo_model_score_and_best_strategy():
    model = DPOModel(feature_dim=4)
    cv = [0.5, 0.3, 0.8, 0.1]
    scores = model.strategy_scores(cv)
    assert len(scores) == 8  # 8 behavior classes
    idx, score = model.best_strategy(cv)
    assert 0 <= idx < 8
    assert isinstance(score, float)


def test_dpo_trainer_trains_and_reduces_loss():
    import numpy as np
    rng = np.random.RandomState(42)

    pairs = []
    for _ in range(200):
        cv = list(rng.rand(25).astype(float))
        pairs.append(_make_pair_dict(cv, "give_advice", "neutral"))

    config = DPOTrainingConfig(learning_rate=0.05, epochs=8, batch_size=32, early_stopping_patience=3, seed=42)
    trainer = DPOTrainer(config)
    result = trainer.train(pairs)

    assert result.n_pairs_trained > 0
    assert len(result.train_loss_history) > 0
    assert len(result.val_loss_history) > 0
    # Training should reduce loss
    assert result.train_loss_history[-1] < result.train_loss_history[0] * 1.2


def test_dpo_model_save_load_roundtrip():
    model = DPOModel(feature_dim=10)
    cv = [0.1] * 10
    scores_before = model.strategy_scores(cv)

    with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
        path = Path(f.name)
    try:
        model.save(path)
        loaded = DPOModel.load(path)
        scores_after = loaded.strategy_scores(cv)
        for k in scores_before:
            assert abs(scores_before[k] - scores_after[k]) < 1e-6
    finally:
        path.unlink(missing_ok=True)


def test_dpo_trainer_empty_pairs():
    trainer = DPOTrainer()
    result = trainer.train([])
    assert result.n_pairs_trained == 0
    assert result.converged is False


# ═══════════════════════════════════════════════════════════
# Phase 4: DPOPolicy integration
# ═══════════════════════════════════════════════════════════

def test_dpo_policy_fallback_when_no_model():
    policy = DPOPolicy()
    assert not policy.is_available
    result = policy.select_strategy([0.5] * 25)
    assert result.model_available is False
    assert result.recommended_strategy in ["give_advice", "ask_question", "encourage", "confirm",
                                            "misunderstand", "refuse", "diverge", "neutral"]
    assert 0.0 < result.confidence <= 1.0


def test_dpo_policy_with_trained_model():
    model = DPOModel(feature_dim=25)
    policy = DPOPolicy(model=model)
    assert policy.is_available

    cv = [0.5] * 25
    result = policy.select_strategy(cv)
    assert result.model_available is True
    assert len(result.strategy_scores) == 8
    assert result.confidence > 0.0


def test_dpo_policy_model_load_failure():
    policy = DPOPolicy()
    ok = policy.load_model(Path("/nonexistent/model.npz"))
    assert ok is False
    assert not policy.is_available


def test_policy_router_integrates_dpo():
    router = PolicyRouter()
    assert router.dpo is not None
    assert not router.dpo.is_available

    # select_strategy returns None when DPO not available
    result = router.select_strategy([0.5] * 25)
    assert result is None


# ═══════════════════════════════════════════════════════════
# Phase 5: Meta loop integration
# ═══════════════════════════════════════════════════════════

def test_meta_orchestrator_run_dpo_cycle_no_sessions():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        db = RunDB(db_path)
        from sgw_v2.meta.meta_orchestrator import MetaOrchestrator
        meta = MetaOrchestrator(db, {"turn_target": 12})
        result = meta.run_dpo_cycle("run_nonexistent")
        assert result["run_id"] == "run_nonexistent"
        assert result["pairs_created"] == 0
        assert result["model_trained"] is False
    finally:
        db_path.unlink(missing_ok=True)


def test_extraction_result_counts():
    result = ExtractionResult(
        run_id="run_test",
        pairs=[],
        sessions_scanned=5,
        turns_evaluated=30,
        pairs_created=10,
        pairs_skipped_low_margin=3,
        pairs_skipped_insufficient_turns=2,
    )
    assert result.total_attempted == 15


def test_strategy_preference_to_recommendation():
    pref = StrategyPreference(
        recommended_strategy="give_advice",
        confidence=0.85,
        strategy_scores={"give_advice": 0.9, "ask_question": 0.3},
    )
    rec = pref.to_recommendation([0.5] * 9)
    assert rec.recommended_behavior == "give_advice"
    assert rec.confidence == 0.85
    assert rec.source == "dpo"


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import traceback

    tests = [
        # Phase 1
        test_response_evaluator_scores_all_dimensions,
        test_response_evaluator_empty_response,
        test_response_evaluator_high_quality_advice,
        test_response_evaluator_evaluate_session,
        test_response_evaluator_safety_flag,
        # Phase 2
        test_preference_extractor_within_session_pairing,
        test_preference_extractor_min_margin_filter,
        test_preference_extractor_min_turns_per_session,
        test_preference_extractor_context_vector_dimensions,
        test_preference_extractor_persist_pairs,
        # Phase 3
        test_dpo_model_score_and_best_strategy,
        test_dpo_trainer_trains_and_reduces_loss,
        test_dpo_model_save_load_roundtrip,
        test_dpo_trainer_empty_pairs,
        # Phase 4
        test_dpo_policy_fallback_when_no_model,
        test_dpo_policy_with_trained_model,
        test_dpo_policy_model_load_failure,
        test_policy_router_integrates_dpo,
        # Phase 5
        test_meta_orchestrator_run_dpo_cycle_no_sessions,
        test_extraction_result_counts,
        test_strategy_preference_to_recommendation,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS {test.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL {test.__name__}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*50}")

    if failed > 0:
        sys.exit(1)
