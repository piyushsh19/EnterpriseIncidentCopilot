# Runbook: Kubernetes CrashLoopBackOff
Service: k8s

## Symptoms
- Pods restarting repeatedly, status `CrashLoopBackOff`, often right after a deploy

## Troubleshooting
1. `kubectl describe pod <pod>` and read Events (OOMKilled, failed probes, image pull).
2. `kubectl logs <pod> --previous` to see the last crash.
3. OOMKilled: raise memory limits or fix the leak.
4. Failed liveness probe: check probe path, port and `initialDelaySeconds`.
5. Bad config/secret: compare ConfigMap and Secret with the previous release.
6. If the deploy caused it, roll back: `kubectl rollout undo deployment/<name>`.

## Escalation
Escalate to the platform team if more than 30% of replicas are down.
