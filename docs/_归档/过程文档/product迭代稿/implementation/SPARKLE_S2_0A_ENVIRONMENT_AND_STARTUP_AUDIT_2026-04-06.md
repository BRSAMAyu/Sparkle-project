# Sparkle S2-0A Environment and Startup Audit

> Date: 2026-04-06  
> Status: Completed on current branch state  
> Stage: `S2-0 Runnable Golden Path Bring-Up`  
> Pack: `S2-0A Environment and Startup Audit`

---

## 0. Purpose

This note records the first Stage 2 environment and startup audit required by:

- `docs/product/implementation/SPARKLE_STAGE2_PRODUCT_COHERENCE_EXECUTION_PLAN_2026-04-06.md`

Its job is not redesign.

Its job is to answer:

> **What is the real local full-stack path today, and does it actually start cleanly enough to inspect the real Sparkle product?**

---

## 1. Audited Startup Surface

The current bring-up path is centered on:

- `scripts/dev_local_stack.sh`
- `Makefile` health and preflight targets
- `backend/scripts/startup_check.py`
- `mobile/integration_test/app_test.dart`

### What `scripts/dev_local_stack.sh up` actually does

It is the real top-level startup command for Stage 2 bring-up on this machine.

It performs these steps:

1. starts Docker infra for PostgreSQL, Redis, and MinIO
2. waits for infra health
3. initializes Apache AGE graph/schema
4. initializes Redis search index `idx:knowledge`
5. starts Python gRPC service
6. starts FastAPI backend
7. builds and starts the Go gateway
8. starts summarization and billing workers

This means Stage 2 startup is already more opinionated than the older broad docs imply.

---

## 2. Real Full-Stack Golden Path

The audited full-stack path for S2-0 is:

- backend: FastAPI + Python gRPC + workers from `scripts/dev_local_stack.sh`
- gateway: local Go gateway on `http://localhost:8080`
- infra: PostgreSQL, Redis, MinIO via Docker Compose
- mobile: Flutter app in `mobile/`
- device target: iOS simulator `iPhone 16e` (`79461B43-C730-47C4-9994-10CA7C5546BD`)

This remains the strongest current Stage 2 device path because:

- the simulator is already available on this machine
- iOS simulator networking resolves `localhost` correctly here
- the repo already contains a real guest-entry integration test for the core shell

---

## 3. Commands Audited

The following commands were executed on 2026-04-06 as the S2-0A audit sequence:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
./scripts/dev_local_stack.sh up
./scripts/dev_local_stack.sh status
make local-config-check
cd backend && .venv/bin/python scripts/startup_check.py
./scripts/dev_local_stack.sh smoke
make smoke
make local-signoff-preflight
cd mobile && flutter devices
cd mobile && flutter test integration_test/app_test.dart -d 79461B43-C730-47C4-9994-10CA7C5546BD -r compact
```

---

## 4. Verified Results

### Environment and config

- required local config audit passed
- backend import/startup audit passed
- live env includes Xiaomi flash and pro configuration
- local iOS simulator target was available

### Infra and services

- PostgreSQL healthy
- Redis healthy
- MinIO running
- API healthy
- gateway healthy
- gateway CQRS health healthy
- summarization worker running
- billing worker running
- Alembic current revision at head
- Redis search index `idx:knowledge` present

### Mobile proof

- Flutter detected the booted `iPhone 16e` simulator
- iOS build completed
- `integration_test/app_test.dart` passed on rerun
- the guest user reached the dashboard and navigated core shell tabs

---

## 5. What This Pack Proves

S2-0A is complete enough to support the next Stage 2 packs because it proves:

1. there is one real top-level startup command
2. the service dependency graph is knowable and reproducible
3. the current machine can open the real product path on a real simulator target
4. startup failure modes are now concrete enough to document instead of hand-wave

---

## 6. Blockers and Non-Blocking Findings

### No current hard startup blocker on this machine

After the current branch fixes already in progress, the audited startup path is runnable.

### Non-blocking but important observations

1. `scripts/dev_local_stack.sh up` is not purely read-only.
   - It recreates the Redis knowledge index each run.
   - It rebuilds the tracked gateway binary at `backend/gateway/bin/gateway`.

2. The iOS proof was not fully clean on the first attempt.
   - One run ended in a failed integration-test result.
   - Later repeated validation stabilized.
   - This was narrowed by S2-0C into a repeatable 3/3 passing simulator path on the same machine.

---

## 7. Exit Assessment

Against the `Pack S2-0A` job definition, this pack is complete:

- startup commands and dependencies were inspected
- the real full-stack path was identified
- the initial golden-path checklist basis is now explicit
- the first real startup was attempted
- blockers and non-blocking findings were documented

Follow-on packs completed on the same date:

- `docs/product/implementation/SPARKLE_S2_0B_GOLDEN_PATH_BRING_UP_CHECKLIST_2026-04-06.md`
- `docs/product/implementation/SPARKLE_S2_0C_IOS_SIMULATOR_SMOKE_VALIDATION_2026-04-06.md`

Recommended next pack:

> `S2-1A North-Star Walkthrough Setup`
