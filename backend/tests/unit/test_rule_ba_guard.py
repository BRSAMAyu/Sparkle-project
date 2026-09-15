from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "guards" / "check_rule_ba_gateway_contract_parity.py"
sys.path.insert(0, str(REPO_ROOT))

from scripts.guards.check_rule_ba_gateway_contract_parity import scan_rule_ba


def test_rule_ba_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_ba_guard_flags_missing_go_field(tmp_path) -> None:
    go_path = tmp_path / "backend" / "gateway" / "internal" / "handler"
    dart_path = tmp_path / "mobile" / "lib" / "features" / "chat" / "data" / "models"
    go_path.mkdir(parents=True)
    dart_path.mkdir(parents=True)

    (go_path / "chat_history.go").write_text(
        """
package handler

type ChatHistoryMessageDTO struct {
    ID string `json:"id"`
    Content string `json:"content"`
}
""".strip(),
        encoding="utf-8",
    )
    (dart_path / "chat_message_model.dart").write_text(
        """
class ChatMessageModel {
  factory ChatMessageModel.fromJson(Map<String, dynamic> json) {
    final normalized = Map<String, dynamic>.from(json);
    normalized['conversation_id'] = json['conversation_id'] ?? json['session_id'];
    return ChatMessageModel._();
  }

  ChatMessageModel._();
  final String id;
  @JsonKey(name: 'conversation_id')
  final String conversationId;
  final String content;

  Map<String, dynamic> toJson() => {};
}
""".strip(),
        encoding="utf-8",
    )

    _, _, violations = scan_rule_ba(repo_root=tmp_path)

    assert any("BA001" in item and "conversation_id" in item for item in violations)
    assert any("BA001" in item and "session_id" in item for item in violations)
