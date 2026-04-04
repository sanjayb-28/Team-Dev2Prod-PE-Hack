export default function PerformancePage() {
  return (
    <div className="performance-page">
      <section className="performance-hero">
        <div className="section-heading">
          <p className="eyebrow">Performance</p>
          <h1>Scale the same workload through two clear test lanes.</h1>
          <p>
            The scale lab now has a baseline path for one service instance and a second
            path that pushes traffic through Nginx across two workload instances.
          </p>
        </div>

        <div className="performance-hero__summary">
          <dl className="performance-stats">
            <div>
              <dt>Bronze</dt>
              <dd>50 concurrent users</dd>
            </div>
            <div>
              <dt>Silver</dt>
              <dd>200 concurrent users</dd>
            </div>
            <div>
              <dt>Target</dt>
              <dd>Under 3s with scale-out</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="performance-grid">
        <article className="performance-panel">
          <p className="eyebrow">Baseline lane</p>
          <h2>Single instance baseline</h2>
          <p>
            This run hits one workload instance directly so the first set of latency and
            error numbers has no load balancer in the middle.
          </p>
          <pre className="performance-code">
            <code>infra/local/run-bronze-load.sh</code>
          </pre>
          <p className="performance-note">
            k6 target: one workload instance on the direct path
          </p>
        </article>

        <article className="performance-panel">
          <p className="eyebrow">Scale lane</p>
          <h2>Two-instance scale-out</h2>
          <p>
            This run routes traffic through Nginx to two workload instances and checks
            both response time and failure rate under the larger load.
          </p>
          <pre className="performance-code">
            <code>infra/local/run-silver-load.sh</code>
          </pre>
          <p className="performance-note">
            k6 target: Nginx on port 16000 with upstream proof in the response headers
          </p>
        </article>
      </section>

      <section className="performance-layout">
        <article className="performance-panel">
          <p className="eyebrow">Lab shape</p>
          <h2>What runs in the scale lab</h2>
          <div className="performance-stack">
            <div>
              <strong>Postgres</strong>
              <span>Shared database for every lane</span>
            </div>
            <div>
              <strong>Workload API</strong>
              <span>Direct baseline target on port 15000</span>
            </div>
            <div>
              <strong>Workload API A + B</strong>
              <span>Two-instance fleet for the scale path</span>
            </div>
            <div>
              <strong>Nginx gateway</strong>
              <span>Load-balanced path on port 16000</span>
            </div>
            <div>
              <strong>k6 runner</strong>
              <span>Scenario runner for both quest tiers</span>
            </div>
          </div>
        </article>

        <article className="performance-panel">
          <p className="eyebrow">Proof points</p>
          <h2>What to capture after each run</h2>
          <div className="performance-proof">
            <div>
              <strong>Bronze</strong>
              <p>k6 output with 50 users, p95 latency, and error rate.</p>
            </div>
            <div>
              <strong>Silver</strong>
              <p>docker ps with Nginx plus both workload instances, then k6 output at 200 users.</p>
            </div>
            <div>
              <strong>Success line</strong>
              <p>Keep the scaled path under 3 seconds with a clean error rate.</p>
            </div>
          </div>
        </article>
      </section>
    </div>
  )
}
