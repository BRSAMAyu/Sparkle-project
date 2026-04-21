"""Reward computation: multi-dimensional reward signal for SGW RL.

Computes r_t from before/after metric deltas with weighted dimensions,
one-vote veto, diversity bonus, and tanh normalization.

Also exposes `load_reward_config()` which reads `reward_weights.yaml` from the
package directory (or an arbitrary path) so operators can hot-edit the
reward mix without touching Python. The loader deliberately falls back to
default weights when PyYAML is unavailable so the module always imports.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .spec import (
    RewardWeights, DEFAULT_REWARD_WEIGHTS, REWARD_SCALE,
    IterationOutcome,
)


_DEFAULT_CONFIG_PATH = Path(__file__).parent / "reward_weights.yaml"


@dataclass
class RewardComponents:
    """Individual dimension rewards for transparency."""
    soft_violation: float = 0.0    # Δ(-soft_violation_rate)
    authenticity: float = 0.0      # Δ(authenticity_mean)
    hard_violation: float = 0.0    # -hard_violations_delta * 10
    session: float = 0.0           # Δ(session_completion_rate)
    diversity: float = 0.0         # diversity bonus

    @property
    def total_raw(self) -> float:
        return (
            self.soft_violation
            + self.authenticity
            + self.hard_violation
            + self.session
            + self.diversity
        )


def compute_reward(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    weights: RewardWeights = DEFAULT_REWARD_WEIGHTS,
    diversity_score: float = 0.0,
    auth_z_statistic: float | None = None,
    alpha: float = 1.96,
) -> tuple[float, float, RewardComponents, bool, str | None]:
    """Compute reward signal from before/after metrics.

    Returns:
        (raw_reward, normalized_reward, components, veto_applied, veto_reason)
    """
    # Delta calculations
    delta_soft = -(after.get("soft_violation_rate", 0) - before.get("soft_violation_rate", 0))
    delta_auth = after.get("authenticity_mean", 0) - before.get("authenticity_mean", 0)
    delta_hard = after.get("hard_violations", 0) - before.get("hard_violations", 0)
    delta_session = after.get("session_completion_rate", 0) - before.get("session_completion_rate", 0)

    # Weighted components
    components = RewardComponents(
        soft_violation=weights.w_soft * delta_soft,
        authenticity=weights.w_auth * delta_auth,
        hard_violation=weights.w_hard * (-delta_hard * 10),
        session=weights.w_session * delta_session,
        diversity=weights.w_diversity * diversity_score,
    )

    # One-vote veto checks
    if delta_hard > 0:
        return (-1.0, math.tanh(-1.0 / REWARD_SCALE), components, True, "hard_violation_increase")

    if auth_z_statistic is not None and auth_z_statistic > alpha:
        return (-0.8, math.tanh(-0.8 / REWARD_SCALE), components, True, "authenticity_sig_regression")

    raw = components.total_raw
    normalized = math.tanh(raw / REWARD_SCALE)
    return (raw, normalized, components, False, None)


@dataclass
class RewardConfig:
    """Parsed view of reward_weights.yaml — only the fields used by the RL layer."""
    weights: RewardWeights
    reward_scale: float
    auth_significance_threshold: float
    min_sample_size: int
    holdout_ratio: float
    holdout_gap_threshold: float
    temperature_start: float
    temperature_end: float
    temperature_decay: float
    max_iterations: int
    convergence_window: int
    explore_every_n: int


def _minimal_yaml_parse(text: str) -> dict[str, Any]:
    """Very small YAML subset parser.

    Handles the flat/nested key: value structure used by reward_weights.yaml
    (two-space indented maps, scalar values, no lists). Used only when PyYAML
    is not installed so the loader never blocks imports.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.strip().partition(":")
        key = key.strip()
        value = value.strip()

        # Walk back up the stack to the correct parent.
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else root

        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
            continue

        lowered = value.lower()
        if lowered in ("true", "false"):
            parent[key] = lowered == "true"
        elif lowered in ("null", "~", ""):
            parent[key] = None
        else:
            try:
                parent[key] = int(value)
            except ValueError:
                try:
                    parent[key] = float(value)
                except ValueError:
                    parent[key] = value.strip("'\"")
    return root


def load_reward_config(path: Path | str | None = None) -> RewardConfig:
    """Load reward configuration from YAML, falling back to defaults on any error."""
    target = Path(path) if path else _DEFAULT_CONFIG_PATH
    data: dict[str, Any] = {}
    if target.exists():
        text = target.read_text(encoding="utf-8")
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text) or {}
        except ImportError:
            data = _minimal_yaml_parse(text)
        except Exception:  # noqa: BLE001
            data = {}

    rw = data.get("reward_weights", {}) or {}
    weights = RewardWeights(
        w_soft=float(rw.get("soft_violation", DEFAULT_REWARD_WEIGHTS.w_soft)),
        w_auth=float(rw.get("authenticity", DEFAULT_REWARD_WEIGHTS.w_auth)),
        w_hard=float(rw.get("hard_violation", DEFAULT_REWARD_WEIGHTS.w_hard)),
        w_session=float(rw.get("session_completion", DEFAULT_REWARD_WEIGHTS.w_session)),
        w_diversity=float(rw.get("diversity", DEFAULT_REWARD_WEIGHTS.w_diversity)),
    )
    veto = data.get("veto", {}) or {}
    sig = data.get("significance", {}) or {}
    anti = data.get("anti_overfitting", {}) or {}
    episode = data.get("episode", {}) or {}

    return RewardConfig(
        weights=weights,
        reward_scale=float(data.get("reward_scale", REWARD_SCALE)),
        auth_significance_threshold=float(veto.get("auth_significance_threshold", 1.96)),
        min_sample_size=int(sig.get("min_sample_size", 200)),
        holdout_ratio=float(anti.get("holdout_ratio", 0.2)),
        holdout_gap_threshold=float(anti.get("holdout_gap_threshold", 0.1)),
        temperature_start=float(anti.get("temperature_start", 1.0)),
        temperature_end=float(anti.get("temperature_end", 0.1)),
        temperature_decay=float(anti.get("temperature_decay", 0.95)),
        max_iterations=int(episode.get("max_iterations", 20)),
        convergence_window=int(episode.get("convergence_window", 5)),
        explore_every_n=int(episode.get("explore_every_n", 10)),
    )
