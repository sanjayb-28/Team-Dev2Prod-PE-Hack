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
    body: 'Start a controlled fault, follow the active target, and watch the system move back toward a steady state.',
    page: 'workspace' as const,
    tone: 'teal',
  },
  {
    title: 'Performance',
    body: 'Compare baseline, scale-out, and cache behavior in one place without digging through raw benchmark output.',
    page: 'performance' as const,
    tone: 'blue',
  },
  {
    title: 'Documentation',
    body: 'Keep the platform architecture, operating model, and supporting context close without crowding the main workflows.',
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
            <span>Cluster resilience engine</span>
            <span className="landing-hero__headline-fill">for faults, recovery, and scale.</span>
          </h1>
          <p className="landing-hero__intro">
            Run controlled disruptions, compare cluster behavior under load, and keep the
            operating picture readable while the system is under pressure. Dev2Prod keeps
            fault testing, recovery signals, and scale evidence in one operating surface.
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
          </div>
        </div>

        <aside className="landing-hero__rail" aria-label="Live environment">
          <div className="landing-hero__rail-header">
            <p className="eyebrow">Active cluster</p>
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
              <dt>Scope</dt>
              <dd>Live cluster with one guarded fault path enabled</dd>
            </div>
            <div>
              <dt>Focus</dt>
              <dd>Cluster failure testing, recovery, and scale verification</dd>
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
          <h2>Three focused surfaces around one cluster operating picture.</h2>
          <p>
            Each surface carries one job, keeps the next action obvious, and stays anchored
            to the same live cluster state.
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
          <h2>Built to make cluster behavior legible before production does it for you.</h2>
        </div>

        <div className="detail-columns">
          <div>
            <strong>Controlled disruption</strong>
            <p>
              Start a fault on purpose, keep the target clear, and follow the cluster
              recovery path without losing the surrounding system context.
            </p>
          </div>
          <div>
            <strong>Performance in context</strong>
            <p>
              Benchmarks, scale-out, and cache behavior should read like one coherent
              cluster story, not like a wall of terminal output.
            </p>
          </div>
          <div>
            <strong>General operating model</strong>
            <p>
              The live environment stays tightly scoped today, but the platform model is
              broader: observe, stress, and verify cluster behavior in one place.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
