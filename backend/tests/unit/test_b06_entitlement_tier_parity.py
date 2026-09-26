"""B-06 审计面二观察收口：entitlement 判级 Python/Go 受控双实现跨语言等价测试（引擎侧）。

双实现注释互认（V3-FIX-02 / D17 冻结决策）：
- 引擎真源：``app/core/entitlement.normalize_entitlement / entitlement_effective``
- 网关副本：``backend/gateway/internal/service/user_context.go
  IsProEntitlement / IsProEntitlementEffective``

等价测试设计（B06_ENTITY_TRUTH_BASELINE.md §2.2-4 观察 / §4 建议 5）：测试向量
**单源** JSON、双端测试各自消费（方案 a）——同一输入集（值域典型值/大小写/空白
边界/值域外非法值/到期与边界时刻）分别喂两端判级函数，断言输出全等：

    backend/tests/fixtures/entitlement_tier_vectors.json
      ├── cases              双端共享（本测试 + gateway entitlement_tier_parity_test.go）
      └── python_only_cases  引擎单侧（Go 调用面不存在的能力）：
                             raw=None/0/false（normalize 的 object|None 假值坍缩面）、
                             expires_at == now 精确边界与 1µs 邻域（Go
                             IsProEntitlementEffective 内取 time.Now() 无注入钟）、
                             tz-aware/naive expiry 的 ensure_naive_utc 归一语义。

两侧判级语义任一改动必须同卡同步另一侧并更新向量文件（任一侧红即漂移报警，
值集/边界行为漂移从此有门；ENUM-PARITY 不覆盖本面——判级函数非枚举镜像）。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.core.entitlement import (
    entitlement_effective,
    entitlement_effective_grants_pro,
    entitlement_grants_pro,
    normalize_entitlement,
)

VECTOR_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "entitlement_tier_vectors.json"


def _load_vectors() -> dict:
    with VECTOR_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _parse_ts(value: str | None) -> datetime | None:
    """向量 ISO 时刻 → datetime（Z 后缀归一为 +00:00；naive 串保持 naive）。"""
    if value is None:
        return None
    return datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)


def _assert_case(case: dict, now: datetime | None) -> None:
    raw = case["raw"]
    expires_at = _parse_ts(case["expires_at"])

    # 无 expiry 面：normalize_entitlement ⟺ 网关 IsProEntitlement
    tier = normalize_entitlement(raw)
    assert tier == case["expected_no_expiry"], (
        f"{case['id']}: normalize_entitlement({raw!r}) = {tier!r}, "
        f"want {case['expected_no_expiry']!r} ({case['note']})"
    )
    assert entitlement_grants_pro(raw) is (tier == "pro")

    # 到期面：entitlement_effective ⟺ 网关 IsProEntitlementEffective
    effective = entitlement_effective(raw, expires_at, now=now)
    assert effective == case["expected_effective"], (
        f"{case['id']}: entitlement_effective({raw!r}, {case['expires_at']!r}, "
        f"now={case['now']!r}) = {effective!r}, want {case['expected_effective']!r} "
        f"({case['note']})"
    )
    assert entitlement_effective_grants_pro(raw, expires_at, now=now) is (effective == "pro")


@pytest.mark.parametrize(
    "case",
    _load_vectors()["cases"],
    ids=lambda case: case["id"],
)
def test_entitlement_tier_parity_shared_vectors(case: dict) -> None:
    """共享向量：双端同输入全等（Go 侧同文件消费于 entitlement_tier_parity_test.go）。"""
    _assert_case(case, now=None)


@pytest.mark.parametrize(
    "case",
    _load_vectors()["python_only_cases"],
    ids=lambda case: case["id"],
)
def test_entitlement_tier_parity_python_only_vectors(case: dict) -> None:
    """引擎单侧向量：注入 now 钟面 / 假值坍缩 / tz 归一（Go 面不存在，注释于向量文件）。"""
    _assert_case(case, now=_parse_ts(case["now"]))


def test_vectors_internal_consistency() -> None:
    """向量自检：expires_at=NULL（永久）时到期面必须与无 expiry 面同判（契约不变量）。"""
    vectors = _load_vectors()
    for case in vectors["cases"]:
        if case["expires_at"] is None:
            assert (
                case["expected_no_expiry"] == case["expected_effective"]
            ), f"{case['id']}: 永久到期面应与无 expiry 面同判"
