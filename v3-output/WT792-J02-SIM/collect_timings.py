#!/usr/bin/env python3
"""wt792: collect J02_SUMMARY lines from per-process logs into the runbook §4/§8
combined j02_timings.json + proposals.json (authoritative source = logs, since
each process overwrites the shared artifact files). Read-only over logs."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

evid = Path(sys.argv[1])
out = {"driver": "integration_test/j02_fastpath_journey_test.dart",
       "spec": "v3-output/WT784-J02PREP/runbook.md §3/§4/§8",
       "budget_ms": 180000,
       "collected_at": datetime.now(timezone.utc).isoformat(),
       "note": "combined from per-process logs' J02_SUMMARY lines by wt792 collect_timings.py",
       "processes": [], "passes": [], "proposals": {}}
for log in sorted(evid.glob("logs/run_macos*.log")):
    text = log.read_text(errors="replace")
    m = re.search(r"^J02_SUMMARY (.*)$", text, re.M)
    if not m:
        continue
    try:
        d = json.loads(m.group(1))
    except json.JSONDecodeError:
        continue
    proc = {"log": log.name, "pass_param": d.get("pass_param"),
            "legs": d.get("legs"), "harness_t0": d.get("harness_t0"),
            "finished_at": d.get("finished_at"),
            "failures": d.get("failures"),
            "guest_username": (d.get("guest_leg") or {}).get("guest_username"),
            "upgraded_username": (d.get("upgrade_leg") or {}).get("upgraded_username")}
    out["processes"].append(proc)
    for p in d.get("passes", []):
        p = dict(p)
        p["source_log"] = log.name
        out["passes"].append(p)
    for k, v in (d.get("proposals") or {}).items():
        out["proposals"][k] = v
(evid / "j02_timings.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
props = out["proposals"]
(evid / "proposals.json").write_text(json.dumps({
    "proposals": props,
    "pairwise_distinct_in_process": None,
    "pairwise_note": "cross-process comparison by executor; proposals only exist for passes whose R8 ran (V3-FIX-539 miss otherwise)",
    "texts": props,
}, ensure_ascii=False, indent=2))
print(f"processes={len(out['processes'])} passes={len(out['passes'])} proposals={list(props)}")
for p in out["passes"]:
    print(p["persona"]["id"], p["source_log"],
          "action_ready=", p.get("t_action_ready_ms"),
          "budget_ok=", p.get("within_3min_budget"),
          "bounce=", p.get("register_ui_bounce"))
