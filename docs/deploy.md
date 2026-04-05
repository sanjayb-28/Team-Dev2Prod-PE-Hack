# Deploy Guide

<p>
  <img src="assets/icons/api.svg" alt="Deploy icon" width="22" />
  &nbsp;<strong>Release and rollback path</strong>
</p>

Dev2Prod deploys through GitHub Actions into one DigitalOcean Kubernetes cluster.

## Release Path

1. Push or merge the intended change into `main`.
2. Let `Tests and Gate` pass.
3. The `Deploy to DigitalOcean` workflow picks up the successful `main` run or can be started manually.
4. The workflow:
   - builds backend and client images
   - pushes them to DigitalOcean Container Registry
   - installs or upgrades Chaos Mesh
   - applies the Kubernetes manifests
   - waits for rollouts
   - recreates the workload seed job
5. Confirm the public client and the reference workload are reachable.

## Rollback Path

The safest rollback is a code rollback, not a manual cluster mutation.

1. Identify the last known good commit on `main`.
2. Revert the bad change in Git.
3. Push the revert so `Tests and Gate` runs again.
4. Let the deploy workflow roll the cluster back to the reverted image set.

This keeps the release history truthful and leaves the repo and cluster in the same state.

## Required Delivery Secrets

- `DIGITALOCEAN_ACCESS_TOKEN`
- `WORKLOAD_DATABASE_URL`
- `CLIENT_TLS_CERT`
- `CLIENT_TLS_KEY`

## Production Runtime Shape

- Namespace: `dev2prod`
- Public service: `client`
- Internal services: `control-plane`, `workload-api`, `redis`
- Managed database: PostgreSQL via secret-backed `DATABASE_URL`

## Supporting References

- [DigitalOcean delivery](../infra/digitalocean/README.md)
- [Workflow: tests](../.github/workflows/tests.yml)
- [Workflow: deploy](../.github/workflows/deploy.yml)
