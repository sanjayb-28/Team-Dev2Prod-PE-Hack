# Dev2Prod

Dev2Prod is a controlled chaos and scale lab for Kubernetes workloads.

It brings resilience and scalability testing into one guided platform so teams can break a deployment on purpose, watch what recovers, and understand where the system bends before production has to teach the lesson the hard way.

![Dev2Prod platform architecture](docs/assets/diagrams/dev2prod-platform-overview.svg)

## Live Demo

Primary demo surfaces:

- Landing page: [dev2prod.sanjaybaskaran.dev](https://dev2prod.sanjaybaskaran.dev)
- Reference workload: [dev2prod.sanjaybaskaran.dev/shortener/](https://dev2prod.sanjaybaskaran.dev/shortener/)

Secondary operator surfaces:

- Workspace: [dev2prod.sanjaybaskaran.dev/workspace](https://dev2prod.sanjaybaskaran.dev/workspace)
- Performance: [dev2prod.sanjaybaskaran.dev/performance](https://dev2prod.sanjaybaskaran.dev/performance)

> Screenshot placeholder: landing page overview  
> Screenshot placeholder: workspace resilience flow

## What This Platform Does

Dev2Prod is built around two active product stories:

- Reliability: run guided fault drills, observe recovery, and make resilience visible.
- Scalability: run baseline, scale-out, and cache-aware benchmark lanes from one operating surface.

The live environment is intentionally scoped to one reference workload today. That lock is a guardrail for a clean demo, not the long-term product limit.

## Why The Reference Workload Is Simple

The URL shortener is intentionally basic.

That was a deliberate choice. We wanted the real effort to go into the platform around it: deployment shape, control plane behavior, cluster testing, cache strategy, recovery visibility, and guided operator flows. The shortener is there to make the platform legible, not to compete with it for attention.

## Reliability

The reliability surface centers on guided chaos drills in the workspace:

- `Pod restart` proves the platform can recover from a deliberate pod kill.
- `CPU pressure` shows how the service behaves when one pod is stressed.
- `Network latency` shows controlled degradation under slower network conditions.

The workspace is designed to make the recovery story readable:

- active target is clearly pinned
- live recovery state stays visible
- evidence and logs stay attached to the current drill

Read more:

- [Reliability doc](docs/reliability.md)
- [Demo walkthrough](docs/demo.md)

## Scalability

The scalability surface is built around three benchmark lanes:

- Bronze baseline
- Silver scale-out
- Gold cache burst

Those lanes combine workload scaling, benchmark jobs, and cache proof so the platform can show:

- baseline latency
- scale-out behavior under higher concurrency
- cached read-path improvement under heavier burst traffic

Read more:

- [Scalability doc](docs/scalability.md)
- [Evidence placeholders](docs/evidence.md)

## Platform Direction

Dev2Prod was shaped around the active quest constraints, but the product direction is broader.

The control plane is intentionally API-first. The current React client is one interface over that engine. The longer-term direction is:

- a headless control plane
- support for onboarding any cluster workload safely
- more supported chaos experiments
- richer cluster signals
- additional clients, including a CLI

The goal is not to hide the system. The goal is to abstract the operational ceremony into guided flows that more people can actually use.

## How To Demo This

Fast demo path:

1. Open the landing page and the reference workload side by side.
2. Go to `Workspace` and run `Pod restart`.
3. Watch the recovery panels and the reference workload together.
4. Run `CPU pressure`.
5. Move to `Performance` and run Bronze, Silver, and Gold in sequence.

Full script:

- [Demo guide](docs/demo.md)

## Repository Guide

Start here:

- [Platform narrative](docs/platform.md)
- [Reliability](docs/reliability.md)
- [Scalability](docs/scalability.md)
- [Evidence placeholders](docs/evidence.md)
- [Docs index](docs/index.md)

Implementation references:

- [DigitalOcean delivery](infra/digitalocean/README.md)
- [Local stack](infra/local/README.md)

## Run Locally

Install backend dependencies:

```bash
uv sync --group dev
```

Bring up the local stack:

```bash
docker compose -f infra/local/compose.yaml --profile scale up --build
```

Key local endpoints:

- cockpit: `http://127.0.0.1:14000`
- workload API: `http://127.0.0.1:15000`
- control plane: `http://127.0.0.1:18000`

## Relevant Reading

Two Meta Engineering pieces that informed the tone of this project:

- [Scaling services with Shard Manager](https://engineering.fb.com/2020/08/24/production-engineering/scaling-services-with-shard-manager/)
- [FOQS: Making a distributed priority queue disaster-ready](https://engineering.fb.com/2022/01/18/production-engineering/foqs-disaster-ready/)

They are not the blueprint for Dev2Prod, but they are useful examples of writing about scaling and resilience as real production problems rather than abstract exercises.
