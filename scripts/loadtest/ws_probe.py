"""WebSocket upgrade 压测基础库（stdlib-only，无第三方依赖）。

为 WS-TICKET-DESIGN §6.2 S1-S5 场景提供可复用原语：
- HS256 JWT 造币（与网关 JWT_HS256_FALLBACK 校验链一致）
- WS 升级握手探测（只取 HTTP 状态码，不建立会话）
- 完整 WS 连接（含 server ping/pong、close 帧码捕获）
- ticket 签发（POST /api/v1/ws/ticket）
- Prometheus /metrics 文本解析（counter 增量计算）
- swap 看门狗（每 15s 自查，free < 阈值触发中止事件）

设计约束（16GB 本机夜间有界执行）：并发由调用方封顶，本库单请求无重试、
短超时，任何探针失败不抛断言异常（压测要的是分布，不是单点成败）。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import socket
import struct
import subprocess
import threading
import time
import urllib.parse
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# ---------------------------------------------------------------------------
# JWT（HS256，匹配网关 validateJWT 的 fallback 校验：sub/type=access/exp）
# ---------------------------------------------------------------------------

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def mint_hs256_jwt(
    secret: str,
    sub: str,
    ttl_seconds: int = 300,
    issuer: str = "sparkle-gateway",
    audience: str = "sparkle-app",
) -> str:
    """签一个网关接受的 access token（type=access，jti 随机）。"""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {
        "sub": sub,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": issuer,
        "aud": audience,
    }
    signing_input = (
        _b64url(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64url(json.dumps(claims, separators=(",", ":")).encode())
    )
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return signing_input + "." + _b64url(sig)


def garbage_jwt() -> str:
    """结构像 JWT 但签名必错的垃圾载荷（S1 的 1/3 载荷之一）。"""
    return _b64url(secrets.token_bytes(24)) + "." + _b64url(secrets.token_bytes(48)) + ".sig"


# ---------------------------------------------------------------------------
# HTTP / WS 握手原语
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    status: int = 0
    retry_after: Optional[str] = None
    body_snippet: str = ""
    elapsed_ms: float = 0.0
    error: str = ""


def _connect(host: str, port: int, timeout: float) -> socket.socket:
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    return s


def _send_upgrade_request(
    s: socket.socket,
    host: str,
    port: int,
    path: str,
    xff: Optional[str],
    extra_headers: Optional[dict] = None,
) -> None:
    headers = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}:{port}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        # RFC 6455：16 字节随机数的标准 base64（含 padding，24 字符）；
        # gorilla 会硬校验 key 长度，urlsafe 无填充编码会被 400 拒绝
        "Sec-WebSocket-Key: " + base64.b64encode(secrets.token_bytes(16)).decode(),
        "Sec-WebSocket-Version: 13",
    ]
    if xff:
        headers.append(f"X-Forwarded-For: {xff}")
    for k, v in (extra_headers or {}).items():
        headers.append(f"{k}: {v}")
    s.sendall(("\r\n".join(headers) + "\r\n\r\n").encode())


def _read_response_head(s: socket.socket) -> tuple[int, dict, bytes]:
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
        if len(buf) > 65536:
            break
    head, _, rest = buf.partition(b"\r\n\r\n")
    lines = head.decode(errors="replace").split("\r\n")
    status = 0
    if lines and lines[0].startswith("HTTP/"):
        try:
            status = int(lines[0].split()[1])
        except (IndexError, ValueError):
            status = 0
    headers: dict = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return status, headers, rest


def ws_upgrade_probe(
    host: str,
    port: int,
    path: str,
    xff: Optional[str] = None,
    extra_headers: Optional[dict] = None,
    timeout: float = 5.0,
) -> ProbeResult:
    """发一次 WS 升级握手，只取状态码 / Retry-After（不建会话，秒断）。"""
    r = ProbeResult()
    t0 = time.monotonic()
    s = None
    try:
        s = _connect(host, port, timeout)
        _send_upgrade_request(s, host, port, path, xff, extra_headers)
        status, headers, rest = _read_response_head(s)
        r.status = status
        r.retry_after = headers.get("retry-after")
        r.body_snippet = rest[:120].decode(errors="replace")
    except Exception as exc:  # noqa: BLE001 压测原语：记录错误而非中断
        r.error = f"{type(exc).__name__}: {exc}"
    finally:
        if s:
            try:
                s.close()
            except OSError:
                pass
    r.elapsed_ms = (time.monotonic() - t0) * 1000
    return r


# ---------------------------------------------------------------------------
# 完整 WS 客户端（handshake + 帧读写 + close 码捕获）
# ---------------------------------------------------------------------------

@dataclass
class WSConn:
    accepted: bool
    status: int = 0
    close_code: Optional[int] = None
    close_reason: str = ""
    frames_received: int = 0
    _sock: Optional[socket.socket] = None
    _buf: bytes = b""
    error: str = ""

    def recv_frame(self, timeout: float = 5.0) -> Optional[tuple[int, bytes]]:
        """读一帧，返回 (opcode, payload)；对端关闭或超时返回 None。

        自动应答 server ping（RFC 6455 要求 pong 掩码）。
        """
        s = self._sock
        if s is None:
            return None
        s.settimeout(timeout)
        while True:
            frame = self._try_parse_frame()
            if frame is not None:
                opcode, payload = frame
                if opcode == 0x9:  # ping -> pong（客户端帧必须掩码）
                    try:
                        s.sendall(_mask_frame(0xA, payload))
                    except OSError:
                        return None
                    continue
                if opcode == 0x8:  # close
                    self.close_code = struct.unpack("!H", payload[:2])[0] if len(payload) >= 2 else None
                    self.close_reason = payload[2:].decode(errors="replace")
                    return (0x8, payload)
                self.frames_received += 1
                return (opcode, payload)
            try:
                chunk = s.recv(4096)
            except (socket.timeout, TimeoutError):
                return None
            except OSError:
                return None
            if not chunk:
                return None
            self._buf += chunk

    def _try_parse_frame(self) -> Optional[tuple[int, bytes]]:
        buf = self._buf
        if len(buf) < 2:
            return None
        opcode = buf[0] & 0x0F
        masked = (buf[1] & 0x80) != 0
        length = buf[1] & 0x7F
        offset = 2
        if length == 126:
            if len(buf) < 4:
                return None
            length = struct.unpack("!H", buf[2:4])[0]
            offset = 4
        elif length == 127:
            if len(buf) < 10:
                return None
            length = struct.unpack("!Q", buf[2:10])[0]
            offset = 10
        if masked:
            if len(buf) < offset + 4:
                return None
            offset += 4
        if len(buf) < offset + length:
            return None
        payload = buf[offset : offset + length]
        self._buf = buf[offset + length :]
        return opcode, payload

    def close(self, code: int = 1000) -> None:
        if self._sock is not None:
            try:
                self._sock.sendall(_mask_frame(0x8, struct.pack("!H", code)))
                self._sock.close()
            except OSError:
                pass
            self._sock = None


def _mask_frame(opcode: int, payload: bytes) -> bytes:
    mask = secrets.token_bytes(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytes([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header += bytes([0x80 | length])
    elif length < 65536:
        header += bytes([0x80 | 126]) + struct.pack("!H", length)
    else:
        header += bytes([0x80 | 127]) + struct.pack("!Q", length)
    return header + mask + masked


def ws_connect(
    host: str,
    port: int,
    path: str,
    xff: Optional[str] = None,
    timeout: float = 5.0,
) -> WSConn:
    """完整 WS 升级；accepted=True 时返回可读帧的连接。"""
    try:
        s = _connect(host, port, timeout)
    except Exception as exc:  # noqa: BLE001
        return WSConn(accepted=False, error=f"{type(exc).__name__}: {exc}")
    _send_upgrade_request(s, host, port, path, xff)
    status, headers, _ = _read_response_head(s)
    # 严格 accept 值校验留给协议单测；压测只认 101 + Sec-WebSocket-Accept 头存在
    if status != 101 or "sec-websocket-accept" not in headers:
        try:
            s.close()
        except OSError:
            pass
        return WSConn(accepted=False, status=status)
    return WSConn(accepted=True, status=status, _sock=s)


# ---------------------------------------------------------------------------
# ticket 签发
# ---------------------------------------------------------------------------

def issue_ticket(
    host: str,
    port: int,
    jwt: str,
    xff: Optional[str] = None,
    timeout: float = 5.0,
) -> ProbeResult:
    """POST /api/v1/ws/ticket（Bearer JWT），返回 ticket JSON 或状态码。"""
    r = ProbeResult()
    t0 = time.monotonic()
    s = None
    try:
        s = _connect(host, port, timeout)
        body = json.dumps({})
        headers = [
            "POST /api/v1/ws/ticket HTTP/1.1",
            f"Host: {host}:{port}",
            "Content-Type: application/json",
            "Content-Length: " + str(len(body)),
            "Authorization: Bearer " + jwt,
        ]
        if xff:
            headers.append(f"X-Forwarded-For: {xff}")
        s.sendall(("\r\n".join(headers) + "\r\n\r\n" + body).encode())
        status, hdrs, rest = _read_response_head(s)
        r.status = status
        r.retry_after = hdrs.get("retry-after")
        # Content-Length 小（<256B），一次头部读取通常已含 body
        r.body_snippet = rest.decode(errors="replace")
    except Exception as exc:  # noqa: BLE001
        r.error = f"{type(exc).__name__}: {exc}"
    finally:
        if s:
            try:
                s.close()
            except OSError:
                pass
    r.elapsed_ms = (time.monotonic() - t0) * 1000
    return r


def ticket_from_result(r: ProbeResult) -> str:
    try:
        return json.loads(r.body_snippet).get("ticket", "")
    except (json.JSONDecodeError, AttributeError):
        return ""


def authed_ws_path(ticket: str) -> str:
    return "/ws/chat?ticket=" + urllib.parse.quote(ticket)


# ---------------------------------------------------------------------------
# Prometheus /metrics 抓取
# ---------------------------------------------------------------------------

_METRIC_LINE = re.compile(r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?P<labels>\{[^}]*\})?\s+(?P<value>[-+0-9.eE]+)$")


def scrape_metrics(host: str, port: int, timeout: float = 5.0) -> dict[str, dict[str, float]]:
    """抓 /metrics，返回 {metric_name: {label串或"": value}}（只取非 HELP/TYPE 行）。"""
    s = None
    out: dict[str, dict[str, float]] = {}
    try:
        s = _connect(host, port, timeout)
        req = f"GET /metrics HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        _, _, body = raw.partition(b"\r\n\r\n")
        # 简易去 chunked
        if b"Transfer-Encoding: chunked" in raw.partition(b"\r\n\r\n")[0]:
            body = _dechunk(body)
        for line in body.decode(errors="replace").splitlines():
            m = _METRIC_LINE.match(line.strip())
            if not m:
                continue
            name = m.group("name")
            labels = m.group("labels") or ""
            try:
                out.setdefault(name, {})[labels] = float(m.group("value"))
            except ValueError:
                continue
    except Exception:  # noqa: BLE001 抓取失败返回空表，由调用方报错
        pass
    finally:
        if s:
            try:
                s.close()
            except OSError:
                pass
    return out


def _dechunk(body: bytes) -> bytes:
    out = []
    while True:
        head, _, rest = body.partition(b"\r\n")
        try:
            size = int(head.strip().split(b";")[0], 16)
        except ValueError:
            break
        if size == 0:
            break
        out.append(rest[:size])
        body = rest[size + 2 :]
    return b"".join(out)


def counter_delta(before: dict, after: dict, name: str) -> dict[str, float]:
    """计算某 counter 按标签的增量（before 缺失按 0 计）。"""
    b = before.get(name, {})
    a = after.get(name, {})
    keys = set(b) | set(a)
    return {k: round(a.get(k, 0.0) - b.get(k, 0.0), 3) for k in sorted(keys)}


# ---------------------------------------------------------------------------
# swap 看门狗（16GB 本机纪律：每 15s 自查，free<800MB 置中止事件）
# ---------------------------------------------------------------------------

@dataclass
class SwapWatchdog:
    interval_s: float = 15.0
    abort_free_mb: float = 800.0
    log: list = field(default_factory=list)
    abort_event: threading.Event = field(default_factory=threading.Event)
    truncation_note: str = ""
    _thread: Optional[threading.Thread] = None
    _stop = threading.Event()

    def _sample(self) -> Optional[float]:
        try:
            out = subprocess.run(
                ["sysctl", "-n", "vm.swapusage"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            m = re.search(r"free = ([0-9.]+)M", out)
            return float(m.group(1)) if m else None
        except (subprocess.SubprocessError, AttributeError):
            return None

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            free = self._sample()
            stamp = time.strftime("%H:%M:%S")
            if free is None:
                self.log.append(f"[{stamp}] swap sample failed")
                continue
            self.log.append(f"[{stamp}] swap_free_mb={free:.0f}")
            if free < self.abort_free_mb:
                self.truncation_note = (
                    f"ABORT at {stamp}: swap free {free:.0f}MB < {self.abort_free_mb:.0f}MB"
                )
                self.abort_event.set()
                return

    def start(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> list:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        return list(self.log)


# ---------------------------------------------------------------------------
# 节拍器：按目标 rps 匀速派发（并发封顶由调用方线程池控制）
# ---------------------------------------------------------------------------

def paced_deadlines(rate_rps: float, total: int) -> list[float]:
    """返回 total 个派发截止时刻（相对起点秒），匀速铺满 duration=total/rate。"""
    interval = 1.0 / rate_rps
    return [i * interval for i in range(total)]


def run_swarm(
    tasks: list[Callable[[], ProbeResult]],
    inflight: int,
    swap_watchdog: Optional[SwapWatchdog] = None,
    deadline_offset: Optional[list[float]] = None,
) -> tuple[list[ProbeResult], int]:
    """有界并发执行任务池。

    - inflight：并发封顶（硬上限，来自任务卡 ≤30）
    - deadline_offset：可选节拍（与 tasks 等长，相对秒）；派发超前则 sleep
    - swap_watchdog：置位 abort_event 时停止派发（在跑任务自然收尾）
    返回 (结果列表, 实际派发数)。串行场景由调用方逐场景调用即达成。
    """
    from concurrent.futures import ThreadPoolExecutor

    results: list[ProbeResult] = [ProbeResult(status=-1, error="not_run")] * len(tasks)
    t0 = time.monotonic()
    dispatched = 0
    with ThreadPoolExecutor(max_workers=inflight) as pool:
        futures = []
        for i, task in enumerate(tasks):
            if swap_watchdog and swap_watchdog.abort_event.is_set():
                break
            if deadline_offset is not None:
                wait = deadline_offset[i] - (time.monotonic() - t0)
                if wait > 0:
                    time.sleep(wait)
                if swap_watchdog and swap_watchdog.abort_event.is_set():
                    break
            futures.append((i, pool.submit(task)))
            dispatched += 1
        for i, fut in futures:
            try:
                results[i] = fut.result(timeout=120)
            except Exception as exc:  # noqa: BLE001
                results[i] = ProbeResult(status=-1, error=f"{type(exc).__name__}: {exc}")
    return results, dispatched
