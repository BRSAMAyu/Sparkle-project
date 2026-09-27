"""V3-FIX-345 处置守卫（wt655）：fme_kill_switch 半假开关死绑定撤面.

原状（wt652 深查亲证）：服务 docstring 宣称治理两特性，但
``task_card_protocol_v2`` 绑定全仓零读者——TaskCardProtocol 真实渲染链
（GET /tasks/{id}/card-protocol + mobile interactive_task_card.dart）不查
开关；且 set_feature_mode/summary 零生产调用方，两开关均无运行时翻转
API（只能改 env）。第二开关属 FIX-341「假开关」模块内同形态：宣称的
治理能力无兑现路径；settings 默认 shadow 更制造「shadow 运行中」假象。

裁决=撤死绑定（FIX-341 先例）：task_card_protocol_v2 是渲染协议而非
analyzer 特性，off/shadow/live 三态语义对其无定义（何谓 render 的
shadow？），接线只会制造语义不明的第二个假开关。goal_first_minute
半边全链真实（analyze-intent 门控+mobile+gateway O10 回归），保留。

本守卫断言：
  - FEATURE_BINDINGS 只含真实读者特性（task_card_protocol_v2 不可复活）；
  - settings 不再声明 FME_TASK_CARD_PROTOCOL_MODE；
  - 每个注册特性在 backend/app 存在 get_feature_mode 生产读者
    （防再挂回零读者死绑定——守卫判据从「必须注册」反转为「注册即须真实」）；
  - 存活面 goal_first_minute 三态门控语义不回退。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.config import settings
from app.services import fme_kill_switch_service as fme_module
from app.services.fme_kill_switch_service import fme_kill_switch_service

BACKEND_APP_ROOT = Path(fme_module.__file__).resolve().parents[1]

EXPECTED_FEATURES = {"goal_first_minute"}
RETIRED_FEATURES = {"task_card_protocol_v2"}


def test_feature_bindings_match_real_readers() -> None:
    """注册表恰等于真实读者集：死绑定不可复活，真实开关不缺席."""
    assert set(fme_kill_switch_service.FEATURE_BINDINGS) == EXPECTED_FEATURES
    for retired in RETIRED_FEATURES:
        assert retired not in fme_kill_switch_service.FEATURE_BINDINGS, (
            f"{retired} 零读者死绑定已随 V3-FIX-345 撤面；重建须先把"
            " card-protocol 渲染链接上 get_feature_mode 并更新本守卫"
        )


def test_settings_no_longer_declares_retired_mode() -> None:
    assert not hasattr(settings, "FME_TASK_CARD_PROTOCOL_MODE")


def test_summary_and_unknown_feature_semantics() -> None:
    """summary 只报注册特性；未注册特性名如实拒绝而非虚报 shadow."""
    import asyncio

    summary = asyncio.run(fme_kill_switch_service.summary())
    assert set(summary) == EXPECTED_FEATURES
    for retired in RETIRED_FEATURES:
        with pytest.raises(ValueError):
            asyncio.run(fme_kill_switch_service.get_feature_mode(retired))


def test_every_registered_feature_has_production_reader() -> None:
    """注册即须真实：每个绑定在服务自身之外存在 get_feature_mode 生产读者."""
    source_files = [
        p
        for p in BACKEND_APP_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts and p.name != "fme_kill_switch_service.py"
    ]
    assert source_files, "backend/app 源码扫描面为空（扫描根配置错误）"
    for feature in fme_kill_switch_service.FEATURE_BINDINGS:
        pattern = re.compile(rf'get_feature_mode\(\s*[\'"]{re.escape(feature)}[\'"]')
        readers = [p for p in source_files if pattern.search(p.read_text(encoding="utf-8"))]
        assert readers, f"FME 特性 {feature} 注册但零生产读者（死开关复活）"


@pytest.mark.parametrize("mode,expected", [("off", "off"), ("shadow", "shadow"), ("live", "live")])
async def test_goal_first_minute_tristate_gate_intact(
    monkeypatch: pytest.MonkeyPatch, mode: str, expected: str
) -> None:
    """存活面钉死：goal_first_minute 三态语义（env 判据+Redis 覆盖）不回退."""
    from app.core.cache import cache_service

    monkeypatch.setattr(settings, "FME_GOAL_FIRST_MINUTE_MODE", mode, raising=False)
    monkeypatch.setattr(cache_service, "redis", None)  # env 判据唯一生效
    assert await fme_kill_switch_service.get_feature_mode("goal_first_minute") == expected
