# Runbook: AWS IAM AccessDenied Errors
Service: iam | Severity: Sev3

## Symptoms
- `AccessDenied` / `UnauthorizedOperation` / `is not authorized to perform` in logs
- A service starts failing right after an IAM, SCP or bucket policy change

## Troubleshooting
1. Identify the principal: `aws sts get-caller-identity` from the failing workload.
2. Find the denied call in CloudTrail (`errorCode = AccessDenied`) with the exact action and resource.
3. Use the IAM Policy Simulator for that principal, action and resource.
4. Check every layer: identity policy, resource policy (S3/KMS), permission boundary, SCP, session policy.
5. Explicit Deny always wins; look for a recent Deny statement.
6. For KMS, the key policy must also allow the principal.

## Escalation
Escalate to the cloud security team before widening any policy to `*`.
