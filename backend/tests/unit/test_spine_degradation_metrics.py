from app.core.business_metrics import SPINE_DEGRADATION_TOTAL, record_spine_degradation, snapshot_metric


def test_record_spine_degradation_increments_labelled_counter() -> None:
    before = snapshot_metric(SPINE_DEGRADATION_TOTAL).get("surface=chat_turn,reason=RuntimeError", 0.0)

    record_spine_degradation("chat_turn", RuntimeError("redis unavailable"))

    after = snapshot_metric(SPINE_DEGRADATION_TOTAL)["surface=chat_turn,reason=RuntimeError"]
    assert after == before + 1
