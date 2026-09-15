#!/usr/bin/env python3
"""Export canonical protobuf contract snapshot from generated Python descriptors."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from google.protobuf.descriptor import Descriptor, EnumDescriptor, FileDescriptor

PROTO_MODULES = [
    "app.gen.agent_service_pb2",
    "app.gen.error_book_pb2",
    "app.gen.websocket_pb2",
]


def _field_summary(field) -> dict[str, object]:
    type_name = ""
    if field.message_type is not None:
        type_name = field.message_type.full_name
    elif field.enum_type is not None:
        type_name = field.enum_type.full_name
    label = getattr(field, "label", None)
    if label is None:
        if getattr(field, "is_repeated", False):
            label = field.LABEL_REPEATED
        elif getattr(field, "is_required", False):
            label = field.LABEL_REQUIRED
        else:
            label = field.LABEL_OPTIONAL
    return {
        "name": field.name,
        "number": field.number,
        "label": label,
        "type": field.type,
        "type_name": type_name,
        "json_name": field.json_name,
    }


def _enum_summary(enum_desc: EnumDescriptor) -> dict[str, object]:
    return {
        "name": enum_desc.full_name,
        "values": [
            {"name": value.name, "number": value.number}
            for value in enum_desc.values
        ],
    }


def _message_summary(message_desc: Descriptor) -> dict[str, object]:
    nested_messages = {
        nested.full_name: _message_summary(nested)
        for nested in sorted(message_desc.nested_types, key=lambda item: item.full_name)
    }
    nested_enums = {
        enum.full_name: _enum_summary(enum)
        for enum in sorted(message_desc.enum_types, key=lambda item: item.full_name)
    }
    return {
        "name": message_desc.full_name,
        "fields": [_field_summary(field) for field in message_desc.fields],
        "nested_messages": nested_messages,
        "nested_enums": nested_enums,
    }


def _service_summary(file_desc: FileDescriptor) -> dict[str, object]:
    services = {}
    for service in sorted(file_desc.services_by_name.values(), key=lambda item: item.full_name):
        services[service.full_name] = {
            "methods": [
                {
                    "name": method.name,
                    "input_type": method.input_type.full_name,
                    "output_type": method.output_type.full_name,
                    "client_streaming": method.client_streaming,
                    "server_streaming": method.server_streaming,
                }
                for method in service.methods
            ]
        }
    return services


def _file_summary(file_desc: FileDescriptor) -> dict[str, object]:
    messages = {
        desc.full_name: _message_summary(desc)
        for desc in sorted(file_desc.message_types_by_name.values(), key=lambda item: item.full_name)
    }
    enums = {
        desc.full_name: _enum_summary(desc)
        for desc in sorted(file_desc.enum_types_by_name.values(), key=lambda item: item.full_name)
    }
    return {
        "package": file_desc.package,
        "dependencies": sorted(dep.name for dep in file_desc.dependencies),
        "messages": messages,
        "enums": enums,
        "services": _service_summary(file_desc),
    }


def build_snapshot() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    gen_dir = backend_dir / "app" / "gen"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    if str(gen_dir) not in sys.path:
        sys.path.insert(0, str(gen_dir))

    snapshot: dict[str, object] = {"files": {}}
    for module_name in PROTO_MODULES:
        module = importlib.import_module(module_name)
        file_desc = module.DESCRIPTOR
        snapshot["files"][file_desc.name] = _file_summary(file_desc)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Export protobuf contract snapshot")
    parser.add_argument("--output", default="docs/contracts/proto_snapshot.json")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_snapshot(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✅ Proto snapshot exported: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
