-- Atomic quota check + decrement
-- KEYS[1]: quota key
-- ARGV[1]: limit
-- ARGV[2]: amount
-- ARGV[3]: ttl_seconds
local key = KEYS[1]
local limit = tonumber(ARGV[1]) or 0
local amount = tonumber(ARGV[2]) or 0
local ttl = tonumber(ARGV[3]) or 0

if limit <= 0 then
  return {1, 0}
end

local current = tonumber(redis.call("get", key) or "0")
if current + amount > limit then
  return {0, current}
end

local new_val = redis.call("incrby", key, amount)
if ttl > 0 then
  redis.call("expire", key, ttl)
end

return {1, new_val}
