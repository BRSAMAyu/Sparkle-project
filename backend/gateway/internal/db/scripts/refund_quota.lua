-- KEYS[1]: Quota Key (e.g., "user:quota:1001")
-- KEYS[2]: Request Key (e.g., "quota:request:1001:req_abc")
-- ARGV[1]: Request TTL seconds

if redis.call("EXISTS", KEYS[2]) == 0 then
  local current = redis.call("GET", KEYS[1]) or "0"
  return {0, tonumber(current)}
end

redis.call("DEL", KEYS[2])
local current = redis.call("INCR", KEYS[1])

return {1, current}
