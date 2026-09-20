"""M-09 Memory Longitudinal / Adversarial evaluation suite.

Evaluates the REAL merged memory chain (M-02 storage gate, M-03 retrieval
prefilter, M-04 conflict arbitration, M-05 use selfcheck, M-06 projector
boundary, M-07 correction/delete invalidation) on an isolated sqlite
database. The only simulated layer is the LLM extraction (which candidate a
chat turn would yield) plus the optional real-model answer probe — memory
behavior itself is never mocked.

Layout:
- ``memory_eval_schema.py``  frozen case JSON schema + loader + coverage matrix
- ``cases/``                10 persona case files (>=80 cases, 5 dimensions)
- ``harness.py``            real-chain timeline executor + probe + paired baseline
- ``grading.py``            marker grading (invalid use / overpersonalization /
                             valid-use precision / uplift)
- ``gate.py``               regression gate (per-case verdicts, thresholds,
                             mutation self-test)
- ``real_model.py``         5 key cases x 5 real model repeats (<=25 calls)
- ``runner.py``             CLI entry (deterministic, seeded)
- ``test_memory_eval_gate.py`` pytest gate assertions
"""
