"""LLM-powered pattern mining: discovers non-obvious failure patterns from run data.

Uses a structured prompt to ask an LLM to identify patterns in failure clusters
that rule-based diagnostics might miss.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MinedPattern:
    """A pattern discovered by LLM analysis."""
    pattern_id: str
    description: str
    category: str                # "compliance" | "authenticity" | "interaction" | "persona"
    confidence: float            # 0-1, LLM's self-rated confidence
    affected_parameters: list[str]
    suggested_experiment: str
    evidence: list[str]
    raw_response: str = ""


# Prompt template for pattern mining
_PATTERN_MINING_PROMPT = """你是一个 SGW（Simulated Gray Window）数据分析专家。

以下是最近运行的失败数据摘要。请从中识别出非显而易见的模式。

## 失败数据

{failure_data}

## 任务

请识别 1-3 个非显而易见的模式。每个模式必须包含：
1. 描述：什么条件下出现失败
2. 类别：compliance | authenticity | interaction | persona
3. 置信度：0.0-1.0
4. 受影响的参数
5. 建议的实验
6. 证据

请严格输出以下 JSON 格式，不要输出其他内容：
```json
{{
  "patterns": [
    {{
      "description": "...",
      "category": "...",
      "confidence": 0.0,
      "affected_parameters": ["..."],
      "suggested_experiment": "...",
      "evidence": ["..."]
    }}
  ]
}}
```"""


class PatternMiner:
    """Discovers failure patterns using LLM analysis of run data.

    Falls back to statistical pattern detection if LLM is unavailable.
    """

    def __init__(
        self,
        *,
        llm_call_fn: Any = None,  # Callable[[str], str] — takes prompt, returns response
        min_failures: int = 5,
    ):
        self.llm_call_fn = llm_call_fn
        self.min_failures = min_failures

    def mine_patterns(
        self,
        failures: list[dict[str, Any]],
    ) -> list[MinedPattern]:
        """Mine patterns from failure data.

        Args:
            failures: list of failure records, each containing at least:
                      'category', 'description', 'evidence', 'persona_id', 'behavior_class'

        Returns:
            List of MinedPattern objects.
        """
        if len(failures) < self.min_failures:
            return self._statistical_patterns(failures)

        # Try LLM mining first
        if self.llm_call_fn is not None:
            try:
                return self._llm_mine(failures)
            except Exception:  # noqa: BLE001
                pass  # Fall back to statistical

        return self._statistical_patterns(failures)

    def _llm_mine(self, failures: list[dict[str, Any]]) -> list[MinedPattern]:
        """Use LLM to discover patterns."""
        # Format failure data for prompt
        failure_summary = []
        for f in failures[:50]:  # Cap at 50 to avoid token limits
            failure_summary.append({
                "category": f.get("category", "unknown"),
                "description": f.get("description", ""),
                "persona": f.get("persona_id", "unknown")[:16],
                "behavior": f.get("behavior_class", "unknown"),
            })

        prompt = _PATTERN_MINING_PROMPT.format(
            failure_data=json.dumps(failure_summary, ensure_ascii=False, indent=2)
        )

        response = self.llm_call_fn(prompt)

        # Parse response
        return self._parse_llm_response(response)

    def _parse_llm_response(self, response: str) -> list[MinedPattern]:
        """Parse LLM JSON response into MinedPattern objects."""
        patterns: list[MinedPattern] = []

        # Extract JSON from response (may have markdown wrapping)
        text = response.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return patterns

        for i, p in enumerate(data.get("patterns", [])):
            patterns.append(MinedPattern(
                pattern_id=f"mp_llm_{i:03d}",
                description=p.get("description", ""),
                category=p.get("category", "interaction"),
                confidence=float(p.get("confidence", 0.5)),
                affected_parameters=p.get("affected_parameters", []),
                suggested_experiment=p.get("suggested_experiment", ""),
                evidence=p.get("evidence", []),
                raw_response=response,
            ))

        return patterns

    def _statistical_patterns(self, failures: list[dict[str, Any]]) -> list[MinedPattern]:
        """Fallback: statistical pattern detection without LLM."""
        patterns: list[MinedPattern] = []

        # Pattern 1: Category co-occurrence
        category_counts: dict[str, int] = {}
        for f in failures:
            cat = f.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        for cat, count in category_counts.items():
            if count >= 3 and count / len(failures) > 0.3:
                patterns.append(MinedPattern(
                    pattern_id=f"mp_stat_{cat}",
                    description=f"Category '{cat}' accounts for {count}/{len(failures)} ({count/len(failures):.0%}) of failures",
                    category=cat,
                    confidence=0.6,
                    affected_parameters=[],
                    suggested_experiment=f"Investigate root cause of {cat} failures",
                    evidence=[f"count={count}/{len(failures)}"],
                ))

        # Pattern 2: Persona-behavior interaction
        cell_counts: dict[str, int] = {}
        for f in failures:
            key = f"{f.get('persona_id', '?')[:8]}_{f.get('behavior_class', '?')}"
            cell_counts[key] = cell_counts.get(key, 0) + 1

        for key, count in cell_counts.items():
            if count >= 3:
                patterns.append(MinedPattern(
                    pattern_id=f"mp_stat_cell_{key}",
                    description=f"Cell {key} has {count} failures (concentration)",
                    category="attribution",
                    confidence=0.5,
                    affected_parameters=["persona_prompt_template", "state_machine_transitions"],
                    suggested_experiment=f"A/B test: modify state machine for {key} cells",
                    evidence=[f"cell={key}, count={count}"],
                ))

        return patterns
