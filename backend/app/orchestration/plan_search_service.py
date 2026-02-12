from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.orchestration.schemas import ExecutablePlan


PlanGenerator = Callable[[ExecutablePlan, int, int], Awaitable[ExecutablePlan | None]]
PlanScorer = Callable[[ExecutablePlan], Awaitable[float]]


@dataclass
class PlanSearchResult:
    best_plan: ExecutablePlan
    best_score: float
    search_budget_used_ms: int
    plan_revision_count: int
    candidate_count: int = 0
    winning_margin: float = 0.0
    explored_candidates: list[dict[str, Any]] = field(default_factory=list)


class PlanSearchService:
    """Budgeted beam-like search for plan deliberation."""

    async def search(
        self,
        *,
        base_plan: ExecutablePlan,
        generate_candidate: PlanGenerator,
        score_plan: PlanScorer,
        beam_width: int = 3,
        max_depth: int = 4,
        time_budget_ms: int = 1200,
    ) -> PlanSearchResult:
        beam = max(1, int(beam_width))
        depth_limit = max(1, int(max_depth))
        budget_ms = max(50, int(time_budget_ms))

        start = time.perf_counter()
        elapsed_ms = lambda: int((time.perf_counter() - start) * 1000)

        base_score = float(await score_plan(base_plan))
        best_plan = base_plan
        best_score = base_score
        revisions = 0
        explored: list[dict[str, Any]] = [
            {
                "plan_id": str(base_plan.plan_id),
                "depth": 0,
                "score": round(base_score, 4),
                "source": "base",
            }
        ]
        ranked_candidates: list[tuple[float, ExecutablePlan]] = [(base_score, base_plan)]

        frontier: list[tuple[float, ExecutablePlan]] = [(base_score, base_plan)]
        for depth in range(1, depth_limit + 1):
            if elapsed_ms() >= budget_ms:
                break
            top_frontier = sorted(frontier, key=lambda item: item[0], reverse=True)[:beam]
            next_frontier: list[tuple[float, ExecutablePlan]] = []

            for branch_index, (_, seed_plan) in enumerate(top_frontier):
                if elapsed_ms() >= budget_ms:
                    break
                candidate = await generate_candidate(seed_plan, depth, branch_index)
                if candidate is None:
                    continue
                revisions += 1
                score = float(await score_plan(candidate))
                explored.append(
                    {
                        "plan_id": str(candidate.plan_id),
                        "depth": depth,
                        "score": round(score, 4),
                        "source": "search",
                    }
                )
                next_frontier.append((score, candidate))
                ranked_candidates.append((score, candidate))
                if score > best_score:
                    best_score = score
                    best_plan = candidate
                if len(next_frontier) >= beam:
                    break

            if not next_frontier:
                break
            frontier = next_frontier

        ranked = sorted(
            ranked_candidates,
            key=lambda item: (item[0], float(item[1].confidence or 0.0)),
            reverse=True,
        )
        if ranked:
            best_score, best_plan = ranked[0]
        winning_margin = 0.0
        if len(ranked) >= 2:
            winning_margin = max(0.0, float(ranked[0][0]) - float(ranked[1][0]))

        return PlanSearchResult(
            best_plan=best_plan,
            best_score=round(best_score, 4),
            search_budget_used_ms=elapsed_ms(),
            plan_revision_count=revisions,
            candidate_count=len(explored),
            winning_margin=round(winning_margin, 4),
            explored_candidates=explored[:100],
        )
