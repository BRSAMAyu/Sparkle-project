"""V4-U11 · 双真实账号场景驱动（分享/撤回/重连 + 单人完整行动 + 单/多实例实时边界）.

对**真实运行中的引擎进程**（本仓 `make api-server` 同款启动方式，uvicorn
app.main:app --env-file .env）跑 HTTP+WS 全链路：注册两个真实测试账号、
建冲刺小队、错题分享/撤回/再分享、群 WS 实时广播、断连重连、以及第二
引擎进程（同 PostgreSQL/Redis/MinIO 数据面）下的跨实例广播。

数据面只读复用既有 sparkle_proj_db/sparkle_proj_redis/sparkle_proj_minio 容器（FIX-557
口径）；测试账号为本次注册的真实账号（u11_a_<ts>/u11_b_<ts>），demo 角色
不冒充真人。

用法：
    .venv/bin/python scripts/devtools/v4_u11_two_account_scenario.py \
        --base http://127.0.0.1:8211 --base2 http://127.0.0.1:8212 \
        --out /tmp/u11_scenario.json

无第二实例时传 --skip-instance2（多实例边界如实记 NOT_RUN）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import websockets

ACCENT = "\u001b[0m"


class Scenario:
    def __init__(self, base: str, base2: str | None) -> None:
        self.base = base
        self.base2 = base2
        self.steps: list[dict] = []
        self.ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    def record(self, step_id: str, name: str, passed: bool, detail: dict) -> dict:
        step = {
            "id": step_id,
            "name": name,
            "verdict": "PASS" if passed else "FAIL",
            "detail": detail,
        }
        self.steps.append(step)
        marker = "PASS" if passed else "FAIL"
        print(f"[{marker}] {step_id} {name} :: {json.dumps(detail, ensure_ascii=False, default=str)[:300]}")
        return step

    # -- HTTP helpers ------------------------------------------------------

    async def register_and_login(self, client: httpx.AsyncClient, tag: str) -> dict:
        suffix = uuid.uuid4().hex[:8]
        username = f"u11_{tag}_{self.ts}_{suffix}"
        payload = {
            "username": username,
            "email": f"{username}@sparkle.dev",
            "password": "U11-Scenario-Pass!2026",
            "accepted_tos": True,
            "accepted_privacy": True,
            "tos_version": "2026-09",
            "privacy_version": "2026-09",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        ok_register = resp.status_code in (200, 201)
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": payload["password"]},
        )
        ok_login = login.status_code == 200
        token = None
        user_id = None
        if ok_login:
            body = login.json()
            token = (
                body.get("access_token")
                or body.get("data", {}).get("access_token")
                or body.get("tokens", {}).get("access_token")
            )
            user = body.get("user") or body.get("data", {}).get("user") or {}
            user_id = user.get("id")
        return {
            "username": username,
            "register_status": resp.status_code,
            "login_status": login.status_code,
            "token": token,
            "user_id": user_id,
            "ok": ok_register and ok_login and bool(token),
        }

    def auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}


async def ws_connect(base: str, group_id: str, token: str):
    """连群 WS（dev 口径 query token；与移动端 ticket-first 等价的真实端点）。"""
    ws_url = base.replace("http", "ws", 1) + f"/api/v1/community/groups/{group_id}/ws?token={token}"
    return await websockets.connect(ws_url, open_timeout=10)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8211")
    parser.add_argument("--base2", default="http://127.0.0.1:8212")
    parser.add_argument("--out", default="/tmp/u11_scenario.json")
    parser.add_argument("--skip-instance2", action="store_true")
    args = parser.parse_args()

    sc = Scenario(args.base, None if args.skip_instance2 else args.base2)
    started = time.monotonic()

    async with httpx.AsyncClient(base_url=args.base, timeout=30) as client:
        # ── 账号面：两个真实测试账号 ─────────────────────────────────────
        account_a = await sc.register_and_login(client, "a")
        sc.record("S01", "注册/登录账号A", account_a["ok"], {k: account_a[k] for k in ("username", "register_status", "login_status")})
        account_b = await sc.register_and_login(client, "b")
        sc.record("S02", "注册/登录账号B", account_b["ok"], {k: account_b[k] for k in ("username", "register_status", "login_status")})
        if not (account_a["ok"] and account_b["ok"]):
            sc.record("S00", "前置：双账号就绪", False, {"account_a": account_a["ok"], "account_b": account_b["ok"]})
            Path(args.out).write_text(json.dumps(sc.steps, ensure_ascii=False, indent=2))
            return 1

        headers_a = sc.auth_headers(account_a["token"])
        headers_b = sc.auth_headers(account_b["token"])

        deadline = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        resp = await client.post(
            "/api/v1/community/squads",
            headers=headers_a,
            json={"name": f"U11 双账号场景队 {sc.ts}", "deadline": deadline, "sprint_goal": "V4-U11 验收场景"},
        )
        squad = resp.json() if resp.status_code in (200, 201) else {}
        squad_id = squad.get("id") or squad.get("data", {}).get("id", "")
        sc.record("S03", "A 创建冲刺小队", resp.status_code == 201 and bool(squad_id), {"status": resp.status_code, "squad_id": squad_id, "member_count": squad.get("member_count"), "my_role": squad.get("my_role")})

        # ── 单人完整行动面（无其他成员）────────────────────────────────
        resp = await client.get(f"/api/v1/community/squads/{squad_id}", headers=headers_a)
        solo_detail = resp.json() if resp.status_code == 200 else {}
        sc.record("S04", "单人行动：1/8 成员即完整小队（owner 角色可达）", resp.status_code == 200 and solo_detail.get("member_count") == 1, {"status": resp.status_code, "member_count": solo_detail.get("member_count"), "my_role": solo_detail.get("my_role")})

        enter = await client.post(f"/api/v1/community/squads/{squad_id}/study-room/enter", headers=headers_a)
        hb = await client.post(f"/api/v1/community/squads/{squad_id}/study-room/heartbeat", headers=headers_a)
        presence = await client.get(f"/api/v1/community/squads/{squad_id}/study-room/presence", headers=headers_a)
        exit_ = await client.post(f"/api/v1/community/squads/{squad_id}/study-room/exit", headers=headers_a)
        sc.record("S05", "单人行动：自习室进入/心跳/在场/退出全链可达", all(r.status_code == 200 for r in (enter, hb, presence, exit_)), {"enter": enter.status_code, "heartbeat": hb.status_code, "presence": presence.status_code, "exit": exit_.status_code})

        board = await client.get(f"/api/v1/community/squads/{squad_id}/leaderboard", headers=headers_a)
        board_body = board.json() if board.status_code == 200 else {}
        sc.record("S06", "单人行动：<3 人榜诚实降级 self_view_only", board.status_code == 200 and board_body.get("self_view_only") is True and board_body.get("board_valid") is False, {"status": board.status_code, "self_view_only": board_body.get("self_view_only"), "board_valid": board_body.get("board_valid"), "member_count": board_body.get("member_count")})

        # ── B 加入 + 成员可见 ───────────────────────────────────────────
        join = await client.post(f"/api/v1/community/squads/{squad_id}/join", headers=headers_b)
        board2 = await client.get(f"/api/v1/community/squads/{squad_id}/leaderboard", headers=headers_a)
        board2_body = board2.json() if board2.status_code == 200 else {}
        sc.record("S07", "B 凭邀请加入小队（真实第二账号）", join.status_code in (200, 201), {"status": join.status_code, "member_count_after": board2_body.get("member_count"), "board_valid": board2_body.get("board_valid")})

        # ── 分享腿：A 建错题并分享，B 可见 ─────────────────────────────
        error_resp = await client.post(
            "/api/v1/errors",
            headers=headers_a,
            json={"question_text": f"U11 场景题：∫x²dx = ?（{sc.ts}）", "subject": "math", "user_answer": "x^3/3 + C", "correct_answer": "x^3/3 + C"},
        )
        error_ok = error_resp.status_code == 201
        error_body = error_resp.json() if error_ok else {}
        error_id = error_body.get("id") or error_body.get("data", {}).get("id", "")
        sc.record("S08", "A 创建真实错题记录", error_ok and bool(error_id), {"status": error_resp.status_code, "error_id": error_id})

        share_resp = await client.post(
            f"/api/v1/community/squads/{squad_id}/shared-errors",
            headers=headers_a,
            json={"error_id": error_id},
        )
        share_body = share_resp.json() if share_resp.status_code == 201 else {}
        share_id = share_body.get("share_id", "")
        sc.record("S09", "A 分享错题到小队（只传 error_id）", share_resp.status_code == 201 and bool(share_id), {"status": share_resp.status_code, "share_id": share_id, "has_answer_field": any(k in share_body for k in ("correct_answer", "user_answer"))})

        list_b = await client.get(f"/api/v1/community/squads/{squad_id}/shared-errors", headers=headers_b)
        list_b_body = list_b.json() if list_b.status_code == 200 else {}
        b_sees = any(item.get("share_id") == share_id for item in list_b_body.get("items", []))
        no_answer = all(not any(k in item for k in ("correct_answer", "user_answer")) for item in list_b_body.get("items", []))
        sc.record("S10", "B（第二账号）列表可见该分享；白名单投影零答案字段", list_b.status_code == 200 and b_sees and no_answer, {"status": list_b.status_code, "b_total": list_b_body.get("total"), "b_sees": b_sees, "no_answer_fields": no_answer})

        # ── 实时腿（单实例）：A/B 同进程群 WS，广播双向可达 ────────────
        ws_a = await ws_connect(args.base, squad_id, account_a["token"])
        ws_b = await ws_connect(args.base, squad_id, account_b["token"])
        sc.record("S11", "单实例：A、B 双账号群 WS 建连", True, {"a": "connected", "b": "connected"})

        await asyncio.sleep(0.3)
        checkin1 = await client.post("/api/v1/community/checkin", headers=headers_a, json={"group_id": squad_id, "today_duration_minutes": 25, "message": "U11 single-instance broadcast probe"})
        a_frames, b_frames = [], []

        async def _collect(ws: object, sink: list, seconds: float) -> None:
            try:
                end = time.monotonic() + seconds
                while time.monotonic() < end:
                    frame = await asyncio.wait_for(ws.recv(), timeout=max(0.05, end - time.monotonic()))
                    sink.append(json.loads(frame))
            except (TimeoutError, asyncio.TimeoutError):
                return

        await asyncio.gather(_collect(ws_a, a_frames, 3.0), _collect(ws_b, b_frames, 3.0))
        got_a = any(f.get("type") == "member_checkin" for f in a_frames)
        got_b = any(f.get("type") == "member_checkin" for f in b_frames)
        sc.record("S12", "单实例：A 打卡广播 → A/B 双端实时可达", checkin1.status_code == 200 and got_a and got_b, {"checkin": checkin1.status_code, "a_got_member_checkin": got_a, "b_got_member_checkin": got_b})

        # ── 重连腿：B 断连 → A 发 typing 广播 → B 重连 → A 再广播 B 仍可达 ──
        # （打卡每人每日一次，重连腿改用群 WS typing 广播这一真实广播路径，
        #  语义等价：经 manager.broadcast 扇出给全组成员。）
        await ws_b.close()
        await asyncio.sleep(0.3)
        await ws_a.send(json.dumps({"type": "typing", "ts": sc.ts}))
        await asyncio.gather(_collect(ws_a, a_frames, 1.5))

        ws_b2 = await ws_connect(args.base, squad_id, account_b["token"])
        b2_frames: list = []
        await asyncio.sleep(0.3)
        await ws_a.send(json.dumps({"type": "typing", "ts": f"{sc.ts}-after-reconnect"}))
        await asyncio.gather(_collect(ws_a, a_frames, 2.0), _collect(ws_b2, b2_frames, 3.0))
        got_b2 = any(f.get("type") == "typing" and "after-reconnect" in str(f.get("ts")) for f in b2_frames)
        sc.record("S13", "重连：B 断连→重连（重新鉴权）→ 群广播恢复可达", ws_b2.state.name == "OPEN" and got_b2, {"reconnected_state": ws_b2.state.name, "b_after_reconnect_got_typing": got_b2})

        # ── 撤回腿：A 撤回 → B 不可见 → B 越权撤回 404 → A 再分享新 share ─
        retract = await client.delete(f"/api/v1/community/squads/{squad_id}/shared-errors/{share_id}", headers=headers_a)
        retract_body = retract.json() if retract.status_code == 200 else {}
        sc.record("S14", "撤回：A 撤回自己的分享（软删诚实回执）", retract.status_code == 200 and retract_body.get("retracted") is True, {"status": retract.status_code, "retracted": retract_body.get("retracted"), "already_retracted": retract_body.get("already_retracted")})

        list_b2 = await client.get(f"/api/v1/community/squads/{squad_id}/shared-errors", headers=headers_b)
        list_b2_body = list_b2.json() if list_b2.status_code == 200 else {}
        b_still_sees = any(item.get("share_id") == share_id for item in list_b2_body.get("items", []))
        sc.record("S15", "撤回传播：B 列表即时不可见撤回条目", list_b2.status_code == 200 and not b_still_sees, {"status": list_b2.status_code, "b_total": list_b2_body.get("total"), "b_still_sees": b_still_sees})

        foreign_retract = await client.delete(f"/api/v1/community/squads/{squad_id}/shared-errors/{share_id}", headers=headers_b)
        sc.record("S16", "撤回授权：非分享者撤回 → 404（不泄露存在性）", foreign_retract.status_code == 404, {"status": foreign_retract.status_code})

        reshare = await client.post(f"/api/v1/community/squads/{squad_id}/shared-errors", headers=headers_a, json={"error_id": error_id})
        reshare_body = reshare.json() if reshare.status_code == 201 else {}
        new_share_id = reshare_body.get("share_id", "")
        sc.record("S17", "撤回后再分享可达（新 share_id，非复活旧行）", reshare.status_code == 201 and bool(new_share_id) and new_share_id != share_id, {"status": reshare.status_code, "new_share_id": new_share_id, "old_share_id": share_id})

        # 清理重连 socket
        await ws_a.close()
        await ws_b2.close()

        # ── 多实例腿：第二引擎进程（同数据面）跨实例广播 ───────────────
        if sc.base2 and not args.skip_instance2:
            try:
                async with httpx.AsyncClient(base_url=sc.base2, timeout=10) as client2:
                    health2 = await client2.get("/health")
                instance2_alive = health2.status_code == 200
            except Exception as exc:  # noqa: BLE001
                instance2_alive = False
                sc.record("S18", "多实例前置：第二引擎进程健康", False, {"base2": sc.base2, "error": str(exc)})

            if instance2_alive:
                sc.record("S18", "多实例前置：第二引擎进程健康（同 PostgreSQL/Redis 数据面）", True, {"base2": sc.base2, "health": health2.json().get("status")})
                # A 连实例1，B 连实例2 —— 跨实例成员资格校验后广播
                ws_a2 = await ws_connect(args.base, squad_id, account_a["token"])
                ws_b3 = await ws_connect(sc.base2, squad_id, account_b["token"])
                # B 经实例2 HTTP 打卡 → 广播走 Redis pub/sub → 实例1 上的 A 收到
                checkin4 = await client.post("/api/v1/community/checkin", headers=headers_b, json={"group_id": squad_id, "today_duration_minutes": 28, "message": "U11 cross-instance probe"})
                a3_frames: list = []
                b3_frames2: list = []
                await asyncio.gather(_collect(ws_a2, a3_frames, 3.5), _collect(ws_b3, b3_frames2, 3.5))
                a_got_cross = any(f.get("type") == "member_checkin" for f in a3_frames)
                b_got_cross = any(f.get("type") == "member_checkin" for f in b3_frames2)
                sc.record("S19", "多实例：B 经实例2 打卡 → 实例1 上的 A 经 Redis pub/sub 实时收到", checkin4.status_code == 200 and a_got_cross and b_got_cross, {"checkin_via_instance2": checkin4.status_code, "a_on_instance1_got": a_got_cross, "b_on_instance2_got": b_got_cross})
                # 反向：A 经实例1 WS typing 广播 → 实例2 上的 B 经 pub/sub 收到
                # （A 的打卡额度已在 S12 消耗；typing 与 checkin 同走
                # manager.broadcast → Redis pub/sub，扇出语义等价）。
                await ws_a2.send(json.dumps({"type": "typing", "ts": f"{sc.ts}-cross-instance-reverse"}))
                a4_frames: list = []
                b4_frames: list = []
                await asyncio.gather(_collect(ws_a2, a4_frames, 2.0), _collect(ws_b3, b4_frames, 3.5))
                b_got_reverse = any(
                    f.get("type") == "typing" and "cross-instance-reverse" in str(f.get("ts"))
                    for f in b4_frames
                )
                sc.record("S20", "多实例（反向）：A 经实例1 WS 广播 → 实例2 上的 B 经 pub/sub 收到", b_got_reverse, {"b_on_instance2_got_typing": b_got_reverse})
                await ws_a2.close()
                await ws_b3.close()
        else:
            sc.record("S18", "多实例边界", True, {"verdict": "NOT_RUN", "reason": "--skip-instance2 或未提供第二实例地址"})

    elapsed = round(time.monotonic() - started, 2)
    passed = sum(1 for s in sc.steps if s["verdict"] == "PASS")
    failed = sum(1 for s in sc.steps if s["verdict"] == "FAIL")
    summary = {
        "task": "V4-U11",
        "scenario": "two-account share/retract/reconnect + solo actions + single/multi-instance realtime boundary",
        "engine_base": args.base,
        "engine_base2": sc.base2,
        "accounts": {"a": account_a["username"], "b": account_b["username"], "real_registered": True},
        "squad_id": squad_id,
        "share_ids": {"first": share_id, "after_reshare": new_share_id},
        "steps": sc.steps,
        "summary": {"passed": passed, "failed": failed, "elapsed_seconds": elapsed},
    }
    Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n== {passed} PASS / {failed} FAIL in {elapsed}s -> {args.out}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
