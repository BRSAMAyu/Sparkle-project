#!/usr/bin/env python3
"""V4-Q01 只读 DB 三证对齐采集器（SELECT-only，铁律：不写库）。

对指定 guest 用户（按 username 前缀）拉取旅程六环节的 DB 侧证据，
输出 json（机器比对）+ txt（人读），供三证对齐表引用。

用法：
  python3 scripts/devtools/q01_db_evidence.py <guest_username> <out_prefix>
"""
from __future__ import annotations

import json
import subprocess
import sys


Q = {
    "user": """
        SELECT id, username, registration_source, created_at
        FROM users WHERE username = %(u)s
    """,
    "memory_goals": """
        SELECT id, title, status, created_at, archived_at
        FROM memory_goals WHERE user_id = %(uid)s ORDER BY created_at
    """,
    "tasks": """
        SELECT id, title, status, estimated_minutes, updated_at
        FROM tasks WHERE user_id = %(uid)s ORDER BY created_at
    """,
    "memory_corrections": """
        SELECT id, memory_type, memory_id, action, LEFT(reason, 200) AS reason_head, created_at
        FROM memory_corrections WHERE user_id = %(uid)s AND deleted_at IS NULL ORDER BY created_at
    """,
    "calibration_runs": """
        SELECT id, overall_status, ran_at, window_days, schema_version, created_at
        FROM understanding_calibration_runs WHERE user_id = %(uid)s AND deleted_at IS NULL ORDER BY created_at
    """,
    "agent_runs": """
        SELECT id, kind, status, current_stage, trace_id, task_id, session_id, created_at, updated_at
        FROM agent_runs WHERE user_id = %(uid)s ORDER BY created_at
    """,
    "hybrid_artifacts": """
        SELECT a.id, a.run_id, a.stage, a.task_id, a.created_at,
               LEFT(a.payload::text, 300) AS payload_head
        FROM hybrid_journey_artifacts a
        JOIN agent_runs r ON r.id = a.run_id
        WHERE r.user_id = %(uid)s ORDER BY a.created_at
    """,
    "agent_tool_calls": """
        SELECT id, tool_name, idempotency_key, status, created_at
        FROM agent_tool_calls WHERE user_id = %(uid)s ORDER BY created_at
    """,
    "stored_files": """
        SELECT id, file_name, mime_type, status, created_at
        FROM stored_files WHERE user_id = %(uid)s ORDER BY created_at
    """,
    "document_chunks": """
        SELECT c.id, c.file_id, c.chunk_index, LEFT(c.content, 120) AS content_head
        FROM document_chunks c
        JOIN stored_files f ON f.id = c.file_id
        WHERE f.user_id = %(uid)s ORDER BY c.file_id, c.chunk_index
    """,
    "token_usage": """
        SELECT id, model, model_tier, prompt_tokens,
               completion_tokens, total_tokens, created_at
        FROM token_usage WHERE user_id = %(uid)s AND deleted_at IS NULL ORDER BY created_at
    """,
    "event_store": """
        SELECT event_type, COUNT(*) AS n
        FROM event_store WHERE aggregate_id = %(uid)s::text
        GROUP BY event_type ORDER BY event_type
    """,
}


def q(sql: str, params: dict) -> dict:
    out = subprocess.run(
        ["docker", "exec", "sparkle_db", "psql", "-U", "postgres", "-d", "sparkle",
         "-A", "-t", "-c", sql],
        capture_output=True, text=True,
    )
    return {"returncode": out.returncode, "stdout": out.stdout, "stderr": out.stderr[-400:]}


def q_json(sql: str, params: dict) -> list:
    def lit(v):
        return "'" + str(v).replace("'", "''") + "'"
    rendered = sql.replace("%(uid)s", lit(params.get("uid", ""))).replace("%(u)s", lit(params.get("u", "")))
    out = subprocess.run(
        ["docker", "exec", "sparkle_db", "psql", "-U", "postgres", "-d", "sparkle",
         "-A", "-t", "-c",
         "SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json) FROM (" + rendered + " LIMIT 200) t;"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return [{"__error__": out.stderr}]
    try:
        return json.loads(out.stdout.strip() or "[]")
    except json.JSONDecodeError:
        return [{"__parse_error__": out.stdout[:200]}]


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    username, prefix = sys.argv[1], sys.argv[2]
    users = q_json(Q["user"], {"u": username})
    users = [u for u in users if isinstance(u, dict) and "id" in u]
    if not users:
        print(f"user {username} not found")
        return 1
    uid = users[0]["id"]
    result: dict = {"username": username, "user_id": uid, "collected_at__utc": None, "readonly": True}
    for name, sql in Q.items():
        result[name] = q_json(sql, {"u": username, "uid": uid})
    out_json = f"{prefix}_db_evidence.json"
    with open(out_json, "w") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2, default=str)
    lines = [f"# DB evidence (readonly) user={username} id={uid}"]
    for name in Q:
        lines.append(f"\n## {name} ({len(result[name])} rows)")
        for row in result[name][:20]:
            lines.append("  " + json.dumps(row, ensure_ascii=False, default=str)[:300])
    with open(f"{prefix}_db_evidence.txt", "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"ok {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
