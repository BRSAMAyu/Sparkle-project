# Stage 30 Scaffolding Combine Matrix

ScaffoldingFSM combines SRL and Metacognition non-additively.

| SRL delta | Metacognition delta | Final delta | Interpretation |
| --- | --- | --- | --- |
| `+1` | any | `+1` | SRL escalation dominates |
| `0` | `>= +0.5` | `+0.5` | Metacognition lightly increases support |
| `0` | `<= -0.5` | `-0.5` | Metacognition lightly reduces support |
| `-1` | any | `-1` | SRL reduction dominates |
| other | other | `0` | No change |

## Contract

- Never compute `support_level = SRL_delta + Metacog_delta`.
- ScaffoldingFSM reads `metacognition_profile` through the Aggregator only.
- ScaffoldingFSM must not import `MetacognitionService`.
- `fsm_combine` has an independent kill switch.
