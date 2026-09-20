"""D-06 · WVPL 事实 JSON golden 冻结（D-03 同款纪律：sha256 钉死 + 双审解冻）。

- 固定 fixture（与测试共享单份事实源 ``north_star_wvpl_fixture``）→
  ``build_fact(as_of=AS_OF, generated_at=AS_OF)`` → canonical JSON 必须与
  golden 文件逐字节一致；
- golden 变更 = 口径/公式变更，必须有意重冻结（更新 GOLDEN_SHA256）并过
  reviewer——聚合公式被任何改动（含无意的）即刻红；
- 变异证明（D-06 验收「改聚合公式 → golden 必红」）：对服务聚合公式的手工
  变异（loops 计数放宽 / 半开窗口改闭区间 / 分母剔除）均使本文件红；
  逐字节还原后复绿（证据见 v3-output/D-06/REPORT.md）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.core.north_star_wvpl import WVPL_CALIBER_VERSION, WVPL_FACT_SCHEMA
from app.services.north_star_wvpl_service import NorthStarWvplService, canonical_fact_json
from tests.golden.north_star_wvpl_fixture import AS_OF, build_standard_fixture

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "golden" / "north_star_wvpl_fact_golden.json"

# sha256 of the golden file captured at D-06 freeze (2026-09-20). Any change to
# the golden must be a deliberate re-freeze with reviewer sign-off (D-03 style).
GOLDEN_SHA256 = "f5ced526eda9a81c08d66a3c46298ce5d78af1b07155689fe4099d4a9f7b974b"


@pytest.fixture(name="golden")
def _golden() -> str:
    # golden 文件 = canonical JSON + 恰一个换行（POSIX 惯例）；比对时剥掉换行。
    return GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n")


@pytest.mark.asyncio
async def test_golden_file_sha256_frozen():
    digest = hashlib.sha256(GOLDEN_PATH.read_bytes()).hexdigest()
    assert digest == GOLDEN_SHA256, (
        "north_star_wvpl_fact_golden.json changed without re-freeze; "
        "update GOLDEN_SHA256 deliberately (caliber/formula change needs reviewer sign-off)"
    )


@pytest.mark.asyncio
async def test_golden_fact_matches_fixed_fixture(db_session, golden):
    await build_standard_fixture(db_session)
    fact = await NorthStarWvplService(db_session).build_fact(as_of=AS_OF, generated_at=AS_OF)
    assert canonical_fact_json(fact) == golden


@pytest.mark.asyncio
async def test_golden_fact_schema_and_caliber_frozen(db_session, golden):
    parsed = json.loads(golden)
    assert parsed["schema"] == WVPL_FACT_SCHEMA
    assert parsed["caliber_version"] == WVPL_CALIBER_VERSION
    assert parsed["as_of"] == AS_OF.isoformat()
    # 可审计三件套随 golden 冻结：口径注释 + 源查询登记 + 事件溯源样本
    assert parsed["definitions"]["loop"]
    assert parsed["provenance"]["source_queries"]
    assert parsed["loops"]["samples"]
