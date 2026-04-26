#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = REPO_ROOT / "backend/app/config/settings.py"
METRICS_PATH = REPO_ROOT / "backend/app/core/metrics.py"
SERVICE_PATH = REPO_ROOT / "backend/app/services/aurora_doc_context_kill_switch_service.py"
CONTEXT_PACK_PATH = REPO_ROOT / "backend/app/core/context_pack.py"
WORKFLOW_PATH = REPO_ROOT / "backend/app/agents/standard_workflow.py"

REQUIRED_SETTINGS = {
    "ENABLE_DOCUMENT_CONTEXT_INJECTION": "True",
    "DOCUMENT_CONTEXT_RATIO": "0.25",
    "DOCUMENT_CONTEXT_MAX_CHUNKS": "5",
    "DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD": "0.72",
    "DOCUMENT_CONTEXT_RECENCY_BOOST_DAYS": "30",
    "AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE": '"shadow"',
}

REQUIRED_METRICS = (
    "sparkle_document_context_chunks_injected_total",
    "sparkle_document_context_tokens_used",
    "sparkle_document_context_cache_hit_ratio",
    "sparkle_kill_switch_mode",
)


def main() -> int:
    violations: list[str] = []
    settings_text = SETTINGS_PATH.read_text(encoding="utf-8")
    metrics_text = METRICS_PATH.read_text(encoding="utf-8")
    service_text = SERVICE_PATH.read_text(encoding="utf-8") if SERVICE_PATH.exists() else ""
    context_pack_text = CONTEXT_PACK_PATH.read_text(encoding="utf-8")
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    for name, expected in REQUIRED_SETTINGS.items():
        pattern = rf"^\s*{re.escape(name)}:\s*(?:bool|float|int|str)\s*=\s*{re.escape(expected)}(?:\s|#|$)"
        if not re.search(pattern, settings_text, re.MULTILINE):
            violations.append(f"missing or unexpected setting default: {name}={expected}")

    for metric in REQUIRED_METRICS:
        if metric not in metrics_text:
            violations.append(f"missing metric: {metric}")

    service_required = (
        "KillSwitchBinding",
        'stage="doc_context"',
        'feature="document_context_injection"',
        'settings_attr="AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE"',
        'fallback_mode="shadow"',
        "ENABLE_DOCUMENT_CONTEXT_INJECTION",
        "record_mode_gauge",
    )
    for needle in service_required:
        if needle not in service_text:
            violations.append(f"doc context kill switch missing {needle}")

    if "AuroraDocContextKillSwitchService" not in context_pack_text:
        violations.append("context_pack does not read document-context kill switch controls")
    if "document_context_controls" not in context_pack_text:
        violations.append("context_pack does not expose document-context controls metadata")

    workflow_required = (
        "AuroraDocContextKillSwitchService",
        "document_context_mode",
        'document_context_mode in {"shadow", "live"}',
        "DOCUMENT_CONTEXT_CHUNKS_INJECTED_TOTAL",
        "DOCUMENT_CONTEXT_TOKENS_USED",
        "DOCUMENT_CONTEXT_MAX_CHUNKS",
        "DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD",
    )
    for needle in workflow_required:
        if needle not in workflow_text:
            violations.append(f"standard workflow missing governance hook: {needle}")
    if 'document_context_mode == "live"' not in workflow_text and 'document_context_mode != "live"' not in workflow_text:
        violations.append("standard workflow must distinguish shadow from live injection")

    if violations:
        print("[Rule BF] FAIL")
        for item in violations:
            print(item)
        return 1

    print("[Rule BF] PASS - document context injection is Aurora-governed and observable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
