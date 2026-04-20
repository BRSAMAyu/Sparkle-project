"""Conversation state machine and arc generator.

Replaces the mechanical turn_index % N approach with:
- ConversationArc: session-level narrative structure
- TurnDecision: per-turn direction output
- StateMachine: event-driven transitions between beats
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .ai_behavior_classifier import AIBehaviorClass, classify_ai_response, classify_confidence


# ── Conversation Beat ──────────────────────────────────

@dataclass
class ConversationBeat:
    beat_id: str
    turn_range: tuple[int, int]   # [start, end] inclusive
    emotional_vector: str          # "低落" | "好奇" | "焦虑" | "振奋" | "烦躁" | "平静" | "自由"
    topic_hint: str                # Direction hint (NOT a script)
    allow_skip: bool = False
    transition_triggers: list[str] = field(default_factory=list)

    def contains_turn(self, turn_index: int) -> bool:
        return self.turn_range[0] <= turn_index <= self.turn_range[1]


# ── Fallback beat ──────────────────────────────────────

FALLBACK_BEAT = ConversationBeat(
    beat_id="fallback",
    turn_range=(999, 9999),
    emotional_vector="自由",
    topic_hint="自然继续对话，可以引入新话题或深化当前话题",
    allow_skip=False,
    transition_triggers=[],
)


# ── ConversationArc ────────────────────────────────────

# Pre-defined arc templates mapped to persona types
ARC_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "exam_rising": [
        {"beat_id": "opening", "turn_range": [1, 3], "emotional_vector": "焦虑",
         "topic_hint": "提到最近的考试或作业压力，表达焦虑或困扰"},
        {"beat_id": "engagement", "turn_range": [4, 7], "emotional_vector": "好奇",
         "topic_hint": "试探性地听AI建议或提出具体问题"},
        {"beat_id": "resolution", "turn_range": [8, 12], "emotional_vector": "振奋",
         "topic_hint": "有点进展或收获，寻求确认或进一步指导"},
    ],
    "exam_oscillating": [
        {"beat_id": "complaint", "turn_range": [1, 3], "emotional_vector": "烦躁",
         "topic_hint": "抱怨学习或考试相关的事情"},
        {"beat_id": "half_try", "turn_range": [4, 6], "emotional_vector": "半信半疑",
         "topic_hint": "对AI的建议表示怀疑或只愿意试一部分"},
        {"beat_id": "setback", "turn_range": [7, 9], "emotional_vector": "低落",
         "topic_hint": "遇到困难或挫折，想放弃或换个方向"},
        {"beat_id": "recovery", "turn_range": [10, 12], "emotional_vector": "平静",
         "topic_hint": "情绪缓和，可能接受帮助或决定下一步"},
    ],
    "interest_exploring": [
        {"beat_id": "discovery", "turn_range": [1, 3], "emotional_vector": "好奇",
         "topic_hint": "分享最近发现的新兴趣或新话题"},
        {"beat_id": "deepening", "turn_range": [4, 8], "emotional_vector": "兴奋",
         "topic_hint": "深入了解这个兴趣，问AI具体问题"},
        {"beat_id": "commitment", "turn_range": [9, 12], "emotional_vector": "坚定",
         "topic_hint": "考虑制定学习计划或深入钻研"},
    ],
    "career_confused": [
        {"beat_id": "confusion", "turn_range": [1, 3], "emotional_vector": "焦虑",
         "topic_hint": "表达对未来方向的困惑或不确定"},
        {"beat_id": "exploration", "turn_range": [4, 7], "emotional_vector": "思考中",
         "topic_hint": "探索不同可能性，与AI讨论选项"},
        {"beat_id": "decision", "turn_range": [8, 12], "emotional_vector": "平静",
         "topic_hint": "逐步缩小范围，做出初步决定或制定行动"},
    ],
}


def generate_arc(arc_shape: str = "", rng: random.Random | None = None) -> list[ConversationBeat]:
    """Generate a ConversationArc from templates or random selection."""
    rng = rng or random.Random()
    if not arc_shape:
        arc_shape = rng.choice(list(ARC_TEMPLATES.keys()))

    template = ARC_TEMPLATES.get(arc_shape, ARC_TEMPLATES["exam_rising"])
    beats = []
    for t in template:
        beats.append(ConversationBeat(
            beat_id=t["beat_id"],
            turn_range=tuple(t["turn_range"]),
            emotional_vector=t["emotional_vector"],
            topic_hint=t["topic_hint"],
            allow_skip=t.get("allow_skip", False),
            transition_triggers=t.get("transition_triggers", []),
        ))
    return beats


# ── TurnDecision ───────────────────────────────────────

@dataclass
class TurnDecision:
    direction: str                 # What the user should do next
    target_reference: str | None   # Should reference specific AI content
    emotional_tone: str            # Emotional tone for expression
    must_include: list[str]        # Required elements
    must_avoid: list[str]          # Forbidden elements
    source: str = "state_machine"
    confidence: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "target_reference": self.target_reference,
            "emotional_tone": self.emotional_tone,
            "must_include": self.must_include,
            "must_avoid": self.must_avoid,
            "source": self.source,
            "confidence": self.confidence,
        }


# ── State Machine ──────────────────────────────────────

class ConversationStateMachine:
    """Event-driven state machine for conversation flow.

    Input: (current_beat, last_ai_behavior, turn_index)
    Output: TurnDecision
    """

    def __init__(self, beats: list[ConversationBeat], rng: random.Random | None = None):
        self.beats = beats + [FALLBACK_BEAT]
        self.rng = rng or random.Random()
        self.current_beat_index = 0

    @property
    def current_beat(self) -> ConversationBeat:
        if self.current_beat_index < len(self.beats):
            return self.beats[self.current_beat_index]
        return FALLBACK_BEAT

    def advance_to_beat_for_turn(self, turn_index: int) -> None:
        """Ensure we're on the correct beat for the given turn index."""
        for i, beat in enumerate(self.beats):
            if beat.contains_turn(turn_index):
                if i > self.current_beat_index:
                    self.current_beat_index = i
                return

    def decide(
        self,
        turn_index: int,
        ai_behavior: AIBehaviorClass,
        last_ai_response: str | None = None,
        persona_compliance: float = 0.5,
    ) -> TurnDecision:
        """Generate a TurnDecision based on conversation context."""
        self.advance_to_beat_for_turn(turn_index)
        beat = self.current_beat

        # Determine direction based on AI behavior + beat
        direction, target_ref, must_include, must_avoid = self._map_behavior_to_direction(
            ai_behavior, beat, turn_index, persona_compliance
        )

        return TurnDecision(
            direction=direction,
            target_reference=target_ref,
            emotional_tone=beat.emotional_vector,
            must_include=must_include,
            must_avoid=must_avoid,
            source="state_machine",
            confidence=classify_confidence(last_ai_response or "", ai_behavior),
        )

    def _map_behavior_to_direction(
        self,
        ai_behavior: AIBehaviorClass,
        beat: ConversationBeat,
        turn_index: int,
        compliance: float,
    ) -> tuple[str, str | None, list[str], list[str]]:
        """Map (AI behavior, beat) → (direction, reference, must_include, must_avoid).

        Returns:
            direction: What the user should do
            target_ref: What part of AI response to reference
            must_include: Required elements in the message
            must_avoid: Forbidden elements
        """
        target_ref = None
        must_include: list[str] = []
        must_avoid: list[str] = ["empty_acknowledgment"]

        if turn_index == 1:
            # First turn: opening
            direction = "开场"
            must_include = ["opening_context"]
            return direction, target_ref, must_include, must_avoid

        if ai_behavior == AIBehaviorClass.ASK_QUESTION:
            direction = "回答问题"
            target_ref = "AI刚才问的问题"
            # 90% chance of answering, 10% chance of deflecting
            if self.rng.random() < 0.1:
                direction = "回避问题或转移话题"
                target_ref = None
            return direction, target_ref, must_include, must_avoid

        if ai_behavior == AIBehaviorClass.GIVE_ADVICE:
            # React to advice based on compliance level
            roll = self.rng.random()
            if roll < compliance * 0.6:
                direction = "接受并尝试建议"
                target_ref = "AI建议中的具体一步"
                must_include = ["specific_reference"]
            elif roll < compliance * 0.6 + 0.3:
                direction = "质疑或追问建议"
                target_ref = "AI建议中不太理解的部分"
                must_include = ["specific_reference"]
            else:
                direction = "觉得建议太多，想从最重要的开始"
                target_ref = "AI建议中最重要的那一条"
                must_include = ["specific_reference"]
            return direction, target_ref, must_include, must_avoid

        if ai_behavior == AIBehaviorClass.ENCOURAGE:
            direction = "对鼓励的反应"
            if self.rng.random() < 0.5:
                direction = "转移话题（被夸不太自在）"
                must_avoid.append("thank_you_only")
            else:
                direction = "顺着鼓励继续说自己的情况"
                target_ref = "刚才聊到的困难"
            return direction, target_ref, must_include, must_avoid

        if ai_behavior == AIBehaviorClass.MISUNDERSTAND:
            direction = "纠正AI的理解"
            target_ref = "AI理解错的地方"
            must_include = ["clarification"]
            return direction, target_ref, must_include, must_avoid

        if ai_behavior == AIBehaviorClass.CONFIRM:
            direction = "确认或补充AI的总结"
            target_ref = "AI总结的内容"
            return direction, target_ref, must_include, must_avoid

        if ai_behavior == AIBehaviorClass.REFUSE:
            direction = "对拒绝的反应"
            if self.rng.random() < 0.5:
                direction = "换个角度再问"
            else:
                direction = "接受并转向其他话题"
            return direction, target_ref, must_include, must_avoid

        # NEUTRAL or DIVERGE: follow beat direction
        direction = "自然接话"
        if beat.emotional_vector in ("好奇", "兴奋"):
            direction = "顺着当前话题深入"
        elif beat.emotional_vector in ("低落", "焦虑"):
            direction = "表达感受或寻求帮助"
        elif beat.emotional_vector in ("烦躁",):
            direction = "继续抱怨或发泄"
        return direction, target_ref, must_include, must_avoid


