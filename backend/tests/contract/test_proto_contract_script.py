from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module(relative_path: str, name: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_export_proto_snapshot_includes_websocket_contract():
    module = _load_module("scripts/export_proto_contract_snapshot.py", "export_proto_contract_snapshot_test")

    snapshot = module.build_snapshot()

    websocket_file = snapshot["files"]["websocket.proto"]
    assert websocket_file["package"] == "sparkle.ws"
    assert "sparkle.ws.WebSocketMessage" in websocket_file["messages"]
    ws_message = websocket_file["messages"]["sparkle.ws.WebSocketMessage"]
    field_names = [field["name"] for field in ws_message["fields"]]
    assert field_names[:4] == ["version", "type", "payload", "trace_id"]


def test_export_dependency_snapshot_captures_three_language_manifests():
    module = _load_module("scripts/export_dependency_snapshot.py", "export_dependency_snapshot_test")

    snapshot = module.build_snapshot(REPO_ROOT)

    assert "fastapi" in snapshot["python"]
    assert "github.com/gin-gonic/gin" in snapshot["go"]["direct"]
    assert "dio" in snapshot["flutter"]
