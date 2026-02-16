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
        candidates_per_branch: int = 2,
    ) -> PlanSearchResult:
        beam = max(1, int(beam_width))
        depth_limit = max(1, int(max_depth))
        budget_ms = max(50, int(time_budget_ms))
        branch_width = max(1, min(int(candidates_per_branch), 4))

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
            depth_plans: list[ExecutablePlan] = []

            for branch_index, (_, seed_plan) in enumerate(top_frontier):
                if elapsed_ms() >= budget_ms:
                    break
                for variant_index in range(branch_width):
                    if elapsed_ms() >= budget_ms:
                        break
                    candidate_slot = branch_index * branch_width + variant_index
                    candidate = await generate_candidate(seed_plan, depth, candidate_slot)
                    if candidate is None:
                        continue
                    revisions += 1
                    raw_score = float(await score_plan(candidate))
                    diversity_penalty = self._diversity_penalty(
                        candidate=candidate,
                        compared=depth_plans,
                    )
                    adjusted_score = max(0.0, min(raw_score - diversity_penalty, 1.0))
                    explored.append(
                        {
                            "plan_id": str(candidate.plan_id),
                            "depth": depth,
                            "score": round(adjusted_score, 4),
                            "raw_score": round(raw_score, 4),
                            "diversity_penalty": round(diversity_penalty, 4),
                            "source": "search",
                        }
                    )
                    depth_plans.append(candidate)
                    next_frontier.append((adjusted_score, candidate))
                    ranked_candidates.append((adjusted_score, candidate))
                    if adjusted_score > best_score:
                        best_score = adjusted_score
                        best_plan = candidate

            if not next_frontier:
                break
            frontier = sorted(next_frontier, key=lambda item: item[0], reverse=True)[:beam]

        ranked = sorted(
            ranked_candidates,
            key=lambda item: (item[0], float(item[1].confidence or 0.0)),
            reverse=True,
        )
        ranked = self._pairwise_rerank(ranked)
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

    @staticmethod
    def _plan_signature(plan: ExecutablePlan) -> tuple[tuple[str, ...], tuple[str, ...]]:
        tools = tuple(sorted(str(tc.name or "") for tc in (plan.tool_calls or [])))
        agents = tuple(sorted(str(agent) for agent in (plan.agents_involved or []) if str(agent).strip()))
        return tools, agents

    def _diversity_penalty(
        self,
        *,
        candidate: ExecutablePlan,
        compared: list[ExecutablePlan],
    ) -> float:
        if not compared:
            return 0.0
        cand_tools, cand_agents = self._plan_signature(candidate)
        if not cand_tools and not cand_agents:
            return 0.0

        max_similarity = 0.0
        cand_tool_set = set(cand_tools)
        cand_agent_set = set(cand_agents)
        for item in compared[-6:]:
            tools, agents = self._plan_signature(item)
            tool_set = set(tools)
            agent_set = set(agents)
            tool_sim = self._jaccard(cand_tool_set, tool_set)
            agent_sim = self._jaccard(cand_agent_set, agent_set)
            similarity = 0.7 * tool_sim + 0.3 * agent_sim
            if similarity > max_similarity:
                max_similarity = similarity

        # Encourage candidate diversity but keep impact bounded.
        return max(0.0, min(0.08 * max_similarity, 0.08))

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 1.0
        if not left or not right:
            return 0.0
        inter = len(left.intersection(right))
        union = len(left.union(right))
        if union <= 0:
            return 0.0
        return inter / union

    def _pairwise_rerank(
        self,
        ranked: list[tuple[float, ExecutablePlan]],
    ) -> list[tuple[float, ExecutablePlan]]:
        if len(ranked) <= 1:
            return ranked
        items = list(ranked)
        for i in range(len(items) - 1):
            left = items[i]
            right = items[i + 1]
            if self._prefer(right, left):
                items[i], items[i + 1] = items[i + 1], items[i]
        return items

    @staticmethod
    def _prefer(
        challenger: tuple[float, ExecutablePlan],
        incumbent: tuple[float, ExecutablePlan],
    ) -> bool:
        challenger_score, challenger_plan = challenger
        incumbent_score, incumbent_plan = incumbent
        if challenger_score - incumbent_score > 0.03:
            return True
        if incumbent_score - challenger_score > 0.04:
            return False

        challenger_conf = float(challenger_plan.confidence or 0.0)
        incumbent_conf = float(incumbent_plan.confidence or 0.0)
        if challenger_conf - incumbent_conf > 0.08:
            return True
        if incumbent_conf - challenger_conf > 0.12:
            return False

        challenger_step_count = len(challenger_plan.tool_calls or [])
        incumbent_step_count = len(incumbent_plan.tool_calls or [])
        challenger_has_success = bool(challenger_plan.success_criteria)
        incumbent_has_success = bool(incumbent_plan.success_criteria)
        if challenger_has_success and not incumbent_has_success:
            return True
        if incumbent_has_success and not challenger_has_success:
            return False
        # Prefer simpler plans when scores are close.
        return challenger_step_count < incumbent_step_count
