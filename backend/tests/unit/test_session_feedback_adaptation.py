from app.orchestration.prompts import build_system_prompt
from app.orchestration.session_feedback import (
    SessionAdaptationContext,
    apply_session_feedback_visible_prefix,
    build_session_adaptation_context,
    build_session_feedback_instruction,
    detect_session_feedback_signal,
)


def test_detect_simplify_signal_applies_adaptation() -> None:
    signal = detect_session_feedback_signal(
        user_message="简单点说，我有点听不懂",
        previous_assistant_message="这里涉及条件概率和后验分布的更新过程。",
        previous_user_message="什么是贝叶斯更新？",
    )

    assert signal is not None
    assert signal.signal_type == "simplify"
    assert signal.applies_adaptation is True
    assert signal.visible_hint == "我换成更简洁的版本："


def test_detect_mismatch_has_higher_priority_than_expand() -> None:
    signal = detect_session_feedback_signal(
        user_message="不是这个意思，详细点讲我该怎么安排复习顺序",
        previous_assistant_message="我建议你先做几道题试试。",
        previous_user_message="我该怎么复习？",
    )

    assert signal is not None
    assert signal.signal_type == "mismatch"
    assert signal.applies_adaptation is True


def test_detect_topic_shift_is_observed_but_not_applied() -> None:
    signal = detect_session_feedback_signal(
        user_message="另外，明天怎么复习英语？",
        previous_assistant_message="刚才这道数学题的关键是先化简再代入。",
        previous_user_message="这道数学题怎么做？",
    )

    assert signal is not None
    assert signal.signal_type == "topic_shift"
    assert signal.applies_adaptation is False


def test_build_session_feedback_instruction_contains_exact_visible_prefix() -> None:
    signal = detect_session_feedback_signal(
        user_message="详细点，再举个例子",
        previous_assistant_message="核心结论是先定义目标。",
        previous_user_message="怎么制定计划？",
    )

    instruction = build_session_feedback_instruction(signal)

    assert signal is not None
    assert signal.signal_type == "expand"
    assert "我改用更展开的方式说明：" in instruction
    assert "至少补 1 个例子或类比" in instruction


def test_apply_visible_prefix_is_idempotent() -> None:
    signal = detect_session_feedback_signal(
        user_message="简单点说",
        previous_assistant_message="上一轮我给了很长的解释。",
        previous_user_message="什么是向量数据库？",
    )
    assert signal is not None

    first, visible_first = apply_session_feedback_visible_prefix("这是正文。", signal)
    second, visible_second = apply_session_feedback_visible_prefix(first, signal)

    assert visible_first is True
    assert visible_second is True
    assert first == second
    assert first.startswith("我换成更简洁的版本：")


def test_build_session_adaptation_context_keeps_latest_three_signals() -> None:
    base = SessionAdaptationContext(
        recent_signals=[
            {"signal_type": "approval"},
            {"signal_type": "topic_shift"},
            {"signal_type": "expand"},
        ]
    )
    signal = detect_session_feedback_signal(
        user_message="不是这个意思",
        previous_assistant_message="上一轮的方向偏掉了。",
        previous_user_message="帮我排计划",
    )

    context = build_session_adaptation_context(signal=signal, existing_context=base)

    assert signal is not None
    assert len(context.recent_signals) == 3
    assert context.recent_signals[0]["signal_type"] == "mismatch"
    assert context.applied_strategy == "mismatch"


def test_build_system_prompt_places_session_feedback_before_dual_core() -> None:
    prompt = build_system_prompt(
        user_context={"preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5}},
        conversation_history={"messages": []},
        intent_instruction="先回答用户当前问题。",
        session_feedback_instruction="用户刚要求更简洁，请立刻收短。",
        dual_core_instruction="先降低认知负荷，再推进执行。",
    )

    intent_pos = prompt.find("## 当前意图指令")
    feedback_pos = prompt.find("## 会话内反馈适配")
    dual_core_pos = prompt.find("## 双核心路由指令")

    assert intent_pos != -1
    assert feedback_pos != -1
    assert dual_core_pos != -1
    assert intent_pos < feedback_pos < dual_core_pos
