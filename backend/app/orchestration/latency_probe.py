"""First-token latency profiling probe.

 Lightweight helper that records per-hop wall-clock durations inside
 ``ChatOrchestrator.process_stream`` and emits a single structured log line
 (``[LATENCY]``) when the probe finishes. The goal is to make the serial
 pre-first-token hop chain observable so regressions and wins are visible in
 engine logs without attaching a profiler.

 Usage:
        probe = LatencyProbe(session_id=session_id, request_id=request_id)
        ...
        with probe.hop("build_full_context"):
            await self._build_full_context(...)
        ...
        probe.finish(first_token=bool)
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from loguru import logger


class LatencyProbe:
    """Accumulates named hop durations and logs a compact summary."""

    def __init__(
        self,
        *,
        session_id: str = "",
        request_id: str = "",
        trace_id: str = "",
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self.session_id = session_id
        self.request_id = request_id
        # O-02 trace spine：[LATENCY] 行携带全链 trace_id，供按 trace 查询。
        self.trace_id = trace_id
        self._t0 = time.perf_counter()
        self._last = self._t0
        self._hops: list[tuple[str, float]] = []
        self._first_token_s: float | None = None

    @contextmanager
    def hop(self, name: str) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        start = time.perf_counter()
        try:
            yield
        finally:
            self._hops.append((name, time.perf_counter() - start))

    def mark(self, name: str) -> None:
        """Record the gap since the previous mark/step as a hop (non-context form)."""
        if not self.enabled:
            return
        now = time.perf_counter()
        self._hops.append((name, now - self._last))
        self._last = now

    def first_token(self) -> None:
        """Record time-to-first-streamed-content once."""
        if not self.enabled:
            return
        if self._first_token_s is None:
            self._first_token_s = time.perf_counter() - self._t0

    def finish(self) -> None:
        if not self.enabled or not self._hops:
            return
        total = time.perf_counter() - self._t0
        chain = " ".join(f"{name}={delta * 1000:.0f}ms" for name, delta in self._hops)
        first_token_part = (
            f" first_stream_content={self._first_token_s * 1000:.0f}ms"
            if self._first_token_s is not None
            else ""
        )
        trace_part = f" trace={self.trace_id}" if self.trace_id else ""
        logger.info(
            "[LATENCY] session={} request={}{} total={:.0f}ms{} hops: {}",
            self.session_id,
            self.request_id,
            trace_part,
            total * 1000,
            first_token_part,
            chain,
        )
