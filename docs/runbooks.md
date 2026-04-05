# Runbooks

<p>
  <img src="assets/icons/chaos.svg" alt="Runbook icon" width="22" />
  &nbsp;<strong>Step-by-step operator guides</strong>
</p>

These runbooks are intentionally short. They are meant to be usable during a real demo or a real failure investigation.

## Runbook: Pod Restart Drill

1. Open `Workspace`.
2. Confirm the target is `URL Shortener API`.
3. Start `Pod restart`.
4. Watch `Recovery watch` and `Resilience proof`.
5. Check the reference workload in the second tab.
6. Wait for the experiment to end and the workload state to settle.

What good looks like:

- one pod is replaced
- healthy replicas recover
- the reference workload stays reachable or returns quickly

## Runbook: CPU Pressure Drill

1. Open `Workspace`.
2. Start `CPU pressure`.
3. Watch the proof panels and evidence feed.
4. Check the reference workload.

What good looks like:

- one pod shows pressure
- the service remains understandable and usable

## Runbook: Gold Cache Burst

1. Open `Performance`.
2. Start `Gold cache burst`.
3. Watch the latest result and cache proof.
4. Confirm the error rate stays within target.

What good looks like:

- cache proof shows `MISS → HIT` or `HIT → HIT`
- the run completes with stable latency and acceptable error rate

## Runbook: Deploy Rollback

1. Identify the last known good commit on `main`.
2. Revert the bad change in Git.
3. Push the revert.
4. Let the release gate and deploy workflow rerun.
5. Confirm the public client and reference workload are healthy again.
