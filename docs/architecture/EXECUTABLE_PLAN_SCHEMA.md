# ExecutablePlan Schema (v1)

## Purpose
Define the minimum executable contract between LangGraph (planner) and the self-built execution system. All execution paths (Fast/LangGraph) must produce this structure and pass validation.

## JSON Schema (Conceptual)
```json
{
  "schema_version": "1.0",
  "plan_id": "string",
  "context_version": "string",
  "source": "langgraph|fast_path",
  "confidence": 0.0,
  "rationale": "string",
  "risk_flags": ["string"],
  "tool_calls": [
    {
      "id": "string",
      "name": "string",
      "params": {},
      "timeout_ms": 10000,
      "priority": "high|normal|low",
      "allow_retry": true,
      "max_retries": 2,
      "point_of_no_return": false,
      "compensation_call": {
        "name": "string",
        "params": {}
      }
    }
  ],
  "fallback_strategy": {
    "on_validation_fail": "replan|hitl|abort",
    "on_execution_fail": "retry|compensate|skip|abort"
  },
  "success_criteria": {
    "metrics": [
      {"name": "string", "threshold": 0.0}
    ]
  }
}
```

## Field Notes
- `context_version`: must match snapshot version used by planner; mismatch triggers replan or discard.
- `tool_calls.compensation_call`: required for reversible operations; if absent, set `point_of_no_return=true`.
- `point_of_no_return`: forces double-confirm or HITL before execution.
- `priority`: required for execution pool scheduling.

## Validation Requirements
- schema_version must be known.
- tool_calls must be non-empty.
- params must be JSON-serializable.
- if `point_of_no_return=true`, validation must enforce confirmation rules.

## Versioning
- v1 is minimal; future versions must be backward compatible or supported via adapters.
