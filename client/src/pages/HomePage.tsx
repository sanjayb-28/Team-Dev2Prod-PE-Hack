import { useEffect, useState } from 'react'

import { fetchClusterStatus } from '../control-plane'
import type { ClusterStatus } from '../types'

type HomeState = 'loading' | 'ready' | 'error'

type NavigateTarget = 'workspace' | 'performance' | 'operations'

interface HomePageProps {
  onNavigate: (page: NavigateTarget) => void
}

const capabilityGroups = [
  {
    title: 'Workspace',
    body: 'Run a controlled fault, follow the active target, and watch the system settle back into shape.',
    page: 'workspace' as const,
    tone: 'teal',
  },
  {
    title: 'Performance',
    body: 'Compare baseline, scale-out, and cache behavior in one place without burying the story in raw load output.',
    page: 'performance' as const,
    tone: 'blue',
  },
  {
    title: 'Operations',
    body: 'Keep the supporting notes, references, and platform context close without crowding the main workflows.',
    page: 'operations' as const,
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
          <h1 className="landing-hero__headline">
            <span>Follow application behavior</span>
            <span className="landing-hero__headline-fill">from fault drills to scale checks.</span>
          </h1>
          <p className="landing-hero__intro">
            Keep the live platform readable while it is being stressed, scaled, and recovered.
            The current demo is pinned to one guarded cluster target today, but the product
            model is broader than this single path.
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
              onClick={() => onNavigate('performance')}
            >
              Open performance
            </button>
            <a
              className="button"
              href="/shortener/"
            >
              Open shortener
            </a>
          </div>
        </div>

        <aside className="landing-hero__rail" aria-label="Live environment">
          <div className="landing-hero__rail-header">
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

          <dl className="landing-hero__facts">
            <div>
              <dt>Current demo</dt>
              <dd>One guarded target in one live cluster</dd>
            </div>
            <div>
              <dt>Focus</dt>
              <dd>Fault drills, recovery, and scale checks</dd>
            </div>
            <div>
              <dt>Mode</dt>
              <dd>{state === 'ready' ? 'Live environment' : 'Status loading'}</dd>
            </div>
          </dl>
        </aside>
      </section>

      <section className="capability-band">
        <div className="section-heading">
          <p className="eyebrow">Core surfaces</p>
          <h2>Three focused surfaces and one live demo workload.</h2>
          <p>
            Each surface carries one job, keeps the next action obvious, and stays anchored
            to the same running system.
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
          <p className="eyebrow">Platform shape</p>
          <h2>Scoped tightly for the demo, but framed like a broader operating product.</h2>
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
            <strong>Locked, not limited</strong>
            <p>
              The current live target is intentionally constrained so the demo stays stable,
              but the product language should still point beyond that guardrail.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
