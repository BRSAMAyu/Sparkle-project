#!/usr/bin/env python3
"""V4-Q04 端到端有用延迟与完整成本重测 — App→Gateway→Engine 真链 WS 采样（真模型真路由）.

沿真实链路（WS 客户端 = App 传输层替身 → Go Gateway /ws/chat → gRPC AgentService.StreamChat
→ ChatOrchestrator）按 L0 快答 / L1 标准 / L2 深推理 / L3 编排·长上下文 四层驱动语料，
逐 query 记录 **四个时刻分开** 的延迟与全量成本字段：

  t_ack_s          ack 时刻（gateway 接受回执帧 type=ack）
  t_first_delta_s  首个文本 delta 时刻（type=delta）
  t_first_useful_s 首个有用内容时刻（冻结确定性 oracle：见 USEFUL_* 常量；
                   按 METRICS M05/M06 语义——ack/stage/模板状态语不算有用内容）
  t_complete_s     完整交付时刻（gateway 终帧 type=meta 或流正常结束）

成本三源对账：流内 usage 帧（引擎回执，I10 单一核价权威）+ DB token_usage 归因
（只读 SELECT，docker exec sparkle_db psql）+ bench 侧官方价表（复用 E08 价表，
来源日期绑定）。计费完整性红项：no_generation 带 token、未归因 token、usage 帧缺失。

分母纪律：每条发送的 query 计一层分母；error/timeout/cancel 全部保留在分母内，
不剔除失败样本美化分位（验收铁律 3）。取消探针（ack 后取消 / 首 delta 后取消）
单独标记 kind=cancel_probe 并计入层分母。

用法:
  python3 bench_v4_q04_e2e_latency_cost.py run --layers L0,L1,L2,L3 [--passes 4] [--tag NAME]
  python3 bench_v4_q04_e2e_latency_cost.py run --cancel-probe --layers L0,L1,L2,L3
  python3 bench_v4_q04_e2e_latency_cost.py summarize [--tag NAME]

环境变量:
  Q04_WS_URL       默认 ws://127.0.0.1:8081/ws/chat
  Q04_HTTP_BASE    默认 http://127.0.0.1:8001/api/v1
  Q04_GUEST        bench guest 账号（默认 wtQ04_bench，与其他 bench 隔离）
  Q04_OUT_DIR      默认 <repo>/outputs/V4-Q04（gitignored；交付时拷贝至 evidence）

语料与价表来源：scripts/devtools/bench_ai_stack_l0_l3.py（WT372-E08，104 条学习成长域
语料 + 官方价表）原样复用；每层 4 遍 × 26 = 104 样本。重复执行不污染测量的依据：
网关语义缓存对带 extra_context 的请求一律跳过（chat_orchestrator_chatflow.go
shouldSkipCache）；引擎幂等缓存按 session_id+request_id 键（本 bench 每 query 唯一）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "devtools"))
import bench_ai_stack_l0_l3 as E08  # noqa: E402  (语料与价表单一来源)

WS_URL = os.environ.get("Q04_WS_URL", "ws://127.0.0.1:8081/ws/chat")
HTTP_BASE = os.environ.get("Q04_HTTP_BASE", "http://127.0.0.1:8001/api/v1")
GUEST_ID = os.environ.get("Q04_GUEST", "wtQ04_bench")
REQ_PREFIX = os.environ.get("Q04_REQ_PREFIX", "wtq04")
OUT_DIR = Path(os.environ.get("Q04_OUT_DIR", str(REPO_ROOT / "outputs" / "V4-Q04")))
PSQL_CONTAINER = os.environ.get("Q04_PSQL_CONTAINER", "sparkle_db")
PSQL_USER = "postgres"
PSQL_DB = "sparkle"

SESSION_ROTATE_EVERY = 3
INTER_QUERY_SLEEP_S = 0.8
# 层级客户端硬超时（秒）。L3 参照 M07 硬 180s + gateway GRPC_TIMEOUT 180s 观察余量。
LAYER_TIMEOUT_S = {"L0": 60.0, "L1": 90.0, "L2": 150.0, "L3": 200.0}
LAYERS = ["L0", "L1", "L2", "L3"]

# ---------------------------------------------------------------------------
# 有用内容 oracle（冻结于采样前；确定性粗筛，非模型评审——语义如实声明）
# METRICS M05: 「按请求相关内容判定，不是ack/stage」；M06 caveat: 「模板鸡汤不算提案」。
# ---------------------------------------------------------------------------
# 引擎/网关已知状态语与纯 ack 模板（I09 快路状态帧 details 也在内）——这些文本即使
# 以 delta 形态到达也不构成「有用内容」。
BOILERPLATE_TEXTS = {
    "已收到你的消息。",
    "已收到你的消息",
    "正在思考",
    "正在思考…",
    "正在思考...",
    "让我想想",
    "让我想想。",
    "好的。",
    "好的",
    "收到",
    "我明白了",
    "明白了",
}
_PUNCT_RE = re.compile(r"^[\s\W_]*$", re.UNICODE)
_MD_NOISE_RE = re.compile(r"[#*`>\-\[\]()!_\n\r\t ]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# phatic 意图的响应本身就是回答（问候的答案就是问候语），有效字符阈值放宽。
PHATIC_INTENTS = {"greeting", "ack", "thanks", "continuation", "farewell"}
PHATIC_MIN_CHARS = 2
SUBSTANTIVE_MIN_CHARS = 12  # 冻结：累计有效字符 ≥12 才算「有用内容」（实质请求须实质内容）


def _effective_chars(text: str) -> int:
    """有效字符数：剥 markdown 噪声符号与空白后的长度（CJK/字母/数字各计 1）。"""
    return len(_MD_NOISE_RE.sub("", text))


def first_useful_check(intent: str, cumulative_text: str) -> bool:
    """冻结 oracle：给定意图与累计响应文本，判定此刻是否已出现有用内容。"""
    if not cumulative_text:
        return False
    stripped = cumulative_text.strip()
    if not stripped or _PUNCT_RE.match(stripped):
        return False
    # 纯模板状态语不算（无论意图）
    if stripped in BOILERPLATE_TEXTS:
        return False
    need = PHATIC_MIN_CHARS if intent in PHATIC_INTENTS else SUBSTANTIVE_MIN_CHARS
    return _effective_chars(cumulative_text) >= need


# ---------------------------------------------------------------------------
# guest 认证（幂等：已存在账号直接登录）；guest 端点零模型调用
# ---------------------------------------------------------------------------
def guest_auth() -> tuple[str, str]:
    import httpx  # noqa: PLC0415

    r = httpx.post(f"{HTTP_BASE}/auth/guest", params={"guest_id": GUEST_ID}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["user"]["id"]


def db_fetch_token_usage(request_ids: list[str]) -> dict[str, dict]:
    """只读批量取 token_usage 归因。失败返回空（如实标注 attribution_failed）。"""
    if not request_ids:
        return {}
    id_list = ",".join(f"'{rid}'" for rid in request_ids)
    sql = (
        "SELECT coalesce(json_agg(t),'[]'::json) FROM ("
        "SELECT request_id, model, model_tier, ai_reasoning_mode, prompt_tokens, "
        "completion_tokens, total_tokens, cost FROM token_usage "
        f"WHERE request_id IN ({id_list})) t"
    )
    cmd = ["docker", "exec", PSQL_CONTAINER, "psql", "-U", PSQL_USER, "-d", PSQL_DB, "-Atc", sql]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        rows = json.loads(out.stdout or "[]")
        return {r["request_id"]: r for r in rows}
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"[warn] db attribution failed: {exc}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# 单 query 采样：一条 WS 连接一轮（连接建立成本单独计时，不计入四时刻）
# ---------------------------------------------------------------------------
async def sample_one(ws_url: str, token: str, q: dict, request_id: str,
                     session_id: str, kind: str = "corpus",
                     cancel_after: str | None = None) -> dict:
    import websockets  # noqa: PLC0415

    rec: dict = {
        "qid": q["qid"], "layer": q["layer"], "persona": q["persona"],
        "lang": q["lang"], "intent": q["intent"], "lane": q["lane"],
        "reasoning_mode_sent": q["reasoning_mode"], "chat_mode_sent": q["chat_mode"],
        "message_chars": len(q["text"]), "request_id": request_id,
        "run_tag": q.get("run_tag", "run"), "kind": kind, "cancel_after": cancel_after,
        "ts_start_utc": datetime.now(timezone.utc).isoformat(),
    }
    extra = {"reasoning_mode": q["reasoning_mode"]}
    if q["lane"] == "pro":
        extra["user_tier"] = "pro"
    send_msg = {
        "type": "message", "message": q["text"], "session_id": session_id,
        "request_id": request_id, "extra_context": extra, "chat_mode": q["chat_mode"],
    }
    url = f"{ws_url}?token={token}"

    t_ack = t_first_delta = t_first_fulltext = t_first_stage = None
    t_first_useful = t_complete = t_error = None
    first_stage_name = ""
    stages_seq: list[str] = []
    usage_frame = None
    usage_frame_meta: dict = {}
    error_info = None
    deltas = 0
    status_events = 0
    frame_count = 0
    response_text = ""
    full_text = ""
    observed_md: dict[str, str] = {}
    frames: list[dict] = []
    meta_frame = None
    outcome = "delivered"
    ws_open_s = None

    t_conn0 = time.perf_counter()
    try:
        async with websockets.connect(url, max_size=2**23, open_timeout=15,
                                      close_timeout=5) as ws:
            ws_open_s = round(time.perf_counter() - t_conn0, 4)
            t0 = time.perf_counter()
            await ws.send(json.dumps(send_msg, ensure_ascii=False))
            useful_seen = False
            try:
                while True:
                    raw = await asyncio.wait_for(ws.recv(), timeout=LAYER_TIMEOUT_S[q["layer"]])
                    t = time.perf_counter() - t0
                    frame_count += 1
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        msg = {"type": "non_json"}
                    ftype = msg.get("type", "")
                    md = msg.get("metadata") or {}
                    if isinstance(md, dict):
                        for k, v in md.items():
                            if isinstance(v, str):
                                observed_md.setdefault(k, v[:400])
                    if t_ack is None and ftype == "ack":
                        t_ack = t
                    if ftype == "status_update":
                        status_events += 1
                        st = msg.get("status") or {}
                        ux = md.get("ux_progress") if isinstance(md, dict) else None
                        stage = None
                        if isinstance(ux, dict) and ux.get("stage"):
                            stage = str(ux["stage"])
                        elif st.get("state"):
                            stage = str(st["state"])
                        if stage:
                            stages_seq.append(stage)
                            if t_first_stage is None:
                                t_first_stage = t
                                first_stage_name = stage
                    elif ftype == "delta":
                        deltas += 1
                        if t_first_delta is None:
                            t_first_delta = t
                        response_text += msg.get("delta", "")
                        if not useful_seen and first_useful_check(q["intent"], response_text):
                            t_first_useful = t
                            useful_seen = True
                    elif ftype == "full_text":
                        ft = msg.get("full_text", "")
                        if t_first_fulltext is None:
                            t_first_fulltext = t
                        if len(ft) > len(full_text):
                            full_text = ft
                        if not useful_seen and first_useful_check(q["intent"], ft):
                            t_first_useful = t
                            useful_seen = True
                    elif ftype == "usage":
                        usage_frame = {
                            "prompt_tokens": (msg.get("usage") or {}).get("prompt_tokens"),
                            "completion_tokens": (msg.get("usage") or {}).get("completion_tokens"),
                            "total_tokens": (msg.get("usage") or {}).get("total_tokens"),
                            "cost_micro_usd": (msg.get("usage") or {}).get("cost_micro_usd"),
                        }
                        usage_frame_meta = {
                            "usage_cost_unpriced": md.get("usage_cost_unpriced") if isinstance(md, dict) else None,
                            "model_key": md.get("model_key") if isinstance(md, dict) else None,
                        }
                    elif ftype == "error":
                        err = msg.get("error") or {}
                        error_info = {"code": err.get("error_code") or err.get("code"),
                                      "message": str(err.get("message", ""))[:300]}
                        t_error = t
                    elif ftype == "meta":
                        meta_frame = msg.get("meta") or msg
                        t_complete = t
                        break  # 终帧：完整交付
                    frames.append({"t": round(t, 4), "type": ftype})

                    if cancel_after == "ack" and t_ack is not None:
                        outcome = "cancelled"
                        break
                    if cancel_after == "first_delta" and t_first_delta is not None:
                        outcome = "cancelled"
                        break
            except asyncio.TimeoutError:
                outcome = "timeout"
                error_info = {"code": "client_timeout",
                              "message": f"no terminal frame within {LAYER_TIMEOUT_S[q['layer']]}s"}
                t_error = time.perf_counter() - t0
            except websockets.exceptions.ConnectionClosed as exc:
                if outcome != "cancelled":
                    outcome = "stream_closed"
                    error_info = {"code": f"connection_closed:{exc.code}" if exc.code else "connection_closed",
                                  "message": str(exc)[:200]}
                t_complete = t_complete or (time.perf_counter() - t0)
    except (OSError, websockets.exceptions.InvalidStatus, asyncio.TimeoutError) as exc:
        outcome = "connect_failed"
        error_info = {"code": type(exc).__name__, "message": str(exc)[:200]}
        t_complete = None

    total_s = time.perf_counter() - t_conn0
    if full_text and len(full_text) > len(response_text):
        response_text = full_text

    rec.update({
        "t_ack_s": round(t_ack, 4) if t_ack is not None else None,
        "t_first_delta_s": round(t_first_delta, 4) if t_first_delta is not None else None,
        "t_first_fulltext_s": round(t_first_fulltext, 4) if t_first_fulltext is not None else None,
        "t_first_stage_s": round(t_first_stage, 4) if t_first_stage is not None else None,
        "first_stage_name": first_stage_name,
        "stage_sequence": ">".join(stages_seq) if stages_seq else "",
        "t_first_useful_s": round(t_first_useful, 4) if t_first_useful is not None else None,
        "t_complete_s": round(t_complete, 4) if t_complete is not None else None,
        "t_error_s": round(t_error, 4) if t_error is not None else None,
        "t_usage_s": None,  # 由 frames 回填
        "ws_open_s": ws_open_s,
        "total_s": round(total_s, 4),
        "outcome": outcome,
        "delta_events": deltas,
        "status_events": status_events,
        "frame_count": frame_count,
        "usage_frame": usage_frame,
        "usage_frame_meta": usage_frame_meta,
        "error": error_info,
        "meta_frame": meta_frame,
        "chat_lane": observed_md.get("chat_lane", ""),
        "deterministic_lane_kind": observed_md.get("deterministic_lane_kind", ""),
        "first_touch_tier": observed_md.get("first_touch_tier", ""),
        "fast_first_touch": observed_md.get("fast_first_touch", ""),
        "is_cache_hit": bool((meta_frame or {}).get("is_cache_hit", False)),
        "session_id": observed_md.get("session_id", ""),
        "response_chars": len(response_text),
        "response_text": response_text[:8000],
        "frame_timeline": frames,
    })
    for f in frames:
        if f.get("type") == "usage":
            rec["t_usage_s"] = f["t"]
            break
    return rec


async def run_layers(layers: list[str], passes: int, tag: str, out_dir: Path,
                     cancel_probe: bool = False, per_layer: int = 0) -> None:
    token, user_id = guest_auth()
    print(f"auth ok: user={user_id}")

    raw_path = out_dir / f"raw{('-' + tag) if tag else ''}.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    done_qids: set[str] = set()
    if raw_path.exists():
        with open(raw_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done_qids.add(json.loads(line)["qid"])
                except (json.JSONDecodeError, KeyError):
                    continue

    if cancel_probe:
        jobs = []
        for layer in layers:
            base = [q for q in E08.CORPUS if q["layer"] == layer]
            # 取该层首条实质/寒暄各一：ack 后取消 + 首 delta 后取消
            phatic = next((q for q in base if q["intent"] in PHATIC_INTENTS), base[0])
            subst = next((q for q in base if q["intent"] not in PHATIC_INTENTS), base[-1])
            for i, (q, ca) in enumerate([(phatic, "ack"), (subst, "first_delta")]):
                qq = dict(q)
                qq["qid"] = f"{layer}-CANCEL-{ca}-{i+1}"
                qq["run_tag"] = tag or "run"
                jobs.append((qq, ca))
    else:
        jobs = []
        for layer in layers:
            base = [dict(q) for q in E08.CORPUS if q["layer"] == layer]
            if per_layer:
                base = base[:per_layer]
            for p in range(1, passes + 1):
                for q in base:
                    qq = dict(q)
                    qq["qid"] = f"{layer}-r{p}-{q['qid'].split('-', 1)[1]}"
                    qq["run_tag"] = tag or "run"
                    jobs.append((qq, None))

    jobs = [(q, ca) for q, ca in jobs if q["qid"] not in done_qids]
    print(f"plan: {len(jobs)} queries across {layers} (resume skip {len(done_qids)})")

    session_id = ""
    session_turn = 0
    try:
        for idx, (q, ca) in enumerate(jobs):
            if session_turn >= SESSION_ROTATE_EVERY or not session_id:
                session_id = ""
                session_turn = 0
            session_turn += 1
            request_id = f"{REQ_PREFIX}-{tag or 'run'}-{q['qid'].lower().replace('+', '')}-{uuid.uuid4().hex[:6]}"
            rec = await sample_one(WS_URL, token, q, request_id, session_id,
                                   kind="cancel_probe" if ca else "corpus",
                                   cancel_after=ca)
            if rec.get("session_id"):
                session_id = rec["session_id"]
            with open(raw_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            print(f"[{idx + 1}/{len(jobs)}] {q['qid']} ack={rec['t_ack_s']} "
                  f"delta={rec['t_first_delta_s']} useful={rec['t_first_useful_s']} "
                  f"done={rec['t_complete_s']} out={rec['outcome']} err={bool(rec['error'])}")
            if rec["is_cache_hit"]:
                print(f"  !! CACHE_HIT on {q['qid']} — 记入 RED 检查", flush=True)
            await asyncio.sleep(INTER_QUERY_SLEEP_S)
    finally:
        enrich(raw_path)


def enrich(raw_path: Path) -> None:
    """批量回填 DB 归因（model/tier/tokens/engine_cost）。缺行保留 stream 侧数据。"""
    if not raw_path.exists():
        return
    recs = [json.loads(l) for l in raw_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    # 未归因（db_model 键缺失，或曾归因失败为 None 且流内有 usage 帧）都可重试——
    # 计费行可能因 worker 暂时故障滞后/进死信，恢复后重查。
    need = [r["request_id"] for r in recs
            if "db_model" not in r or (r.get("db_model") is None and r.get("usage_frame") is not None
                                       and r.get("db_total_tokens") is None)]
    db: dict[str, dict] = {}
    for i in range(0, len(need), 40):
        db.update(db_fetch_token_usage(need[i:i + 40]))
    for r in recs:
        row = db.get(r["request_id"])
        if row:
            r["db_model"] = row["model"]
            r["db_model_tier"] = row["model_tier"] or ""
            r["db_prompt_tokens"] = row["prompt_tokens"]
            r["db_completion_tokens"] = row["completion_tokens"]
            r["db_total_tokens"] = row["total_tokens"]
            r["engine_cost_usd_db"] = row["cost"]
        else:
            r.setdefault("db_model", None)
    with open(raw_path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"enrich done: {len(db)}/{len(need)} attributed")


# ---------------------------------------------------------------------------
# summarize：分位表（四时刻分开）、分母、成本三源、SLO 对照、计费完整性红项
# ---------------------------------------------------------------------------
def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vs = sorted(values)
    k = (len(vs) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(vs) - 1)
    return vs[lo] + (vs[hi] - vs[lo]) * (k - lo)


def _fmt(v, nd=3):
    return "-" if v is None else f"{v:.{nd}f}"


def cost_of(model_key: str | None, ptok: int, ctok: int) -> tuple[float | None, str]:
    table = E08.PRICE_TABLE_USD_PER_MTOK
    if model_key is None:
        return None, "unattributed"
    p = table.get(model_key)
    if not p:
        return None, "unpriced"
    if p.get("fallback_marker"):
        return 0.0, "no_generation_marker"
    return ptok / 1e6 * p["in"] + ctok / 1e6 * p["out"], p["model"]


def summarize(out_dir: Path, tag: str) -> None:
    raw_path = out_dir / f"raw{('-' + tag) if tag else ''}.jsonl"
    enrich(raw_path)  # 取消探针的 DB 计量可能滞后，汇总前补一轮归因
    recs = [json.loads(l) for l in raw_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    lines: list[str] = []
    lines.append(f"# V4-Q04 run summary — tag={tag or 'run'} raw={raw_path.name}")
    lines.append(f"generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    reds: list[str] = []
    cost_rollup: dict[str, dict] = {}
    for layer in LAYERS:
        rs = [r for r in recs if r["layer"] == layer]
        if not rs:
            continue
        n = len(rs)
        by_outcome: dict[str, int] = {}
        for r in rs:
            by_outcome[r["outcome"]] = by_outcome.get(r["outcome"], 0) + 1
        lines.append(f"## {layer}（分母 n={n}；失败/取消/超时不剔除，分位基于实际到达样本并单独列分母）")
        lines.append(f"outcome: {by_outcome}")
        moments = ["t_ack_s", "t_first_delta_s", "t_first_useful_s", "t_complete_s",
                   "t_first_stage_s", "t_first_fulltext_s"]
        header = "| 时刻 | n_reached | P50(s) | P90(s) | P99(s) | max(s) |"
        lines.append(header)
        lines.append("|---|---|---|---|---|---|")
        for m in moments:
            vals = [r[m] for r in rs if r.get(m) is not None]
            lines.append(f"| {m} | {len(vals)} | {_fmt(_pct(vals, 50), 3)} | {_fmt(_pct(vals, 90), 3)} "
                         f"| {_fmt(_pct(vals, 99), 3)} | {_fmt(max(vals), 3) if vals else '-'} |")
        delivered = [r for r in rs if r["outcome"] == "delivered"]
        lines.append(f"delivered={len(delivered)}  non_delivered={n - len(delivered)}")
        roll = cost_rollup.setdefault(layer, {"db_rows": 0, "db_tokens": 0, "db_cost": 0.0,
                                              "frame_only_rows": 0, "frame_tokens": 0,
                                              "frame_cost": 0.0, "unmetered": 0,
                                              "bench_priced_db_cost": 0.0})
        for r in rs:
            ptok = r.get("db_prompt_tokens")
            ctok = r.get("db_completion_tokens")
            model = r.get("db_model")
            tt = r.get("db_total_tokens")
            if tt is not None:
                roll["db_rows"] += 1
                roll["db_tokens"] += tt or 0
                roll["db_cost"] += r.get("engine_cost_usd_db") or 0.0
                c, _ = cost_of(model, ptok or 0, ctok or 0)
                if c:
                    roll["bench_priced_db_cost"] += c
            elif r.get("usage_frame") is not None:
                uf = r["usage_frame"]
                roll["frame_only_rows"] += 1
                roll["frame_tokens"] += uf.get("total_tokens") or 0
                roll["frame_cost"] += (uf.get("cost_micro_usd") or 0) / 1e6
                if r["outcome"] == "delivered":
                    reds.append(f"{layer}/{r['qid']}: billing_persistence_loss tokens={uf.get('total_tokens')} "
                                f"receipt_usd={(uf.get('cost_micro_usd') or 0)/1e6:.6f} but no token_usage row req={r['request_id']}")
            elif r["outcome"] == "delivered":
                roll["unmetered"] += 1
                reds.append(f"{layer}/{r['qid']}: fully_unmetered_delivered 无usage帧且无token_usage行 req={r['request_id']}")
            # 计费完整性红项检查（验收 2）
            if model in ("default", "no_generation_model") and (tt or 0) > 0:
                reds.append(f"{layer}/{r['qid']}: no_generation_with_tokens model={model} tokens={tt} req={r['request_id']}")
            if model == "no_generation_model_estimated" and (tt or 0) > 0:
                reds.append(f"{layer}/{r['qid']}: no_generation_estimated_with_tokens(I10检出桶) tokens={tt} req={r['request_id']}")
            if model is None and (tt or 0) > 0:
                reds.append(f"{layer}/{r['qid']}: unattributed_tokens tokens={tt} req={r['request_id']}")
            if model is not None and model not in E08.PRICE_TABLE_USD_PER_MTOK and (tt or 0) > 0 \
                    and model not in ("no_generation_model", "no_generation_model_estimated"):
                reds.append(f"{layer}/{r['qid']}: unpriced_model model={model} tokens={tt} req={r['request_id']}")
            if r.get("usage_frame") is None and (tt or 0) > 0 and r["outcome"] == "delivered":
                reds.append(f"{layer}/{r['qid']}: usage_frame_missing_but_db_tokens req={r['request_id']}")
            if r.get("is_cache_hit"):
                reds.append(f"{layer}/{r['qid']}: semantic_cache_hit_in_bench req={r['request_id']}")
        roll["total_cost_est"] = roll["db_cost"] + roll["frame_cost"]
        lines.append(f"cost: db_attributed={roll['db_rows']}行/{roll['db_tokens']}tok/${roll['db_cost']:.6f} | "
                     f"stream_frame_only={roll['frame_only_rows']}行/{roll['frame_tokens']}tok/${roll['frame_cost']:.6f} | "
                     f"fully_unmetered_delivered={roll['unmetered']}行 | "
                     f"合计(三源)≈${roll['total_cost_est']:.6f}")
        lines.append("")

    lines.append("## 成本三源口径")
    lines.append("- db_attributed：token_usage 行（引擎账，I10 单一核价权威；模型/tier 归因完整）")
    lines.append("- stream_frame_only：DB 行丢失（共享队列竞争消费者致死信后未恢复/丢失），")
    lines.append("  以流内 usage 帧（引擎回执 cost_micro_usd，同源权威）计量；模型归因缺失如实标注")
    lines.append("- fully_unmetered：无 usage 帧且无 DB 行——计费完整性红项（见下）")

    lines.append("")
    lines.append("## 计费完整性红项（验收 2：no_generation 带 token/漏辅助计费必须报红）")
    if reds:
        for x in reds:
            lines.append(f"- RED: {x}")
    else:
        lines.append("- 无（本 run 观测面内未发现 no_generation 带 token / 未归因 / usage 帧缺失）")
    lines.append("")
    lines.append("注：隐藏辅助调用（Layer3 意图分类/sufficiency/HyDE/router embedding）不在 token_usage")
    lines.append("计量范围——本表口径为「主生成计量成本」；辅助调用无计量即属漏计费面，")
    lines.append("以 token_usage 行数与 attempt 数的差异另报（见 run_manifest.attempt_reconciliation）。")

    out = out_dir / f"summary{('-' + tag) if tag else ''}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    roll_path = out_dir / f"cost_rollup{('-' + tag) if tag else ''}.json"
    roll_path.write_text(json.dumps({"generated": datetime.now(timezone.utc).isoformat(),
                                     "layers": cost_rollup, "red_count": len(reds),
                                     "reds": reds}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"summary -> {out}")
    print(f"cost_rollup -> {roll_path} (red_count={len(reds)})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "summarize"])
    ap.add_argument("--layers", default="L0,L1,L2,L3")
    ap.add_argument("--passes", type=int, default=4)
    ap.add_argument("--tag", default="")
    ap.add_argument("--cancel-probe", action="store_true")
    ap.add_argument("--per-layer", type=int, default=0, help="每层只取语料前 N 条（pilot 用）")
    args = ap.parse_args()
    layers = [x.strip().upper() for x in args.layers.split(",") if x.strip()]
    out_dir = OUT_DIR
    if args.cmd == "run":
        asyncio.run(run_layers(layers, args.passes, args.tag, out_dir,
                               args.cancel_probe, args.per_layer))
    else:
        summarize(out_dir, args.tag)


if __name__ == "__main__":
    main()
