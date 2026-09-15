-- KEYS[1]: Usage Key
-- KEYS[2]: Request Key
-- ARGV[1]: Tokens
-- ARGV[2]: Request TTL
-- ARGV[3]: Usage TTL

if redis.call("EXISTS", KEYS[2]) == 1 then
  return 0
end

redis.call("INCRBY", KEYS[1], ARGV[1])
redis.call("SETEX", KEYS[2], ARGV[2], "1")
redis.call("EXPIRE", KEYS[1], ARGV[3])

return 1