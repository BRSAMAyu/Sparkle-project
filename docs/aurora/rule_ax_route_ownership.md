# Rule AX - Route Ownership

> Status: locked for Stage 37 finalization
> Scope: gateway route registration lines + Python API route decorators

## 1. One-Sentence Definition

Every new or changed route registration must carry an adjacent ownership comment:

`route-tier: public|authed|internal|deprecated`

## 2. Accepted Comment Forms

Go:

`// route-tier: internal`

Python:

`# route-tier: authed`

Single-line ignore:

`// rule-ax: ignore <reason>`

`# rule-ax: ignore <reason>`

## 3. Enforcement

CI enforcement is diff-only:

1. full-repo scan is used to record baseline debt
2. `scripts/guards/check_rule_ax_route_ownership.py` fails only on newly changed route lines without ownership comments
3. current baseline debt remains visible until gradually burned down

## 4. Baseline

- Baseline scan date: `2026-04-23`
- Baseline violation count: `1135`
- Baseline artifact: `docs/aurora/rule_ax_route_ownership_baseline.txt`

## 5. Entry Point

- `scripts/guards/check_rule_ax_route_ownership.py`
