"""小队错题卡分享回归（D-COMM-5 · 错题卡互助分享）。

钉八条验收面：
1. 分享/列表回路：分享者/科目/知识点/掌握度快照/时间逐字段如实；
   掌握度负 delta 不粉饰（诚实性红线）；
2. 内容服务端取：POST 只收 error_id（schema 白名单），响应内容来自
   服务端 error_records——客户端塞内容字段不可伪造；非本人错题 404；
3. 安全过滤（SAFETY 词库面）：命中即拒（400），零落库，不泄露违规明细；
4. 撤回：软删可撤回；仅分享者本人可撤（非本人 404 不泄露存在性）；
   撤回后可再分享；
5. 隐私：非成员 403（分享/列表双拦）；非 SPRINT 群组 404 不泄露存在性；
   源错题被主人删除 → 分享自动从流中消失（删错题=撤回下游曝光）；
   图片仅 sparkle-file:// 引用原样透传，不新开公共 URL；
6. 幂等：同错题重复分享不建重复记录（部分唯一索引 + 服务层幂等双保证）；
7. 反刷红线（D20）：分享零光子零榜分——AST 导入扫描（结构断言）+
   光子/火苗扰动后列表与榜分逐字段不变、零 photon_transaction_history
   写入（行为断言）双钉；
8. 网关代理照 D-COMM-4 先例（见 proxy_routes_dcomm5_test.go）。
"""

from __future__ import annotations

import ast
import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.api.deps import get_current_user, get_db
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.shop import PhotonTransactionHistory
from app.models.squad_shared_error import SquadSharedError
from app.models.user import User
from app.schemas.error_book import ErrorRecordCreate, SubjectEnum
from app.services.community_shared_error_service import (
    SharedErrorRejected,
    SourceErrorNotFound,
    SquadSharedErrorService,
)
from app.services.community_squad_board_service import SquadBoardService
from app.services.community_squad_service import SquadNotFoundError, SquadPermissionError
from app.services.error_book_service import ErrorBookService

SQUAD_ROUTER_PREFIX = "/api/v1/community/squads"

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DCOMM5_MODULES = (
    _BACKEND_ROOT / "app" / "services" / "community_shared_error_service.py",
    _BACKEND_ROOT / "app" / "api" / "v1" / "community_squad_shared_errors.py",
    _BACKEND_ROOT / "app" / "schemas" / "community_shared_errors.py",
    _BACKEND_ROOT / "app" / "models" / "squad_shared_error.py",
)


