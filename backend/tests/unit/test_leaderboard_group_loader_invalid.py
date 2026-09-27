"""V3-FIX-509 回归测试：群组榜 ``selectinload(GroupMember)`` 套 ``select(User)`` 构造期炸。

修前 ``LeaderboardService._get_group_leaderboard`` :487
``select(User).options(selectinload(GroupMember))``——``GroupMember`` 是映射类而
非 ORM 关系属性（``User`` 模型零 ``GroupMember`` 关系可引），SQLAlchemy 2.0 在
loader 选项**构造时**即抛 ``ArgumentError: expected ORM mapped attribute for
loader strategy argument``（strategy_options._parse_attr_argument，本仓
SA 2.0.48 运行级探针实录）；API 路由 leaderboards.py ``except Exception → 500``
兜底，群组榜（带 group_id）成为必炸 500。且该 loader 即便合法也是双重死码：
贡献值来自 :493 独立 members 查询，loader 产物零消费者。

修法：整体摘除 ``.options(selectinload(GroupMember))``（含 import）——无合法
形态可修（无关系路径可指），无消费面需要它。

钉两件事：① 端到端不炸 + 排行数值正确（按 flame_contribution 降序）；
② AST 源码扫描 leaderboard_service.py 不得再出现 selectinload（防回归）。
"""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.community import Group, GroupMember, GroupType
from app.models.intervention import UserInterventionSettings
from app.models.user import PushPreference, User
from app.schemas.leaderboard import LeaderboardRequest, LeaderboardType
from app.services.leaderboard_service import LeaderboardService

SERVICE_FILE = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "services"
    / "leaderboard_service.py"
)


async def _seed_group_scenario(session_factory) -> tuple[object, object, object, object]:
    """建 caller + 两名成员（火焰贡献 30/10），caller 贡献 20 居中。"""
    caller_id, member_a_id, member_b_id = uuid4(), uuid4(), uuid4()
    group_id = uuid4()
    async with session_factory() as session:
        session.add_all(
            [
                User(id=caller_id, username="caller", email="caller@test.local", hashed_password="x"),
                User(id=member_a_id, username="member_a", email="a@test.local", hashed_password="x"),
                User(id=member_b_id, username="member_b", email="b@test.local", hashed_password="x"),
                Group(id=group_id, name="sprint-group", type=GroupType.SPRINT),
                GroupMember(group_id=group_id, user_id=caller_id, flame_contribution=20),
                GroupMember(group_id=group_id, user_id=member_a_id, flame_contribution=30),
                GroupMember(group_id=group_id, user_id=member_b_id, flame_contribution=10),
            ]
        )
        await session.commit()
    return group_id, caller_id, member_a_id, member_b_id


@pytest.mark.asyncio
async def test_group_leaderboard_does_not_raise_and_ranks_by_flame():
    """带 group_id 的群组榜端到端：修前 selectinload 构造即 ArgumentError，修后按贡献降序出榜。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            User.metadata.create_all,
            tables=[
                User.__table__,
                Group.__table__,
                GroupMember.__table__,
                # User 的 joined 关系面：select(User) 语句带 LEFT OUTER JOIN
                PushPreference.__table__,
                UserInterventionSettings.__table__,
            ],
        )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    group_id, caller_id, member_a_id, member_b_id = await _seed_group_scenario(session_factory)

    async with session_factory() as session:
        service = LeaderboardService(session)
        response = await service.get_leaderboard(
            LeaderboardRequest(type=LeaderboardType.GROUP, group_id=group_id),
            caller_id,
        )

    assert [e.user_id for e in response.entries] == [member_a_id, caller_id, member_b_id]
    assert [e.rank for e in response.entries] == [1, 2, 3]
    assert response.entries[0].stats["flame_contribution"] == 30
    assert response.my_rank == 2
    assert response.my_score == 20.0
    assert response.total_participants == 3
    await engine.dispose()


def test_leaderboard_service_source_has_no_selectinload():
    """AST 源码扫描钉：selectinload 不得回流 leaderboard_service.py。

    User 模型没有指向 GroupMember 的关系路径，任何 selectinload 形态在本文件
    都无法合法表达；贡献值消费面走独立 members 查询。防「顺手加回来」回归。
    """
    tree = ast.parse(SERVICE_FILE.read_text(encoding="utf-8"))
    hits = [
        f"line {node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "selectinload"
    ]
    assert hits == [], (
        "selectinload re-introduced in leaderboard_service.py — User has no GroupMember "
        f"relationship path; contributions come from the standalone members query. Offending lines: {hits}"
    )
