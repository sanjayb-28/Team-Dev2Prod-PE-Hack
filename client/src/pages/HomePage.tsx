import { useEffect, useState } from 'react'

import { fetchClusterStatus } from '../control-plane'
import type { ClusterStatus } from '../types'

type HomeState = 'loading' | 'ready' | 'error'

type NavigateTarget = 'workspace' | 'performance' | 'observability' | 'evidence'

interface HomePageProps {
  onNavigate: (page: NavigateTarget) => void
}

const capabilityGroups = [
  {
    title: 'Live workspace',
    body: 'Run a fault, watch the workload respond, and inspect the proof without dropping into kubectl first.',
    page: 'workspace' as const,
  },
  {
    title: 'Performance view',
    body: 'Track scale tests, compare scenarios, and keep the load story understandable instead of burying it in raw output.',
    page: 'performance' as const,
  },
  {
    title: 'Observability view',
    body: 'Bring alerts, golden signals, logs, and runbooks into one operating surface.',
    page: 'observability' as const,
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

function HeroIllustration() {
  return (
    <svg
      className="hero-visual"
      viewBox="0 0 640 520"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="44" y="68" width="552" height="384" rx="28" className="hero-visual__frame" />
      <path
        d="M96 164H544"
        className="hero-visual__line hero-visual__line--strong"
        strokeLinecap="round"
      />
      <path d="M96 210H476" className="hero-visual__line" strokeLinecap="round" />
      <path d="M96 246H404" className="hero-visual__line" strokeLinecap="round" />
      <rect x="96" y="300" width="164" height="104" rx="18" className="hero-visual__panel" />
      <rect x="286" y="300" width="118" height="104" rx="18" className="hero-visual__panel" />
      <rect x="430" y="300" width="114" height="104" rx="18" className="hero-visual__panel" />
      <path d="M146 352L178 326L214 368L244 316" className="hero-visual__accent" />
      <path d="M318 374H372" className="hero-visual__line hero-visual__line--strong" strokeLinecap="round" />
      <path d="M454 326H518" className="hero-visual__line hero-visual__line--strong" strokeLinecap="round" />
      <circle cx="488" cy="364" r="18" className="hero-visual__signal" />
      <circle cx="538" cy="120" r="38" className="hero-visual__orb hero-visual__orb--warm" />
      <circle cx="122" cy="116" r="24" className="hero-visual__orb hero-visual__orb--cool" />
      <path d="M516 124H560" className="hero-visual__accent" strokeLinecap="round" />
      <path d="M122 92V140" className="hero-visual__accent" strokeLinecap="round" />
    </svg>
  )
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
          <h1>One operating surface for resilience, scale, and response.</h1>
          <p className="landing-hero__intro">
            Dev2Prod keeps one service understandable under stress. Run guided failures,
            follow recovery, review load behavior, and step into observability without
            switching mental models.
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
          <HeroIllustration />
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
          <h2>Three focused views, one product story.</h2>
          <p>
            The product stays cohesive. Each surface carries one responsibility and keeps
            the next action obvious.
          </p>
        </div>

        <div className="capability-grid">
          {capabilityGroups.map((group) => (
            <button
              key={group.title}
              type="button"
              className="capability-tile"
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
          <h2>Built around one service, not a fake platform.</h2>
        </div>

        <div className="detail-columns">
          <div>
            <strong>Guided fault flow</strong>
            <p>
              Keep the live chaos path intact, but make it readable enough for a judge to
              follow in minutes.
            </p>
          </div>
          <div>
            <strong>Performance as evidence</strong>
            <p>
              Benchmarks, scale-out, and caching should read like proof, not like a wall of
              terminal output.
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
