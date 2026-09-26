"""FIX-16 ①残留收口回归锁：优雅关停必须接通 post-commit 检索失效 drain。

E05X ②把检索失效改为事务 commit 后异步 spawn（消灭 DEL→commit 陈旧窗口）；
请求路径由 ``drain_session_retrieval_invalidations`` 在五处 sources handler 显式
await（live 3/3 变异承重），但进程关停路径此前未接线——残留任务要么撞上已关闭
Redis 客户端、要么被静默丢弃，陈旧版本化键将残留至 TTL（最长 30s 可重播旧版本
内容）。本文件钉死两面：

1. 行为面：``wait_for_pending_post_commit_invalidation`` 确实排空
   ``_PENDING_INVALIDATION_TASKS``（语义面，详测见
   tests/services/test_post_commit_retrieval_invalidation.py）；
2. 接线面：``app.main.lifespan`` 关停段确实调用该 drain——关停闭包无法在单测中
   直接驱动，按仓库契约钉惯例（inspect.getsource，同 test_signal_spine /
   test_memory_service_regression）对 lifespan 源做变异检查：摘除接线调用即红。
"""

from __future__ import annotations

import asyncio
import inspect

from app.services import source_lifecycle as sl


def test_wait_for_pending_post_commit_invalidation_drains_pending_set() -> None:
    """行为面：drain await 全部在飞任务后才返回，任务完成回调清空登记集。"""
    done_flag = False

    async def _scenario() -> None:
        nonlocal done_flag

        async def _slow() -> None:
            nonlocal done_flag

            await asyncio.sleep(0.05)
            done_flag = True

        task = asyncio.get_running_loop().create_task(_slow())
        sl._PENDING_INVALIDATION_TASKS.add(task)
        task.add_done_callback(sl._on_invalidation_task_done)

        await sl.wait_for_pending_post_commit_invalidation()
        # drain 返回时任务必须已完成、登记集必须已清空
        assert done_flag, "drain 返回时在飞失效任务尚未完成（语义破损）"
        assert task not in sl._PENDING_INVALIDATION_TASKS, "完成任务后登记集未清空"

    asyncio.run(_scenario())


def test_lifespan_shutdown_wires_post_commit_invalidation_drain() -> None:
    """接线面：main.lifespan 关停段必须调用 post-commit 失效 drain（变异承重）。"""
    from app.main import lifespan

    src = inspect.getsource(lifespan)
    # 断言必须钉在 await 调用上——只查名字会被 import 行假绿
    call = "await wait_for_pending_post_commit_invalidation()"
    assert call in src, (
        "FIX-16 ①残留：优雅关停未接通 post-commit 检索失效 drain——"
        "残留 DEL 将撞已关闭 Redis 或被静默丢弃（陈旧键残留至 TTL）"
    )
