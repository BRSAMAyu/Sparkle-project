#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_CONTEXT_SERVICE = REPO_ROOT / "backend/app/services/profile_context_service.py"
CONTEXT_BUILDER = REPO_ROOT / "backend/app/orchestration/context_builder.py"
ROUTING_ENGINE = REPO_ROOT / "backend/app/orchestration/routing_engine.py"
PROMPTS = REPO_ROOT / "backend/app/orchestration/prompts.py"
IGNORE_PATTERN = re.compile(r"#\s*rule-as:\s*ignore\s+(?P<reason>.+)")
SCAN_CONTEXT_BUILDER = True
EXPECTATIONS: dict[str, dict[Path, tuple[str, ...]]] = {
    "srl_phase": {
        ROUTING_ENGINE: (
            "srl_phase_hint",
            'stage33_modes.get("srl")',
            'stage33_shadow_delta["srl"]',
        ),
        PROMPTS: (
            "学习自调节阶段",
            "AURORA_STAGE33_SRL_MODE",
        ),
    },
    "metacognition_profile": {
        ROUTING_ENGINE: (
            "_build_metacognition_hint",
            'required_fields=("metacognition_profile",)',
            "metacognition_hint",
            'stage35_metacognition_shadow_delta',
        ),
    },
    "active_goals": {
        CONTEXT_BUILDER: (
            "_attach_stage34_memory_context",
            'payload["active_goals"]',
        ),
        PROMPTS: (
            "【当前目标】",
            'normalized.get("active_goals")',
        ),
    },
    "episodic_memories": {
        CONTEXT_BUILDER: (
            "_attach_stage34_memory_context",
            'payload["episodic_memories"]',
        ),
        PROMPTS: (
            "【近期相关记忆】",
            'normalized.get("episodic_memories")',
        ),
    },
    "aurora_stage39_modes": {
        CONTEXT_BUILDER: (
            'payload["aurora_stage39_modes"]',
        ),
        ROUTING_ENGINE: (
            'user_context_payload["aurora_stage39_modes"]',
            '"aurora_stage39_modes": stage39_modes',
        ),
    },
    "scaffolding_fsm_snapshot": {
        CONTEXT_BUILDER: (
            'payload["scaffolding_fsm_snapshot"]',
        ),
        PROMPTS: (
            'user_context.get("scaffolding_fsm_snapshot")',
        ),
    },
    "galaxy_snapshot": {
        CONTEXT_BUILDER: (
            'payload["galaxy_snapshot"]',
        ),
        PROMPTS: (
            '_format_galaxy_snapshot_section',
            'user_context.get("galaxy_snapshot")',
        ),
    },
}


@dataclass(frozen=True)
class AttachmentSignal:
    method_name: str
    field_name: str
    line_no: int
    ignore_reason: str | None = None


def _ignore_reason_for_method(lines: list[str], line_no: int) -> str | None:
    start = max(0, line_no - 3)
    for idx in range(start, line_no):
        match = IGNORE_PATTERN.search(lines[idx])
        if match:
            return match.group("reason").strip()
    return None


def _extract_attached_fields(
    body: str,
) -> list[str]:
    fields: list[str] = []
    patterns = (
        re.compile(r"context\.user_insight_state\.([A-Za-z_][A-Za-z0-9_]*)\s*="),
        re.compile(r"context\.([A-Za-z_][A-Za-z0-9_]*)\s*="),
    )
    for pattern in patterns:
        for match in pattern.finditer(body):
            field_name = match.group(1)
            if field_name not in fields:
                fields.append(field_name)
    return fields


def collect_profile_context_attachments(
    profile_context_service: Path = PROFILE_CONTEXT_SERVICE,
) -> list[AttachmentSignal]:
    text = profile_context_service.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    attachments: list[AttachmentSignal] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("_attach_"):
            continue
        body = ast.get_source_segment(text, node) or ""
        ignore_reason = _ignore_reason_for_method(lines, node.lineno - 1)
        for field_name in _extract_attached_fields(body):
            attachments.append(
                AttachmentSignal(
                    method_name=node.name,
                    field_name=field_name,
                    line_no=node.lineno,
                    ignore_reason=ignore_reason,
                )
            )
    return attachments


def collect_context_builder_attachments(
    context_builder: Path = CONTEXT_BUILDER,
) -> list[AttachmentSignal]:
    if not context_builder.exists():
        return []
    text = context_builder.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    attachments: list[AttachmentSignal] = []
    field_pattern = re.compile(r'payload\["([A-Za-z_][A-Za-z0-9_]*)"\]\s*=')

    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        if not node.name.startswith("_attach_") and not re.match(r"_build_.*_section", node.name):
            continue
        body = ast.get_source_segment(text, node) or ""
        ignore_reason = _ignore_reason_for_method(lines, node.lineno - 1)
        seen_fields: list[str] = []
        for match in field_pattern.finditer(body):
            field_name = match.group(1)
            if field_name in seen_fields:
                continue
            seen_fields.append(field_name)
            attachments.append(
                AttachmentSignal(
                    method_name=node.name,
                    field_name=field_name,
                    line_no=node.lineno,
                    ignore_reason=ignore_reason,
                )
            )
    return attachments


def scan_rule_as(
    *,
    profile_context_service: Path = PROFILE_CONTEXT_SERVICE,
    context_builder: Path = CONTEXT_BUILDER,
    consumer_targets: tuple[Path, ...] = (ROUTING_ENGINE, PROMPTS, CONTEXT_BUILDER),
) -> list[str]:
    attachments = [
        *collect_profile_context_attachments(profile_context_service),
        *(collect_context_builder_attachments(context_builder) if SCAN_CONTEXT_BUILDER else []),
    ]
    consumer_text: dict[Path, str] = {}
    for path in consumer_targets:
        consumer_text[path] = path.read_text(encoding="utf-8")
        if path.name == PROFILE_CONTEXT_SERVICE.name:
            consumer_text[PROFILE_CONTEXT_SERVICE] = consumer_text[path]
        if path.name == CONTEXT_BUILDER.name:
            consumer_text[CONTEXT_BUILDER] = consumer_text[path]
        if path.name == ROUTING_ENGINE.name:
            consumer_text[ROUTING_ENGINE] = consumer_text[path]
        if path.name == PROMPTS.name:
            consumer_text[PROMPTS] = consumer_text[path]
    violations: list[str] = []

    for attachment in attachments:
        if attachment.ignore_reason:
            continue
        expected_tokens = EXPECTATIONS.get(attachment.field_name)
        if not expected_tokens:
            violations.append(
                f"AS001 {profile_context_service}:{attachment.line_no} "
                f"attached field `{attachment.field_name}` is missing Rule AS expectation or ignore"
            )
            continue
        for target_path, tokens in expected_tokens.items():
            text = consumer_text.get(target_path)
            if text is None:
                continue
            for token in tokens:
                if token not in text:
                    violations.append(
                        f"AS002 {target_path} missing token `{token}` for attached field `{attachment.field_name}`"
                    )
    return violations


def main() -> int:
    violations = scan_rule_as()
    if violations:
        print("[Rule AS] FAIL")
        for violation in violations:
            print(violation)
        return 1
    attachments = collect_profile_context_attachments()
    if SCAN_CONTEXT_BUILDER:
        attachments.extend(collect_context_builder_attachments())
    print(f"[Rule AS] PASS - attachments={len(attachments)} tracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
