#!/usr/bin/env python3
"""Gateway-backed acceptance for accountability partnerships."""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import requests
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.notification import Notification
from app.models.user import User


GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
PASSWORD = os.getenv("ACCOUNTABILITY_TEST_PASSWORD", "Temp123456")
TIMEOUT = 60


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def request_json(
    session: requests.Session,
    method: str,
    path: str,
    *,
    token: str,
    expected: int | None = None,
    **kwargs,
):
    response = session.request(
        method,
        f"{GATEWAY_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
        **kwargs,
    )
    ok = response.status_code == expected if expected is not None else 200 <= response.status_code < 300
    if not ok:
        raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:800]}")
    if not response.content:
        return None
    return response.json()


async def create_test_user(prefix: str) -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        suffix = uuid.uuid4().hex[:8]
        username = f"{prefix}_{suffix}"
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            password_login_enabled=True,
            nickname=username,
            registration_source="email",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {
            "id": str(user.id),
            "username": username,
            "token": create_access_token({"sub": str(user.id)}),
        }


async def get_notification_types(user_id: str) -> list[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Notification.type)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.asc())
        )
        return [item for item in result.scalars().all()]


async def main() -> int:
    owner = await create_test_user("accountability_owner")
    partner = await create_test_user("accountability_partner")
    outsider = await create_test_user("accountability_outsider")

    session = requests.Session()

    no_friend_resp = session.post(
        f"{GATEWAY_BASE}/accountability/request",
        headers={"Authorization": f"Bearer {owner['token']}"},
        timeout=TIMEOUT,
        json={
            "partner_id": outsider["id"],
            "initiator_goal": "先验证没有好友关系不能发起责任伙伴",
            "check_in_days": 2,
        },
    )
    ensure(
        no_friend_resp.status_code == 400,
        f"request without friendship should fail: {no_friend_resp.status_code} {no_friend_resp.text[:400]}",
    )

    self_invite_resp = session.post(
        f"{GATEWAY_BASE}/accountability/request",
        headers={"Authorization": f"Bearer {owner['token']}"},
        timeout=TIMEOUT,
        json={
            "partner_id": owner["id"],
            "initiator_goal": "给自己发邀请",
            "check_in_days": 1,
        },
    )
    ensure(
        self_invite_resp.status_code == 400,
        f"self invite should fail: {self_invite_resp.status_code} {self_invite_resp.text[:400]}",
    )

    friend_req = request_json(
        session,
        "POST",
        "/community/friends/request",
        token=owner["token"],
        json={"target_user_id": partner["id"], "message": "一起做责任伙伴吧"},
    )
    friendship_id = friend_req["friendship_id"]

    pending_friends = request_json(
        session,
        "GET",
        "/community/friends/pending",
        token=partner["token"],
    )
    ensure(
        any(item["id"] == friendship_id for item in pending_friends),
        f"pending friendship missing: {json.dumps(pending_friends, ensure_ascii=False)}",
    )

    request_json(
        session,
        "POST",
        "/community/friends/respond",
        token=partner["token"],
        json={"friendship_id": friendship_id, "accept": True},
    )

    recommendations = request_json(
        session,
        "GET",
        "/community/friends/recommendations",
        token=owner["token"],
        params={"strategy": "compatibility", "target": "accountability", "limit": 5},
    )
    ensure(recommendations, "friend/accountability recommendations should not be empty")
    ensure(
        any(item["user"]["id"] == partner["id"] for item in recommendations),
        f"accepted friend should surface in accountability recommendations: {recommendations}",
    )
    first_recommendation = recommendations[0]
    request_json(
        session,
        "POST",
        "/community/friends/recommendations/feedback",
        token=owner["token"],
        expected=200,
        json={
            "target_user_id": first_recommendation["user"]["id"],
            "strategy": first_recommendation["strategy"],
            "target": first_recommendation["target"],
            "action": "view",
            "source": "acceptance",
            "score": first_recommendation["match_score"],
        },
    )

    partnership = request_json(
        session,
        "POST",
        "/accountability/request",
        token=owner["token"],
        expected=201,
        json={
            "partner_id": partner["id"],
            "initiator_goal": "每天晚上完成 45 分钟深度学习",
            "check_in_days": 2,
        },
    )
    partnership_id = partnership["id"]
    ensure(partnership["status"] == "pending", f"unexpected partnership state: {partnership}")

    owner_notifications = await get_notification_types(owner["id"])
    partner_notifications = await get_notification_types(partner["id"])
    ensure(
        "accountability_partner_request" in partner_notifications,
        f"partner request notification missing: {partner_notifications}",
    )

    duplicate_pending = session.post(
        f"{GATEWAY_BASE}/accountability/request",
        headers={"Authorization": f"Bearer {owner['token']}"},
        timeout=TIMEOUT,
        json={
            "partner_id": partner["id"],
            "initiator_goal": "重复邀请应该被拦截",
            "check_in_days": 1,
        },
    )
    ensure(
        duplicate_pending.status_code == 409,
        f"duplicate pending request should fail: {duplicate_pending.status_code} {duplicate_pending.text[:400]}",
    )

    partner_mine_pending = request_json(
        session,
        "GET",
        "/accountability/mine",
        token=partner["token"],
    )
    pending_entry = next((item for item in partner_mine_pending if item["id"] == partnership_id), None)
    ensure(pending_entry is not None, f"pending partnership missing from /mine: {partner_mine_pending}")
    ensure(
        pending_entry["initiator"]["id"] == owner["id"] and pending_entry["partner"]["id"] == partner["id"],
        f"nested user info missing from pending partnership: {pending_entry}",
    )

    partnership = request_json(
        session,
        "POST",
        f"/accountability/{partnership_id}/respond",
        token=partner["token"],
        json={"accept": True, "partner_goal": "每天复盘并给伙伴一句反馈"},
    )
    ensure(partnership["status"] == "active", f"partnership did not activate: {partnership}")
    ensure(partnership["partner_goal"] == "每天复盘并给伙伴一句反馈", f"partner goal missing: {partnership}")

    owner_notifications = await get_notification_types(owner["id"])
    ensure(
        "accountability_partner_accepted" in owner_notifications,
        f"partner accepted notification missing: {owner_notifications}",
    )

    overview = request_json(
        session,
        "GET",
        "/accountability/overview",
        token=owner["token"],
    )
    ensure(
        overview["slot_type"] == "core" and overview["active_partnership"]["id"] == partnership_id,
        f"overview should expose active core partner: {overview}",
    )

    dashboard = request_json(
        session,
        "GET",
        f"/accountability/{partnership_id}/dashboard",
        token=owner["token"],
    )
    ensure(
        dashboard["partnership"]["id"] == partnership_id and dashboard["quick_actions"]["can_open_dashboard"] is True,
        f"dashboard payload malformed: {dashboard}",
    )

    friend_profile = request_json(
        session,
        "GET",
        f"/community/friends/{partner['id']}/profile",
        token=owner["token"],
    )
    ensure(
        friend_profile["accountability"]["id"] == partnership_id
        and friend_profile["quick_actions"]["can_open_dashboard"] is True,
        f"friend profile should include accountability enrichment: {friend_profile}",
    )

    profile_context = request_json(
        session,
        "GET",
        "/profile/context",
        token=owner["token"],
    )
    ensure(
        profile_context["accountability_summary"]["has_core_partner"] is True
        and profile_context["accountability_summary"]["slot_type"] == "core",
        f"profile context missing accountability summary: {profile_context}",
    )

    second_friend_req = request_json(
        session,
        "POST",
        "/community/friends/request",
        token=owner["token"],
        json={"target_user_id": outsider["id"], "message": "先成为好友"},
    )
    request_json(
        session,
        "POST",
        "/community/friends/respond",
        token=outsider["token"],
        json={"friendship_id": second_friend_req["friendship_id"], "accept": True},
    )
    single_core_blocked = session.post(
        f"{GATEWAY_BASE}/accountability/request",
        headers={"Authorization": f"Bearer {owner['token']}"},
        timeout=TIMEOUT,
        json={
            "partner_id": outsider["id"],
            "initiator_goal": "已有核心伙伴时不能再发起新的核心伙伴邀请",
            "check_in_days": 1,
        },
    )
    ensure(
        single_core_blocked.status_code == 409,
        f"single core constraint should block second partner request: {single_core_blocked.status_code} {single_core_blocked.text[:400]}",
    )

    owner_mine = request_json(
        session,
        "GET",
        "/accountability/mine",
        token=owner["token"],
    )
    owner_entry = next((item for item in owner_mine if item["id"] == partnership_id), None)
    ensure(owner_entry is not None, f"active partnership missing from /mine: {owner_mine}")
    ensure(owner_entry["my_role"] == "initiator", f"my_role missing or wrong: {owner_entry}")
    ensure(owner_entry["my_checked_in_today"] is False, f"unexpected pre-checkin state: {owner_entry}")
    ensure(owner_entry["partner_checked_in_today"] is False, f"unexpected partner pre-checkin state: {owner_entry}")

    owner_checkin = request_json(
        session,
        "POST",
        f"/accountability/{partnership_id}/checkin",
        token=owner["token"],
        expected=201,
        json={
            "content": "完成了英语精读和一道算法题，状态很稳。",
            "mood": 4,
            "minutes": 65,
        },
    )
    owner_checkin_id = owner_checkin["id"]
    ensure(owner_checkin["author"]["id"] == owner["id"], f"checkin author missing: {owner_checkin}")

    duplicate_checkin = session.post(
        f"{GATEWAY_BASE}/accountability/{partnership_id}/checkin",
        headers={"Authorization": f"Bearer {owner['token']}"},
        timeout=TIMEOUT,
        json={
            "content": "今天第二次打卡应该被拦截",
            "mood": 3,
            "minutes": 10,
        },
    )
    ensure(
        duplicate_checkin.status_code == 400,
        f"duplicate same-day checkin should fail: {duplicate_checkin.status_code} {duplicate_checkin.text[:400]}",
    )

    partner_checkin = request_json(
        session,
        "POST",
        f"/accountability/{partnership_id}/checkin",
        token=partner["token"],
        expected=201,
        json={
            "content": "做了 50 分钟复盘，还给伙伴整理了明天的提醒。",
            "mood": 5,
            "minutes": 50,
        },
    )
    partner_checkin_id = partner_checkin["id"]

    like_resp = request_json(
        session,
        "POST",
        f"/accountability/checkin/{partner_checkin_id}/like",
        token=owner["token"],
    )
    ensure(like_resp["likes"] == 1, f"like count mismatch: {like_resp}")

    encourage_resp = request_json(
        session,
        "POST",
        f"/accountability/checkin/{partner_checkin_id}/encourage",
        token=owner["token"],
        json={"message": "这条复盘很到位，我们明天继续保持。"},
    )
    ensure(encourage_resp["total_encouragements"] == 1, f"encouragement count mismatch: {encourage_resp}")

    stats = request_json(
        session,
        "GET",
        f"/accountability/{partnership_id}/stats",
        token=owner["token"],
    )
    ensure(stats["my_checked_in_today"] is True, f"my_checked_in_today not updated: {stats}")
    ensure(stats["partner_checked_in_today"] is True, f"partner_checked_in_today not updated: {stats}")
    ensure(stats["total_checkins"] == 2, f"unexpected total checkins: {stats}")

    nudge_resp = request_json(
        session,
        "POST",
        f"/accountability/{partnership_id}/nudge",
        token=owner["token"],
        json={"message": "今晚一起收尾"},
    )
    ensure(nudge_resp["success"] is True, f"manual nudge failed: {nudge_resp}")
    nudge_again = session.post(
        f"{GATEWAY_BASE}/accountability/{partnership_id}/nudge",
        headers={"Authorization": f"Bearer {owner['token']}"},
        timeout=TIMEOUT,
        json={"message": "再次提醒"},
    )
    ensure(
        nudge_again.status_code == 429,
        f"nudge rate limit should trigger: {nudge_again.status_code} {nudge_again.text[:400]}",
    )

    timeline = request_json(
        session,
        "GET",
        f"/accountability/{partnership_id}/timeline",
        token=owner["token"],
        params={"limit": 10},
    )
    ensure(len(timeline) >= 2, f"timeline too short: {timeline}")
    partner_timeline_item = next((item for item in timeline if item["id"] == partner_checkin_id), None)
    ensure(partner_timeline_item is not None, f"partner checkin missing from timeline: {timeline}")
    ensure(partner_timeline_item["author"]["id"] == partner["id"], f"timeline author missing: {partner_timeline_item}")
    ensure(partner_timeline_item["likes"] == 1, f"timeline likes mismatch: {partner_timeline_item}")
    ensure(
        len(partner_timeline_item["encouragements"]) == 1,
        f"timeline encouragements mismatch: {partner_timeline_item}",
    )

    heatmap = request_json(
        session,
        "GET",
        f"/accountability/{partnership_id}/heatmap",
        token=owner["token"],
    )
    ensure(heatmap["total_days"] >= 1, f"heatmap should contain today: {heatmap}")
    ensure(
        any(item["initiator_checkins"] >= 1 and item["partner_checkins"] >= 1 for item in heatmap["heatmap"]),
        f"heatmap should capture both users: {heatmap}",
    )

    achievement_defs = request_json(
        session,
        "GET",
        "/accountability/achievements",
        token=owner["token"],
    )
    ensure(achievement_defs["total_available"] >= 1, f"achievement definitions missing: {achievement_defs}")

    partnership_achievements = request_json(
        session,
        "GET",
        f"/accountability/{partnership_id}/achievements",
        token=owner["token"],
    )
    ensure(
        isinstance(partnership_achievements["my_achievements"], list)
        and isinstance(partnership_achievements["partner_achievements"], list),
        f"partnership achievements malformed: {partnership_achievements}",
    )

    owner_mine_after = request_json(
        session,
        "GET",
        "/accountability/mine",
        token=owner["token"],
    )
    owner_entry_after = next((item for item in owner_mine_after if item["id"] == partnership_id), None)
    ensure(owner_entry_after is not None, f"active partnership missing after checkins: {owner_mine_after}")
    ensure(owner_entry_after["my_checked_in_today"] is True, f"/mine not updated after checkin: {owner_entry_after}")
    ensure(
        owner_entry_after["partner_checked_in_today"] is True,
        f"/mine partner status not updated after checkin: {owner_entry_after}",
    )
    ensure(owner_entry_after["last_checkin_at"] is not None, f"last_checkin_at missing: {owner_entry_after}")

    request_json(
        session,
        "DELETE",
        f"/accountability/{partnership_id}",
        token=owner["token"],
    )

    owner_notifications = await get_notification_types(owner["id"])
    partner_notifications = await get_notification_types(partner["id"])
    ensure(
        "accountability_partnership_ended" in owner_notifications
        and "accountability_partnership_ended" in partner_notifications,
        f"partnership ended notifications missing: owner={owner_notifications} partner={partner_notifications}",
    )

    recreated = request_json(
        session,
        "POST",
        "/accountability/request",
        token=owner["token"],
        expected=201,
        json={
            "partner_id": partner["id"],
            "initiator_goal": "重建伙伴关系以验证重复发起场景",
            "check_in_days": 3,
        },
    )
    ensure(recreated["id"] == partnership_id, f"ended partnership should be reused: {recreated}")
    ensure(recreated["status"] == "pending", f"recreated partnership should return to pending: {recreated}")

    recreated_active = request_json(
        session,
        "POST",
        f"/accountability/{partnership_id}/respond",
        token=partner["token"],
        json={"accept": True, "partner_goal": "重新配对后继续互相监督"},
    )
    ensure(recreated_active["status"] == "active", f"recreated partnership not active: {recreated_active}")
    ensure(recreated_active["check_in_days"] == 3, f"recreated partnership days not refreshed: {recreated_active}")

    print(
        json.dumps(
            {
                "status": "ALL_OK",
                "friendship_id": friendship_id,
                "partnership_id": partnership_id,
                "owner_checkin_id": owner_checkin_id,
                "partner_checkin_id": partner_checkin_id,
                "timeline_count": len(timeline),
                "heatmap_days": heatmap["total_days"],
                "achievement_total": achievement_defs["total_available"],
                "owner_notifications": owner_notifications,
                "partner_notifications": partner_notifications,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
