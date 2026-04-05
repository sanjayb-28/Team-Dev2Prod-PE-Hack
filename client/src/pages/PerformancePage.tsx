import { startTransition, useEffect, useState } from 'react'

import { createScaleRun, fetchScaleLab } from '../control-plane'
import type { ScaleLabLane, ScaleLabRun, ScaleLabSnapshot } from '../types'

type RequestState = 'loading' | 'ready' | 'error'
type ActionState = 'idle' | 'running' | 'success' | 'error'

function InfoHint({ label }: { label: string }) {
  const [open, setOpen] = useState(false)

  return (
    <span
      className="info-hint"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="info-hint__trigger"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        i
      </button>
      {open ? <span className="info-hint__panel">{label}</span> : null}
    </span>
  )
}

function formatUpdatedAt(value: string | undefined) {
  if (!value) {
    return 'Waiting for the first run'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Waiting for the first run'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function formatPercent(value: number | undefined) {
  if (typeof value !== 'number') {
    return 'Waiting'
  }
  return `${(value * 100).toFixed(2)}%`
}

function formatRate(value: number | undefined) {
  if (typeof value !== 'number') {
    return 'Waiting'
  }
  return `${value.toFixed(2)} req/s`
}

function toneForRun(status: string) {
  if (status === 'completed') {
    return 'good'
  }
  if (status === 'running' || status === 'pending') {
    return 'warn'
  }
  if (status === 'failed') {
    return 'bad'
  }
  return 'quiet'
}

function currentLaneRun(runs: ScaleLabRun[], lane: ScaleLabLane) {
  return runs.find((run) => run.lane === lane.id) ?? null
}

function latestRunOutcome(run: ScaleLabRun | null) {
  if (!run?.summary || run.status !== 'completed') {
    return null
  }

  if (run.lane === 'gold-cache-burst') {
    const targetMet = run.summary.errorRate < 0.05
    return {
      tone: targetMet ? 'good' : 'bad',
      label: targetMet ? 'Burst held steady' : 'Error budget missed',
      detail: targetMet
        ? 'The cached burst stayed below the 5% error budget under the heaviest lane.'
        : 'The cached burst crossed the 5% error budget and needs more tuning.',
    }
  }

  if (run.lane === 'silver-scale-out') {
    const targetMet = run.summary.p95LatencyMs < 3000 && run.summary.errorRate < 0.05
    return {
      tone: targetMet ? 'good' : 'bad',
      label: targetMet ? 'Target met' : 'Needs attention',
      detail: targetMet
        ? 'The scale-out lane stayed inside the 3s p95 and 5% error targets.'
        : 'The scale-out lane missed one of its latency or error targets.',
    }
  }

  return {
    tone: 'good',
    label: 'Baseline captured',
    detail: 'The baseline lane finished and recorded a fresh latency sample.',
  }
}

function describeCacheProof(
  cacheProof: ScaleLabSnapshot['cacheProof'],
): { tone: 'good' | 'bad'; label: string; detail: string } | null {
  if (!cacheProof) {
    return null
  }

  if (cacheProof.second === 'HIT' && cacheProof.first === 'MISS') {
    return {
      tone: 'good',
      label: 'Cache warmed on the second request',
      detail: `The first request to ${cacheProof.path} fetched fresh data. The second request reused the stored response, which is the behavior we want under repeated traffic.`,
    }
  }

  if (cacheProof.second === 'HIT' && cacheProof.first === 'HIT') {
    return {
      tone: 'good',
      label: 'Cache was already warm',
      detail: `Both probes to ${cacheProof.path} were served from Redis. That means this path was already cached before the latest check started.`,
    }
  }

  return {
    tone: 'bad',
    label: 'Cache did not settle yet',
    detail: `The platform probes ${cacheProof.path} twice. A healthy read cache should end on a hit, but this path still looks cold or bypassed.`,
  }
}

function performancePresenceState(snapshot: ScaleLabSnapshot | null, state: RequestState) {
  if (state === 'loading') {
    return 'connecting'
  }

  if (state === 'error' || !snapshot?.enabled) {
    return 'offline'
  }

  return 'live'
}

export default function PerformancePage() {
  const [snapshot, setSnapshot] = useState<ScaleLabSnapshot | null>(null)
  const [state, setState] = useState<RequestState>('loading')
  const [actionState, setActionState] = useState<ActionState>('idle')
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [activeLane, setActiveLane] = useState<string | null>(null)

  async function refresh() {
    try {
      const response = await fetchScaleLab()
      startTransition(() => {
        setSnapshot(response.data)
        setState('ready')
      })
    } catch {
      startTransition(() => {
        setState('error')
      })
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  useEffect(() => {
    if (!snapshot?.runs.some((run) => run.status === 'running' || run.status === 'pending')) {
      return
    }

    const interval = window.setInterval(() => {
      void refresh()
    }, 3000)

    return () => {
      window.clearInterval(interval)
    }
  }, [snapshot])

  const latestRun = snapshot?.runs[0] ?? null
  const liveRun = snapshot?.runs.find((run) => run.status === 'running' || run.status === 'pending')
  const runInProgress = Boolean(liveRun)
  const latestOutcome = latestRunOutcome(latestRun)
  const cacheOutcome = describeCacheProof(snapshot?.cacheProof ?? null)
  const presenceState = performancePresenceState(snapshot, state)

  async function handleRun(lane: ScaleLabLane) {
    setActionState('running')
    setActiveLane(lane.id)
    setActionMessage(`Starting ${lane.label.toLowerCase()}.`)

    try {
      const response = await createScaleRun(lane.id)
      await refresh()
      startTransition(() => {
        setActionState('success')
        setActionMessage(`${response.data.label} is running in the cluster.`)
      })
    } catch (error) {
      startTransition(() => {
        setActionState('error')
        setActionMessage(
          error instanceof Error ? error.message : 'The scale lab could not start that run.',
        )
      })
    } finally {
      startTransition(() => {
        setActiveLane(null)
      })
    }
  }

  return (
    <div className="performance-page">
      <header className="workspace-masthead performance-masthead">
        <div className="workspace-masthead__copy">
          <p className="eyebrow">Performance</p>
          <h1>Run baseline, scale-out, and cache-burst checks from the cluster.</h1>
          <p className="workspace-masthead__intro">
            The scale lab can rebalance the workload, launch a benchmark job, and bring
            the latest latency, error-rate, and throughput evidence back into this
            surface.
          </p>
        </div>

        <div className="workspace-masthead__scope performance-masthead__scope">
          <div className={`presence presence--${presenceState}`}>
            <span className="presence__dot" />
            <span>
              {presenceState === 'live'
                ? 'Scale lab live'
                : presenceState === 'connecting'
                  ? 'Connecting'
                  : 'Unavailable'}
            </span>
          </div>
          <dl className="performance-stats">
            <div>
              <dt>Lab mode</dt>
              <dd>{snapshot?.enabled ? 'Live cluster' : state === 'loading' ? 'Loading' : 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Workload scale</dt>
              <dd>
                {snapshot?.workloadScale
                  ? `${snapshot.workloadScale.readyReplicas} / ${snapshot.workloadScale.desiredReplicas} ready`
                  : 'Waiting for cluster data'}
              </dd>
            </div>
            <div>
              <dt>Cache proof</dt>
              <dd>
                {snapshot?.cacheProof
                  ? `${snapshot.cacheProof.first ?? '—'} → ${snapshot.cacheProof.second ?? '—'}`
                  : 'Waiting for cache data'}
              </dd>
            </div>
            <div>
              <dt>Latest run</dt>
              <dd>{latestRun ? latestRun.label : 'No benchmark run yet'}</dd>
            </div>
          </dl>
        </div>
      </header>

      {state === 'error' ? (
        <section className="performance-banner performance-banner--error">
          The performance surface could not reach the scale lab right now.
        </section>
      ) : null}

      {!snapshot?.enabled && state === 'ready' ? (
        <section className="performance-banner">
          Scale runs are only available from the live cluster. The local page can still
          show the layout, but the buttons stay disabled until the control plane is
          running in Kubernetes.
        </section>
      ) : null}

      <section className="performance-section">
        <div className="performance-section__header">
          <div className="section-heading">
            <p className="eyebrow">Run scenarios</p>
            <h2>Choose one benchmark lane at a time.</h2>
            <p>
              Each lane shifts traffic pressure and workload scale in a slightly different
              way, so the latest result reads like one clear performance story.
            </p>
          </div>
        </div>

        <div className="performance-grid">
          {(snapshot?.lanes ?? []).map((lane) => {
            const run = currentLaneRun(snapshot?.runs ?? [], lane)
            const isGoldLane = lane.id === 'gold-cache-burst'
            return (
              <article
                key={lane.id}
                className={
                  isGoldLane
                    ? 'performance-panel performance-panel--spotlight'
                    : 'performance-panel'
                }
              >
                <p className="eyebrow">{lane.label}</p>
                <h2>
                  {lane.concurrency} concurrent users
                  <InfoHint label="Concurrent users are the number of simulated people hitting the app at the same time during this run." />
                </h2>
                <p>{lane.description}</p>
                <dl className="performance-lane-stats">
                  <div>
                    <dt>
                      Replicas
                      <InfoHint label="Replicas are the number of app copies serving traffic during this lane." />
                    </dt>
                    <dd>{lane.replicas}</dd>
                  </div>
                  <div>
                    <dt>Duration</dt>
                    <dd>{lane.durationSeconds}s</dd>
                  </div>
                  <div>
                    <dt>Latest status</dt>
                    <dd
                      className={`resource-list__status resource-list__status--${toneForRun(run?.status ?? 'quiet')}`}
                    >
                      {run ? run.status : 'Waiting'}
                    </dd>
                  </div>
                </dl>
                <button
                  type="button"
                  className="button button--primary"
                  disabled={!snapshot?.enabled || actionState === 'running' || runInProgress}
                  onClick={() => {
                    void handleRun(lane)
                  }}
                >
                  {activeLane === lane.id && actionState === 'running'
                    ? 'Starting run'
                    : runInProgress
                      ? 'Run in progress'
                      : `Run ${lane.label}`}
                </button>
              </article>
            )
          })}
        </div>
      </section>

      {actionMessage ? (
        <section
          className={
            actionState === 'error'
              ? 'performance-banner performance-banner--error'
              : 'performance-banner'
          }
        >
          {actionMessage}
        </section>
      ) : null}

      {runInProgress ? (
        <section className="performance-banner">
          {liveRun?.label ?? 'A scale run'} is active now. This page will keep polling until
          the benchmark pod finishes and the summary lands here.
        </section>
      ) : null}

      <section className="performance-section">
        <div className="performance-section__header">
          <div className="section-heading">
            <p className="eyebrow">Evidence</p>
            <h2>Read the latest impact in one place.</h2>
            <p>
              Cache proof, latest result, and run history stay together so the page feels
              like one operating surface instead of a detached benchmark board.
            </p>
          </div>
        </div>

        <div className="performance-layout">
          <article className="performance-panel">
          <p className="eyebrow">Cache proof</p>
          <h2>
            Read-path cache status
            <InfoHint label="A cache stores a recent response in memory so the app can answer repeated reads faster without going back to the database every time." />
          </h2>
          {cacheOutcome ? (
            <div className={`performance-outcome performance-outcome--${cacheOutcome.tone}`}>
              <strong>
                {snapshot?.cacheProof?.first ?? '—'} → {snapshot?.cacheProof?.second ?? '—'}
              </strong>
              <p>{cacheOutcome.label}</p>
              <p>{cacheOutcome.detail}</p>
            </div>
          ) : (
            <p className="performance-note">
              Cache proof appears here once the live workload responds with cache headers.
            </p>
          )}
          </article>

          <article className="performance-panel">
          <p className="eyebrow">Latest result</p>
          <h2>{latestRun ? latestRun.label : 'Waiting for the first cluster run'}</h2>
          {latestOutcome ? (
            <div className={`performance-outcome performance-outcome--${latestOutcome.tone}`}>
              <strong>{latestOutcome.label}</strong>
              <p>{latestOutcome.detail}</p>
            </div>
          ) : null}
          {latestRun?.summary ? (
            <dl className="performance-result-grid">
              <div>
                <dt>
                  P95 latency
                  <InfoHint label="P95 latency is the response time that 95% of requests stay under. It is a better stress signal than a simple average." />
                </dt>
                <dd>{latestRun.summary.p95LatencyMs} ms</dd>
              </div>
              <div>
                <dt>Average latency</dt>
                <dd>{latestRun.summary.avgLatencyMs} ms</dd>
              </div>
              <div>
                <dt>
                  Error rate
                  <InfoHint label="Error rate is the share of requests that failed during the run. Lower is better." />
                </dt>
                <dd>{formatPercent(latestRun.summary.errorRate)}</dd>
              </div>
              <div>
                <dt>Requests</dt>
                <dd>{latestRun.summary.requestCount}</dd>
              </div>
              <div>
                <dt>Throughput</dt>
                <dd>{formatRate(latestRun.summary.requestRatePerSecond)}</dd>
              </div>
            </dl>
          ) : (
            <p className="performance-note">
              Completed runs show latency and error-rate numbers here once the benchmark
              pod finishes and the control plane reads the summary.
            </p>
          )}
          </article>

          <article className="performance-panel">
          <p className="eyebrow">Run history</p>
          <h2>Recent benchmark runs</h2>
          <div className="performance-proof">
            {(snapshot?.runs ?? []).length === 0 ? (
              <p>No runs yet.</p>
            ) : (
              snapshot?.runs.map((run) => (
                <div key={run.name}>
                  <strong>{run.label}</strong>
                  <p>
                    {run.concurrency} users • {run.replicas} replicas • {run.status} •{' '}
                    {formatUpdatedAt(run.createdAt)}
                  </p>
                  {run.summary ? (
                    <p>
                      P95 {run.summary.p95LatencyMs} ms • {formatPercent(run.summary.errorRate)}{' '}
                      errors • {formatRate(run.summary.requestRatePerSecond)}
                    </p>
                  ) : null}
                </div>
              ))
            )}
          </div>
          </article>
        </div>
      </section>
    </div>
  )
}
