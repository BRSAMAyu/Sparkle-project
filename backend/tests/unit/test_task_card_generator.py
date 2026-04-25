from app.orchestration.task_card_generator import TaskCardGenerator


def _guide_json() -> dict:
    return {
        "objective": "Day 2：TCP 三次握手流程追踪",
        "output_action": "画出一次完整三次握手时序图，并标出关键报文。",
        "success_criteria": "能不看资料说出三次握手每一步的目的与关键标志位。",
        "method_steps": [
            "先写出三次握手里每一步的角色和目的。",
            "独立画出一次完整时序图。",
            "对照标准答案补关键标志位和序号。",
            "闭卷再重画一遍。",
        ],
        "common_mistakes": ["把 SYN、ACK 的作用混在一起。"],
        "minimum_output": "3 道快速检查题",
        "time_estimate_minutes": 28,
    }


def test_generator_uses_sprint_pack_template_when_available() -> None:
    result = TaskCardGenerator().generate(
        guide_json=_guide_json(),
        task_kind="retrieval_drill",
        subject="计算机网络",
        focus="TCP 三次握手流程",
        knowledge_state={
            "overall_mastery": 0.34,
            "weak_nodes": [{"node_name": "TCP 可靠传输"}],
        },
        aurora_control_signal={
            "strategy": {
                "concept_first": False,
                "problem_first": True,
            }
        },
    )

    assert result["task_card_pack_id"] == "computer_networks@v1"
    assert result["task_card_template_id"] == "process_trace_card"
    assert len(result["steps"]) == 4
    assert all(set(step.keys()) == {"name", "duration_min", "output"} for step in result["steps"])
    assert result["mini_quiz"]["pass_threshold"] == 0.5
    assert len(result["mini_quiz"]["items"]) == 3
    assert result["fallback_if_stuck"][0]["title"] == "先给半成品框架"
    assert any(trigger["code"] == "overall_mastery_below_0.4" for trigger in result["aurora_triggers"])


def test_generator_falls_back_to_existing_logic_when_pack_missing() -> None:
    result = TaskCardGenerator().generate(
        guide_json={
            "objective": "Day 1：极限与连续",
            "output_action": "先闭卷复述概念，再做 2 道基础题。",
            "success_criteria": "能说出定义并完成 2 道基础题。",
            "method_steps": [
                "先写出定义和关键词。",
                "不看答案做 2 道基础题。",
                "对照解析补关键缺口。",
            ],
            "minimum_output": "闭卷复述或小测",
            "time_estimate_minutes": 24,
        },
        task_kind="concept_review",
        subject="高等数学",
        focus="极限与连续",
        knowledge_state={"weak_nodes": ["极限定义"]},
        aurora_control_signal={"strategy": {"concept_first": True}},
    )

    assert "task_card_pack_id" not in result
    assert len(result["steps"]) == 4
    assert "闭卷复述或小测" in result["steps"][-1]["output"]
    assert len(result["done_criteria"]) >= 2
    assert result["mini_quiz"]["items"][0]["question"].startswith("不用看资料")
    assert len(result["fallback_if_stuck"]) == 3
    assert any(trigger["code"] == "accuracy_below_0.5" for trigger in result["aurora_triggers"])
