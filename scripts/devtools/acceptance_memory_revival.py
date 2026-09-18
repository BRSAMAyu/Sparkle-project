#!/usr/bin/env python3
"""记忆链复活端到端验收（memory-revival round2，MR-1/2/3/4 修复后全链真跑）。

对应多端实测 docs/competition/2026-tmall-hackathon/多端实测/memory-rag-seedlib-eval.md
的 A1/A2(短问句)/B1+B1' 场景。前置条件：
  1. 主栈在跑：gateway :8080（新版引擎已 apply memory-revival patch 并重启）
  2. PostgreSQL/Redis/MinIO 容器在跑（sparkle_db / sparkle_redis / sparkle_minio）
  3. Celery worker 已启动（bash scripts/devtools/start_celery_worker_dev.sh）
  4. 本机可 docker exec（DB 断言用，不消耗 LLM）

LLM 预算：5 次聊天调用（埋点×2 + 跨会话提问×2 + RAG 问答×1），
另有 1 次 embedding 调用（上传切片向量化，非聊天 LLM）。

用法：
  /opt/homebrew/bin/python3.11 scripts/devtools/acceptance_memory_revival.py

产出：逐项 PASS/FAIL 与最终摘要（0 退出码 = 全过）。
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from uuid import uuid4

import websocket

GATEWAY = "http://localhost:8080"
DB_CONTAINER = "sparkle_db"
DB_NAME = "sparkle"
RAG_KEYWORD = "MRV-7749"  # 本轮验收专用唯一关键词，避免历史数据干扰
RESULTS: list[dict] = []


def http(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: float = 30.0):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{GATEWAY}{path}",
        method=method,
        headers=headers,
        data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def ws_ticket(token: str) -> str:
    data = http("POST", "/api/v1/ws/ticket", token=token, body={})
    return data.get("ticket") or (data.get("data") or {}).get("ticket") or ""


def ws_chat(token: str, session_id: str, message: str, timeout_s: float = 90.0, extra: dict | None = None) -> dict:
    ticket = ws_ticket(token)
    ws = websocket.create_connection(f"ws://localhost:8080/ws/chat?ticket={ticket}", timeout=timeout_s)
    payload = {"type": "message", "message": message, "session_id": session_id}
    if extra:
        payload.update(extra)
    ws.send(json.dumps(payload, ensure_ascii=False))
    parts: list[str] = []
    meta: dict = {}
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            break
        if not raw:
            continue
        try:
            frame = json.loads(raw)
        except (TypeError, ValueError):
            continue
        ftype = str(frame.get("type") or frame.get("event") or "")
        if ftype in ("delta", "content_delta", "text_delta", "stream"):
            delta = frame.get("delta") or frame.get("content") or frame.get("text") or ""
            if delta:
                parts.append(delta)
        elif ftype in ("full_text", "message", "response", "chat_response", "final"):
            txt = (
                frame.get("full_text")
                or frame.get("content")
                or frame.get("text")
                or (frame.get("data") or {}).get("content", "")
            )
            if txt and txt not in "".join(parts):
                parts.append(txt)
        if isinstance(frame.get("metadata"), dict):
            meta.update(frame["metadata"])
        if ftype in ("done", "end", "complete", "stream_end", "response_end"):
            break
    ws.close()
    return {"text": "".join(parts).strip(), "metadata": meta, "elapsed": round(time.time() - t0, 1)}


def db_scalar(sql: str) -> str:
    out = subprocess.run(
        ["docker", "exec", DB_CONTAINER, "psql", "-U", "postgres", "-d", DB_NAME, "-tAc", sql],
        capture_output=True,
        text=True,
    )
    return (out.stdout or "").strip()


def record(step: str, ok: bool, detail: str) -> None:
    RESULTS.append({"step": step, "ok": ok, "detail": detail})
    print(f"{'✅ PASS' if ok else '⛔ FAIL'} | {step} | {detail}")


def main() -> int:
    # ---- 0. 游客身份 ----
    guest = http("POST", "/api/v1/auth/guest", body={"guest_id": f"memrev_{uuid4().hex[:8]}"})
    token = guest["access_token"]
    user_id = guest["user"]["id"]
    print(f"guest user_id={user_id}")

    # ---- MR-1/2 验收 a：跨会话记忆 ----
    s1 = str(uuid4())
    seed_exam = ws_chat(token, s1, "我下周三有数据结构期中考试，帮我记住这个。")
    record(
        "a1.seeded-exam(会话1)",
        "数据结构" in seed_exam["text"] or "记" in seed_exam["text"],
        f"reply[:80]={seed_exam['text'][:80]!r}",
    )
    seed_movie = ws_chat(token, s1, "我最喜欢的电影是《星际穿越》，帮我记住这个。")
    record(
        "a1.seeded-movie(会话1)",
        "星际穿越" in seed_movie["text"] or "记" in seed_movie["text"],
        f"reply[:80]={seed_movie['text'][:80]!r}",
    )

    # 等待异步记忆 lane（enqueue_from_session 为后台任务）
    deadline = time.time() + 30
    lanes = "0"
    while time.time() < deadline:
        lanes = db_scalar(
            f"SELECT count(*) FROM episodic_memories WHERE user_id='{user_id}' "
            f"AND source_lane='inferred_extraction' AND deleted_at IS NULL"
        )
        if lanes not in ("", "0"):
            break
        time.sleep(3)
    record(
        "mr1.episodic-written(聊天一轮后记忆表有写入)",
        lanes not in ("", "0"),
        f"inferred_extraction rows={lanes} (期望>=1，跨轮异步最多等30s)",
    )

    s2 = str(uuid4())
    q1 = ws_chat(token, s2, "根据你的记忆，我之前提到过什么考试？")
    record(
        "a2.cross-session-recall(新会话2含答案)",
        "数据结构" in q1["text"],
        f"reply[:120]={q1['text'][:120]!r}",
    )

    s3 = str(uuid4())
    q2 = ws_chat(token, s3, "我最喜欢的电影是什么？")
    record(
        "a2.slim-short-recall(新会话3短问句召回)",
        "星际穿越" in q2["text"],
        f"reply[:120]={q2['text'][:120]!r}",
    )

    # ---- MR-3/4 验收 c：文档上传 → RAG 问答引用 ----
    doc_text = (
        f"{RAG_KEYWORD} 材料验收说明。\n"
        f"{RAG_KEYWORD} 是 Sparkle 验收测试专用的星火物质编号：由实验室在第 2049 次实验中合成的"
        f"蓝色荧光晶体，遇紫外线会发出星轨状磷光，保存温度要求零下 20 摄氏度。"
    ).encode()
    upload = http(
        "POST",
        "/api/v1/documents/upload",
        token=token,
        body={
            "filename": f"{RAG_KEYWORD.lower()}_note.txt",
            "mime_type": "text/plain",
            "file_size": len(doc_text),
            "visibility": "private",
        },
    )
    file_id, presigned = upload.get("file_id"), upload.get("presigned_url")
    put_req = urllib.request.Request(presigned, data=doc_text, method="PUT", headers={"Content-Type": "text/plain"})
    with urllib.request.urlopen(put_req, timeout=30) as resp:
        put_ok = resp.status == 200
    record("mr3.presigned-put(凭证对齐后上传)", put_ok, f"file_id={file_id}")

    confirm = http("POST", f"/api/v1/documents/{file_id}/confirm-upload", token=token, body={})
    job_ok = bool(confirm.get("job_id"))
    record("mr3.confirm-queued(celery 消费)", job_ok, f"confirm={ {k: confirm.get(k) for k in ('job_id', 'estimated_seconds')} }")

    status = ""
    deadline = time.time() + 120
    while time.time() < deadline:
        st = http("GET", f"/api/v1/documents/{file_id}/status", token=token)
        status = str(st.get("status") or st.get("stage") or "")
        if status in {"processed", "completed", "ready", "done", "succeeded"}:
            break
        if status in {"failed", "error"}:
            break
        time.sleep(4)
    record("mr3.processed(切片+embedding 入库)", status in {"processed", "completed", "ready", "done", "succeeded"}, f"final status={status}")

    s4 = str(uuid4())
    q3 = ws_chat(
        token,
        s4,
        f"{RAG_KEYWORD} 是什么？请根据我上传的资料回答它的性状与保存要求。",
        extra={"use_document_context": True},
    )
    grounding_ok = RAG_KEYWORD in q3["text"] and ("磷光" in q3["text"] or "荧光" in q3["text"] or "零下" in q3["text"])
    refused = ("没有拿到" in q3["text"]) or ("不能复述" in q3["text"]) or ("没有找到相关" in q3["text"])
    record(
        "mr4.rag-cited(RAG 问答引用材料)",
        grounding_ok and not refused,
        f"reply[:160]={q3['text'][:160]!r}",
    )

    # ---- 摘要 ----
    passed = sum(1 for r in RESULTS if r["ok"])
    total = len(RESULTS)
    summary = {
        "passed": passed,
        "total": total,
        "chat_llm_calls": 5,
        "results": RESULTS,
    }
    print("\n== SUMMARY ==")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, ensure_ascii=False))
    return 0 if passed == total else 1


if __name__ == "__main__":
    if Path(__file__).stem and sys.version_info < (3, 11):
        print("need python3.11+")
        sys.exit(2)
    sys.exit(main())
