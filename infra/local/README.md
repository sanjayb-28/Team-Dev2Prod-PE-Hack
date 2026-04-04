# Local Stack

Bring up the backend stack:

```bash
docker compose -f infra/local/compose.yaml up --build
```

Endpoints:

- workload API: `http://127.0.0.1:15000`
- control plane: `http://127.0.0.1:18000`

Run the client separately:

```bash
cd client
npm install
npm run dev
```

The client dev server proxies `/api/*` to the local control plane by default.
