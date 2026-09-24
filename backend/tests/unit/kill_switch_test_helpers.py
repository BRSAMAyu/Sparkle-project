"""Kill switch 测试共享内存桩。

kill switch 写路径只在 cache_service.redis 可用时才真正落键；Redis 缺席时
write_mode 显式告警并忽略写入、读路径回落 settings 默认（app/core/kill_switch.py:141-154）。
断言"提交值可回读"的测试若把 redis 注入 None，翻转即不可观察，读侧只能回落
settings 默认（全 "live"）——正确装配是注入本内存桩。

先例链：tests/unit/test_stage18_kill_switch.py 首立 _InMemoryKillSwitchRedis
（get/set）；wt341 在 test_memory_admin_api.py 扩展 delete/incr/expire；wt343 按
卡面授权（参照 tests/unit/foresight_test_helpers.py 的共享 helper 惯例）提炼为
本模块，并收敛各测试文件中的就地副本。

方法面覆盖 kill_switch 与 cache_service 实际调用的 redis 契约子集：
get / set(key, value, ex=...) / setex / delete / incr / incrby / expire /
scan_iter（cache_service.delete_pattern 需要，glob 语义对齐 fnmatchcase）。
（cache_service.set 底层固定以 ex= 关键字调用 set，见 app/core/cache.py:195。）
"""

from __future__ import annotations

import fnmatch


class InMemoryKillSwitchRedis:
    """内存版 redis 客户端桩：str→str 键值 + 独立计数器，无 TTL/连接语义。"""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0

    async def incr(self, key: str) -> int:
        return await self.incrby(key, 1)

    async def incrby(self, key: str, amount: int = 1) -> int:
        self._counters[key] = self._counters.get(key, 0) + int(amount)
        return self._counters[key]

    async def expire(self, key: str, ttl: int) -> bool:
        # 内存桩无 TTL 语义；仅对存在的键报告成功，与 redis.expire 布尔契约一致
        return key in self._counters or key in self._store

    def scan_iter(self, pattern: str):
        """异步迭代匹配键；glob 语义与 cache_service 本地兜底的 fnmatchcase 一致。"""

        async def _iter():
            for key in list(self._store):
                if fnmatch.fnmatchcase(key, pattern):
                    yield key

        return _iter()
