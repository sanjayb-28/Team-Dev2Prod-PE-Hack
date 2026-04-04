import { startTransition, useEffect, useState } from 'react'

import HomePage from './pages/HomePage'
import SurfacePage from './pages/SurfacePage'
import WorkspacePage from './pages/WorkspacePage'

type PageName = 'home' | 'workspace' | 'performance' | 'observability' | 'evidence'

const pageMeta: Array<{ page: PageName; label: string; path: string }> = [
  { page: 'home', label: 'Home', path: '/' },
  { page: 'workspace', label: 'Workspace', path: '/workspace' },
  { page: 'performance', label: 'Performance', path: '/performance' },
  { page: 'observability', label: 'Observability', path: '/observability' },
  { page: 'evidence', label: 'Evidence', path: '/evidence' },
]

function pageFromPath(pathname: string): PageName {
  const normalized = pathname.replace(/\/+$/, '') || '/'
  return pageMeta.find((entry) => entry.path === normalized)?.page ?? 'home'
}

function pathForPage(page: PageName) {
  return pageMeta.find((entry) => entry.page === page)?.path ?? '/'
}

function AppNavLink({
  active,
  href,
  label,
  onNavigate,
}: {
  active: boolean
  href: string
  label: string
  onNavigate: () => void
}) {
  return (
    <a
      href={href}
      className={active ? 'site-nav__link site-nav__link--active' : 'site-nav__link'}
      onClick={(event) => {
        event.preventDefault()
        onNavigate()
      }}
    >
      {label}
    </a>
  )
}

function renderPage(page: PageName, onNavigate: (nextPage: PageName) => void) {
  if (page === 'home') {
    return <HomePage onNavigate={onNavigate} />
  }

  if (page === 'workspace') {
    return <WorkspacePage />
  }

  if (page === 'performance') {
    return (
      <SurfacePage
        eyebrow="Performance"
        title="Load, scale, and cache in one readable flow."
        intro="This surface will hold the benchmark story: baseline load, scale-out proof, caching impact, and the bottleneck notes that explain where the service bends first."
        summary="The goal is to present recent results clearly before exposing raw benchmark detail."
        sections={[
          {
            title: 'Scenario summary',
            body: 'Keep baseline, scale-out, and cache scenarios readable from one top summary instead of scattering the load story across logs and screenshots.',
          },
          {
            title: 'Topology view',
            body: 'Show the scale lab setup with the workload fleet, Nginx, Postgres, Redis, and the benchmark runner in a simple visual layout.',
          },
          {
            title: 'Bottleneck notes',
            body: 'Capture what limited throughput, how the team found it, and what changed after the optimization pass.',
          },
        ]}
      />
    )
  }

  if (page === 'observability') {
    return (
      <SurfacePage
        eyebrow="Observability"
        title="Alerts, signals, and logs without the dashboard sprawl."
        intro="This surface will connect golden signals, alert state, remote log access, and the runbook path into one calmer operating view."
        summary="The page should read like a command center, not like a collage of tools."
        sections={[
          {
            title: 'Golden signals',
            body: 'Lead with latency, traffic, errors, and saturation in a clean summary that helps someone orient quickly.',
          },
          {
            title: 'Alert path',
            body: 'Show the active rules, delivery path, and the channel operators would actually use during an incident.',
          },
          {
            title: 'Diagnosis flow',
            body: 'Make it easy to move from alert to logs to runbook so the incident story stays coherent during the demo.',
          },
        ]}
      />
    )
  }

  return (
    <SurfacePage
      eyebrow="Evidence"
      title="Keep submission proof easy to find and easy to trust."
      intro="This page will gather CI, coverage, recovery proof, load-test outputs, dashboard links, and operating notes without forcing judges to hunt through the repository."
      summary="Every submission field should map cleanly to one direct piece of proof."
      sections={[
        {
          title: 'Reliability proof',
          body: 'Link the health check, CI, failure handling, recovery behavior, and fault evidence from one place.',
        },
        {
          title: 'Performance proof',
          body: 'Group benchmark outputs, scale lab topology, caching notes, and the final load numbers into one obvious submission surface.',
        },
        {
          title: 'Operations proof',
          body: 'Point straight to logs, metrics, alerts, dashboards, runbooks, and decision notes with no vague labels.',
        },
      ]}
    />
  )
}

export default function App() {
  const [page, setPage] = useState<PageName>(() => pageFromPath(window.location.pathname))

  function navigate(nextPage: PageName) {
    if (nextPage === page) {
      return
    }

    const nextPath = pathForPage(nextPage)
    window.history.pushState({}, '', nextPath)
    startTransition(() => {
      setPage(nextPage)
    })
    window.scrollTo({ top: 0, behavior: 'auto' })
  }

  useEffect(() => {
    function handlePopState() {
      startTransition(() => {
        setPage(pageFromPath(window.location.pathname))
      })
    }

    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  return (
    <div className="app-shell">
      <header className="site-header">
        <a
          href="/"
          className="site-brand"
          onClick={(event) => {
            event.preventDefault()
            navigate('home')
          }}
        >
          <span className="site-brand__mark" />
          <span>
            <strong>Dev2Prod</strong>
            <small>Operations cockpit</small>
          </span>
        </a>

        <nav className="site-nav" aria-label="Primary">
          {pageMeta.map((entry) => (
            <AppNavLink
              key={entry.page}
              active={entry.page === page}
              href={entry.path}
              label={entry.label}
              onNavigate={() => navigate(entry.page)}
            />
          ))}
        </nav>
      </header>

      <main className="site-main">{renderPage(page, navigate)}</main>
    </div>
  )
}
