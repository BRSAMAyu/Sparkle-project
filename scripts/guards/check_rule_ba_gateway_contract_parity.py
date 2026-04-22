#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GO_HANDLER_PATH = REPO_ROOT / "backend/gateway/internal/handler/chat_history.go"
DART_MODEL_PATH = REPO_ROOT / "mobile/lib/features/chat/data/models/chat_message_model.dart"


def _extract_go_chat_history_fields(path: Path = GO_HANDLER_PATH) -> set[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start_index = next(
        (index for index, line in enumerate(lines) if "type ChatHistoryMessageDTO struct {" in line),
        None,
    )
    if start_index is None:
        raise RuntimeError(f"Could not locate ChatHistoryMessageDTO in {path}")
    fields: set[str] = set()
    for line in lines[start_index + 1 :]:
        if line.strip() == "}":
            break
        match = re.search(r'json:"([^",]+)', line)
        if match:
            fields.add(match.group(1))
    return fields


def _extract_dart_chat_history_fields(path: Path = DART_MODEL_PATH) -> set[str]:
    text = path.read_text(encoding="utf-8")
    class_start = text.find("class ChatMessageModel {")
    if class_start == -1:
        raise RuntimeError(f"Could not locate ChatMessageModel in {path}")
    to_json_index = text.find("Map<String, dynamic> toJson()", class_start)
    if to_json_index == -1:
        raise RuntimeError(f"Could not locate ChatMessageModel fields in {path}")
    class_block = text[class_start:to_json_index]
    field_start = class_block.find("final String id;")
    if field_start == -1:
        raise RuntimeError(f"Could not locate ChatMessageModel fields in {path}")

    factory_block = class_block[:field_start]
    fields: set[str] = set(re.findall(r"json\['([^']+)'\]", factory_block))
    field_block = class_block[field_start:]

    pending_annotation = ""
    collecting_annotation = False
    for raw_line in field_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("@JsonKey(") or collecting_annotation:
            pending_annotation = f"{pending_annotation} {line}".strip()
            collecting_annotation = ")" not in line
            continue
        field_match = re.search(r"final\s+[^;=]+\s+([A-Za-z0-9_]+);", line)
        if not field_match:
            continue
        field_name = field_match.group(1)
        if "includeFromJson: false" in pending_annotation:
            pending_annotation = ""
            continue
        name_match = re.search(r"name:\s*'([^']+)'", pending_annotation)
        fields.add(name_match.group(1) if name_match else field_name)
        pending_annotation = ""

    return fields


def scan_rule_ba(*, repo_root: Path | None = None) -> tuple[set[str], set[str], list[str]]:
    if repo_root is None:
        go_fields = _extract_go_chat_history_fields()
        dart_fields = _extract_dart_chat_history_fields()
    else:
        go_fields = _extract_go_chat_history_fields(repo_root / "backend/gateway/internal/handler/chat_history.go")
        dart_fields = _extract_dart_chat_history_fields(
            repo_root / "mobile/lib/features/chat/data/models/chat_message_model.dart"
        )

    missing_fields = sorted(dart_fields - go_fields)
    violations = [
        f"BA001 missing Go chat history field `{field}` in backend/gateway/internal/handler/chat_history.go"
        for field in missing_fields
    ]
    return go_fields, dart_fields, violations


def main() -> int:
    go_fields, dart_fields, violations = scan_rule_ba()
    if violations:
        print("[Rule BA] FAIL")
        print(f"go_fields={sorted(go_fields)}")
        print(f"dart_fields={sorted(dart_fields)}")
        for violation in violations:
            print(violation)
        return 1
    print(
        f"[Rule BA] PASS - go_fields={len(go_fields)} dart_fields={len(dart_fields)} missing=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