# ---------------------------------------------------------------------------
# 工具（与 D-COMM-3/4 测试同款造数惯例）
# ---------------------------------------------------------------------------
async def _make_user(db, prefix: str = "share") -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_squad(db, owner: User, *, max_members: int = 8) -> Group:
    group = Group(
        name=f"squad-{uuid_mod.uuid4().hex[:8]}",
        type=GroupType.SPRINT,
        focus_tags=[],
        deadline=(datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)),
        sprint_goal="期末周互助",
        max_members=max_members,
        is_public=True,
        join_requires_approval=False,
    )
    db.add(group)
    await db.flush()
    db.add(
        GroupMember(
            group_id=group.id,
            user_id=owner.id,
            role=GroupRole.OWNER,
            joined_at=datetime.now(UTC).replace(tzinfo=None),
            last_active_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    await db.flush()
    return group


async def _join(db, group: Group, user: User) -> GroupMember:
    member = GroupMember(
        group_id=group.id,
        user_id=user.id,
        role=GroupRole.MEMBER,
        joined_at=datetime.now(UTC).replace(tzinfo=None),
        last_active_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(member)
    await db.flush()
    return member


async def _make_error(
    db,
    user: User,
    *,
    question_text: str | None = "证明：任意 6 人中必有 3 人互相认识或互相不认识",
    subject_code: str = "math",
    question_image_url: str | None = None,
    latest_analysis: dict | None = None,
    linked_node: KnowledgeNode | None = None,
    mastery_level: float = 0.3,
    mastery_delta: float | None = -8.0,
    review_count: int = 2,
) -> ErrorRecord:
    error = ErrorRecord(
        user_id=user.id,
        question_text=question_text,
        question_image_url=question_image_url,
        subject_code=subject_code,
        chapter="图论",
        latest_analysis=latest_analysis,
        linked_knowledge_node_ids=[linked_node.id] if linked_node else [],
        affected_node_id=linked_node.id if linked_node else None,
        mastery_level=mastery_level,
        mastery_delta=mastery_delta,
        review_count=review_count,
    )
    db.add(error)
    await db.flush()
    return error


async def _make_node(db, name: str = "拉姆齐定理") -> KnowledgeNode:
    node = KnowledgeNode(name=name)
    db.add(node)
    await db.flush()
    return node


# ---------------------------------------------------------------------------
# 1. 反刷红线：零光子零榜分（结构 + 行为双断言）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module_path", _DCOMM5_MODULES)
def test_dcomm5_modules_import_scan_no_xp_photon_leaderboard(module_path):
    """AST 导入扫描：分享四模块不得 import photon/experience/leaderboard/xp 域。"""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    forbidden = ("photon", "experience", "leaderboard", "xp")
    hits = [m for m in imported_modules if any(f in m.lower() for f in forbidden)]
    assert hits == [], f"D-COMM-5 模块出现了禁入域导入（D20 红线）: {hits} in {module_path.name}"


@pytest.mark.asyncio
async def test_share_produces_zero_photon_and_zero_board_delta(db_session):
    """行为断言：分享零光子（余额不变 + 零流水写入）、榜分逐字段不变；
    光子/火苗任意改写也不影响分享流（纯分发记录，无行为量进面）。"""
    owner = await _make_user(db_session, "zown")
    mate = await _make_user(db_session, "zmate")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    node = await _make_node(db_session)
    error = await _make_error(db_session, owner, linked_node=node)
    await db_session.commit()

    async def photon_tx_count() -> int:
        result = await db_session.execute(select(func.count(PhotonTransactionHistory.id)))
        return int(result.scalar() or 0)

    board_before = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, owner.id)
    balance_before = {u.id: u.photon_balance for u in (owner, mate)}
    tx_before = await photon_tx_count()

    share, created = await SquadSharedErrorService.share_error(db_session, squad.id, error.id, owner.id)
    await db_session.flush()
    assert created is True and share.id is not None

    feed = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, mate.id)
    assert feed["total"] == 1

    board_after = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, owner.id)
    assert [(e.user_id, e.rank, e.task_total, e.task_completed, e.completion_rate) for e in board_before.entries] == [
        (e.user_id, e.rank, e.task_total, e.task_completed, e.completion_rate) for e in board_after.entries
    ], "分享不得改变小队榜分（零榜分红线）"
    assert {u.id: u.photon_balance for u in (owner, mate)} == balance_before, "分享不得改变光子余额（零光子红线）"
    assert await photon_tx_count() == tx_before == 0, "分享不得产生光子流水"

    # 光子/火苗扰动不改变分享流
    owner.photon_balance = 999_999
    owner.flame_level = 99
    db_session.add(owner)
    await db_session.commit()
    feed2 = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, mate.id)
    assert feed2["total"] == 1
    assert feed2["items"][0].share_id == feed["items"][0].share_id


