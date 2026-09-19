"""API backend driver：经网关公开 REST+WS 通道驱动真实后端（非 UI 通道）。

复用 scripts/devtools/acceptance_memory_revival.py 的成熟模式：
  POST /api/v1/auth/register|login|guest -> token
  POST /api/v1/ws/ticket -> ticket
  ws://gateway/ws/chat?ticket=... 流式聊天
DB 断言只读（SELECT-only，docker exec psql），不向产品库写探针数据之外的内容；
一切写入都走产品自身公开 API（与真实用户等价），不直接写库、不 mock。

使用边界：api lane 不等于 UI 实测，输出与 manifest 必须标注 non-ui lane，
不得用来宣称"用户体验通过"（USER_SIMULATION.md Ban 条款）。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any
from uuid import uuid4

import websocket

from ..evidence import EvidenceCollector
from .base import BaseDriver, StepFailure


class ApiDriver(BaseDriver):
    name = "api"

    def __init__(self, evidence: EvidenceCollector, config: dict[str, Any]) -> None:
        super().__init__(evidence, config)
        self.gateway: str = str(self.config.get("gateway", "http://localhost:8080")).rstrip("/")
        self.timeout: float = float(self.config.get("timeout", 30.0))
        self.state: dict[str, Any] = {}  # journey 运行期上下文（token/user_id 等）

    def start(self) -> None:
        # 网关必须存活，否则直接失败（不允许"连不上=PASS"）
        try:
            with urllib.request.urlopen(f"{self.gateway}/healthz", timeout=5) as resp:
                body = json.loads(resp.read())
        except Exception as exc:
            raise StepFailure(f"网关 {self.gateway} 不可达: {exc}") from exc
        if str(body.get("status")) != "alive":
            raise StepFailure(f"网关 healthz 异常: {body}")

    # ---------- HTTP ----------
    def http(
        self,
        method: str,
        path: str,
        token: str | None = None,
        body: dict[str, Any] | None = None,
        timeout: float | None = None,
        expect_2xx: bool = True,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(
            f"{self.gateway}{path}",
            method=method,
            headers=headers,
            data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                payload = json.loads(resp.read())
                status = resp.status
        except urllib.error.HTTPError as exc:
            payload = {}
            try:
                payload = json.loads(exc.read())
            except Exception:
                pass
            status = exc.code
            self.evidence.log_api(
                "api",
                {"method": method, "path": path, "status": status, "elapsed_ms": int((time.time() - t0) * 1000), "response": payload},
            )
            if expect_2xx:
                raise StepFailure(f"{method} {path} -> HTTP {status}: {json.dumps(payload, ensure_ascii=False)[:300]}")
            return payload
        self.evidence.log_api(
            "api",
            {"method": method, "path": path, "status": status, "elapsed_ms": int((time.time() - t0) * 1000), "response": payload},
        )
        return payload

    # ---------- WS 聊天（复用 acceptance_memory_revival 模式） ----------
    def ws_chat(
        self,
        token: str,
        session_id: str,
        message: str,
        timeout_s: float = 120.0,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ticket_data = self.http("POST", "/api/v1/ws/ticket", token=token, body={})
        ticket = ticket_data.get("ticket") or (ticket_data.get("data") or {}).get("ticket") or ""
        if not ticket:
            raise StepFailure(f"ws/ticket 未返回 ticket: {json.dumps(ticket_data, ensure_ascii=False)[:200]}")
        ws_base = self.gateway.replace("http", "ws", 1)
        ws = websocket.create_connection(f"{ws_base}/ws/chat?ticket={ticket}", timeout=timeout_s)
        payload = {"type": "message", "message": message, "session_id": session_id}
        if extra:
            payload.update(extra)
        ws.send(json.dumps(payload, ensure_ascii=False))
        parts: list[str] = []
        meta: dict[str, Any] = {}
        frames = 0
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
            frames += 1
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
        text = "".join(parts).strip()
        self.evidence.log_api(
            "ws_chat",
            {
                "session_id": session_id,
                "message": message,
                "frames": frames,
                "elapsed_s": round(time.time() - t0, 1),
                "reply_chars": len(text),
            },
        )
        return {"text": text, "metadata": meta, "frames": frames}

    # ---------- step handlers ----------
    def do_api_register(
        self,
        username_prefix: str = "jh",
        password: str = "Journey#2026A",
        store_as: str = "default",
    ) -> tuple[bool, str, list[str]]:
        username = f"{username_prefix}_{uuid4().hex[:8]}"
        # .local/.test 等保留域会被后端 email-validator 拒绝；example.com 子域可过校验
        email = f"{username}@sparkle-journey.example.com"
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "nickname": username,
            "accepted_tos": True,
            "accepted_privacy": True,
            "tos_version": "v1",
            "privacy_version": "v1",
            "agreed_locale": "zh-CN",
        }
        data = self.http("POST", "/api/v1/auth/register", body=payload)
        token = data.get("access_token") or (data.get("token") or {}).get("access_token") or ""
        user = data.get("user") or {}
        if not token or not user.get("id"):
            raise StepFailure(f"register 响应缺 token/user: {json.dumps(data, ensure_ascii=False)[:300]}")
        bucket = self.state.setdefault("accounts", {})
        bucket[store_as] = {
            "username": username,
            "email": email,
            "password": password,
            "token": token,
            "user_id": str(user["id"]),
        }
        if store_as == "default" or "default" not in bucket:
            bucket.setdefault("default", bucket[store_as])
        return True, f"注册成功 user_id={user['id']} username={username}", []

    def do_api_onboarding(self, account: str = "default", goal: str = "两周内完成数据结构期中复习", **overrides) -> tuple[bool, str, list[str]]:
        acc = self._account(account)
        payload = {
            "learning_goal_type": "exam",
            "learning_goal": goal,
            "learning_style": "balanced",
            "study_time_minutes": 60,
            "knowledge_level": "beginner",
            "response_depth": 0.5,
            "curiosity_preference": 0.5,
        }
        payload.update(overrides)
        data = self.http("POST", "/api/v1/profile/onboarding", token=acc["token"], body=payload)
        acc["onboarding_response"] = data
        first_message = str(data.get("first_message") or data.get("message") or "")
        return True, f"onboarding 提交成功 response_keys={sorted(data)[:10]} first_message[:60]={first_message[:60]!r}", []

    def do_api_get(self, path: str, account: str = "default", assert_status_2xx: bool = True) -> tuple[bool, str, list[str]]:
        acc = self._account(account)
        data = self.http("GET", path, token=acc["token"])
        return True, f"GET {path} -> keys={sorted(data)[:12]}", []

    def do_ws_chat(
        self,
        message: str,
        account: str = "default",
        session_id: str = "",
        timeout_s: float = 120.0,
        store_reply_as: str = "",
        assert_contains_any: list[str] | None = None,
        assert_not_contains_any: list[str] | None = None,
        save_reply_to: str = "",
    ) -> tuple[bool, str, list[str]]:
        acc = self._account(account)
        sid = session_id or str(uuid4())
        result = self.ws_chat(acc["token"], sid, message, timeout_s=timeout_s)
        reply = result["text"]
        if store_reply_as:
            acc[store_reply_as] = reply
        artifacts: list[str] = []
        if save_reply_to:
            path = self.evidence.save_text(save_reply_to, f"Q: {message}\n\nA: {reply}\n")
            artifacts.append(str(path))
        if not reply:
            raise StepFailure(f"ws_chat 空回复（frames={result['frames']}）")
        low = reply.lower()
        if assert_contains_any and not any(k.lower() in low for k in assert_contains_any):
            raise StepFailure(
                f"回复不含任何期望关键词 {assert_contains_any}; reply[:200]={reply[:200]!r}"
            )
        if assert_not_contains_any and any(k.lower() in low for k in assert_not_contains_any):
            raise StepFailure(
                f"回复含禁止关键词 {assert_not_contains_any}; reply[:200]={reply[:200]!r}"
            )
        return True, f"回复 {len(reply)} 字 frames={result['frames']} reply[:120]={reply[:120]!r}", artifacts

    def do_wait_for(
        self,
        kind: str,
        sql: str,
        timeout: float = 150.0,
        poll_interval: float = 4.0,
        expect_nonzero: bool = True,
        label: str = "",
    ) -> tuple[bool, str, list[str]]:
        """轮询只读 SQL 直到结果非零（或超时）。sql 必须是 SELECT。"""
        if not sql.strip().lower().startswith("select"):
            raise StepFailure("wait_for 只允许 SELECT 语句（DB 只读纪律）")
        deadline = time.time() + timeout
        value = ""
        while time.time() < deadline:
            value = self.evidence.db_scalar(sql)
            if (value not in ("", "0")) or not expect_nonzero:
                return True, f"{label or kind}: 结果={value!r}", []
            time.sleep(poll_interval)
        raise StepFailure(f"等待 DB 结果超时({timeout:.0f}s): {label or kind} 最后值={value!r}")

    def do_assert_reply_reuses(
        self,
        reply_key: str,
        keywords: list[str],
        account: str = "default",
    ) -> tuple[bool, str, list[str]]:
        """跨步断言：后续回复复用了前文信息（跨会话记忆召回的轻量结构断言）。"""
        acc = self._account(account)
        reply = str(acc.get(reply_key) or "")
        hit = [k for k in keywords if k.lower() in reply.lower()]
        if not hit:
            raise StepFailure(
                f"回复未复用任何关键词 {keywords}; {reply_key}[:200]={reply[:200]!r}"
            )
        return True, f"复用关键词命中={hit}", []

    def do_sleep(self, seconds: float = 1.0) -> tuple[bool, str, list[str]]:
        time.sleep(float(seconds))
        return True, f"等待 {seconds}s", []

    # ---------- helpers ----------
    def _account(self, key: str) -> dict[str, Any]:
        acc = (self.state.get("accounts") or {}).get(key)
        if not acc:
            raise StepFailure(f"journey 上下文中没有账号 {key!r}（先执行 api_register）")
        return acc
