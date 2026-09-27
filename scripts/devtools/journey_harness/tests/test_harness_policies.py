"""网络切换/test clock/诚实 unsupported 策略单测（B-03 work#2，无设备依赖）。

统一化裁决落点：
- set_network：web=CDP（浏览器栈内真实生效）、android=系统飞行模式；
  macos/api 明确 unsupported 并登记原因（验收「明确 unsupported 原因」），
  不允许静默跳过或假成功。
- 能力校验先于设备触达：未知 mode/不支持的平台在触达任何设备/浏览器前即失败。

运行：
    pytest scripts/devtools/journey_harness/tests/test_harness_policies.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS_DIR))

from harness.drivers.android_driver import AndroidDriver  # noqa: E402
from harness.drivers.api_driver import ApiDriver  # noqa: E402
from harness.drivers.base import StepFailure  # noqa: E402
from harness.drivers.macos_driver import MacosDriver  # noqa: E402
from harness.drivers.web_driver import WebDriver  # noqa: E402
from harness.evidence import EvidenceCollector  # noqa: E402


@pytest.fixture()
def evidence(tmp_path: Path) -> EvidenceCollector:
    return EvidenceCollector(tmp_path, "policy_t")


def test_web_network_presets() -> None:
    assert set(WebDriver.NETWORK_PRESETS) == {"offline", "online", "slow"}
    assert WebDriver.NETWORK_PRESETS["offline"]["offline"] is True
    assert WebDriver.NETWORK_PRESETS["online"]["offline"] is False
    # slow 默认即 DevTools Slow-3G 同源档（400ms/400kbps）
    assert WebDriver.NETWORK_PRESETS["slow"]["latency"] == 400


def test_web_set_network_unknown_mode_fails_before_browser(evidence: EvidenceCollector) -> None:
    driver = WebDriver(evidence, {})
    assert driver.cdp is None  # 无浏览器
    with pytest.raises(StepFailure, match="bogus"):
        driver.do_set_network("bogus")


def test_android_set_network_slow_is_honest_unsupported(evidence: EvidenceCollector) -> None:
    driver = AndroidDriver(evidence, {})
    with pytest.raises(StepFailure, match="限速"):
        driver.do_set_network("slow")


def test_macos_set_network_unsupported_with_reason(evidence: EvidenceCollector) -> None:
    driver = MacosDriver(evidence, {})
    with pytest.raises(StepFailure, match="seam"):
        driver.do_set_network("offline")


def test_api_set_network_unsupported_with_reason(evidence: EvidenceCollector) -> None:
    driver = ApiDriver(evidence, {})
    with pytest.raises(StepFailure, match="non-ui"):
        driver.do_set_network("online")


def test_android_ui_steps_unsupported_is_explicit(evidence: EvidenceCollector) -> None:
    """基线诚实声明钉：android UI 步进 unsupported 必须继续显式失败，不得冒充。"""
    driver = AndroidDriver(evidence, {})
    with pytest.raises(StepFailure, match="UI 步进"):
        driver.do_ui_steps_unsupported()


def test_api_wait_for_select_only(evidence: EvidenceCollector) -> None:
    """DB 探针只读纪律钉：非 SELECT 一律拒绝（触达任何设备前即失败）。"""
    driver = ApiDriver(evidence, {})
    with pytest.raises(StepFailure, match="SELECT"):
        driver.do_wait_for(kind="x", sql="DELETE FROM users", timeout=0.1)
