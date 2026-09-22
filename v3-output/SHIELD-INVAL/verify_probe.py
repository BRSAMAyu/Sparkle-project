#!/usr/bin/env python3
"""SHIELD-INVAL · 活栈复验探针：诊断评分 → 星图 API 双层缓存立即失效验证.

背景（LOOP4 CP-00 假 fail 的最后一块，活栈实证）：``GET /api/v1/galaxy/graph``
有两层读面缓存——服务层 ``@cached(ttl=600)``（NBP-4 已挂失效）与 API 层
``_galaxy_graph_shield``（single-flight + 10s TTL）。修复前 shield 无失效面：
prime 后诊断评分，Redis 视图键已删，但 shield 仍回 prime 时的旧快照
（mastery 全 null），星图最长 10s 不更新。

用法（针对运行中的 Python 引擎 FastAPI :8000，不是 Go 网关）：

    python3 verify_probe.py --base-url http://127.0.0.1:8000

流程（API 级黑盒，零凭据、零 DB 直连）：
  1. 注册一次性用户（shieldinval_<rand>，密码随机不入输出）并登录取 token；
  2. GET /api/v1/galaxy/graph → prime 两层缓存（记录快照指纹）；
  3. POST /api/v1/exam-sprint/diagnose/generate（exam_prep_14d 包，10 题，
     零 LLM）→ diagnostic_id；
  4. POST /api/v1/exam-sprint/diagnose/grade（全部答 A、update_galaxy=true，
     触发 _write_mastery_value → 失效链）；
  5. 立即（零 sleep）再 GET graph：断言出现带 user_status（mastery 可见）
     的节点，且整图 payload 与 prime 快照不同——
     修复前：shield 回旧快照 → 「payload 未变 + 0 个状态节点」= FAIL；
     修复后：两层失效 → 新图立即可见 = PASS。

退出码：0=PASS，1=FAIL（复现陈旧读面），2=环境错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
import urllib.error
import urllib.request

GRADE_ANSWER = "A"


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict | list | str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:
            return exc.code, {}
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[ENV] 无法连接 {url}: {exc}")
        sys.exit(2)


def _fingerprint(graph: dict) -> str:
    return hashlib.sha256(json.dumps(graph, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def _status_nodes(graph: dict) -> list[str]:
    return [n["id"] for n in graph.get("nodes", []) if n.get("user_status") is not None]


def main() -> None:
    parser = argparse.ArgumentParser(description="SHIELD-INVAL galaxy 双层缓存失效复验探针")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Python 引擎 FastAPI 地址")
    parser.add_argument("--subject", default="计算机网络", help="诊断科目")
    parser.add_argument("--question-count", type=int, default=10, help="诊断题数（10-15）")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    rand = secrets.token_hex(6)
    username = f"shieldinval_{rand}"
    password = secrets.token_urlsafe(16)

    # 1. 注册 + 登录（零凭据：一次性账号，密码不入输出）
    status, _ = _request(
        "POST",
        f"{base}/api/v1/auth/register",
        payload={
            "username": username,
            "email": f"{username}@sparkleprobe.dev",
            "password": password,
            "accepted_tos": True,
            "accepted_privacy": True,
        },
    )
    if status not in (200, 201):
        print(f"[ENV] 注册失败 HTTP {status}")
        sys.exit(2)
    status, body = _request(
        "POST", f"{base}/api/v1/auth/login", payload={"username": username, "password": password}
    )
    token = body.get("access_token") if isinstance(body, dict) else None
    if status != 200 or not token:
        print(f"[ENV] 登录失败 HTTP {status}: {str(body)[:200]}")
        sys.exit(2)
    print(f"[1] 一次性用户就绪: {username}")

    # 2. prime 两层缓存（服务层 @cached + API shield 10s TTL）
    status, prime = _request("GET", f"{base}/api/v1/galaxy/graph", token=token, timeout=60.0)
    if status != 200:
        print(f"[ENV] 取图失败 HTTP {status}")
        sys.exit(2)
    prime_fp = _fingerprint(prime)
    print(f"[2] 图已 prime: nodes={len(prime.get('nodes', []))} fingerprint={prime_fp}")

    # 3. 生成诊断卷（exam_prep_14d 静态包，零 LLM）
    status, gen = _request(
        "POST",
        f"{base}/api/v1/exam-sprint/diagnose/generate",
        token=token,
        payload={"subject": args.subject, "question_count": args.question_count},
        timeout=60.0,
    )
    diagnostic_id = gen.get("diagnostic_id") if isinstance(gen, dict) else None
    questions = gen.get("questions", []) if isinstance(gen, dict) else []
    if status != 200 or not diagnostic_id or not questions:
        print(f"[ENV] 诊断生成失败 HTTP {status}: {str(gen)[:200]}")
        sys.exit(2)
    print(f"[3] 诊断卷就绪: diagnostic_id={diagnostic_id} questions={len(questions)}")

    # 4. 评分（全答 A、FUZZY 置信；update_galaxy=true 触发 mastery 写 + 失效链）
    answers = [{"question_id": q["question_id"], "answer": GRADE_ANSWER} for q in questions]
    status, grade = _request(
        "POST",
        f"{base}/api/v1/exam-sprint/diagnose/grade",
        token=token,
        payload={
            "subject": args.subject,
            "diagnostic_id": diagnostic_id,
            "answers": answers,
            "update_galaxy": True,
        },
        timeout=60.0,
    )
    updates = grade.get("node_mastery_updates", []) if isinstance(grade, dict) else []
    if status != 200 or not updates:
        print(f"[ENV] 评分失败 HTTP {status}: {str(grade)[:200]}")
        sys.exit(2)
    print(f"[4] 评分完成: {len(updates)} 个节点写入 mastery（含 0 分节点）")

    # 5. 立即重读（零 sleep）——判定窗口就在 shield 的 10s TTL 内
    status, fresh = _request("GET", f"{base}/api/v1/galaxy/graph", token=token, timeout=60.0)
    if status != 200:
        print(f"[ENV] 复读取图失败 HTTP {status}")
        sys.exit(2)
    fresh_fp = _fingerprint(fresh)
    status_nodes = _status_nodes(fresh)
    print(f"[5] 立即复读: fingerprint={fresh_fp} 带状态节点={len(status_nodes)}")

    # 6. 判定
    if fresh_fp == prime_fp:
        print(
            "[FAIL] 复读 payload 与 prime 快照完全一致 —— API 层 shield 未失效，"
            "回放写前旧值（修复前行为复现）"
        )
        sys.exit(1)
    if not status_nodes:
        print("[FAIL] 图有变化但无任何 user_status —— 评分链未落图（非本卡失效面问题，请查吸收链）")
        sys.exit(1)
    print(
        f"[PASS] 评分后立即取图即见 mastery（{len(status_nodes)} 个节点带状态，"
        f"fingerprint {prime_fp} → {fresh_fp}）：双层缓存失效正常"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
