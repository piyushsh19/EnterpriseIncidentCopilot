# Postmortem: Expired TLS certificate on api.example.com
Service: edge | Duration: 47 minutes

## What happened
The public API certificate expired; clients saw `certificate has expired` errors.

## Root cause
Auto-renewal failed silently because the DNS validation record had been deleted.

## Fix
Re-created the DNS validation CNAME, re-issued the cert, reloaded the load balancer listener.

## Actions
- Alert 21 days before any certificate expiry.
- Add a synthetic check for TLS validity.
