# Aurora Experience Goldens

This suite protects Aurora's user-facing copy from silent regression without calling a real LLM.

Run:

```bash
cd backend
pytest tests/golden -v
```

Update baselines after an intentional wording or tone change:

```bash
cd backend
pytest tests/golden --update-goldens -v
```

The checks cover:

- Snapshot drift for deterministic Aurora experience scenarios.
- Banned expression and internal token leaks.
- Same-family template repetition across three or more variants.
- Coverage minimums for daily startup, checkpoint return, Core Session opening, memory reference, task-stuck intervention, push copy, and correction replies.
