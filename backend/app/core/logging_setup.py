"""ENGINE-LOGROT · loguru 可选轮转文件 sink。

背景（PROD-LOG2 ④-P3）：引擎 uvicorn 进程的日志只挂 stderr sink，主会话以
nohup 重定向到 /tmp/*.log——每次重启旧文件被顶掉，证据链断裂（2026-09-23
巡检中 09:10 实例的日志即因此丢失）。gRPC 进程不受影响：``grpc_server.py``
自带 ``logs/grpc_server_{time}.log``（1 天轮转 / 7 天保留）。

设计裁决（显式开，非默认开）：
- ``LOG_FILE_PATH`` 默认空串 = **不挂载**，引擎行为与本卡合入前逐位一致；
- 仅当主会话在 .env（或启动 env）显式配置路径时才挂载文件 sink，且 stderr
  sink 一律保留（双写）；
- rotation/retention 由 ``LOG_ROTATION_MB``（默认 20）/``LOG_RETENTION``
  （默认 10 个文件）控制，与日志现量级匹配；
- 显式开而非默认开的理由：磁盘纪律（AGENTS.md 2026-09-19 立规）要求运行时
  数据可归口管理，默认落盘会让测试/CI/子 agent 环境意外产生文件；主会话是
  唯一合入方，由它决定路径（推荐 backend/logs/ 下，已被 .gitignore 覆盖，
  且不随 /tmp 清理丢失）。
"""

from __future__ import annotations

from typing import Any, cast

from loguru import logger


def format_rotation_size(rotation_mb: float) -> str:
    """把 MB 数值转成 loguru rotation 尺寸串。

    整数归一为 ``"20 MB"`` 形制；非整数保留小数（如 ``"0.05 MB"``），
    以便用小阈值在单测里真实触发轮转。非正数直接拒绝。
    """
    value = float(rotation_mb)
    if value <= 0:
        raise ValueError(f"rotation_mb must be > 0, got {rotation_mb!r}")
    if value.is_integer():
        return f"{int(value)} MB"
    return f"{value} MB"


def add_rotating_file_sink_if_configured(
    path: str,
    *,
    rotation_mb: float = 20,
    retention: int = 10,
    level: str = "INFO",
    serialize: bool = False,
    sink_logger: Any = logger,
) -> int | None:
    """按配置挂载轮转文件 sink；未配置路径时是严格 no-op。

    - ``path`` 空/空白 → 返回 ``None``，不触碰任何既有 handler（默认行为
      与本卡之前逐位一致）；
    - 配置了路径 → 以 ``"<N> MB"`` 尺寸轮转、保留 ``retention`` 个文件，
      与 stderr sink 同 level/serialize 语义；loguru 会自动创建父目录；
    - 返回挂载成功的 handler id（进程生命周期内有效，调用方无需持有）。
    """
    if not path or not path.strip():
        return None
    return cast("int | None", (sink_logger.add(
        path.strip(),
        level=level,
        serialize=serialize,
        rotation=format_rotation_size(rotation_mb),
        retention=retention,
    )))
