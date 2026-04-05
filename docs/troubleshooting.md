# Troubleshooting

<p>
  <img src="assets/icons/evidence.svg" alt="Troubleshooting icon" width="22" />
  &nbsp;<strong>Common issues and the fixes that mattered</strong>
</p>

This page records the bugs and failure cases that showed up during the build and what fixed them.

## Quick Table

| Symptom | Likely cause | What fixed it |
| --- | --- | --- |
| Network-latency drill caused workload restarts | The workload was running on the Flask development server and probes were too strict. | Switched to Gunicorn and tuned startup, readiness, and liveness probes. |
| Gold cache burst exceeded the error budget | Database connections were exhausted under burst traffic. | Added pooled PostgreSQL connections and kept cache-friendly reads away from unnecessary DB churn. |
| Seed job failed during deploy | Kubernetes Job pod templates are immutable across image changes. | Recreate the `workload-seed` job during deploy instead of applying it in place. |
| Workspace looked offline even when the app worked | The SSE stream sent one snapshot and closed. | Keep `/api/stream` open and send repeated snapshots plus keep-alives. |
| Old ReplicaSets cluttered the UI | Rollout history objects were being shown as active inventory. | Filter inactive `0/0` ReplicaSets out of the main workspace view. |

## If The Workspace Does Not Update

Try this:

1. check `/api/stream` from the client network path
2. confirm the control plane is healthy
3. refresh the page and confirm the live-update chip reconnects

Likely areas:

- `control_plane/__init__.py`
- client SSE handling

## If Gold Cache Burst Misses Budget

Check:

1. whether Redis is enabled
2. whether the workload is using pooled PostgreSQL connections
3. whether the cache headers show `MISS`, `HIT`, or `BYPASS`

Likely areas:

- `app/cache.py`
- `app/database.py`
- `control_plane/scale_lab.py`

## If The Reference Workload Looks Empty

Check:

1. whether the seed job completed
2. whether the database secret is valid
3. whether `/shortener/status-summary` returns counts

Likely areas:

- `infra/digitalocean/k8s/workload-seed.yaml`
- `.github/workflows/deploy.yml`
- `scripts/seed_all.py`
