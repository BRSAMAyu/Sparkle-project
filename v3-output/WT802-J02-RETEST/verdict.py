#!/usr/bin/env python3
"""wt802: J-02 retest verdict — per Leg-R pass stopwatch verdict from the
combined J02_SUMMARY lines (authoritative source = per-process logs).
Read-only over logs; writes verdict.json next to the run logs' parent dir."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

evid = Path(sys.argv[1])
budget = 180000
passes = []
for log in sorted((evid / "logs").glob("run_macos*.log")):
    text = log.read_text(errors="replace")
    m = re.search(r"^J02_SUMMARY (.*)$", text, re.M)
    if not m:
        continue
    d = json.loads(m.group(1))
    for p in d.get("passes", []):
        p = dict(p)
        p["source_log"] = log.name
        if "R" in d.get("legs", []):
            ready = p.get("t_action_ready_ms")
            p["verdict_within_budget"] = (
                isinstance(ready, int) and ready <= budget
            )
            p["verdict_first_action_card"] = p.get("t_action_ready_ms") is not None
            passes.append(p)
summary = {
    "budget_ms": budget,
    "collected_at": datetime.now(timezone.utc).isoformat(),
    "leg_r_runs": len(passes),
    "within_budget": sum(1 for p in passes if p.get("verdict_within_budget")),
    "passes": [
        {
            "persona": p["persona"]["id"],
            "log": p["source_log"],
            "t_action_ready_ms": p.get("t_action_ready_ms"),
            "within_3min_budget": p.get("verdict_within_budget"),
            "pure_ui_register": p.get("pure_ui_register", False),
            "register_ui_bounce": p.get("register_ui_bounce", False),
            "consent_inline_error_shown": p.get("consent_inline_error_shown"),
            "consent_inline_error_text": p.get("consent_inline_error_text"),
            "tile_checked_states_pre_submit": p.get("tile_checked_states_pre_submit"),
            "post_skip_route": p.get("post_skip_route"),
            "loading_feedback_observed": p.get("loading_feedback_observed"),
            "action_confirmed": p.get("action_confirmed"),
            "total_ms": p.get("total_ms"),
            "clicks": p.get("clicks"),
        }
        for p in passes
    ],
}
(evid / "verdict.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps({k: v for k, v in summary.items() if k != "passes"}, ensure_ascii=False))
for p in summary["passes"]:
    print(
        f"  {p['persona']:>4} ready={p['t_action_ready_ms']} in_budget={p['within_3min_budget']} "
        f"ui_register={p['pure_ui_register']} bounce={p['register_ui_bounce']} "
        f"inline={p.get('consent_inline_error_text')}"
    )
