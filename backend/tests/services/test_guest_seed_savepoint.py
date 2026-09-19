"""V3-FIX-13 / D-12: guest 种子事务隔离。

登录事务内同步种子，任一失败曾会毒化整个登录事务：
- seed 中途异常向上传播，调用方必须整体回滚；
- seed 内部的 sync_achievement_definitions 自行 commit，产生"已提交的部分种子"
  （调用方回滚也无法撤销）。

修复后：seed 全程包在 begin_nested()（SAVEPOINT）里，失败回滚到 SAVEPOINT 并
降级为告警（种子是 best-effort 演示数据，不阻断登录）；sync_achievement_definitions
支持 commit=False 保留调用者事务。
"""

from sqlalchemy import func, select

from app.models import Achievement, User, UserAchievement
from app.services import guest_seed_service as gss
from app.services.guest_seed_service import seed_guest_user_data


def _make_guest(username: str) -> User:
    return User(
        username=username,
        email=f"{username}@guest.local",
        hashed_password="hashed",
        password_login_enabled=False,
        nickname="访客",
        registration_source="guest",
        is_active=True,
    )


async def test_guest_seed_failure_does_not_poison_login_transaction(db_session, monkeypatch):
    """种子中途失败：不抛出、外层事务可用、无部分种子残留。"""
    guest = _make_guest("guest_seed_boom")
    db_session.add(guest)
    await db_session.flush()

    async def _boom(session):
        raise RuntimeError("seed exploded mid-way")

    # _ensure_achievements 已跑完后才轮到 _ensure_galaxy_skins —— 制造"部分种子已写入"的现场
    monkeypatch.setattr(gss, "_ensure_galaxy_skins", _boom)

    # 修复后：失败被 SAVEPOINT 吸收，登录事务不毒化
    await seed_guest_user_data(db_session, guest)

    # 外层事务仍然可用：用户行随本次 commit 落库
    await db_session.commit()
    survivor = (await db_session.execute(select(User).where(User.username == "guest_seed_boom"))).scalar_one_or_none()
    assert survivor is not None

    # 无部分种子残留：SAVEPOINT 内写入的成就定义/用户成就全部回滚
    achievement_count = await db_session.scalar(select(func.count(Achievement.id)))
    user_achievement_count = await db_session.scalar(
        select(func.count(UserAchievement.user_id)).where(UserAchievement.user_id == guest.id)
    )
    assert achievement_count == 0
    assert user_achievement_count == 0


async def test_sync_achievement_definitions_commit_flag_preserves_caller_transaction(db_session, monkeypatch):
    """commit=False：种子写入走调用者事务，绝不擅自 commit。"""
    commit_calls: list[int] = []
    original_commit = db_session.commit

    async def _spy_commit():
        commit_calls.append(1)
        await original_commit()

    monkeypatch.setattr(db_session, "commit", _spy_commit)

    from app.data.populate_achievements import sync_achievement_definitions

    await sync_achievement_definitions(db_session, commit=False)
    assert commit_calls == []

    # 数据在调用者事务内可见，且随调用者回滚而消失（证明没有偷偷提交过）
    seeded = await db_session.scalar(select(func.count(Achievement.id)))
    assert seeded > 0
    await db_session.rollback()
    after_rollback = await db_session.scalar(select(func.count(Achievement.id)))
    assert after_rollback == 0


async def test_sync_achievement_definitions_default_commits(db_session, monkeypatch):
    """默认 commit=True：独立调用方（CLI populate_achievements）行为不变。"""
    commit_calls: list[int] = []
    original_commit = db_session.commit

    async def _spy_commit():
        commit_calls.append(1)
        await original_commit()

    monkeypatch.setattr(db_session, "commit", _spy_commit)

    from app.data.populate_achievements import sync_achievement_definitions

    await sync_achievement_definitions(db_session)
    assert commit_calls == [1]
