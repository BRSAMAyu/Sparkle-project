# Rule AT — No Orphan Data / No Orphan Service

- Scope: `backend/app/services/**/*.py` and `backend/app/consumers/**/*.py`
- Requirement: every non-deprecated runtime file must be imported by at least one other non-test runtime file.
- Escape hatch: add `# rule-at: orphan-by-design <reason>` to the file and document the same file path in [rule_at_exceptions.md](./rule_at_exceptions.md).
- Guard: `scripts/guards/check_rule_at_no_orphan.py`
- Goal: prevent silent dead code accumulation after staged Aurora wiring work.
