# SOP: Production Rollback
Service: deploy

1. Decide fast: if errors or latency regressed within 30 minutes of a deploy, roll back first and debug later.
2. Announce the rollback in #incidents with the release version.
3. Kubernetes: `kubectl rollout undo deployment/<name>` then `kubectl rollout status deployment/<name>`.
4. ECS: update the service to the previous task definition revision.
5. Database migrations: never roll back a destructive migration without the DBA (CONFIRM FIRST).
6. Disable the feature flag if the change was flag-guarded; that is faster than a redeploy.
7. Verify metrics returned to baseline for 15 minutes, then close the rollback.
