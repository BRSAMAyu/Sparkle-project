from __future__ import annotations

from app.state_aggregator.schema import UserStateV1

__all__ = ["StateAggregatorService", "UserStateV1"]


def __getattr__(name: str):
    if name == "StateAggregatorService":
        from app.state_aggregator.service import StateAggregatorService

        return StateAggregatorService
    raise AttributeError(name)
