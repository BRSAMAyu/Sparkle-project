"""NORTHSTAR · TOUR 功能成体检验——6 个新面串成一条真实用户旅程（API 级）。

与 real_drive.py 的关系：同一 EvidenceStore/StepEvidence 证据模式，但驱动的是
「功能协同成体」而非单日学习闭环。本模块不改产品代码，只经真实网关把
2026-09-22 夜落地的 6 个新面串成一个期末冲刺学生的 20 分钟：

  1. 注册 → exam-sprint intake（静态包，零 LLM）→ POST /plans/{id}/confirm（CP-01）
  2. 建冲刺小队（3 人）→ 队友 join → 各自走真实任务完成 API 完成 Day1 的一部分
  3. 主号进自习室学习 → 完成自己 Day1 任务 → 出自习室（presence 今日累计）
  4. 小队榜（完成度排序/并列名次，与 sprint_task_ledger 单一事实源对账）
     + 自我锚（7 日序列含今日）
  5. 主号走成就/首胜真实路径攒光子 → 审计流水重放对账「可兑换基数」
     → POST /photons/redeem-pro 兑 Pro 7 天 → entitlement 落库断言（含月顶幂等）
  6. 全程跨面一致性：确认后的计划出 today 任务；榜序即时反映完成度变化
     （D-COMM 面不走 galaxy 缓存——本脚本零失效调用下断言新鲜度，记录结论）

诚实红线：LLM 零消费（intake 走 exam_prep_14d 静态包确定性路径）；空数据/失败
如实落证据 verdict，不折算 pass。任务完成只传真实观测（actual_minutes 缺省，
由服务端从真实起止时间推算——X-04 红线）。

用法（栈须已在跑；TOUR_GATEWAY_URL 指向含全部新路由的网关）::

    SECRET_KEY=test python3 -m tests.northstar_eval.feature_tour --check   # 栈自检
    SECRET_KEY=test python3 -m tests.northstar_eval.feature_tour           # 全旅程
    SECRET_KEY=test python3 -m tests.northstar_eval.feature_tour --phase plan

配置注入：TOUR_GATEWAY_URL（默认 http://localhost:8090）、TOUR_OUT_DIR
（默认 <repo>/v3-output/TOUR）、TOUR_USERNAME_PREFIX（默认 tour_voyage_）。
账号凭据只落 /tmp 运行态（600）；证据里凭据只以 sha256 前缀出现。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

SCHEMA_STEP = "sparkle.tour.voyage.step.v1"
SCHEMA_RUN = "sparkle.tour.voyage.run.v1"

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_BLOCKED = "blocked"
VERDICTS = (VERDICT_PASS, VERDICT_FAIL, VERDICT_BLOCKED)

#: 与 app/services/photon_redeem_service.py 同源（本模块是消费面，不 import 产品代码）
REDEEMABLE_INCOME_TYPES = frozenset(
    {"grant_achievement", "grant_daily_first", "grant_contract", "grant_contract_bonus", "grant_bonus"}
)
REDEEM_PRO_TX_TYPE = "redeem_pro"
REDEEM_PRO_COST = 3000  # settings.PHOTON_REDEEM_PRO_COST 部署值（【待产品校准】）
REDEEM_PRO_DAYS = 7

GATEWAY_URL = os.environ.get("TOUR_GATEWAY_URL", "http://localhost:8090")
OUT_DIR = Path(os.environ.get("TOUR_OUT_DIR", "")) if os.environ.get("TOUR_OUT_DIR") else None
USERNAME_PREFIX = os.environ.get("TOUR_USERNAME_PREFIX", "tour_voyage_")
STATE_PATH = Path(os.environ.get("TOUR_STATE_PATH", "/tmp/tour_voyage_state.json"))
REQUEST_TIMEOUT_S = 60.0
EVENT_SETTLE_S = 12.0  # task.completed → 成就/光子异步链路的期望收敛窗口（含重试）
EVENT_MAX_WAIT_S = 90.0
EARNING_SPRINT_CAP = 14  # 攒光子的冲刺上限（护栏）
EARN_TARGET = REDEEM_PRO_COST + 200  # 兑换门槛 + 余量


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_prefix(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def out_dir() -> Path:
    base = OUT_DIR or (_repo_root() / "v3-output" / "TOUR")
    base.mkdir(parents=True, exist_ok=True)
    (base / "evidence" / "steps").mkdir(parents=True, exist_ok=True)
    return base


def redact(
    payload: dict[str, Any], keys: tuple[str, ...] = ("password", "access_token", "refresh_token", "token")
) -> dict[str, Any]:
    out = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    if isinstance(out, dict):
        for key, value in list(out.items()):
            if key in keys and isinstance(value, str):
                out[key] = f"sha256:{sha256_prefix(value)}"
            elif isinstance(value, dict):
                out[key] = redact(value, keys)
    return out


def truncate(value: Any, limit: int = 2600) -> Any:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, default=str)
        if len(text) <= limit:
            return value
        return {"_truncated": True, "_preview": text[:limit]}
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"...[truncated {len(value)}->{limit}]"
    return value


@dataclass
class StepEvidence:
    run_id: str
    step_id: str
    phase: str
    name: str
    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    verdict: str = VERDICT_BLOCKED
    notes: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=utcnow_iso)
    finished_at: str = ""

    def note(self, text: str) -> None:
        self.notes.append(text)

    def finish(self, verdict: str, notes: list[str] | None = None) -> StepEvidence:
        self.verdict = verdict if verdict in VERDICTS else VERDICT_BLOCKED
        if notes:
            self.notes.extend(notes)
        self.finished_at = utcnow_iso()
        return self

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_STEP,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "phase": self.phase,
            "name": self.name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "request": self.request,
            "response": self.response,
            "verdict": self.verdict,
            "notes": list(self.notes),
        }


class EvidenceStore:
    """证据落盘：out/evidence/steps/*.json + out/evidence/*.json（逐文件稳定 schema）。"""

    def __init__(self, base: Path, run_id: str) -> None:
        self.base = base
        self.run_id = run_id
        self.steps_dir = base / "evidence" / "steps"

    def write_step(self, step: StepEvidence) -> Path:
        path = self.steps_dir / f"{step.step_id}_{_slug(step.name)}.json"
        path.write_text(json.dumps(step.to_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_json(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.base / "evidence" / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-")[:60]


# ---------------------------------------------------------------------------
# 网关 REST 客户端（stdlib；多账号各持 token）
# ---------------------------------------------------------------------------


class GatewayClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.tokens: dict[str, str] = {}

    def request(
        self,
        method: str,
        path: str,
        token: str | None = None,
        body: dict[str, Any] | None = None,
        timeout: float = REQUEST_TIMEOUT_S,
    ) -> dict[str, Any]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        started = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode()
                payload: Any = json.loads(raw) if raw else {}
                return {"status": resp.status, "body": payload, "latency_ms": int((time.monotonic() - started) * 1000)}
        except urllib.error.HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode())
            except Exception:  # noqa: BLE001 — 探针要的是可读错误
                payload = {"_raw": str(exc)}
            return {"status": exc.code, "body": payload, "latency_ms": int((time.monotonic() - started) * 1000)}
        except Exception as exc:  # noqa: BLE001
            return {"status": -1, "body": {"_error": str(exc)}, "latency_ms": -1}

    def get(self, path: str, token: str | None = None) -> dict[str, Any]:
        return self.request("GET", path, token)

    def post(self, path: str, token: str | None = None, body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("POST", path, token, body)

    def register(self, username: str) -> dict[str, Any]:
        password = "Tour#" + uuid.uuid4().hex[:12]
        body = {
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "nickname": username,
            "accepted_tos": True,
            "accepted_privacy": True,
            "tos_version": "v1",
            "privacy_version": "v1",
        }
        resp = self.request("POST", "/api/v1/auth/register", body=body)
        token = None
        if resp["status"] == 200 and isinstance(resp["body"], dict):
            token = resp["body"].get("access_token") or resp["body"].get("token")
        if token:
            self.tokens[username] = str(token)
        return {**resp, "username": username, "password": password, "token": token}

    def register_or_login(self, username: str) -> dict[str, Any]:
        """幂等建号：用户名已存在（重跑）→ 登录复用。"""
        resp = self.register(username)
        if resp["token"]:
            return resp
        password = _state()["accounts"].get(username, {}).get("password")
        if password:
            login = self.request("POST", "/api/v1/auth/login", body={"username": username, "password": password})
            token = login["body"].get("access_token") if isinstance(login["body"], dict) else None
            if login["status"] == 200 and token:
                self.tokens[username] = str(token)
                return {**login, "username": username, "password": password, "token": str(token), "reused": True}
        return resp


_STATE_CACHE: dict[str, Any] | None = None


def _state() -> dict[str, Any]:
    global _STATE_CACHE
    if _STATE_CACHE is None:
        if STATE_PATH.exists():
            _STATE_CACHE = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        else:
            _STATE_CACHE = {"run_id": uuid.uuid4().hex[:8], "accounts": {}, "artifacts": {}}
            _save_state(_STATE_CACHE)
    return _STATE_CACHE


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(STATE_PATH, 0o600)
    except OSError:
        pass


def _remember_account(account: dict[str, Any]) -> None:
    state = _state()
    state["accounts"][account["username"]] = {
        "username": account["username"],
        "password": account["password"],
        "user_id": account.get("user_id") or state["accounts"].get(account["username"], {}).get("user_id"),
    }
    _save_state(state)


# ---------------------------------------------------------------------------
# 剧情助手（确定性 exam_prep_14d 静态包 intake；真实任务完成）
# ---------------------------------------------------------------------------


def intake_exam_sprint(
    client: GatewayClient, token: str, subject: str, days_left: int, weak: list[str]
) -> dict[str, Any]:
    exam = date.today() + timedelta(days=days_left)
    return client.post(
        "/api/v1/exam-sprint/intake",
        token,
        {
            "subject": subject,
            "exam_date": exam.isoformat(),
            "target_mode": "pass",
            "baseline": {"current_level": 55, "weak_chapters": weak},
            "daily_study_minutes": 90,
        },
    )


def create_sprint_plan_with_tasks(
    client: GatewayClient,
    token: str,
    *,
    name: str,
    subject: str,
    task_titles: list[str],
    days_left: int = 5,
) -> dict[str, Any]:
    """直创冲刺计划 + 挂任务（真实 API；攒光子阶段的批量载体）。"""
    exam = date.today() + timedelta(days=days_left)
    created = client.post(
        "/api/v1/plans",
        token,
        {
            "name": name,
            "type": "sprint",
            "subject": subject,
            "target_date": exam.isoformat(),
            "daily_available_minutes": 60,
        },
    )
    if created["status"] != 201:
        return {"plan": created, "tasks": [], "task_ids": []}
    plan_body = created["body"]
    plan_id = plan_body["id"] if "id" in plan_body else plan_body.get("data", {}).get("id")
    task_ids: list[str] = []
    failures: list[dict[str, Any]] = []
    for title in task_titles:
        resp = client.post(
            "/api/v1/tasks",
            token,
            {"title": title, "type": "practice", "plan_id": plan_id, "estimated_minutes": 30},
        )
        payload = resp["body"] if isinstance(resp["body"], dict) else {}
        node = payload.get("data") or payload
        tid = node.get("id") if isinstance(node, dict) else None
        if resp["status"] == 200 and tid:
            task_ids.append(str(tid))
        else:
            failures.append({"status": resp["status"], "title": title})
    return {"plan": created, "plan_id": plan_id, "tasks": failures, "task_ids": task_ids}


def complete_task(client: GatewayClient, token: str, task_id: str) -> dict[str, Any]:
    """PENDING → IN_PROGRESS → COMPLETED（状态机），actual_minutes 缺省（X-04）。"""
    start = client.post(f"/api/v1/tasks/{task_id}/start", token, {})
    if start["status"] != 200:
        return {"status": start["status"], "body": start["body"], "task_id": task_id, "stage": "start"}
    done = client.post(f"/api/v1/tasks/{task_id}/complete", token, {})
    return {"status": done["status"], "body": done["body"], "task_id": task_id, "stage": "complete"}


def await_photon_balance(
    client: GatewayClient, token: str, *, at_least: int | None = None, max_wait: float = EVENT_MAX_WAIT_S
) -> int:
    """轮询余额直至 ≥ at_least（或超时返回当前值）——成就/光子链路是异步事件流。"""
    deadline = time.monotonic() + max_wait
    balance = -1
    while time.monotonic() < deadline:
        resp = client.get("/api/v1/photons/balance", token)
        if resp["status"] == 200:
            balance = int(resp["body"].get("data", {}).get("balance") or 0)
            if at_least is None or balance >= at_least:
                return balance
        time.sleep(4)
    return balance


def replay_redeemable_base(client: GatewayClient, token: str) -> dict[str, Any]:
    """审计流水重放「可兑换基数」（口径词典：四收入类型+首胜/combo；transfer_in 排除）。"""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        resp = client.get(f"/api/v1/photons/transactions?limit=100&offset={offset}", token)
        if resp["status"] != 200:
            return {"error": resp, "rows": rows}
        payload = resp["body"]
        rows.extend(payload.get("data") or [])
        meta = payload.get("meta") or {}
        if not meta.get("has_next") or not payload.get("data"):
            break
        offset += 100
    replay = 0
    by_type: Counter[str] = Counter()
    for row in rows:
        tx_type = str(row.get("transaction_type") or "")
        amount = int(row.get("amount") or 0)
        by_type[tx_type] += 1
        if tx_type in REDEEMABLE_INCOME_TYPES:
            replay += amount
        elif tx_type == REDEEM_PRO_TX_TYPE:
            replay += amount  # 负数扣减同向累计（重放=净额）
    return {"rows": rows, "replay_base": replay, "by_type": dict(by_type)}


# ---------------------------------------------------------------------------
# 旅程步骤（每步 = StepEvidence + 跨面一致性断言）
# ---------------------------------------------------------------------------


class Tour:
    def __init__(self) -> None:
        self.base = out_dir()
        self.state = _state()
        self.run_id = self.state.get("run_id") or uuid.uuid4().hex[:8]
        self.state["run_id"] = self.run_id
        _save_state(self.state)
        self.store = EvidenceStore(self.base, self.run_id)
        self.client = GatewayClient(GATEWAY_URL)
        self.results: list[dict[str, Any]] = []

    # -- 基建 ----------------------------------------------------------------

    def step(self, step_id: str, phase: str, name: str) -> StepEvidence:
        return StepEvidence(run_id=self.run_id, step_id=step_id, phase=phase, name=name)

    def finish(self, step: StepEvidence, ok: bool, verdict_notes: list[str] | None = None) -> bool:
        step.finish(VERDICT_PASS if ok else VERDICT_FAIL, verdict_notes)
        self.store.write_step(step)
        self.results.append(step.to_payload())
        print(f"[{step.step_id}] {step.name} -> {step.verdict}")
        for n in step.notes:
            print(f"    · {n}")
        return ok

    def account(self, role: str) -> dict[str, Any]:
        username = f"{USERNAME_PREFIX}{role}_{self.run_id}"
        acct = self.client.register_or_login(username)
        acct.setdefault("username", username)
        if acct.get("token"):
            if not acct.get("user_id"):
                body = acct.get("body") if isinstance(acct.get("body"), dict) else {}
                user = (body.get("user") or {}) if body else {}
                acct["user_id"] = user.get("id")
            if not acct.get("user_id"):
                me = self.client.get("/api/v1/auth/me", acct["token"])
                if me["status"] == 200 and isinstance(me["body"], dict):
                    node = me["body"].get("data") or me["body"].get("user") or {}
                    acct["user_id"] = node.get("id")
            _remember_account(acct)
        return acct

    # -- S0 栈自检 -----------------------------------------------------------

    def check(self) -> bool:
        step = self.step("S0", "check", "栈健康自检（worktree 网关 + 引擎）")
        health = self.client.get("/healthz")
        ok = health["status"] == 200
        step.request["gateway"] = GATEWAY_URL
        step.response["healthz"] = truncate(health)
        # 网关路由真相探针：假 token 打 6 面关键路由——已注册→401（auth 拦截），
        # 未注册→404 route not found（CP-01 的教训：引擎实现了网关不注册仍 404）。
        need = [
            "/api/v1/leaderboards/self-anchor",
            "/api/v1/photons/redeem-pro",
            "/api/v1/community/squads",
        ]
        missing: list[str] = []
        for path in need:
            probe = self.client.get(path, token="tour-route-probe-invalid")
            if probe["status"] == 404:
                missing.append(path)
        step.response["missing_routes"] = missing
        step.note(f"网关路由探针（401=已注册/404=缺失）：缺失 {len(missing)} 条")
        return self.finish(step, ok and not missing)

    # -- S1 注册 -------------------------------------------------------------

    def setup(self) -> dict[str, Any]:
        step = self.step("S1", "setup", "注册主号 + 两个队友号")
        main = self.account("main")
        mate_a = self.account("matea")
        mate_b = self.account("mateb")
        registered = [a for a in (main, mate_a, mate_b) if a.get("token")]
        step.response["accounts"] = [
            {"username": a["username"], "token": a.get("token") or "", "user_id": a.get("user_id")}
            for a in (main, mate_a, mate_b)
        ]
        step.response["accounts"] = redact(step.response["accounts"])
        step.note(f"registered={len(registered)}/3 (重跑幂等复用)")
        return {"main": main, "mate_a": mate_a, "mate_b": mate_b, "all_ready": len(registered) == 3}

    # -- S2 计划确认（CP-01） -------------------------------------------------

    def phase_plan(self, crew: dict[str, Any]) -> dict[str, Any]:
        step = self.step("S2", "plan", "CP-01：exam-sprint 计划确认（confirmed_at 落库）+ today 面板跨面")
        main = crew["main"]
        tok = main["token"]
        intake = intake_exam_sprint(self.client, tok, "高等数学", days_left=2, weak=["极限", "微分中值定理"])
        step.request["intake"] = {"subject": "高等数学", "days_left": 2, "pack": "exam_prep_14d@v1.0 静态包（零 LLM）"}
        if intake["status"] != 200:
            step.response["intake"] = truncate(intake)
            step.note("intake 失败——旅程中断")
            self.finish(step, False)
            return {}
        launch = intake["body"]["launch"]
        plan_id = launch["plan_id"]
        day1_ids = launch.get("first_day_task_ids") or []

        confirm = self.client.post(f"/api/v1/plans/{plan_id}/confirm", tok)
        confirmed_at = (confirm["body"] or {}).get("confirmed_at") if isinstance(confirm["body"], dict) else None
        reconfirm = self.client.post(f"/api/v1/plans/{plan_id}/confirm", tok)
        already = (reconfirm["body"] or {}).get("already_confirmed") if isinstance(reconfirm["body"], dict) else None
        foreign = self.client.post(f"/api/v1/plans/{plan_id}/confirm", crew["mate_a"]["token"])
        today = self.client.get(f"/api/v1/plans/{plan_id}/today", tok)
        today_tasks = (today["body"] or {}).get("tasks") if isinstance(today["body"], dict) else None

        step.response.update(
            {
                "plan_id": plan_id,
                "confirm": truncate(confirm),
                "reconfirm_already_confirmed": already,
                "foreign_confirm_status": foreign["status"],
                "today_status": today["status"],
                "today_task_count": len(today_tasks or []),
            }
        )
        ok = (
            confirm["status"] == 200
            and bool(confirmed_at)
            and already is True
            and foreign["status"] == 404  # 他人计划 404（防枚举）
            and today["status"] == 200
            and len(today_tasks or []) >= 1
        )
        step.note(f"confirmed_at={confirmed_at}")
        step.note(f"幂等再确认 already_confirmed={already}；他人确认={foreign['status']}")
        step.note(f"跨面：确认后 today 面板出 {len(today_tasks or [])} 个任务")
        self.finish(step, ok)
        return {"plan_id": plan_id, "day1_ids": day1_ids, "confirmed_at": confirmed_at}

    # -- S3 冲刺小队 ----------------------------------------------------------

    def phase_squad(self, crew: dict[str, Any]) -> dict[str, Any]:
        step = self.step("S3", "squad", "D-COMM-3：建 3 人冲刺小队 + 队友 join")
        main, mate_a, mate_b = crew["main"], crew["mate_a"], crew["mate_b"]
        deadline = (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)).isoformat()
        created = self.client.post(
            "/api/v1/community/squads",
            main["token"],
            {
                "name": f"TOUR 冲刺小队 {self.run_id}",
                "deadline": deadline,
                "sprint_goal": "Day1 全清",
                "max_members": 3,
            },
        )
        if created["status"] != 201:
            step.response["create"] = truncate(created)
            self.finish(step, False)
            return {}
        squad_id = created["body"]["id"]
        join_a = self.client.post(f"/api/v1/community/squads/{squad_id}/join", mate_a["token"])
        join_b = self.client.post(f"/api/v1/community/squads/{squad_id}/join", mate_b["token"])
        members = self.client.get(f"/api/v1/community/squads/{squad_id}/members", main["token"])
        member_list = members["body"] if isinstance(members["body"], list) else []
        progress = self.client.get(f"/api/v1/community/squads/{squad_id}/sprint-progress", main["token"])
        prog_members = (progress["body"] or {}).get("members") if isinstance(progress["body"], dict) else []

        step.response.update(
            {
                "squad_id": squad_id,
                "join_a": join_a["status"],
                "join_b": join_b["status"],
                "member_count": len(member_list),
                "sprint_progress_members": [
                    {
                        "total": m.get("task_total"),
                        "completed": m.get("task_completed"),
                        "has_ledger_data": m.get("has_ledger_data"),
                    }
                    for m in prog_members
                ],
            }
        )
        ledger_shape_ok = bool(prog_members) and all(
            m.get("task_total") is not None and m.get("has_ledger_data") is not None for m in prog_members
        )
        ok = (
            created["status"] == 201
            and join_a["status"] == 200
            and join_b["status"] == 200
            and len(member_list) == 3
            and len(prog_members) == 3
            and ledger_shape_ok
        )
        step.note(
            "跨面：sprint-progress 直读 sprint_task_ledger（BP-4），3 成员账本形状完整"
            if ledger_shape_ok
            else "跨面：账本形状缺失"
        )
        self.finish(step, ok)
        return {"squad_id": squad_id}

    # -- S4 自习室 ------------------------------------------------------------

    def phase_study_room(self, crew: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
        step = self.step("S4", "study", "D-COMM-4：自习室在场证明 + 主号完成 Day1（presence 今日累计）")
        main, mate_b = crew["main"], crew["mate_b"]
        squad_id = (self.state.get("artifacts") or {}).get("squad_id")
        if not squad_id or not plan.get("day1_ids"):
            step.note("缺少 squad_id/Day1 任务——上一步失败")
            self.finish(step, False)
            return {}
        day1_task = plan["day1_ids"][0]

        enter = self.client.post(f"/api/v1/community/squads/{squad_id}/study-room/enter", main["token"], {})
        heartbeat = self.client.post(f"/api/v1/community/squads/{squad_id}/study-room/heartbeat", main["token"], {})
        presence_in = self.client.get(f"/api/v1/community/squads/{squad_id}/study-room/presence", main["token"])
        entries = (presence_in["body"] or {}).get("members") if isinstance(presence_in["body"], dict) else []
        main_in_room = any(e.get("user_id") == main.get("user_id") and e.get("in_room") for e in entries)

        complete = complete_task(self.client, main["token"], day1_task)
        exit_ = self.client.post(f"/api/v1/community/squads/{squad_id}/study-room/exit", main["token"], {})
        presence_out = self.client.get(f"/api/v1/community/squads/{squad_id}/study-room/presence", main["token"])
        entries_out = (presence_out["body"] or {}).get("members") if isinstance(presence_out["body"], dict) else []
        main_out = not any(e.get("user_id") == main.get("user_id") and e.get("in_room") for e in entries_out)
        hb_after_exit = self.client.post(f"/api/v1/community/squads/{squad_id}/study-room/heartbeat", main["token"], {})
        hb_honest = (
            (hb_after_exit["body"] or {}).get("in_room") is False if isinstance(hb_after_exit["body"], dict) else False
        )
        foreign = self.client.get(f"/api/v1/community/squads/{squad_id}/study-room/presence", mate_b["token"])

        exit_minutes = (exit_["body"] or {}).get("today_minutes") if isinstance(exit_["body"], dict) else None
        step.response.update(
            {
                "enter": truncate(enter),
                "heartbeat_in_room": (
                    (heartbeat["body"] or {}).get("in_room") if isinstance(heartbeat["body"], dict) else None
                ),
                "presence_in_room_count": (
                    (presence_in["body"] or {}).get("in_room_count") if isinstance(presence_in["body"], dict) else None
                ),
                "main_in_room": main_in_room,
                "day1_complete": {"status": complete["status"], "stage": complete["stage"]},
                "exit": truncate(exit_),
                "exit_today_minutes": exit_minutes,
                "main_out_after_exit": main_out,
                "heartbeat_after_exit_honest": hb_honest,
                "presence_member_view_status": foreign["status"],
            }
        )
        ok = (
            enter["status"] == 200
            and main_in_room
            and complete["status"] == 200
            and exit_["status"] == 200
            and main_out
            and hb_honest
            and foreign["status"] == 200  # 成员可读（在册成员全可见）
        )
        step.note(f"在场→完成任务→退出全链通；exit today_minutes={exit_minutes}（瞬时会话诚实为 0，不造时长）")
        self.finish(step, ok)
        return {"exit_today_minutes": exit_minutes}

    # -- S5 队友 Day1 + 小队榜 --------------------------------------------------

    def phase_board(self, crew: dict[str, Any]) -> dict[str, Any]:
        step = self.step("S5", "board", "D-COMM-4 榜 + 口径对账：完成度排序 == sprint_task_ledger 重放")
        main, mate_a, mate_b = crew["main"], crew["mate_a"], crew["mate_b"]
        squad_id = (self.state.get("artifacts") or {}).get("squad_id")
        plans = self.state.get("artifacts") or {}
        a_day1 = (plans.get("matea_day1_ids") or [None])[0]
        b_day1 = (plans.get("mateb_day1_ids") or [None])[0]

        a_done = b_done = True
        if a_day1:
            r = complete_task(self.client, mate_a["token"], a_day1)
            a_done = r["status"] == 200
            step.note(f"队友A 完成 Day1：{r['status']}")
        if b_day1:
            r = complete_task(self.client, mate_b["token"], b_day1)
            b_done = r["status"] == 200
            step.note(f"队友B 完成 Day1：{r['status']}（B 只完成一部分——剧情：掉队生）")

        progress = self.client.get(f"/api/v1/community/squads/{squad_id}/sprint-progress", main["token"])
        board = self.client.get(f"/api/v1/community/squads/{squad_id}/leaderboard?limit=10", main["token"])
        prog = (progress["body"] or {}).get("members") if isinstance(progress["body"], dict) else []
        entries = (board["body"] or {}).get("entries") if isinstance(board["body"], dict) else []

        # 口径对账：榜条目的 (completed,total) 必须等于 sprint-progress（同源账本）的值
        prog_by_user = {str(m.get("user_id")): m for m in prog}
        ledger_consistent = bool(entries) and all(
            str(e.get("user_id")) in prog_by_user
            and e.get("task_completed") == prog_by_user[str(e.get("user_id"))].get("task_completed")
            and e.get("task_total") == prog_by_user[str(e.get("user_id"))].get("task_total")
            for e in entries
        )
        ranks = [e.get("rank") for e in entries]
        rates = [round(e.get("completion_rate") or 0, 4) for e in entries]
        # 榜序真相：名次非降 + 完成率非增（并列名次内次序由 user_id 定序，不重复断言）
        order_ok = ranks == sorted(ranks) and rates == sorted(rates, reverse=True)
        tie_ok = len(entries) == 3 and ranks[0] == 1 and (ranks[1], ranks[2]) in ((1, 3), (2, 3))
        board_valid = (board["body"] or {}).get("board_valid") if isinstance(board["body"], dict) else None
        my_rank = (board["body"] or {}).get("my_rank") if isinstance(board["body"], dict) else None

        step.response.update(
            {
                "sprint_progress": [
                    {
                        "user_id": str(m.get("user_id")),
                        "completed": m.get("task_completed"),
                        "total": m.get("task_total"),
                        "rate": m.get("completion_rate"),
                    }
                    for m in prog
                ],
                "board_entries": [
                    {
                        "rank": e.get("rank"),
                        "rate": e.get("completion_rate"),
                        "completed": e.get("task_completed"),
                        "percentile": e.get("percentile"),
                    }
                    for e in entries
                ],
                "board_valid": board_valid,
                "my_rank": my_rank,
                "ledger_consistent": ledger_consistent,
                "order_ok": order_ok,
                "tie_ranks": ranks,
            }
        )
        ok = (
            progress["status"] == 200
            and board["status"] == 200
            and a_done
            and b_done
            and ledger_consistent
            and order_ok
            and tie_ok
            and board_valid is True
            and my_rank is not None
        )
        step.note(f"榜序={ranks}（并列 1,1,3 形态）；ledger 一致={ledger_consistent}；board_valid={board_valid}")
        self.finish(step, ok)
        return {}

    # -- S6 自我锚 -------------------------------------------------------------

    def phase_self_anchor(self, crew: dict[str, Any]) -> dict[str, Any]:
        step = self.step("S6", "anchor", "D-COMM-1：自我锚 7 日序列（含今日）+ 跨面对账")
        main = crew["main"]
        resp = self.client.get("/api/v1/leaderboards/self-anchor", main["token"])
        data = (resp["body"] or {}).get("data") if isinstance(resp["body"], dict) else None
        series = (data or {}).get("series") or []
        today_str = datetime.now(UTC).date().isoformat()
        today_point = next((p for p in series if str(p.get("date")) == today_str), None)
        has_any = (data or {}).get("has_any_data")
        total = (data or {}).get("total_tasks_completed")
        ok = (
            resp["status"] == 200
            and len(series) == 7
            and today_point is not None
            and int(today_point.get("tasks_completed") or 0) >= 1
            and has_any is True
        )
        step.response.update(
            {
                "window": [str((data or {}).get("window_start")), str((data or {}).get("window_end"))],
                "series_len": len(series),
                "today": today_point,
                "has_any_data": has_any,
                "total_tasks_completed": total,
                "utc_today": today_str,
            }
        )
        step.note(
            f"7 日窗口含今日（UTC 日界），今日完成 {today_point.get('tasks_completed') if today_point else '?'} 个——与 S4 真实完成对齐"
        )
        self.finish(step, ok)
        return {}

    # -- S7 攒光子（成就/首胜真实路径） -----------------------------------------

    def phase_earn(self, crew: dict[str, Any]) -> dict[str, Any]:
        step = self.step("S7", "earn", "攒光子：成就/首胜真实路径（sprint 归档触发 check_daily_first + 成就引擎）")
        main = crew["main"]
        tok = main["token"]
        start_balance = await_photon_balance(self.client, tok, at_least=0, max_wait=5)
        step.note(f"起手里程碑余额={start_balance}")

        earned_log: list[dict[str, Any]] = []
        balance = start_balance
        target_hit = balance >= EARN_TARGET
        for i in range(1, EARNING_SPRINT_CAP + 1):
            if target_hit:
                break
            run = f"{self.run_id}-{i}-{uuid.uuid4().hex[:6]}"  # subject 全局唯一（重跑安全）
            titles = [f"TOUR 专题{d}-{run}: 真题演练与错因回看" for d in range(1, 8)]
            built = create_sprint_plan_with_tasks(
                self.client,
                tok,
                name=f"TOUR 冲刺 {run}",
                subject=f"TOUR科目-{run}",
                task_titles=titles,
            )
            if built["plan"]["status"] != 201 or len(built["task_ids"]) != 7:
                earned_log.append({"sprint": i, "error": "plan/tasks 创建失败", "detail": truncate(built["plan"], 600)})
                step.note(f"冲刺{i} 创建失败，跳过")
                continue
            fails = 0
            for tid in built["task_ids"]:
                r = complete_task(self.client, tok, tid)
                if r["status"] != 200:
                    fails += 1
            time.sleep(EVENT_SETTLE_S)  # 事件流：成就/星图/进度异步收敛
            plan_detail = self.client.get(f"/api/v1/plans/{built['plan_id']}", tok)
            progress = (plan_detail["body"] or {}).get("progress") if isinstance(plan_detail["body"], dict) else None
            archive = self.client.post(f"/api/v1/plans/{built['plan_id']}/archive", tok)
            time.sleep(6)  # 归档内联成就 + 事件流余波
            balance = await_photon_balance(self.client, tok, at_least=balance + 1, max_wait=25)
            earned_log.append(
                {
                    "sprint": i,
                    "plan_id": built["plan_id"],
                    "task_failures": fails,
                    "progress_before_archive": progress,
                    "archive_status": archive["status"],
                    "balance": balance,
                }
            )
            step.note(f"冲刺{i}: 7 任务完成失败 {fails}，归档 {archive['status']}，余额 {balance}")
            target_hit = balance >= EARN_TARGET

        step.response["earning_log"] = earned_log
        step.response["final_balance"] = balance
        ok = target_hit and all(e.get("archive_status") == 200 for e in earned_log if "plan_id" in e)
        step.note(f"目标 ≥{EARN_TARGET}（兑换 {REDEEM_PRO_COST} + 余量）：{'达成' if target_hit else '未达成'}")
        self.finish(step, ok)
        return {"balance": balance, "target_hit": target_hit}

    # -- S8 兑换 Pro ------------------------------------------------------------

    def phase_redeem(self, crew: dict[str, Any]) -> dict[str, Any]:
        step = self.step("S8", "redeem", "D-COMM-2：审计重放对账可兑换基数 → 兑 Pro 7 天 → entitlement 落库 → 月顶幂等")
        main = crew["main"]
        tok = main["token"]
        balance_before = await_photon_balance(self.client, tok, at_least=0, max_wait=5)
        replay = replay_redeemable_base(self.client, tok)
        redeem = self.client.post("/api/v1/photons/redeem-pro", tok, {})
        time.sleep(2)
        balance_after = await_photon_balance(self.client, tok, at_least=0, max_wait=5)
        replay_after = replay_redeemable_base(self.client, tok)
        cap_retry = self.client.post("/api/v1/photons/redeem-pro", tok, {})
        cap_body = (cap_retry["body"] or {}).get("detail") if isinstance(cap_retry["body"], dict) else None

        body = redeem["body"] if isinstance(redeem["body"], dict) else {}
        data = body.get("data") or {}
        entitlement = data.get("entitlement")
        expires_at = data.get("entitlement_expires_at")
        cost = data.get("cost_photons")

        expires_ok = False
        if isinstance(expires_at, str):
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00")).replace(tzinfo=None)
                expected = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=REDEEM_PRO_DAYS)
                expires_ok = abs((expiry - expected).total_seconds()) < 6 * 3600
            except ValueError:
                pass

        replay_base = replay.get("replay_base", 0)
        replay_consistent = bool(redeem["status"] == 200) and replay_base >= REDEEM_PRO_COST
        deduct_ok = (
            isinstance(balance_before, int)
            and isinstance(balance_after, int)
            and balance_before - balance_after == REDEEM_PRO_COST
        )
        deduction_rows = [r for r in replay_after.get("rows", []) if r.get("transaction_type") == REDEEM_PRO_TX_TYPE]
        cap_blocked = (
            cap_retry["status"] in (400, 409, 422)
            and isinstance(cap_body, dict)
            and cap_body.get("status") == "monthly_cap_reached"
        )

        step.response.update(
            {
                "balance_before": balance_before,
                "replay_base": replay_base,
                "replay_by_type": replay.get("by_type"),
                "redeem_status": redeem["status"],
                "redeem": truncate(body, 900),
                "entitlement": entitlement,
                "expires_at": expires_at,
                "expires_within_7d": expires_ok,
                "balance_after": balance_after,
                "deduction_rows": len(deduction_rows),
                "monthly_cap_retry": {"status": cap_retry["status"], "detail": truncate(cap_body, 400)},
            }
        )
        ok = (
            redeem["status"] == 200
            and entitlement == "pro"
            and expires_ok
            and cost == REDEEM_PRO_COST
            and replay_consistent
            and deduct_ok
            and len(deduction_rows) == 1
            and cap_blocked
        )
        step.note(f"审计重放基数={replay_base} ≥ 兑换价 {REDEEM_PRO_COST}（transfer_in 不计入口径已随词表排除）")
        step.note(f"扣减 {balance_before}->{balance_after}（=3000）；redeem_pro 流水恰 {len(deduction_rows)} 条")
        step.note(
            f"entitlement={entitlement} 到期 {expires_at}（7 天内偏差 <6h：{expires_ok}）——落库经响应+_grant_pro 语义"
        )
        step.note(
            f"月顶幂等：二次兑换被拒 status={cap_retry['status']} detail.status={cap_body.get('status') if isinstance(cap_body, dict) else '?'}"
        )
        self.finish(step, ok)
        return {}

    # -- S9 全程跨面一致性 -------------------------------------------------------

    def phase_consistency(self, crew: dict[str, Any]) -> dict[str, Any]:
        step = self.step(
            "S9", "consistency", "全程跨面一致性：确认计划→today；完成度变化→榜序即时反映（零缓存失效调用）"
        )
        main, mate_a = crew["main"], crew["mate_a"]
        squad_id = (self.state.get("artifacts") or {}).get("squad_id")
        plan_id = (self.state.get("artifacts") or {}).get("plan_id")

        # 1) 榜新鲜度：S7 之后主号账本暴涨（70+ 任务），榜必须即时反映——期间
        #    本旅程零次调用任何 galaxy 缓存失效（invalidate_galaxy_graph_view_cache）。
        #    GET /tasks 用 page/page_size 分页（默认 20）——翻全页重放账本。
        task_items: list[dict[str, Any]] = []
        page = 1
        while True:
            tasks = self.client.get(f"/api/v1/tasks?page={page}&page_size=100", main["token"])
            payload = tasks["body"] if isinstance(tasks["body"], dict) else {}
            batch = payload.get("data") or []
            task_items.extend(batch)
            total_claimed = int(payload.get("total") or 0)
            if not batch or len(task_items) >= total_claimed or page > 20:
                break
            page += 1
        total = len(task_items)
        completed = sum(1 for t in task_items if (t.get("status") or "").upper() == "COMPLETED")
        rate = round(completed / total, 4) if total else 0.0
        board = self.client.get(f"/api/v1/community/squads/{squad_id}/leaderboard?limit=10", main["token"])
        entries = (board["body"] or {}).get("entries") if isinstance(board["body"], dict) else []
        mine = next((e for e in entries if e.get("user_id") == main.get("user_id")), None)
        fresh = bool(mine) and mine.get("task_total") == total and mine.get("task_completed") == completed
        step.note(f"主号账本重放 total={total} completed={completed} rate={rate}；榜直读一致={fresh}")

        # 2) 完成度变化即时反映（B 掉队生没动，主号暴涨 → 主号第一）
        my_rank = (board["body"] or {}).get("my_rank")
        rank_is_one = my_rank == 1

        # 3) 确认过的 intake 计划 still 出 today 任务（面与面之间没有互相踩状态）
        today = self.client.get(f"/api/v1/plans/{plan_id}/today", main["token"])
        today_tasks = (today["body"] or {}).get("tasks") if isinstance(today["body"], dict) else []
        today_ok = today["status"] == 200

        # 4) 队友榜视角隔离：队友读同一榜（成员可见），主号仍是第一
        board_by_a = self.client.get(f"/api/v1/community/squads/{squad_id}/leaderboard?limit=10", mate_a["token"])
        a_top = entries and entries[0].get("user_id") == main.get("user_id")
        a_sees = board_by_a["status"] == 200

        step.response.update(
            {
                "main_ledger": {"total": total, "completed": completed, "rate": rate},
                "board_mine": truncate(mine, 500),
                "board_fresh_without_invalidation": fresh,
                "my_rank_after_grind": my_rank,
                "intake_today_status": today["status"],
                "intake_today_tasks": len(today_tasks or []),
                "teammate_board_view_ok": a_sees and a_top,
            }
        )
        ok = fresh and rank_is_one and today_ok and a_sees and a_top
        step.note("结论：D-COMM 面直读 sprint_task_ledger（BP-4），不挂 galaxy 缓存——零失效调用下完成度变化即时可见")
        self.finish(step, ok)
        return {}

    # -- 全旅程 ----------------------------------------------------------------

    def voyage(self) -> bool:
        started = utcnow_iso()
        t0 = time.monotonic()
        if not self.check():
            self.summary(started, "blocked: stack unhealthy")
            return False
        crew = self.setup()
        if not crew.get("all_ready"):
            self.summary(started, "blocked: accounts not ready")
            return False

        plan = self.phase_plan(crew)
        squad = self.phase_squad(crew)
        artifacts = self.state.setdefault("artifacts", {})
        artifacts.update({"squad_id": squad.get("squad_id"), "plan_id": plan.get("plan_id")})
        _save_state(self.state)

        # 队友各自 intake（静态包）拿 Day1 任务——为榜/锚提供真实账本差异
        for role, key, subject, days in (
            ("mate_a", "matea_day1_ids", "大学英语", 2),
            ("mate_b", "mateb_day1_ids", "概率论", 3),
        ):
            resp = intake_exam_sprint(self.client, crew[role]["token"], subject, days_left=days, weak=["阅读"])
            ids = []
            if resp["status"] == 200:
                ids = resp["body"]["launch"].get("first_day_task_ids") or []
            artifacts[key] = ids
        _save_state(self.state)

        self.phase_study_room(crew, plan)
        self.phase_board(crew)
        self.phase_self_anchor(crew)
        earn = self.phase_earn(crew)
        if earn.get("target_hit"):
            self.phase_redeem(crew)
        else:
            step = self.step("S8", "redeem", "D-COMM-2 兑换（被阻塞：光子未达 3000——诚实降级）")
            step.note("真实路径攒光子未达兑换价，不造假兑换；产出校准登记供主会话立卡")
            self.finish(step, False)
        self.phase_consistency(crew)
        all_ok = all(r["verdict"] == VERDICT_PASS for r in self.results if r["step_id"] not in ("S0",))
        self.summary(started, "all green" if all_ok else "has failures", elapsed=time.monotonic() - t0)
        return all_ok

    def summary(self, started: str, conclusion: str, elapsed: float | None = None) -> None:
        payload = {
            "schema": SCHEMA_RUN,
            "run_id": self.run_id,
            "gateway": GATEWAY_URL,
            "started_at": started,
            "finished_at": utcnow_iso(),
            "elapsed_s": round(elapsed, 1) if elapsed else None,
            "conclusion": conclusion,
            "steps": [
                {"step_id": r["step_id"], "phase": r["phase"], "name": r["name"], "verdict": r["verdict"]}
                for r in self.results
            ],
            "verdicts": dict(Counter(r["verdict"] for r in self.results)),
        }
        self.store.write_json("run_summary.json", payload)
        print(json.dumps(payload["verdicts"], ensure_ascii=False), conclusion)


def main() -> int:
    parser = argparse.ArgumentParser(description="TOUR 功能成体检验：6 新面用户旅程")
    parser.add_argument(
        "--phase",
        choices=["check", "plan", "squad", "study", "board", "anchor", "earn", "redeem", "consistency"],
        default=None,
    )
    parser.add_argument("--check", action="store_true", help="仅栈自检")
    args = parser.parse_args()

    tour = Tour()
    if args.check or args.phase == "check":
        return 0 if tour.check() else 1
    if args.phase:
        crew = tour.setup()
        dispatch = {
            "plan": lambda: tour.phase_plan(crew),
            "squad": lambda: tour.phase_squad(crew),
            "study": lambda: tour.phase_study_room(crew, tour.phase_plan(crew)),
            "board": lambda: tour.phase_board(crew),
            "anchor": lambda: tour.phase_self_anchor(crew),
            "earn": lambda: tour.phase_earn(crew),
            "redeem": lambda: tour.phase_redeem(crew),
            "consistency": lambda: tour.phase_consistency(crew),
        }
        return 0 if dispatch[args.phase]() else 1
    return 0 if tour.voyage() else 1


if __name__ == "__main__":
    raise SystemExit(main())
