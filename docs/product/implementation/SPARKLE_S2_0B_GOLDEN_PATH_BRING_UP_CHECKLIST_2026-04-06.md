# Sparkle S2-0B Golden-Path Bring-Up Checklist

> Date: 2026-04-06  
> Status: Completed  
> Stage: `S2-0 Runnable Golden Path Bring-Up`  
> Pack: `S2-0B Golden-Path Bring-Up Checklist`

---

## 0. Goal

This is the shortest trusted operator checklist for opening the real Sparkle product locally on the current branch state.

It is intentionally narrow:

- one machine path
- one device target
- one simulator proof

---

## 1. Chosen Golden Path

Use this exact target:

- platform: iOS simulator
- device: `iPhone 16e`
- simulator id: `79461B43-C730-47C4-9994-10CA7C5546BD`
- stack: local backend + local gateway + local PostgreSQL + local Redis + local MinIO + local workers

Do not switch to Android or physical-device bring-up for Stage 2 unless this path breaks.

---

## 2. Preconditions

Before starting, confirm:

1. Docker Desktop is running
2. `backend/.venv` exists and Python deps are installed
3. Flutter is installed and `flutter devices` works
4. local env files are already configured

If any of those is false, stop and fix that first.

---

## 3. Bring-Up Checklist

### Step 1. Go to repo root

```bash
cd /Users/brsama/code/GitHub/Sparkle-project
```

### Step 2. Start the full local stack

```bash
./scripts/dev_local_stack.sh up
```

Expected:

- PostgreSQL healthy
- Redis healthy
- MinIO running
- API ready
- gateway ready
- workers started

### Step 3. Confirm service status

```bash
./scripts/dev_local_stack.sh status
```

Expected:

- `sparkle_db` healthy
- `sparkle_redis` healthy
- `sparkle_minio` running
- `grpc` running
- `api` running
- `gateway` running
- `summarization_worker` running
- `billing_worker` running

### Step 4. Run config and startup checks

```bash
make local-config-check
cd backend && .venv/bin/python scripts/startup_check.py
cd ..
```

Expected:

- local config audit passed
- startup import check passed

### Step 5. Run stack health gates

```bash
./scripts/dev_local_stack.sh smoke
make smoke
make local-signoff-preflight
```

Expected:

- backend health `200`
- gateway health `200`
- gateway CQRS health `200`
- postgres reachable
- redis reachable
- alembic at head
- Redis search index `idx:knowledge` present

### Step 6. Confirm the simulator target

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter devices
```

Expected:

- `iPhone 16e` appears as a booted iOS simulator

### Step 7. Run the real mobile proof

```bash
flutter test integration_test/app_test.dart -d 79461B43-C730-47C4-9994-10CA7C5546BD -r compact
```

Expected:

- Xcode build completes
- guest enters the app
- dashboard shell loads
- navigation reaches galaxy, chat, community, profile, and back home
- test ends with `All tests passed!`

---

## 4. Stop Conditions

Stop and treat the run as failed if any of these happen:

1. `dev_local_stack.sh up` cannot reach healthy infra
2. API or gateway health checks fail
3. `startup_check.py` fails imports
4. `local-signoff-preflight` fails any gate
5. the simulator is missing
6. the integration test fails to reach `All tests passed!`

---

## 5. Known Side Effects

This bring-up path is not side-effect free.

1. `./scripts/dev_local_stack.sh up` recreates the Redis knowledge index
2. `./scripts/dev_local_stack.sh up` rebuilds the tracked binary `backend/gateway/bin/gateway`

Future Codex runs should expect the worktree to show that binary as modified after gateway bring-up.

---

## 6. Known Non-Blocking Warnings

1. this bring-up path still rebuilds the tracked gateway binary as part of startup
2. the checklist proves shell viability, not the full north-star user journey
3. passing this checklist does not yet prove first-response quality or adaptation quality

---

## 7. Exit Signal

S2-0B is satisfied when a future Codex can follow this checklist without tribal knowledge and reach the real simulator proof.

As of 2026-04-06, this condition is met on this machine.
