from __future__ import annotations


SCENARIOS: dict[str, dict[str, object]] = {
    "knowledge_debate": {
        "description": "围绕一个知识点，AI 生成正反方论点，用户参与辩论。",
        "participants": ["正方专家", "反方专家", "主持人"],
        "rounds": 5,
    },
    "historical_roleplay": {
        "description": "历史事件角色扮演，用户作为关键角色推进推演。",
        "participants_from": "knowledge_graph",
        "participants": ["历史导师", "关键人物", "时代观察者"],
        "rounds": 4,
    },
    "study_group": {
        "description": "虚拟学习小组讨论，每个 AI 有不同理解层次。",
        "participants": ["优等生", "中等生", "提问者"],
        "rounds": 3,
    },
    "socratic_dialogue": {
        "description": "苏格拉底式对话，AI 用问题引导用户自己推导结论。",
        "participants": ["苏格拉底"],
        "rounds": 4,
    },
}

DEFAULT_SCENARIO_KEY = "study_group"


def normalize_scenario_key(scenario_key: str | None) -> str:
    normalized = (scenario_key or "").strip()
    if not normalized:
        return DEFAULT_SCENARIO_KEY
    if normalized not in SCENARIOS:
        raise ValueError(f"Unsupported simulation scenario: {normalized}")
    return normalized
