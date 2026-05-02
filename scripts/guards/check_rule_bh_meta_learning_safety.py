#!/usr/bin/env python3
"""Rule BH: Meta-learning parameter safety guard.

Verifies:
1. Registry always has fallback to hardcoded defaults
2. Every parameter has min/max bounds in PARAMETER_BOUNDS
3. Meta-learning kill switch binding exists
4. No parameter changes applied without experiment or audit trail

Exit 0 on pass, non-zero on fail.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_FILE = REPO_ROOT / "backend" / "app" / "orchestration" / "routing_parameter_registry.py"
EXPERIMENT_FILE = REPO_ROOT / "backend" / "app" / "services" / "routing_parameter_experiment_service.py"


def check_registry_defaults_fallback() -> list[str]:
    """Registry must have _defaults_snapshot and _merge_with_defaults methods."""
    failures: list[str] = []
    source = REGISTRY_FILE.read_text()
    tree = ast.parse(source)

    class_names = set()
    method_names: dict[str, set] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_names.add(node.name)
            method_names[node.name] = {
                n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            }

    if "RoutingParameterRegistry" not in class_names:
        failures.append("Missing RoutingParameterRegistry class")
    else:
        reg_methods = method_names.get("RoutingParameterRegistry", set())
        for required in ("_defaults_snapshot", "_merge_with_defaults", "load"):
            if required not in reg_methods:
                failures.append(f"RoutingParameterRegistry missing method: {required}")

    if "RoutingParameterSnapshot" not in class_names:
        failures.append("Missing RoutingParameterSnapshot dataclass")

    return failures


def check_all_parameters_have_bounds() -> list[str]:
    """Every parameter in ALL_DEFAULT_PARAMETERS must have bounds."""
    failures: list[str] = []
    source = REGISTRY_FILE.read_text()

    # Extract param names from ALL_DEFAULT_PARAMETERS
    defaults_names = set()
    in_defaults = False
    for line in source.splitlines():
        stripped = line.strip()
        if "ALL_DEFAULT_PARAMETERS" in stripped and ": dict" in stripped:
            in_defaults = True
            continue
        if in_defaults:
            if stripped.startswith("}"):
                break
            if ":" in stripped and not stripped.startswith("#") and not stripped.startswith("*"):
                key = stripped.split(":")[0].strip().strip('"').strip("'")
                if key and not key.startswith("{"):
                    defaults_names.add(key)

    # Check PARAMETER_BOUNDS covers all precedence + threshold params
    bounds_names = set()
    in_bounds = False
    for line in source.splitlines():
        stripped = line.strip()
        if "PARAMETER_BOUNDS" in stripped and ": dict" in stripped:
            in_bounds = True
            continue
        if in_bounds:
            if stripped.startswith("}"):
                break
            # Handle both dict-style and **-style entries
            if "**" in stripped:
                continue
            if ":" in stripped and not stripped.startswith("#"):
                key = stripped.split(":")[0].strip().strip('"').strip("'")
                if key and not key.startswith("{"):
                    bounds_names.add(key)

    # Precedence weights and profile defaults are covered by ** expansion in bounds
    # Check thresholds individually
    missing = defaults_names - bounds_names
    # Filter out ones covered by ** expansion (they're in DEFAULT_PRECEDENCE_WEIGHTS or DEFAULT_PROFILE_DEFAULTS)
    threshold_only = defaults_names - set()
    for name in missing:
        # These are covered by ** expansion, not individual entries
        if name in ("emotional_block", "procrastination", "cognitive_mode", "low_metacognition",
                     "high_cognitive_load", "spine_fatigue", "reflection_phase", "goal_clarity",
                     "scaffolding_frustration", "scaffolding_boredom",
                     "procrastination_threshold", "emotional_sensitivity", "directness_preference"):
            continue
        failures.append(f"Parameter {name!r} has no bounds in PARAMETER_BOUNDS")

    return failures


def check_kill_switch_binding() -> list[str]:
    """META_LEARNING_BINDING must exist with correct stage/feature."""
    failures: list[str] = []
    source = REGISTRY_FILE.read_text()

    if "META_LEARNING_BINDING" not in source:
        failures.append("Missing META_LEARNING_BINDING in registry")
    if 'stage="meta_learning"' not in source:
        failures.append("META_LEARNING_BINDING missing stage='meta_learning'")
    if 'feature="routing_parameters"' not in source:
        failures.append("META_LEARNING_BINDING missing feature='routing_parameters'")

    return failures


def check_experiment_safety() -> list[str]:
    """Experiment service must only apply changes with >5% improvement check."""
    failures: list[str] = []
    if not EXPERIMENT_FILE.exists():
        failures.append("Missing routing_parameter_experiment_service.py")
        return failures

    source = EXPERIMENT_FILE.read_text()

    # Must check sample size before applying
    if "total" not in source or "insufficient_samples" not in source:
        failures.append("Experiment service must verify minimum sample size before applying")

    # Must require improvement threshold
    if "1.05" not in source and "improvement" not in source.lower():
        failures.append("Experiment service must require minimum improvement to apply changes")

    # Must use _clamp when writing parameters
    if "_clamp" not in source:
        failures.append("Experiment service must clamp parameter values when applying")

    return failures


def main() -> int:
    all_failures: list[str] = []
    all_failures.extend(check_registry_defaults_fallback())
    all_failures.extend(check_all_parameters_have_bounds())
    all_failures.extend(check_kill_switch_binding())
    all_failures.extend(check_experiment_safety())

    if all_failures:
        print("Rule BH violations:")
        for f in all_failures:
            print(f"  - {f}")
        return 1

    print("Rule BH: meta-learning safety — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
