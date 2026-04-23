-- KEYS[1]: Quota Key (e.g., "user:quota:1001")

local current = redis.call("DECR", KEYS[1])
return current
