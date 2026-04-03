from __future__ import annotations


SCENARIOS: dict[str, dict[str, object]] = {
    "knowledge_debate": {
        "description": "围绕一个知识点，AI 生成正反方论点，用户参与辩论。",
        "participants": ["正方专家", "反方专家", "主持人"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["concept", "textbook_passage", "error_record"],
        "facilitation_hint": "围绕具体材料展开正反论证，并用反例检测理解边界。",
    },
    "historical_roleplay": {
        "description": "历史事件角色扮演，用户作为关键角色推进推演。",
        "participants_from": "knowledge_graph",
        "participants": ["历史导师", "关键人物", "时代观察者"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["historical_source"],
        "facilitation_hint": "必须提供历史材料作为讨论基础，避免脱离史料自由发挥。",
    },
    "study_group": {
        "description": "虚拟学习小组讨论，每个 AI 有不同理解层次。",
        "participants": ["优等生", "中等生", "提问者"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["concept", "textbook_passage", "error_record"],
        "facilitation_hint": "围绕具体材料展开多角度分析。",
    },
    "socratic_dialogue": {
        "description": "苏格拉底式对话，AI 用问题引导用户自己推导结论。",
        "participants": ["苏格拉底"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["concept", "textbook_passage", "case"],
        "facilitation_hint": "优先通过连续追问检验理解深度，而不是直接给结论。",
    },
    "case_analysis": {
        "description": "围绕具体案例拆解决策过程，定位哪一步最容易失误。",
        "participants": ["案例导师", "诊断官", "实践派"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["case", "error_record"],
        "facilitation_hint": "始终围绕案例材料定位判断链条中的薄弱环节。",
    },
    "what_if_path": {
        "description": "比较不同学习选择带来的后果，适合做 What-If 推演。",
        "participants": ["当前路线", "激进路线", "风险观察者"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["concept", "case", "error_record"],
        "facilitation_hint": "围绕同一锚点比较不同选择的后果，不做脱锚发挥。",
    },
    "concept_map_build": {
        "description": "协作搭建概念图，把前置依赖和关键桥梁节点说清楚。",
        "participants": ["结构师", "连接者", "提问者"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["concept", "textbook_passage"],
        "facilitation_hint": "把锚点材料拆成概念、关系和前置依赖。",
    },
    "error_diagnosis": {
        "description": "从错误现象倒推根因，形成可执行修补方案。",
        "participants": ["错因分析师", "纠偏教练", "验证者"],
        "rounds": "dynamic",
        "recommended_anchor_types": ["error_record"],
        "facilitation_hint": "分析错误原因，不直接给答案。",
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
