# Config Reference

<p>
  <img src="assets/icons/api.svg" alt="Config icon" width="22" />
  &nbsp;<strong>Environment variables and deploy secrets</strong>
</p>

This page lists the runtime knobs that matter for Dev2Prod.

## Workload API

| Variable | Required | What it controls |
| --- | --- | --- |
| `APP_HOST` | No | Host binding for the Flask workload process. |
| `APP_PORT` | No | Port binding for the workload process. |
| `DATABASE_URL` | Yes in production | PostgreSQL connection string for the workload data. |
| `DATABASE_HOST` | Local fallback | Host-based PostgreSQL config when `DATABASE_URL` is not used. |
| `DATABASE_NAME` | Local fallback | Database name for host-based PostgreSQL config. |
| `DATABASE_PORT` | Local fallback | PostgreSQL port for host-based config. |
| `DATABASE_USER` | Local fallback | PostgreSQL username for host-based config. |
| `DATABASE_PASSWORD` | Local fallback | PostgreSQL password for host-based config. |
| `DATABASE_POOL_MAX_CONNECTIONS` | No | Maximum pooled PostgreSQL connections per process. |
| `DATABASE_POOL_STALE_TIMEOUT` | No | Seconds before pooled connections are considered stale. |
| `REDIS_URL` | No | Enables Redis-backed caching for the read-heavy URL paths. |

## Control Plane

| Variable | Required | What it controls |
| --- | --- | --- |
| `CLUSTER_NAME` | No | Display name for the cluster. |
| `CLUSTER_NAMESPACE` | No | Namespace the control plane targets. |
| `CLUSTER_PROVIDER` | No | Provider label shown in the product. |
| `WORKLOAD_API_URL` | Yes | Base URL for workload health checks and proof paths. |
| `WORKLOAD_DEPLOYMENT_NAME` | Yes | Deployment name used for targeting and inventory. |
| `WORKLOAD_SERVICE_NAME` | Yes | Service name used for targeting and scale runs. |
| `WORKLOAD_DISPLAY_NAME` | No | Human-readable workload label shown in the client. |
| `CONTROL_PLANE_DEPLOYMENT_NAME` | Yes | Deployment name for the control plane itself. |
| `CONTROL_PLANE_ALLOWED_ORIGIN` | Optional | CORS origin for the client. |
| `CHAOS_MESH_ENABLED` | No | Enables or disables cluster fault execution. |
| `CONTROL_PLANE_STREAM_INTERVAL_SECONDS` | No | Live-stream snapshot interval. |

## Client

| Variable | Required | What it controls |
| --- | --- | --- |
| `VITE_CONTROL_PLANE_URL` | Optional | Hosted control-plane URL for local client development. |

## GitHub Actions Secrets

| Secret | Required | What it controls |
| --- | --- | --- |
| `DIGITALOCEAN_ACCESS_TOKEN` | Yes | Access token for registry, Kubernetes, and managed database operations. |
| `WORKLOAD_DATABASE_URL` | Yes | Managed PostgreSQL connection string injected into the workload secret. |
| `CLIENT_TLS_CERT` | Yes | TLS certificate for the public client ingress. |
| `CLIENT_TLS_KEY` | Yes | TLS key for the public client ingress. |
