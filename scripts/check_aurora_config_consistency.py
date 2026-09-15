#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = REPO_ROOT / "backend/app/config/settings.py"
ENV_EXAMPLE_PATHS = (
    REPO_ROOT / ".env.example",
    REPO_ROOT / "backend/.env.example",
)
COMPOSE_PATHS = (
    REPO_ROOT / "docker-compose.yml",
    REPO_ROOT / "docker-compose.prod.yml",
)

AI_LAUNCH_KEYS = {
    "ENABLE_CONTEXT_FOCUSING",
    "ENABLE_CONTEXT_SEMANTIC_GATING",
    "ENABLE_CONTEXT_BRIEFING",
    "ENABLE_CONTEXT_FOCUS_METADATA",
    "ENABLE_SESSION_FEEDBACK_ADAPTATION",
    "ENABLE_ADAPTIVE_PRESENTATION",
    "ENABLE_STRUCTURED_NEXT_ACTIONS",
    "ENABLE_BLOCKED_TEMPERATURE",
    "ENABLE_UX_PRESENTATION_METADATA",
    "ENABLE_PERCEPTIBLE_INTELLIGENCE",
    "ENABLE_PROACTIVE_INSIGHTS",
    "ENABLE_PLAN_REASONING_SUMMARY",
    "ENABLE_WEEKLY_LEARNING_REPORT",
    "ENABLE_PROGRESS_COMPARISONS",
}
REQUIRED_MANAGED_KEYS = AI_LAUNCH_KEYS | {
    "ENABLE_AURORA_RUNTIME_V1",
    "SPARKLE_AGGREGATOR_ENABLED",
    "SPARKLE_CONFLICT_RESOLVER_SHADOW_MODE",
    "SPARKLE_CONSOLIDATION_ENABLED",
    "SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED",
    "SPARKLE_LLM_EXTRACTOR_ENABLED",
    "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED",
    "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED",
    "SPARKLE_PROMPT_SOCIAL_CONTEXT_RENDER_ENABLED",
    "SPARKLE_PUSH_DELIVERY_ENABLED",
    "SPARKLE_PUSH_POLICY_ENABLED",
    "SPARKLE_ROUTER_SOCIAL_CONTEXT_READ_ENABLED",
    "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED",
    "SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER",
    "SPARKLE_SKILL_EXTRACT_ENABLED",
    "SPARKLE_SKILL_SELECTION_ENABLED",
    "SPARKLE_SKILL_SHARE_ENABLED",
    "SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED",
    "SPARKLE_WORKING_MEMORY_ENABLED",
}
COMPOSE_REF_PATTERN = re.compile(r"^\$\{(?P<key>[A-Z0-9_]+)(?::-(?P<default>[^}]*))?\}$")


def _is_managed_env_key(key: str) -> bool:
    return key.startswith("AURORA_") or key in REQUIRED_MANAGED_KEYS


def _literal_default(node: ast.AST | None) -> Any:
    if node is None:
        return None
    if isinstance(node, ast.Call) and _call_name(node) == "Field":
        if node.args:
            return _literal_default(node.args[0])
        for keyword in node.keywords:
            if keyword.arg == "default":
                return _literal_default(keyword.value)
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def parse_settings_defaults() -> dict[str, Any]:
    module = ast.parse(SETTINGS_PATH.read_text(encoding="utf-8"))
    settings_class = next(
        node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "Settings"
    )
    defaults: dict[str, Any] = {}
    for statement in settings_class.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            defaults[statement.target.id] = _literal_default(statement.value)
    return defaults


def parse_env_example(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.split("#", 1)[0].strip()
    return values


def _as_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def values_match(expected: str, actual: Any) -> bool:
    expected = str(expected).strip()
    if isinstance(actual, bool):
        return expected.lower() == ("true" if actual else "false")
    if isinstance(actual, int) and not isinstance(actual, bool):
        return _as_decimal(expected) == Decimal(actual)
    if isinstance(actual, float):
        return _as_decimal(expected) == Decimal(str(actual))
    return expected == str(actual)


def _display_default(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _compose_environment_entries(path: Path) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    service_name = "<unknown>"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        service_match = re.match(r"^  (?P<service>[A-Za-z0-9_-]+):\s*$", raw_line)
        if service_match:
            service_name = service_match.group("service")
            continue

        list_match = re.match(r"^\s+-\s+(?P<key>[A-Z0-9_]+)=(?P<value>.*)$", raw_line)
        if list_match:
            entries.append((service_name, list_match.group("key"), list_match.group("value").strip()))
    return entries


def validate() -> list[str]:
    violations: list[str] = []
    settings_defaults = parse_settings_defaults()
    env_maps = {path: parse_env_example(path) for path in ENV_EXAMPLE_PATHS}
    managed_keys = set(REQUIRED_MANAGED_KEYS)
    for values in env_maps.values():
        managed_keys.update(key for key in values if _is_managed_env_key(key))

    for path, values in env_maps.items():
        missing = sorted(managed_keys - set(values))
        for key in missing:
            violations.append(f"{path.relative_to(REPO_ROOT)} missing managed key {key}")

    reference_path = ENV_EXAMPLE_PATHS[0]
    reference_values = env_maps[reference_path]
    for key in sorted(managed_keys):
        if key not in reference_values:
            continue
        expected = reference_values[key]
        for path, values in env_maps.items():
            if key in values and values[key] != expected:
                violations.append(
                    f"{path.relative_to(REPO_ROOT)} {key}={values[key]!r} "
                    f"does not match {reference_path.relative_to(REPO_ROOT)}={expected!r}"
                )

        if key not in settings_defaults:
            violations.append(f"settings.py missing default for managed key {key}")
            continue
        if not values_match(expected, settings_defaults[key]):
            violations.append(
                f"settings.py default for {key}={_display_default(settings_defaults[key])!r} "
                f"does not match env example {expected!r}"
            )

        if expected.lower() in {"off", "shadow"} and key.startswith("AURORA_"):
            violations.append(f"{key} remains {expected!r}; add an explicit whitelist/comment if intentional")

    for path in COMPOSE_PATHS:
        for service_name, key, value in _compose_environment_entries(path):
            if not (key.startswith("AURORA_") or key == "ENABLE_AURORA_RUNTIME_V1"):
                continue
            if key not in settings_defaults:
                violations.append(f"{path.relative_to(REPO_ROOT)}:{service_name} uses unknown Aurora key {key}")
                continue

            match = COMPOSE_REF_PATTERN.match(value)
            if match:
                referenced_key = match.group("key")
                if referenced_key != key:
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}:{service_name} {key} references {referenced_key}"
                    )
                default = match.group("default")
                if default is not None and not values_match(default, settings_defaults[key]):
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}:{service_name} {key} fallback {default!r} "
                        f"does not match settings default {_display_default(settings_defaults[key])!r}"
                    )
            elif not values_match(value, settings_defaults[key]):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{service_name} {key}={value!r} "
                    f"does not match settings default {_display_default(settings_defaults[key])!r}"
                )

    return violations


def main() -> int:
    violations = validate()
    if violations:
        print("[Aurora Config] FAIL")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("[Aurora Config] PASS - settings, env examples, and compose Aurora defaults are aligned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
