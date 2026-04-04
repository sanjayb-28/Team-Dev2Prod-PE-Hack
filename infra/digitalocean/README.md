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
- A GitHub Actions secret named `CLIENT_TLS_CERT`
- A GitHub Actions secret named `CLIENT_TLS_KEY`

The deploy workflow currently uses the fixed production names already provisioned in DigitalOcean:

- Registry: `dev2prod`
- Cluster: `dev2prod`
- Database cluster: `dev2prod`

## Runtime Shape

- Namespace: `dev2prod`
- Public service: `client`
- Internal services: `control-plane`, `workload-api`
- Secret created by CD: `workload-env`
- Chaos Mesh namespace: `chaos-mesh`

## Notes

- CD installs or upgrades Chaos Mesh before the platform manifests roll out.
- The control plane uses namespace-scoped RBAC and reads pod logs through `pods/log`.
- After deploying the TLS-enabled client, set Cloudflare SSL mode to `Full (strict)`.
