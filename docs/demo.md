# Demo Guide

This is the short live walkthrough for Dev2Prod.

## Open These First

- Landing page: [dev2prod.sanjaybaskaran.dev](https://dev2prod.sanjaybaskaran.dev)
- Reference workload: [dev2prod.sanjaybaskaran.dev/shortener/](https://dev2prod.sanjaybaskaran.dev/shortener/)
- Workspace: [dev2prod.sanjaybaskaran.dev/workspace](https://dev2prod.sanjaybaskaran.dev/workspace)
- Performance: [dev2prod.sanjaybaskaran.dev/performance](https://dev2prod.sanjaybaskaran.dev/performance)

## Workspace Flow

### 1. Start with the healthy state

Action:
- show the `URL Shortener API` target
- point to `Service continuity`
- point to healthy pods

Inference:
- this is the baseline before any fault is introduced

### 2. Run `Pod restart`

Action:
- start the pod restart drill
- keep the reference workload tab visible

Inference:
- one pod is deliberately removed
- Kubernetes replaces it
- the system moves back toward a steady state

### 3. Watch recovery

Action:
- point to `Recovery watch`
- point to `Resilience proof`
- open the evidence feed

Inference:
- the cluster is not only recovering
- the platform is making the recovery understandable

### 4. Run `CPU pressure`

Action:
- start the CPU pressure drill

Inference:
- one workload pod is stressed
- the service should remain understandable and available

### 5. Optional: run `Network latency`

Action:
- start the network latency drill only if there is time

Inference:
- this is the degradation story
- it shows the platform can surface slowdown clearly, not only failure

## Performance Flow

### 1. Run `Bronze baseline`

Action:
- start the baseline lane

Inference:
- this is the starting performance reference

### 2. Run `Silver scale-out`

Action:
- start the scale-out lane

Inference:
- the workload scales horizontally and the benchmark result changes with it

### 3. Run `Gold cache burst`

Action:
- start the cache burst lane
- point to the cache proof and the latest result

Inference:
- this is the optimization story
- caching changes the burst behavior, not only the replica count

## Short Spoken Summary

If you need one short closing line:

Dev2Prod turns resilience and scale testing into guided product flows, so a team can break a workload before production does and actually understand what happened.
