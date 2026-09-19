# Sparkle V3 Pack Contents

This package is the V3 **Agent-only execution source** for taking Sparkle from a technically solid V2.5 baseline to a product-quality commercial release candidate.

## Read first

1. `README_START_HERE.md` — operating contract
2. `NORTH_STAR.md` — product north star
3. `MASTER_DESIGN.md` — integrated product + system design
4. `V3_DEFINITION_OF_DONE.md` — objective completion gates
5. `06_agent_fleet/START_PROMPT.md` — hand this to the Fleet Leader
6. `07_tasks/TASK_INDEX.md` — all 107 V3-only tasks

## Directory map

- `00_context/` — frozen V3 decisions, baseline truth, module portfolio, entity map, differentiation thesis
- `01_product/` — target users, JTBD, first 3 minutes, Day 0–14 journey, product language, commercial model, demo path
- `02_core_systems/` — Aurora, user world model, Memory, conflict arbitration, Context Compiler, RAG, action engine, Human–AI allocation, Agent Runtime, proactive system, AI routing/latency, data flywheel
- `03_modules/` — desired product behavior for every major product surface and long-tail capability family
- `04_ux/` — design direction, interaction patterns, state completeness, visual QA, accessibility, cross-platform consistency, copy/tone
- `05_metrics_eval/` — metric tree, personalization evaluation, 260 scenarios, 20 Golden Journeys, 10 personas
- `06_agent_fleet/` — Leader/Worker/Reviewer/Simulator prompts, dynamic issue protocol, merge protocol, six-slot fleet operating model
- `07_tasks/` — machine-readable task graph + 107 full task cards
- `08_operations/` — deployment, observability, security/privacy, release gates, demo runbook
- `09_research/` — supplied source snapshots, current research synthesis, competitor matrix, source register
- `10_tools/` — pack validator, scheduler, fleet-state helper, reading-room builder
- `templates/` — completion and review receipts
- `tests/` — pack-level tests

## Execution principle

V3 does not repeat completed V2/V2.5 cards. If a V3 behavior is already present, an Agent may complete the task through **evidence-only verification**. If behavior differs from the V3 specification, repair only the demonstrated gap.

The six concurrent slots are dynamically assigned by dependency/lock/resource constraints. They are not six permanent job titles.