# ---------------------------------------------------------------------------
# 2. 分享/列表回路 + 掌握度快照诚实
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_share_list_round_trip_fields_and_honest_snapshot(db_session):
    owner = await _make_user(db_session, "rown")
    mate = await _make_user(db_session, "rmate")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    node = await _make_node(db_session, "鸽巢原理")
    error = await _make_error(
        db_session,
        owner,
        linked_node=node,
        latest_analysis={
            "error_type": "concept_confusion",
            "error_type_label": "概念混淆",
            "root_cause": "把抽屉原理的方向用反了",
            "correct_approach": "应该先构造反例再论证（不分享面）",
            "similar_traps": ["陷阱A"],
            "study_suggestion": "重做课本例题 3 道",
        },
        mastery_level=0.25,
        mastery_delta=-8.0,
        review_count=3,
    )
    await db_session.commit()

    share, created = await SquadSharedErrorService.share_error(
        db_session, squad.id, error.id, owner.id, note="这题我方向想反了"
    )
    assert created is True
    await db_session.commit()

    feed = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, mate.id)
    assert feed["total"] == 1 and len(feed["items"]) == 1
    entry = feed["items"][0]
    assert entry.share_id == share.id
    assert entry.sharer_id == owner.id and entry.sharer_name == owner.username
    assert entry.subject_code == "math" and entry.chapter == "图论"
    assert [n.name for n in entry.knowledge_nodes] == ["鸽巢原理"]
    assert entry.knowledge_nodes[0].is_primary is True
    assert entry.error_type == "concept_confusion" and entry.root_cause == "把抽屉原理的方向用反了"
    assert entry.study_suggestion == "重做课本例题 3 道"
    assert entry.note == "这题我方向想反了"
    assert entry.mastery_level == 0.25 and entry.mastery_delta == -8.0, "掌握度快照如实（负 delta 不粉饰）"
    assert entry.review_count == 3
    assert entry.created_at is not None

    # 反抄答案白名单：答案/解析思路绝不进分享面
    payload = entry.model_dump()
    assert "correct_answer" not in payload and "user_answer" not in payload
    assert entry.root_cause != "应该先构造反例再论证（不分享面）"

    # 分享者自己也能看自己的分享
    own_view = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, owner.id)
    assert own_view["total"] == 1


@pytest.mark.asyncio
async def test_snapshot_freezes_content_against_later_edit(db_session):
    """快照语义：分享后 PATCH 源错题内容，小队流里仍是分享时刻的快照
    （安全过滤检查对象=所服务内容，关闭 TOCTOU 夹带）。"""
    owner = await _make_user(db_session, "fown")
    squad = await _make_squad(db_session, owner)
    error = await _make_error(db_session, owner, question_text="原始题目")
    await db_session.commit()

    await SquadSharedErrorService.share_error(db_session, squad.id, error.id, owner.id)

    error.question_text = "分享后被篡改的内容"
    error.mastery_level = 0.99
    db_session.add(error)
    await db_session.flush()

    feed = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, owner.id)
    assert feed["items"][0].question_text == "原始题目", "分享流服务快照，不随源错题后续编辑漂移"


