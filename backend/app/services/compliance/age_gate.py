from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.user import User


@dataclass
class AgeGateDecision:
    is_minor: Optional[bool]
    should_collect_sensitive: bool
    source: Optional[str]


class AgeGateService:
    """
    端侧年龄校验与最小化采集策略
    """

    @staticmethod
    def evaluate(user: User, payload: Dict[str, Any]) -> AgeGateDecision:
        declared_age = payload.get("declared_age")
        parent_mode = payload.get("parental_control_enabled")
        registration_verified = payload.get("registration_age_verified")

        if registration_verified is True and declared_age is not None:
            is_minor = declared_age < 18
            return AgeGateDecision(
                is_minor=is_minor,
                should_collect_sensitive=not is_minor,
                source="registration"
            )

        if parent_mode is True:
            return AgeGateDecision(
                is_minor=True,
                should_collect_sensitive=False,
                source="device_mode"
            )

        return AgeGateDecision(
            is_minor=user.is_minor if user.is_minor is not None else None,
            should_collect_sensitive=False,
            source=None
        )

    @staticmethod
    def apply_to_user(user: User, decision: AgeGateDecision) -> None:
        if decision.is_minor is None:
            return
        user.is_minor = decision.is_minor
        user.age_verified = True
        user.age_verification_source = decision.source
        user.age_verified_at = datetime.utcnow()
