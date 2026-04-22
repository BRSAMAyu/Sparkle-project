#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_CONTEXT_SERVICE = REPO_ROOT / "backend/app/services/profile_context_service.py"
ROUTING_ENGINE = REPO_ROOT / "backend/app/orchestration/routing_engine.py"
PROMPTS = REPO_ROOT / "backend/app/orchestration/prompts.py"
IGNORE_PATTERN = re.compile(r"#\s*rule-as:\s*ignore\s+(?P<reason>.+)")
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


def scan_rule_as(
    *,
    profile_context_service: Path = PROFILE_CONTEXT_SERVICE,
    consumer_targets: tuple[Path, ...] = (ROUTING_ENGINE, PROMPTS),
) -> list[str]:
    attachments = collect_profile_context_attachments(profile_context_service)
    consumer_text = {
        path: path.read_text(encoding="utf-8")
        for path in consumer_targets
    }
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
    print(f"[Rule AS] PASS - attachments={len(attachments)} tracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
