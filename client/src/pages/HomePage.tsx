import { useEffect, useState } from 'react'

import { fetchClusterStatus } from '../control-plane'
import type { ClusterStatus } from '../types'

type HomeState = 'loading' | 'ready' | 'error'

type NavigateTarget = 'workspace' | 'performance' | 'observability' | 'operations'

interface HomePageProps {
  onNavigate: (page: NavigateTarget) => void
}

const capabilityGroups = [
  {
    title: 'Control room',
    body: 'Run a fault, follow the workload response, and inspect the cluster from one live surface.',
    page: 'workspace' as const,
    tone: 'teal',
  },
  {
    title: 'Load view',
    body: 'Compare baseline, scale-out, and cache runs without burying the story in raw benchmark output.',
    page: 'performance' as const,
    tone: 'blue',
  },
  {
    title: 'Signal view',
    body: 'Bring alerts, golden signals, logs, and runbooks into one calmer operating surface.',
    page: 'observability' as const,
    tone: 'orange',
  },
]

function statusLabel(status: string | undefined) {
  if (!status) {
    return 'Waiting'
  }

  return status.replace(/([A-Z])/g, ' $1').replace(/^./, (value) => value.toUpperCase())
}

function toneForStatus(status?: string) {
  if (status === 'healthy' || status === 'ready' || status === 'active' || status === 'running') {
    return 'good'
  }
  if (status === 'degraded' || status === 'pending') {
    return 'warn'
  }
  if (status === 'unreachable' || status === 'failed' || status === 'unknown') {
    return 'bad'
  }
  return 'quiet'
}

export default function HomePage({ onNavigate }: HomePageProps) {
  const [clusterStatus, setClusterStatus] = useState<ClusterStatus | null>(null)
  const [state, setState] = useState<HomeState>('loading')

  useEffect(() => {
    let cancelled = false

    async function loadStatus() {
      try {
        const response = await fetchClusterStatus()
        if (!cancelled) {
          setClusterStatus(response.data)
          setState('ready')
        }
      } catch {
        if (!cancelled) {
          setState('error')
        }
      }
    }

    loadStatus()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="landing-hero__copy">
          <p className="eyebrow">Dev2Prod</p>
          <h1>Operate one service from fault to steady state.</h1>
          <p className="landing-hero__intro">
            Keep the live service readable while it is being stressed, scaled, or traced.
            The product stays focused on one workload and one clean operating flow.
          </p>
          <div className="landing-hero__actions">
            <button
              type="button"
              className="button button--primary"
              onClick={() => onNavigate('workspace')}
            >
              Open workspace
            </button>
            <button
              type="button"
              className="button"
              onClick={() => onNavigate('observability')}
            >
              View observability
            </button>
          </div>
        </div>

        <div className="landing-hero__visual">
          <img src="/k8s.png" alt="" className="hero-visual-image" />
        </div>
      </section>

      <section className="landing-strip">
        <div>
          <p className="eyebrow">Live environment</p>
          <strong>
            {state === 'ready'
              ? `${clusterStatus?.clusterName} / ${clusterStatus?.namespace}`
              : state === 'error'
                ? 'Status unavailable'
                : 'Loading live status'}
          </strong>
        </div>
        <dl className="status-strip">
          <div>
            <dt>Service</dt>
            <dd className={`status-strip__value status-strip__value--${toneForStatus(clusterStatus?.workload.status)}`}>
              {statusLabel(clusterStatus?.workload.status)}
            </dd>
          </div>
          <div>
            <dt>Control plane</dt>
            <dd className={`status-strip__value status-strip__value--${toneForStatus(clusterStatus?.controlPlane.status)}`}>
              {statusLabel(clusterStatus?.controlPlane.status)}
            </dd>
          </div>
          <div>
            <dt>Fault tooling</dt>
            <dd className={`status-strip__value status-strip__value--${toneForStatus(clusterStatus?.chaosMesh.status)}`}>
              {statusLabel(clusterStatus?.chaosMesh.status)}
            </dd>
          </div>
        </dl>
      </section>

      <section className="capability-band">
        <div className="section-heading">
          <p className="eyebrow">Core surfaces</p>
          <h2>Three focused views, one operating rhythm.</h2>
          <p>
            Each surface carries one job, keeps the next action obvious, and stays connected
            to the same live system.
          </p>
        </div>

        <div className="capability-grid">
          {capabilityGroups.map((group) => (
            <button
              key={group.title}
              type="button"
              className={`capability-tile capability-tile--${group.tone}`}
              onClick={() => onNavigate(group.page)}
            >
              <span className="capability-tile__index">
                0{capabilityGroups.indexOf(group) + 1}
              </span>
              <strong>{group.title}</strong>
              <p>{group.body}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="landing-detail">
        <div className="section-heading">
          <p className="eyebrow">What makes it work</p>
          <h2>Built around one service, not a bloated platform story.</h2>
        </div>

        <div className="detail-columns">
          <div>
            <strong>Guided fault flow</strong>
            <p>
              Keep the live fault path intact, but make it readable enough for someone opening
              the product for the first time.
            </p>
          </div>
          <div>
            <strong>Performance in context</strong>
            <p>
              Benchmarks, scale-out, and caching should read like a clear system story, not
              like a wall of terminal output.
            </p>
          </div>
          <div>
            <strong>Response without clutter</strong>
            <p>
              Logs, alerts, and golden signals belong in one calm surface that stays useful
              under pressure.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
