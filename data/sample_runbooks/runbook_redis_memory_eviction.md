# Runbook: Redis Memory Pressure and Key Eviction
Service: redis | Severity: Sev2 by default

## Symptoms
- `used_memory` close to `maxmemory`, `evicted_keys` rising
- Cache hit rate dropping, upstream database load increasing
- Errors like `OOM command not allowed when used memory > 'maxmemory'`

## Troubleshooting
1. Run `INFO memory` and `INFO stats`; note `used_memory_human`, `maxmemory_policy`, `evicted_keys`.
2. Find big keys: `redis-cli --bigkeys` (run on a replica if possible).
3. Check for keys without TTL: sample with `SCAN` + `TTL`; missing TTLs are the usual cause.
4. Confirm the eviction policy; for a cache use `allkeys-lru`, never `noeviction`.
5. Short-term: scale up the node type or add shards (ElastiCache cluster mode).
6. Do not run `FLUSHALL` in production (CONFIRM FIRST with the service owner).

## Escalation
Page the platform on-call if evictions push database CPU above 80%.
