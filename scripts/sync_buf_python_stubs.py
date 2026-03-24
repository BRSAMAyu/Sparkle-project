#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

# Python protobuf stubs are generated at backend/app/gen/*.py, while runtime
# imports still use versioned packages such as app.gen.agent.v1. Mirror the
# generated root-level stubs into the package paths the backend imports.
SYNC_MAP = {
    "backend/app/gen/agent_service_pb2.py": "backend/app/gen/agent/v1/agent_service_pb2.py",
    "backend/app/gen/agent_service_pb2_grpc.py": "backend/app/gen/agent/v1/agent_service_pb2_grpc.py",
    "backend/app/gen/galaxy_service_pb2.py": "backend/app/gen/galaxy/v1/galaxy_service_pb2.py",
    "backend/app/gen/galaxy_service_pb2_grpc.py": "backend/app/gen/galaxy/v1/galaxy_service_pb2_grpc.py",
    "backend/app/gen/stt_service_pb2.py": "backend/app/gen/stt/v1/stt_service_pb2.py",
    "backend/app/gen/stt_service_pb2_grpc.py": "backend/app/gen/stt/v1/stt_service_pb2_grpc.py",
    "backend/app/gen/websocket_pb2.py": "backend/app/gen/ws/websocket_pb2.py",
    "backend/app/gen/websocket_pb2.pyi": "backend/app/gen/ws/websocket_pb2.pyi",
}


def main() -> int:
    copied = 0
    for source_rel, target_rel in SYNC_MAP.items():
        source = REPO_ROOT / source_rel
        target = REPO_ROOT / target_rel
        if not source.exists():
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1

    print(f"Synced {copied} Python protobuf runtime stubs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
