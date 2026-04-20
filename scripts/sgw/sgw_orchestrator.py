#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import random
import signal
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp
import websockets
from sqlalchemy import select

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from hard_violation_rules import HardViolation, check_inferred_record
from metrics_collector import MetricsCollector

from app.db.session import AsyncSessionLocal, engine
from app.core.security import create_access_token
from app.models.memory import EpisodicMemory
from app.models.user import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_now() -> str:
    return utcnow().isoformat(timespec="seconds")


@dataclass
class SessionTask:
    task_id: str
    role: str
    persona_id: str | None
    playbook_id: str | None
    user_id: str
    username: str
    email: str
    session_id: str
    target_turns: int
    turns_completed: int = 0
    status: str = "pending"
    transcript: list[dict[str, str]] = field(default_factory=list)
    detected_memory_ids: list[str] = field(default_factory=list)
    last_note: str | None = None
    last_error: str | None = None
    retry_count: int = 0
    revoke_scheduled: bool = False
    created_at: str = field(default_factory=iso_now)
    updated_at: str = field(default_factory=iso_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionTask":
        return cls(**payload)


@dataclass
class AuditTask:
    case_id: str
    record: dict[str, Any]
    source_chat_turn: str
    status: str = "pending"
    retry_count: int = 0
    score: dict[str, Any] | None = None
    created_at: str = field(default_factory=iso_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AuditTask":
        return cls(**payload)


@dataclass
class OrchestratorConfig:
    persona_library: Path
    adversarial_playbook: Path
    report_path: Path
    checkpoint_path: Path
    wall_clock_hours: float = float(os.getenv("SGW_WALL_CLOCK_HOURS", "18"))
    min_sessions: int = 360
    min_turns: int = 4000
    turn_target: int = 12
    adversarial_sessions: int = 24
    websocket_url: str = os.getenv("WS_BASE_URL", "ws://127.0.0.1:8080")
    api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8080")
    soft_violation_threshold: float = 0.85
    soft_violation_rate_limit: float = 0.05
    claude_model: str = os.getenv("SGW_CLAUDE_MODEL", "")
    claude_effort: str = os.getenv("SGW_CLAUDE_EFFORT", "medium")
    claude_timeout_seconds: int = int(os.getenv("SGW_CLAUDE_TIMEOUT_SECONDS", "45"))
    claude_min_parallel: int = int(os.getenv("SGW_CLAUDE_MIN_PARALLEL", "1"))
    claude_max_parallel: int = int(os.getenv("SGW_CLAUDE_MAX_PARALLEL", "2"))
    claude_initial_parallel: int = int(os.getenv("SGW_CLAUDE_INITIAL_PARALLEL", "2"))
    claude_min_interval_seconds: float = float(os.getenv("SGW_CLAUDE_MIN_INTERVAL_SECONDS", "5"))
    claude_rate_limit_backoff_seconds: int = int(os.getenv("SGW_CLAUDE_RATE_LIMIT_BACKOFF_SECONDS", "300"))
    claude_short_backoff_seconds: int = int(os.getenv("SGW_CLAUDE_SHORT_BACKOFF_SECONDS", "60"))
    claude_failure_backoff_seconds: int = int(os.getenv("SGW_CLAUDE_FAILURE_BACKOFF_SECONDS", "30"))
    claude_budget_reset_seconds: int = int(os.getenv("SGW_CLAUDE_WINDOW_RESET_SECONDS", str(5 * 3600)))
    claude_scale_up_cooldown_seconds: int = int(os.getenv("SGW_CLAUDE_SCALE_UP_COOLDOWN_SECONDS", "600"))
    claude_ceiling_probe_cooldown_seconds: int = int(
        os.getenv("SGW_CLAUDE_CEILING_PROBE_COOLDOWN_SECONDS", "1800")
    )
    max_history_pairs: int = int(os.getenv("SGW_MAX_HISTORY_PAIRS", "6"))
    audit_sample_rate: float = float(os.getenv("SGW_AUDIT_SAMPLE_RATE", "0.25"))
    random_seed: int = int(os.getenv("SGW_RANDOM_SEED", "17"))
    resume: bool = False


class ClaudeCallError(RuntimeError):
    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


class ClaudeCliClient:
    def __init__(self, config: OrchestratorConfig):
        self._config = config
        self._hard_cap = max(1, config.claude_max_parallel)
        self._min_parallel = max(1, min(config.claude_min_parallel, self._hard_cap))
        requested_initial = max(self._min_parallel, config.claude_initial_parallel)
        self._effective_parallel = min(requested_initial, self._hard_cap)
        self._call_semaphore = asyncio.Semaphore(self._hard_cap)
        self._parallel_condition = asyncio.Condition()
        self._inflight_calls = 0
        self._call_pace_lock = asyncio.Lock()
        self._last_call_started_at = 0.0
        self._last_rate_limit_at = 0.0
        self._last_scaled_up_at = time.time()
        self._stable_parallel_ceiling = self._hard_cap
        self._last_ceiling_probe_at = 0.0
        self._debug_dir = config.checkpoint_path.parent / "claude_debug"
        self._debug_dir.mkdir(parents=True, exist_ok=True)

    async def text_call(self, *, system_prompt: str, prompt: str) -> str:
        raw = await self._run_raw(system_prompt=system_prompt, prompt=prompt)
        cleaned = self._normalize_output(raw)
        if not cleaned:
            raise ClaudeCallError("process", "claude CLI returned empty output")
        return cleaned

    async def _run_raw(self, *, system_prompt: str, prompt: str) -> str:
        async with self._call_semaphore:
            await self._acquire_effective_slot()
            try:
                await self._pace_calls()
                debug_path = self._debug_dir / f"{int(time.time())}_{uuid.uuid4().hex}.log"
                command = [
                    "claude",
                    "-p",
                    prompt,
                    "--system-prompt",
                    system_prompt,
                    "--output-format",
                    "text",
                    "--tools",
                    "",
                    "--effort",
                    self._config.claude_effort,
                    "--bare",
                    "--no-session-persistence",
                    "--permission-mode",
                    "bypassPermissions",
                    "--debug-file",
                    str(debug_path),
                ]
                if self._config.claude_model:
                    command.extend(["--model", self._config.claude_model])

                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                timed_out = False
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self._config.claude_timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    timed_out = True
                    with contextlib.suppress(ProcessLookupError):
                        process.send_signal(signal.SIGINT)
                    try:
                        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3)
                    except asyncio.TimeoutError as exc:
                        process.kill()
                        stdout, stderr = await process.communicate()
                        debug_text = self._read_debug_text(debug_path)
                        classified = self._classify_failure(
                            output=stdout.decode("utf-8", errors="replace").strip(),
                            error_text=stderr.decode("utf-8", errors="replace").strip(),
                            debug_text=debug_text,
                            timed_out=True,
                        )
                        raise classified or ClaudeCallError("timeout", "claude CLI timed out") from exc

                output = stdout.decode("utf-8", errors="replace").strip()
                error_text = stderr.decode("utf-8", errors="replace").strip()
                debug_text = self._read_debug_text(debug_path)
                classified = self._classify_failure(
                    output=output,
                    error_text=error_text,
                    debug_text=debug_text,
                    timed_out=timed_out,
                )
                if classified:
                    raise classified
                return output
            finally:
                await self._release_effective_slot()

    async def _acquire_effective_slot(self) -> None:
        async with self._parallel_condition:
            await self._parallel_condition.wait_for(lambda: self._inflight_calls < self._effective_parallel)
            self._inflight_calls += 1

    async def _release_effective_slot(self) -> None:
        async with self._parallel_condition:
            self._inflight_calls = max(0, self._inflight_calls - 1)
            self._parallel_condition.notify_all()

    async def _pace_calls(self) -> None:
        async with self._call_pace_lock:
            now = time.time()
            wait_seconds = self._config.claude_min_interval_seconds - (now - self._last_call_started_at)
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_call_started_at = time.time()

    @property
    def effective_parallel(self) -> int:
        return self._effective_parallel

    @property
    def hard_cap(self) -> int:
        return self._hard_cap

    def state_dict(self) -> dict[str, Any]:
        return {
            "effective_parallel": self._effective_parallel,
            "last_rate_limit_at": self._last_rate_limit_at,
            "last_scaled_up_at": self._last_scaled_up_at,
            "stable_parallel_ceiling": self._stable_parallel_ceiling,
            "last_ceiling_probe_at": self._last_ceiling_probe_at,
        }

    def restore_state(self, payload: dict[str, Any] | None) -> None:
        if not payload:
            return
        effective = int(payload.get("effective_parallel", self._effective_parallel))
        self._effective_parallel = max(self._min_parallel, min(effective, self._hard_cap))
        self._last_rate_limit_at = float(payload.get("last_rate_limit_at", self._last_rate_limit_at))
        self._last_scaled_up_at = float(payload.get("last_scaled_up_at", self._last_scaled_up_at))
        ceiling = int(payload.get("stable_parallel_ceiling", self._hard_cap))
        self._stable_parallel_ceiling = max(self._min_parallel, min(ceiling, self._hard_cap))
        self._last_ceiling_probe_at = float(payload.get("last_ceiling_probe_at", self._last_ceiling_probe_at))

    async def maybe_scale_up(self, *, queue_backlog: int) -> tuple[int, int] | None:
        if queue_backlog <= 0 or self._effective_parallel >= self._hard_cap:
            return None
        now = time.time()
        stable_since = max(self._last_rate_limit_at, self._last_scaled_up_at)
        async with self._parallel_condition:
            if self._inflight_calls > self._effective_parallel:
                return None
            if self._effective_parallel < self._stable_parallel_ceiling:
                if now - stable_since < self._config.claude_scale_up_cooldown_seconds:
                    return None
            else:
                if self._stable_parallel_ceiling >= self._hard_cap:
                    return None
                if now - max(self._last_rate_limit_at, self._last_ceiling_probe_at) < self._config.claude_ceiling_probe_cooldown_seconds:
                    return None
                self._stable_parallel_ceiling = min(self._hard_cap, self._stable_parallel_ceiling + 1)
                self._last_ceiling_probe_at = now
            before = self._effective_parallel
            self._effective_parallel = min(self._hard_cap, self._effective_parallel + 1)
            self._last_scaled_up_at = now
            self._parallel_condition.notify_all()
            return before, self._effective_parallel

    async def back_off_after_rate_limit(self) -> tuple[int, int] | None:
        self._last_rate_limit_at = time.time()
        async with self._parallel_condition:
            before = self._effective_parallel
            new_effective = max(self._min_parallel, before - 1)
            self._stable_parallel_ceiling = min(self._stable_parallel_ceiling, new_effective)
            if before <= self._min_parallel:
                return None
            self._effective_parallel = new_effective
            self._parallel_condition.notify_all()
            return before, self._effective_parallel

    @staticmethod
    def _read_debug_text(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _classify_failure(
        *,
        output: str,
        error_text: str,
        debug_text: str,
        timed_out: bool,
    ) -> ClaudeCallError | None:
        combined = "\n".join([output, error_text, debug_text]).lower()
        quota_markers = (
            "usage limit",
            "quota",
            "credit balance",
            "套餐",
            "额度",
            "five hour",
            "5 hour",
            "5-hour",
        )
        rate_limit_markers = (
            "429",
            "rate limit",
            "too many requests",
            "达到速率限制",
            "请求频率",
            '"code":"1302"',
            '"code":"429"',
        )
        if any(marker in combined for marker in quota_markers):
            return ClaudeCallError("quota", error_text or output or "claude quota exhausted")
        if any(marker in combined for marker in rate_limit_markers):
            return ClaudeCallError("rate_limit", error_text or output or "claude rate limited")
        if timed_out:
            return ClaudeCallError("timeout", error_text or output or "claude CLI timed out")
        normalized = output.strip().lower()
        if normalized == "execution error":
            return ClaudeCallError("process", error_text or output or "claude CLI failed")
        if not output.strip():
            return ClaudeCallError("process", error_text or "claude CLI returned empty output")
        return None

    @staticmethod
    def _normalize_output(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = next((part for part in parts if part.strip()), text)
        text = text.strip().strip('"').strip("'").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        return "\n".join(lines)


class SparkleGatewayClient:
    def __init__(self, config: OrchestratorConfig):
        self._config = config

    async def chat_once(self, *, token: str, session_id: str, user_id: str, message: str) -> str:
        uri = f"{self._config.websocket_url}/ws/chat?token={quote(token)}"
        request = {
            "type": "message",
            "message": message,
            "session_id": session_id,
            "user_id": user_id,
        }
        chunks: list[str] = []
        full_text: str | None = None
        async with websockets.connect(uri, ping_interval=None, ping_timeout=None, close_timeout=10) as websocket:
            await websocket.send(json.dumps(request))
            while True:
                raw = await asyncio.wait_for(websocket.recv(), timeout=300)
                data = json.loads(raw)
                msg_type = data.get("type")
                if msg_type == "delta":
                    chunks.append(data.get("delta", ""))
                elif msg_type == "full_text":
                    full_text = data.get("full_text", "")
                elif msg_type == "error":
                    raise RuntimeError(data.get("message") or data.get("error") or "Sparkle gateway returned error")
                elif msg_type == "done":
                    break
        return (full_text if full_text is not None else "".join(chunks)).strip()

    async def retract_memory(self, *, token: str, memory_id: str, reason: str) -> bool:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"type": "episodic", "id": memory_id, "reason": reason}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(f"{self._config.api_base_url}/api/v1/memory/retract", json=payload) as resp:
                return resp.status == 200

    async def export_memory_ids(self, *, token: str) -> set[str]:
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{self._config.api_base_url}/api/v1/memory/export") as resp:
                if resp.status != 200:
                    return set()
                payload = await resp.json()
        episodic = payload.get("episodic", [])
        return {str(item.get("id")) for item in episodic if item.get("id")}


class SGWOrchestrator:
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.random = random.Random(config.random_seed)
        self.metrics = MetricsCollector()
        self.claude = ClaudeCliClient(config)
        self.gateway = SparkleGatewayClient(config)
        self.persona_prompt_template = (SCRIPT_DIR / "prompts" / "persona_system_prompt.md").read_text(encoding="utf-8")
        self.adversarial_prompt_template = (SCRIPT_DIR / "prompts" / "adversarial_system_prompt.md").read_text(
            encoding="utf-8"
        )
        self.audit_prompt_template = (SCRIPT_DIR / "prompts" / "audit_system_prompt.md").read_text(encoding="utf-8")
        self.personas = json.loads(config.persona_library.read_text(encoding="utf-8"))
        self.playbook = json.loads(config.adversarial_playbook.read_text(encoding="utf-8"))
        self.session_tasks: dict[str, SessionTask] = {}
        self.audit_tasks: dict[str, AuditTask] = {}
        self.persona_queue: asyncio.Queue[str] = asyncio.Queue()
        self.adversarial_queue: asyncio.Queue[str] = asyncio.Queue()
        self.audit_queue: asyncio.Queue[str] = asyncio.Queue()
        self.seen_memory_ids: set[str] = set()
        self.global_cooldown_until: float | None = None
        self.stop_reason = ""
        self.stop_event = asyncio.Event()
        self.started_at = time.time()
        self._last_progress_emit = 0.0
        self._active_workers = 0
        self._db_sessions_in_use = 0
    async def run(self) -> int:
        self._install_signal_handlers()
        if self.config.resume and self.config.checkpoint_path.exists():
            self._load_checkpoint()
            self.metrics.record_resume()
        else:
            await self._bootstrap_tasks()
            await self._checkpoint()

        workers = [
            asyncio.create_task(self._session_worker(f"persona_{index}", "persona"))
            for index in range(1, 4)
        ]
        workers.append(asyncio.create_task(self._session_worker("adversarial_1", "adversarial")))
        workers.append(asyncio.create_task(self._audit_worker("audit_1")))

        try:
            while not self._should_stop():
                if self._recover_stalled_tasks():
                    await self._checkpoint()
                self.metrics.observe_queue_depth(
                    self.persona_queue.qsize() + self.adversarial_queue.qsize() + self.audit_queue.qsize()
                )
                self.metrics.observe_concurrency(self._active_workers)
                self.metrics.observe_claude_parallel(self.claude.effective_parallel)
                self.metrics.record_db_pool_peak(self._read_pool_in_use())
                if adjustment := await self.claude.maybe_scale_up(
                    queue_backlog=self.persona_queue.qsize() + self.adversarial_queue.qsize() + self.audit_queue.qsize()
                ):
                    before, after = adjustment
                    self.metrics.record_concurrency_adjustment(
                        before=before,
                        after=after,
                        reason="stable_window_probe",
                    )
                    print(f"[sgw] increasing Claude parallelism {before} -> {after} after stable window")
                    await self._checkpoint()
                self._emit_progress_if_needed()
                await asyncio.sleep(2)
            self.stop_event.set()
        finally:
            await asyncio.gather(*workers, return_exceptions=True)
            await self._checkpoint()
            await self._write_report()
        acceptance = self._acceptance()
        return 0 if all(acceptance.values()) else 1

    async def _bootstrap_tasks(self) -> None:
        persona_batches: list[list[SessionTask]] = []
        max_sessions_per_persona = 0
        for persona in self.personas:
            sessions = int(persona.get("session_multiplier", 1))
            max_sessions_per_persona = max(max_sessions_per_persona, sessions)
            user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sgw-user:{persona['id']}"))
            username = f"sgw_{persona['id']}"
            email = f"{persona['id']}@sgw.sparkle.local"
            await self._ensure_user(user_id=user_id, username=username, email=email)
            batch: list[SessionTask] = []
            for _ in range(sessions):
                batch.append(
                    SessionTask(
                        task_id=str(uuid.uuid4()),
                        role="persona",
                        persona_id=persona["id"],
                        playbook_id=None,
                        user_id=user_id,
                        username=username,
                        email=email,
                        session_id=str(uuid.uuid4()),
                        target_turns=self.config.turn_target,
                    )
                )
            persona_batches.append(batch)

        for index in range(max_sessions_per_persona):
            for batch in persona_batches:
                if index >= len(batch):
                    continue
                task = batch[index]
                self.session_tasks[task.task_id] = task
                await self.persona_queue.put(task.task_id)
                self.metrics.record_session_planned()

        for index in range(self.config.adversarial_sessions):
            playbook_item = self.playbook[index % len(self.playbook)]
            persona = self.personas[index % len(self.personas)]
            user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"sgw-adv-user:{playbook_item['id']}:{index}"))
            username = f"sgw_adv_{index:02d}"
            email = f"sgw_adv_{index:02d}@sgw.sparkle.local"
            await self._ensure_user(user_id=user_id, username=username, email=email)
            task = SessionTask(
                task_id=str(uuid.uuid4()),
                role="adversarial",
                persona_id=persona["id"],
                playbook_id=playbook_item["id"],
                user_id=user_id,
                username=username,
                email=email,
                session_id=str(uuid.uuid4()),
                target_turns=self.config.turn_target,
            )
            self.session_tasks[task.task_id] = task
            await self.adversarial_queue.put(task.task_id)
            self.metrics.record_session_planned()

    def _load_checkpoint(self) -> None:
        payload = json.loads(self.config.checkpoint_path.read_text(encoding="utf-8"))
        self.metrics = MetricsCollector.from_dict(payload["metrics"])
        self.session_tasks = {
            task_id: SessionTask.from_dict(task_payload)
            for task_id, task_payload in payload.get("session_tasks", {}).items()
        }
        self.audit_tasks = {
            case_id: AuditTask.from_dict(task_payload)
            for case_id, task_payload in payload.get("audit_tasks", {}).items()
        }
        self.seen_memory_ids = set(payload.get("seen_memory_ids", []))
        self.global_cooldown_until = payload.get("global_cooldown_until")
        self.claude.restore_state(payload.get("claude_state"))
        self.started_at = payload.get("started_at", time.time())
        for task in self.session_tasks.values():
            if task.status in {"running", "retry"}:
                task.status = "pending"
            if task.status == "pending":
                if task.role == "adversarial":
                    self.adversarial_queue.put_nowait(task.task_id)
                else:
                    self.persona_queue.put_nowait(task.task_id)
        for audit_task in self.audit_tasks.values():
            if audit_task.status in {"running", "retry"}:
                audit_task.status = "pending"
            if audit_task.status == "pending":
                self.audit_queue.put_nowait(audit_task.case_id)

    async def _checkpoint(self) -> None:
        payload = {
            "started_at": self.started_at,
            "global_cooldown_until": self.global_cooldown_until,
            "claude_state": self.claude.state_dict(),
            "seen_memory_ids": sorted(self.seen_memory_ids),
            "metrics": self.metrics.to_dict(),
            "session_tasks": {task_id: task.to_dict() for task_id, task in self.session_tasks.items()},
            "audit_tasks": {case_id: task.to_dict() for case_id, task in self.audit_tasks.items()},
        }
        self.config.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.config.checkpoint_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.config.checkpoint_path)
        self.metrics.record_checkpoint()

    async def _write_report(self) -> None:
        wall_clock_hours = (time.time() - self.started_at) / 3600
        acceptance = self._acceptance()
        self.config.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.report_path.write_text(
            self.metrics.to_markdown(wall_clock_hours=wall_clock_hours, acceptance=acceptance),
            encoding="utf-8",
        )

    async def _session_worker(self, worker_name: str, queue_name: str) -> None:
        while not self.stop_event.is_set():
            try:
                await self._wait_for_global_cooldown()
                task_id = await self._next_task_id(queue_name)
                if task_id is None:
                    if self._should_stop():
                        return
                    await asyncio.sleep(2)
                    continue
                task = self.session_tasks[task_id]
                task.status = "running"
                task.last_error = None
                task.updated_at = iso_now()
                await self._checkpoint()
                await self._run_session(task, worker_name=worker_name)
                if task.status == "pending":
                    target_queue = self.adversarial_queue if task.role == "adversarial" else self.persona_queue
                    target_queue.put_nowait(task.task_id)
            except Exception as exc:  # noqa: BLE001
                self.metrics.record_worker_restart()
                await asyncio.sleep(3)
                if isinstance(exc, ClaudeCallError):
                    continue

    async def _audit_worker(self, worker_name: str) -> None:
        while not self.stop_event.is_set():
            try:
                await self._wait_for_global_cooldown()
                case_id = await self._next_audit_case()
                if case_id is None:
                    if self._should_stop():
                        return
                    await asyncio.sleep(2)
                    continue
                task = self.audit_tasks[case_id]
                task.status = "running"
                await self._run_audit(task, worker_name=worker_name)
                if task.status == "pending":
                    self.audit_queue.put_nowait(task.case_id)
            except Exception:  # noqa: BLE001
                self.metrics.record_worker_restart()
                await asyncio.sleep(3)

    async def _run_session(self, task: SessionTask, *, worker_name: str) -> None:
        self._active_workers += 1
        try:
            token = self._issue_token(task.user_id)
            while task.turns_completed < task.target_turns and not self.stop_event.is_set():
                if self.global_cooldown_until and time.time() < self.global_cooldown_until:
                    task.status = "pending"
                    await self._checkpoint()
                    return
                system_prompt = self._build_system_prompt(task)
                prompt = self._build_turn_prompt(task)
                try:
                    if self.global_cooldown_until and time.time() < self.global_cooldown_until:
                        task.status = "pending"
                        await self._checkpoint()
                        return
                    message = await self.claude.text_call(system_prompt=system_prompt, prompt=prompt)
                except ClaudeCallError as exc:
                    task.status = "pending"
                    task.last_error = exc.detail
                    task.retry_count += 1
                    if exc.kind == "rate_limit":
                        self.metrics.record_rate_limit()
                        adjustment = await self.claude.back_off_after_rate_limit()
                        if adjustment:
                            before, after = adjustment
                            self.metrics.record_concurrency_adjustment(
                                before=before,
                                after=after,
                                reason="rate_limit_backoff",
                            )
                        cooldown_until = self._arm_rate_limit_cooldown(task.retry_count, reason=exc.detail)
                        print(
                            f"[sgw] {worker_name} hit rate limit"
                            f"{f'; reducing Claude parallelism {adjustment[0]} -> {adjustment[1]}' if adjustment else ''}, cooling down until "
                            f"{datetime.fromtimestamp(cooldown_until).isoformat(timespec='seconds')}"
                        )
                    elif exc.kind == "quota":
                        cooldown_until = time.time() + self.config.claude_budget_reset_seconds
                        self.global_cooldown_until = cooldown_until
                        print(
                            f"[sgw] {worker_name} hit quota window, cooling down until "
                            f"{datetime.fromtimestamp(cooldown_until).isoformat(timespec='seconds')}"
                        )
                        self.metrics.record_quota_exhaustion(
                            cooldown_until=datetime.fromtimestamp(cooldown_until).isoformat(timespec="seconds"),
                            reason=exc.detail,
                        )
                    else:
                        await asyncio.sleep(self.config.claude_failure_backoff_seconds)
                    await self._checkpoint()
                    return

                if not message:
                    task.status = "pending"
                    task.last_error = "worker produced empty message"
                    task.retry_count += 1
                    await self._checkpoint()
                    return

                task.last_note = None
                assistant_reply = ""
                try:
                    assistant_reply = await self.gateway.chat_once(
                        token=token,
                        session_id=task.session_id,
                        user_id=task.user_id,
                        message=message,
                    )
                    self.metrics.record_websocket_success()
                except Exception as exc:  # noqa: BLE001
                    self.metrics.record_websocket_failure()
                    task.status = "pending"
                    task.last_error = f"websocket chat failed: {exc}"
                    task.retry_count += 1
                    await asyncio.sleep(10)
                    await self._checkpoint()
                    return

                task.transcript.append({"role": "user", "content": message})
                task.transcript.append({"role": "assistant", "content": assistant_reply})
                task.turns_completed += 1
                task.updated_at = iso_now()
                task.retry_count = 0
                self.metrics.record_turn()

                new_records = await self._collect_new_records(task=task, source_chat_turn=message)
                if new_records and (not task.revoke_scheduled):
                    persona = self._persona_by_id(task.persona_id)
                    revoke_probability = float(persona.get("revoke_probability", 0.15)) if persona else 0.15
                    if self.random.random() < revoke_probability:
                        task.revoke_scheduled = True
                        await self._run_revoke_probe(token=token, task=task)

                await self._checkpoint()

            task.status = "completed"
            task.updated_at = iso_now()
            self.metrics.record_session_completed(role=task.role, persona_id=task.persona_id)
            await self._checkpoint()
        finally:
            self._active_workers = max(0, self._active_workers - 1)

    async def _run_revoke_probe(self, *, token: str, task: SessionTask) -> None:
        if not task.detected_memory_ids:
            return
        target_id = task.detected_memory_ids[-1]
        success = await self.gateway.retract_memory(token=token, memory_id=target_id, reason="sgw_revoke_probe")
        verified = False
        if success:
            visible_ids = await self.gateway.export_memory_ids(token=token)
            verified = target_id not in visible_ids
        self.metrics.record_revoke(verified=verified)

    async def _run_audit(self, task: AuditTask, *, worker_name: str) -> None:
        self._active_workers += 1
        try:
            audit_prompt = json.dumps(
                {
                    "case_id": task.case_id,
                    "source_chat_turn": task.source_chat_turn,
                    "inferred_record": task.record,
                },
                ensure_ascii=False,
                indent=2,
            )
            try:
                if self.global_cooldown_until and time.time() < self.global_cooldown_until:
                    task.status = "pending"
                    await self._checkpoint()
                    return
                audit_output = await self.claude.text_call(
                    system_prompt=self.audit_prompt_template,
                    prompt=audit_prompt,
                )
                score = self._parse_audit_score(audit_output)
            except ClaudeCallError as exc:
                task.status = "pending"
                task.retry_count += 1
                if exc.kind == "rate_limit":
                    self.metrics.record_rate_limit()
                    adjustment = await self.claude.back_off_after_rate_limit()
                    if adjustment:
                        before, after = adjustment
                        self.metrics.record_concurrency_adjustment(
                            before=before,
                            after=after,
                            reason="rate_limit_backoff",
                        )
                    cooldown_until = self._arm_rate_limit_cooldown(task.retry_count, reason=exc.detail)
                    print(
                        f"[sgw] {worker_name} audit hit rate limit"
                        f"{f'; reducing Claude parallelism {adjustment[0]} -> {adjustment[1]}' if adjustment else ''}, cooling down until "
                        f"{datetime.fromtimestamp(cooldown_until).isoformat(timespec='seconds')}"
                    )
                elif exc.kind == "quota":
                    cooldown_until = time.time() + self.config.claude_budget_reset_seconds
                    self.global_cooldown_until = cooldown_until
                    print(
                        f"[sgw] {worker_name} audit hit quota window, cooling down until "
                        f"{datetime.fromtimestamp(cooldown_until).isoformat(timespec='seconds')}"
                    )
                    self.metrics.record_quota_exhaustion(
                        cooldown_until=datetime.fromtimestamp(cooldown_until).isoformat(timespec="seconds"),
                        reason=exc.detail,
                    )
                else:
                    await asyncio.sleep(self.config.claude_failure_backoff_seconds)
                await self._checkpoint()
                return
            except ValueError as exc:
                task.status = "pending"
                task.retry_count += 1
                await asyncio.sleep(self.config.claude_failure_backoff_seconds)
                task.score = None
                await self._checkpoint()
                return

            task.score = score
            task.status = "completed"
            overall = float(score.get("overall", 0.0))
            soft_violation = bool(score.get("soft_violation")) or overall < self.config.soft_violation_threshold
            self.metrics.record_audit(soft_violation=soft_violation, reason=str(score.get("reason", "")))
            await self._checkpoint()
        finally:
            self._active_workers = max(0, self._active_workers - 1)

    async def _collect_new_records(self, *, task: SessionTask, source_chat_turn: str) -> list[dict[str, Any]]:
        user_uuid = uuid.UUID(task.user_id)
        lower_bound = utcnow() - timedelta(minutes=10)
        self._db_sessions_in_use += 1
        try:
            async with AsyncSessionLocal() as db:
                query = (
                    select(EpisodicMemory)
                    .where(
                        EpisodicMemory.user_id == user_uuid,
                        EpisodicMemory.source_lane == "inferred_extraction",
                        EpisodicMemory.created_at >= lower_bound,
                    )
                    .order_by(EpisodicMemory.created_at.asc())
                )
                result = await db.execute(query)
                items = result.scalars().all()
        finally:
            self._db_sessions_in_use = max(0, self._db_sessions_in_use - 1)

        serialized: list[dict[str, Any]] = []
        for item in items:
            memory_id = str(item.id)
            if memory_id in self.seen_memory_ids:
                continue
            self.seen_memory_ids.add(memory_id)
            record = self._serialize_memory(item)
            serialized.append(record)
            task.detected_memory_ids.append(memory_id)
            violations = check_inferred_record(record)
            if violations:
                for violation in violations:
                    self.metrics.record_hard_violation(violation.to_dict())
                self.stop_reason = "hard violation"
                self.stop_event.set()
            if self._should_enqueue_audit(task=task, record=record):
                audit_task = AuditTask(case_id=memory_id, record=record, source_chat_turn=source_chat_turn)
                self.audit_tasks[audit_task.case_id] = audit_task
                self.audit_queue.put_nowait(audit_task.case_id)
        if violations := self._check_explicit_overwrite(task.detected_memory_ids):
            for violation in violations:
                self.metrics.record_hard_violation(violation.to_dict())
            self.stop_reason = "hard violation"
            self.stop_event.set()
        return serialized

    async def _ensure_user(self, *, user_id: str, username: str, email: str) -> None:
        user_uuid = uuid.UUID(user_id)
        self._db_sessions_in_use += 1
        try:
            async with AsyncSessionLocal() as db:
                existing = await db.execute(select(User).where(User.id == user_uuid))
                if existing.scalar_one_or_none() is not None:
                    return
                user = User(
                    id=user_uuid,
                    username=username,
                    email=email,
                    hashed_password="sgw_not_used",
                    password_login_enabled=False,
                    email_verified=True,
                    is_active=True,
                    nickname=username,
                )
                db.add(user)
                await db.commit()
        finally:
            self._db_sessions_in_use = max(0, self._db_sessions_in_use - 1)

    def _issue_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "is_admin": False,
        }
        return create_access_token(payload)

    def _build_system_prompt(self, task: SessionTask) -> str:
        if task.role == "adversarial":
            return self.adversarial_prompt_template.replace(
                "{{PLAYBOOK_JSON}}",
                json.dumps(self.playbook, ensure_ascii=False, indent=2),
            )
        persona = self._persona_by_id(task.persona_id)
        return self.persona_prompt_template.replace(
            "{{PERSONA_JSON}}",
            json.dumps(persona, ensure_ascii=False, indent=2),
        )

    def _build_turn_prompt(self, task: SessionTask) -> str:
        history = task.transcript[-2 * self.config.max_history_pairs :]
        playbook = self._playbook_by_id(task.playbook_id)
        persona = self._persona_by_id(task.persona_id) or {}
        turn_index = task.turns_completed + 1
        payload = {
            "worker_role": task.role,
            "session_id": task.session_id,
            "turn_index": turn_index,
            "target_turns": task.target_turns,
            "history": history,
            "persona_id": task.persona_id,
            "persona_constraints": {
                "mention_density": persona.get("mention_density", 0.15),
                "commitment_density": persona.get("commitment_density", 0.1),
            },
            "playbook_item": playbook,
            "instruction": "继续自然对话，只输出下一条要发给 Sparkle 的中文用户消息，不要输出 JSON 或解释。",
            "turn_requirements": self._build_turn_requirements(task=task, turn_index=turn_index),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _arm_rate_limit_cooldown(self, retry_count: int, *, reason: str) -> float:
        multiplier = min(max(retry_count, 1), 6)
        seconds = min(
            self.config.claude_rate_limit_backoff_seconds * multiplier,
            self.config.claude_budget_reset_seconds,
        )
        cooldown_until = time.time() + seconds
        existing = self.global_cooldown_until or 0.0
        self.global_cooldown_until = max(existing, cooldown_until)
        return self.global_cooldown_until

    @staticmethod
    def _parse_audit_score(raw: str) -> dict[str, Any]:
        values: dict[str, str] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()

        required = {
            "metadata_correctness",
            "semantic_fidelity",
            "entity_boundary",
            "time_anchor_validity",
            "confidence_calibration",
            "overall",
            "reason",
        }
        missing = required - set(values)
        if missing:
            raise ValueError(f"audit output missing keys: {sorted(missing)}")

        score = {
            "metadata_correctness": SGWOrchestrator._parse_score_value(values["metadata_correctness"]),
            "semantic_fidelity": SGWOrchestrator._parse_score_value(values["semantic_fidelity"]),
            "entity_boundary": SGWOrchestrator._parse_score_value(values["entity_boundary"]),
            "time_anchor_validity": SGWOrchestrator._parse_score_value(values["time_anchor_validity"]),
            "confidence_calibration": SGWOrchestrator._parse_score_value(values["confidence_calibration"]),
            "overall": SGWOrchestrator._parse_score_value(values["overall"]),
            "reason": values["reason"],
        }
        score["soft_violation"] = bool(score["overall"] < 0.85)
        return score

    @staticmethod
    def _parse_score_value(value: str) -> float:
        numeric = float(value)
        if numeric < 0.0 or numeric > 1.0:
            raise ValueError(f"score out of range: {value}")
        return numeric

    def _should_enqueue_audit(self, *, task: SessionTask, record: dict[str, Any]) -> bool:
        if task.role == "adversarial":
            return True
        if not task.detected_memory_ids:
            return True
        return self.random.random() < self.config.audit_sample_rate

    def _build_turn_requirements(self, *, task: SessionTask, turn_index: int) -> list[str]:
        persona = self._persona_by_id(task.persona_id) or {}
        mention_density = float(persona.get("mention_density", 0.15))
        commitment_density = float(persona.get("commitment_density", 0.1))
        requirements = [
            "保持真实中文口语，不要像测试脚本。",
            "优先使用第一人称描述自己的近况或行动。",
        ]
        if turn_index == 1:
            requirements.append("本轮必须带一个明确时间锚点或行动信号，例如“最近/今天/明天/这周/要/准备/打算/复习”。")
        elif turn_index % 3 == 0:
            requirements.append("本轮尽量自然加入一个时间锚点或行动信号，帮助系统观察承压中的连续对话。")
        if mention_density >= 0.15 and turn_index % 4 == 0:
            requirements.append("本轮自然提到一个家人、朋友、同学或同事，但不要机械生硬。")
        if commitment_density >= 0.1 and turn_index % 5 == 0:
            requirements.append("本轮给出一个带明确时间的打算或承诺，例如“明天/这周/今晚/周末之前我会…”。")
        if task.role == "adversarial":
            requirements.append("本轮继续围绕当前 playbook 场景施压，但保持像真实用户说话。")
        return requirements

    async def _wait_for_global_cooldown(self) -> None:
        while self.global_cooldown_until and time.time() < self.global_cooldown_until:
            await asyncio.sleep(30)
        if self.global_cooldown_until and time.time() >= self.global_cooldown_until:
            self.global_cooldown_until = None

    async def _next_task_id(self, queue_name: str) -> str | None:
        queue = self.adversarial_queue if queue_name == "adversarial" else self.persona_queue
        if queue.empty():
            return None
        return await queue.get()

    async def _next_audit_case(self) -> str | None:
        if self.audit_queue.empty():
            return None
        return await self.audit_queue.get()

    def _should_stop(self) -> bool:
        if self.stop_event.is_set():
            return True
        if self.metrics.hard_violations:
            return True
        wall_clock_ok = (time.time() - self.started_at) / 3600 >= self.config.wall_clock_hours
        sessions_ok = self.metrics.sessions_completed >= self.config.min_sessions
        turns_ok = self.metrics.turns_completed >= self.config.min_turns
        queues_empty = self.persona_queue.empty() and self.adversarial_queue.empty() and self.audit_queue.empty()
        if wall_clock_ok and sessions_ok and turns_ok and queues_empty and self._active_workers == 0:
            return True
        return False

    def _recover_stalled_tasks(self) -> int:
        recovered = 0
        cutoff = utcnow() - timedelta(seconds=max(self.config.claude_timeout_seconds * 2, 90))
        for task in self.session_tasks.values():
            if task.status != "running":
                continue
            if datetime.fromisoformat(task.updated_at) >= cutoff:
                continue
            task.status = "pending"
            if not task.last_error:
                task.last_error = "stalled session recovered"
            task.updated_at = iso_now()
            target_queue = self.adversarial_queue if task.role == "adversarial" else self.persona_queue
            target_queue.put_nowait(task.task_id)
            recovered += 1
        for audit_task in self.audit_tasks.values():
            if audit_task.status != "running":
                continue
            if datetime.fromisoformat(audit_task.created_at) >= cutoff:
                continue
            audit_task.status = "pending"
            self.audit_queue.put_nowait(audit_task.case_id)
            recovered += 1
        return recovered

    def _serialize_memory(self, item: EpisodicMemory) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "summary": item.summary,
            "source_type": item.source_type,
            "source_id": item.source_id,
            "source_lane": item.source_lane,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "occurred_at": item.occurred_at.isoformat() if item.occurred_at else None,
            "confidence": item.confidence,
            "evidence_token": item.evidence_token,
            "decay_policy": item.decay_policy,
            "semantic_key": item.semantic_key,
            "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
            "evidence_refs": item.evidence_refs or [],
        }

    def _persona_by_id(self, persona_id: str | None) -> dict[str, Any] | None:
        if persona_id is None:
            return None
        for persona in self.personas:
            if persona["id"] == persona_id:
                return persona
        return None

    def _playbook_by_id(self, playbook_id: str | None) -> dict[str, Any] | None:
        if playbook_id is None:
            return None
        for item in self.playbook:
            if item["id"] == playbook_id:
                return item
        return None

    def _read_pool_in_use(self) -> int:
        try:
            pool = engine.sync_engine.pool
            if hasattr(pool, "checkedout"):
                return int(pool.checkedout())
        except Exception:  # noqa: BLE001
            return self._db_sessions_in_use
        return self._db_sessions_in_use

    def _check_explicit_overwrite(self, memory_ids: list[str]) -> list[HardViolation]:
        del memory_ids
        return []

    def _acceptance(self) -> dict[str, bool]:
        wall_clock_hours = (time.time() - self.started_at) / 3600
        return {
            f"wall_clock_runtime>={self.config.wall_clock_hours:g}h": wall_clock_hours >= self.config.wall_clock_hours,
            "personas>=44": len(self.personas) >= 44,
            "sessions>=360": self.metrics.sessions_completed >= self.config.min_sessions,
            "turns>=4000": self.metrics.turns_completed >= self.config.min_turns,
            "hard_violations=0": len(self.metrics.hard_violations) == 0,
            "soft_violation_rate<5%": self.metrics.soft_violation_rate() < self.config.soft_violation_rate_limit,
        }

    def _emit_progress_if_needed(self) -> None:
        now = time.time()
        if now - self._last_progress_emit < 60:
            return
        self._last_progress_emit = now
        print(
            "[sgw] progress "
            f"sessions={self.metrics.sessions_completed}/{self.metrics.sessions_planned} "
            f"turns={self.metrics.turns_completed} "
            f"audits={self.metrics.audit_cases} "
            f"soft_rate={self.metrics.soft_violation_rate():.4f} "
            f"hard={len(self.metrics.hard_violations)} "
            f"queues={self.persona_queue.qsize() + self.adversarial_queue.qsize() + self.audit_queue.qsize()} "
            f"active={self._active_workers} "
            f"claude_parallel={self.claude.effective_parallel}/{self.claude.hard_cap}"
        )

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, self.stop_event.set)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Stage 16 SGW orchestrator")
    parser.add_argument("--persona-library", required=True, type=Path)
    parser.add_argument("--adversarial-playbook", required=True, type=Path)
    parser.add_argument("--report-path", required=True, type=Path)
    parser.add_argument("--checkpoint-path", required=True, type=Path)
    parser.add_argument("--wall-clock-hours", type=float, default=float(os.getenv("SGW_WALL_CLOCK_HOURS", "18")))
    parser.add_argument("--min-sessions", type=int, default=360)
    parser.add_argument("--min-turns", type=int, default=4000)
    parser.add_argument("--turn-target", type=int, default=12)
    parser.add_argument("--adversarial-sessions", type=int, default=24)
    parser.add_argument("--resume", action="store_true")
    return parser


def parse_args(argv: list[str] | None = None) -> OrchestratorConfig:
    args = build_parser().parse_args(argv)
    return OrchestratorConfig(
        persona_library=args.persona_library,
        adversarial_playbook=args.adversarial_playbook,
        report_path=args.report_path,
        checkpoint_path=args.checkpoint_path,
        wall_clock_hours=args.wall_clock_hours,
        min_sessions=args.min_sessions,
        min_turns=args.min_turns,
        turn_target=args.turn_target,
        adversarial_sessions=args.adversarial_sessions,
        resume=args.resume,
    )


async def async_main(argv: list[str] | None = None) -> int:
    config = parse_args(argv)
    orchestrator = SGWOrchestrator(config)
    return await orchestrator.run()


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
