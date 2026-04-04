import { startTransition, useEffect, useState } from 'react'

import { createScaleRun, fetchScaleLab } from '../control-plane'
import type { ScaleLabLane, ScaleLabRun, ScaleLabSnapshot } from '../types'

type RequestState = 'loading' | 'ready' | 'error'
type ActionState = 'idle' | 'running' | 'success' | 'error'

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
      <section className="performance-hero">
        <div className="section-heading">
          <p className="eyebrow">Performance</p>
          <h1>Run baseline and scale-out checks from the cluster.</h1>
          <p>
            The scale lab can switch the workload between one and two replicas, launch a
            benchmark run, and report the result back into this surface.
          </p>
        </div>

        <div className="performance-hero__summary">
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
              <dt>Latest run</dt>
              <dd>{latestRun ? latestRun.label : 'No benchmark run yet'}</dd>
            </div>
          </dl>
        </div>
      </section>

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

      <section className="performance-grid">
        {(snapshot?.lanes ?? []).map((lane) => {
          const run = currentLaneRun(snapshot?.runs ?? [], lane)
          return (
            <article key={lane.id} className="performance-panel">
              <p className="eyebrow">{lane.label}</p>
              <h2>{lane.concurrency} concurrent users</h2>
              <p>{lane.description}</p>
              <dl className="performance-lane-stats">
                <div>
                  <dt>Replicas</dt>
                  <dd>{lane.replicas}</dd>
                </div>
                <div>
                  <dt>Duration</dt>
                  <dd>{lane.durationSeconds}s</dd>
                </div>
                <div>
                  <dt>Latest status</dt>
                  <dd className={`resource-list__status resource-list__status--${toneForRun(run?.status ?? 'quiet')}`}>
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

      <section className="performance-layout">
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
                <dt>P95 latency</dt>
                <dd>{latestRun.summary.p95LatencyMs} ms</dd>
              </div>
              <div>
                <dt>Average latency</dt>
                <dd>{latestRun.summary.avgLatencyMs} ms</dd>
              </div>
              <div>
                <dt>Error rate</dt>
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
      </section>
    </div>
  )
}
