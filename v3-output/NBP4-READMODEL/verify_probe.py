#!/usr/bin/env python3
"""NBP-4 · 活栈验证探针：任务完成 → 星图读模型可见延迟测量.

用法（针对运行中的 Python 引擎 FastAPI :8000，不是 Go 网关）：

    python3 verify_probe.py --base-url http://127.0.0.1:8000
    python3 verify_probe.py --timeout 120 --poll-interval 0.2

流程（API 级，零凭据、零 DB 直连）：
  1. 注册一次性用户（用户名 nbp4_<rand>，密码随机不入输出）；
  2. GET /api/v1/galaxy/graph 预热读面缓存（记录基线节点数）；
  3. POST /api/v1/tasks 建一个学习任务（标题含随机锚）；
  4. POST /api/v1/tasks/{id}/start → /complete（触发 outcome.recorded → 吸收链）；
  5. 完成时刻 t0 起以 poll-interval 轮询 GET /api/v1/galaxy/graph，
     直到任务星（确定性标题锚 uuid5(title)）出现 mastery>0 或超时；
  6. 输出延迟与判定：PASS < 60s（分钟级消除），并单独标注
     「首拍即见」（第一轮询即命中 = 亚秒级爽点，NBP-6 同款体验）。

判定线（默认 60s）可用 --threshold 覆盖。退出码：0=PASS，1=FAIL，2=环境错误。
"""

from __future__ import annotations

import argparse
import secrets
import sys
import time
import uuid

import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
API = "/api/v1"


def _request(method: str, url: str, *, token: str | None = None, body: dict | None = None, timeout: float = 15.0):
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        import json

        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            import json

            return resp.status, (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")[:400]


def _graph_nodes(base_url: str, token: str) -> list[dict]:
    status, body = _request("GET", f"{base_url}{API}/galaxy/graph", token=token)
    if status != 200:
        raise RuntimeError(f"GET /galaxy/graph -> {status}: {body}")
    return body.get("nodes") or []


def _node_mastery(node: dict) -> float:
    status = node.get("user_status") or {}
    value = status.get("mastery_score")
    if value is None:
        value = node.get("mastery", 0) or 0
    return float(value or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=120.0, help="可见性等待上限秒数")
    parser.add_argument("--poll-interval", type=float, default=0.2)
    parser.add_argument("--threshold", type=float, default=60.0, help="PASS 判定线秒数（分钟级消除）")
    args = parser.parse_args()

    tag = uuid.uuid4().hex[:10]
    username = f"nbp4_{tag}"
    password = secrets.token_urlsafe(16)  # 一次性，不入任何输出
    email = f"nbp4_{tag}@probe.local"

    # 1. 注册（拿 token）
    status, body = _request(
        "POST",
        f"{args.base_url}{API}/auth/register",
        body={
            "username": username,
            "email": email,
            "password": password,
            "accepted_tos": True,
            "accepted_privacy": True,
        },
    )
    if status not in (200, 201):
        print(f"[ENV-ERROR] register -> {status}: {body}")
        return 2
    token = body.get("access_token") or body.get("token") or (body.get("data") or {}).get("access_token")
    if not token:
        # 兜底走 login
        status, body = _request(
            "POST", f"{args.base_url}{API}/auth/login", body={"username": username, "password": password}
        )
        token = body.get("access_token") or body.get("token")
    if not token:
        print(f"[ENV-ERROR] no token from register/login response keys={sorted(body)}")
        return 2
    print(f"[1] registered user={username}")

    # 2. 预热读面缓存（吸收前快照）
    try:
        before_nodes = _graph_nodes(args.base_url, token)
    except RuntimeError as exc:
        print(f"[ENV-ERROR] {exc}")
        return 2
    print(f"[2] galaxy graph warm read: total_nodes={len(before_nodes)}")

    # 3. 建任务（标题 = 确定性任务星锚）
    title = f"NBP4 探针任务 {tag}"
    status, body = _request(
        "POST",
        f"{args.base_url}{API}/tasks",
        token=token,
        body={"title": title, "type": "learning", "estimated_minutes": 5, "energy_cost": 1},
    )
    if status not in (200, 201):
        print(f"[ENV-ERROR] create task -> {status}: {body}")
        return 2
    task = body.get("data") or body
    task_id = task.get("id") or task.get("task_id")
    if not task_id:
        print(f"[ENV-ERROR] no task id in create response keys={sorted(task)}")
        return 2
    print(f"[3] task created id={task_id} title={title!r}")

    # 4. start → complete
    status, body = _request("POST", f"{args.base_url}{API}/tasks/{task_id}/start", token=token, body={})
    if status not in (200, 201):
        print(f"[ENV-ERROR] start task -> {status}: {body}")
        return 2
    status, body = _request(
        "POST", f"{args.base_url}{API}/tasks/{task_id}/complete", token=token, body={"actual_minutes": 5}
    )
    if status not in (200, 201):
        print(f"[ENV-ERROR] complete task -> {status}: {body}")
        return 2
    t0 = time.monotonic()
    print("[4] task completed (outcome.recorded emitted); polling galaxy read face...")

    # 5. 轮询读面直到任务星可见
    deadline = t0 + args.timeout
    first_hit_latency: float | None = None
    last_total = -1
    while time.monotonic() < deadline:
        nodes = _graph_nodes(args.base_url, token)
        last_total = len(nodes)
        star = next((n for n in nodes if n.get("name") == title), None)
        if star is not None and _node_mastery(star) > 0:
            first_hit_latency = time.monotonic() - t0
            break
        time.sleep(args.poll_interval)

    if first_hit_latency is None:
        print(f"[FAIL] task star not visible within {args.timeout:.0f}s (last total_nodes={last_total})")
        return 1

    verdict = "PASS" if first_hit_latency < args.threshold else "FAIL"
    instant = "（首拍即见，亚秒级）" if first_hit_latency < 1.0 else ""
    print(
        f"[5] star visible: latency={first_hit_latency:.2f}s {instant} "
        f"total_nodes={last_total} verdict={verdict} (threshold={args.threshold:.0f}s)"
    )
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
