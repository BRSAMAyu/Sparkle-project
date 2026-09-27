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

# ---------------------------------------------------------------------------
# 仿真证据 schema/标记（B-03 红线：模拟器产出的数据必须可区分于真实驱动数据）
#
# 真实驱动（ns001 JOURNEY）证据写 sparkle.northstar.real-drive.*.v1
# （backend/tests/northstar_eval/real_drive.py，本 harness 只读参照、不碰其文件）。
# 仿真器证据一律写 sparkle.journey.simulator.*.v1 —— schema 字符串层面即可被
# 机器区分，任何聚合/统计都不会把 simulator run 误计为 real-drive run。
# ---------------------------------------------------------------------------

SIM_RUN_SCHEMA = "sparkle.journey.simulator.run.v1"
SIM_STEP_SCHEMA = "sparkle.journey.simulator.step.v1"

# lane 标记：结构化的通道声明（替代此前只藏在 summary 自由文本里的 non-ui 注记）。
LANE_UI = "simulator-ui"  # web/android/macos：真实 UI 通道
LANE_NONUI = "simulator-nonui"  # api：后端直驱冒烟，不得冒充 UI 实测

# 受控测试时钟裁决块（USER_SIMULATION longitudinal 要求 vs 产品现实）：
# 产品无时钟 seam（backend/tests/northstar_eval/real_drive.py「时间语义裁决」方案 c
# 已定谳：跨进程假钟会撕裂网关 JWT/DB now()/Redis TTL 与引擎时钟一致性，且伪造
# 证据时间戳）——故本 harness 的 run 一律真实墙钟；受控时钟推进 unsupported 并
# 登记原因，不静默缺失也不伪造。改此裁决必须先推翻 real_drive 的时间语义裁决。
CLOCK_WALL = {
    "mode": "wall",
    "controlled_advance": "unsupported",
    "reason": (
        "product has no clock seam (real_drive.py 时间语义裁决方案 c: 跨进程假钟撕裂"
        " JWT/DB/Redis 时钟一致性并伪造证据时间戳)；longitudinal Day-N 只允许真实跨日"
    ),
}


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
    # 声明的 test persona（v3/05_metrics_eval/persona_library.json 的 id，可选）。
    # 声明后 runner 记入 manifest（persona 可追溯）；未声明 = 该 journey 无 persona
    # 语义（如 GJ01S 最小壳），loader 不强求。
    persona: dict[str, Any] = field(default_factory=dict)
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
    """一次 journey 运行的环境与产物清单（任务卡验收：build SHA/device/time/screenshots/log refs）。

    schema/lane 字段是仿真-真实数据区分契约（见模块头注释）：run_manifest.json
    自标识为 sparkle.journey.simulator.run.v1 + simulator-ui/simulator-nonui lane，
    与 real-drive 证据（sparkle.northstar.real-drive.*）在 schema 字符串层面互斥。
    """

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
    schema: str = SIM_RUN_SCHEMA
    lane: str = LANE_UI
    persona: dict[str, Any] = field(default_factory=dict)
    clock: dict[str, Any] = field(default_factory=lambda: dict(CLOCK_WALL))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "lane": self.lane,
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
            "persona": self.persona,
            "clock": self.clock,
            "ok": self.ok,
            "summary": self.summary,
            "steps": [s.to_dict() for s in self.steps],
            "artifacts": self.artifacts,
        }
