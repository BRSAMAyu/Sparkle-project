# Rule AU - Mobile Parity

Rule AU governs Stage 35 parity between `UserStateV1` and mobile consumption.

## Contract

Each `UserStateV1` field must resolve to exactly one of:

1. `rendered`
   Mobile owns a Dart model field and at least one widget/screen consumption path.
2. `backend-only`
   Mobile keeps the field in its Dart model, but the field is explicitly marked with `// @BackendOnly: <reason>`.
3. `declared`
   The field is registered in `docs/aurora/stage35_backend_only_fields.md` under `Declared Exceptions`.

Fields that are neither `backend-only` nor `declared` are part of the Rule AU denominator.

## Formula

- Numerator: fields in the denominator that do not have a widget consumption path.
- Denominator: `total - declared - backend-only`
- Threshold: `numerator / denominator <= 10%`

## Source Of Truth

- Backend schema: `backend/app/state_aggregator/schema.py`
- Mobile model annotations: `mobile/lib/core/models/user_state_models.dart`
- Declared exceptions: `docs/aurora/stage35_backend_only_fields.md`
- Exception log: `docs/aurora/rule_au_exceptions.md`
- Guard: `scripts/guards/check_rule_au_mobile_parity.py`

## Stage 35 Notes

- The six low-value fields mandated by Stage 35 are tracked as `backend-only`.
- `social_signals_summary` and reserved `emotion_hint` stay `declared` until a dedicated mobile surface exists.
- Existing non-profile surfaces may satisfy `rendered` when they already own the user-facing widget contract.
