import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_rule_k_write_paths import scan_rule_z_paths


def test_rule_z_guard_detects_sha1_based_mention_hash(tmp_path):
    repo_root = tmp_path / "repo"
    file_path = repo_root / "backend/app/services/social_guard_sample.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "mentioned_entity_hash = hashlib.sha1(normalized_person_name.encode('utf-8')).hexdigest()\n",
        encoding="utf-8",
    )

    violations = scan_rule_z_paths([file_path], repo_root)
    assert [item.rule_id for item in violations] == ["RZ001"]


def test_rule_z_guard_detects_cross_user_join(tmp_path):
    repo_root = tmp_path / "repo"
    file_path = repo_root / "backend/app/services/social_join_sample.sql"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "SELECT * FROM a JOIN b ON a.mentioned_entity_hash = b.mentioned_entity_hash\n",
        encoding="utf-8",
    )

    violations = scan_rule_z_paths([file_path], repo_root)
    assert [item.rule_id for item in violations] == ["RZ002"]
