-- KEYS[1]: Quota Key (e.g., "user:quota:1001")
-- ARGV[1]: TTL in seconds (optional, defaults to 86400)

local current = tonumber(redis.call("GET", KEYS[1])) or 0
if current <= 0 then
    return -1
end
local result = redis.call("DECR", KEYS[1])
-- Set TTL on first decrement so quota keys don't accumulate in Redis forever
if result == current - 1 then
    local ttl = tonumber(ARGV[1]) or 86400
    redis.call("EXPIRE", KEYS[1], ttl)
end
return result
