#!/usr/bin/env python3
"""wt760 S-01 follow-up: verify nonce-ACK delivery via personal channel (designed path),
plus send-message-while-not-connected (offline member) semantics. Light load, serial."""
import json, time, uuid, requests, websocket

GW = "http://localhost:8080"
GW_WS = "ws://localhost:8080"
TAG = "wt760s01"
OUT = open("/tmp/wt760_s01_evidence.jsonl", "a", encoding="utf-8")
T0 = time.time()
GID = "52fe48b1-98e7-475f-b3db-135eacb149b7"  # from run1
UID_A = "eae2761d-3dde-4a89-a01d-5ae7e4954ce9"

def ev(step, **kw):
    rec = {"t": round(time.time() - T0, 3), "iso": time.strftime("%H:%M:%S"), "step": step, **kw}
    OUT.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n"); OUT.flush()
    print(json.dumps(rec, ensure_ascii=False, default=str))

def http(method, path, token=None, body=None, note=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    t = time.time()
    r = requests.request(method, GW + path, headers=h, json=body, timeout=15)
    try: data = r.json()
    except Exception: data = r.text[:200]
    ev(f"http {method} {path}", status=r.status_code, latency_ms=round((time.time()-t)*1000,1),
       note=note, resp=json.dumps(data, ensure_ascii=False, default=str)[:400])
    return r.status_code, data

# re-login both accounts (tokens from run1 not persisted)
st, a = http("POST", f"/api/v1/auth/guest?guest_id={TAG}_a", note="re-login A (existing, reseeded)")
assert st == 200
time.sleep(1.2)
st, b = http("POST", f"/api/v1/auth/guest?guest_id={TAG}_b", note="re-login B")
assert st == 200
tok_a, tok_b = a["access_token"], b["access_token"]
time.sleep(1.2)

# A opens GROUP ws; B opens BOTH group ws and PERSONAL ws (mobile-equivalent dual channel)
gws_a = websocket.create_connection(f"{GW_WS}/api/v1/community/groups/{GID}/ws", timeout=10,
                                    header={"Authorization": f"Bearer {tok_a}"}, origin="http://localhost:8080")
ev("ws A group OPEN")
time.sleep(1.2)
gws_b = websocket.create_connection(f"{GW_WS}/api/v1/community/groups/{GID}/ws", timeout=10,
                                    header={"Authorization": f"Bearer {tok_b}"}, origin="http://localhost:8080")
ev("ws B group OPEN")
time.sleep(1.2)
pws_b = websocket.create_connection(f"{GW_WS}/api/v1/community/ws/connect", timeout=10,
                                    header={"Authorization": f"Bearer {tok_b}"}, origin="http://localhost:8080")
ev("ws B personal OPEN")
time.sleep(1.2)

def drain(ws, wait_s, tag):
    ws.settimeout(wait_s)
    frames = []
    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            break
        except Exception as e:
            ev(f"ws recv {tag}", error=repr(e)[:150]); break
        try: f = json.loads(raw)
        except Exception: f = {"raw": str(raw)[:150]}
        frames.append(f)
        ev(f"ws frame {tag}", frame=json.dumps(f, ensure_ascii=False, default=str)[:300])
    if not frames:
        ev(f"ws frame {tag}", note="TIMEOUT no frame")
    return frames

drain(gws_a, 2, "A-init"); drain(gws_b, 2, "B-init"); drain(pws_b, 2, "B-p-init")

# A sends msg4 with nonce -> ACK should arrive on B's PERSONAL channel? No — ack goes to SENDER (A).
# A only holds group channel in this step, so A's ack must NOT arrive anywhere (verified in run1).
# Then repeat with A holding BOTH channels: ack should arrive on A's personal channel.
# Step 1: A group-only (control, expect no ack anywhere)
n4 = f"{TAG}-n4-{uuid.uuid4().hex[:8]}"
st, m4 = http("POST", f"/api/v1/community/groups/{GID}/messages", tok_a,
              body={"message_type": "text", "content": f"{TAG} ack控制 消息4 {n4}", "nonce": n4},
              note="A sends msg4 group-channel-only (control)")
drain(gws_b, 4, "B-msg4"); drain(gws_a, 4, "A-msg4-grouponly")
drain(pws_b, 2, "B-p-msg4")
time.sleep(1.2)

# Step 2: A also opens personal channel (dual), sends msg5 -> ack expected on A personal channel
pws_a = websocket.create_connection(f"{GW_WS}/api/v1/community/ws/connect", timeout=10,
                                    header={"Authorization": f"Bearer {tok_a}"}, origin="http://localhost:8080")
ev("ws A personal OPEN")
drain(pws_a, 2, "A-p-init")
time.sleep(1.2)
n5 = f"{TAG}-n5-{uuid.uuid4().hex[:8]}"
st, m5 = http("POST", f"/api/v1/community/groups/{GID}/messages", tok_a,
              body={"message_type": "text", "content": f"{TAG} ack双通道 消息5 {n5}", "nonce": n5},
              note="A sends msg5 with A holding dual channels")
frames_pa = drain(pws_a, 6, "A-p-msg5-ack")
got_ack = any(isinstance(f, dict) and f.get("type") == "ack" and f.get("nonce") == n5 for f in frames_pa)
frames_ga = drain(gws_a, 3, "A-g-msg5-echo")
ev("ASSERT ack-via-personal-channel", ack_on_personal=got_ack, nonce=n5)
time.sleep(1.2)

# offline-member semantics: B closes both; A sends msg6; B reconnects -> refill
gws_b.close(); pws_b.close()
ev("B offline (both channels closed)")
time.sleep(1.5)
n6 = f"{TAG}-n6-{uuid.uuid4().hex[:8]}"
st, m6 = http("POST", f"/api/v1/community/groups/{GID}/messages", tok_a,
              body={"message_type": "text", "content": f"{TAG} 离线消息6 {n6}", "nonce": n6},
              note="A sends msg6 while B fully offline")
drain(gws_a, 3, "A-msg6-echo"); drain(pws_a, 2, "A-p-msg6")
time.sleep(1.5)
gws_b2 = websocket.create_connection(f"{GW_WS}/api/v1/community/groups/{GID}/ws", timeout=10,
                                     header={"Authorization": f"Bearer {tok_b}"}, origin="http://localhost:8080")
ev("ws B group reconnect OPEN")
st, hist = http("GET", f"/api/v1/community/groups/{GID}/messages?limit=50", tok_b, note="B history after reconnect")
contents = [h.get("content") for h in hist] if isinstance(hist, list) else []
ev("ASSERT offline refill", count=len(contents), msg6_present=bool(any(n6 in (c or "") for c in contents)),
   last3=contents[:3])

for w in (gws_a, pws_a, gws_b2):
    try: w.close()
    except Exception: pass
ev("run end")
