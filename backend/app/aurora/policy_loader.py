"""Aurora policy loading utilities."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.aurora.config import DEFAULT_AURORA_CONFIG
from app.aurora.schemas import AuroraPolicyVersion


class AuroraPolicyLoadError(RuntimeError):
    """Raised when a policy fixture cannot be loaded or validated."""


def _normalize_policy_token(policy_version: str | None) -> str:
    token = (policy_version or DEFAULT_AURORA_CONFIG.default_policy_version).strip()
    if not token:
        token = DEFAULT_AURORA_CONFIG.default_policy_version
    if token.startswith("aurora_policy@"):
        token = token.split("@", 1)[1]
    return token


def _policy_path(policy_version: str | None = None, policy_path: str | Path | None = None) -> Path:
    if policy_path is not None:
        candidate = Path(policy_path).expanduser().resolve()
        if candidate.is_dir():
            return candidate / f"{_normalize_policy_token(policy_version)}.yaml"
        return candidate
    return DEFAULT_AURORA_CONFIG.policy_directory / f"{_normalize_policy_token(policy_version)}.yaml"


@lru_cache(maxsize=8)
def load_policy_version(
    policy_version: str | None = None,
    policy_path: str | Path | None = None,
) -> AuroraPolicyVersion:
    """Load and validate a frozen Aurora policy fixture."""

    path = _policy_path(policy_version=policy_version, policy_path=policy_path)
    if not path.exists():
        raise AuroraPolicyLoadError(f"Aurora policy fixture not found: {path}")

    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parsing guard
        raise AuroraPolicyLoadError(f"Failed to parse Aurora policy fixture at {path}") from exc

    if not isinstance(raw, dict):
        raise AuroraPolicyLoadError(f"Aurora policy fixture at {path} did not contain a mapping")

    try:
        return AuroraPolicyVersion.model_validate(raw)
    except Exception as exc:  # pragma: no cover - validation guard
        raise AuroraPolicyLoadError(f"Aurora policy fixture at {path} is invalid") from exc

