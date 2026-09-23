"""EXC-TRACEBACK · loguru ``exc_info=True`` 死参清零回归测试。

背景（wt187 LOGURU-BATCH 申报、本卡全量修复）：
- loguru 的 logger 不认 ``exc_info=``（未知 kwarg 被静默吞进 extra），
  传了 ``exc_info=True`` **堆栈也从不落日志**——与 stdlib logging 语义不同。
- 正确形制：``logger.opt(exception=True).<level>(...)``（except 块内、有活跃
  异常时）；``logger.exception`` 仅限 except 块内直呼场景。
- stdlib logging（``logging.getLogger`` 绑定）文件的 ``exc_info=True`` 是
  正确用法，不在本卡范围（守卫按 import 绑定甄别，不会误伤）。

本文件三层断言：
1. 守卫：全仓 loguru 绑定文件不得再出现 exc_info kwarg（AST 精确判定）。
2. 行为：迁移后的真实代码路径（cost_wvpl 除道路径）必须把 traceback 帧确实
   附到日志记录与渲染文本上。
3. 死参语义存档：证明旧写法（``exc_info=True`` 直传 loguru）堆栈确实丢失，
   防止回潮者误以为"传了就行"。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from loguru import logger

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _loguru_bound_names(tree: ast.AST) -> set[str]:
    """文件内绑定到 loguru logger 的名字（``from loguru import logger [as x]``）。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "loguru":
            for alias in node.names:
                if alias.name == "logger":
                    names.add(alias.asname or alias.name)
    return names


# ---------------------------------------------------------------------------
# 1) 守卫：loguru 源文件 exc_info 清零
# ---------------------------------------------------------------------------


def test_no_loguru_exc_info_in_loguru_sources():
    """loguru 绑定的 logger 调用不得再带 exc_info kwarg（stdlib 文件自动豁免）。"""
    targets = set(BACKEND_ROOT.glob("app/**/*.py")) | {
        p for p in BACKEND_ROOT.glob("*.py") if p.is_file()
    }
    offenders: list[str] = []
    for path in sorted(targets):
        src = path.read_text(encoding="utf-8")
        if "exc_info" not in src:
            continue
        tree = ast.parse(src, filename=str(path))
        loguru_names = _loguru_bound_names(tree)
        if not loguru_names:
            continue  # stdlib logging 文件：exc_info 是正确用法
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            root = node.func.value
            if not (isinstance(root, ast.Name) and root.id in loguru_names):
                continue
            if any(kw.arg == "exc_info" for kw in node.keywords):
                rel = path.relative_to(BACKEND_ROOT)
                offenders.append(f"{rel}:{node.lineno}")
    assert offenders == [], (
        "loguru 不支持 exc_info=（kwarg 被吞，堆栈静默丢失）；"
        f"请改用 logger.opt(exception=True).<level>(...)，位置：{offenders}"
    )


# ---------------------------------------------------------------------------
# 2) 行为：迁移后真实路径堆栈确实附加
# ---------------------------------------------------------------------------


class _ExplodingBreaker:
    """read_daily_spend 必炸的预算闸门替身（驱动 cost_wvpl 除道路径）。"""

    async def read_daily_spend(self, category: Any) -> float:
        raise ValueError("simulated redis down (EXC-TRACEBACK)")


async def test_migrated_path_attaches_traceback(monkeypatch, caplog) -> None:
    """cost_wvpl 读失败路径：loguru 记录必须携带活跃异常的完整 traceback 帧。"""
    import traceback

    from app.core import cost_wvpl_metrics

    monkeypatch.setattr(
        cost_wvpl_metrics, "get_budget_breaker", lambda: _ExplodingBreaker()
    )

    records: list[Any] = []
    handler_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG")
    rendered: list[str] = []
    text_id = logger.add(rendered.append, level="DEBUG")
    try:
        total = await cost_wvpl_metrics._daily_spend_all_categories()
    finally:
        logger.remove(handler_id)
        logger.remove(text_id)

    assert total == 0.0  # 单类目失败不拖垮聚合
    assert records, "迁移后的调用必须产出日志记录"
    exc_records = [r for r in records if r["level"].name == "DEBUG" and r["exception"]]
    assert exc_records, (
        "logger.opt(exception=True) 必须把活跃异常附到记录上（record.exception 非空）"
    )
    exc_type, exc_value, exc_tb = exc_records[0]["exception"]
    assert exc_type is ValueError
    assert "simulated redis down (EXC-TRACEBACK)" in str(exc_value)
    # traceback 帧确实出现：除道路径函数名必须出现在格式化帧序列里
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    assert "_daily_spend_all_categories" in tb_text or "read_daily_spend" in tb_text
    # 渲染文本（真正落 sink 的东西）也必须带 traceback，而不是只有消息行
    assert any("Traceback" in text or "ValueError" in text for text in rendered), (
        f"渲染文本缺少 traceback：{rendered[:1]}"
    )


def test_dead_kwarg_exc_info_is_swallowed_by_loguru():
    """存档断言：旧写法 ``logger.debug(..., exc_info=True)`` 在 loguru 下堆栈丢失。

    这是 wt187 申报的缺陷语义本尊——未知 kwarg 被吞进 extra，record.exception
    始终为 None。若未来有人改回直传 exc_info=，此测试红。
    """

    records: list[Any] = []
    handler_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG")
    try:
        try:
            raise RuntimeError("boom for dead-kwarg archive")
        except RuntimeError:
            logger.debug("legacy dead-kwarg call", exc_info=True)  # noqa: LOG015
    finally:
        logger.remove(handler_id)

    assert records, "记录应存在"
    assert records[0]["exception"] is None, (
        "loguru 直传 exc_info=True 不会附加堆栈（这正是要清零的死参）；"
        "若此断言变红说明 loguru 语义变化，需重审本卡全部迁移"
    )
