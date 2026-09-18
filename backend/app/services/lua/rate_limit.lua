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
-- 固定窗口：仅当 key 尚无 TTL（首写/历史遗留）时设置，
-- 避免每次 incrby 滑动续期导致"日"配额永不跨日重置（Q1）
if ttl > 0 and redis.call("ttl", key) < 0 then
  redis.call("expire", key, ttl)
end

return {1, new_val}
