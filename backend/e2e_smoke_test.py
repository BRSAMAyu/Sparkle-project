"""
End-to-end smoke test: gRPC StreamChat → Python FSM → Response stream.
Tests the full backend path that Flutter uses via Go Gateway.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid

# Match grpc_server.py path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, "app", "gen", "agent", "v1"))

import grpc

from app.gen.agent.v1 import agent_service_pb2, agent_service_pb2_grpc
from app.core.security import create_access_token
from app.config import settings
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

import redis as redis_sync


async def resolve_user_id() -> str:
    env_uid = os.getenv("TEST_USER_ID")
    if env_uid:
        return env_uid
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT id::text FROM users WHERE is_active = true LIMIT 1"))
        row = result.first()
        if row:
            return str(row[0])
    raise RuntimeError("No active user found. Seed demo data first.")


async def test_grpc_chat(user_id: str) -> dict:
    """Test 1: Direct gRPC StreamChat."""
    result = {"test": "gRPC StreamChat", "passed": False, "details": {}}
    session_id = str(uuid.uuid4())
    request = agent_service_pb2.ChatRequest(
        user_id=user_id,
        session_id=session_id,
        message="你好，我想制定一个学习计划",
        user_profile=agent_service_pb2.UserProfile(
            nickname="测试同学",
            timezone="Asia/Shanghai",
            language="zh-CN",
        ),
        request_id=f"e2e_smoke_{int(time.time())}",
    )
    token = create_access_token({"sub": user_id})
    internal_key = os.getenv("INTERNAL_API_KEY") or settings.INTERNAL_API_KEY
    metadata = (
        ("authorization", f"Bearer {token}"),
        ("user-id", user_id),
        ("x-trace-id", f"e2e_trace_{int(time.time())}"),
        ("x-internal-api-key", internal_key),
    )

    chunks = 0
    full_text = ""
    states_seen = []
    t0 = time.time()
    error_msg = None

    try:
        async with grpc.aio.insecure_channel("localhost:50051") as channel:
            stub = agent_service_pb2_grpc.AgentServiceStub(channel)
            async for response in stub.StreamChat(request, metadata=metadata):
                chunks += 1
                if response.HasField("delta"):
                    full_text += response.delta
                elif response.HasField("status_update"):
                    state_name = agent_service_pb2.AgentStatus.State.Name(response.status_update.state)
                    states_seen.append(state_name)
                elif response.HasField("full_text"):
                    full_text = response.full_text
                elif response.HasField("error"):
                    error_msg = f"[{response.error.code}] {response.error.message}"

        elapsed = time.time() - t0
        result["details"] = {
            "chunks": chunks,
            "response_length": len(full_text),
            "states_seen": states_seen,
            "elapsed_seconds": round(elapsed, 2),
            "error": error_msg,
            "has_meaningful_response": len(full_text) > 20,
        }
        result["passed"] = len(full_text) > 20 and error_msg is None

    except grpc.RpcError as e:
        result["details"]["error"] = f"gRPC {e.code()}: {e.details()}"
    except Exception as e:
        result["details"]["error"] = str(e)

    return result


def test_belief_state_pipeline() -> dict:
    """Test 2: BeliefState pipeline - verify traces in Redis."""
    result = {"test": "BeliefState Pipeline", "passed": False, "details": {}}

    try:
        r = redis_sync.Redis(host="127.0.0.1", port=6379, password="change-me", decode_responses=True)

        belief_keys = r.keys("aurora:belief_state:v1:*")
        trace_keys = r.keys("aurora:belief_trace:v1:*")

        trace_count = 0
        disagreement_count = 0
        sample_traces = []

        for key in trace_keys:
            entries = r.lrange(key, 0, -1)
            trace_count += len(entries)
            for raw in entries[:3]:
                try:
                    trace = json.loads(raw)
                    shadow = trace.get("router_shadow_projection", {})
                    actual = trace.get("actual_router_mode")
                    shadow_mode = shadow.get("shadow_mode")
                    if actual and shadow_mode and actual != shadow_mode:
                        disagreement_count += 1
                    if len(sample_traces) < 3:
                        sample_traces.append({
                            "user": key.split(":")[-1][:12],
                            "shadow": shadow_mode,
                            "actual": actual,
                            "disagreement": actual != shadow_mode if actual and shadow_mode else None,
                        })
                except json.JSONDecodeError:
                    pass

        result["details"] = {
            "belief_state_keys": len(belief_keys),
            "trace_keys": len(trace_keys),
            "total_traces": trace_count,
            "disagreement_count": disagreement_count,
            "sample_traces": sample_traces,
        }
        result["passed"] = trace_count > 0

    except Exception as e:
        result["details"]["error"] = str(e)

    return result


def test_go_gateway_health() -> dict:
    """Test 3: Go Gateway HTTP health."""
    import urllib.request

    result = {"test": "Go Gateway Health", "passed": False, "details": {}}
    try:
        req = urllib.request.Request("http://localhost:8080/api/v1/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
            result["details"] = {"status_code": resp.status, "body": body[:200]}
            result["passed"] = resp.status == 200
    except Exception as e:
        result["details"]["error"] = str(e)

    return result


def test_go_gateway_grpc_proxy() -> dict:
    """Test 4: Go Gateway → gRPC proxy health."""
    import urllib.request

    result = {"test": "Go Gateway gRPC Proxy", "passed": False, "details": {}}
    try:
        req = urllib.request.Request("http://localhost:8080/ready")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode())
            components = body.get("components", {})
            agent_status = components.get("grpc_agent", {}).get("status", "unknown")
            result["details"] = {"agent_status": agent_status, "all_components": {k: v.get("status") for k, v in components.items()}}
            result["passed"] = agent_status == "healthy"
    except Exception as e:
        result["details"]["error"] = str(e)

    return result


def test_db_data_integrity() -> dict:
    """Test 5: Database has seed data for testing."""
    import psycopg2

    result = {"test": "Database Data Integrity", "passed": False, "details": {}}
    try:
        conn = psycopg2.connect(
            host="127.0.0.1", port=5432, dbname="sparkle",
            user="brsama", password="change-me",
        )
        cur = conn.cursor()
        counts = {}
        for table in ("users", "achievements", "plans", "tasks", "goals"):
            try:
                cur.execute(f"SELECT count(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            except Exception:
                counts[table] = "N/A"
        cur.close()
        conn.close()
        result["details"] = counts
        result["passed"] = counts.get("users", 0) > 0
    except Exception as e:
        result["details"]["error"] = str(e)

    return result


async def run_all():
    print("=" * 70)
    print("  SPARKLE E2E SMOKE TEST")
    print("=" * 70)
    print()

    user_id = await resolve_user_id()
    print(f"[INFO] Using user_id: {user_id}")

    results = []

    # Sync tests
    print("[1/5] Go Gateway health...", end=" ")
    r = test_go_gateway_health()
    print("PASS" if r["passed"] else "FAIL")
    results.append(r)

    print("[2/5] Go Gateway gRPC proxy...", end=" ")
    r = test_go_gateway_grpc_proxy()
    print("PASS" if r["passed"] else "FAIL")
    results.append(r)

    print("[3/5] Database integrity...", end=" ")
    r = test_db_data_integrity()
    print("PASS" if r["passed"] else "FAIL")
    results.append(r)

    print("[4/5] BeliefState pipeline...", end=" ")
    r = test_belief_state_pipeline()
    print("PASS" if r["passed"] else "FAIL")
    results.append(r)

    print("[5/5] gRPC StreamChat (this may take 10-30s)...", end=" ", flush=True)
    r = await test_grpc_chat(user_id)
    print("PASS" if r["passed"] else "FAIL")
    results.append(r)

    print()
    print("=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n  {passed}/{total} tests passed\n")

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['test']}")
        for k, v in r["details"].items():
            if k == "sample_traces":
                print(f"         {k}:")
                for st in v:
                    print(f"           user={st['user']} shadow={st['shadow']} actual={st['actual']} disagreement={st['disagreement']}")
            elif k != "error" or not r["passed"]:
                print(f"         {k}: {v}")

    # Save full report
    report_path = os.path.join(current_dir, "e2e_smoke_report.json")
    with open(report_path, "w") as f:
        json.dump({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "user_id": user_id, "results": results}, f, indent=2, default=str)
    print(f"\n  Full report: {report_path}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
