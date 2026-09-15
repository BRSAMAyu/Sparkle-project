# Feedback Payload Schema (v1)

## Purpose
Define the feedback payload captured after each micro-task. Feedback is used for session adjustments (hot path) and offline analysis (cold path).

## JSON Schema (Conceptual)
```json
{
  "schema_version": "1.0",
  "event_id": "string",
  "task_id": "string",
  "user_id": "string",
  "session_id": "string",
  "context_version": "string",
  "timestamp": "ISO-8601",
  "feedback_type": "explicit|implicit",
  "rating": 1,
  "comment": "string",
  "completion": {
    "status": "completed|partial|failed|skipped",
    "duration_seconds": 0,
    "attempts": 1
  },
  "signals": {
    "clicked_next": false,
    "delayed": false,
    "abandoned": false
  },
  "predictive_hints": {
    "next_intent": "string",
    "energy_level": "low|medium|high"
  }
}
```

## Field Notes
- `rating` is optional; if missing, infer from behavior signals.
- `signals` should be collected passively where possible.
- `predictive_hints` are low-confidence hints and must not directly alter core logic.

## Hot/Cold Split
- Hot: session-level adjustments only.
- Cold: offline analysis and model updates.
