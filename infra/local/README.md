# Local Stack

Bring up the local stack:

```bash
docker compose -f infra/local/compose.yaml up --build
```

Endpoints:

- cockpit: `http://127.0.0.1:14000`
- workload API: `http://127.0.0.1:15000`
- control plane: `http://127.0.0.1:18000`

If you want the client with live reload instead of the container:

```bash
cd client
npm install
npm run dev
```

The client dev server proxies `/api/*` to the local control plane by default.
