-- KEYS[1]: Quota Key (e.g., "user:quota:1001")
-- KEYS[2]: Request Key (e.g., "quota:request:1001:req_abc")
-- KEYS[3]: Sync Queue Key (e.g., "queue:sync:quota")
-- ARGV[1]: Queue Payload JSON (e.g., '{"uid":"1001","delta":1,"ts":123456,"request_id":"req_abc","type":"refund"}')
-- ARGV[2]: Request TTL seconds

if redis.call("EXISTS", KEYS[2]) == 0 then
  local current = redis.call("GET", KEYS[1]) or "0"
  return {0, tonumber(current)}
end

redis.call("DEL", KEYS[2])
local current = redis.call("INCR", KEYS[1])
redis.call("RPUSH", KEYS[3], ARGV[1])

return {1, current}