# ---------------------------------------------------------------------------
# 3. 内容服务端取（不可伪造）+ 非本人错题
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_share_api_content_is_server_side_and_not_forgeable(db_session):
    owner = await _make_user(db_session, "cown")
    other = await _make_user(db_session, "cother")
    squad = await _make_squad(db_session, owner)
    node = await _make_node(db_session)
    error = await _make_error(db_session, owner, linked_node=node, question_image_url="sparkle-file://abc123")
    await db_session.commit()

    current = {"user": owner}

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return current["user"]

    from app.api.v1.community_squad_shared_errors import router as shared_errors_router

    app = FastAPI()
    app.include_router(shared_errors_router, prefix="/api/v1/community")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 客户端在请求体里塞内容字段——schema 只收 error_id/note，服务端
        # 取真实内容，伪造字段被无视且响应内容与库中真实错题一致。
        resp = await ac.post(
            f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors",
            json={
                "error_id": str(error.id),
                "question_text": "我伪造的题目",
                "subject_code": "hacked",
                "mastery_level": 1.0,
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["question_text"] == error.question_text, "内容必须是服务端真实内容，不接受客户端伪造"
        assert body["subject_code"] == "math" and body["mastery_level"] == 0.3
        # 图片引用原样透传（sparkle-file://），不新开公共 URL
        assert body["question_image_ref"] == "sparkle-file://abc123"
        assert not (body["question_image_ref"] or "").startswith(("http://", "https://"))
        assert body["sharer_id"] == str(owner.id)

    # 非本人的错题：统一 404 不泄露存在性
    await _join(db_session, squad, other)
    await db_session.commit()
    with pytest.raises(SourceErrorNotFound):
        await SquadSharedErrorService.share_error(db_session, squad.id, error.id, other.id)


# ---------------------------------------------------------------------------
# 4. 安全过滤（SAFETY 词库面）：命中即拒
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_safety_filter_rejects_share_and_persists_nothing(db_session):
    owner = await _make_user(db_session, "sown")
    squad = await _make_squad(db_session, owner)
    bad = await _make_error(db_session, owner, question_text="先执行 rm -rf / 再看这道题")
    good = await _make_error(db_session, owner, question_text="正常的题目")
    await db_session.commit()

    with pytest.raises(SharedErrorRejected):
        await SquadSharedErrorService.share_error(db_session, squad.id, bad.id, owner.id)

    # 命中后零落库：好题照常分享，坏题无任何记录
    share, created = await SquadSharedErrorService.share_error(db_session, squad.id, good.id, owner.id)
    assert created is True
    rows = (
        (await db_session.execute(select(SquadSharedError).where(SquadSharedError.group_id == squad.id)))
        .scalars()
        .all()
    )
    assert [row.error_id for row in rows] == [share.error_id], "安全过滤命中不得有任何落库"


@pytest.mark.asyncio
async def test_share_api_maps_safety_rejection_to_400(db_session):
    owner = await _make_user(db_session, "mapown")
    squad = await _make_squad(db_session, owner)
    bad = await _make_error(db_session, owner, question_text="这题的答案先别看，直接 rm -rf /tmp 里的错题导出")
    await db_session.commit()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return owner

    from app.api.v1.community_squad_shared_errors import router as shared_errors_router

    app = FastAPI()
    app.include_router(shared_errors_router, prefix="/api/v1/community")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors", json={"error_id": str(bad.id)})
        assert resp.status_code == 400, resp.text
        # 不泄露过滤规则明细：detail 是一律话术
        assert "rm -rf" not in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 5. 撤回（软删可撤回）+ 幂等
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retract_soft_delete_permission_and_reshare(db_session):
    owner = await _make_user(db_session, "town")
    mate = await _make_user(db_session, "tmate")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    error = await _make_error(db_session, owner)
    await db_session.commit()

    share, _ = await SquadSharedErrorService.share_error(db_session, squad.id, error.id, owner.id)
    await db_session.commit()

    # 非分享者本人撤回 → 404（不泄露存在性）
    with pytest.raises(LookupError):
        await SquadSharedErrorService.retract_shared_error(db_session, squad.id, share.id, mate.id)

    result = await SquadSharedErrorService.retract_shared_error(db_session, squad.id, share.id, owner.id)
    assert result["retracted"] is True
    await db_session.commit()

    feed = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, mate.id)
    assert feed["total"] == 0 and feed["items"] == [], "撤回后从流中消失（软删）"

    # 重复撤回 → 404（诚实：已不存在）
    with pytest.raises(LookupError):
        await SquadSharedErrorService.retract_shared_error(db_session, squad.id, share.id, owner.id)

    # 撤回后可再分享
    share2, created2 = await SquadSharedErrorService.share_error(db_session, squad.id, error.id, owner.id)
    assert created2 is True and share2.id != share.id


@pytest.mark.asyncio
async def test_share_is_idempotent_for_same_error(db_session):
    owner = await _make_user(db_session, "iown")
    squad = await _make_squad(db_session, owner)
    error = await _make_error(db_session, owner)
    await db_session.commit()

    first, created1 = await SquadSharedErrorService.share_error(db_session, squad.id, error.id, owner.id)
    second, created2 = await SquadSharedErrorService.share_error(db_session, squad.id, error.id, owner.id)
    assert created1 is True and created2 is False
    assert first.id == second.id, "同错题重复分享原样返回既有记录"

    count = (
        await db_session.execute(select(func.count(SquadSharedError.id)).where(SquadSharedError.group_id == squad.id))
    ).scalar()
    assert count == 1


# ---------------------------------------------------------------------------
# 6. 隐私：非成员 403 / 非 SPRINT 404 / 源错题删除自动消失
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_nonmember_403_and_non_sprint_404_and_source_delete_gone(db_session):
    owner = await _make_user(db_session, "pown")
    outsider = await _make_user(db_session, "pout")
    squad = await _make_squad(db_session, owner)
    error = await _make_error(db_session, owner)
    await db_session.commit()

    with pytest.raises(SquadPermissionError):
        await SquadSharedErrorService.share_error(db_session, squad.id, error.id, outsider.id)
    with pytest.raises(SquadPermissionError):
        await SquadSharedErrorService.list_shared_errors(db_session, squad.id, outsider.id)

    plain = Group(name="普通学习小队", type=GroupType.SQUAD, focus_tags=[], max_members=50)
    db_session.add(plain)
    await db_session.flush()
    db_session.add(GroupMember(group_id=plain.id, user_id=owner.id, role=GroupRole.OWNER))
    await db_session.flush()

    with pytest.raises(SquadNotFoundError):
        await SquadSharedErrorService.share_error(db_session, plain.id, error.id, owner.id)
    with pytest.raises(SquadNotFoundError):
        await SquadSharedErrorService.list_shared_errors(db_session, plain.id, owner.id)

    # 分享后主人删除源错题 → 分享自动从流中消失（删错题=撤回下游曝光）
    await SquadSharedErrorService.share_error(db_session, squad.id, error.id, owner.id)
    await db_session.commit()
    feed = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, owner.id)
    assert feed["total"] == 1
    error.is_deleted = True
    db_session.add(error)
    await db_session.flush()
    feed_after = await SquadSharedErrorService.list_shared_errors(db_session, squad.id, owner.id)
    assert feed_after["total"] == 0, "源错题软删后分享不得继续出现在小队流"


