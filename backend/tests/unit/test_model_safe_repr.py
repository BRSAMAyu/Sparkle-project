"""
wt588 SafeReprMixin IO-free repr 加固回归（V3-FIX-298 族防御）。

背景：V3-FIX-298 根因放大器——rollback/commit 会过期全部 ORM 加载属性，此后
日志/f-string 打印模型实例（如 loguru diagnose 逐帧 repr）会经
InstrumentedAttribute 描述符触发同步刷新 IO（greenlet 上下文外），抛
MissingGreenlet 并毒化共享会话。本文件钉死三条不变量：

1. ``app.models`` 下全部 ORM 模型类的 ``__repr__`` 均来自 SafeReprMixin
   （只读 ``inspect(instance).dict`` 已加载值字典，永不走描述符）；
2. 任何模型在 expired / detached / expunged 状态下 repr：不抛
   MissingGreenlet / DetachedInstanceError，且零 SQL 发射（事件计数）；
3. repr 不触碰 lazy 关系（unloaded 集合不变、零 SQL）。

对照锚点：同一对象同一状态下，描述符直读路径（``user.username``）确实抛
DetachedInstanceError / MissingGreenlet——证明旧手写 repr 的危险是真实的，
而 mixin 路径免疫。
"""

import importlib
import pkgutil
import uuid

import pytest
from sqlalchemy import event
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as models_pkg
from app.db.session import Base
from app.models.agent_run import AgentRun
from app.models.audit_log import SecurityAuditLog
from app.models.base import GUID, SafeReprMixin
from app.models.chat import ChatMessage, ChatSession
from app.models.idempotency_key import IdempotencyKey
from app.models.plan import Plan
from app.models.task import SubTask, Task
from app.models.user import User


def _import_all_models() -> None:
    """与 tests/conftest.py 同款：确保全部模型模块注册进 Base.registry。"""
    for mi in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"app.models.{mi.name}")


_import_all_models()

# ---------------------------------------------------------------------------
# 结构不变量：全模型 mixin 覆盖 + 无手写 __repr__ 回潮
# ---------------------------------------------------------------------------


def _orm_model_classes() -> list[type]:
    classes = []
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if cls.__module__.startswith("app.models"):
            classes.append(cls)
    return classes


def test_safe_repr_mixin_covers_all_orm_model_classes():
    classes = _orm_model_classes()
    assert len(classes) >= 200  # 当前 225，防半途而废
    missing = [cls for cls in classes if not issubclass(cls, SafeReprMixin)]
    assert missing == []


def test_no_model_class_defines_its_own_repr():
    """防回归：任何 app.models ORM 类不得再自定义 __repr__（repr 只属于 mixin）。"""
    offenders = [cls for cls in _orm_model_classes() if "__repr__" in vars(cls)]
    assert offenders == []


@pytest.mark.parametrize(
    "cls",
    [
        User,
        Plan,
        Task,
        SubTask,
        ChatSession,
        ChatMessage,
        AgentRun,
        IdempotencyKey,
        SecurityAuditLog,
    ],
)
def test_core_samples_expose_class_name_in_repr(cls):
    assert issubclass(cls, SafeReprMixin)
    # 裸实例（无任何已加载属性）也要给出类名，且绝不抛异常
    r = repr(cls())
    assert cls.__name__ in r


# ---------------------------------------------------------------------------
# 行为不变量：loaded-dict 渲染 + detached/expired 零 IO
# ---------------------------------------------------------------------------


def test_transient_repr_renders_loaded_fields_only():
    user = User(username="alice", email="a@b.c")
    r = repr(user)
    assert r.startswith("<User(") and r.endswith(")>")
    assert "username=alice" in r
    assert "email=a@b.c" in r
    assert "id=?" in r  # 未 flush 前主键未加载 → 问号占位而非描述符读取

    user.id = uuid.uuid4()
    assert f"id={user.id}" in repr(user)

    # __repr_fields__ 声明但未赋值的字段：问号占位，不抛 DetachedInstanceError
    assert "progress=?" in repr(Plan(name="p", type="sprint"))


def _pk_sample_value(column) -> object:
    if isinstance(column.type, GUID):
        return uuid.uuid4()
    if str(column.type).upper().startswith("INT"):
        return 1
    return "sample-key"


