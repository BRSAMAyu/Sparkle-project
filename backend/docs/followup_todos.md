# Follow-up TODOs

- Harden Redis bandit state for concurrency (HINCRBY vs JSON blob)
  - Acceptance criteria:
    - atomic updates under concurrent requests
    - no lost updates
    - backward compatible migration from existing state format
