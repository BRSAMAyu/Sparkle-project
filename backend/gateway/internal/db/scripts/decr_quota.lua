-- KEYS[1]: Quota Key (e.g., "user:quota:1001")
-- ARGV[1]: TTL in seconds (optional, defaults to 86400)

local current = tonumber(redis.call("GET", KEYS[1])) or 0
if current <= 0 then
    return -1
end
local result = redis.call("DECR", KEYS[1])
-- R2-GW-2: only stamp a TTL when the key has none. The previous guard
-- (`result == current - 1`) was a tautology — DECR always returns current-1,
-- so every decrement slid the TTL forward ("first decrement" never held) and
-- an active user's daily quota key would never expire / never reset. The
-- reserve/refund/decr family currently has no production callers in the
-- gateway (admission is usage-metering based); fixed conservatively so the
-- script is safe if it is ever wired up.
if redis.call("TTL", KEYS[1]) == -1 then
    local ttl = tonumber(ARGV[1]) or 86400
    redis.call("EXPIRE", KEYS[1], ttl)
end
return result
