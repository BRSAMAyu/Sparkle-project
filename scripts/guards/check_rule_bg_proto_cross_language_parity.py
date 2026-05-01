#!/usr/bin/env python3
"""Rule BG: Proto cross-language parity guard.

Ensures every .proto file has corresponding generated code in Go, Python,
and Dart, and that generated files are not stale (older than their proto source).
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PROTO_DIR = REPO_ROOT / "proto"
GO_GEN_DIR = REPO_ROOT / "backend/gateway/gen"
PY_GEN_DIR = REPO_ROOT / "backend/app/gen"
DART_GEN_DIR = REPO_ROOT / "mobile/lib/gen"

PROTO_FILES = sorted(PROTO_DIR.glob("*.proto"))

# Mapping: proto basename → expected generated file patterns per language
# Each value is a list of glob patterns relative to the gen directory.
PROTO_TO_GO: dict[str, list[str]] = {
    "agent_service.proto": ["agent/v1/agent_service.pb.go", "agent/v1/agent_service_grpc.pb.go"],
    "community_service.proto": ["community/community_service.pb.go", "community/community_service_grpc.pb.go"],
    "error_book.proto": ["proto/error_book/error_book.pb.go", "proto/error_book/error_book_grpc.pb.go"],
    "galaxy_service.proto": ["galaxy/v1/galaxy_service.pb.go", "galaxy/v1/galaxy_service_grpc.pb.go"],
    "stt_service.proto": ["stt/v1/stt_service.pb.go", "stt/v1/stt_service_grpc.pb.go"],
    "user_state.proto": ["userstate/v1/user_state.pb.go"],
    "websocket.proto": ["ws/websocket.pb.go"],
}

PROTO_TO_PY: dict[str, list[str]] = {
    "agent_service.proto": ["agent_service_pb2.py", "agent_service_pb2_grpc.py"],
    "community_service.proto": ["community_service_pb2.py", "community_service_pb2_grpc.py"],
    "error_book.proto": ["error_book_pb2.py", "error_book_pb2_grpc.py"],
    "galaxy_service.proto": ["galaxy_service_pb2.py", "galaxy_service_pb2_grpc.py"],
    "stt_service.proto": ["stt_service_pb2.py", "stt_service_pb2_grpc.py"],
    "user_state.proto": ["user_state_pb2.py"],
    "websocket.proto": ["websocket_pb2.py"],
}

PROTO_TO_DART: dict[str, list[str]] = {
    "agent_service.proto": ["agent_service.pb.dart", "agent_service.pbenum.dart"],
    "community_service.proto": ["community_service.pb.dart", "community_service.pbenum.dart"],
    "error_book.proto": ["error_book.pb.dart", "error_book.pbenum.dart"],
    "galaxy_service.proto": ["galaxy_service.pb.dart", "galaxy_service.pbenum.dart"],
    "stt_service.proto": ["stt_service.pb.dart", "stt_service.pbenum.dart"],
    "user_state.proto": ["user_state.pb.dart", "user_state.pbenum.dart"],
    "websocket.proto": ["websocket.pb.dart", "websocket.pbenum.dart"],
}


def check_generated_files(
    proto_name: str,
    gen_dir: Path,
    expected_patterns: list[str],
    lang: str,
) -> list[str]:
    violations: list[str] = []
    for pattern in expected_patterns:
        gen_file = gen_dir / pattern
        if not gen_file.exists():
            violations.append(
                f"BG001 {lang} generated file missing: {pattern} (from {proto_name})"
            )
        elif gen_file.stat().st_size == 0:
            violations.append(
                f"BG002 {lang} generated file empty: {pattern} (from {proto_name})"
            )
    return violations


def check_staleness(proto_path: Path, gen_dir: Path, expected_patterns: list[str], lang: str) -> list[str]:
    violations: list[str] = []
    proto_mtime = proto_path.stat().st_mtime
    for pattern in expected_patterns:
        gen_file = gen_dir / pattern
        if gen_file.exists() and gen_file.stat().st_mtime < proto_mtime:
            violations.append(
                f"BG003 {lang} generated file stale: {pattern} is older than {proto_path.name}"
            )
    return violations


def main() -> int:
    violations: list[str] = []
    warnings: list[str] = []

    for proto_path in PROTO_FILES:
        proto_name = proto_path.name
        if proto_name not in PROTO_TO_GO:
            violations.append(f"BG004 unmapped proto file: {proto_name}")
            continue

        violations.extend(check_generated_files(proto_name, GO_GEN_DIR, PROTO_TO_GO[proto_name], "Go"))
        violations.extend(check_generated_files(proto_name, PY_GEN_DIR, PROTO_TO_PY[proto_name], "Python"))
        violations.extend(check_generated_files(proto_name, DART_GEN_DIR, PROTO_TO_DART[proto_name], "Dart"))
        warnings.extend(check_staleness(proto_path, GO_GEN_DIR, PROTO_TO_GO[proto_name], "Go"))
        warnings.extend(check_staleness(proto_path, PY_GEN_DIR, PROTO_TO_PY[proto_name], "Python"))
        warnings.extend(check_staleness(proto_path, DART_GEN_DIR, PROTO_TO_DART[proto_name], "Dart"))

    for w in warnings:
        print(f"[Rule BG] WARN {w}")

    if violations:
        print("[Rule BG] FAIL")
        for v in violations:
            print(v)
        return 1

    print(f"[Rule BG] PASS - checked {len(PROTO_FILES)} proto files across Go/Python/Dart ({len(warnings)} staleness warnings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