@pytest.mark.parametrize(
    "cls",
    [
        User,
        Plan,
        Task,
        SubTask,
        ChatSession,
        ChatMessage,
        AgentRun,
        IdempotencyKey,
        SecurityAuditLog,
    ],
)
def test_detached_instances_repr_class_name_and_pk(cls):
    """detached（无 session 绑定）状态下 repr 输出类名+主键，零异常。"""
    obj = cls()
    for col in sa_inspect(cls).mapper.primary_key:
        setattr(obj, col.key, _pk_sample_value(col))
    from sqlalchemy.orm import make_transient_to_detached

    make_transient_to_detached(obj)
    assert sa_inspect(obj).session_id is None  # 真正脱离 session
    r = repr(obj)
    assert cls.__name__ in r
    for col in sa_inspect(cls).mapper.primary_key:
        assert f"{col.key}=" in r


# ---------------------------------------------------------------------------
# 真 DB 生命周期：commit 过期 / rollback / expunge+close 全链路零 SQL
# ---------------------------------------------------------------------------


@pytest.fixture(name="lifecycle_env")
async def lifecycle_env_fixture():
    """独立引擎+生产语义 session（expire_on_commit=True），带 SQL 事件计数。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sql_counter = {"count": 0}

    def _count(*args, **kwargs):
        sql_counter["count"] += 1

    event.listen(engine.sync_engine, "before_cursor_execute", _count)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=True)
    async with session_factory() as session:
        yield session, sql_counter
    await engine.dispose()


async def test_expired_repr_emits_zero_sql(lifecycle_env):
    session, sql_counter = lifecycle_env
    user = User(username="alice", email="a@b.c", hashed_password="h", photon_balance=0)
    session.add(user)
    await session.commit()  # 生产语义：commit 过期全部加载属性

    from sqlalchemy import exc as sa_exc

    # 负面锚点 1：expired 且仍挂在 session 上，描述符直读 = greenlet 外刷新 IO
    with pytest.raises(sa_exc.MissingGreenlet):
        _ = user.username

    sql_counter["count"] = 0
    r = repr(user)
    assert "User" in r and "id=?" in r
    assert sql_counter["count"] == 0  # repr 零 SQL——旧手写版本在此触发 MissingGreenlet


async def test_rollback_poison_repr_emits_zero_sql(lifecycle_env):
    session, sql_counter = lifecycle_env
    user = User(username="alice", email="a@b.c", hashed_password="h", photon_balance=0)
    session.add(user)
    await session.commit()
    await session.rollback()  # V3-FIX-298 场景：rollback 过期共享会话内全部 ORM

    sql_counter["count"] = 0
    r = repr(user)
    assert "User" in r
    assert sql_counter["count"] == 0


async def test_detached_expired_repr_emits_zero_sql(lifecycle_env):
    from sqlalchemy.orm.exc import DetachedInstanceError

    session, sql_counter = lifecycle_env
    user = User(username="alice", email="a@b.c", hashed_password="h", photon_balance=0)
    session.add(user)
    await session.commit()  # 生产语义：commit 即过期全部加载属性
    session.expire(user)  # 显式钉死 expired 态（须在 expunge 前，persistent 校验）
    session.expunge(user)
    session.close()

    # 负面锚点 2：detached + expired 下描述符直读抛 DetachedInstanceError
    with pytest.raises(DetachedInstanceError):
        _ = user.username

    sql_counter["count"] = 0
    r = repr(user)
    assert "User" in r and "id=?" in r  # 过期后主键也不可加载 → 问号，零 IO
    assert sql_counter["count"] == 0


async def test_repr_does_not_touch_lazy_relationships(lifecycle_env):
    session, sql_counter = lifecycle_env
    user = User(username="alice", email="a@b.c", hashed_password="h", photon_balance=0)
    session.add(user)
    await session.commit()
    await session.refresh(user)  # 重新加载标量

    state = sa_inspect(user)
    assert "tasks" in state.unloaded  # lazy="dynamic" 关系未加载
    before = set(state.unloaded)

    sql_counter["count"] = 0
    repr(user)
    assert set(sa_inspect(user).unloaded) >= before  # repr 不触发任何关系加载
    assert sql_counter["count"] == 0


async def test_loaded_repr_includes_pk_and_fields(lifecycle_env):
    """加载态 repr 的正向形状：类名+真实主键+声明字段（信息不回退）。"""
    session, _ = lifecycle_env
    user = User(username="alice", email="a@b.c", hashed_password="h", photon_balance=0)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    r = repr(user)
    assert f"id={user.id}" in r
    assert "username=alice" in r
    assert "email=a@b.c" in r
