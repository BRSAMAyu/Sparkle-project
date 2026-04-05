# SPARKLE_THREE_SYSTEM_IMPROVEMENT_PLAN_2026-04-05

This document defines the concrete improvement path for the three core systems of Sparkle, as identified in the 2026-04-05 product thesis. Our goal is to move from a "sophisticated architecture" to a "winning product" that provides undeniably better planning and understanding than raw AI models.

---

## 1. User Insight System (The Understanding Engine)
**Current State:** Passive aggregation. Sparkle waits for signals (chat, tasks) and maps them to semantic primitives.
**Strategic Gap:** It doesn't actively close understanding gaps required for superior planning.

### Improvements
| Feature | Description | Action |
| :--- | :--- | :--- |
| **Strategic Interrogator** | A runtime agent that detects when "Plan Readiness" is low and proactively asks the user for missing high-signal data. | Add `StrategicInterrogator` to `orchestration/sufficiency_checker.py`. |
| **User Readiness Score** | A metric derived from `CognitiveFragment` and `StudyRecord` that tells the Planning Engine if the user is actually ready for a specific goal (e.g., 14-day exam prep). | Implement in `services/profile_context_service.py`. |
| **Hidden Constraint Discovery** | A pipeline that looks for recurring failure patterns (e.g., "Always fails on weekends") and surfaces them as explicit planning constraints. | Extend `services/cognitive/behavior_pattern_service.py`. |

---

## 2. AI Planning System (The Plan Quality Engine)
**Current State:** Sophisticated Graph/Agent architecture, but prompts still rely largely on general LLM planning capabilities.
**Strategic Gap:** We haven't proven it's materially better than raw GPT-4/Claude-3 for non-expert users.

### Improvements
| Feature | Description | Action |
| :--- | :--- | :--- |
| **Growth-First Planning Logic** | Instead of generic task sequences, enforce a planning structure: [Weakness Focus] -> [High-Impact Recovery] -> [Adaptive Density]. | Implement in `orchestration/lang_graph_planner.py`. |
| **Benchmark Evaluator** | A tool that runs the same user data through Sparkle vs. a Raw LLM and scores the output based on "Plan Superiority" metrics. | Create `scripts/benchmark_planning_quality.py`. |
| **Subsystem Governance** | Move Body-Awareness from "Advice in Prompt" to "Runtime Routing". Let Sparkle choose specific tools/pipelines based on their proven reliability for the goal. | Upgrade `services/capability_registry_service.py`. |

---

## 3. Feedback Loop & Growth System (The Evolution Engine)
**Current State:** Reactive feedback on immediate answers; preference binding.
**Strategic Gap:** No long-term outcome validation. We don't know if the *plans* worked.

### Improvements
| Feature | Description | Action |
| :--- | :--- | :--- |
| **Plan Outcome Tracker** | A long-term feedback mechanism that checks if the goal (e.g., "Exam Pass") was reached and feeds the *logic failure* back into the system. | Create `services/plan_outcome_tracker_service.py`. |
| **Logic Evolution Engine** | Automatically tune the "Growth-First" planning weights based on what actually works for the specific user across sessions. | Implement in `services/feedback_learning_service.py`. |
| **Human-in-the-Loop Eval (HITL)** | Operationalize the thermodynamics protocol into a regular "Product Truth" cycle. | Standardize `scripts/review_human_eval_run.py`. |

---

## The 14-Day Benchmark Target
To prove these systems work, we will focus on the **14-Day Exam Prep** scenario as our primary proof point.

1. **Understanding:** Does Sparkle ask the right diagnostic questions (Mastery level, available hours, energy cycles) within the first 3 turns?
2. **Planning:** Is the resulting plan objectively more realistic and growth-focused than a raw LLM output?
3. **Growth:** If the user fails a task on Day 3, does Sparkle adapt Day 4-14 better than Day 1-3 did?

---

## Next Moves
1. Implement the **Strategic Interrogator** prototype.
2. Run the first **Planning Superiority Benchmark**.
3. Integrate **Plan Readiness** into the Situation Brief.