@pytest.mark.asyncio
async def test_api_round_trip_403_and_404_mapping(db_session):
    owner = await _make_user(db_session, "aown")
    outsider = await _make_user(db_session, "aout")
    squad = await _make_squad(db_session, owner)
    error = await _make_error(db_session, owner)
    await db_session.commit()

    current = {"user": owner}

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return current["user"]

    from app.api.v1.community_squad_shared_errors import router as shared_errors_router

    app = FastAPI()
    app.include_router(shared_errors_router, prefix="/api/v1/community")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        share_resp = await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors", json={"error_id": str(error.id)})
        assert share_resp.status_code == 201, share_resp.text
        share_id = share_resp.json()["share_id"]

        list_resp = await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1

        current["user"] = outsider
        assert (
            await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors", json={"error_id": str(error.id)})
        ).status_code == 403
        assert (await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors")).status_code == 403
        assert (
            await ac.delete(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors/{share_id}")
        ).status_code == 403, "非成员统一 403（与小队面既有惯例一致）"

        current["user"] = owner
        missing_squad = uuid4()
        assert (await ac.get(f"{SQUAD_ROUTER_PREFIX}/{missing_squad}/shared-errors")).status_code == 404
        missing_share = uuid4()
        assert (await ac.delete(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors/{missing_share}")).status_code == 404

        # 不存在的错题：404
        assert (
            await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/shared-errors", json={"error_id": str(uuid4())})
        ).status_code == 404


# ---------------------------------------------------------------------------
# 7. 错题域既有服务零回归（对比法锚点：create/list 路径不受新面影响）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_error_book_service_unaffected_by_share(db_session):
    """error_book 只读面零改动对比锚：分享前后 get/list 返回逐字段一致。"""
    owner = await _make_user(db_session, "eown")
    service = ErrorBookService(db_session)
    created = await service.create_error(
        owner.id,
        ErrorRecordCreate(
            question_text="对比锚题目",
            subject=SubjectEnum.MATH,
            chapter="数论",
        ),
    )
    await db_session.commit()
    before = await service.get_error(created.id, owner.id)
    assert before is not None

    squad = await _make_squad(db_session, owner)
    await SquadSharedErrorService.share_error(db_session, squad.id, created.id, owner.id)
    await db_session.commit()

    after = await service.get_error(created.id, owner.id)
    assert (after.id, after.question_text, after.mastery_level, after.review_count) == (
        before.id,
        before.question_text,
        before.mastery_level,
        before.review_count,
    ), "分享不得改变源错题（error_book 纯读面，对比法零新增）"
