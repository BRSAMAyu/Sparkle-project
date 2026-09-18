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

-- KEEPTTL：SET 默认会隐式清除 TTL，需保留原固定窗口；
-- 历史遗留的无 TTL key 在此补设，且不滑动续期（Q1）
redis.call("set", key, new_val, "KEEPTTL")
if ttl > 0 and redis.call("ttl", key) < 0 then
  redis.call("expire", key, ttl)
end

return new_val
