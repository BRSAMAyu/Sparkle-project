"""Journey harness 数据模型（B-03 跨端 Journey Simulator Harness 基线）。

journey 用例来源：v3/05_metrics_eval/GOLDEN_JOURNEYS.md（20 条 Golden Journeys）
与 v3/05_metrics_eval/USER_SIMULATION.md（真实 UI 操作、不许绕过体验层）。

设计约束：
- driver 可替换（web/android/api/macos），journey 步骤按 backend 分组声明；
- 每一步产出 StepResult，任何一步失败 => 整条 journey 失败且进程退出非零
  （不允许"没找到目标=PASS"，对应任务卡验收第 2 条）；
- 断言失败与异常都保留现场证据（截图/API 留存/DB 探针输出）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StepSpec:
    """journey 内一步。action 语义由各 driver 的 step handler 解释。"""

    name: str
    action: str
    args: dict[str, Any] = field(default_factory=dict)
    # 可选结构化断言（与 action 分离，便于 evidence 记录）
    assert_: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any], index: int) -> "StepSpec":
        if "action" not in raw:
            raise ValueError(f"step#{index} 缺少 action 字段: {raw!r}")
        return cls(
            name=str(raw.get("name") or raw["action"]),
            action=str(raw["action"]),
            args=dict(raw.get("args") or {}),
            assert_=raw.get("assert"),
        )


@dataclass
class JourneySpec:
    id: str
    title: str
    golden_ref: str
    description: str
    # backend 名（web/api/android/macos）-> 步骤列表；至少一个 backend 有步骤
    backends: dict[str, list[StepSpec]]
    # journey 结束后执行的只读 DB 断言（SELECT-only，经 docker exec psql）
    db_asserts: list[dict[str, Any]] = field(default_factory=list)
    # 平台适用性标记（GOLDEN_JOURNEYS.md 要求逐平台标记 applicable）
    platforms: dict[str, dict[str, Any]] = field(default_factory=dict)
    path: Path | None = None

    def steps_for(self, backend: str) -> list[StepSpec]:
        if backend not in self.backends or not self.backends[backend]:
            raise KeyError(
                f"journey {self.id} 没有 backend={backend} 的步骤定义；"
                f"可用 backends={sorted(self.backends)}"
            )
        return self.backends[backend]


@dataclass
class StepResult:
    name: str
    action: str
    ok: bool
    detail: str
    duration_ms: int
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "action": self.action,
            "ok": self.ok,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "artifacts": self.artifacts,
        }


@dataclass
class RunManifest:
    """一次 journey 运行的环境与产物清单（任务卡验收：build SHA/device/time/screenshots/log refs）。"""

    journey_id: str
    backend: str
    run_id: str
    started_at: str
    finished_at: str | None = None
    base_sha: str = ""
    final_sha: str = ""
    device: str = ""
    app_build: dict[str, Any] = field(default_factory=dict)
    gateway: str = ""
    steps: list[StepResult] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    ok: bool = False
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "journey_id": self.journey_id,
            "backend": self.backend,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "base_sha": self.base_sha,
            "final_sha": self.final_sha,
            "device": self.device,
            "app_build": self.app_build,
            "gateway": self.gateway,
            "ok": self.ok,
            "summary": self.summary,
            "steps": [s.to_dict() for s in self.steps],
            "artifacts": self.artifacts,
        }
