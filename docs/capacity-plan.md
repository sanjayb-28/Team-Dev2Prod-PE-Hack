# Capacity Plan

<p>
  <img src="assets/icons/scale.svg" alt="Capacity icon" width="22" />
  &nbsp;<strong>What is proven today and where the system bends first</strong>
</p>

This is not a universal production SLA. It is the current demonstrated capacity story for the reference workload and the benchmark lanes that ship with Dev2Prod.

## Current Proven Benchmarks

| Lane | Target shape | What it proves today |
| --- | --- | --- |
| Bronze baseline | 50 concurrent users | The platform can establish a measurable starting point with p95 latency and error rate. |
| Silver scale-out | 200 concurrent users | The workload can be scaled horizontally and measured again under a larger load shape. |
| Gold cache burst | 500 concurrent users or equivalent heavy burst lane | Redis-backed reads and pooled database connections keep the heavy lane stable enough to stay within the documented error-budget target. |

## What Bends First

The first meaningful pressure points found during the project were:

1. database connection pressure under burst traffic
2. probe sensitivity during network-delay drills
3. UI clarity when a drill completed too quickly for the workspace to narrate it well

## Current Limits

The current live shape is still intentionally scoped:

- one cluster namespace
- one reference workload
- one guarded fault target
- one public client surface

That means the product demonstrates controlled resilience and scalability well, but it is not yet a general multi-workload platform.

## What Extends The Limit

The next meaningful platform steps are:

- headless control-plane expansion
- workload onboarding beyond the reference app
- broader fault coverage
- more cluster-level context
- more automation and CLI-friendly flows
