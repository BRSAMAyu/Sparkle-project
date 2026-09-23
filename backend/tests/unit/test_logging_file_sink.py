"""ENGINE-LOGROT · 引擎可选轮转文件 sink 回归测试。

覆盖三份契约（对应卡片验收口径）：
1. 配置了 ``LOG_FILE_PATH`` → 文件 sink 挂载成功，rotation/retention 参数
   按 settings 生效（小阈值真实触发轮转，证据行数零丢失）；
2. 未配置 → 严格 no-op，handler 集合不变——uvicorn 进程行为与本卡之前
   逐位一致；
3. 接线不回潮：``app/main.py`` 的 stderr sink 形制不被本卡改动，helper
   以 settings 字段挂载；``grpc_server.py`` 自带轮转文件 sink 保持原样
   （本卡明确不动 gRPC 进程）。
"""

from __future__ import annotations

import ast
from pathlib import Path

from loguru import logger as loguru_logger

from app.config.settings import Settings
from app.core.logging_setup import add_rotating_file_sink_if_configured, format_rotation_size

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _handler_ids() -> set[int]:
    # loguru 0.7 稳定内部结构；仅测试内用于 handler 集合对比
    return set(loguru_logger._core.handlers.keys())


# ---------------------------------------------------------------------------
# 1) rotation 参数形制
# ---------------------------------------------------------------------------


def test_format_rotation_size_integer_normalizes():
    assert format_rotation_size(20) == "20 MB"
    assert format_rotation_size(20.0) == "20 MB"


def test_format_rotation_size_decimal_kept_for_small_threshold_tests():
    assert format_rotation_size(0.05) == "0.05 MB"


def test_format_rotation_size_rejects_non_positive():
    for bad in (0, 0.0, -1, -0.5):
        try:
            format_rotation_size(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


# ---------------------------------------------------------------------------
# 2) 未配置 → 严格 no-op（与现状逐位一致）
# ---------------------------------------------------------------------------


def test_unconfigured_path_is_strict_noop():
    ids_before = _handler_ids()
    for empty in ("", "   "):
        assert add_rotating_file_sink_if_configured(empty) is None
    assert _handler_ids() == ids_before, "未配置路径时不得新增/改动任何 handler"


# ---------------------------------------------------------------------------
# 3) 配置了 → 文件 sink 挂载 + 参数正确
# ---------------------------------------------------------------------------


def test_configured_path_mounts_file_sink(tmp_path):
    log_file = tmp_path / "engine.log"
    ids_before = _handler_ids()
    hid = add_rotating_file_sink_if_configured(str(log_file), level="INFO", serialize=False)
    try:
        assert hid is not None
        assert hid in _handler_ids() and hid not in ids_before
        loguru_logger.info("LOGROT-MOUNT-PROBE {}", 1)
        loguru_logger.warning("LOGROT-MOUNT-PROBE {}", 2)
    finally:
        loguru_logger.remove(hid)

    text = log_file.read_text(encoding="utf-8")
    assert "LOGROT-MOUNT-PROBE 1" in text and "LOGROT-MOUNT-PROBE 2" in text


def test_file_sink_respects_level_filter(tmp_path):
    log_file = tmp_path / "engine_warn.log"
    hid = add_rotating_file_sink_if_configured(str(log_file), level="WARNING", serialize=False)
    try:
        loguru_logger.info("LOGROT-FILTERED-OUT")
        loguru_logger.warning("LOGROT-KEPT-IN")
    finally:
        loguru_logger.remove(hid)

    text = log_file.read_text(encoding="utf-8")
    assert "LOGROT-KEPT-IN" in text
    assert "LOGROT-FILTERED-OUT" not in text


def test_rotation_triggers_with_small_threshold_and_no_line_loss(tmp_path):
    log_file = tmp_path / "engine.log"
    hid = add_rotating_file_sink_if_configured(
        str(log_file), rotation_mb=0.05, retention=3, level="INFO", serialize=False
    )
    # 每行约 240B（默认格式 + 120 字符负载）：300 行 ≈ 72KB，恰好跨过一次
    # 0.05MB(≈52KB) 阈值、远低于第二次（≈104KB）——确定性单次轮转。
    total_lines = 300
    try:
        for i in range(total_lines):
            loguru_logger.info("LOGROT-ROTATE-PROBE {:04d} {}", i, "p" * 120)
    finally:
        loguru_logger.remove(hid)

    rotated = sorted(tmp_path.glob("engine*.log"))
    assert len(rotated) == 2, f"expected exactly one rotation (rotated + active), got {rotated}"
    # 轮转不得丢行——证据链完整的本质断言
    kept = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in rotated)
    assert kept == total_lines


# ---------------------------------------------------------------------------
# 4) settings 缺省契约：默认关闭
# ---------------------------------------------------------------------------


def test_settings_defaults_keep_file_sink_disabled():
    fields = Settings.model_fields
    assert fields["LOG_FILE_PATH"].default == ""
    assert fields["LOG_ROTATION_MB"].default == 20.0
    assert fields["LOG_RETENTION"].default == 10


# ---------------------------------------------------------------------------
# 5) 接线不回潮（AST 精确判定，不 import app.main 避免全应用副作用）
# ---------------------------------------------------------------------------


def _iter_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def test_main_stderr_sink_form_unchanged():
    src = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    stderr_adds = [
        node
        for node in _iter_calls(tree)
        if isinstance(node.func, ast.Attribute)
        and node.func.attr == "add"
        and node.args
        and isinstance(node.args[0], ast.Attribute)
        and node.args[0].attr == "stderr"
    ]
    assert len(stderr_adds) == 1, "uvicorn 进程 stderr sink 必须有且仅有一处"
    assert {kw.arg for kw in stderr_adds[0].keywords} == {"level", "serialize"}, (
        "stderr sink 形制（level/serialize）不得被本卡改动"
    )


def test_main_wires_optional_file_sink_via_settings():
    src = (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = [
        node
        for node in _iter_calls(tree)
        if getattr(node.func, "id", None) == "add_rotating_file_sink_if_configured"
    ]
    assert len(calls) == 1, "helper 在 main.py 必须有且仅有一处挂载调用"
    call = calls[0]
    assert len(call.args) == 1 and call.args[0].attr == "LOG_FILE_PATH"
    kw = {k.arg: getattr(k.value, "attr", None) for k in call.keywords}
    assert kw == {
        "rotation_mb": "LOG_ROTATION_MB",
        "retention": "LOG_RETENTION",
        "level": "LOG_LEVEL",
        "serialize": None,  # 表达式 not settings.DEBUG，非裸属性
    }


def test_grpc_entry_keeps_own_rotating_sink_untouched():
    src = (BACKEND_ROOT / "grpc_server.py").read_text(encoding="utf-8")
    assert "grpc_server_{time}.log" in src
    assert 'rotation="1 day"' in src
    assert "retention=" in src
