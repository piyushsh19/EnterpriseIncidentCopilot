# Runbook: Disk Full on Linux Hosts / EBS Volumes
Service: ec2 | Severity: Sev3, Sev2 if a database host

## Symptoms
- Alerts on `disk_used_percent` above 90%
- `No space left on device` in application logs; writes failing

## Troubleshooting
1. `df -h` to find the full mount, `df -i` to rule out inode exhaustion.
2. `sudo du -xh / --max-depth=2 | sort -h | tail` to find large directories.
3. Common culprits: `/var/log` (rotate with logrotate), Docker images (`docker system prune`, CONFIRM FIRST), core dumps, old deploy artifacts.
4. Deleted-but-open files: `sudo lsof +L1`; restart the holding process.
5. Grow the EBS volume (modify volume, then `growpart` + `resize2fs`/`xfs_growfs`).

## Escalation
Escalate to the database on-call immediately if the host runs a database.
