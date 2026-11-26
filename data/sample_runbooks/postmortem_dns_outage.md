# Postmortem: Internal DNS Resolution Failures
Service: dns | Duration: 1 h 12 min | Severity: Sev1

## What happened
Services intermittently failed to resolve internal hostnames; requests failed with `getaddrinfo ENOTFOUND` and `SERVFAIL`.

## Root cause
CoreDNS pods in the Kubernetes cluster were CPU-throttled after a traffic increase; the `ndots:5` default caused every lookup to try 5 search domains, multiplying DNS queries.

## Fix
Scaled CoreDNS replicas from 2 to 6, raised CPU limits, enabled NodeLocal DNSCache, and set `ndots:2` in pod dnsConfig.

## Actions
- Autoscale CoreDNS with cluster-proportional-autoscaler.
- Alert on CoreDNS `SERVFAIL` rate and latency.
- Use fully-qualified names (trailing dot) for hot external hostnames.
