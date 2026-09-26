"""wt422 kill_switch 邻批扫雷：Celery/定时唤醒面补挂矩阵（V3-FIX-108/109）。

扫雷结论（base 实录红→绿）：
- V3-FIX-109：stage33 community 模式在 bridge 面（community_signal_bridge
  `_community_mode() != "live"` 即跳过）与 HTTP 面均有门，但 celery beat 面
  scan_community_cohort_signals → community_cohort_signal_task →
  spine.on_community_cohort_data 全链无门——开关关掉后社群错因数据仍被
  定时扫描并注入个人 Spine（与 2026-09-21 引擎内调度器绕过 stage38 开关
  同类：run_smart_push_cycle docstring 记录的烧钱事故根修先例）。
- V3-FIX-108：stage27 attractor 特征在 predictive 读取面有
  is_feature_enabled("attractor") 门，但 celery beat 面
  recompute_persdyn_attractors → PersDynAttractorService.recompute_all_users
  无门——attractor 关闭后仍全量重算并落库。
  （编号沿革：本项在 wt422 落地时曾按登记号 V3-FIX-110 提交，与 wt424 已
  占的 110 撞号，集成时重编为 V3-FIX-108；wt500 闭账时校正本文件与
  celery_tasks.py 注释中的旧编号残留。）

修法与既有开关门先例对齐（run_push_policy_scheduler / run_smart_push_cycle）：
- community 面：门 = get_feature_mode("community") != "live" 即跳过
  （bridge 同语义：off 与 shadow 都不得把社群数据写进个人系统）；
  scan 与 task 双层挂门（scan 省全量扫描，task 防独立派发路径）。
- attractor 面：门 = is_feature_enabled("attractor")（off 跳过；
  shadow/live 与 predictive 读取面同语义放行）。

判据锚点（V3-FIX-108/109 闭账时由 wt500 记录）：两类 beat 周期任务的
kill 判据均锚在**任务启动时读**（worker 侧执行时刻），而非 beat 注册/调度期——
crontab 注册表是静态配置，开关是动态状态；只有执行时刻读才能拦住
「调度后、执行前翻 off」的窗口。scan→task 双层各读一次同一开关，
task 不继承 scan 时刻的裁决（test_cohort_chain_rechecks_gate_at_task_start
锁定该锚点语义）。

其余面（HTTP/WS/定时唤醒主链）既有覆盖矩阵：
- HTTP：predictive/jitai/idiographic/metacognition/traits/task_reflection/
  policy/skills/scene 等服务入口自门控（各自 stage 开关单测锁定）。
- WS：journey_consumer_base.start() 挂 stage34 journey_subscribers 门，
  7 个 consumer 全部继承同一基类门（test_stage34_kill_switch.py）。
- 定时唤醒：run_smart_push_cycle 挂 stage38 push_scheduler 门
  （test_scheduler_push_kill_switch.py 三态矩阵）。
本文件补齐 Celery/beat 面矩阵。wt500 闭账：摘门突变检查实录
5 红（三处门各摘→对应 skip 测试全红、4 守卫放行测试不误伤）→复门全绿。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

import app.core.celery_tasks as celery_tasks_module
import app.db.session as db_session_module
import app.services.persdyn_attractor_service as persdyn_module
import app.signals.spine_orchestrator as spine_orchestrator_module
from app.core.celery_tasks import (
    community_cohort_signal_task,
    recompute_persdyn_attractors,
    scan_community_cohort_signals,
)
from app.services.aurora_stage27_foresight_kill_switch_service import (
    AuroraStage27ForesightKillSwitchService as Stage27Switch,
)
from app.services.aurora_stage33_kill_switch_service import (
    AuroraStage33KillSwitchService as Stage33Switch,
)

# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class _FakeRedis:
    """community cohort 链路所需的最小 redis 面：scan + get。"""

    def __init__(
        self,
        *,
        last_seen_keys: list[bytes] | None = None,
        node_keys: list[bytes] | None = None,
        signal_payload: bytes | None = None,
    ) -> None:
        self._last_seen_keys = last_seen_keys or []
        self._node_keys = node_keys or []
        self._signal_payload = signal_payload

    async def scan(self, *args, **kwargs):
        if "cursor" in kwargs:
            return "0", list(self._node_keys)
        return 0, list(self._last_seen_keys)

    async def get(self, key):
        if "community_signal" in str(key):
            return self._signal_payload
        return None


class _FakeSession:
    def __call__(self):
        return self

    async def __aenter__(self):
        return object()

    async def __aexit__(self, *exc):
        return False


class _SilentLogger:
    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass

    def opt(self, *a, **k):
        return self


def _patch_stage33_mode(monkeypatch, mode: str) -> None:
    monkeypatch.setattr(Stage33Switch, "get_feature_mode", AsyncMock(return_value=mode))


def _patch_stage27_attractor(monkeypatch, *, enabled: bool, mode: str) -> None:
    monkeypatch.setattr(Stage27Switch, "is_feature_enabled", AsyncMock(return_value=enabled))
    monkeypatch.setattr(Stage27Switch, "get_feature_mode", AsyncMock(return_value=mode))


def _patch_redis(monkeypatch, fake_redis) -> None:
    from app.core.cache import cache_service

    monkeypatch.setattr(cache_service, "redis", fake_redis, raising=False)


_SIGNAL = json.dumps(
    {
        "subject": "math",
        "common_mistake_patterns": [
            {"error_type": "sign_error", "error_category": "algebra", "count": 7, "user_count": 5}
        ],
    }
).encode()


# ---------------------------------------------------------------------------
# V3-FIX-109：stage33 community Celery 面
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_cohort_task_skips_when_community_mode_not_live(monkeypatch, mode):
    """开关未开（off/shadow）→ 社群错因不得注入个人 Spine（bridge 同语义）。"""
    spine = SimpleNamespaceLike()
    spine.on_community_cohort_data = AsyncMock(return_value=None)
    monkeypatch.setattr(
        spine_orchestrator_module, "get_spine_orchestrator", lambda redis_client=None: spine
    )
    _patch_stage33_mode(monkeypatch, mode)

    result = community_cohort_signal_task("u1", "n1")

    spine.on_community_cohort_data.assert_not_called()
    assert result["status"] == "skipped"


def test_cohort_task_injects_when_community_mode_live(monkeypatch):
    """开关 live → 正常注入（开关不得误伤正常链）。"""
    spine = SimpleNamespaceLike()
    spine.on_community_cohort_data = AsyncMock(return_value=object())
    monkeypatch.setattr(
        spine_orchestrator_module, "get_spine_orchestrator", lambda redis_client=None: spine
    )
    _patch_stage33_mode(monkeypatch, "live")
    _patch_redis(
        monkeypatch,
        _FakeRedis(signal_payload=_SIGNAL),
    )

    result = community_cohort_signal_task("u1", "n1")

    spine.on_community_cohort_data.assert_awaited_once()
    assert result["status"] == "injected"


@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_cohort_scan_skips_when_community_mode_not_live(monkeypatch, mode):
    """beat 扫描任务：开关未开 → 不扫不派发（scan 层省全量扫描）。"""
    dispatch = AsyncMock(return_value=True)
    monkeypatch.setattr(celery_tasks_module, "dispatch_task_async", dispatch)
    _patch_stage33_mode(monkeypatch, mode)
    _patch_redis(
        monkeypatch,
        _FakeRedis(
            last_seen_keys=[b"spine:last_seen:u1"],
            node_keys=[b"galaxy:user_nodes:u1:n1"],
            signal_payload=_SIGNAL,
        ),
    )

    result = scan_community_cohort_signals(limit=10)

    dispatch.assert_not_called()
    assert result["dispatched"] == 0


def test_cohort_scan_dispatches_when_community_mode_live(monkeypatch):
    """开关 live → 扫描链正常派发。"""
    dispatch = AsyncMock(return_value=True)
    monkeypatch.setattr(celery_tasks_module, "dispatch_task_async", dispatch)
    _patch_stage33_mode(monkeypatch, "live")
    _patch_redis(
        monkeypatch,
        _FakeRedis(
            last_seen_keys=[b"spine:last_seen:u1"],
            node_keys=[b"galaxy:user_nodes:u1:n1"],
            signal_payload=_SIGNAL,
        ),
    )

    result = scan_community_cohort_signals(limit=10)

    dispatch.assert_awaited_once()
    assert result["dispatched"] == 1


def test_cohort_chain_rechecks_gate_at_task_start(monkeypatch):
    """锚点语义锁（wt500 V3-FIX-109 闭账）：scan 与 task 各自在任务启动时
    读开关，task 不继承 scan 时刻的裁决。

    beat 链 scan（每 8h tick）→ 派发 → task 执行之间存在时间窗：开关在
    scan 之后翻 off 时，task 层必须在执行时刻再读一次并早退。若 task 层
    门被摘（回归形态=只留 scan 层门），本测试红。
    """
    spine = SimpleNamespaceLike()
    spine.on_community_cohort_data = AsyncMock(return_value=object())
    monkeypatch.setattr(
        spine_orchestrator_module, "get_spine_orchestrator", lambda redis_client=None: spine
    )
    dispatch = AsyncMock(return_value=True)
    monkeypatch.setattr(celery_tasks_module, "dispatch_task_async", dispatch)
    # 第一次读=scan 启动时刻（live 放行），第二次读=task 启动时刻（已翻 off）。
    monkeypatch.setattr(
        Stage33Switch,
        "get_feature_mode",
        AsyncMock(side_effect=["live", "off"]),
    )
    _patch_redis(
        monkeypatch,
        _FakeRedis(
            last_seen_keys=[b"spine:last_seen:u1"],
            node_keys=[b"galaxy:user_nodes:u1:n1"],
            signal_payload=_SIGNAL,
        ),
    )

    scan_result = scan_community_cohort_signals(limit=10)
    assert scan_result["dispatched"] == 1  # scan 时刻开关仍 live，正常派发
    dispatch.assert_awaited_once()

    task_result = community_cohort_signal_task("u1", "n1")

    spine.on_community_cohort_data.assert_not_called()  # task 时刻开关已翻 off
    assert task_result["status"] == "skipped"


# ---------------------------------------------------------------------------
# V3-FIX-108：stage27 attractor Celery 面
# ---------------------------------------------------------------------------


def test_persdyn_recompute_skips_when_attractor_off(monkeypatch):
    """attractor off → 不全量重算不落库（predictive 读取面已关，写面不得空转）。

    判据锚点=任务启动时读（worker 执行时刻，非 beat 注册期）：beat crontab
    静态、开关动态，执行时刻读才能拦住「调度后、执行前翻 off」窗口。
    """
    service = SimpleNamespaceLike()
    service.recompute_all_users = AsyncMock(return_value=3)
    monkeypatch.setattr(persdyn_module, "PersDynAttractorService", lambda session: service)
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", _FakeSession())
    _patch_stage27_attractor(monkeypatch, enabled=False, mode="off")

    result = recompute_persdyn_attractors()

    service.recompute_all_users.assert_not_called()
    assert result["status"] == "skipped"


@pytest.mark.parametrize("mode", ["shadow", "live"])
def test_persdyn_recompute_runs_when_attractor_enabled(monkeypatch, mode):
    """attractor shadow/live（is_feature_enabled 语义）→ 重算放行，与读取面同门。"""
    service = SimpleNamespaceLike()
    service.recompute_all_users = AsyncMock(return_value=3)
    monkeypatch.setattr(persdyn_module, "PersDynAttractorService", lambda session: service)
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", _FakeSession())
    _patch_stage27_attractor(monkeypatch, enabled=True, mode=mode)

    result = recompute_persdyn_attractors()

    service.recompute_all_users.assert_awaited_once()
    assert result["status"] == "success"
    assert result["updated_users"] == 3


class SimpleNamespaceLike:
    pass
