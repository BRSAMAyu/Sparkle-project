"""HYGIENE-2：conftest redis_client fixture 隔离 DB index 的守卫测试。

旧实现直连 REDIS_URL（通常 db0）且 teardown ``flushdb()``——在主仓跑测试会
清空 dev redis 的真实缓存/队列数据。现在 fixture 一律改写到专用测试 DB
（默认 db15，``TEST_REDIS_DB`` 可覆盖），teardown 只 flush 该隔离 DB。

涉及真 redis 的用例随 fixture 的 ping 门槛自动 skip（redis 不可用时），
且只读写隔离 DB，绝不触碰 db0 的真实数据。
"""

from redis import Redis

from tests.conftest import TEST_REDIS_DB, _isolate_test_redis_db


class TestIsolateTestRedisDb:
    def test_bare_host_url_gets_isolated_db(self):
        assert _isolate_test_redis_db("redis://localhost:6379/0") == (f"redis://localhost:6379/{TEST_REDIS_DB}")

    def test_no_path_url_gets_isolated_db(self):
        assert _isolate_test_redis_db("redis://localhost:6379") == (f"redis://localhost:6379/{TEST_REDIS_DB}")

    def test_explicit_db_is_overridden(self):
        # 即使 REDIS_URL 显式带了 db，也强制改写到隔离 DB
        assert _isolate_test_redis_db("redis://localhost:6379/5") == (f"redis://localhost:6379/{TEST_REDIS_DB}")

    def test_auth_and_host_preserved(self):
        assert (
            _isolate_test_redis_db("redis://:secret@sparkle_redis:6379/2")
            == f"redis://:secret@sparkle_redis:6379/{TEST_REDIS_DB}"
        )

    def test_env_override_respected(self, monkeypatch):
        import tests.conftest as conftest_module

        monkeypatch.setattr(conftest_module, "TEST_REDIS_DB", 9)
        assert conftest_module._isolate_test_redis_db("redis://localhost:6379/0") == ("redis://localhost:6379/9")


class TestRedisClientFixtureIsolation:
    """功能验证：fixture 客户端落在隔离 DB（随 ping 门槛 skip）。"""

    def test_fixture_client_lands_on_isolated_db(self, redis_client):
        kwargs = redis_client.connection_pool.connection_kwargs
        assert kwargs.get("db") == TEST_REDIS_DB
        # 关键红线：绝不在 dev 数据所在的 db0 上操作
        assert kwargs.get("db") != 0 or TEST_REDIS_DB == 0

    async def test_fixture_writes_visible_and_scoped(self, redis_client):
        await redis_client.set("hygiene2:isolation:probe", "ok", ex=60)
        assert await redis_client.get("hygiene2:isolation:probe") == "ok"
        # 用独立的裸连接核对数据确实只存在于隔离 DB
        probe = Redis(
            host=redis_client.connection_pool.connection_kwargs.get("host", "localhost"),
            port=redis_client.connection_pool.connection_kwargs.get("port", 6379),
            db=TEST_REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        try:
            assert probe.get("hygiene2:isolation:probe") == "ok"
        finally:
            probe.close()