# ── Persona BehaviorSampler ────────────────────────────

@dataclass
class BehaviorSample:
    """A concrete sample from the three persona axes."""
    compliance: float = 0.5
    digression_rate: float = 0.2
    challenge_tendency: float = 0.3
    responsiveness: float = 0.6
    emotion_intensity: float = 0.5


# Mapping from persona_library.json fields to behavior axis
_AGE_STAGE_COMPLIANCE = {
    "middle_school": 0.25,
    "high_school": 0.35,
    "university": 0.50,
    "working_adult": 0.60,
}

_GOAL_CHALLENGE = {
    "exam": 0.2,
    "interest": 0.5,
    "career_transition": 0.35,
}

_STYLE_EMOTION = {
    "fragmented": 0.5,
    "narrative": 0.4,
    "emotional": 0.8,
}

_STYLE_DIGRESSION = {
    "fragmented": 0.4,
    "narrative": 0.15,
    "emotional": 0.3,
}


def sample_behavior_from_persona(
    persona: dict[str, Any],
    rng: random.Random | None = None,
) -> BehaviorSample:
    """Sample behavior axis values from a seed persona definition."""
    rng = rng or random.Random()

    age = persona.get("age_stage", "university")
    goal = persona.get("goal", "interest")
    style = persona.get("style", "narrative")
    mention_density = float(persona.get("mention_density", 0.15))
    commitment_density = float(persona.get("commitment_density", 0.1))

    # Base values from persona fields
    base_compliance = _AGE_STAGE_COMPLIANCE.get(age, 0.5)
    base_challenge = _GOAL_CHALLENGE.get(goal, 0.3)
    base_emotion = _STYLE_EMOTION.get(style, 0.5)
    base_digression = _STYLE_DIGRESSION.get(style, 0.2)

    # Add noise (±20% of base)
    def jitter(val: float, scale: float = 0.2) -> float:
        return max(0.0, min(1.0, val + rng.gauss(0, val * scale)))

    return BehaviorSample(
        compliance=jitter(base_compliance + commitment_density * 0.3),
        digression_rate=jitter(base_digression + mention_density * 0.2),
        challenge_tendency=jitter(base_challenge),
        responsiveness=jitter(0.6 if style != "fragmented" else 0.4),
        emotion_intensity=jitter(base_emotion),
    )


# ── Arc shape selector ─────────────────────────────────

_GOAL_ARC_SHAPES = {
    "exam": ["exam_rising", "exam_oscillating"],
    "interest": ["interest_exploring"],
    "career_transition": ["career_confused"],
}


def select_arc_shape(persona: dict[str, Any], rng: random.Random | None = None) -> str:
    """Select an arc shape based on persona goal."""
    rng = rng or random.Random()
    goal = persona.get("goal", "interest")
    shapes = _GOAL_ARC_SHAPES.get(goal, ["exam_rising"])
    return rng.choice(shapes)
