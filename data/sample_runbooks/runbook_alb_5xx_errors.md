# Runbook: Load Balancer 5xx Errors (ALB / ELB)
Service: alb | Severity: Sev2, Sev1 if customer-facing traffic is above 5% errors

## Symptoms
- CloudWatch `HTTPCode_ELB_5XX_Count` or `HTTPCode_Target_5XX_Count` spiking
- Users see 502 Bad Gateway or 503 Service Unavailable

## Troubleshooting
1. Split ELB vs target errors: ELB 5xx = the load balancer itself, Target 5xx = your app.
2. 502: targets closing connections; check app keep-alive timeout is longer than the ALB idle timeout (60s).
3. 503: no healthy targets; check target group health checks and the health check path.
4. 504: target response slower than the idle timeout; look at app latency and slow dependencies.
5. Check recent deploys; roll back if errors started with a release.
6. Read ALB access logs in S3 for the failing paths and `target_status_code`.

## Escalation
Declare Sev1 and follow the Sev1 escalation SOP if errors exceed 5% for 5 minutes.
