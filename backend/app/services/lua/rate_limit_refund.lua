-- Atomic quota refund for usage counters.
-- KEYS[1]: quota key
-- ARGV[1]: amount
-- ARGV[2]: ttl_seconds
local key = KEYS[1]
local amount = tonumber(ARGV[1]) or 0
local ttl = tonumber(ARGV[2]) or 0

if amount <= 0 then
  return tonumber(redis.call("get", key) or "0")
end

local current = tonumber(redis.call("get", key) or "0")
if current <= 0 then
  return 0
end

local refund = amount
if refund > current then
  refund = current
end

local new_val = current - refund
if new_val <= 0 then
  redis.call("del", key)
  return 0
end

redis.call("set", key, new_val)
if ttl > 0 then
  redis.call("expire", key, ttl)
end

return new_val
