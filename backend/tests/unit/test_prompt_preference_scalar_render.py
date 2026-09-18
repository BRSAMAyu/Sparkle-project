"""偏好标量渲染回归：画像脏数据（dict/str 形态的偏好值）不得炸掉 prompt 渲染链。

背景（V2.5 deep_analysis qwen3.8-flash 复验 q1 实证）：
`_render_user_context_content` 对 `depth_preference` 直接 `:.1f` 格式化，
画像管道中出现 `{"value": x}` 包装 dict 时抛
`TypeError: unsupported format string passed to dict.__format__`，
generation 节点整体失败 → deep_analysis 档空回复（finish=STOP, 0 delta）。
"""
from app.orchestration.prompts import _preference_scalar, _render_user_context_content


def test_preference_scalar_passthrough_float() -> None:
    assert _preference_scalar(0.3) == 0.3
    assert _preference_scalar(0.5, 0.5) == 0.5


def test_preference_scalar_numeric_string() -> None:
    assert _preference_scalar("0.7") == 0.7


def test_preference_scalar_value_wrapped_dict() -> None:
    # users.py / profile_transparency.py 的写入形态：{"value": x}
    assert _preference_scalar({"value": 0.8}) == 0.8


def test_preference_scalar_junk_dict_falls_back_to_default() -> None:
    assert _preference_scalar({"deep": True}, 0.5) == 0.5
    assert _preference_scalar({"value": "很深"}, 0.5) == 0.5


def test_preference_scalar_none_and_junk_fall_back_to_default() -> None:
    assert _preference_scalar(None) == 0.5
    assert _preference_scalar("偏好很高") == 0.5
    assert _preference_scalar(["high"], 0.2) == 0.2


def test_render_user_context_survives_dict_shaped_preference() -> None:
    text, _telemetry = _render_user_context_content(
        {
            "preferences": {
                "depth_preference": {"value": 0.8},
                "curiosity_preference": {"value": 0.6},
            }
        }
    )
    assert "- 深度: 0.8" in text
    assert "- 好奇心: 0.6" in text


def test_render_user_context_survives_string_preference() -> None:
    text, _telemetry = _render_user_context_content(
        {
            "preferences": {
                "depth_preference": "非常深",
                "curiosity_preference": None,
            }
        }
    )
    assert "- 深度: 0.5" in text
    assert "- 好奇心: 0.5" in text


def test_default_preference_instructions_survive_dict_shaped_preference() -> None:
    """V2.5 q1 复测实证的第二崩溃点：_get_default_preference_instructions 对
    {"value": 0.5} 形态的 depth_preference 做 >= 比较 → TypeError，
    generation 节点失败 → deep_analysis 空回复。"""
    from app.orchestration.prompts import _get_default_preference_instructions

    text = _get_default_preference_instructions(
        {
            "profile": {
                "preferences": {
                    "depth_preference": {"value": 0.5},
                    "curiosity_preference": {"value": 0.5},
                }
            }
        }
    )
    assert "回答深度：适中" in text
    assert "探索倾向：适中" in text


def test_default_preference_instructions_thresholds_with_wrapped_values() -> None:
    from app.orchestration.prompts import _get_default_preference_instructions

    text = _get_default_preference_instructions(
        {
            "profile": {
                "preferences": {
                    "depth_preference": {"value": 0.9},
                    "curiosity_preference": {"value": 0.1},
                }
            }
        }
    )
    assert "回答深度：深入详尽" in text
    assert "探索倾向：专注聚焦" in text
