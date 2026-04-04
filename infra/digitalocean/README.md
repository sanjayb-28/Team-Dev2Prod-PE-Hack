# DigitalOcean Delivery

This deployment shape keeps the full product on one DigitalOcean Kubernetes cluster:

- `client` is the public entrypoint
- `control-plane` stays private inside the namespace
- `workload-api` stays private inside the namespace
- PostgreSQL is provided through a managed database URL secret

The client container proxies `/api/*` to the in-cluster control plane, so the browser only needs one public URL.

## Prerequisites

- A DOKS cluster
- A DigitalOcean Container Registry linked to that cluster
- A GitHub Actions secret named `DIGITALOCEAN_ACCESS_TOKEN`
- A GitHub Actions secret named `WORKLOAD_DATABASE_URL`

The deploy workflow currently uses the fixed production names already provisioned in DigitalOcean:

- Registry: `dev2prod`
- Cluster: `dev2prod`
- Database cluster: `dev2prod`

## Runtime Shape

- Namespace: `dev2prod`
- Public service: `client`
- Internal services: `control-plane`, `workload-api`
- Secret created by CD: `workload-env`

## Notes

- `CHAOS_MESH_ENABLED` is `false` by default. Turn it on after Chaos Mesh is installed in the cluster.
- The control plane uses namespace-scoped RBAC and reads pod logs through `pods/log`.
