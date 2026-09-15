# Runtime Verification Runbook for Phase 2/3
> **Objective:** Generate hard evidence for Semantic Cache, Hybrid Fallback, and Bandit Feedback Loop to unblock the PR.

**Prerequisites:**
- Docker and Docker Compose must be running (`make dev-up`).
- `curl` installed.
- Access to the terminal.

---

## Step 1: Semantic Cache & Fallback Verification

### 1.1 Baseline Metrics
Capture the initial state of the metrics.

**Command:**
```bash
curl -s http://localhost:8080/metrics | egrep "sparkle_semantic_cache_(hit|miss|bypass)_total|sparkle_retrieval_(timeout|error)_total|rag_retrieval_latency"
# OR if using Backend directly:
# curl -s http://localhost:8000/api/v1/health/metrics | egrep ...
```

### 1.2 Verify Semantic Cache Hit
Trigger the cache by sending the same query twice.

**Action:**
1. Send a Chat Query (e.g., via UI or `test_websocket_client.py`).
2. Wait for response.
3. Send the **exact same** Query again.

**Verification:**
Run the metrics command again.
- Expect `sparkle_semantic_cache_miss_total` to increase by 1 (first query).
- Expect `sparkle_semantic_cache_hit_total` to increase by 1 (second query).

### 1.3 Verify Hybrid Fallback (Resilience)
Simulate a Redis/RediSearch failure.

**Action:**
1. Stop the Redis container:
   ```bash
   docker stop sparkle_redis
   ```
2. Send a **new** Chat Query (one that isn't cached).
3. Verify the chat still works (fallback to PGVector).

**Verification:**
Run the metrics command again.
- Expect `sparkle_retrieval_error_total` or `sparkle_retrieval_timeout_total` to increase.
- The chat response should still contain valid information (proving fallback success).

**Restore:**
```bash
docker start sparkle_redis
```

---

## Step 2: Bandit Feedback Loop Verification

### 2.1 Submit Feedback
Trigger the feedback loop.

**Action:**
1. Send a Chat Query. Note the `message_id`.
2. Submit "Thumbs Down" (or Up) feedback for that message.
   - Use the UI or a direct API call if available.
3. Send **another** Chat Query (triggers bandit update/selection).

### 2.2 Verify Bandit Metrics
Check if the feedback influenced the system latency/metrics.

**Command:**
```bash
curl -s http://localhost:8080/metrics | grep "sparkle_feedback_to_effect_seconds"
```

**Verification:**
- Expect `sparkle_feedback_to_effect_seconds_count` to increase.
- Expect `sparkle_prompt_bandit_updates_total` to increase.

---

## Appendix: Automated Test Scripts
You can use the following scripts to automate the chat interaction:

- `python backend/test_websocket_client.py` (Integration Test)
- `python backend/test_grpc_simple.py` (gRPC Demo Mode)

**Note on Environment:**
The current CLI environment detected that Docker is not running. Please execute these steps in a terminal with full Docker access to generate the evidence logs.
