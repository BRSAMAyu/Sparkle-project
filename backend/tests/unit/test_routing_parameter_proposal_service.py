"""RoutingParameterProposalService.propose_from_effectiveness 到达路径守卫。

V3-FIX-264 点位1（wt543）：`_compute_proposed_value` 是纯同步 @staticmethod
（返回 float|None，无 I/O 无并发），修前在 :197 被 `await`——证据到达
（param_effectiveness 样本 ≥ MIN_SAMPLES_FOR_PROPOSAL 且
best_rate ≥ baseline × MIN_IMPROVEMENT_RATIO）即抛
`TypeError: object float can't be used in 'await' expression`，
一路穿透到 celery 任务（唯一生产调用方 app/core/celery_tasks.py:3785）。

修法裁决：(a) 去 await 直调——函数纯同步、调用点不在任何并发原语
（gather/create_task）语境，改 async def 无收益且零个其他调用点需跟随。
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.learning.persistent_bayesian_learner import build_persistent_bayesian_key
from app.orchestration.routing_parameter_registry import ALL_DEFAULT_PARAMETERS
from app.services.routing_parameter_effectiveness_service import EFFECTIVENESS_REDIS_KEY
from app.services.routing_parameter_proposal_service import RoutingParameterProposalService


class FakeRedis:
    """最小异步 Redis 替身：dict 存储，仅覆盖本服务用到的 get/set。"""

    def __init__(self, store: dict[str, str]):
        self._store = store

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._store[key] = value
        return True


def _reaching_store() -> dict[str, str]:
    """构造能穿过全部阈值闸、到达 _compute_proposed_value 调用点的证据面。

    effectiveness 组：total≥50 提供 baseline 0.5；
    learner stats：obs = alpha+beta-2 = 60 ≥ 50，rate = 60/62 ≈ 0.968 ≥ 0.5×1.05。
    """
    return {
        EFFECTIVENESS_REDIS_KEY: json.dumps(
            [
                {
                    "dominant_signal": "frustration",
                    "routing_mode": "standard",
                    "total": 100,
                    "success_rate": 0.5,
                }
            ]
        ),
        build_persistent_bayesian_key("system:meta_learning"): json.dumps(
            {
                "param_effectiveness:v2->emotional_block": {
                    "alpha": 60.0,
                    "beta": 2.0,
                    "mean": 0.9677,
                },
            }
        ),
    }


def _make_service(store: dict[str, str]) -> RoutingParameterProposalService:
    return RoutingParameterProposalService(db=MagicMock(), redis_client=FakeRedis(store))


async def test_propose_from_effectiveness_reaches_compute_without_typeerror(monkeypatch):
    """证据到达时不得因 await 同步函数抛 TypeError，且首个参数产出提案。

    修前实录（台账 V3-FIX-263「跳过留裁决」段）：pytest 实跑
    TypeError: object float can't be used in 'await' expression。
    """
    store = _reaching_store()
    svc = _make_service(store)
    # 隔离漂移防火墙外部性：本守卫只针对 await 缺陷，防火墙行为另有归属
    monkeypatch.setattr(svc, "_check_drift", lambda proposal: {"disposition": "allowed"})

    proposals = await svc.propose_from_effectiveness()

    assert len(proposals) >= 1
    first = proposals[0]
    assert first.parameter_name in ALL_DEFAULT_PARAMETERS
    assert first.proposed_value is not None
    assert first.current_value == float(ALL_DEFAULT_PARAMETERS[first.parameter_name])
    # 提案已落 Redis（键含参数名与创建时间戳）
    stored = [k for k in store if k.startswith("aurora:param_proposals:")]
    assert len(stored) >= 1
    assert any(first.parameter_name in k for k in stored)
