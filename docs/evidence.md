# Evidence Plan

<p>
  <img src="assets/icons/evidence.svg" alt="Evidence icon" width="22" />
  &nbsp;<strong>Submission-ready links, screenshots, and notes</strong>
</p>

This file is the working evidence sheet for the submission form. Each section below maps to one quest tier and records:

- the best link to attach
- the screenshot or video that supports it
- the short note that explains what the evidence proves

## Reliability

### Bronze

**Link**

- [Tests and Gate workflow run](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/actions/runs/23996027297)

**Image / video**

<table>
  <tr>
    <td align="center" width="50%">
      <img src="image-1.png" alt="Passing GitHub Actions test and coverage gate" />
      <br />
      <sub><strong>CI gate</strong>: automated tests and coverage passing in GitHub Actions.</sub>
    </td>
    <td align="center" width="50%">
      <img src="image.png" alt="Health endpoint returning status ok" />
      <br />
      <sub><strong>Health pulse</strong>: public workload health check returning <code>{"status":"ok"}</code>.</sub>
    </td>
  </tr>
</table>

**Notes**

- Automated tests run before release, coverage is enforced in CI, and the workload exposes a live `/health` pulse check.

### Silver

**Link**

- [Tests and Gate job view](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/actions/runs/23996027297/job/69984127615)

**Image / video**

<p align="center">
  <img src="image-2.png" alt="Failed test gate blocking release" width="90%" />
  <br />
  <sub><strong>Blocked gate</strong>: a failing test run stops the release path before broken code can move forward.</sub>
</p>

**Notes**

- The release gate blocks when tests fail, coverage remains visible in CI, and the public API returns structured JSON errors for invalid, missing, or inactive resources.

### Gold

**Link**

- [Workspace recovery demo](https://www.loom.com/share/01e5d8258899486aa2f99ba0d7240f06)

**Image / video**

- Loom recording linked above

**Notes**

- Workspace shows a deliberate fault, live recovery signals, and the reference workload staying readable while the cluster returns to a healthy state.

## Scalability

### Bronze

**Link**

- [Scalability implementation guide](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/scalability.md)

**Image / video**

<p align="center">
  <img src="image-3.png" alt="Bronze baseline result" width="90%" />
  <br />
  <sub><strong>Bronze baseline</strong>: the starting latency and error-rate profile before scale-out and cache help are applied.</sub>
</p>

**Notes**

- Baseline lane simulates 50 concurrent users and records the starting latency, error rate, request count, and throughput in one readable surface.

### Silver

**Link**

- [Silver scale-out demo](https://www.loom.com/share/6b63bbf844cd486b8ce725fb08069581)

**Image / video**

- Loom recording linked above

**Notes**

- Silver scale-out runs the workload behind a traffic-splitting layer and shows how the platform behaves at the 200-user lane with multiple app instances.

### Gold

**Link**

- [Capacity plan](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/capacity-plan.md)

**Image / video**

<p align="center">
  <img src="image-4.png" alt="Gold cache burst result with recent benchmark history" width="90%" />
  <br />
  <sub><strong>Gold cache burst</strong>: the cache-aware heavy lane, with recent benchmark history visible beside the latest result.</sub>
</p>

**Notes**

- Gold uses Redis-backed reads and the heaviest benchmark lane to show cache proof, burst stability, and the throughput gain after database-connection pressure was addressed.

## Documentation

### Bronze

**Link**

- [README](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/README.md)

**Image / video**

<p align="center">
  <img src="image-5.png" alt="README overview with live links and architecture diagram" width="90%" />
  <br />
  <sub><strong>README overview</strong>: top-level project framing, demo links, platform summary, and architecture diagram.</sub>
</p>

**Notes**

- The README gives setup context, demo entry points, architecture framing, and a direct path into the platform and API docs.

### Silver

**Link**

- [Deploy guide](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/deploy.md)
- [Troubleshooting guide](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/troubleshooting.md)
- [Config reference](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/config.md)

**Image / video**

- Pending capture

**Notes**

- Silver documentation covers how the platform is deployed, how a rollback is performed, how common failures are diagnosed, and which environment variables control the live system.

### Gold

**Link**

- [Runbooks](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/runbooks.md)
- [Decision log](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/decision-log.md)
- [Capacity plan](https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/capacity-plan.md)

**Image / video**

- Pending capture

**Notes**

- Gold documentation covers operational runbooks, the real technical tradeoffs behind the platform shape, and the measured capacity story for the benchmark lanes.
