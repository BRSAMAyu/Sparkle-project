#!/usr/bin/env python3
"""wt760 S-01 live truth test — two guest accounts, full community loop via gateway :8080.

Discipline:
- Serial, >=1.2s spacing between steps (light load).
- Never touches user ns001 or any other user's data (only wt760s01_* accounts).
- No process restarts, no docker ops, read-only infra inspection elsewhere.
- Every result recorded as JSONL evidence, pass or fail, no fabrication.
"""
import json
import sys
import time
import uuid
import websocket  # websocket-client
import requests

GW = "http://localhost:8080"
GW_WS = "ws://localhost:8080"
TAG = "wt760s01"
OUT = open("/tmp/wt760_s01_evidence.jsonl", "a", encoding="utf-8")
T0 = time.time()


def ev(step, **kw):
    rec = {"t": round(time.time() - T0, 3), "iso": time.strftime("%H:%M:%S"), "step": step, **kw}
    OUT.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    OUT.flush()
    print(json.dumps(rec, ensure_ascii=False, default=str))
    return rec


def http(method, path, token=None, body=None, note=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    t = time.time()
    try:
        r = requests.request(method, GW + path, headers=headers, json=body, timeout=15)
        try:
            data = r.json()
        except Exception:
            data = r.text[:300]
        latency = round((time.time() - t) * 1000, 1)
        ev(f"http {method} {path}", status=r.status_code, latency_ms=latency, note=note,
           resp=json.dumps(data, ensure_ascii=False, default=str)[:600])
        return r.status_code, data, latency
    except Exception as e:
        ev(f"http {method} {path}", status=None, error=repr(e)[:300], note=note)
        return None, None, None


class GroupWS:
    def __init__(self, who, token, gid):
        self.who = who
        self.ws = None
        url = f"{GW_WS}/api/v1/community/groups/{gid}/ws"
        t = time.time()
        try:
            self.ws = websocket.create_connection(
                url, timeout=10, header={"Authorization": f"Bearer {token}"},
                origin="http://localhost:8080")
            ev(f"ws connect {who}", status="OPEN", latency_ms=round((time.time() - t) * 1000, 1),
               path=f"/api/v1/community/groups/{gid}/ws")
        except Exception as e:
            ev(f"ws connect {who}", status="FAIL", error=repr(e)[:300])
            raise

    def recv(self, wait_s=8, tag=""):
        """Receive frames until timeout; returns list of parsed frames."""
        self.ws.settimeout(wait_s)
        frames = []
        deadline = time.time() + wait_s
        while time.time() < deadline:
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                break
            except Exception as e:
                ev(f"ws recv {self.who}", status="ERROR", error=repr(e)[:200], tag=tag)
                break
            try:
                f = json.loads(raw)
            except Exception:
                f = {"raw": str(raw)[:200]}
            frames.append(f)
            ev(f"ws frame {self.who}", tag=tag, frame=json.dumps(f, ensure_ascii=False, default=str)[:500])
        if not frames:
            ev(f"ws frame {self.who}", tag=tag, note="TIMEOUT no frame")
        return frames

    def send(self, obj, tag=""):
        try:
            self.ws.send(json.dumps(obj))
            ev(f"ws send {self.who}", tag=tag, sent=json.dumps(obj, ensure_ascii=False)[:200])
            return True
        except Exception as e:
            ev(f"ws send {self.who}", tag=tag, status="ERROR", error=repr(e)[:200])
            return False

    def close(self, tag=""):
        if self.ws:
            try:
                self.ws.close()
                ev(f"ws close {self.who}", status="CLOSED", tag=tag)
            except Exception as e:
                ev(f"ws close {self.who}", status="ERROR", error=repr(e)[:200], tag=tag)
            self.ws = None


def main():
    ev("run start", tag=TAG, gateway=GW, discipline="serial>=1.2s")

    # ---- 1. two guest accounts ----
    st, a, _ = http("POST", f"/api/v1/auth/guest?guest_id={TAG}_a", note="create test account A")
    assert st == 200, f"guest login A failed: {st}"
    time.sleep(1.2)
    st, b, _ = http("POST", f"/api/v1/auth/guest?guest_id={TAG}_b", note="create test account B")
    assert st == 200, f"guest login B failed: {st}"
    tok_a, uid_a = a["access_token"], a["user"]["id"]
    tok_b, uid_b = b["access_token"], b["user"]["id"]
    ev("accounts", user_a={"id": uid_a, "username": a["user"]["username"], "seed": a.get("seed_status")},
       user_b={"id": uid_b, "username": b["user"]["username"], "seed": b.get("seed_status")})
    time.sleep(1.2)

    # ---- 2. group create + join ----
    st, g, _ = http("POST", "/api/v1/community/groups", tok_a,
                    body={"name": f"{TAG} 真相复测群(测试)", "type": "squad", "is_public": False,
                          "description": "wt760 S-01 两账号真相复测专用，可删"},
                    note="A creates squad")
    assert st in (200, 201), f"group create failed: {st}"
    gid = g["id"]
    ev("group created", group_id=gid)
    time.sleep(1.2)

    st, j, _ = http("POST", f"/api/v1/community/groups/{gid}/join", tok_b, body={}, note="B joins")
    ev("join result", status=st)
    time.sleep(1.2)
    st, mem, _ = http("GET", f"/api/v1/community/groups/{gid}/members", tok_a, note="members after join")
    ids = sorted(m.get("user_id") or m.get("id") or "" for m in mem) if isinstance(mem, list) else mem
    ev("members", member_ids=ids, expect_sorted_pair=sorted([uid_a, uid_b]))
    time.sleep(1.2)

    # ---- 3. WS both connect via gateway ----
    ws_a = GroupWS("A", tok_a, gid)
    time.sleep(1.2)
    ws_b = GroupWS("B", tok_b, gid)

    # drain any welcome/join frames
    ev("drain", note="initial frames after connect")
    ws_a.recv(2, tag="drain-connect")
    ws_b.recv(2, tag="drain-connect")

    # ---- 4. A -> chat, B receives via WS ----
    n1 = f"{TAG}-n1-{uuid.uuid4().hex[:8]}"
    st, m1, lat = http("POST", f"/api/v1/community/groups/{gid}/messages", tok_a,
                       body={"message_type": "text", "content": f"{TAG} A->B 消息1 {n1}", "nonce": n1},
                       note="A sends msg1 with nonce")
    msg1_id = m1.get("id") if isinstance(m1, dict) else None
    frames_b = ws_b.recv(8, tag="msg1-broadcast-to-B")
    got1 = any((f.get("content") or "") .endswith(n1) or f.get("content") == f"{TAG} A->B 消息1 {n1}" for f in frames_b if isinstance(f, dict))
    ack_a = ws_a.recv(6, tag="msg1-ack-or-echo-to-A")
    got_ack = any(f.get("type") == "ack" and f.get("nonce") == n1 for f in ack_a if isinstance(f, dict))
    ev("ASSERT msg1 realtime", b_saw_broadcast=got1, a_got_ack=got_ack, msg1_id=msg1_id)
    time.sleep(1.2)

    # ---- 5. B -> chat, A receives via WS ----
    n2 = f"{TAG}-n2-{uuid.uuid4().hex[:8]}"
    st, m2, lat = http("POST", f"/api/v1/community/groups/{gid}/messages", tok_b,
                       body={"message_type": "text", "content": f"{TAG} B->A 消息2 {n2}", "nonce": n2},
                       note="B sends msg2 with nonce")
    msg2_id = m2.get("id") if isinstance(m2, dict) else None
    frames_a = ws_a.recv(8, tag="msg2-broadcast-to-A")
    got2 = any((f.get("content") or "") == f"{TAG} B->A 消息2 {n2}" for f in frames_a if isinstance(f, dict))
    ack_b = ws_b.recv(6, tag="msg2-ack-to-B")
    got_ack2 = any(f.get("type") == "ack" and f.get("nonce") == n2 for f in ack_b if isinstance(f, dict))
    ev("ASSERT msg2 realtime", a_saw_broadcast=got2, b_got_ack=got_ack2, msg2_id=msg2_id)
    time.sleep(1.2)

    # ---- 6. typing: B sends WS frame, A receives broadcast ----
    ok = ws_b.send({"type": "typing", "user": TAG + "_b"}, tag="typing")
    frames_t = ws_a.recv(6, tag="typing-broadcast-to-A")
    got_t = any(f.get("type") == "typing" and f.get("user_id") == uid_b for f in frames_t if isinstance(f, dict))
    ev("ASSERT typing realtime", sent_ok=ok, a_saw_typing=got_t)
    time.sleep(1.2)

    # ---- 7. checkin both ----
    st, c1, _ = http("POST", "/api/v1/community/checkin", tok_a,
                     body={"group_id": gid, "message": f"{TAG} A 打卡", "today_duration_minutes": 25},
                     note="A checkin")
    cc1 = ws_b.recv(6, tag="checkinA-broadcast-to-B")
    got_c1 = any(f.get("type") == "member_checkin" and f.get("duration") == 25 for f in cc1 if isinstance(f, dict))
    ev("ASSERT checkin A", status=st, resp=json.dumps(c1, ensure_ascii=False)[:300],
       b_saw_member_checkin=got_c1)
    ws_a.recv(3, tag="checkinA-echo-to-A")
    time.sleep(1.2)

    st, c2, _ = http("POST", "/api/v1/community/checkin", tok_b,
                     body={"group_id": gid, "message": f"{TAG} B 打卡", "today_duration_minutes": 40},
                     note="B checkin")
    cc2 = ws_a.recv(6, tag="checkinB-broadcast-to-A")
    got_c2 = any(f.get("type") == "member_checkin" and f.get("duration") == 40 for f in cc2 if isinstance(f, dict))
    ev("ASSERT checkin B", status=st, resp=json.dumps(c2, ensure_ascii=False)[:300],
       a_saw_member_checkin=got_c2)
    ws_b.recv(3, tag="checkinB-echo-to-B")
    time.sleep(1.2)

    # ---- 8. reconnect: B drops, A sends msg3, B reconnects and must see it ----
    ws_b.close(tag="drop-before-msg3")
    time.sleep(1.5)
    n3 = f"{TAG}-n3-{uuid.uuid4().hex[:8]}"
    st, m3, _ = http("POST", f"/api/v1/community/groups/{gid}/messages", tok_a,
                     body={"message_type": "text", "content": f"{TAG} 离线补发 消息3 {n3}", "nonce": n3},
                     note="A sends msg3 while B offline")
    msg3_id = m3.get("id") if isinstance(m3, dict) else None
    ws_a.recv(4, tag="msg3-echo-to-A")
    ev("msg3 sent while B offline", status=st, msg3_id=msg3_id, content=f"{TAG} 离线补发 消息3 {n3}")
    time.sleep(1.5)

    ws_b2 = GroupWS("B-reconnect", tok_b, gid)
    ws_b2.recv(2, tag="reconnect-drain")
    st, hist, _ = http("GET", f"/api/v1/community/groups/{gid}/messages?limit=50", tok_b,
                       note="B reconnect history fetch")
    contents = [h.get("content") for h in hist] if isinstance(hist, list) else []
    ev("ASSERT reconnect refill", status=st, count=len(contents) if isinstance(contents, list) else None,
       contents=contents, msg3_present=bool(contents and any(n3 in (c or "") for c in contents)))
    time.sleep(1.2)
    st, hist_a, _ = http("GET", f"/api/v1/community/groups/{gid}/messages?limit=50", tok_a,
                         note="A history fetch (cross-check)")
    contents_a = [h.get("content") for h in hist_a] if isinstance(hist_a, list) else []
    ev("ASSERT history consistency A vs B", same=bool(contents_a == contents), a_count=len(contents_a))
    time.sleep(1.2)

    # flame/checkin authoritative state
    st, fl, _ = http("GET", f"/api/v1/community/groups/{gid}/flame", tok_a, note="flame status after 2 checkins")
    ev("flame status", status=st, resp=json.dumps(fl, ensure_ascii=False)[:300])

    # close
    ws_a.close(tag="end")
    ws_b2.close(tag="end")
    ev("run end", group_id=gid, user_a=uid_a, user_b=uid_b,
       msg_ids=[msg1_id, msg2_id, msg3_id])
    print(f"\nGROUP_ID={gid}\nUSER_A={uid_a}\nUSER_B={uid_b}\nMSG1={msg1_id}\nMSG2={msg2_id}\nMSG3={msg3_id}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        ev("FATAL", error=str(e)[:300])
        sys.exit(1)
