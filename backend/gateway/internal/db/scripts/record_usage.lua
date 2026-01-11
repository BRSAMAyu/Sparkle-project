-- KEYS[1]: Usage Key (e.g., "llm_tokens:1001:2025-01-11")
-- KEYS[2]: Request Key (e.g., "usage:request:1001:req_abc")
-- ARGV[1]: Tokens to add
-- ARGV[2]: Request TTL seconds
-- ARGV[3]: Usage TTL seconds

if redis.call("EXISTS", KEYS[2]) == 1 then
  return 0
end

redis.call("INCRBY", KEYS[1], tonumber(ARGV[1]))
redis.call("SETEX", KEYS[2], tonumber(ARGV[2]), "1")
redis.call("EXPIRE", KEYS[1], tonumber(ARGV[3]))

return 1
