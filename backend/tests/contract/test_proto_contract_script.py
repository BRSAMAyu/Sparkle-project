from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


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


def test_export_proto_snapshot_includes_agent_chat_contract():
    module = _load_module("scripts/export_proto_contract_snapshot.py", "export_proto_contract_snapshot_agent_test")

    snapshot = module.build_snapshot()

    agent_file = snapshot["files"]["agent_service.proto"]
    assert agent_file["package"] == "agent.v1"
    assert "agent.v1.AgentService" in agent_file["services"]

    chat_request = agent_file["messages"]["agent.v1.ChatRequest"]
    request_fields = {field["name"]: field["number"] for field in chat_request["fields"]}
    assert request_fields["message"] == 3
    assert request_fields["tool_result"] == 7
    assert request_fields["chat_mode"] == 13

    chat_response = agent_file["messages"]["agent.v1.ChatResponse"]
    response_fields = {field["name"]: field["number"] for field in chat_response["fields"]}
    assert response_fields["trace_id"] == 15
    assert response_fields["event_time"] == 19
    assert response_fields["session_id"] == 20


def test_export_dependency_snapshot_captures_three_language_manifests():
    module = _load_module("scripts/export_dependency_snapshot.py", "export_dependency_snapshot_test")

    snapshot = module.build_snapshot(REPO_ROOT)

    assert "fastapi" in snapshot["python"]
    assert "github.com/gin-gonic/gin" in snapshot["go"]["direct"]
    assert "dio" in snapshot["flutter"]


def test_dependency_snapshot_requirement_parser_handles_extras_and_markers(tmp_path):
    module = _load_module("scripts/export_dependency_snapshot.py", "export_dependency_snapshot_parser_test")
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        "\n".join(
            [
                "passlib[bcrypt]>=1.7.4",
                "foo>=1.0; python_version < '3.12'",
                "bar",
            ]
        ),
        encoding="utf-8",
    )

    parsed = module._parse_requirements(requirements)

    assert parsed == {
        "bar": "*",
        "foo": ">=1.0 ; python_version < \"3.12\"",
        "passlib[bcrypt]": ">=1.7.4",
    }


def test_dependency_snapshot_prefers_go_tool_output_for_replace_entries():
    module = _load_module("scripts/export_dependency_snapshot.py", "export_dependency_snapshot_go_tool_test")
    go_mod_json = """
{
  "Require": [
    {"Path": "example.com/direct", "Version": "v1.2.3"},
    {"Path": "example.com/indirect", "Version": "v0.9.0", "Indirect": true},
    {"Path": "example.com/replaced", "Version": "v1.0.0"}
  ],
  "Replace": [
    {
      "Old": {"Path": "example.com/replaced", "Version": "v1.0.0"},
      "New": {"Path": "../local/replaced"}
    }
  ]
}
""".strip()

    with patch.object(module, "_run_command", return_value=go_mod_json):
        parsed = module._build_go_snapshot_from_tool(REPO_ROOT)

    assert parsed == {
        "direct": {
            "example.com/direct": "v1.2.3",
            "example.com/replaced": "v1.0.0 => ../local/replaced",
        },
        "indirect": {
            "example.com/indirect": "v0.9.0",
        },
    }
