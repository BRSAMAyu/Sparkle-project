"""V3-FIX-506（P3，wt775 登记）：guest_seed 后端播种的演示群必须可被判为演示。

S-03 验收「seed/demo group 明确标演示」的双面现状（WT775-DOC-UPSG/S-line.md
§S-03 亲证）：mobile demo-mode 的 mock 群一律在名称尾部带「（演示）」后缀
（mock_community_repository.dart + l10n demoGroupSuffix），而 guest_seed_service
后端播种的 6 个真·访客可见演示群（算法冲刺小队/期末自习室/英语口语晨读营/
产品设计共学社/考研政治夜航团/AIGC 创作实验室）经 GET /groups（我的群组）、
群详情、群聊天等读面展示时与真实群完全不可区分。

修法（最小诚实修，不加列不加迁移，与 O1 ``Plan.source="example"`` 同判）：
guest_seed_service 建群统一走「基础名 + GUEST_SEED_DEMO_GROUP_SUFFIX（（演示），
与 mobile mock demoGroupSuffix 同词）」的单一约定出口 ``_ensure_group``：
- 新建群直接落带标记名；name 进所有群读面（列表/详情/聊天），任何读面可区分；
- 存量无标记种子群（修前已播种的库）在种子重播时就地改名收敛，不另建双份；
- 导出 ``is_demo_group_name`` 谓词供任何读面程序化判定，导出 ``demo_group_name``
  供种子写入面与断言同源。
"""

from sqlalchemy import select

from app.models import Group, GroupType, User
from app.services.community_service import GroupService
from app.services.guest_seed_service import (
    GUEST_SEED_DEMO_GROUP_SUFFIX,
    demo_group_name,
    is_demo_group_name,
    seed_guest_user_data,
)

_SEED_GROUP_BASE_NAMES = (
    "算法冲刺小队",
    "期末自习室",
    "英语口语晨读营",
    "产品设计共学社",
    "考研政治夜航团",
    "AIGC 创作实验室",
)


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


async def test_guest_seed_groups_are_marked_demo_in_my_groups_read_surface(db_session):
    """红测①：guest 登录播种后，「我的群组」读面（GET /groups 同构）里
    每一个群名都带演示标记——修前 6 个种子群与真实群不可区分。"""
    guest = _make_guest("guest_demo_group_marker")
    db_session.add(guest)
    await db_session.flush()
    await seed_guest_user_data(db_session, guest)
    await db_session.commit()
    await db_session.refresh(guest)

    my_groups = await GroupService.get_my_groups(db_session, guest.id)
    assert len(my_groups) >= 4, "guest seed 应让访客加入演示群"
    unmarked = [item["name"] for item in my_groups if not is_demo_group_name(item["name"])]
    assert not unmarked, (
        "V3-FIX-506：我的群组读面存在无演示标记的种子群 " f"（base 红：demo 与真实群不可区分）：{unmarked}"
    )

    # 库面全量：种子事务后库内不应存在任何无标记群（演示群 6 个全带标记）。
    all_groups = (await db_session.execute(select(Group))).scalars().all()
    seeded = [g for g in all_groups if is_demo_group_name(g.name)]
    assert len(seeded) == 6, f"种子应产出 6 个带标记演示群，实得 {len(seeded)}"
    marked_names = {g.name for g in seeded}
    for base in _SEED_GROUP_BASE_NAMES:
        assert demo_group_name(base) in marked_names, f"演示群「{base}」缺标记（V3-FIX-506）"


async def test_demo_group_marker_contracts(db_session):
    """红测②：标记谓词/派生函数是读面可程序化判定的契约——
    演示名可判 True、真实自建群名可判 False，后缀与 mobile mock 同词。"""
    assert GUEST_SEED_DEMO_GROUP_SUFFIX == "（演示）", (
        "后端演示后缀必须与 mobile mock demoGroupSuffix（（演示））同词，" "双端演示标记口径一致"
    )
    for base in _SEED_GROUP_BASE_NAMES:
        assert is_demo_group_name(demo_group_name(base)) is True
        assert is_demo_group_name(base) is False, "基础名（无后缀）不得被判为演示群"
    # 真实用户自建群名（可能恰好含「演示」字样但无标记后缀）不得误判。
    assert is_demo_group_name("演示项目管理实践组") is False


async def test_legacy_unmarked_seed_group_heals_to_marked_name_on_reseed(db_session):
    """红测③：修前已播种的存量库里有无标记同名群——种子重播时必须就地
    改名收敛为带标记群，而不是另建一份带标记副本留下无标记双份。"""
    legacy = Group(
        name="算法冲刺小队",
        description="一起冲刺算法与数据结构的学习群",
        type=GroupType.SPRINT,
        focus_tags=["数据结构"],
    )
    db_session.add(legacy)
    await db_session.commit()

    guest = _make_guest("guest_demo_group_heal")
    db_session.add(guest)
    await db_session.flush()
    await seed_guest_user_data(db_session, guest)
    await db_session.commit()

    family = (await db_session.execute(select(Group).where(Group.name.like("%算法冲刺小队%")))).scalars().all()
    assert len(family) == 1, (
        "V3-FIX-506：存量无标记种子群必须就地改名收敛，不得留下无标记副本双份：" f"{[g.name for g in family]}"
    )
    assert is_demo_group_name(family[0].name) is True, "收敛后的群必须带演示标记"
