# API Docs

<p>
  <img src="assets/icons/api.svg" alt="API icon" width="22" />
  &nbsp;<strong>Reference workload and control-plane endpoints</strong>
</p>

This page lists the main endpoints exposed by Dev2Prod.

The product has two API layers:

- the reference workload API
- the control-plane API used by the client

## Reference Workload API

### Health and showcase

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status":"ok"}` when the workload is alive. |
| `GET` | `/shortener/` | Renders the public reference-workload page. |
| `GET` | `/shortener/status-summary` | Returns live counts, latest activity, and cache mode for the workload. |
| `GET` | `/<short_code>` | Resolves a short code to the target URL and records a click event when the link is active. |

### Users

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/users` | Lists users. Supports optional pagination with `page` and `per_page`. |
| `GET` | `/users/<id>` | Returns one user. |
| `POST` | `/users` | Creates a user with `username` and `email`. |
| `PUT` | `/users/<id>` | Updates a user. |
| `DELETE` | `/users/<id>` | Deletes a user and the related data. |
| `POST` | `/users/bulk` | Imports users from CSV. |

### URLs

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/urls` | Lists URLs. Supports `user_id` and `is_active` filtering. |
| `GET` | `/urls/<id>` | Returns one URL. |
| `POST` | `/urls` | Creates a short URL. |
| `PUT` | `/urls/<id>` | Updates URL metadata such as title or active state. |
| `DELETE` | `/urls/<id>` | Deactivates and removes a URL entry. |

### Events

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/events` | Lists events. Supports `url_id`, `user_id`, and `event_type` filtering. |
| `POST` | `/events` | Creates an event tied to an active URL. |

### Compatibility layer

The older `/api/links` routes still exist as a compatibility surface for the original app shape.

## Control-Plane API

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/health` | Health endpoint for the control plane itself. |
| `GET` | `/api/cluster/status` | Returns cluster, workload, and Chaos Mesh status. |
| `GET` | `/api/resources` | Lists namespace resources for the Workspace page. |
| `GET` | `/api/resources/<kind>/<name>` | Returns one resource detail payload. |
| `GET` | `/api/resources/<kind>/<name>/events` | Returns events for a resource. |
| `GET` | `/api/resources/<kind>/<name>/logs` | Returns logs for a resource when available. |
| `GET` | `/api/experiments` | Lists fault experiments. |
| `POST` | `/api/experiments` | Starts a new fault experiment. |
| `POST` | `/api/experiments/<name>/cancel` | Stops a running experiment. |
| `GET` | `/api/scale-lab` | Returns the current scale-lab state and available lanes. |
| `POST` | `/api/scale-lab/runs` | Starts a new benchmark lane run. |
| `GET` | `/api/stream` | Streams live cluster snapshots to the client with Server-Sent Events. |

## Error Handling

Public API errors are returned as JSON with this general shape:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "A human-readable explanation."
  }
}
```

Typical cases:

- `404` for missing users, URLs, links, or resources
- `409` for conflicts such as duplicate usernames or duplicate short codes
- `422` for malformed or invalid input
