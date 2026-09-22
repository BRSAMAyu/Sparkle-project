"""NORTHSTAR · NS-001 真实驱动适配器（API 级真实闭环，观察/评估专用）。

与 runner.py（contract-simulation 骨架）的关系：本模块**不改产品代码**，只把 NS-001
剧本经真实网关（Go :8080 REST/WS → Python 引擎 gRPC）真实驱动一遍，落证据 JSON。
诚实红线：API 压缩轮（Day0+Day1）永远不能宣称北极星达成——CP-98/99 按冻结规则
一律 unsupported，压缩轮无法覆盖的多日检查点（CP-02/04/05/06/07/08）一律 blocked。

用法（backend/ 下；栈须已在跑，本模块不启任何服务）::

    SECRET_KEY=test python3 -m tests.northstar_eval.real_drive --check            # 栈健康自检
    SECRET_KEY=test python3 -m tests.northstar_eval.real_drive --phase setup     # 建号（主号+对照号）
    SECRET_KEY=test python3 -m tests.northstar_eval.real_drive --phase day0      # 诊断/摸底/计划
    SECRET_KEY=test python3 -m tests.northstar_eval.real_drive --phase day1      # 五段循环
    SECRET_KEY=test python3 -m tests.northstar_eval.real_drive --phase gain      # GP-04/07/03/11 取证
    SECRET_KEY=test python3 -m tests.northstar_eval.real_drive --phase report    # 汇总 run_summary.json

配置注入：NORTHSTAR_GATEWAY_URL（默认 http://localhost:8080）、NORTHSTAR_OUT_DIR
（默认 <repo>/v3-output/NORTHSTAR-LOOP1）。账号凭据只落 /tmp 运行态（600），
证据里凭据只以 sha256 前缀出现；不落任何真实密钥。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import string
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
import websocket

SCHEMA_STEP = "sparkle.northstar.real-drive.step.v1"
SCHEMA_RUN = "sparkle.northstar.real-drive.run.v1"
SCHEMA_GAIN = "sparkle.northstar.real-drive.gain-proof.v1"

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_BLOCKED = "blocked"
VERDICTS = (VERDICT_PASS, VERDICT_FAIL, VERDICT_BLOCKED)

#: 压缩轮 11 检查点（CP-00..CP-08 冻结词表 + CP-98/99 诚实降级），与 journey_schema 一致。
CHECKPOINT_API_SUPPORTED = tuple(
    text
    for text in (
        "CP-00 baseline recorded and syllabus mapped",
        "CP-01 plan targets weakest exam-weighted nodes with human confirmation",
        "CP-02 quiz score trajectory non-decreasing",
        "CP-03 mistakes fully land in error book with mastery sync",
        "CP-04 next-day plan adapts to previous outcome",
        "CP-05 review hit rate at or above threshold",
        "CP-06 weighted coverage at or above threshold by last study day",
        "CP-07 posttest gain at or above MDE",
        "CP-08 forgetting rate at or below threshold",
    )
)
CHECKPOINT_ALWAYS_UNSUPPORTED = (
    "CP-98 daily cognitive load self-report",
    "CP-99 full mock exam wall clock at or below budget",
)
CHECKPOINT_API_VOCAB = CHECKPOINT_API_SUPPORTED + CHECKPOINT_ALWAYS_UNSUPPORTED

#: 压缩轮（Day0+Day1）内不可判定的多日检查点 → 一律 blocked（诚实降级，不折算 pass）。
COMPRESSED_ROUND_BLOCKED = (
    "CP-02 quiz score trajectory non-decreasing",  # 需 ≥3 日滑动窗，本轮仅 1 个 quiz 点
    "CP-04 next-day plan adapts to previous outcome",  # 需次日计划对照，本轮无 Day2
    "CP-05 review hit rate at or above threshold",  # 需重测首答对率；本轮仅拉取复习队列无作答
    "CP-06 weighted coverage at or above threshold by last study day",  # 需 Day6 末
    "CP-07 posttest gain at or above MDE",  # 需 Day7 模拟考
    "CP-08 forgetting rate at or below threshold",  # 需 Day10 重测
)

WS_MESSAGE_BUDGET = 24  # 全轮真实 LLM 消息硬上限（费用护栏，Qwen 压缩轮足够）
WS_RECV_TIMEOUT_S = 60.0  # 单条消息等待上限（纪律：≤60s）
REST_TIMEOUT_S = 30.0
TOKEN_REFRESH_MARGIN_S = 120.0  # token 30min 过期，留 2min 余量主动重登

DEFAULT_GATEWAY_URL = os.environ.get("NORTHSTAR_GATEWAY_URL", "http://localhost:8080")
USERNAME_PREFIX = "northstar_ns001_"
CONTROL_USERNAME_PREFIX = "northstar_ns001_ctrl_"
STATE_PATH = Path("/tmp/northstar_ns001_real_drive_state.json")


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_prefix(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def truncate_text(value: Any, limit: int = 6000) -> Any:
    """证据落盘截断（保结构：dict/list 递归字符串化后截断）。"""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
        if len(text) <= limit:
            return value
        return {"_truncated": True, "_preview": text[:limit]}
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"...[truncated {len(value)}->{limit}]"
    return value


def redact(payload: dict[str, Any], keys: tuple[str, ...] = ("password", "refresh_token", "access_token")) -> dict[str, Any]:
    """证据中的敏感字段替换为 sha256 前缀（测试凭据也不明文落盘）。"""
    out = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    for key in keys:
        if isinstance(out, dict) and key in out and isinstance(out[key], str):
            out[key] = f"sha256:{sha256_prefix(out[key])}"
    return out


@dataclass
class StepEvidence:
    """单步证据（schema 精神沿用 runner.write_evidence：稳定键 + provenance + verdict）。"""

    run_id: str
    step_id: str
    phase: str
    name: str
    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    verdict: str = VERDICT_BLOCKED
    checkpoints: tuple[str, ...] = ()
    notes: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=utcnow_iso)
    finished_at: str = ""

    def finish(self, verdict: str, notes: list[str] | None = None) -> "StepEvidence":
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
            "checkpoints": list(self.checkpoints),
            "notes": list(self.notes),
        }


class EvidenceStore:
    """证据落盘：out/evidence/steps/*.json + out/evidence/gp-*.json（逐文件稳定 schema）。"""

    def __init__(self, out_dir: Path, run_id: str) -> None:
        self.out_dir = out_dir
        self.run_id = run_id
        self.steps_dir = out_dir / "evidence" / "steps"
        self.steps_dir.mkdir(parents=True, exist_ok=True)

    def write_step(self, step: StepEvidence) -> Path:
        path = self.steps_dir / f"{step.step_id}_{_slug(step.name)}.json"
        path.write_text(json.dumps(step.to_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_gain(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.out_dir / "evidence" / f"gp-{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_json(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.out_dir / "evidence" / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-")[:60]


# ---------------------------------------------------------------------------
# REST 客户端（自动重登：token 30min 过期）
# ---------------------------------------------------------------------------


class GatewayClient:
    """网关 REST 客户端；多账号各自持 token，401/过期自动用账号密码重登。"""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = requests.Session()
        self.tokens: dict[str, dict[str, Any]] = {}  # username -> {access_token, issued_monotonic}

    def health(self) -> tuple[bool, str]:
        try:
            resp = self.http.get(f"{self.base_url}/healthz", timeout=5)
            return resp.ok, f"healthz={resp.status_code} {resp.text[:120]}"
        except Exception as exc:  # noqa: BLE001 — 探针要的是可读错误
            return False, f"healthz unreachable: {exc}"

    # -- auth ---------------------------------------------------------------

    def register(self, username: str, email: str, password: str) -> dict[str, Any]:
        body = {
            "username": username,
            "email": email,
            "password": password,
            "nickname": username,
            "accepted_tos": True,
            "accepted_privacy": True,
            "tos_version": "v1",
            "privacy_version": "v1",
        }
        resp = self.http.post(f"{self.base_url}/api/v1/auth/register", json=body, timeout=REST_TIMEOUT_S)
        data = _safe_json(resp)
        if resp.status_code < 300:
            self._store_token(username, data)
        return {"status": resp.status_code, "body": data}

    def login(self, username: str, password: str) -> dict[str, Any]:
        resp = self.http.post(
            f"{self.base_url}/api/v1/auth/login", json={"username": username, "password": password}, timeout=REST_TIMEOUT_S
        )
        data = _safe_json(resp)
        if resp.status_code < 300:
            self._store_token(username, data)
        return {"status": resp.status_code, "body": data}

    def _store_token(self, username: str, data: dict[str, Any]) -> None:
        token = data.get("access_token") or data.get("token")
        if token:
            self.tokens[username] = {"access_token": str(token), "issued": time.monotonic()}

    def ensure_login(self, username: str, password: str | None = None) -> None:
        """新进程内存无 token → 先登录（密码取 /tmp 运行态）。"""
        info = self.tokens.get(username)
        if info and time.monotonic() - info["issued"] < 25 * 60:
            return
        if password:
            self.login(username, password)

    # -- authorized request --------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        username: str,
        password: str | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: float = REST_TIMEOUT_S,
    ) -> dict[str, Any]:
        token_info = self.tokens.get(username)
        if token_info and time.monotonic() - token_info["issued"] > 25 * 60:
            token_info = None  # 主动过期（30min 窗口留余量）
        if not token_info and password:
            self.login(username, password)
        token_info = self.tokens.get(username)
        headers = {"Authorization": f"Bearer {token_info['access_token']}"} if token_info else {}
        resp = self.http.request(
            method, f"{self.base_url}{path}", json=json_body, headers=headers, timeout=timeout
        )
        if resp.status_code == 401 and password:  # 过期/失效 → 重登重试一次
            self.login(username, password)
            token_info = self.tokens.get(username)
            if token_info:
                headers = {"Authorization": f"Bearer {token_info['access_token']}"}
                resp = self.http.request(method, f"{self.base_url}{path}", json=json_body, headers=headers, timeout=timeout)
        return {"status": resp.status_code, "body": _safe_json(resp)}

    def ws_url(self, username: str) -> str:
        token_info = self.tokens.get(username)
        if not token_info:
            raise RuntimeError(f"no token for {username}; login first")
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_base}/ws/chat?token={token_info['access_token']}"


def _safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"_raw": resp.text[:2000]}


# ---------------------------------------------------------------------------
# WS chat 客户端（真实 LLM 链路 /ws/chat）
# ---------------------------------------------------------------------------


class WSChatSession:
    """持久 WS 会话：同 account 同 session_id 多轮；事件聚合 delta→full_text。"""

    def __init__(self, client: GatewayClient, username: str) -> None:
        self.client = client
        self.username = username
        self.session_id = f"ns001-{uuid.uuid4().hex[:12]}"
        self.conn: websocket.WebSocket | None = None
        self.messages_sent = 0

    def _connect(self) -> None:
        self.conn = websocket.create_connection(
            self.client.ws_url(self.username), timeout=WS_RECV_TIMEOUT_S, enable_multithread=True
        )

    def _ensure(self) -> None:
        if self.conn is None:
            self._connect()

    def close(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:  # noqa: BLE001
                pass
            self.conn = None

    def send_message(self, text: str, deadline_s: float = WS_RECV_TIMEOUT_S) -> dict[str, Any]:
        """发一条聊天消息，聚合事件流到 full_text。诚实契约：超时/错误原样返回不美化。

        P1-3（BP-3 复盘）修订的终止与归因语义：
        - ``usage`` 是引擎逐跳计量事件（网关据其在流内做配额分段），不是回合
          终止；本回合真正的终止帧是本 request_id 的 ``full_text`` / ``error``，
          或网关流末尾必发的 ``meta``（合成 ``done`` 视上游 finish_reason 而定）。
        - 网关 WS 读泵按连接串行处理消息：上一回合未结束时新消息排队，上一回
          合的残帧（含其 final full_text）会先于本回合 ack 到达。所有帧都带
          request_id，本循环按其归因：非本请求的帧与 ack 前到达的无主帧一律
          计入 ``stale_*`` 排干，不参与答案聚合——否则会把上一回合的答案误记
          为本回合答案（LOOP1 C2/C3「99.5% 重放」假象的根因）。
        """
        self._ensure()
        assert self.conn is not None
        self.messages_sent += 1
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        payload = {"type": "message", "message": text, "session_id": self.session_id, "request_id": request_id}
        self.conn.send(json.dumps(payload, ensure_ascii=False))
        deltas: list[str] = []
        event_types: Counter[str] = Counter()
        citations: list[dict[str, Any]] = []
        tool_calls: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        full_text = ""
        own_turn_started = False  # 已见到本请求的 ack/message_ack
        stale_frames = 0
        while True:
            remaining = deadline_s - (time.monotonic() - started)
            if remaining <= 0:
                errors.append({"error_code": "client_deadline", "message": f"exceeded {deadline_s}s budget"})
                break
            self.conn.settimeout(remaining)
            try:
                raw = self.conn.recv()
            except websocket.WebSocketTimeoutException:
                errors.append({"error_code": "recv_timeout", "message": f"no terminal event within {deadline_s}s"})
                break
            except Exception as exc:  # noqa: BLE001
                errors.append({"error_code": "ws_error", "message": repr(exc)})
                break
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if "payload" in event and isinstance(event["payload"], dict):
                event = event["payload"]
            etype = str(event.get("type", ""))
            frame_rid = str(event.get("request_id", "") or "")
            # request_id 归因：带他人 rid 的帧、以及 ack 之前到达的无主帧，
            # 只可能是同连接上一回合的残帧——排干并显式计数。
            if (frame_rid and frame_rid != request_id) or (not frame_rid and not own_turn_started):
                stale_frames += 1
                event_types[f"stale_{etype or '(none)'}"] += 1
                continue
            if etype in ("ack", "message_ack"):
                own_turn_started = True
                event_types[etype] += 1
                continue
            event_types[etype or "(none)"] += 1
            if etype == "delta":
                deltas.append(str(event.get("delta", "")))
            elif etype == "full_text":
                # 语义与网关持久化一致：后到的 full_text 覆盖前者（last wins）。
                full_text = str(event.get("full_text", ""))
            elif etype == "citations":
                citations.extend(event.get("citations", []) or [])
            elif etype == "tool_call":
                tool_calls.append(event.get("tool_call", {}))
            elif etype in ("error", "message_nack", "nack"):
                errors.append(event.get("error") or event)
                break
            elif etype in ("meta", "done"):
                # 网关在引擎流 EOF 后必发 meta：真正的回合终止。缺 full_text
                # 时降级用 delta 聚合（原降级路径，现正确锚定在回合末尾）。
                if not full_text and deltas:
                    full_text = "".join(deltas)
                break
            # usage / status_update / metadata / tool_result 等为过程帧：只计数。
        return {
            "full_text": full_text or "".join(deltas),
            "delta_events": event_types.get("delta", 0),
            "event_types": dict(event_types),
            "citations": citations[:10],
            "tool_calls": tool_calls[:5],
            "errors": errors,
            "elapsed_s": round(time.monotonic() - started, 2),
            "request_id": request_id,
            "session_id": self.session_id,
            "stale_frames_drained": stale_frames,
        }


# ---------------------------------------------------------------------------
# 判定辅助（诚实启发式：全部标注 heuristic，需人工复核）
# ---------------------------------------------------------------------------

MEMORY_RECALL_MARKERS = (
    "上次", "之前", "你提到", "你说过", "刚才", "前面", "上次说", "记得", "之前说", "你之前",
)
#: 反记忆指称：出现即判「未复用记忆」（防关键词误报——「记得」出现在「只记得你刚完成…」里）。
MEMORY_ANTI_RECALL_MARKERS = (
    "没有完整记录", "没有记录", "不记得", "无法记录", "未记录", "这里没有", "我这里没有", "不掌握",
    "没有你", "无法获取", "无法查看", "看不到",
)
CORRECTION_TOPIC_MARKERS = ("偶数", "度数", "连通", "欧拉")
PERSONALIZATION_MARKERS = ("你", "你的", "图论", "弱", "掌握", "欧拉", "哈密顿", "离散")


def judge_memory_recall(correction_exchange_text: str, followup_text: str) -> tuple[str, list[str]]:
    """GP-07 启发式判定：后续回答是否真实复用了纠正记忆。

    反记忆指称（「没有完整记录」等）一票否决 → fail：这类句式里「记得/你提到」
    只是让步从句，语义是失忆。返回 (verdict, markers_found)。只产 heuristic 证据。
    """
    if not followup_text:
        return VERDICT_BLOCKED, []
    lowered = followup_text.lower()
    anti = [m for m in MEMORY_ANTI_RECALL_MARKERS if m in followup_text]
    topic = [m for m in CORRECTION_TOPIC_MARKERS if m in followup_text or m in lowered]
    if anti:
        return VERDICT_FAIL, anti + topic
    recall = [m for m in MEMORY_RECALL_MARKERS if m in followup_text]
    if correction_exchange_text and recall and len(topic) >= 2:
        return VERDICT_PASS, recall + topic
    if len(topic) >= 2:
        return VERDICT_BLOCKED, topic  # 主题对上了但无记忆指称 → 记忆复用未证明
    return VERDICT_FAIL, topic


def judge_personalization(answer_text: str) -> tuple[str, list[str]]:
    """GP-04 压缩轮代理判定：回答是否体现用户私有上下文（非通用百科回答）。

    反记忆指称一票否决（系统自述「没有完整记录」= 私有上下文未进入回答）。
    """
    if not answer_text:
        return VERDICT_BLOCKED, []
    anti = [m for m in MEMORY_ANTI_RECALL_MARKERS if m in answer_text]
    if anti:
        return VERDICT_FAIL, anti
    found = [m for m in PERSONALIZATION_MARKERS if m in answer_text]
    if len(found) >= 3:
        return VERDICT_PASS, found
    if found:
        return VERDICT_BLOCKED, found
    return VERDICT_FAIL, found


def diff_galaxy_nodes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """GP-03：两次 galaxy graph 快照的节点级对账（新增/ mastery 变化）。"""
    bmap = _node_map(before)
    amap = _node_map(after)
    added = sorted(set(amap) - set(bmap))
    changed: dict[str, dict[str, float]] = {}
    for node_id, astat in amap.items():
        bstat = bmap.get(node_id)
        if bstat and abs(astat["mastery"] - bstat["mastery"]) > 1e-6:
            changed[node_id] = {"before": bstat["mastery"], "after": astat["mastery"]}
    return {"added_nodes": added, "mastery_changes": changed, "before_count": len(bmap), "after_count": len(amap)}


def _node_map(graph: dict[str, Any]) -> dict[str, dict[str, float]]:
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    if nodes is None and isinstance(graph, dict):
        nodes = (graph.get("data") or {}).get("nodes") if isinstance(graph.get("data"), dict) else None
    out: dict[str, dict[str, float]] = {}
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or node.get("node_id") or node.get("name"))
        user_status = node.get("user_status") or {}
        mastery = node.get("mastery", node.get("mastery_level"))
        if mastery is None:
            mastery = user_status.get("mastery_score", 0.0) if isinstance(user_status, dict) else 0.0
        try:
            mastery_f = float(mastery)
        except (TypeError, ValueError):
            mastery_f = 0.0
        out[node_id] = {"mastery": mastery_f}
    return out


def galaxy_state_summary(graph: dict[str, Any]) -> dict[str, Any]:
    """星图状态摘要（user_stats + 节点 learning_state 分布 + 已解锁节点明细）。"""
    nodes = (graph.get("nodes") or []) if isinstance(graph, dict) else []
    states: Counter = Counter(str(n.get("learning_state")) for n in nodes if isinstance(n, dict))
    unlocked = [
        {
            "id": n.get("id"),
            "name": n.get("name"),
            "learning_state": n.get("learning_state"),
            "mastery_score": ((n.get("user_status") or {}).get("mastery_score")) if isinstance(n.get("user_status"), dict) else None,
            "study_minutes": ((n.get("user_status") or {}).get("total_study_minutes")) if isinstance(n.get("user_status"), dict) else None,
        }
        for n in nodes
        if isinstance(n, dict) and isinstance(n.get("user_status"), dict) and n["user_status"].get("is_unlocked")
    ]
    return {
        "user_stats": graph.get("user_stats") if isinstance(graph, dict) else None,
        "learning_state_distribution": dict(states),
        "unlocked_nodes": unlocked,
    }


# ---------------------------------------------------------------------------
# 运行态（/tmp，600；凭据不进 git）
# ---------------------------------------------------------------------------


@dataclass
class RunState:
    run_id: str
    gateway_url: str
    main_username: str = ""
    main_password: str = ""
    main_email: str = ""
    control_username: str = ""
    control_password: str = ""
    control_email: str = ""
    main_user_id: str = ""
    day0_session_id: str = ""
    exam_date: str = ""
    diagnostic_id: str = ""
    plan_id: str = ""
    recommended_task_id: str = ""
    task_id: str = ""
    goal_created: bool = False
    diagnostic_attempted: bool = False
    llm_messages_sent: int = 0
    evidence_step_ids: list[str] = field(default_factory=list)

    @staticmethod
    def load_or_create(gateway_url: str) -> "RunState":
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return RunState(**data)
        state = RunState(
            run_id=f"NS001-LOOP1-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}", gateway_url=gateway_url
        )
        state.save()
        return state

    def save(self) -> None:
        STATE_PATH.write_text(json.dumps(self.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            STATE_PATH.chmod(0o600)
        except OSError:
            pass


def gen_password() -> str:
    """强随机密码（字母+数字+符号，18 字符；只在 /tmp 运行态出现）。"""
    pool = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(pool) for _ in range(18))


# ---------------------------------------------------------------------------
# Driver：剧本步进器
# ---------------------------------------------------------------------------


class NS001Driver:
    def __init__(self, gateway_url: str, out_dir: Path) -> None:
        self.gateway_url = gateway_url
        self.out_dir = out_dir
        self.state = RunState.load_or_create(gateway_url)
        self.store = EvidenceStore(out_dir, self.state.run_id)
        self.client = GatewayClient(gateway_url)
        self.ws_budget_left = WS_MESSAGE_BUDGET
        self._chat: dict[str, WSChatSession] = {}

    # -- infra ---------------------------------------------------------------

    def _step(self, step_id: str, phase: str, name: str, checkpoints: tuple[str, ...] = ()) -> StepEvidence:
        return StepEvidence(
            run_id=self.state.run_id, step_id=step_id, phase=phase, name=name, checkpoints=checkpoints
        )

    def _rest_step(
        self,
        step_id: str,
        phase: str,
        name: str,
        method: str,
        path: str,
        username: str = "",
        password: str | None = None,
        json_body: dict[str, Any] | None = None,
        checkpoints: tuple[str, ...] = (),
        expect_status: tuple[int, ...] = (200,),
        notes_on_fail: str | None = None,
        timeout: float = REST_TIMEOUT_S,
    ) -> tuple[StepEvidence, dict[str, Any]]:
        """REST 调用 + 证据落盘一步完成。"""
        step = self._step(step_id, phase, name, checkpoints)
        step.request = {"method": method, "path": path, "body": truncate_text(redact(json_body or {}), 4000)}
        account = username or self.state.main_username
        try:
            result = self.client.request(method, path, account, password, json_body, timeout=timeout)
        except requests.RequestException as exc:
            step.finish(VERDICT_BLOCKED, [f"transport error: {exc!r}"])
            step.response = {"status": None, "body": {"_error": repr(exc)}}
            self.store.write_step(step)
            return step, {}
        step.response = {"status": result["status"], "body": truncate_text(result["body"], 8000)}
        ok = result["status"] in expect_status
        step.finish(
            VERDICT_PASS if ok else VERDICT_FAIL,
            [] if ok else [notes_on_fail or f"unexpected status {result['status']}"],
        )
        self.store.write_step(step)
        body = result["body"]
        return step, body if isinstance(body, dict) else {"_raw": body, "_is_list": isinstance(body, list)}

    def chat(self, username: str, password: str, text: str) -> dict[str, Any]:
        """真实 LLM 对话（WS）；预算护栏 + 60s 上限。"""
        if self.ws_budget_left <= 0:
            return {"full_text": "", "errors": [{"error_code": "budget_exhausted"}], "event_types": {}, "delta_events": 0}
        self.ws_budget_left -= 1
        self.state.llm_messages_sent += 1
        self.state.save()
        password = self.state.main_password if username == self.state.main_username else self.state.control_password
        self.client.ensure_login(username, password)
        session = self._chat.get(username)
        if session is None:
            session = WSChatSession(self.client, username)
            self._chat[username] = session
        try:
            return session.send_message(text)
        except Exception as exc:  # noqa: BLE001 — 连接级故障原样返回
            session.close()
            self._chat.pop(username, None)
            return {"full_text": "", "errors": [{"error_code": "ws_connect_or_send", "message": repr(exc)}], "event_types": {}}

    def _chat_step(
        self, step_id: str, phase: str, name: str, username: str, password: str, text: str, checkpoints: tuple[str, ...] = ()
    ) -> tuple[StepEvidence, dict[str, Any]]:
        step = self._step(step_id, phase, name, checkpoints)
        step.request = {"ws": "/ws/chat", "username_sha": sha256_prefix(username), "message": truncate_text(text, 4000)}
        result = self.chat(username, password, text)
        step.response = {
            "full_text": truncate_text(result.get("full_text", ""), 8000),
            "event_types": result.get("event_types", {}),
            "citations": result.get("citations", [])[:5],
            "errors": result.get("errors", []),
            "elapsed_s": result.get("elapsed_s"),
            "session_id": result.get("session_id"),
            "llm_messages_budget_left": self.ws_budget_left,
        }
        ok = bool(result.get("full_text")) and not result.get("errors")
        step.finish(VERDICT_PASS if ok else VERDICT_BLOCKED, [] if ok else [f"chat errors: {result.get('errors')}"])
        self.store.write_step(step)
        return step, result

    # -- phases ----------------------------------------------------------------

    def phase_check(self) -> int:
        ok, detail = self.client.health()
        print(f"[{'OK' if ok else 'FAIL'}] gateway: {detail}")
        engine_host = self.gateway_url.split("//", 1)[-1].split(":")[0]
        for port in (50051,):
            sock = socket.socket()
            sock.settimeout(3)
            try:
                sock.connect((engine_host, port))
                print(f"[OK] engine tcp {port} open")
            except OSError as exc:
                print(f"[FAIL] engine tcp {port}: {exc}")
            finally:
                sock.close()
        return 0 if ok else 1

    def phase_setup(self) -> None:
        main_user = f"{USERNAME_PREFIX}{secrets.token_hex(4)}"
        main_pwd = gen_password()
        control_user = f"{CONTROL_USERNAME_PREFIX}{secrets.token_hex(4)}"
        control_pwd = gen_password()
        step = self._step("A1", "setup", "register main account", ("CP-00",))
        reg = self.client.register(main_user, f"{main_user}@example.com", main_pwd)
        step.request = {"path": "/api/v1/auth/register", "username": main_user, "password_sha": sha256_prefix(main_pwd)}
        step.response = {"status": reg["status"], "keys": sorted(reg["body"]) if isinstance(reg["body"], dict) else None}
        if reg["status"] < 300:
            user = reg["body"].get("user", {})
            self.state.main_user_id = str(user.get("id", ""))
            self.state.main_username, self.state.main_password = main_user, main_pwd
            self.state.main_email = f"{main_user}@example.com"
            step.finish(VERDICT_PASS, [f"user_id={self.state.main_user_id}"])
        else:
            step.finish(VERDICT_FAIL, [f"register status {reg['status']}"])
        self.store.write_step(step)

        step2 = self._step("A2", "setup", "register control account (GP-04 blind arm)")
        reg2 = self.client.register(control_user, f"{control_user}@example.com", control_pwd)
        step2.request = {"path": "/api/v1/auth/register", "username": control_user, "password_sha": sha256_prefix(control_pwd)}
        step2.response = {"status": reg2["status"], "keys": sorted(reg2["body"]) if isinstance(reg2["body"], dict) else None}
        if reg2["status"] < 300:
            self.state.control_username, self.state.control_password = control_user, control_pwd
            self.state.control_email = f"{control_user}@example.com"
            step2.finish(VERDICT_PASS)
        else:
            step2.finish(VERDICT_FAIL, [f"register status {reg2['status']}"])
        self.store.write_step(step2)

        # exam date: 今天 + 7 天（NS-001 冻结约束「还有 7 天」）
        self.state.exam_date = (datetime.now(UTC).date() + timedelta(days=7)).isoformat()
        self.state.evidence_step_ids.extend(["A1", "A2"])
        self.state.save()

    def _require_main(self) -> tuple[str, str]:
        if not self.state.main_username:
            raise SystemExit("no main account in run state — run --phase setup first")
        return self.state.main_username, self.state.main_password

    def phase_day0(self) -> None:
        username, password = self._require_main()
        day0_text = (
            "你好，我要开始备考：离散数学期末考试在 7 天后（闭卷，100 分卷）。我的情况："
            "自评当前掌握度大约 42/100；最薄弱的章是图论（CH4）；"
            "一个具体的困惑：我总是分不清欧拉回路和哈密顿回路的判定条件，考试肯定考。"
            "我每天只能投入 165 分钟。请帮我建立目标并给我冲刺计划。"
        )
        # B1 onboarding chat（幂等：已成功过则跳过，防复跑双烧 LLM）
        if self.state.day0_session_id:
            print(f"[skip] B1 already done: session={self.state.day0_session_id}")
        else:
            _, chat_result = self._chat_step(
                "B1", "day0", "onboarding diagnostic chat", username, password, day0_text, ("CP-00", "CP-01")
            )
            self.state.day0_session_id = chat_result.get("session_id", "")
            self.state.save()

        # B2 goal（幂等：已有 plan_id 则跳过重建，避免复跑重复建档）
        if self.state.plan_id:
            print(f"[skip] B2/B3 already done: plan_id={self.state.plan_id}")
        else:
            goal_body = {
                "goal_type": "exam",
                "title": "离散数学期末 7 天冲刺：及格冲 70+",
                "motivation": "一周后期末考，目标及格并冲击 70+",
                "time_horizon": "short",
                "description": "NS-001 北极星压缩轮；考试日 " + self.state.exam_date,
                "target_date": self.state.exam_date,
            }
            self._rest_step(
                "B2", "day0", "create goal", "POST", "/api/v1/goals/", username, password, goal_body, ("CP-01",)
            )

            # B3 exam-sprint intake（7 天 backbone）
            intake_body = {
                "subject": "离散数学",
                "exam_date": self.state.exam_date,
                "target_mode": "pass",
                "scope_context": {"text": "闭卷 100 分卷；覆盖 CH1 数理逻辑/CH2 集合与关系/CH3 函数与基数/CH4 图论/CH5 组合数学/CH6 代数系统"},
                "baseline": {"current_level": 42, "weak_chapters": ["CH4 图论", "图论"]},
                "daily_study_minutes": 165,
                "conversation_id": self.state.day0_session_id or None,
            }
            _, intake_resp = self._rest_step(
                "B3", "day0", "exam-sprint intake (7-day backbone)", "POST", "/api/v1/exam-sprint/intake",
                username, password, intake_body, ("CP-00", "CP-01"), timeout=WS_RECV_TIMEOUT_S,
            )
            launch = intake_resp.get("launch") if isinstance(intake_resp, dict) else {}
            if isinstance(launch, dict):
                self.state.plan_id = str(launch.get("plan_id", "") or "")
                self.state.recommended_task_id = str(launch.get("recommended_task_id", "") or "")
                self.state.save()
            if not self.state.plan_id:
                # B3r 恢复路径：intake 非幂等（复跑 403）→ 从活跃计划恢复锚点
                _, active = self._rest_step(
                    "B3r", "day0", "recover plan anchor via GET /plans/active (intake 403 recovery)",
                    "GET", "/api/v1/plans/active", username, password,
                )
                if isinstance(active, dict):
                    plan = active.get("plan") or active.get("data") or active
                    if isinstance(plan, dict):
                        self.state.plan_id = str(plan.get("id") or plan.get("plan_id") or "")
                        self.state.recommended_task_id = str(plan.get("recommended_task_id", "") or "")
                        self.state.save()

        # B4 摸底卷生成（question_count 上限 15，SCENARIO 24 题受 API 合同约束 → 记录偏差）
        if self.state.diagnostic_attempted:
            print("[skip] B4/B5 already attempted this account (diagnostic_attempted=true)")
            questions, diag_resp = [], {}
        else:
            diag_body = {"subject": "离散数学", "question_count": 15, "days_left": 7, "pass_score": 60.0}
            _, diag_resp = self._rest_step(
                "B4", "day0", "diagnostic generate (pretest)", "POST", "/api/v1/exam-sprint/diagnose/generate",
                username, password, diag_body, ("CP-00",), timeout=WS_RECV_TIMEOUT_S,
            )
            questions = diag_resp.get("questions", []) if isinstance(diag_resp, dict) else []
            self.state.diagnostic_id = str(diag_resp.get("diagnostic_id", "")) if isinstance(diag_resp, dict) else ""
            self.state.diagnostic_attempted = True
            self.state.save()

        # B5 判卷：确定性人设作答（图论链题故意选非常识选项 → 弱点暴露；其余选首选项）。
        # B4 失败（科目题包缺失）时级联跳过：级联失败不再是独立断点。
        answers: list[dict[str, Any]] = []
        for index, question in enumerate(questions):
            linked = [str(n) for n in (question.get("linked_node_names") or []) + (question.get("linked_node_slugs") or [])]
            is_graph = any(("图" in item or "graph" in item.lower()) for item in linked)
            choices = question.get("choices") or []
            if is_graph:
                answer_text = choices[2] if len(choices) > 2 else (choices[-1] if choices else "不确定")
            else:
                answer_text = choices[0] if choices else "不确定"
            answers.append(
                {
                    "question_id": str(question.get("question_id", "")),
                    "answer": answer_text,
                    "confidence": "FUZZY",
                    "elapsed_seconds": 45,
                }
            )
        if not answers:
            step_skip = self._step("B5", "day0", "diagnostic grade (skipped: B4 produced 0 questions)", ("CP-00",))
            step_skip.response = {"status": None, "body": {"cascade": "B4 422 subject pack missing; nothing to grade"}}
            step_skip.finish(VERDICT_BLOCKED, ["cascade of B4: diagnostic pack for 离散数学 not built in"])
            self.store.write_step(step_skip)
            grade_resp: dict[str, Any] = {}
        else:
            grade_body = {
                "subject": "离散数学",
                "answers": answers,
                "days_left": 7,
                "pass_score": 60.0,
                "update_galaxy": True,
            }
            if self.state.diagnostic_id:
                grade_body["diagnostic_id"] = self.state.diagnostic_id
            _, grade_resp = self._rest_step(
                "B5", "day0", "diagnostic grade (persona: graph-theory weak)", "POST", "/api/v1/exam-sprint/diagnose/grade",
                username, password, grade_body, ("CP-00",), timeout=WS_RECV_TIMEOUT_S,
            )

        # B6 galaxy 基线快照（GP-03/GP-11 before）
        _, graph_before = self._rest_step(
            "B6", "day0", "galaxy graph snapshot (before Day1)", "GET", "/api/v1/galaxy/graph", username, password
        )
        self.store.write_json("snapshot-galaxy-before-day1.json", {"schema": SCHEMA_RUN, "snapshot": graph_before, "at": utcnow_iso()})

        # B7 profile 基线快照（GP-11 before）
        _, profile_before = self._rest_step(
            "B7", "day0", "profile snapshot (before Day1)", "GET", "/api/v1/profile/transparent", username, password
        )
        self.store.write_json("snapshot-profile-before-day1.json", {"schema": SCHEMA_RUN, "snapshot": profile_before, "at": utcnow_iso()})
        self.state.evidence_step_ids.extend(["B1", "B2", "B3", "B4", "B5", "B6", "B7"])
        self.state.save()

    def phase_day1(self) -> None:
        username, password = self._require_main()

        # C1 段1 计划：今日卡
        _, today_resp = self._rest_step(
            "C1", "day1", "today cockpit task cards", "GET", "/api/v1/tasks/today", username, password, None, ("CP-04",)
        )
        tasks = today_resp.get("_raw") if isinstance(today_resp, dict) and "_raw" in today_resp else (
            today_resp if isinstance(today_resp, list) else (today_resp.get("data") or today_resp.get("tasks") or [])
        )
        task_id = ""
        if isinstance(tasks, list) and tasks:
            # 优先完成 intake 推荐任务（真实计划链路），否则取第一张卡
            recommended = self.state.recommended_task_id
            for item in tasks:
                candidate = str(item.get("id") or item.get("task_id") or "")
                if recommended and candidate == recommended:
                    task_id = candidate
                    break
            if not task_id:
                task_id = str(tasks[0].get("id") or tasks[0].get("task_id") or "")
        if not task_id:
            # 引擎未自动生成当日卡 → 手建一张（记录为断点证据：计划→任务链路断裂）
            create_body = {
                "title": "Day1 数理逻辑 I：命题逻辑复习 + 图论弱点预习",
                "type": "review",
                "tags": ["NS-001", "day1", "discrete-math"],
                "estimated_minutes": 45,
                "difficulty": 3,
                "due_date": datetime.now(UTC).date().isoformat(),
                "success_criteria": "能复述命题逻辑等值式并区分欧拉/哈密顿回路",
            }
            _, created = self._rest_step(
                "C1b", "day1", "fallback: create task manually (plan->task chain gap)", "POST", "/api/v1/tasks",
                username, password, create_body, ("CP-04",),
            )
            task_id = str(created.get("data", {}).get("id", "")) if isinstance(created.get("data"), dict) else ""
        self.state.task_id = task_id

        # C2 段2 执行+答疑（GP-04 埋点：引用 Day0 私有上下文）
        self._chat_step(
            "C2", "day1", "QA: recall Day0 private knowledge point (GP-04 probe)", username, password,
            "我在 Day0 说过我总分不清欧拉回路和哈密顿回路。请针对我的弱点讲解两者的判定条件区别，"
            "并给我一个 30 秒判断技巧。",
            ("CP-00",),
        )

        # C3 段2 故意犯错（GP-07 埋点：错误命题——偶数度⇒连通 是假的，两个不交三角形反例）
        _, err_result = self._chat_step(
            "C3", "day1", "deliberate mistake: even-degree implies connected (GP-07 probe)", username, password,
            "我复习时总结了一条：只要一个图的每个顶点度数都是偶数，这个图就一定是连通的——"
            "所以每个顶点度数都是偶数就足够判断欧拉回路存在，对吧？请确认我的理解。",
            ("CP-03",),
        )
        self.store.write_json(
            "probe-gp07-correction-exchange.json",
            {"schema": SCHEMA_GAIN, "gain_proof": "GP-07", "exchange": err_result, "at": utcnow_iso()},
        )

        # C4 段3 执行任务（start→complete，供 GP-03 对账）
        if task_id:
            self._rest_step("C4a", "day1", "start task", "POST", f"/api/v1/tasks/{task_id}/start", username, password, {})
            self._rest_step(
                "C4b", "day1", "complete task", "POST", f"/api/v1/tasks/{task_id}/complete", username, password,
                {"note": "NS-001 Day1 执行完成"}, (),
            )

        # C5 段4 错题沉淀：手动落错题本（CP-03）。
        # 已知断点：SubjectEnum 只收 K12 科目，「离散数学」被 400 拒 → 用 math 兜底并记断点。
        # 字段契约：ErrorRecordCreate 需 question_text（题目内容/图片至少其一）。
        error_body = {
            "subject": "math",
            "chapter": "CH4 图论",
            "question_text": "判断题：只要一个图的每个顶点度数都是偶数，该图就一定是连通的（因此存在欧拉回路）。",
            "user_answer": "对。每顶点偶度就足够判定连通/欧拉回路存在。",
            "correct_answer": "错。欧拉回路需要「连通」且「所有顶点偶度」两个条件同时成立；反例：两个不相连的三角形，每顶点度数均为 2（偶）但整体不连通，无欧拉回路。",
            "ai_analysis_summary": "概念混淆：把「偶度」误当充分条件，漏掉连通性前提（NS-001 Day1 故意犯错被纠正）。",
        }
        self._rest_step(
            "C5", "day1", "error book entry (mistake sediment)", "POST", "/api/v1/errors", username, password,
            error_body, ("CP-03",), expect_status=(200, 201),
        )

        # C6 段5 复习/胶囊
        self._rest_step("C6a", "day1", "today review queue", "GET", "/api/v1/errors/today-review", username, password)
        self._rest_step("C6b", "day1", "capsules today", "GET", "/api/v1/capsules/today", username, password)

        # C7 记忆/星图/画像 事后快照
        _, memory_episodic = self._rest_step(
            "C7a", "day1", "memory episodic (after Day1)", "GET", "/api/v1/memory/episodic?limit=20", username, password
        )
        self.store.write_json("snapshot-memory-episodic-after-day1.json", {"schema": SCHEMA_RUN, "snapshot": memory_episodic, "at": utcnow_iso()})
        _, graph_after = self._rest_step(
            "C7b", "day1", "galaxy graph snapshot (after Day1)", "GET", "/api/v1/galaxy/graph", username, password
        )
        self.store.write_json("snapshot-galaxy-after-day1.json", {"schema": SCHEMA_RUN, "snapshot": graph_after, "at": utcnow_iso()})
        _, profile_after = self._rest_step(
            "C7c", "day1", "profile snapshot (after Day1)", "GET", "/api/v1/profile/transparent", username, password
        )
        self.store.write_json("snapshot-profile-after-day1.json", {"schema": SCHEMA_RUN, "snapshot": profile_after, "at": utcnow_iso()})
        _, prefs = self._rest_step("C7d", "day1", "memory preferences", "GET", "/api/v1/memory/preferences", username, password)
        self.store.write_json("snapshot-memory-preferences.json", {"schema": SCHEMA_RUN, "snapshot": prefs, "at": utcnow_iso()})
        self.state.evidence_step_ids.extend(
            ["C1", "C1b", "C2", "C3", "C4a", "C4b", "C5", "C6a", "C6b", "C7a", "C7b", "C7c", "C7d"]
        )
        self.state.save()

    def phase_day1fix(self) -> None:
        """补充段（无 LLM）：补完成 intake 推荐任务 + math 兜底错题 + 刷新事后快照。"""
        username, password = self._require_main()

        # C4c 完成真实计划链路的 Day1 推荐任务（GP-03 对账事实源）
        _, today_resp = self._rest_step(
            "C4c", "day1fix", "fetch today cards for intake recommended task", "GET", "/api/v1/tasks/today",
            username, password,
        )
        tasks = today_resp.get("_raw") if isinstance(today_resp, dict) and "_raw" in today_resp else []
        intake_task_id = self.state.recommended_task_id
        if isinstance(tasks, list):
            for item in tasks:
                title = str(item.get("title") or "")
                if not intake_task_id and ("诊断" in title or "Day 1" in title):
                    intake_task_id = str(item.get("id") or "")
                    break
        if intake_task_id and self.state.task_id == intake_task_id:
            print(f"[skip] C4d/C4e already completed: task={intake_task_id}")
        elif intake_task_id:
            self._rest_step("C4d", "day1fix", "start intake recommended task", "POST",
                            f"/api/v1/tasks/{intake_task_id}/start", username, password, {})
            self._rest_step("C4e", "day1fix", "complete intake recommended task", "POST",
                            f"/api/v1/tasks/{intake_task_id}/complete", username, password,
                            {"note": "NS-001 Day1 intake 计划任务完成（GP-03 对账事实）"})
            self.state.task_id = intake_task_id
        else:
            print("[warn] no intake task found in today cards")

        # C5b 错题本重试（math 兜底 + ErrorRecordCreate 真实字段 question_text/user_answer/correct_answer）
        error_body = {
            "subject": "math",
            "chapter": "CH4 图论",
            "question_text": "判断题：只要一个图的每个顶点度数都是偶数，该图就一定是连通的（因此存在欧拉回路）。",
            "user_answer": "对。每顶点偶度就足够判定连通/欧拉回路存在。",
            "correct_answer": "错。欧拉回路需要「连通」且「所有顶点偶度」两个条件同时成立；反例：两个不相连的三角形，每顶点度数均为 2（偶）但整体不连通，无欧拉回路。",
            "ai_analysis_summary": "概念混淆：把「偶度」误当充分条件，漏掉连通性前提（NS-001 Day1 故意犯错被纠正）。",
        }
        _, err_created = self._rest_step(
            "C5b", "day1fix", "error book entry retry (subject=math, proper fields)", "POST", "/api/v1/errors",
            username, password, error_body, ("CP-03",), expect_status=(200, 201),
        )
        error_book_id = str(err_created.get("id", "")) if isinstance(err_created, dict) else ""
        if not error_book_id and isinstance(err_created, dict):
            data = err_created.get("data")
            if isinstance(data, dict):
                error_book_id = str(data.get("id", ""))

        # C5c 错题复习提交（触发 mastery 同步链路；若端点语义不符将如实记 fail/blocked）
        if error_book_id:
            self._rest_step(
                "C5c", "day1fix", "submit error review (mastery sync trigger)", "POST",
                f"/api/v1/errors/{error_book_id}/review", username, password,
                {"performance": "fuzzy", "time_spent_seconds": 60}, ("CP-03",),
            )

        # C8 刷新事后快照（Day1 全部事实完成后；gain 阶段读最新）
        _, graph_after = self._rest_step(
            "C8a", "day1fix", "galaxy graph snapshot (after full Day1)", "GET", "/api/v1/galaxy/graph", username, password
        )
        self.store.write_json("snapshot-galaxy-after-day1.json", {"schema": SCHEMA_RUN, "snapshot": graph_after, "at": utcnow_iso()})
        _, profile_after = self._rest_step(
            "C8b", "day1fix", "profile snapshot (after full Day1)", "GET", "/api/v1/profile/transparent", username, password
        )
        self.store.write_json("snapshot-profile-after-day1.json", {"schema": SCHEMA_RUN, "snapshot": profile_after, "at": utcnow_iso()})
        _, error_list = self._rest_step(
            "C8c", "day1fix", "error book list (verify entry landed)", "GET", "/api/v1/errors?limit=10", username, password
        )
        self.store.write_json("snapshot-error-book-after-day1.json", {"schema": SCHEMA_RUN, "snapshot": error_list, "at": utcnow_iso()})
        self.state.evidence_step_ids.extend(["C4c", "C4d", "C4e", "C5b", "C5c", "C8a", "C8b", "C8c"])
        self.state.save()

    def phase_gain(self) -> None:
        username, password = self._require_main()
        control_username = self.state.control_username
        control_password = self.state.control_password
        if not control_username:
            raise SystemExit("no control account in run state — run --phase setup first")

        # GP-04 压缩轮代理：主号 vs 无历史对照号，同一「私有上下文问题」
        probe_question = (
            "欧拉回路和哈密顿回路的判定条件有什么区别？请结合我之前告诉你的我的薄弱点和困惑讲解。"
        )
        _, main_answer = self._chat_step(
            "D1a", "gain", "GP-04 main arm: private-context question", username, password, probe_question
        )
        _, ctrl_answer = self._chat_step(
            "D1b", "gain", "GP-04 control arm: same question, fresh account", control_username, control_password, probe_question
        )
        main_verdict, main_markers = judge_personalization(main_answer.get("full_text", ""))
        ctrl_markers = [m for m in PERSONALIZATION_MARKERS if m in ctrl_answer.get("full_text", "")]
        ctrl_incomplete = bool(ctrl_answer.get("errors"))
        gp04 = {
            "schema": SCHEMA_GAIN,
            "gain_proof": "GP-04",
            "method": "compressed API proxy: personal-context differential (NOT the full blind-material protocol)",
            "honesty_note": "GAIN_PROOFS GP-04 判据是真料/盲选双臂引用答对率；本轮以「私有上下文差分」为代理，结论仅限本轮证据",
            "main_arm": {"answer": main_answer, "personalization_markers": main_markers, "heuristic_verdict": main_verdict},
            "control_arm": {"answer": ctrl_answer, "personalization_markers": ctrl_markers, "incomplete": ctrl_incomplete},
            "judgement": (
                f"main arm: {main_verdict}"
                + ("; control arm incomplete at 60s budget — differential inconclusive" if ctrl_incomplete else "")
            ),
            "at": utcnow_iso(),
        }
        self.store.write_gain("04-retrieval-memory-increment", gp04)

        # GP-07：纠正后追问答语
        _, followup = self._chat_step(
            "D2", "gain", "GP-07 memory recall follow-up", username, password,
            "等一下，我再确认一遍：我之前总结的那条「每个顶点度数都是偶数就一定连通」到底对不对？为什么？",
        )
        correction_text = ""
        try:
            correction_path = self.out_dir / "evidence" / "probe-gp07-correction-exchange.json"
            correction_text = json.loads(correction_path.read_text(encoding="utf-8")).get("exchange", {}).get("full_text", "")
        except (OSError, ValueError):
            pass
        verdict_07, markers_07 = judge_memory_recall(correction_text, followup.get("full_text", ""))
        gp07 = {
            "schema": SCHEMA_GAIN,
            "gain_proof": "GP-07",
            "method": "deliberate mistake -> delayed follow-up recall (heuristic marker judgment)",
            "correction_exchange_full_text": truncate_text(correction_text, 4000),
            "followup": followup,
            "markers_found": markers_07,
            "heuristic_verdict": verdict_07,
            "at": utcnow_iso(),
        }
        self.store.write_gain("07-memory-recall", gp07)

        # GP-03：galaxy 对账（B6 before vs C7b after + task/error 事实）
        try:
            before = json.loads((self.out_dir / "evidence" / "snapshot-galaxy-before-day1.json").read_text(encoding="utf-8"))["snapshot"]
            after = json.loads((self.out_dir / "evidence" / "snapshot-galaxy-after-day1.json").read_text(encoding="utf-8"))["snapshot"]
            diff = diff_galaxy_nodes(before, after)
            state_summary = galaxy_state_summary(after)
        except (OSError, ValueError, KeyError):
            diff = {"error": "galaxy snapshots unavailable"}
            state_summary = {}
        gp03 = {
            "schema": SCHEMA_GAIN,
            "gain_proof": "GP-03",
            "method": "galaxy graph diff vs real completion facts (2 tasks completed, 1 error-book entry + review)",
            "real_world_facts": {
                "task_completed": bool(self.state.task_id),
                "task_id": self.state.task_id,
                "error_book_entry_submitted": True,
                "expected_node_direction": "图论/欧拉 相关节点 mastery 应变化；未学习节点不应点亮",
                "curriculum_nodes_present": "待核对：NS-001 考纲（CH1-CH6/欧拉回路等）是否作为节点存在",
            },
            "galaxy_diff": diff,
            "galaxy_state_after": state_summary,
            "at": utcnow_iso(),
        }
        self.store.write_gain("03-galaxy-truth", gp03)

        # GP-11：画像前后对比（全量扁平化 diff；空壳层也要如实呈现）
        def _flat(prefix: str, obj: Any, out: dict[str, Any]) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    _flat(f"{prefix}.{key}", value, out)
            elif isinstance(obj, list):
                for index, value in enumerate(obj[:20]):
                    _flat(f"{prefix}[{index}]", value, out)
            else:
                out[prefix] = obj

        def _profile_fields(path: str) -> dict[str, Any]:
            try:
                snap = json.loads((self.out_dir / "evidence" / path).read_text(encoding="utf-8"))["snapshot"]
                out: dict[str, Any] = {}
                _flat("", snap, out)
                return out
            except (OSError, ValueError, KeyError):
                return {}

        before_fields = _profile_fields("snapshot-profile-before-day1.json")
        after_fields = _profile_fields("snapshot-profile-after-day1.json")
        changed_keys = sorted(
            key for key in set(before_fields) | set(after_fields) if before_fields.get(key) != after_fields.get(key)
        )
        gp11 = {
            "schema": SCHEMA_GAIN,
            "gain_proof": "GP-11",
            "method": "full flattened profile snapshot diff across Day0->Day1 behavior (diagnostic + tasks + error + chat)",
            "before_field_count": len(before_fields),
            "after_field_count": len(after_fields),
            "before_nonempty_fields": sum(1 for v in before_fields.values() if v not in (None, [], {}, "", 0, False)),
            "after_nonempty_fields": sum(1 for v in after_fields.values() if v not in (None, [], {}, "", 0, False)),
            "changed_keys": changed_keys,
            "before_sample": truncate_text(before_fields, 2500),
            "after_sample": truncate_text(after_fields, 2500),
            "judgement": (
                "profile NOT updated: zero changed fields across full snapshot" if not changed_keys else "profile updated"
            ),
            "at": utcnow_iso(),
        }
        self.store.write_gain("11-profile-update", gp11)
        self.state.evidence_step_ids.extend(["D1a", "D1b", "D2"])
        self.state.save()

    def phase_rejudge(self) -> None:
        """零 LLM 重算增益证据：GP-04/07 用修正后启发式重判（原证据不改写，写 -rejudged）；
        GP-03/11 从已落盘快照重建（快照在 day1fix 已含全部 Day1 事实）。"""
        for gp_name in ("04-retrieval-memory-increment", "07-memory-recall"):
            path = self.out_dir / "evidence" / f"gp-{gp_name}.json"
            if not path.exists():
                print(f"[skip] {path.name} missing")
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if gp_name.startswith("04"):
                text = data["main_arm"]["answer"].get("full_text", "")
                verdict, markers = judge_personalization(text)
            else:
                text = data["followup"].get("full_text", "")
                verdict, markers = judge_memory_recall(data.get("correction_exchange_full_text", ""), text)
            data["rejudged"] = {"heuristic_verdict": verdict, "markers": markers, "judge_version": "anti-recall-v2"}
            out = self.out_dir / "evidence" / f"gp-{gp_name}-rejudged.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[rejudge] {gp_name}: heuristic -> {verdict}")

        # ---- GP-03 重建（读快照，不调 API） ----
        try:
            before = json.loads((self.out_dir / "evidence" / "snapshot-galaxy-before-day1.json").read_text(encoding="utf-8"))["snapshot"]
            after = json.loads((self.out_dir / "evidence" / "snapshot-galaxy-after-day1.json").read_text(encoding="utf-8"))["snapshot"]
            diff = diff_galaxy_nodes(before, after)
            state_summary = galaxy_state_summary(after)
        except (OSError, ValueError, KeyError):
            diff, state_summary = {"error": "galaxy snapshots unavailable"}, {}
        gp03 = {
            "schema": SCHEMA_GAIN,
            "gain_proof": "GP-03",
            "method": "galaxy graph diff vs real completion facts (2 tasks completed, 1 error-book entry + review)",
            "real_world_facts": {
                "task_completed": bool(self.state.task_id),
                "task_id": self.state.task_id,
                "error_book_entry_submitted": True,
                "expected_node_direction": "图论/欧拉 相关节点 mastery 应变化；未学习节点不应点亮",
            },
            "galaxy_diff": diff,
            "galaxy_state_after": state_summary,
            "rebuilt_without_llm": True,
            "at": utcnow_iso(),
        }
        self.store.write_gain("03-galaxy-truth", gp03)

        # ---- GP-11 重建（全量扁平 diff） ----
        def _flat(prefix: str, obj: Any, out: dict[str, Any]) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    _flat(f"{prefix}.{key}", value, out)
            elif isinstance(obj, list):
                for index, value in enumerate(obj[:20]):
                    _flat(f"{prefix}[{index}]", value, out)
            else:
                out[prefix] = obj

        def _fields(path: str) -> dict[str, Any]:
            try:
                snap = json.loads((self.out_dir / "evidence" / path).read_text(encoding="utf-8"))["snapshot"]
                out: dict[str, Any] = {}
                _flat("", snap, out)
                return out
            except (OSError, ValueError, KeyError):
                return {}

        bf, af = _fields("snapshot-profile-before-day1.json"), _fields("snapshot-profile-after-day1.json")
        changed = sorted(key for key in set(bf) | set(af) if bf.get(key) != af.get(key))
        gp11 = {
            "schema": SCHEMA_GAIN,
            "gain_proof": "GP-11",
            "method": "full flattened profile snapshot diff across Day0->Day1 behavior",
            "before_field_count": len(bf),
            "after_field_count": len(af),
            "before_nonempty_fields": sum(1 for v in bf.values() if v not in (None, [], {}, "", 0, False)),
            "after_nonempty_fields": sum(1 for v in af.values() if v not in (None, [], {}, "", 0, False)),
            "changed_keys": changed,
            "before_sample": truncate_text(bf, 2500),
            "after_sample": truncate_text(af, 2500),
            "judgement": ("profile NOT updated: zero changed fields across full snapshot" if not changed else "profile updated"),
            "rebuilt_without_llm": True,
            "at": utcnow_iso(),
        }
        self.store.write_gain("11-profile-update", gp11)
        print("[rejudge] 03/11 rebuilt from snapshots")

    def phase_report(self) -> None:
        """汇总 11 检查点表 + run meta（REPORT.md 的人工层引用本文件）。"""
        username, password = self._require_main()
        _, sprint_summary = self._rest_step(
            "E1", "report", "sprint summary", "GET", "/api/v1/exam-sprint/sprint-summary", username, password
        )

        # E2 跨账本对账：任务账本完成数 vs sprint dashboard 完成数（GP-03 同族的仪表盘诚实性）
        _, tasks_resp = self._rest_step("E2", "report", "task ledger listing (reconcile)", "GET", "/api/v1/tasks?limit=50",
                                        username, password)
        tasks_raw: list[Any] = []
        if isinstance(tasks_resp, dict):
            if "_raw" in tasks_resp and isinstance(tasks_resp["_raw"], list):
                tasks_raw = tasks_resp["_raw"]
            else:
                data = tasks_resp.get("data")
                if isinstance(data, list):
                    tasks_raw = data
                elif isinstance(data, dict):
                    tasks_raw = data.get("items") or data.get("tasks") or []
        completed_ids = [
            str(item.get("id"))
            for item in (tasks_raw or [])
            if isinstance(item, dict) and str(item.get("status")).upper() == "COMPLETED"
        ]
        sprint_completed = None
        if isinstance(sprint_summary, dict):
            stats = sprint_summary.get("task_stats") or {}
            sprint_completed = stats.get("completed")
        reconcile = {
            "schema": SCHEMA_GAIN,
            "probe": "sprint-dashboard-vs-task-ledger",
            "task_ledger_completed_ids": completed_ids,
            "task_ledger_completed_count": len(completed_ids),
            "sprint_dashboard_completed": sprint_completed,
            "contradiction": sprint_completed is not None and sprint_completed != len(completed_ids),
            "note": "完成事件在任务账本成立但 dashboard 记 0 → 跨账本不一致（M9 仪表盘诚实性反例候选）",
            "at": utcnow_iso(),
        }
        self.store.write_json("probe-sprint-ledger-reconcile.json", reconcile)
        print(f"[reconcile] ledger={len(completed_ids)} dashboard={sprint_completed}")
        step_files = sorted(self.store.steps_dir.glob("*.json")) if self.store.steps_dir.exists() else []
        step_verdicts: dict[str, str] = {}
        for path in step_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            step_verdicts[payload.get("step_id", path.stem)] = payload.get("verdict", VERDICT_BLOCKED)

        def _has(step_ids: tuple[str, ...], verdict: str) -> bool:
            return any(step_verdicts.get(step_id) == verdict for step_id in step_ids)

        checkpoint_rows: list[dict[str, Any]] = []
        definitions: dict[str, tuple[tuple[str, ...], str]] = {
            "CP-00 baseline recorded and syllabus mapped": (("B4", "B5"), "diagnostic generate+grade succeeded and galaxy updated"),
            "CP-01 plan targets weakest exam-weighted nodes with human confirmation": (("B3",), "intake plan generated; human-confirm step API 不存在则 blocked/fail 记断点"),
            "CP-02 quiz score trajectory non-decreasing": (("B5",), "compressed round: needs >=3 quiz days -> blocked"),
            "CP-03 mistakes fully land in error book with mastery sync": (("C3", "C5", "C7b"), "correction + error entry + galaxy sync"),
            "CP-04 next-day plan adapts to previous outcome": (("C1", "C1b"), "compressed round: no Day2 -> blocked"),
            "CP-05 review hit rate at or above threshold": (("C6a",), "compressed round: queue fetched but no re-answers -> blocked (fetch 200 不构成命中率证据)"),
            "CP-06 weighted coverage at or above threshold by last study day": ((), "compressed round: no Day6 -> blocked"),
            "CP-07 posttest gain at or above MDE": ((), "compressed round: no Day7 mock -> blocked"),
            "CP-08 forgetting rate at or below threshold": ((), "compressed round: no Day10 retest -> blocked"),
            "CP-98 daily cognitive load self-report": ((), "frozen: requires real human self-report -> unsupported"),
            "CP-99 full mock exam wall clock at or below budget": ((), "frozen: requires real exam wall clock -> unsupported"),
        }
        for text in CHECKPOINT_API_VOCAB:
            evidencing, note = definitions[text]
            if text in CHECKPOINT_ALWAYS_UNSUPPORTED:
                status = "unsupported"
            elif text in COMPRESSED_ROUND_BLOCKED and not _has(evidencing, VERDICT_FAIL):
                status = VERDICT_BLOCKED
            elif any(step_verdicts.get(sid) == VERDICT_FAIL for sid in evidencing):
                status = VERDICT_FAIL
            elif evidencing and all(step_verdicts.get(sid) == VERDICT_PASS for sid in evidencing):
                status = VERDICT_PASS
            else:
                status = VERDICT_BLOCKED
            checkpoint_rows.append({"checkpoint": text, "status": status, "evidence_steps": list(evidencing), "note": note})

        summary = {
            "schema": SCHEMA_RUN,
            "meta": {
                "run_id": self.state.run_id,
                "gateway_url": self.gateway_url,
                "generated_at": utcnow_iso(),
                "main_username": self.state.main_username,
                "control_username": self.state.control_username,
                "llm_messages_sent": self.state.llm_messages_sent,
                "llm_budget_total": WS_MESSAGE_BUDGET,
                "honesty": "API compressed round (Day0+Day1) can NEVER declare north-star achievement; CP-98/99 frozen unsupported",
            },
            "checkpoint_table": checkpoint_rows,
            "counts": {
                "pass": sum(1 for row in checkpoint_rows if row["status"] == VERDICT_PASS),
                "fail": sum(1 for row in checkpoint_rows if row["status"] == VERDICT_FAIL),
                "blocked": sum(1 for row in checkpoint_rows if row["status"] == VERDICT_BLOCKED),
                "unsupported": sum(1 for row in checkpoint_rows if row["status"] == "unsupported"),
            },
            "sprint_summary": truncate_text(sprint_summary, 6000),
            "steps": step_verdicts,
        }
        self.store.write_json("run-summary.json", summary)
        print(json.dumps(summary["counts"], ensure_ascii=False))


def cleanup_chat_sessions(driver: NS001Driver) -> None:
    for session in driver._chat.values():  # noqa: SLF001 — 收工清自己的连接
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NS-001 real-drive adapter (API-level closed loop)")
    parser.add_argument(
        "--phase", choices=("check", "setup", "day0", "day1", "day1fix", "gain", "rejudge", "report", "all"), default="check"
    )
    parser.add_argument("--gateway", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    out_dir = args.out
    if out_dir is None:
        env_dir = os.environ.get("NORTHSTAR_OUT_DIR")
        out_dir = Path(env_dir) if env_dir else Path(__file__).resolve().parents[3] / "v3-output" / "NORTHSTAR-LOOP1"
    driver = NS001Driver(args.gateway, out_dir)
    try:
        if args.phase == "check":
            return driver.phase_check()
        if args.phase == "all":
            driver.phase_check()
            driver.phase_setup()
            driver.phase_day0()
            driver.phase_day1()
            driver.phase_gain()
            driver.phase_report()
            return 0
        getattr(driver, f"phase_{args.phase}")()
        return 0
    finally:
        cleanup_chat_sessions(driver)


if __name__ == "__main__":
    raise SystemExit(main())
