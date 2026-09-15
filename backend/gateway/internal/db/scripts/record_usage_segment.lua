-- KEYS[1]: Daily Usage Key (e.g., "llm_tokens:1001:2025-01-11")
-- KEYS[2]: Weekly Usage Key (e.g., "llm_tokens:1001:week:2025:02")
-- KEYS[3]: Segment Key (e.g., "usage:segment:1001:req_abc:1")
-- ARGV[1]: Tokens to add
-- ARGV[2]: Segment TTL seconds
-- ARGV[3]: Daily TTL seconds
-- ARGV[4]: Weekly TTL seconds

if redis.call("EXISTS", KEYS[3]) == 1 then
  return 0
end

redis.call("INCRBY", KEYS[1], tonumber(ARGV[1]))
redis.call("INCRBY", KEYS[2], tonumber(ARGV[1]))
redis.call("SETEX", KEYS[3], tonumber(ARGV[2]), "1")
redis.call("EXPIRE", KEYS[1], tonumber(ARGV[3]))
redis.call("EXPIRE", KEYS[2], tonumber(ARGV[4]))

return 1
