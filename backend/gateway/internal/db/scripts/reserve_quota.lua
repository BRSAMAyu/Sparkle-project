-- KEYS[1]: Quota Key (e.g., "user:quota:1001")
-- KEYS[2]: Request Key (e.g., "quota:request:1001:req_abc")
-- KEYS[3]: Sync Queue Key (e.g., "queue:sync:quota")
-- ARGV[1]: Queue Payload JSON (e.g., '{"uid":"1001","delta":-1,"ts":123456,"request_id":"req_abc"}')
-- ARGV[2]: Request TTL seconds

-- 1. Idempotency check
if redis.call("EXISTS", KEYS[2]) == 1 then
  local current = redis.call("GET", KEYS[1]) or "0"
  return {0, tonumber(current)}
end

-- 2. Quota check
local current = tonumber(redis.call("GET", KEYS[1]) or "0")
if current <= 0 then
  return {-1, current}
end

-- 3. Reserve (decrement) and enqueue sync
current = redis.call("DECR", KEYS[1])
redis.call("SETEX", KEYS[2], tonumber(ARGV[2]), "1")
redis.call("RPUSH", KEYS[3], ARGV[1])

return {1, current}
