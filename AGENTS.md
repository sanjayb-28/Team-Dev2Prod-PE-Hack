# AGENTS

This file is for coding agents and automated collaborators working in this repository.

## Repo Shape

- `app/`: reference workload API and routes
- `control_plane/`: API-first orchestration layer for cluster state, chaos drills, and scale runs
- `client/`: React + Vite product client
- `infra/`: local Docker Compose and DigitalOcean Kubernetes manifests
- `tests/`: backend and control-plane test coverage
- `docs/`: public-facing project, architecture, and submission documentation

## Product Context

Dev2Prod is a controlled chaos and scale lab for Kubernetes workloads.

The current live product is intentionally scoped to one reference workload so the reliability and scalability story stays clear. The platform direction is broader: a headless control plane with more workload onboarding and more client surfaces later.

## Core Tooling

- Python: `uv`, Flask, Peewee, pytest
- Frontend: React 19, Vite, TypeScript, ESLint
- Infra: Docker Compose, DigitalOcean Kubernetes, Chaos Mesh, Redis, managed PostgreSQL
- CI/CD: GitHub Actions in `.github/workflows/tests.yml` and `.github/workflows/deploy.yml`

## Common Commands

Backend setup:

```bash
uv sync --group dev
```

Backend tests:

```bash
uv run pytest
```

Frontend dev:

```bash
cd client
npm install
npm run dev
```

Frontend verification:

```bash
cd client
npm run build
npm run lint
```

Local stack:

```bash
docker compose -f infra/local/compose.yaml --profile scale up --build
```

## Validation Expectations

Do not treat a change as complete until it has been validated.

Minimum expectations:

- backend changes: run the relevant `uv run pytest ...` targets
- client changes: run `npm run build` and `npm run lint`
- workflow or deploy changes: read the affected GitHub Actions file and check the manifest or command path carefully
- docs changes: verify links, paths, and referenced assets

If a change affects both client and backend behavior, validate both sides.

## Editing Guidance

- Keep the reference workload simple. Platform behavior matters more than sample-app feature expansion.
- Preserve the API-first control-plane direction.
- Prefer clear operator-facing behavior over raw infrastructure detail in user surfaces.
- Keep docs aligned with the real system. Do not document features that do not exist.
- Do not silently change product framing. The live product is a controlled chaos and scale lab, not a generic platform already supporting arbitrary workloads.

## Deployment Notes

- Production deploys from `main` through `.github/workflows/deploy.yml`
- Tests and coverage gate deploys through `.github/workflows/tests.yml`
- Production data uses managed PostgreSQL
- Redis is a cache, not the system of record
- `workload-seed` is recreated during deploy and reseeds the reference dataset

## High-Risk Areas

Be careful when changing:

- `control_plane/experiments.py`
- `control_plane/scale_lab.py`
- `app/database.py`
- `infra/digitalocean/k8s/*.yaml`
- `.github/workflows/*.yml`

These files directly affect runtime behavior, scale-lab correctness, or production delivery.

## Documentation Rule

If you change product behavior, infrastructure shape, benchmark behavior, or operator flow, check whether the following also need updates:

- `README.md`
- `docs/platform.md`
- `docs/reliability.md`
- `docs/scalability.md`
- `docs/api.md`
- `docs/deploy.md`
- `docs/decision-log.md`
- `docs/capacity-plan.md`

## AI Workflow Note

The project also includes [AI_USAGE.md](AI_USAGE.md), which explains how Codex was used in the build process. That file is for repo readers. This file is for agents working on the codebase.
