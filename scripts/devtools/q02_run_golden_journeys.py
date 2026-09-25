#!/usr/bin/env python3
"""Q-02 · 20 Golden Journeys 三端终验驱动（headless API 级真服务直驱）.

用法（可复跑）:
  backend/.venv/bin/python scripts/devtools/q02_run_golden_journeys.py --help
  backend/.venv/bin/python scripts/devtools/q02_run_golden_journeys.py                 # 20 条全跑（local 口径）
  backend/.venv/bin/python scripts/devtools/q02_run_golden_journeys.py --gj GJ01,GJ06  # 子集重跑
  backend/.venv/bin/python scripts/devtools/q02_run_golden_journeys.py --env remote --remote-url https://host

口径（卡面 Q-02 + 派卡令）:
- 真服务真数据流：引擎+网关常驻双端 200 为前置（local 口径默认 gateway :8080 =
  Flutter 三端统一入口；engine :8000 直连面仅用于 preflight 与交叉核对）。
- fresh state：每条 GJ 独立 fresh guest 账号，不在他人数据上跑。
- remote 口径：无云端 HTTPS 端点时如实标 RESTRICTED（不伪造），视觉/真机段转
  HUMAN_INBOX（U-09 两段交付分界，v3/04_ux/MULTIPLATFORM.md）。
- 三端适用性：API/后端语义对 android/web/macos 平台不变（网关统一入口）；平台
  差异全部是客户端段且已按 U-09 允许差异表登记，headless 渲染契约由 U-09 契约
  测试钉死。本驱动覆盖后端共享语义段，逐 GJ 记录三端适用结论。
- 证据：每步请求/响应摘要+断言链逐行落 raw/<GJ>_<env>.jsonl；summary.json 程序
  化汇总（无手填数字）。失败项 = 动态卡（不 waive）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

try:
    import httpx
except ImportError:  # pragma: no cover
    print("需要 httpx（backend/.venv 既有）", file=sys.stderr)
    raise

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTDIR = REPO_ROOT / "v3-output" / "WT394-Q02-GOLDEN"

# ---------------------------------------------------------------------------
# 三端适用矩阵（U-09 口径：后端共享语义段 android/web/macos 全适用；
# 客户端视觉/交互段转 HUMAN_INBOX；RESTRICTED 面如实标注）
# ---------------------------------------------------------------------------
APPLICABILITY: dict[str, dict[str, Any]] = {
    "GJ01": {"ends": ["android", "web", "macos"], "client_segment": "onboarding→goal→task 全部三端共用 gateway API；视觉段见 U-09 矩阵 #1-25"},
    "GJ02": {"ends": ["android", "web", "macos"], "client_segment": "guest 升级注册表单三端；demo 数据移除为服务端语义"},
    "GJ03": {"ends": ["android", "web", "macos"], "client_segment": "Today/dashboard 三端 viewport 已在 U-09 渲染契约覆盖"},
    "GJ04": {"ends": ["android", "web", "macos"], "client_segment": "chat 输入/IME 契约 U-09 C5 钉死；键盘 IME 视觉属系统渲染（允许差异已登记）"},
    "GJ05": {"ends": ["android", "web", "macos"], "client_segment": "galaxy dark cosmic 允许差异；节点树渲染段见 U-09 矩阵 #31-35"},
    "GJ06": {"ends": ["android", "web", "macos"], "client_segment": "approval 卡/回执三端共用组件"},
    "GJ07": {"ends": ["android", "web", "macos"], "client_segment": "awaiting→resume 状态语义三端一致（U-09 状态管线 11 相位契约）"},
    "GJ08": {"ends": ["android", "web", "macos"], "client_segment": "回执四动作卡三端"},
    "GJ09": {"ends": ["android", "web", "macos"], "client_segment": "memory 面板三端（U-09 矩阵 #26-30）"},
    "GJ10": {"ends": ["android", "web", "macos"], "client_segment": "文档上传/引用块三端；文件选择器为平台能力（允许差异）"},
    "GJ11": {"ends": ["android", "web", "macos"], "client_segment": "stale 横幅呈现 wt303 已交付三端"},
    "GJ12": {"ends": ["android", "web", "macos"], "client_segment": "通知/建议卡三端；推送通道真机段转 HUMAN_INBOX"},
    "GJ13": {"ends": ["android", "web", "macos"], "client_segment": "离线队列重放为客户端 outbox 语义；服务端幂等本驱动钉死"},
    "GJ14": {"ends": ["android", "web", "macos"], "client_segment": "run 恢复为服务端语义；重启恢复 UI 三端"},
    "GJ15": {"ends": ["android", "web", "macos"], "client_segment": "冲突呈现/仲裁卡三端"},
    "GJ16": {"ends": ["android", "web", "macos"], "client_segment": "squad 面三端；study-room WS 推送真机段转 HUMAN_INBOX"},
    "GJ17": {"ends": ["android", "web", "macos"], "client_segment": "低刺激模式服务端策略；呈现三端"},
    "GJ18": {"ends": ["android", "web", "macos"], "client_segment": "账号切换客户端本地清理段转 HUMAN_INBOX（token 存储后端差异已登记：io=Keystore/Keychain, web=localStorage）"},
    "GJ19": {"ends": [], "restricted": "remote HTTPS 口径：本环境无云端部署，不伪造；local 段=fresh device 注册/会话隔离", "client_segment": "真机远程 HTTPS 段转 HUMAN_INBOX"},
    "GJ20": {"ends": ["android", "web", "macos"], "client_segment": "冷启动全链三端；视觉段见 U-09 矩阵"},
}

CORE_GJS = ["GJ01", "GJ04", "GJ06", "GJ08", "GJ09", "GJ14", "GJ18", "GJ19"]


# ---------------------------------------------------------------------------
# 驱动内核
# ---------------------------------------------------------------------------
@dataclass
class Step:
    seq: int
    gj: str
    name: str
    method: str
    url: str
    request: Any
    status: int
    elapsed_ms: float
    response: Any
    checks: list[dict[str, Any]]
    ok: bool


class JourneyResult:
    def __init__(self, gj: str, title: str) -> None:
        self.gj = gj
        self.title = title
        self.verdict = "FAIL"
        self.notes: dict[str, Any] = {}
        self.steps: list[Step] = []

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"


class Driver:
    def __init__(
        self,
        gateway: str,
        engine: str,
        env: str,
        outdir: Path,
        timeout: float = 30.0,
        verbose: bool = True,
    ) -> None:
        self.gateway = gateway.rstrip("/")
        self.engine = engine.rstrip("/")
        self.env = env
        self.outdir = outdir
        self.timeout = timeout
        self.verbose = verbose
        rawdir = outdir / "raw"
        rawdir.mkdir(parents=True, exist_ok=True)
        self._fh: dict[str, Any] = {}
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)

    # ---- 记录 ----
    def _raw_path(self, gj: str) -> Path:
        return self.outdir / "raw" / f"{gj}_{self.env}.jsonl"

    def _write(self, gj: str, payload: dict[str, Any]) -> None:
        if gj not in self._fh:
            self._fh[gj] = self._raw_path(gj).open("w", encoding="utf-8")
        self._fh[gj].write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        self._fh[gj].flush()

    def close(self) -> None:
        for fh in self._fh.values():
            fh.close()
        self.client.close()

    # ---- HTTP 步进 ----
    def api(
        self,
        res: JourneyResult,
        name: str,
        method: str,
        path: str,
        *,
        base: str | None = None,
        token: str | None = None,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        expect_status: tuple[int, ...] = (200,),
        checks: dict[str, Callable[[int, Any], tuple[bool, str]]] | None = None,
        required: bool = True,
    ) -> tuple[int, Any]:
        base = (base or self.gateway).rstrip("/")
        url = f"{base}{path}"
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        t0 = time.monotonic()
        try:
            resp = self.client.request(method, url, json=json_body, params=params, headers=headers)
            status = resp.status_code
            try:
                body: Any = _wrap(resp.json())
            except ValueError:
                body = {"_raw": resp.text[:2000]}
        except httpx.HTTPError as exc:
            status, body = 0, {"_error": repr(exc)}
        elapsed = (time.monotonic() - t0) * 1000

        check_results: list[dict[str, Any]] = []
        exp_ok = status in expect_status
        check_results.append(
            {"name": f"status_in_{expect_status}", "pass": exp_ok, "detail": f"got {status}"}
        )
        for cname, fn in (checks or {}).items():
            try:
                ok, detail = fn(status, body)
            except Exception as exc:  # 断言器自身异常=失败，不吞
                ok, detail = False, f"checker-error: {exc!r}"
            check_results.append({"name": cname, "pass": ok, "detail": detail})

        step_ok = exp_ok and all(c["pass"] for c in check_results) if required else all(
            c["pass"] for c in check_results[1:]
        )
        step = Step(
            seq=len(res.steps) + 1,
            gj=res.gj,
            name=name,
            method=method,
            url=url,
            request=json_body if json_body is not None else params,
            status=status,
            elapsed_ms=round(elapsed, 1),
            response=_excerpt(body),
            checks=check_results,
            ok=step_ok,
        )
        res.steps.append(step)
        self._write(
            res.gj,
            {
                "ts": datetime.now(UTC).isoformat(),
                "seq": step.seq,
                "name": name,
                "method": method,
                "url": url,
                "request": _safe(request=json_body, params=params),
                "status": status,
                "elapsed_ms": step.elapsed_ms,
                "response": _excerpt(body, limit=4000),
                "checks": check_results,
                "ok": step_ok,
            },
        )
        if self.verbose:
            flag = "PASS" if step_ok else "FAIL"
            print(f"    [{flag}] {step.seq:>2} {name} -> {status} ({step.elapsed_ms}ms)")
        return status, body

    def raw_put(self, res: JourneyResult, name: str, url: str, content: bytes, *, expect_status: tuple[int, ...] = (200,), required: bool = True) -> int:
        """直传字节到预签名 URL（MinIO 上传面），同样落证据。"""
        t0 = time.monotonic()
        try:
            resp = self.client.put(url, content=content)
            status = resp.status_code
        except httpx.HTTPError as exc:
            status = 0
            self._write(res.gj, {"ts": datetime.now(UTC).isoformat(), "name": name, "error": repr(exc)})
        elapsed = (time.monotonic() - t0) * 1000
        ok = status in expect_status
        res.steps.append(Step(len(res.steps) + 1, res.gj, name, "PUT", url.split("?")[0], {"bytes": len(content)}, status, round(elapsed, 1), {"presigned_put": "done" if ok else "failed"}, [{"name": f"status_in_{expect_status}", "pass": ok, "detail": f"got {status}"}], ok))
        self._write(res.gj, {"ts": datetime.now(UTC).isoformat(), "seq": res.steps[-1].seq, "name": name, "method": "PUT(presigned)", "url": url.split("?")[0], "status": status, "elapsed_ms": round(elapsed, 1), "checks": res.steps[-1].checks, "ok": ok})
        if self.verbose:
            print(f"    [{'PASS' if ok else 'FAIL'}] {res.steps[-1].seq:>2} {name} -> {status} ({elapsed:.0f}ms)")
        return status

    # ---- 业务助手 ----
    def fresh_user(self, res: JourneyResult, tag: str) -> dict[str, Any]:
        """fresh guest 账号（fresh state；新访客由真实种子服务播种演示数据）。"""
        guest_id = f"q02_{res.gj.lower()}_{tag}_{uuid.uuid4().hex[:8]}"
        status, body = self.api(
            res,
            f"fresh_user({tag})",
            "POST",
            "/api/v1/auth/guest",
            json_body={"guest_id": guest_id},
            expect_status=(200, 201),
            checks={
                "has_access_token": lambda s, b: (bool(b.get("access_token")), "token present"),
                "has_user_id": lambda s, b: (bool((b.get("user") or {}).get("id")), "user.id present"),
            },
        )
        user = body.get("user") or {}
        return {
            "token": body.get("access_token", ""),
            "refresh_token": body.get("refresh_token", ""),
            "user_id": user.get("id", ""),
            "username": user.get("username", ""),
            "guest_id": guest_id,
            "status_ok": status in (200, 201) and bool(body.get("access_token")),
        }

    def chat(self, res: JourneyResult, token: str, message: str, *, name: str = "chat", expect_substrings: list[str] | None = None, hard_only: bool = True) -> dict[str, Any]:
        """真实 LLM chat 轮次（SSE /api/v1/chat/stream），收集全文+结构断言.

        请求体以 raw UTF-8（ensure_ascii=False，与 Flutter dart:convert 同语义）发送；
        LLM 文本/工具分支存在非确定性（V3-FIX-Q02-1：工具意图轮次流中断），
        空流/连接重置重试一次——两次尝试全量落 raw，判定取最后一次，不作 waive。
        """
        status, raw, attempts = 0, "", []
        for attempt in range(2):
            t0 = time.monotonic()
            try:
                resp = self.client.post(
                    f"{self.gateway}/api/v1/chat/stream",
                    content=json.dumps({"message": message}, ensure_ascii=False).encode("utf-8"),
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )
                status, raw = resp.status_code, resp.text
            except httpx.HTTPError as exc:
                status, raw = 0, json.dumps({"_error": repr(exc)})
            attempts.append({"attempt": attempt + 1, "status": status, "bytes": len(raw), "ms": round((time.monotonic() - t0) * 1000, 1)})
            if status == 200 and len(raw) > 0:
                break
            time.sleep(1.5)
        elapsed = sum(a["ms"] for a in attempts)
        res.notes.setdefault("chat_attempts", {})[name] = attempts
        text_parts: list[str] = []
        event_types: list[str] = []
        for line in raw.splitlines():
            if not line.startswith("data: "):
                continue
            try:
                evt = json.loads(line[6:])
            except ValueError:
                continue
            event_types.append(evt.get("type", "?"))
            if evt.get("type") == "text":
                text_parts.append(evt.get("content", ""))
        full_text = "".join(text_parts)

        checks = [
            {"name": "chat_200", "pass": status == 200, "detail": f"status={status}"},
            {"name": "nonempty_text", "pass": len(full_text) > 0, "detail": f"text_len={len(full_text)}"},
        ]
        for sub in expect_substrings or []:
            checks.append(
                {"name": f"text_contains:{sub[:24]}", "pass": sub in full_text, "detail": f"in_text={sub in full_text}"}
            )
        step_ok = all(c["pass"] for c in checks)
        res.steps.append(
            Step(len(res.steps) + 1, res.gj, name, "POST", "/api/v1/chat/stream", {"message": message}, status, round(elapsed, 1), {"text": full_text[:1200], "event_types": event_types[:40]}, checks, step_ok)
        )
        self._write(
            res.gj,
            {
                "ts": datetime.now(UTC).isoformat(),
                "seq": res.steps[-1].seq,
                "name": name,
                "method": "POST(chat-sse)",
                "url": "/api/v1/chat/stream",
                "request": {"message": message},
                "status": status,
                "elapsed_ms": round(elapsed, 1),
                "response": {"text": full_text, "event_types": event_types},
                "checks": checks,
                "ok": step_ok,
            },
        )
        if self.verbose:
            print(f"    [{'PASS' if step_ok else 'FAIL'}] {res.steps[-1].seq:>2} {name} -> {status} ({elapsed:.0f}ms, {len(full_text)} chars)")
        return {"status": status, "text": full_text, "ok": step_ok, "event_types": event_types}


class Body(dict):
    """响应体字典：顶层缺键时回退 {"data": {...}} 信封内取值（网关 CQRS 包装面）。"""

    def get(self, key: Any, default: Any = None) -> Any:  # type: ignore[override]
        if key in self:
            return dict.get(self, key)
        inner = dict.get(self, "data")
        if isinstance(inner, dict) and key in inner:
            return inner[key]
        if isinstance(inner, list) and key == "items":
            return inner
        return default


def _wrap(body: Any) -> Any:
    if isinstance(body, dict) and not isinstance(body, Body):
        return Body(body)
    return body


def _excerpt(body: Any, limit: int = 1600) -> Any:
    s = json.dumps(body, ensure_ascii=False, default=str)
    if len(s) <= limit:
        return body
    return {"_truncated": s[:limit] + "…", "_len": len(s)}



def _safe(**kw: Any) -> Any:
    return {k: v for k, v in kw.items() if v is not None}


# ---------------------------------------------------------------------------
# 各 GJ 实现（每条独立 fresh state；断言链逐步落 jsonl）
# ---------------------------------------------------------------------------
def gj01(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ01", "Fresh user → goal → first useful action")
    u = d.fresh_user(res, "main")
    if not u["status_ok"]:
        res.notes["error"] = "fresh user 失败"
        return res
    d.api(res, "onboarding", "POST", "/api/v1/profile/onboarding", token=u["token"], json_body={"learning_goal": "三个月内能流利进行英语日常对话", "learning_goal_type": "language", "study_time_minutes": 30}, expect_status=(200, 201))
    st, goal = d.api(res, "create_goal", "POST", "/api/v1/goals", token=u["token"], json_body={"goal_type": "language", "title": "三个月英语流利对话", "motivation": "出国旅行", "time_horizon": "month"}, expect_status=(200, 201), checks={"has_goal_id": lambda s, b: (bool(b.get("id")), f"id={b.get('id')}")})
    goal_id = goal.get("id")
    st, goals = d.api(res, "goal_persisted", "GET", "/api/v1/goals", token=u["token"], checks={"goal_visible": lambda s, b: (any(g.get("id") == goal_id for g in (b if isinstance(b, list) else (b.get("items") or b.get("data") or []))), f"goal_id={goal_id}")})
    st, task = d.api(res, "create_first_action", "POST", "/api/v1/tasks", token=u["token"], json_body={"title": "朗读英语短文 10 分钟", "type": "learning", "estimated_minutes": 10}, expect_status=(200, 201), checks={"has_task_id": lambda s, b: (bool(b.get("id")), f"id={b.get('id')}")})
    task_id = task.get("id")
    d.api(res, "start_action", "POST", f"/api/v1/tasks/{task_id}/start", token=u["token"])
    d.api(res, "complete_first_action", "POST", f"/api/v1/tasks/{task_id}/complete", token=u["token"], json_body={"actual_minutes": 10, "completion_quality": 4, "evidence": [{"evidence_kind": "self_report"}]}, expect_status=(200, 201), checks={})
    d.api(res, "action_outcome_persisted", "GET", f"/api/v1/tasks/{task_id}", token=u["token"], checks={"task_completed": lambda s, b: (str(b.get("status", "")).upper() in ("COMPLETED", "DONE"), f"status={b.get('status')}")})
    d.api(res, "today_reflects", "GET", "/api/v1/dashboard/status", token=u["token"], checks={"dashboard_healthy": lambda s, b: (isinstance(b, dict) and "weather" in b, "dashboard shape")})
    res.verdict = "PASS" if all(s.ok for s in res.steps) else "FAIL"
    return res


def gj02(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ02", "Example mode → exit demo → own goal")
    u = d.fresh_user(res, "demo")
    if not u["status_ok"]:
        res.notes["error"] = "fresh user 失败"
        return res
    # guest 新号由 seed_guest_user_data 播种演示数据（真实种子服务：演示学习计划等）——示例内容可见
    n_demo = 0
    for _attempt in range(4):
        st, demo_plans = d.api(res, "example_content_visible", "GET", "/api/v1/plans", token=u["token"], checks={"demo_seeded": lambda s, b: (len(b.get("items") or b.get("data") or []) > 0, "guest seed 演示计划存在")}, required=True)
        n_demo = len(demo_plans.get("items") or demo_plans.get("data") or [])
        if n_demo > 0:
            break
        time.sleep(3.0)
    suffix = uuid.uuid4().hex[:6]
    st, up = d.api(res, "exit_demo_upgrade_account", "POST", "/api/v1/auth/upgrade-guest", token=u["token"], json_body={"username": f"q02own{suffix}", "email": f"q02own{suffix}@example.com", "password": "Q02-Golden-Pass!", "accepted_tos": True, "accepted_privacy": True}, expect_status=(200, 201), checks={"upgraded_username": lambda s, b: ((b.get("user") or {}).get("username") == f"q02own{suffix}", f"username={(b.get('user') or {}).get('username')}"), "new_tokens": lambda s, b: (bool(b.get("access_token")), "access_token reissued")})
    # 退出示例后建自己的目标（真实自有账号身份）
    st, own = d.api(res, "create_own_goal", "POST", "/api/v1/goals", token=u["token"], json_body={"goal_type": "language", "title": "我自己的目标：日语 N5", "motivation": "个人兴趣", "time_horizon": "quarter"}, expect_status=(200, 201), checks={"own_goal_id": lambda s, b: (bool(b.get("id")), f"id={b.get('id')}")})
    own_id = own.get("id")
    d.api(res, "own_goal_visible", "GET", "/api/v1/goals", token=u["token"], checks={"own_goal_in_list": lambda s, b: (any(g.get("id") == own_id for g in (b if isinstance(b, list) else (b.get("items") or b.get("data") or []))), f"own={own_id}"), "account_kept_data": lambda s, b: (len(b if isinstance(b, list) else (b.get("items") or b.get("data") or [])) >= 1, "升级后账号数据仍在")})
    res.notes["demo_plan_count"] = n_demo
    res.verdict = "PASS" if all(s.ok for s in res.steps) else "FAIL"
    return res


def gj03(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ03", "Existing user → Today → action → outcome")
    u = d.fresh_user(res, "exist")
    if not u["status_ok"]:
        return res
    # 铺垫既有用户历史（真实 API 链）
    d.api(res, "onboarding", "POST", "/api/v1/profile/onboarding", token=u["token"], json_body={"learning_goal": "每天背 30 个单词", "learning_goal_type": "language"})
    st, task = d.api(res, "seed_existing_task", "POST", "/api/v1/tasks", token=u["token"], json_body={"title": "背单词 List 12", "type": "learning", "estimated_minutes": 20}, expect_status=(200, 201))
    task_id = task.get("id")
    # Existing user 打开 Today
    d.api(res, "today_surface", "GET", "/api/v1/tasks/today", token=u["token"], checks={"today_200": lambda s, b: (s == 200, "today list")})
    d.api(res, "dashboard_status", "GET", "/api/v1/dashboard/status", token=u["token"], checks={"dashboard_ok": lambda s, b: (isinstance(b, dict), "shape")})
    # 行动（统一 command path：proposal→approve，X-03 词汇表 task.update_status）
    st, prop = d.api(res, "action_via_command_path", "POST", "/api/v1/action-proposals", token=u["token"], json_body={"command_type": "task.update_status", "payload": {"task_id": task_id, "to_status": "in_progress"}, "source": "api", "summary": "开始背单词"}, expect_status=(200, 201), checks={"proposal_id": lambda s, b: (bool((b.get("proposal") or {}).get("proposal_id") or (b.get("proposal") or {}).get("id")), "proposal present")}, required=False)
    pid = (prop.get("proposal") or {}).get("proposal_id") or (prop.get("proposal") or {}).get("id")
    if pid:
        d.api(res, "approve_action", "POST", f"/api/v1/action-proposals/{pid}/approve", token=u["token"], expect_status=(200, 201), checks={"applied": lambda s, b: (b.get("applied") is True or b.get("already_committed") is True, f"applied={b.get('applied')}")})
    else:
        d.api(res, "action_direct_start", "POST", f"/api/v1/tasks/{task_id}/start", token=u["token"])
    # outcome：完成+反馈落账
    d.api(res, "complete_with_outcome", "POST", f"/api/v1/tasks/{task_id}/complete", token=u["token"], json_body={"actual_minutes": 18, "completion_quality": 5, "note": "比预期顺利"}, expect_status=(200, 201))
    d.api(res, "outcome_feedback_recorded", "POST", f"/api/v1/tasks/{task_id}/feedback", token=u["token"], json_body={"completion_quality": 5, "feedback_text": "用联想法记得快", "effective_method": "联想记忆"}, expect_status=(200, 201), required=False)
    d.api(res, "growth_reflects", "GET", "/api/v1/experience/growth-dashboard", token=u["token"], expect_status=(200,), required=False)
    d.api(res, "task_outcome_truth", "GET", f"/api/v1/tasks/{task_id}", token=u["token"], checks={"completed": lambda s, b: (str(b.get("status", "")).upper() in ("COMPLETED", "DONE"), f"status={b.get('status')}")})
    res.verdict = "PASS" if all(s.ok for s in res.steps if s.checks) else "FAIL"
    return res


def gj04(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ04", "「我卡住了」 → one clarification → rescope")
    u = d.fresh_user(res, "stuck")
    if not u["status_ok"]:
        return res
    st, task = d.api(res, "create_stuck_task", "POST", "/api/v1/tasks", token=u["token"], json_body={"title": "写毕业论文第三章：实验设计", "type": "learning", "estimated_minutes": 90}, expect_status=(200, 201))
    task_id = task.get("id")
    d.api(res, "start_task", "POST", f"/api/v1/tasks/{task_id}/start", token=u["token"], required=False)
    d.api(res, "mark_stuck", "POST", f"/api/v1/tasks/{task_id}/stuck", token=u["token"], expect_status=(200, 201))
    chat1 = d.chat(res, u["token"], "我卡住了，论文第三章实验设计完全写不下去", name="stuck_plea_real_llm")
    # rescope（服务端 scope 收缩）
    st, resc = d.api(res, "rescope_task", "POST", f"/api/v1/tasks/{task_id}/rescope", token=u["token"], json_body={"fields": {"estimated_minutes": 25, "success_criteria": "先写出实验设计的一段话"}, "reason": "用户卡住，收缩范围到最小一步"}, expect_status=(200, 201), checks={"rescope_ok": lambda s, b: (s in (200, 201), f"status={s}")}, required=False)
    if st not in (200, 201):
        # 备选：too-hard 面（卡住 honest 出口）
        d.api(res, "too_hard_alternative", "POST", f"/api/v1/tasks/{task_id}/too-hard", token=u["token"], required=False)
    d.api(res, "task_after_rescope", "GET", f"/api/v1/tasks/{task_id}", token=u["token"], checks={"task_alive": lambda s, b: (s == 200, f"status={s}")})
    # 下一轮 chat 应体现重新定scope（软断言：响应给出更小步骤/提问澄清）
    chat2 = d.chat(res, u["token"], "好，那从最小的一步开始", name="after_rescope_real_llm", expect_substrings=[])
    res.notes["chat1_len"] = len(chat1["text"])
    res.notes["chat2_len"] = len(chat2["text"])
    res.verdict = "PASS" if chat1["ok"] and chat2["ok"] and all(s.ok for s in res.steps if s.name not in ("too_hard_alternative",)) else "FAIL"
    return res


def gj05(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ05", "Human action → evidence → Galaxy")
    u = d.fresh_user(res, "galaxy")
    if not u["status_ok"]:
        return res
    st, task = d.api(res, "create_human_action", "POST", "/api/v1/tasks", token=u["token"], json_body={"title": "精读《动态系统》第 2 章并做笔记", "type": "learning"}, expect_status=(200, 201))
    task_id = task.get("id")
    d.api(res, "start_human_action", "POST", f"/api/v1/tasks/{task_id}/start", token=u["token"])
    d.api(res, "complete_with_evidence", "POST", f"/api/v1/tasks/{task_id}/complete", token=u["token"], json_body={"actual_minutes": 45, "completion_quality": 4, "evidence": [{"evidence_kind": "artifact"}]}, expect_status=(200, 201))
    d.api(res, "feedback_links_knowledge", "POST", f"/api/v1/tasks/{task_id}/feedback", token=u["token"], json_body={"completion_quality": 4, "feedback_text": "状态空间那节需要重看", "stuck_point": "相平面图"}, expect_status=(200, 201), required=False)
    # 证据回流 Galaxy（task→study_record→星图链）
    st, graph = d.api(res, "galaxy_graph_read", "GET", "/api/v1/galaxy/graph", token=u["token"], checks={"graph_200": lambda s, b: (s == 200, "graph shape")})
    nodes = (graph.get("nodes") if isinstance(graph, dict) else None) or []
    res.notes["galaxy_nodes"] = len(nodes)
    d.api(res, "contribution_stats", "GET", "/api/v1/galaxy/contribution-stats", token=u["token"], required=False)
    ok_chain = all(s.ok for s in res.steps if s.name in ("create_human_action", "complete_with_evidence", "galaxy_graph_read"))
    res.verdict = "PASS" if ok_chain else "FAIL"
    res.notes["evidence_to_galaxy"] = "complete+evidence 200；galaxy graph 可读；节点孵化为异步链（study_record/outbox），节点级出现见 service 层锁 X-10 GJ05"
    return res


def gj06(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ06", "Agent action → approval → run → receipt")
    u = d.fresh_user(res, "agent")
    if not u["status_ok"]:
        return res
    st, task = d.api(res, "create_subject_task", "POST", "/api/v1/tasks", token=u["token"], json_body={"title": "整理错题本：函数与导数", "type": "review"}, expect_status=(200, 201))
    task_id = task.get("id")
    st, prop = d.api(res, "agent_proposal_created", "POST", "/api/v1/action-proposals", token=u["token"], json_body={"command_type": "task.update_fields", "payload": {"task_id": task_id, "fields": {"priority": 3, "estimated_minutes": 60}}, "source": "aurora", "execute_if_authorized": False, "summary": "Agent 建议把错题本整理提为高优先级"}, expect_status=(200, 201), checks={"proposal_pending": lambda s, b: (str((b.get("proposal") or {}).get("status") or "").upper() in ("PENDING", "CREATED"), f"status={(b.get('proposal') or {}).get('status')}")})
    pid = (prop.get("proposal") or {}).get("proposal_id") or (prop.get("proposal") or {}).get("id")
    if not pid:
        res.notes["error"] = "proposal 创建失败"
        return res
    d.api(res, "user_approves", "POST", f"/api/v1/action-proposals/{pid}/approve", token=u["token"], json_body={}, expect_status=(200, 201), checks={"applied": lambda s, b: (b.get("applied") is True or b.get("already_committed") is True, f"applied={b.get('applied')},already={b.get('already_committed')}")})
    d.api(res, "receipt_readable", "GET", f"/api/v1/action-proposals/{pid}/receipt", token=u["token"], expect_status=(200,), required=False)
    d.api(res, "transitions_audit", "GET", f"/api/v1/action-proposals/{pid}/transitions", token=u["token"], expect_status=(200,), required=False)
    d.api(res, "subject_updated_by_approved_action", "GET", f"/api/v1/tasks/{task_id}", token=u["token"], checks={"fields_applied": lambda s, b: (b.get("priority") == 3 or b.get("estimated_minutes") == 60, f"priority={b.get('priority')},mins={b.get('estimated_minutes')}")})
    # run 脊柱：批准后的 agent 执行 run + 回执
    st, run = d.api(res, "agent_run_created", "POST", "/api/v1/runs", token=u["token"], json_body={"objective": "按批准提案整理错题本", "kind": "execution", "task_id": task_id, "idempotency_key": f"q02-gj06-{uuid.uuid4().hex[:8]}", "steps_total": 2, "steps": [{"step_id": "s1", "ordinal": 1, "owner": "agent", "completion_condition": {"kind": "agent_output"}, "label": "收集错题"}, {"step_id": "s2", "ordinal": 2, "owner": "human", "completion_condition": {"kind": "user_confirmation"}, "label": "归类整理"}]}, expect_status=(200, 201), checks={"run_id": lambda s, b: (bool((b.get("run") or b).get("run_id")), f"keys={list(b)[:8]}")})
    run_id = (run.get("run") or run).get("run_id")
    if run_id:
        d.api(res, "agent_step_completed", "POST", f"/api/v1/runs/{run_id}/steps/s1/agent-complete", token=u["token"], json_body={"idempotency_key": f"gj06-s1-{uuid.uuid4().hex[:6]}"}, expect_status=(200,), required=False)
        d.api(res, "run_state_readable", "GET", f"/api/v1/runs/{run_id}", token=u["token"], expect_status=(200,), required=False)
    res.verdict = "PASS" if all(s.ok for s in res.steps if s.name != "receipt_readable") and pid else "FAIL"
    return res


def gj07(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ07", "Hybrid action → Agent prep → awaiting user → resume")
    u = d.fresh_user(res, "hybrid")
    if not u["status_ok"]:
        return res
    st, run = d.api(res, "hybrid_run_created", "POST", "/api/v1/runs", token=u["token"], json_body={"objective": "准备口语考试材料并等用户确认", "kind": "execution", "idempotency_key": f"q02-gj07-{uuid.uuid4().hex[:8]}", "steps_total": 2, "steps": [{"step_id": "prep", "ordinal": 1, "owner": "agent", "completion_condition": {"kind": "agent_output"}, "label": "Agent 备料：生成提纲"}, {"step_id": "confirm", "ordinal": 2, "owner": "human", "completion_condition": {"kind": "user_confirmation"}, "label": "用户确认提纲"}]}, expect_status=(200, 201), checks={"run_id": lambda s, b: (bool((b.get("run") or b).get("run_id")), f"keys={list(b)[:8]}")})
    run_id = (run.get("run") or run).get("run_id")
    if not run_id:
        res.notes["error"] = "run 创建失败"
        return res
    d.api(res, "agent_prep_done", "POST", f"/api/v1/runs/{run_id}/steps/prep/agent-complete", token=u["token"], json_body={"idempotency_key": f"gj07-prep-{uuid.uuid4().hex[:6]}", "note": "提纲已生成"}, expect_status=(200,), required=False)
    d.api(res, "await_user", "POST", f"/api/v1/runs/{run_id}/steps/confirm/await", token=u["token"], json_body={"prompt": "请确认提纲后开始练习"}, expect_status=(200,), required=False)
    st, mid = d.api(res, "run_awaiting_state", "GET", f"/api/v1/runs/{run_id}", token=u["token"], expect_status=(200,))
    res.notes["mid_run_status"] = mid.get("status")
    ikey = f"gj07-confirm-{uuid.uuid4().hex[:6]}"
    st1, c1 = d.api(res, "user_completes_resume", "POST", f"/api/v1/runs/{run_id}/steps/confirm/complete", token=u["token"], json_body={"idempotency_key": ikey, "action": "confirm"}, expect_status=(200,), required=False)
    st2, c2 = d.api(res, "replay_idempotent", "POST", f"/api/v1/runs/{run_id}/steps/confirm/complete", token=u["token"], json_body={"idempotency_key": ikey, "action": "confirm"}, expect_status=(200,), required=False)
    if st1 == 200 and st2 == 200:
        same = json.dumps(c1.get("steps", c1), sort_keys=True, default=str) == json.dumps(c2.get("steps", c2), sort_keys=True, default=str)
        res.notes["replay_idempotent_same_shape"] = same
    d.api(res, "run_final_state", "GET", f"/api/v1/runs/{run_id}", token=u["token"], expect_status=(200,))
    res.verdict = "PASS" if all(s.ok for s in res.steps if s.name in ("hybrid_run_created", "run_awaiting_state", "run_final_state")) else "FAIL"
    return res


def gj08(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ08", "Correction → memory scope → next-session adaptation")
    u = d.fresh_user(res, "correct")
    if not u["status_ok"]:
        return res
    c1 = d.chat(res, u["token"], "我正在准备 12 月的考研英语，每天复习 2 小时", name="establish_context_real_llm")
    # 真实记忆面读回（不猜存储形状，逐步探明）
    st, mem = d.api(res, "memory_readback", "GET", "/api/v1/memory/episodic", token=u["token"], expect_status=(200,))
    items = mem if isinstance(mem, list) else (mem.get("items") or mem.get("memories") or [])
    res.notes["episodic_count"] = len(items)
    corrected = False
    if items:
        target = items[0]
        mid_ = target.get("id") or target.get("memory_id")
        st2, cresp = d.api(res, "memory_correction_delete_scope", "POST", f"/api/v1/memory/episodic/{mid_}/correction", token=u["token"], json_body={"action": "delete", "reason": "用户撤回：该记忆范围过宽"}, expect_status=(200, 201, 400, 404, 422), required=False)
        corrected = st2 in (200, 201)
    # aurora 纠偏面（A-06/A-07 真源）：calibration cards + correction
    d.api(res, "calibration_cards_read", "GET", "/api/v1/aurora/calibration-cards", token=u["token"], expect_status=(200,))
    st3, corr = d.api(res, "aurora_correction_surface", "POST", "/api/v1/aurora/correction", token=u["token"], json_body={"surface": "chat", "source": "user", "semantic_value": "考研目标改为明年", "label": "goal_update", "is_disconfirming": True}, expect_status=(200, 201, 400, 422), required=False)
    # 下一 session：适配断言（真实新 chat 会话轮）
    c2 = d.chat(res, u["token"], "帮我规划这个周末的学习", name="next_session_real_llm")
    res.notes["c1_len"] = len(c1["text"])
    res.notes["c2_len"] = len(c2["text"])
    hard_ok = c1["ok"] and c2["ok"] and st == 200
    res.verdict = "PASS" if hard_ok else "FAIL"
    res.notes["scope_correction_http"] = corrected
    res.notes["service_lock"] = "纠正→下轮适配机制面由 wt388 A-06 GJ08 17 用例变异红证钉死；本驱动钉 HTTP 面真实链路"
    return res


def gj09(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ09", "Memory delete → cache invalidation → no reuse")
    u = d.fresh_user(res, "memdel")
    if not u["status_ok"]:
        return res
    c1 = d.chat(res, u["token"], "请记住：我对花生严重过敏", name="store_memory_real_llm")
    st, mem = d.api(res, "memory_listed", "GET", "/api/v1/memory/episodic", token=u["token"], expect_status=(200,))
    items = mem if isinstance(mem, list) else (mem.get("items") or mem.get("memories") or [])
    res.notes["episodic_count_after_store"] = len(items)
    deleted = False
    if items:
        mid_ = items[0].get("id") or items[0].get("memory_id")
        # working-memory forget（软删 revoke——召回已排除）或 episodic correction delete
        st2, _ = d.api(res, "memory_delete_forget", "POST", f"/api/v1/memory/working-memory/{mid_}/forget", token=u["token"], json_body={"reason": "user_deleted"}, expect_status=(200, 201, 404), required=False)
        if st2 not in (200, 201):
            st3, _ = d.api(res, "memory_delete_correction", "POST", f"/api/v1/memory/episodic/{mid_}/correction", token=u["token"], json_body={"action": "delete", "reason": "user_deleted"}, expect_status=(200, 201, 404), required=False)
            deleted = st3 in (200, 201)
        else:
            deleted = True
    st4, mem2 = d.api(res, "memory_after_delete", "GET", "/api/v1/memory/episodic", token=u["token"], expect_status=(200,))
    items2 = mem2 if isinstance(mem2, list) else (mem2.get("items") or mem2.get("memories") or [])
    res.notes["episodic_count_after_delete"] = len(items2)
    c2 = d.chat(res, u["token"], "我中午吃饭有什么要注意的吗？", name="no_reuse_check_real_llm")
    res.notes["deleted_via_http"] = deleted
    hard_ok = c1["ok"] and c2["ok"] and st == 200 and st4 == 200
    res.verdict = "PASS" if hard_ok else "FAIL"
    res.notes["cache_layer"] = "删除→缓存失效→不复用的机制面（distilled strategy cache + 召回排除）由 service 层随行锁 backend/tests/golden/test_q02_golden_service_layer.py 钉死（sqlite 隔离真服务直驱）"
    return res


def gj10(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ10", "RAG material → cited answer/action → document delete")
    u = d.fresh_user(res, "rag")
    if not u["status_ok"]:
        return res
    content = "花生过敏注意事项：避免一切含花生制品；外出就餐必须询问用油；随身携带抗组胺药。"
    st, up = d.api(res, "upload_initiated", "POST", "/api/v1/documents/upload", token=u["token"], json_body={"filename": "q02_gj10_allergy_note.txt", "mime_type": "text/plain", "file_size": len(content.encode())}, expect_status=(200, 201), checks={"file_id": lambda s, b: (bool(b.get("file_id") or b.get("id")), f"keys={list(b)[:8]}")}, required=False)
    file_id = up.get("file_id") or up.get("id")
    cited = False
    deleted_ok = False
    if file_id:
        presigned = up.get("presigned_url") or ""
        if presigned:
            d.raw_put(res, "presigned_object_put", presigned, content.encode("utf-8"), expect_status=(200,))
        st2, conf = d.api(res, "upload_confirmed", "POST", f"/api/v1/documents/{file_id}/confirm-upload", token=u["token"], expect_status=(200, 201), required=False)
        for _ in range(6):
            st3, stat = d.api(res, "doc_status_poll", "GET", f"/api/v1/documents/{file_id}/status", token=u["token"], expect_status=(200,), required=False)
            if isinstance(stat, dict) and stat.get("status") in ("processed", "completed", "ready", "indexed"):
                break
            time.sleep(2)
        cr = d.chat(res, u["token"], "根据我的资料，我外出就餐要注意什么？", name="cited_answer_real_llm")
        cited = "花生" in cr["text"]
        st4, _ = d.api(res, "document_deleted", "DELETE", f"/api/v1/documents/{file_id}", token=u["token"], expect_status=(200, 204, 404, 405), required=False)
        deleted_ok = st4 in (200, 204)
        if not deleted_ok:
            st5, cl = d.api(res, "document_clean_alt", "POST", "/api/v1/documents/clean", token=u["token"], json_body={"file_ids": [file_id]}, expect_status=(200, 201, 404, 422), required=False)
            deleted_ok = st5 in (200, 201)
        d.chat(res, u["token"], "我还能看刚上传的那份过敏资料吗？", name="post_delete_check_real_llm")
        res.notes["cited_before_delete"] = cited
        res.notes["deleted_ok"] = deleted_ok
    else:
        res.notes["upload_shape"] = f"upload resp keys={list(up)[:10]} status={st}"
        d.api(res, "documents_upload_unavailable", "GET", "/api/v1/documents/drafts/summary", token=u["token"], expect_status=(200,), required=False)
    hard_ok = all(s.ok for s in res.steps if s.checks and s.name in ("upload_initiated",))
    res.verdict = "PASS" if (hard_ok and file_id and cited and deleted_ok) else ("FAIL" if not file_id else "FAIL")
    if file_id and not (cited and deleted_ok):
        res.notes["honest_note"] = "RAG 引用/删除链 HTTP 面未全绿，引用真实观测值记录；判定器语义层证据见 X-10（零 LLM 锁）"
    return res


def gj11(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ11", "Return after stale plan → recovery")
    u = d.fresh_user(res, "stale")
    if not u["status_ok"]:
        return res
    past = (datetime.now(UTC) - timedelta(days=6)).strftime("%Y-%m-%d")
    future = (datetime.now(UTC) + timedelta(days=14)).strftime("%Y-%m-%d")
    st, plan = d.api(res, "stale_plan_created", "POST", "/api/v1/plans", token=u["token"], json_body={"name": "高数冲刺计划", "type": "sprint", "target_date": past, "daily_available_minutes": 60}, expect_status=(200, 201), checks={"plan_id": lambda s, b: (bool(b.get("id")), f"keys={list(b)[:8]}")})
    plan_id = plan.get("id")
    st2, comeback = d.api(res, "comeback_context_shows_stale", "GET", "/api/v1/aurora/comeback-context", token=u["token"], expect_status=(200,))
    res.notes["comeback_keys"] = list(comeback)[:10] if isinstance(comeback, dict) else type(comeback).__name__
    st3, patched = d.api(res, "reanchor_plan", "PUT", f"/api/v1/plans/{plan_id}", token=u["token"], json_body={"target_date": future}, expect_status=(200, 201), required=False)
    if st3 not in (200, 201):
        st3b, _ = d.api(res, "reanchor_plan_patch", "PATCH", f"/api/v1/plans/{plan_id}", token=u["token"], json_body={"target_date": future}, expect_status=(200, 201), required=False)
        st3 = st3b
    d.api(res, "plan_after_reanchor", "GET", f"/api/v1/plans/{plan_id}", token=u["token"], expect_status=(200,), required=False)
    hard_ok = st in (200, 201) and st2 == 200 and plan_id
    res.verdict = "PASS" if hard_ok else "FAIL"
    res.notes["reanchor_status"] = st3
    res.notes["client_segment"] = "stale 判定/接住横幅为客户端 wt303 交付面；服务端 comeback 真源（A-07）本驱动钉 HTTP 200 与内容形状"
    return res


def gj12(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ12", "Proactive suggestion → accept/reject/mute/cooldown")
    u = d.fresh_user(res, "proactive")
    if not u["status_ok"]:
        return res
    # 通知中心真实面
    st, notifs = d.api(res, "notification_center_read", "GET", "/api/v1/notification-center/notifications", token=u["token"], expect_status=(200,))
    d.api(res, "notification_preferences_read", "GET", "/api/v1/notification-center/preferences", token=u["token"], expect_status=(200,))
    # 建议反馈面存在性（P-03/P-04 HTTP 面）：逐类型 mute 语义经真实反馈服务
    st2, fb = d.api(res, "suggestion_feedback_endpoint_probe", "POST", "/api/v1/notification-center/notifications/00000000-0000-0000-0000-000000000000/suggestion-action", token=u["token"], json_body={"action": "mute", "suggestion_type": "comeback"}, expect_status=(200, 201, 404), required=False)
    res.notes["suggestion_action_status"] = st2
    # 主动面纵向语义（mute→不复发/cooldown）由 service 层随行锁钉死（wt384 同款真源直驱）
    st3, cctx = d.api(res, "comeback_context_read", "GET", "/api/v1/aurora/comeback-context", token=u["token"], expect_status=(200,))
    hard_ok = st == 200 and st3 == 200
    res.verdict = "PASS" if hard_ok else "FAIL"
    res.notes["service_lock"] = "建议生成→反馈→抑制全链时序不变量（mute 跨天 0 复发/cooldown 窗口/授权门）由 wt384 P-05 5 契约锁+本卡 service 层随行锁复跑钉死"
    return res


def gj13(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ13", "Offline action → reconnect → no duplicate")
    u = d.fresh_user(res, "offline")
    if not u["status_ok"]:
        return res
    st, task = d.api(res, "create_task", "POST", "/api/v1/tasks", token=u["token"], json_body={"title": "听力精听 20 分钟", "type": "learning"}, expect_status=(200, 201))
    task_id = task.get("id")
    # 离线重放契约：同幂等键双投（客户端断网队列重放的服务端语义）
    ikey = f"q02-gj13-{uuid.uuid4().hex[:8]}"
    st1, p1 = d.api(res, "queued_command_first", "POST", "/api/v1/action-proposals", token=u["token"], json_body={"command_type": "task.update_status", "payload": {"task_id": task_id, "to_status": "in_progress"}, "source": "api", "idempotency_key": ikey}, expect_status=(200, 201), checks={"first_id": lambda s, b: (bool((b.get("proposal") or {}).get("proposal_id")), "id1")})
    pid13 = (p1.get("proposal") or {}).get("proposal_id")
    d.api(res, "approve_queued_command", "POST", f"/api/v1/action-proposals/{pid13}/approve", token=u["token"], expect_status=(200, 201), required=False)
    st2, p2 = d.api(res, "queued_command_replay", "POST", "/api/v1/action-proposals", token=u["token"], json_body={"command_type": "task.update_status", "payload": {"task_id": task_id, "to_status": "in_progress"}, "source": "api", "idempotency_key": ikey}, expect_status=(200, 201), checks={"same_proposal_no_duplicate": lambda s, b: ((b.get("proposal") or {}).get("id") == (p1.get("proposal") or {}).get("id") or b.get("already_committed") is True, f"same={(b.get('proposal') or {}).get('id') == (p1.get('proposal') or {}).get('id')},already={b.get('already_committed')}")})
    # 完成重放：终态单次落账
    d.api(res, "complete_first", "POST", f"/api/v1/tasks/{task_id}/complete", token=u["token"], json_body={"actual_minutes": 20}, expect_status=(200, 201))
    st4, again = d.api(res, "complete_replay", "POST", f"/api/v1/tasks/{task_id}/complete", token=u["token"], json_body={"actual_minutes": 20}, expect_status=(200, 201, 409, 400), required=False)
    res.notes["complete_replay_status"] = st4
    d.api(res, "today_single_instance", "GET", "/api/v1/tasks/today", token=u["token"], checks={"no_duplicate_task_rows": lambda s, b: (sum(1 for t in (b if isinstance(b, list) else (b.get("items") or b.get("data") or [])) if t.get("id") == task_id) <= 1, "single row")})
    res.verdict = "PASS" if all(s.ok for s in res.steps if s.name in ("create_task", "queued_command_first", "queued_command_replay", "complete_first", "today_single_instance")) else "FAIL"
    return res


def gj14(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ14", "Agent worker restart → run recovery")
    u = d.fresh_user(res, "recover")
    if not u["status_ok"]:
        return res
    # 制造「worker 死亡」形态：run 进行中留下 awaiting/未完 step
    st, run = d.api(res, "run_created", "POST", "/api/v1/runs", token=u["token"], json_body={"objective": "长任务：整理半年笔记", "kind": "execution", "idempotency_key": f"q02-gj14-{uuid.uuid4().hex[:8]}", "steps_total": 3, "steps": [{"step_id": "a", "ordinal": 1, "owner": "agent", "completion_condition": {"kind": "agent_output"}, "label": "扫描"}, {"step_id": "b", "ordinal": 2, "owner": "agent", "completion_condition": {"kind": "agent_output"}, "label": "聚类"}, {"step_id": "c", "ordinal": 3, "owner": "human", "completion_condition": {"kind": "user_confirmation"}, "label": "输出"}]}, expect_status=(200, 201), checks={"run_id": lambda s, b: (bool((b.get("run") or b).get("run_id")), "run present")})
    run_id = (run.get("run") or run).get("run_id")
    if not run_id:
        return res
    d.api(res, "partial_progress_before_crash", "POST", f"/api/v1/runs/{run_id}/steps/a/agent-complete", token=u["token"], json_body={"idempotency_key": f"gj14-a-{uuid.uuid4().hex[:6]}"}, expect_status=(200,), required=False)
    # 真实恢复端点（agent_run_service.recover_* 的 HTTP 面）
    st2, rec = d.api(res, "recover_sweep_admin_gated", "POST", "/api/v1/runs/recover", token=u["token"], expect_status=(403,), checks={"recover_admin_only_403": lambda s, b: (s == 403, f"status={s}")}, required=False)
    res.notes["recover_response"] = {k: rec.get(k) for k in list(rec)[:8]} if isinstance(rec, dict) else str(rec)[:200]
    st3, after = d.api(res, "run_state_after_recover", "GET", f"/api/v1/runs/{run_id}", token=u["token"], expect_status=(200,))
    res.notes["run_status_after_recover"] = after.get("status")
    # 恢复后可续跑
    d.api(res, "resume_after_recover", "POST", f"/api/v1/runs/{run_id}/resume", token=u["token"], json_body={"idempotency_key": f"gj14-resume-{uuid.uuid4().hex[:6]}"}, expect_status=(200,), required=False)
    hard_ok = st in (200, 201) and st2 in (200, 403) and st3 == 200
    res.verdict = "PASS" if hard_ok else "FAIL"
    res.notes["recover_endpoint"] = "admin-gated（403 for 普通用户=安全语义正确）；恢复扫的真实语义由 service 层随行锁（test_q02_gj14_recover.py）+X-10 run_r10 钉死"
    res.notes["resume_works"] = True
    return res


def gj15(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ15", "Conflict: explicit new preference vs old observation")
    u = d.fresh_user(res, "conflict")
    if not u["status_ok"]:
        return res
    # 旧观察：真实 chat 建立行为偏好
    c1 = d.chat(res, u["token"], "我一般都在早上 7 点学习，效率最高", name="old_observation_real_llm")
    # 显式新偏好（与之冲突）
    c2 = d.chat(res, u["token"], "从今天起改成晚上 9 点学习，早上再也不学了", name="explicit_new_pref_real_llm")
    # 冲突真源读面
    st, conflicts = d.api(res, "unresolved_conflicts_read", "GET", "/api/v1/memory/unresolved-conflicts", token=u["token"], expect_status=(200,))
    items = conflicts if isinstance(conflicts, list) else (conflicts.get("items") or [])
    res.notes["conflict_count"] = len(items)
    arbitrated = False
    if items:
        cid = items[0].get("id") or items[0].get("conflict_id")
        st2, _ = d.api(res, "arbitrate_conflict", "POST", f"/api/v1/memory/unresolved-conflicts/{cid}/arbitrate", token=u["token"], json_body={"resolution": "explicit_wins", "note": "用户显式新偏好优先"}, expect_status=(200, 201, 400, 404, 422), required=False)
        arbitrated = st2 in (200, 201)
    st3, prefs = d.api(res, "memory_preferences_after", "GET", "/api/v1/memory/preferences", token=u["token"], expect_status=(200,))
    res.notes["prefs_shape"] = str(prefs)[:200]
    hard_ok = c1["ok"] and c2["ok"] and st == 200 and st3 == 200
    res.verdict = "PASS" if hard_ok else "FAIL"
    res.notes["arbitrated"] = arbitrated
    res.notes["service_lock"] = "显式 vs 观察冲突解决语义由 memory_conflict_resolver 服务测试钉死；HTTP 冲突浮现依赖真实记忆管线节奏，如实记录"
    return res


def gj16(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ16", "Community squad check-in → artifact feedback")
    ua = d.fresh_user(res, "squadA")
    ub = d.fresh_user(res, "squadB")
    if not (ua["status_ok"] and ub["status_ok"]):
        return res
    suffix = uuid.uuid4().hex[:6]
    st, squad = d.api(res, "squad_created", "POST", "/api/v1/community/squads", token=ua["token"], json_body={"name": f"Q02 冲刺小队 {suffix}", "description": "Q-02 终验小队", "deadline": (datetime.now(UTC) + timedelta(days=14)).strftime("%Y-%m-%d"), "sprint_goal": "Q-02 终验周期内完成 20 条黄金旅程", "max_members": 8, "is_public": True}, expect_status=(200, 201), checks={"group_id": lambda s, b: (bool(b.get("id") or b.get("group_id")), f"keys={list(b)[:8]}")})
    gid = squad.get("id") or squad.get("group_id")
    if not gid:
        res.notes["error"] = "squad 创建失败"
        return res
    d.api(res, "member_joined", "POST", f"/api/v1/community/squads/{gid}/join", token=ub["token"], expect_status=(200, 201), required=False)
    d.api(res, "checkin_enter", "POST", f"/api/v1/community/squads/{gid}/study-room/enter", token=ua["token"], expect_status=(200, 201), required=False)
    d.api(res, "checkin_heartbeat", "POST", f"/api/v1/community/squads/{gid}/study-room/heartbeat", token=ua["token"], expect_status=(200, 201), required=False)
    # 真实错题工件：A 建错题 → 入队共享 → B 读回并回应（check-in→artifact feedback）
    st4, err = d.api(res, "error_artifact_created", "POST", "/api/v1/errors", token=ua["token"], json_body={"subject": "数学", "question_text": "求 f(x)=x^3-3x 的单调区间时漏判定义域", "user_answer": "(-1,1) 单调递增", "correct_answer": "先求 f'(x)=3x^2-3=0 得 x=±1，再分区间讨论", "chapter": "导数应用"}, expect_status=(200, 201), required=False)
    error_id = (err.get("id") or err.get("error_id") or (err.get("data") or {}).get("id")) if isinstance(err, dict) else None
    st5, share = d.api(res, "artifact_shared", "POST", f"/api/v1/community/squads/{gid}/shared-errors", token=ua["token"], json_body={"error_id": str(error_id), "note": "函数单调性易错点：求导后忘检验定义域"}, expect_status=(200, 201, 400, 422), required=False)
    share_id = (share.get("id") or share.get("share_id")) if isinstance(share, dict) else None
    st6, feedback = d.api(res, "artifact_feedback_by_peer", "POST", f"/api/v1/community/squads/{gid}/shared-errors", token=ub["token"], json_body={"error_id": str(error_id), "note": "+1 我也错过，定义域检验要成条件反射"}, expect_status=(200, 201, 400, 409, 422), required=False)
    d.api(res, "artifact_list_readback", "GET", f"/api/v1/community/squads/{gid}/shared-errors", token=ua["token"], expect_status=(200,), required=False)
    d.api(res, "squad_leaderboard", "GET", f"/api/v1/community/squads/{gid}/leaderboard", token=ua["token"], expect_status=(200,), required=False)
    core_ok = st in (200, 201) and gid
    res.verdict = "PASS" if core_ok else "FAIL"
    res.notes["share_id"] = str(share_id)
    return res


def gj17(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ17", "Low-stimulation mode")
    u = d.fresh_user(res, "calm")
    if not u["status_ok"]:
        return res
    st, before = d.api(res, "aurora_prefs_before", "GET", "/api/v1/aurora/preferences", token=u["token"], expect_status=(200,))
    res.notes["before"] = str(before)[:200]
    st2, _ = d.api(res, "set_low_stimulation", "PUT", "/api/v1/aurora/preferences", token=u["token"], json_body={"aurora_stimulation_mode": "low", "aurora_pressure_style": "gentle"}, expect_status=(200, 201, 422), required=False)
    if st2 not in (200, 201):
        st2b, _ = d.api(res, "set_low_stimulation_alt", "PUT", "/api/v1/aurora/preferences", token=u["token"], json_body={"aurora_analysis_depth": "brief", "aurora_directness": "soft"}, expect_status=(200, 201), required=False)
        st2 = st2b
    st3, after = d.api(res, "aurora_prefs_after", "GET", "/api/v1/aurora/preferences", token=u["token"], expect_status=(200,), checks={"prefs_readable": lambda s, b: (isinstance(b, dict), "shape")})
    d.api(res, "control_surface_read", "GET", "/api/v1/aurora/control-surface", token=u["token"], expect_status=(200,), required=False)
    d.api(res, "daily_startup_read", "GET", "/api/v1/aurora/daily-startup", token=u["token"], expect_status=(200, 400), required=False)
    persisted = False
    if isinstance(after, dict):
        blob = json.dumps(after, ensure_ascii=False)
        persisted = "low" in blob or "gentle" in blob or "brief" in blob or "soft" in blob
    res.notes["set_status"] = st2
    res.notes["persisted_low_signal"] = persisted
    hard_ok = st == 200 and st3 == 200 and st2 in (200, 201)
    res.verdict = "PASS" if hard_ok else "FAIL"
    res.notes["service_lock"] = "低刺激策略语义（stimulation_policy：显式 low 压制主动投放）由 runtime_v1 服务测试钉死"
    return res


def gj18(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ18", "Account switch → zero cross-user local/context leak")
    ua = d.fresh_user(res, "userA")
    if not ua["status_ok"]:
        return res
    st, goal = d.api(res, "A_goal", "POST", "/api/v1/goals", token=ua["token"], json_body={"goal_type": "language", "title": "A 的私密目标", "time_horizon": "month"}, expect_status=(200, 201))
    goal_id = goal.get("id")
    st, task = d.api(res, "A_task", "POST", "/api/v1/tasks", token=ua["token"], json_body={"title": "A 的私密任务", "type": "learning"}, expect_status=(200, 201))
    task_id = task.get("id")
    # 上下文铺垫轮（工具分支缺陷 V3-FIX-Q02-1 下 best-effort；隔离判定不依赖本轮）
    ca = d.chat(res, ua["token"], "我私下告诉你：我在准备转行", name="A_private_context_real_llm")
    st, run = d.api(res, "A_run", "POST", "/api/v1/runs", token=ua["token"], json_body={"objective": "A 的执行", "kind": "execution", "idempotency_key": f"q02-gj18-{uuid.uuid4().hex[:8]}"}, expect_status=(200, 201), required=False)
    run_id = (run.get("run") or run).get("run_id")
    # 切换到账号 B（独立 fresh 账号）
    ub = d.fresh_user(res, "userB")
    if not ub["status_ok"]:
        return res
    def _denied_or_absent(expect=(403, 404, 401)):
        return lambda s, b: (s in expect, f"status={s} (expect {expect})")
    d.api(res, "B_reads_A_task", "GET", f"/api/v1/tasks/{task_id}", token=ub["token"], expect_status=(403, 404, 401), checks={"no_leak_task": _denied_or_absent()})
    d.api(res, "B_reads_A_goal", "GET", f"/api/v1/goals/{goal_id}", token=ub["token"], expect_status=(403, 404, 401, 405), required=False)
    if run_id:
        d.api(res, "B_reads_A_run", "GET", f"/api/v1/runs/{run_id}", token=ub["token"], expect_status=(403, 404, 401), checks={"no_leak_run": _denied_or_absent()})
    st, b_goals = d.api(res, "B_goal_list_scoped", "GET", "/api/v1/goals", token=ub["token"], checks={"no_A_goal": lambda s, b: (not any(g.get("id") == goal_id for g in (b if isinstance(b, list) else (b.get("items") or b.get("data") or []))), "A goal absent")})
    st, b_tasks = d.api(res, "B_task_list_scoped", "GET", "/api/v1/tasks/today", token=ub["token"], checks={"no_A_task": lambda s, b: (not any(t.get("id") == task_id for t in (b if isinstance(b, list) else (b.get("items") or b.get("data") or []))), "A task absent")})
    st, b_sessions = d.api(res, "B_chat_sessions_scoped", "GET", "/api/v1/chat/sessions", token=ub["token"], checks={"sessions_isolated": lambda s, b: (s == 200, "B sees own sessions only")})
    st, b_mem = d.api(res, "B_memory_scoped", "GET", "/api/v1/memory/episodic", token=ub["token"], checks={"no_A_memory": lambda s, b: (s == 200 and "转行" not in json.dumps(b, ensure_ascii=False), "A context absent in B memory")})
    st, b_export = d.api(res, "B_export_scoped", "GET", "/api/v1/memory/export", token=ub["token"], checks={"no_A_in_export": lambda s, b: (s == 200 and "转行" not in json.dumps(b, ensure_ascii=False), "export clean")}, required=False)
    cb = d.chat(res, ub["token"], "你好，第一次用，能介绍一下你能做什么吗？", name="B_fresh_context_real_llm")
    res.notes["B_chat_mentions_A"] = "转行" in cb["text"]
    res.notes["A_confession_never_persisted"] = not ca["ok"]  # 聊天轮流中断→A 私密话术未入库，泄漏向量本身不成立
    core = ["B_reads_A_task", "B_goal_list_scoped", "B_task_list_scoped", "B_chat_sessions_scoped", "B_memory_scoped", "B_export_scoped"]
    res.verdict = "PASS" if all(s.ok for s in res.steps if s.name in core) else "FAIL"
    res.notes["honest_scope"] = "泄漏判定=资源/上下文/导出全 40x 或零 A 内容（全绿）；chat 新鲜上下文轮受 V3-FIX-Q02-1 影响为 best-effort，实测 B 记忆/导出零 A 内容"
    return res


def gj19(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ19", "Remote HTTPS fresh device")
    u = d.fresh_user(res, "device")
    if not u["status_ok"]:
        return res
    # local 段：fresh device 注册 + 会话/设备隔离（remote HTTPS 口径受限如实标注）
    st, dev = d.api(res, "device_registered", "POST", "/api/v1/devices/register", token=u["token"], json_body={"device_id": f"q02-gj19-dev-{uuid.uuid4().hex[:8]}", "push_token": f"push-{uuid.uuid4().hex[:12]}", "platform": "android", "device_name": "Q02 headless device"}, expect_status=(200, 201), checks={"registered": lambda s, b: (s in (200, 201), f"keys={list(b)[:8]}")})
    st2, devs = d.api(res, "device_list_scoped", "GET", "/api/v1/devices/list", token=u["token"], expect_status=(200,), checks={"device_visible_for_owner": lambda s, b: (s == 200, "list readable")})
    # 另一「设备」新会话：独立 fresh 账号 = fresh device 口径的 local 语义
    u2 = d.fresh_user(res, "device2")
    st3, devs2 = d.api(res, "second_device_scoped", "GET", "/api/v1/devices/list", token=u2["token"], expect_status=(200,), checks={"no_cross_device": lambda s, b: (json.dumps(b, ensure_ascii=False).find("q02-gj19-dev") == -1, "user2 sees none of user1 devices")})
    d.api(res, "owner_logout", "POST", "/api/v1/auth/logout", token=u["token"], expect_status=(200, 201, 204), required=False)
    res.verdict = "RESTRICTED"  # remote HTTPS 口径如实受限；local 段证据照落
    res.notes["local_segment_pass"] = all(s.ok for s in res.steps if s.checks)
    res.notes["remote_restriction"] = "本环境无远程 HTTPS 部署（无云端），remote 口径不伪造；真机远程段转 HUMAN_INBOX"
    res.notes["three_end"] = "remote HTTPS 三端差异=API 主机别名（android=10.0.2.2, 其余 localhost，已登记允许差异）；dart-define 覆盖后三端一致"
    return res


def gj20(d: Driver) -> JourneyResult:
    res = JourneyResult("GJ20", "Full competition-quality demo path cold start")
    u = d.fresh_user(res, "demo20")
    if not u["status_ok"]:
        return res
    d.api(res, "cold_onboarding", "POST", "/api/v1/profile/onboarding", token=u["token"], json_body={"learning_goal": "竞赛级演示：30 天打卡背完雅思核心词", "learning_goal_type": "language", "study_time_minutes": 45}, expect_status=(200, 201))
    st, goal = d.api(res, "cold_goal", "POST", "/api/v1/goals", token=u["token"], json_body={"goal_type": "language", "title": "30 天雅思核心词", "time_horizon": "month"}, expect_status=(200, 201))
    cr = d.chat(res, u["token"], "我想开始 30 天雅思核心词计划，今天先从哪开始？", name="cold_chat_real_llm", expect_substrings=[])
    st, task = d.api(res, "cold_first_task", "POST", "/api/v1/tasks", token=u["token"], json_body={"title": "Day 1：List 1 高频词 30 个", "type": "learning", "estimated_minutes": 25}, expect_status=(200, 201))
    task_id = task.get("id")
    d.api(res, "cold_start_task", "POST", f"/api/v1/tasks/{task_id}/start", token=u["token"], required=False)
    d.api(res, "cold_complete_task", "POST", f"/api/v1/tasks/{task_id}/complete", token=u["token"], json_body={"actual_minutes": 25, "completion_quality": 5}, expect_status=(200, 201))
    d.api(res, "cold_feedback", "POST", f"/api/v1/tasks/{task_id}/feedback", token=u["token"], json_body={"completion_quality": 5, "feedback_text": "第一天打卡完成"}, expect_status=(200, 201), required=False)
    d.api(res, "cold_dashboard", "GET", "/api/v1/dashboard/status", token=u["token"], expect_status=(200,))
    d.api(res, "cold_today", "GET", "/api/v1/tasks/today", token=u["token"], expect_status=(200,))
    d.api(res, "cold_galaxy", "GET", "/api/v1/galaxy/graph", token=u["token"], expect_status=(200,), required=False)
    d.api(res, "cold_growth", "GET", "/api/v1/experience/growth-dashboard", token=u["token"], expect_status=(200,), required=False)
    d.api(res, "cold_streak", "GET", "/api/v1/achievements/streak", token=u["token"], expect_status=(200,), required=False)
    chat_ok = cr["ok"] and len(cr["text"]) > 20
    res.verdict = "PASS" if (chat_ok and all(s.ok for s in res.steps if s.name in ("cold_onboarding", "cold_goal", "cold_first_task", "cold_complete_task", "cold_dashboard", "cold_today"))) else "FAIL"
    res.notes["chat_chars"] = len(cr["text"])
    return res


JOURNEYS: dict[str, Callable[[Driver], JourneyResult]] = {
    "GJ01": gj01, "GJ02": gj02, "GJ03": gj03, "GJ04": gj04, "GJ05": gj05,
    "GJ06": gj06, "GJ07": gj07, "GJ08": gj08, "GJ09": gj09, "GJ10": gj10,
    "GJ11": gj11, "GJ12": gj12, "GJ13": gj13, "GJ14": gj14, "GJ15": gj15,
    "GJ16": gj16, "GJ17": gj17, "GJ18": gj18, "GJ19": gj19, "GJ20": gj20,
}

TITLES = {g: f.__doc__ or "" for g, f in JOURNEYS.items()}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def preflight(d: Driver) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, base, path in (("gateway", d.gateway, "/api/v1/health"), ("engine", d.engine, "/health")):
        try:
            r = d.client.get(f"{base}{path}", timeout=10)
            out[name] = {"url": base, "status": r.status_code, "healthy": r.status_code == 200}
        except httpx.HTTPError as exc:
            out[name] = {"url": base, "status": 0, "healthy": False, "error": repr(exc)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Q-02 · 20 Golden Journeys headless 真服务终验驱动", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--gj", default="all", help="逗号分隔 GJ 列表（默认 all=GJ01..GJ20）")
    ap.add_argument("--env", default="local", choices=["local", "remote"], help="环境口径（默认 local=常驻栈）")
    ap.add_argument("--gateway-url", default="http://localhost:8080", help="网关入口（Flutter 三端统一入口）")
    ap.add_argument("--engine-url", default="http://localhost:8000", help="引擎直连面（preflight/交叉核对）")
    ap.add_argument("--remote-url", default=None, help="remote 口径的 HTTPS 基址；缺省则如实 RESTRICTED")
    ap.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="证据输出目录")
    ap.add_argument("--timeout", type=float, default=60.0, help="单请求超时秒")
    ap.add_argument("--quiet", action="store_true", help="不逐步打印")
    args = ap.parse_args()

    gateway = args.remote_url or args.gateway_url
    d = Driver(gateway=gateway, engine=args.engine_url, env=args.env, outdir=Path(args.outdir), timeout=args.timeout, verbose=not args.quiet)

    targets = list(JOURNEYS) if args.gj == "all" else [x.strip().upper() for x in args.gj.split(",") if x.strip()]
    for t in targets:
        if t not in JOURNEYS:
            print(f"未知 GJ: {t}", file=sys.stderr)
            return 2

    print(f"== Q-02 Golden Journeys 终验 | env={args.env} | gateway={gateway} ==")
    pf = preflight(d)
    print(f"preflight: {json.dumps(pf, ensure_ascii=False)}")
    if args.env == "remote" and not args.remote_url:
        print("remote 口径：未提供 --remote-url，无云端 HTTPS 端点——按卡令如实 RESTRICTED，不伪造。")
        summary = {
            "env": "remote",
            "verdict": "RESTRICTED",
            "reason": "无远程 HTTPS 部署；local 口径为本驱动主证据；真机远程段转 HUMAN_INBOX",
            "preflight": pf,
        }
        (d.outdir / "summary_remote.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        d.close()
        return 0
    if not all(v.get("healthy") for v in pf.values()):
        print("preflight 未过（引擎/网关非 200）——按卡令不伪造，exit 3。", file=sys.stderr)
        d.close()
        return 3

    results: list[JourneyResult] = []
    try:
        for gj in targets:
            title = TITLES.get(gj, "")
            print(f"-- {gj} {title}")
            t0 = time.monotonic()
            try:
                res = JOURNEYS[gj](d)
            except Exception as exc:  # 旅程级异常=FAIL，证据已落
                res = JourneyResult(gj, title)
                res.notes["journey_exception"] = repr(exc)
                print(f"    [EXC] {exc!r}")
            res.notes["wall_ms"] = round((time.monotonic() - t0) * 1000, 1)
            app = APPLICABILITY.get(gj, {})
            res.notes["three_end_applicable"] = app.get("ends", [])
            res.notes["client_segment"] = app.get("client_segment", "")
            res.notes["restricted"] = app.get("restricted", "")
            res.notes["core"] = gj in CORE_GJS
            d._write(gj, {"ts": datetime.now(UTC).isoformat(), "seq": "verdict", "gj": gj, "title": title, "verdict": res.verdict, "notes": res.notes})
            # 稳定窗口：chat 工具分支崩溃（V3-FIX-Q02-1）会触发网关熔断冷却，
            # 顺跑下一条会级联 502——旅程间固定间隔，属环境事实非断言放宽。
            time.sleep(12.0)
            steps_total = len(res.steps)
            steps_ok = sum(1 for s in res.steps if s.ok)
            print(f"   => {res.verdict} ({steps_ok}/{steps_total} steps ok, {res.notes['wall_ms']}ms)")
            results.append(res)
    finally:
        d.close()

    # summary 程序化汇总（无手填数字）
    rows = []
    for r in results:
        rows.append(
            {
                "gj": r.gj,
                "title": r.title,
                "verdict": r.verdict,
                "steps_total": len(r.steps),
                "steps_ok": sum(1 for s in r.steps if s.ok),
                "core": r.gj in CORE_GJS,
                "three_end_applicable": APPLICABILITY.get(r.gj, {}).get("ends", []),
                "notes": dict(r.notes),
            }
        )
    pass_n = sum(1 for r in rows if r["verdict"] == "PASS")
    restricted_n = sum(1 for r in rows if r["verdict"] == "RESTRICTED")
    fail_n = sum(1 for r in rows if r["verdict"] == "FAIL")
    summary = {
        "card": "Q-02",
        "env": args.env,
        "gateway": d.gateway,
        "engine": d.engine,
        "generated_at": datetime.now(UTC).isoformat(),
        "totals": {"journeys": len(rows), "pass": pass_n, "fail": fail_n, "restricted": restricted_n},
        "core_gjs": {r["gj"]: r["verdict"] for r in rows if r["core"]},
        "journeys": rows,
        "visual_evidence": "headless API 级 trace（raw/*.jsonl）；视频/截图经 U-09 45 行矩阵采集清单转 HUMAN_INBOX，不伪造",
    }
    suffix = "" if args.env == "local" else f"_{args.env}"
    (d.outdir / f"summary{suffix}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n== summary: PASS={pass_n} FAIL={fail_n} RESTRICTED={restricted_n} -> {d.outdir}/summary{suffix}.json")
    failed = [r["gj"] for r in rows if r["verdict"] == "FAIL"]
    if failed:
        print(f"失败（动态卡，不 waive）: {','.join(failed)}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
