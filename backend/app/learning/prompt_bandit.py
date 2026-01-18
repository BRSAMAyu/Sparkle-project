import json
import random
import time
from typing import Dict, List, Optional

from loguru import logger

from app.core.metrics import PROMPT_BANDIT_STATE_MISSING_TOTAL, PROMPT_BANDIT_UPDATES_TOTAL


class PromptBandit:
    def __init__(
        self,
        redis_client=None,
        ttl_seconds: int = 60 * 60 * 24 * 30,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.rng = rng or random.Random()

    def _key(self, workflow_id: str) -> str:
        return f"bandit:prompt:{workflow_id}"

    def _default_state(self, arms: List[str]) -> Dict:
        return {
            "version": 1,
            "updated_at": int(time.time()),
            "arms": {arm: {"alpha": 1.0, "beta": 1.0} for arm in arms},
        }

    async def _load_state(self, workflow_id: str, arms: List[str]) -> Dict:
        if not self.redis:
            PROMPT_BANDIT_STATE_MISSING_TOTAL.labels(workflow_id=workflow_id).inc()
            return self._default_state(arms)

        key = self._key(workflow_id)
        raw = await self.redis.get(key)
        if not raw:
            PROMPT_BANDIT_STATE_MISSING_TOTAL.labels(workflow_id=workflow_id).inc()
            state = self._default_state(arms)
            await self._save_state(key, state)
            return state

        try:
            state = json.loads(raw)
        except json.JSONDecodeError:
            PROMPT_BANDIT_STATE_MISSING_TOTAL.labels(workflow_id=workflow_id).inc()
            state = self._default_state(arms)
            await self._save_state(key, state)
            return state

        stored_arms = state.get("arms", {})
        updated = False
        for arm in arms:
            if arm not in stored_arms:
                stored_arms[arm] = {"alpha": 1.0, "beta": 1.0}
                updated = True
        state["arms"] = stored_arms
        if updated:
            await self._save_state(key, state)
        return state

    async def _save_state(self, key: str, state: Dict) -> None:
        if not self.redis:
            return
        state["updated_at"] = int(time.time())
        await self.redis.set(key, json.dumps(state), ex=self.ttl_seconds)

    async def select(self, workflow_id: str, arms: List[str]) -> str:
        state = await self._load_state(workflow_id, arms)
        best_arm = arms[0]
        best_sample = -1.0
        for arm in arms:
            params = state["arms"].get(arm, {"alpha": 1.0, "beta": 1.0})
            sample = self.rng.betavariate(params["alpha"], params["beta"])
            if sample > best_sample:
                best_sample = sample
                best_arm = arm
        return best_arm

    async def update(self, workflow_id: str, arm: str, reward: int) -> None:
        if reward not in (0, 1):
            logger.warning("PromptBandit received invalid reward=%s", reward)
            return
        state = await self._load_state(workflow_id, [arm])
        params = state["arms"].get(arm, {"alpha": 1.0, "beta": 1.0})
        if reward == 1:
            params["alpha"] += 1.0
        else:
            params["beta"] += 1.0
        state["arms"][arm] = params
        await self._save_state(self._key(workflow_id), state)
        PROMPT_BANDIT_UPDATES_TOTAL.labels(workflow_id=workflow_id).inc()

    @staticmethod
    def summarize_state(state: Dict) -> Dict[str, Dict[str, float]]:
        summary = {}
        for arm, params in state.get("arms", {}).items():
            alpha = float(params.get("alpha", 1.0))
            beta = float(params.get("beta", 1.0))
            mean = alpha / (alpha + beta)
            summary[arm] = {"alpha": alpha, "beta": beta, "mean": mean}
        return summary

    async def get_debug_state(self, workflow_id: str, arms: List[str], samples: int = 200) -> Dict:
        state = await self._load_state(workflow_id, arms)
        summary = self.summarize_state(state)

        counts = {arm: 0 for arm in arms}
        for _ in range(samples):
            choice = await self.select(workflow_id, arms)
            counts[choice] += 1

        probabilities = {arm: counts[arm] / samples for arm in arms}
        return {
            "workflow_id": workflow_id,
            "state": summary,
            "selection_probabilities": probabilities,
        }
