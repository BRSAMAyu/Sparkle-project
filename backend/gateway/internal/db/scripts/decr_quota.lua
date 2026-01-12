-- KEYS[1]: Quota Key (e.g., "user:quota:1001")
-- KEYS[2]: Sync Queue Key (e.g., "queue:sync:quota")
-- ARGV[1]: Queue Payload JSON (e.g., '{"uid":"1001", "delta":-1, "ts":123456}')

-- 1. Execute decrement
local current = redis.call("DECR", KEYS[1])

-- 2. Atomically push to sync queue
redis.call("RPUSH", KEYS[2], ARGV[1])

-- 3. Return latest balance
return current
