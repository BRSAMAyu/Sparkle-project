from app.config import settings
from app.orchestration.routing_engine import RoutingEngineMixin
from app.state_aggregator.schema import SufficiencySummaryValue


class _RoutingHarness(RoutingEngineMixin):
    pass


# ---------------------------------------------------------------------------
# V3-FIX-187：router sufficiency follow-up 分支判据必须走 stage20 三态门
#
# _build_stage20_prompt_additions 曾直读 legacy bool
# SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED，不读
# AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE——stage20 kill-switch off/shadow
# 不断该分支（治理面与行为面双权威分叉，同 V3-FIX-186 族）。
#
# shadow 档语义裁决（本卡）：follow-up 是用户可见的 prompt 行为指令
# （"在给出方案前，先只问这一句"），按 kill_switch 既有模式，用户可见
# 注入面统一为 live-only——stage21 技能 prompt 注入以 selection_mode ==
# "live" 为闸（routing_engine.py:1195），stage33/35/39 的 shadow 一律只记
# delta/候选比较不改 live prompt 与决策；stage20 sufficiency judge 本身即
# shadow 的观察通道（_collect_stage20_sufficiency 以 is_enabled=shadow|live
# 放行 judge 运行并持久化 judgment，routing_engine.py:1128 与
# state_aggregator/service.py:1138 同源）。故裁决为：off=不生成、
# shadow=不生成（观察由 judge 通道承接）、live=生成。与 V3-FIX-186 采用
# is_enabled_mode 的差异：186 是数据取数面（provider 选中后 fetch 携
# expose_shadow 标记、数据本身即观察物），本分支是行为面指令，与 stage21
# 同构。
#
# 修法 = 判据改走 kill_switch.resolve_settings_mode（V3-FIX-21 唯一判据，
# 复用 AuroraStage20KillSwitchService.BINDINGS["sufficiency_judge"] 同一
# binding）：tri-state 设置在场即唯一判据，legacy bool 仅缺席时兜底。
# ---------------------------------------------------------------------------


def _task_summary(score: float) -> SufficiencySummaryValue:
    return SufficiencySummaryValue(
        score=score,
        top_missing_dimensions=("target_object_resolved", "constraint_explicit"),
    )


def test_router_sufficiency_branch_only_uses_task_score(monkeypatch):
    """tri-state live（权威判据）下行为不变：score<0.6 生成 follow-up。"""
    monkeypatch.setattr(settings, "AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE", "live", raising=False)
    harness = _RoutingHarness()

    follow_up_question, context_caveat = harness._build_stage20_prompt_additions(
        task_summary=_task_summary(0.42),
        context_summary=SufficiencySummaryValue(
            score=0.2,
            top_missing_dimensions=("recent_user_state_known", "social_context_loaded"),
        ),
    )

    assert follow_up_question is not None
    assert "近期的活跃节奏" in context_caveat
    assert "社交背景" in context_caveat


def test_router_sufficiency_branch_stays_off_when_stage20_mode_off(monkeypatch):
    """tri-state off 下 follow-up 不生成；context_caveat 无门槛语义保持。"""
    monkeypatch.setattr(settings, "AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE", "off", raising=False)
    harness = _RoutingHarness()

    follow_up_question, context_caveat = harness._build_stage20_prompt_additions(
        task_summary=_task_summary(0.3),
        context_summary=SufficiencySummaryValue(
            score=0.4,
            top_missing_dimensions=("relevant_memory_present",),
        ),
    )

    assert follow_up_question is None
    assert "记忆线索" in context_caveat


def test_stage20_off_cannot_be_hijacked_open_by_legacy_bool_true(monkeypatch):
    """红测方向一：tri-state off 时 legacy bool True 不得顶开 follow-up 分支。"""
    monkeypatch.setattr(settings, "AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE", "off", raising=False)
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED", True, raising=False)
    harness = _RoutingHarness()

    follow_up_question, _ = harness._build_stage20_prompt_additions(
        task_summary=_task_summary(0.3),
        context_summary=None,
    )

    assert follow_up_question is None


def test_stage20_live_cannot_be_pushed_back_by_legacy_bool_false(monkeypatch):
    """红测方向二（对偶）：tri-state live 时 legacy bool False 不得压回分支。"""
    monkeypatch.setattr(settings, "AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED", False, raising=False)
    harness = _RoutingHarness()

    follow_up_question, _ = harness._build_stage20_prompt_additions(
        task_summary=_task_summary(0.3),
        context_summary=None,
    )

    assert follow_up_question is not None


def test_stage20_shadow_does_not_generate_follow_up(monkeypatch):
    """shadow 裁决钉测：shadow 不生成 follow-up（行为面 live-only，见文件头裁决注释）。"""
    monkeypatch.setattr(settings, "AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE", "shadow", raising=False)
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED", True, raising=False)
    harness = _RoutingHarness()

    follow_up_question, context_caveat = harness._build_stage20_prompt_additions(
        task_summary=_task_summary(0.3),
        context_summary=SufficiencySummaryValue(
            score=0.4,
            top_missing_dimensions=("relevant_memory_present",),
        ),
    )

    assert follow_up_question is None
    assert "记忆线索" in context_caveat


def test_legacy_bool_backfills_when_tri_state_setting_absent(monkeypatch):
    """未声明 tri-state 设置时 legacy bool 仍按 V3-FIX-21 语义兜底（缺席→live/off）。"""
    monkeypatch.delattr(settings, "AURORA_STAGE20_SUFFICIENCY_JUDGE_MODE", raising=False)
    harness = _RoutingHarness()

    monkeypatch.setattr(settings, "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED", True, raising=False)
    follow_up_question, _ = harness._build_stage20_prompt_additions(
        task_summary=_task_summary(0.3),
        context_summary=None,
    )
    assert follow_up_question is not None

    monkeypatch.setattr(settings, "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED", False, raising=False)
    follow_up_question, _ = harness._build_stage20_prompt_additions(
        task_summary=_task_summary(0.3),
        context_summary=None,
    )
    assert follow_up_question is None
