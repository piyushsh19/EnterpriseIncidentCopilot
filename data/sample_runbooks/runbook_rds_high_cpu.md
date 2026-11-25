# Runbook: RDS High CPU
Service: rds | Severity: Sev2 by default

## Symptoms
- CloudWatch `CPUUtilization` above 90% for 5+ minutes
- API p99 latency rising, DB connection pool saturation

## Troubleshooting
1. Open Performance Insights and sort by "Top SQL" to find the heaviest query.
2. Check `DatabaseConnections`; a spike usually means a connection leak or retry storm.
3. Look for missing indexes: run `EXPLAIN ANALYZE` on the top query.
4. Kill a runaway query only after confirming with the owning team (CONFIRM FIRST).
5. If load is legitimate, scale the instance class up or add a read replica.

## Escalation
Page the database on-call if CPU stays above 90% for 15 minutes after mitigation.
