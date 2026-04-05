# Decision Log

<p>
  <img src="assets/icons/api.svg" alt="Decision log icon" width="22" />
  &nbsp;<strong>Why the platform is shaped this way</strong>
</p>

| Decision | Why we made it | Tradeoff |
| --- | --- | --- |
| Keep the reference workload simple | We wanted time and attention to go into infrastructure, resilience, scaling, and operator experience. | The sample app is intentionally not the product story by itself. |
| Build an API-first control plane | The product direction is headless and should support more than one client. | The current client can only expose what the control plane already models well. |
| Use a lightweight React client instead of a heavier framework | The first client should stay close to the API and leave room for other interfaces later. | Fewer built-in framework conveniences. |
| Use Chaos Mesh for faults | It gives structured, cluster-native fault injection instead of ad hoc kill scripts. | Requires Kubernetes-specific setup and careful guardrails. |
| Use Redis for Gold scale proof | The fastest read is the one that does not hit the database. | Cache invalidation and proof logic add complexity. |
| Use pooled PostgreSQL connections | Heavy read bursts were exhausting database connections. | Pool sizing has to stay disciplined per workload process. |
| Keep the live product locked to one reference workload | It keeps the story clean and safe while the control plane model hardens. | The current demo is narrower than the long-term platform direction. |
