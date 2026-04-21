"""Observability dashboard: generates HTML report from RL episode data.

Produces a self-contained HTML file with charts and tables showing:
- Reward trajectory over iterations
- Policy stage progression
- Parameter change history
- Diversity metrics
- Holdout vs training performance
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def generate_dashboard(
    episode_history: list[dict[str, Any]],
    *,
    title: str = "SGW RL Episode Report",
    output_path: Path | None = None,
) -> str:
    """Generate an HTML dashboard from episode iteration history.

    Args:
        episode_history: list of iteration records from MetaLoopCoordinator
        title: report title
        output_path: if provided, write HTML to this file

    Returns:
        HTML string
    """
    reward_data = _extract_reward_data(episode_history)
    param_data = _extract_param_data(episode_history)
    summary = _compute_summary(episode_history)

    html_content = _TEMPLATE.format(
        title=html.escape(title),
        reward_json=json.dumps(reward_data),
        param_json=json.dumps(param_data),
        summary_json=json.dumps(summary),
        summary_table=_build_summary_table(summary),
        iteration_table=_build_iteration_table(episode_history),
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

    return html_content


def _extract_reward_data(history: list[dict[str, Any]]) -> dict[str, Any]:
    iterations = []
    raw_rewards = []
    norm_rewards = []
    outcomes = []
    for h in history:
        iterations.append(h.get("iteration", 0))
        raw_rewards.append(h.get("reward_raw", 0))
        norm_rewards.append(h.get("reward_normalized", 0))
        outcomes.append(h.get("outcome", "pending"))
    return {
        "iterations": iterations,
        "raw_rewards": raw_rewards,
        "norm_rewards": norm_rewards,
        "outcomes": outcomes,
    }


def _extract_param_data(history: list[dict[str, Any]]) -> dict[str, Any]:
    params: dict[str, list] = {}
    for h in history:
        action = h.get("action", {})
        changes = action.get("changes", {})
        for param, value in changes.items():
            if param not in params:
                params[param] = []
            params[param].append({
                "iteration": h.get("iteration", 0),
                "value": value,
            })
    return params


def _compute_summary(history: list[dict[str, Any]]) -> dict[str, Any]:
    if not history:
        return {"total_iterations": 0, "total_reward": 0}

    total_reward = sum(h.get("reward_normalized", 0) for h in history)
    outcomes = [h.get("outcome", "pending") for h in history]
    improved = sum(1 for o in outcomes if o.startswith("improved"))
    regressed = sum(1 for o in outcomes if o.startswith("regressed"))
    neutral = sum(1 for o in outcomes if o == "neutral")

    return {
        "total_iterations": len(history),
        "total_reward": round(total_reward, 4),
        "improved_count": improved,
        "regressed_count": regressed,
        "neutral_count": neutral,
        "improvement_rate": round(improved / max(len(outcomes), 1), 4),
    }


def _build_summary_table(summary: dict[str, Any]) -> str:
    rows = ""
    for key, value in summary.items():
        rows += f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(value))}</td></tr>"
    return f"<table class='table'>{rows}</table>"


def _build_iteration_table(history: list[dict[str, Any]]) -> str:
    if not history:
        return "<p>No iterations recorded</p>"

    rows = ""
    for h in history:
        outcome = h.get("outcome", "pending")
        outcome_class = f"outcome-{outcome.replace('_', '-')}"
        action_changes = h.get("action", {}).get("changes", {})
        changes_str = ", ".join(f"{k}={v}" for k, v in action_changes.items()) or "none"

        rows += (
            f"<tr>"
            f"<td>{h.get('iteration', '?')}</td>"
            f"<td class='{outcome_class}'>{outcome}</td>"
            f"<td>{h.get('reward_normalized', 0):.3f}</td>"
            f"<td>{html.escape(changes_str)}</td>"
            f"<td>{'Yes' if h.get('veto') else 'No'}</td>"
            f"</tr>"
        )

    return (
        f"<table class='table'><tr>"
        f"<th>Iteration</th><th>Outcome</th><th>Reward</th>"
        f"<th>Changes</th><th>Veto</th></tr>"
        f"{rows}</table>"
    )


_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; background: #1a1a2e; color: #eee; }}
h1 {{ color: #e94560; }}
h2 {{ color: #0f3460; background: #16213e; padding: 0.5rem 1rem; border-radius: 4px; }}
.table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
.table td, .table th {{ border: 1px solid #333; padding: 0.5rem; text-align: left; }}
.table th {{ background: #16213e; }}
.outcome-improved-sig {{ color: #4caf50; font-weight: bold; }}
.outcome-regressed-sig {{ color: #f44336; font-weight: bold; }}
.outcome-neutral {{ color: #ff9800; }}
canvas {{ max-width: 100%; }}
</style>
</head>
<body>
<h1>{title}</h1>

<h2>Summary</h2>
{summary_table}

<h2>Reward Trajectory</h2>
<canvas id="rewardChart" height="300"></canvas>

<h2>Iteration Details</h2>
{iteration_table}

<script>
const rewardData = {reward_json};
const paramData = {param_json};
const summary = {summary_json};

// Simple text-based chart (no external dependencies)
const canvas = document.getElementById('rewardChart');
if (canvas.getContext && rewardData.iterations.length > 0) {{
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = 300;
    const pad = 40;
    const rewards = rewardData.norm_rewards;
    const maxR = Math.max(...rewards.map(Math.abs), 0.5);
    const xScale = (W - 2*pad) / Math.max(rewards.length - 1, 1);
    const yScale = (H - 2*pad) / (2 * maxR);

    // Background
    ctx.fillStyle = '#16213e';
    ctx.fillRect(0, 0, W, H);

    // Zero line
    ctx.strokeStyle = '#555';
    ctx.beginPath();
    ctx.moveTo(pad, H/2);
    ctx.lineTo(W-pad, H/2);
    ctx.stroke();

    // Reward line
    ctx.strokeStyle = '#4caf50';
    ctx.lineWidth = 2;
    ctx.beginPath();
    rewards.forEach((r, i) => {{
        const x = pad + i * xScale;
        const y = H/2 - r * yScale;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }});
    ctx.stroke();

    // Points
    rewards.forEach((r, i) => {{
        const x = pad + i * xScale;
        const y = H/2 - r * yScale;
        const outcome = rewardData.outcomes[i] || '';
        ctx.fillStyle = outcome.includes('improved') ? '#4caf50' :
                        outcome.includes('regressed') ? '#f44336' : '#ff9800';
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
    }});
}}
</script>
</body>
</html>"""
