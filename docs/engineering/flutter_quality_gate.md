# Flutter Quality Gate (M4)

Last updated: 2026-02-07

## Policy

- `ERROR` must be `0`
- `WARNING` must be `0`
- `INFO` is budgeted by allowlist and cannot increase during freeze.

## Files

- Gate script: `scripts/check_flutter_analyze_gate.py`
- Budget file: `quality/flutter_analyze_allowlist.json`
- Report output: `quality/flutter_analyze_report.json`

## Local commands

```bash
python3 scripts/check_flutter_analyze_gate.py \
  --project-dir mobile \
  --budget-file quality/flutter_analyze_allowlist.json \
  --write-report quality/flutter_analyze_report.json
```

## Budget refresh (intentional only)

```bash
cd mobile
dart analyze --format machine > /tmp/mobile_analyze_machine.txt
```

Then regenerate `quality/flutter_analyze_allowlist.json` in a dedicated quality-governance change, with rationale.
