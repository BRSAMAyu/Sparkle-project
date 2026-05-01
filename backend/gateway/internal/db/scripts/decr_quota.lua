-- KEYS[1]: Quota Key (e.g., "user:quota:1001")

local current = tonumber(redis.call("GET", KEYS[1])) or 0
if current <= 0 then
    return -1
end
local result = redis.call("DECR", KEYS[1])
return result
