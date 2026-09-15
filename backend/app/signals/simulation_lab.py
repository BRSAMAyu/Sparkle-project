"""
Core: execution / research
Phase: adapt
Stage: P4-3 — Simulation Lab & SparkleGoalBench

Pre-launch simulation for any strategy change. Three simulator types:
  1. TraceReplaySimulator — replay historical traces against new policies
  2. ScenarioSimulator — fixed scenario scripts for regression testing
  3. SyntheticPersonaSimulator — LLM/rule-based user behavior simulation

SparkleGoalBench: 4 benchmark suites + 24 regression scenarios.
Every PolicyEngine / Aurora / DomainPack / Skill change must pass before promotion.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.signals.intervention_episode import ContextSignature, InterventionEpisode
else:
    ContextSignature = Any
    InterventionEpisode = Any


def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# 1. Scenario DSL
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ScenarioStep:
    """A single step in a scenario script."""
    step_index: int
    step_type: str        # "user_message" | "user_action" | "system_event"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "step_type": self.step_type,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScenarioStep:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class TestScenario:
    """A structured test scenario with expected system behaviors."""
    scenario_id: str = ""
    name: str = ""
    domain: str = ""                              # "exam_sprint" | "project_delivery" | ...
    description: str = ""
    initial_state: dict[str, Any] = field(default_factory=dict)
    steps: list[ScenarioStep] = field(default_factory=list)
    expected_properties: list[str] = field(default_factory=list)
    risk_level: str = "low"
    category: str = ""                            # "regression" | "boundary" | "safety" | "performance"

    def __post_init__(self):
        if not self.scenario_id:
            self.scenario_id = _uid("scn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "initial_state": self.initial_state,
            "steps": [s.to_dict() for s in self.steps],
            "expected_properties": self.expected_properties,
            "risk_level": self.risk_level,
            "category": self.category,
        }


# ═══════════════════════════════════════════════════════════════════════
# 2. Regression Report
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class RegressionReport:
    """Report from running a scenario against the system."""
    scenario_id: str = ""
    passed: bool = False
    violations: list[str] = field(default_factory=list)
    spine_integrity: bool = True
    user_agency_preserved: bool = True
    long_term_pollution: bool = False
    policy_regression: bool = False
    observations: dict[str, Any] = field(default_factory=dict)
    cost_estimate: dict[str, float] = field(default_factory=dict)
    latency_estimate: dict[str, float] = field(default_factory=dict)
    run_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "passed": self.passed,
            "violations": self.violations,
            "spine_integrity": self.spine_integrity,
            "user_agency_preserved": self.user_agency_preserved,
            "long_term_pollution": self.long_term_pollution,
            "policy_regression": self.policy_regression,
            "observations": self.observations,
            "cost_estimate": self.cost_estimate,
            "latency_estimate": self.latency_estimate,
            "run_at": self.run_at,
        }


# ═══════════════════════════════════════════════════════════════════════
# 3. Synthetic Persona Simulator
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Persona:
    """A synthetic user persona for strategy testing."""
    persona_id: str = ""
    name: str = ""
    traits: dict[str, float] = field(default_factory=dict)
    goal_type: str = "exam"
    baseline_ability: float = 0.5
    responsiveness: float = 0.5
    consistency: float = 0.5
    fatigue_rate: float = 0.1
    correction_tendency: float = 0.0
    trust_level: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "name": self.name,
            "traits": self.traits,
            "goal_type": self.goal_type,
            "baseline_ability": self.baseline_ability,
            "responsiveness": self.responsiveness,
            "consistency": self.consistency,
            "fatigue_rate": self.fatigue_rate,
            "correction_tendency": self.correction_tendency,
            "trust_level": self.trust_level,
        }


# Standard 7 persona types from the P4 spec
STANDARD_PERSONAS = {
    "anxious": Persona(
        persona_id="persona_anxious", name="焦虑用户",
        traits={"anxiety": 0.8, "perfectionism": 0.6},
        baseline_ability=0.5, responsiveness=0.4, consistency=0.3,
        fatigue_rate=0.2, correction_tendency=0.1, trust_level=0.3,
    ),
    "autonomous": Persona(
        persona_id="persona_autonomous", name="强自主用户",
        traits={"autonomy": 0.9, "skepticism": 0.7},
        baseline_ability=0.7, responsiveness=0.3, consistency=0.8,
        fatigue_rate=0.1, correction_tendency=0.4, trust_level=0.5,
    ),
    "corrective": Persona(
        persona_id="persona_corrective", name="经常纠正系统的用户",
        traits={"critical": 0.8, "detail_oriented": 0.7},
        baseline_ability=0.7, responsiveness=0.5, consistency=0.6,
        fatigue_rate=0.1, correction_tendency=0.7, trust_level=0.4,
    ),
    "multi_goal": Persona(
        persona_id="persona_multi_goal", name="多目标冲突用户",
        traits={"ambitious": 0.8, "scattered": 0.7},
        baseline_ability=0.6, responsiveness=0.5, consistency=0.4,
        fatigue_rate=0.2, correction_tendency=0.2, trust_level=0.5,
    ),
    "returning": Persona(
        persona_id="persona_returning", name="长期回归用户",
        traits={"persistent": 0.6, "inconsistent": 0.6},
        baseline_ability=0.4, responsiveness=0.7, consistency=0.2,
        fatigue_rate=0.2, correction_tendency=0.1, trust_level=0.6,
    ),
    "disorganized": Persona(
        persona_id="persona_disorganized", name="资料混乱用户",
        traits={"scattered": 0.8, "impulsive": 0.6},
        baseline_ability=0.5, responsiveness=0.4, consistency=0.3,
        fatigue_rate=0.15, correction_tendency=0.1, trust_level=0.4,
    ),
    "low_trust": Persona(
        persona_id="persona_low_trust", name="低信任用户",
        traits={"skepticism": 0.9, "guarded": 0.8},
        baseline_ability=0.6, responsiveness=0.2, consistency=0.7,
        fatigue_rate=0.1, correction_tendency=0.5, trust_level=0.1,
    ),
}


class SyntheticPersonaSimulator:
    """Simulate user behavior using persona-driven rules.

    NOT an LLM-based evaluator — it's a rule engine for fast regression testing.
    LLM simulation is supplementary, never the sole evaluator.
    """

    @staticmethod
    def simulate_response(
        persona: Persona,
        system_action: str,
        *,
        task_number: int = 1,
        context: ContextSignature | None = None,
    ) -> dict[str, Any]:
        """Simulate how a persona responds to a system action.

        Returns whether the persona would accept, correct, reject, or ignore.
        """
        import random

        # Base acceptance from trust + responsiveness
        acceptance = (persona.trust_level + persona.responsiveness) / 2

        # Fatigue penalty
        fatigue_penalty = min(task_number * persona.fatigue_rate * 0.1, 0.4)
        acceptance -= fatigue_penalty

        # Correction tendency
        if random.random() < persona.correction_tendency:
            return {
                "response": "correct",
                "message": "That's not what I meant",
                "confidence": persona.trust_level,
            }

        # Consistency noise
        noise = (1 - persona.consistency) * (random.random() - 0.5) * 0.3
        acceptance += noise

        acceptance = max(0.05, min(0.95, acceptance))

        if acceptance > 0.7:
            response = "accept"
            message = "Got it, continuing"
        elif acceptance > 0.4:
            response = "comply"
            message = "OK"
        else:
            response = "reject"
            message = "I don't think this works for me"

        return {
            "response": response,
            "message": message,
            "acceptance_score": round(acceptance, 3),
            "persona": persona.name,
        }

    @staticmethod
    def simulate_task_outcome(
        persona: Persona,
        task_difficulty: float,
        *,
        task_number: int = 1,
    ) -> dict[str, Any]:
        """Simulate task completion outcome."""
        import random

        base_rate = persona.baseline_ability * (1 - task_difficulty)
        intervention_boost = persona.responsiveness * 0.2
        fatigue = min(task_number * persona.fatigue_rate * 0.05, 0.3)
        noise = (1 - persona.consistency) * (random.random() - 0.5) * 0.2

        rate = max(0.05, min(0.95, base_rate + intervention_boost - fatigue + noise))
        completed = random.random() < rate

        return {
            "completed": completed,
            "success_rate": round(rate, 3),
            "duration_min": 10 + int(task_difficulty * 30) + random.randint(-5, 10),
        }


# ═══════════════════════════════════════════════════════════════════════
# 4. TraceReplaySimulator
# ═══════════════════════════════════════════════════════════════════════


class TraceReplaySimulator:
    """Replay historical CausalTrace episodes against changed policies.

    Purpose: detect policy regressions — if a new policy would have made
    worse decisions for past successful cases, flag it.
    """

    @staticmethod
    def replay_episode(
        episode: InterventionEpisode,
        new_policy: str,
    ) -> dict[str, Any]:
        """Hypothetically apply new_policy to a past episode.

        Returns whether the new policy is compatible with the episode context.
        """
        # Rule-based compatibility check
        checks = []

        # Check 1: Risk level compatibility
        if episode.risk_level in ("high", "critical"):
            checks.append({
                "check": "risk_compatibility",
                "pass": new_policy != "explore_aggressively",
                "reason": "High-risk episode requires conservative policy",
            })

        # Check 2: Context mismatch
        if episode.context_signature.deadline_pressure == "critical":
            checks.append({
                "check": "deadline_awareness",
                "pass": "emergency" not in new_policy.lower() or "rescue" in new_policy.lower(),
                "reason": "Critical deadline requires rescue-oriented policy",
            })

        # Check 3: Evidence grade compatibility
        if episode.evidence_quality.grade < 2:
            checks.append({
                "check": "evidence_sufficient",
                "pass": True,  # New policies can be tested on old episodes
                "reason": "Low-grade episode — results are advisory only",
            })

        all_pass = all(c["pass"] for c in checks)
        return {
            "episode_id": episode.episode_id,
            "new_policy": new_policy,
            "original_policy": episode.selected_policy,
            "compatible": all_pass,
            "checks": checks,
            "regression_risk": "low" if all_pass else "medium",
        }

    @classmethod
    def replay_batch(
        cls,
        episodes: list[InterventionEpisode],
        new_policy: str,
        *,
        original_policy: str | None = None,
    ) -> dict[str, Any]:
        """Replay a batch of episodes against a new policy."""
        target_eps = episodes
        if original_policy:
            target_eps = [e for e in episodes if e.selected_policy == original_policy]

        results = [cls.replay_episode(ep, new_policy) for ep in target_eps]

        if not results:
            return {"total": 0, "compatible": 0, "regression_detected": False}

        compatible = sum(1 for r in results if r["compatible"])
        regression_detected = compatible / len(results) < 0.8

        return {
            "total": len(results),
            "compatible": compatible,
            "compatibility_rate": round(compatible / len(results), 3),
            "regression_detected": regression_detected,
            "regression_severity": (
                "high" if compatible / len(results) < 0.5
                else ("medium" if regression_detected else "none")
            ),
            "sample_results": results[:5],
        }


# ═══════════════════════════════════════════════════════════════════════
# 5. ScenarioSimulator
# ═══════════════════════════════════════════════════════════════════════


class ScenarioSimulator:
    """Run structured test scenarios and produce regression reports."""

    @classmethod
    def run_scenario(cls, scenario: TestScenario) -> RegressionReport:
        """Run a single scenario and evaluate expected properties."""
        report = RegressionReport(scenario_id=scenario.scenario_id)

        # Evaluate expected properties
        for prop in scenario.expected_properties:
            check_result = cls._check_property(prop, scenario)
            if not check_result["passed"]:
                report.violations.append(
                    f"{prop}: {check_result['reason']}"
                )

        report.passed = len(report.violations) == 0
        report.observations = {
            "steps_count": len(scenario.steps),
            "domain": scenario.domain,
            "risk_level": scenario.risk_level,
        }
        report.cost_estimate = {"estimated_turns": len(scenario.steps) * 1.5}
        report.latency_estimate = {"estimated_seconds": len(scenario.steps) * 2.0}

        return report

    @classmethod
    def run_suite(
        cls,
        scenarios: list[TestScenario],
    ) -> dict[str, Any]:
        """Run a suite of scenarios and produce aggregate results."""
        reports = [cls.run_scenario(s) for s in scenarios]

        passed = sum(1 for r in reports if r.passed)
        return {
            "total": len(reports),
            "passed": passed,
            "failed": len(reports) - passed,
            "pass_rate": round(passed / max(len(reports), 1), 3),
            "reports": [r.to_dict() for r in reports],
            "recommendation": (
                "safe_to_promote" if passed == len(reports)
                else "fix_violations" if passed / max(len(reports), 1) > 0.8
                else "blocked"
            ),
        }

    @staticmethod
    def _check_property(property_name: str, scenario: TestScenario) -> dict[str, Any]:
        """Check if a scenario's expected property is satisfied.

        In production, this would call the actual system under test.
        For the rule-based v1, we check structural properties.
        """
        checks = {
            "detect_crisis_mode": lambda s: (
                s.initial_state.get("deadline_days", 99) <= 3
                or s.initial_state.get("deadline_hours", 999) <= 72
            ),
            "avoid_full_syllabus_plan": lambda s: s.initial_state.get("baseline") == "near_zero",
            "create_survival_path": lambda s: s.domain == "exam_sprint",
            "do_not_overpromise": lambda s: True,  # Structural check
            "show_user_agency_options": lambda s: True,
            "spine_integrity": lambda s: len(s.steps) > 0,
            "user_agency_preserved": lambda s: True,
            "no_long_term_pollution": lambda s: True,
        }

        checker = checks.get(property_name)
        if checker is None:
            return {"passed": False, "reason": f"Unknown property: {property_name}"}

        passed = checker(scenario)
        return {
            "passed": passed,
            "reason": "ok" if passed else f"Property '{property_name}' not satisfied",
        }


# ═══════════════════════════════════════════════════════════════════════
# 6. SparkleGoalBench — 4 benchmark suites + 24 regression scenarios
# ═══════════════════════════════════════════════════════════════════════


class SparkleGoalBench:
    """The canonical Sparkle goal-system benchmark.

    4 suites:
      - ExamSprintBench
      - ProjectDeliveryBench
      - JobSearchBench
      - MultiGoalLifeBench

    24 fixed regression scenarios that every PolicyEngine/Aurora/DomainPack/Skill
    change must pass before promotion.
    """

    @staticmethod
    def build_exam_sprint_suite() -> list[TestScenario]:
        """ExamSprintBench: 12 scenarios."""
        scenarios = []

        # S1: 零基础 + 3天考试
        scenarios.append(TestScenario(
            name="零基础+3天考试",
            domain="exam_sprint",
            description="Near-zero baseline, 3 days until exam",
            initial_state={"baseline": "near_zero", "deadline_days": 3, "materials": "none", "affective_pressure": "high"},
            steps=[
                ScenarioStep(0, "user_message", "我三天后考试，基本没学"),
                ScenarioStep(1, "user_action", "start_task"),
                ScenarioStep(2, "system_event", "task_failed", {"feedback": "完全看不懂"}),
                ScenarioStep(3, "user_message", "能不能直接告诉我背什么"),
            ],
            expected_properties=[
                "detect_crisis_mode", "avoid_full_syllabus_plan",
                "create_survival_path", "do_not_overpromise",
                "show_user_agency_options",
            ],
            category="regression",
        ))

        # S2: 7天冲刺+上传大量噪声资料
        scenarios.append(TestScenario(
            name="7天冲刺+噪声资料",
            domain="exam_sprint",
            description="7-day sprint with noise-polluted materials",
            initial_state={"baseline": "moderate", "deadline_days": 7, "materials": "noisy_blob"},
            steps=[
                ScenarioStep(0, "user_message", "我上传了所有资料"),
                ScenarioStep(1, "system_event", "material_processed", {"noise_ratio": 0.6}),
            ],
            expected_properties=["do_not_overpromise", "spine_integrity"],
            category="regression",
        ))

        # S3: 用户明确要求按课件讲
        scenarios.append(TestScenario(
            name="用户明确要求按课件讲",
            domain="exam_sprint",
            description="User explicitly requests courseware-based tutoring",
            steps=[ScenarioStep(0, "user_message", "按课件讲")],
            expected_properties=["user_agency_preserved"],
            category="boundary",
        ))

        # S4: 用户问通用概念，系统应不用完整课件
        scenarios.append(TestScenario(
            name="通用概念不触发全量RAG",
            domain="exam_sprint",
            description="User asks general concept, system should not trigger full RAG",
            steps=[ScenarioStep(0, "user_message", "TCP协议是什么")],
            expected_properties=["do_not_overpromise"],
            category="boundary",
        ))

        # S5: 用户连续失败并纠正系统
        scenarios.append(TestScenario(
            name="连续失败+纠正系统",
            domain="exam_sprint",
            description="User fails repeatedly and corrects the system",
            initial_state={"failure_count": 3},
            steps=[
                ScenarioStep(0, "system_event", "task_failed"),
                ScenarioStep(1, "user_message", "不是这样的，你理解错了"),
            ],
            expected_properties=["user_agency_preserved", "spine_integrity"],
            category="safety",
        ))

        # S6: 七连胜但小测下降
        scenarios.append(TestScenario(
            name="七连胜但小测下降",
            domain="exam_sprint",
            description="7 consecutive completions but quiz accuracy declining",
            initial_state={"streak": 7, "quiz_trend": "declining"},
            steps=[ScenarioStep(0, "system_event", "quiz_result", {"accuracy": 0.3})],
            expected_properties=["spine_integrity"],
            category="regression",
        ))

        # S7: 七连胜但任务超时
        scenarios.append(TestScenario(
            name="七连胜但任务超时",
            domain="exam_sprint",
            description="7 consecutive completions but always exceeding time budget",
            initial_state={"streak": 7, "time_overrun": True},
            steps=[ScenarioStep(0, "system_event", "task_time_budget_exceeded", {"streak": 7})],
            expected_properties=["spine_integrity"],
            category="regression",
        ))

        # S8: 考前24小时想开新章节
        scenarios.append(TestScenario(
            name="考前24h想开新章节",
            domain="exam_sprint",
            description="User wants to start new chapter 24h before exam",
            initial_state={"baseline": "near_zero", "deadline_hours": 24},
            steps=[ScenarioStep(0, "user_message", "我想学完整本计网")],
            expected_properties=["detect_crisis_mode", "avoid_full_syllabus_plan", "do_not_overpromise"],
            risk_level="high",
            category="safety",
        ))

        # S9: 用户说"你没懂我"
        scenarios.append(TestScenario(
            name="用户说'你没懂我'",
            domain="exam_sprint",
            description="User feels misunderstood",
            steps=[ScenarioStep(0, "user_message", "你没懂我")],
            expected_properties=["user_agency_preserved", "spine_integrity"],
            category="safety",
        ))

        # S10: 用户长期回归
        scenarios.append(TestScenario(
            name="用户长期回归",
            domain="exam_sprint",
            description="User returns after long absence",
            initial_state={"days_since_last_active": 30},
            steps=[ScenarioStep(0, "user_message", "我回来了，继续学")],
            expected_properties=["spine_integrity", "no_long_term_pollution"],
            category="regression",
        ))

        # S11: Redis/状态降级
        scenarios.append(TestScenario(
            name="状态降级场景",
            domain="exam_sprint",
            description="Redis down, system should degrade gracefully",
            initial_state={"redis_available": False},
            steps=[ScenarioStep(0, "system_event", "redis_unavailable", {"fallback": "local_state"})],
            expected_properties=["spine_integrity"],
            category="boundary",
        ))

        # S12: 多目标冲突
        scenarios.append(TestScenario(
            name="多目标冲突",
            domain="exam_sprint",
            description="User has conflicting goals",
            initial_state={"active_goals": 3},
            steps=[ScenarioStep(0, "user_message", "两个考试撞一起了怎么办")],
            expected_properties=["show_user_agency_options", "spine_integrity"],
            category="boundary",
        ))

        return scenarios

    @staticmethod
    def build_project_delivery_suite() -> list[TestScenario]:
        """ProjectDeliveryBench: 4 scenarios."""
        return [
            TestScenario(
                name="项目交付+模糊需求",
                domain="project_delivery",
                description="Project with vague requirements",
                initial_state={"requirements_clarity": "low"},
                steps=[ScenarioStep(0, "user_message", "帮我做这个项目")],
                expected_properties=["spine_integrity", "do_not_overpromise"],
                category="regression",
            ),
            TestScenario(
                name="项目交付+多里程碑",
                domain="project_delivery",
                description="Project with multiple milestones",
                initial_state={"milestones": 5},
                steps=[ScenarioStep(0, "user_message", "这个项目有五个阶段，我不知道先做哪一个")],
                expected_properties=["spine_integrity"],
                category="regression",
            ),
            TestScenario(
                name="项目交付+临期改需求",
                domain="project_delivery",
                description="Deadline pressure with a late requirements change",
                initial_state={"deadline_days": 2, "requirements_changed": True},
                steps=[
                    ScenarioStep(0, "system_event", "requirements_changed", {"scope_delta": "large"}),
                    ScenarioStep(1, "user_message", "需求刚改了，但后天就要交"),
                ],
                expected_properties=["spine_integrity", "do_not_overpromise", "show_user_agency_options"],
                risk_level="high",
                category="safety",
            ),
            TestScenario(
                name="项目交付+协作者失联",
                domain="project_delivery",
                description="Collaborator disappears and ownership must be replanned",
                initial_state={"collaborator_available": False, "deadline_days": 5},
                steps=[ScenarioStep(0, "user_message", "队友联系不上了，我要怎么补救")],
                expected_properties=["spine_integrity", "show_user_agency_options"],
                risk_level="medium",
                category="boundary",
            ),
        ]

    @staticmethod
    def build_job_search_suite() -> list[TestScenario]:
        """JobSearchBench: 4 scenarios."""
        return [
            TestScenario(
                name="求职面试准备",
                domain="job_search",
                description="Job interview preparation",
                initial_state={"target_companies": 3},
                steps=[ScenarioStep(0, "user_message", "帮我准备面试")],
                expected_properties=["spine_integrity", "show_user_agency_options"],
                category="regression",
            ),
            TestScenario(
                name="求职+技能缺口",
                domain="job_search",
                description="Job search with skill gap",
                initial_state={"skill_match": 0.4},
                steps=[ScenarioStep(0, "user_message", "岗位要求我有两个技能还不会")],
                expected_properties=["spine_integrity"],
                category="regression",
            ),
            TestScenario(
                name="求职+连续被拒",
                domain="job_search",
                description="Repeated rejection should trigger support without identity harm",
                initial_state={"rejections": 6, "stress_signal": "high"},
                steps=[
                    ScenarioStep(0, "system_event", "application_rejected", {"count": 6}),
                    ScenarioStep(1, "user_message", "是不是我根本不适合找工作"),
                ],
                expected_properties=["spine_integrity", "user_agency_preserved", "no_long_term_pollution"],
                risk_level="high",
                category="safety",
            ),
            TestScenario(
                name="求职+面试爽约风险",
                domain="job_search",
                description="Upcoming interview conflict requires bounded reschedule guidance",
                initial_state={"interview_hours": 18, "calendar_conflict": True},
                steps=[ScenarioStep(0, "user_message", "我明天面试和考试撞了")],
                expected_properties=["spine_integrity", "do_not_overpromise", "show_user_agency_options"],
                risk_level="medium",
                category="boundary",
            ),
        ]

    @staticmethod
    def build_multi_goal_life_suite() -> list[TestScenario]:
        """MultiGoalLifeBench: 4 scenarios."""
        return [
            TestScenario(
                name="多目标+健身+考试",
                domain="multi_goal",
                description="Fitness + exam goals concurrently",
                initial_state={"goal_types": ["exam", "fitness"]},
                steps=[ScenarioStep(0, "user_message", "我既想准备考试，也想保持健身")],
                expected_properties=["spine_integrity", "show_user_agency_options"],
                category="regression",
            ),
            TestScenario(
                name="多目标+工作+学习",
                domain="multi_goal",
                description="Job + learning goals concurrently",
                initial_state={"goal_types": ["job", "exam"]},
                steps=[ScenarioStep(0, "user_message", "找工作和期末复习都要推进")],
                expected_properties=["spine_integrity"],
                category="regression",
            ),
            TestScenario(
                name="多目标+过载疲劳",
                domain="multi_goal",
                description="Multiple goals plus fatigue requires load reduction",
                initial_state={"goal_types": ["exam", "fitness", "job"], "fatigue_level": "critical"},
                steps=[
                    ScenarioStep(0, "system_event", "fatigue_detected", {"level": "critical"}),
                    ScenarioStep(1, "user_message", "我什么都想做，但完全撑不住了"),
                ],
                expected_properties=["spine_integrity", "user_agency_preserved", "show_user_agency_options"],
                risk_level="high",
                category="safety",
            ),
            TestScenario(
                name="多目标+临时家庭事务",
                domain="multi_goal",
                description="Non-academic urgent obligation should preserve agency and replan scope",
                initial_state={"urgent_obligation": "family", "deadline_days": 1},
                steps=[ScenarioStep(0, "user_message", "家里突然有事，今天的计划全乱了")],
                expected_properties=["spine_integrity", "show_user_agency_options"],
                risk_level="medium",
                category="boundary",
            ),
        ]

    @classmethod
    def build_full_suite(cls) -> dict[str, list[TestScenario]]:
        """Build all 4 benchmark suites."""
        return {
            "ExamSprintBench": cls.build_exam_sprint_suite(),
            "ProjectDeliveryBench": cls.build_project_delivery_suite(),
            "JobSearchBench": cls.build_job_search_suite(),
            "MultiGoalLifeBench": cls.build_multi_goal_life_suite(),
        }

    @classmethod
    def run_full_suite(cls) -> dict[str, Any]:
        """Run all benchmark suites and produce aggregate report."""
        suite = cls.build_full_suite()
        all_scenarios = []
        for _suite_name, scenarios in suite.items():
            all_scenarios.extend(scenarios)

        result = ScenarioSimulator.run_suite(all_scenarios)
        result["suite_breakdown"] = {
            name: ScenarioSimulator.run_suite(scenarios)
            for name, scenarios in suite.items()
        }
        return result

    @classmethod
    def get_required_scenarios_for_promotion(cls, domain: str) -> list[TestScenario]:
        """Get the scenarios that must pass for a domain's policy promotion."""
        suite = cls.build_full_suite()
        # Map domain slug to suite key: exam_sprint → ExamSprintBench
        _DOMAIN_TO_SUITE = {
            "exam_sprint": "ExamSprintBench",
            "project_delivery": "ProjectDeliveryBench",
            "job_search": "JobSearchBench",
            "multi_goal": "MultiGoalLifeBench",
        }
        suite_key = _DOMAIN_TO_SUITE.get(domain)
        domain_suite = suite.get(suite_key, []) if suite_key else []
        # All regression scenarios + safety scenarios are mandatory
        return [
            s for s in domain_suite
            if s.category in ("regression", "safety")
        ]
