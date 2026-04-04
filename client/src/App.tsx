import { startTransition, useEffect, useState } from 'react'

import HomePage from './pages/HomePage'
import SurfacePage from './pages/SurfacePage'
import WorkspacePage from './pages/WorkspacePage'

type PageName = 'home' | 'workspace' | 'performance' | 'observability' | 'operations'

const pageMeta: Array<{ page: PageName; label: string; path: string }> = [
  { page: 'home', label: 'Home', path: '/' },
  { page: 'workspace', label: 'Workspace', path: '/workspace' },
  { page: 'performance', label: 'Performance', path: '/performance' },
  { page: 'observability', label: 'Observability', path: '/observability' },
  { page: 'operations', label: 'Operations', path: '/operations' },
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
        title="Baseline load and scale-out in one lab."
        intro="This surface now tracks two concrete lanes: a single-instance baseline and a two-instance scale path behind Nginx."
        summary="The local scale lab is set up to prove a 50-user baseline first, then a 200-user load-balanced run with the same workload."
        sections={[
          {
            title: 'Baseline lane',
            body: 'Run the Bronze path against one workload instance and capture p95 latency plus error rate from the 50-user k6 output.',
          },
          {
            title: 'Scale lane',
            body: 'Run the Silver path through Nginx across two workload instances and confirm the 200-user run stays under the response-time target.',
          },
          {
            title: 'Lab shape',
            body: 'The scale lab now includes Postgres, one baseline workload service, a two-instance workload fleet, one Nginx gateway, and k6 scenarios for both runs.',
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
      eyebrow="Operations"
      title="Keep release, rollback, and reference material close at hand."
      intro="This surface will gather runbooks, deploy notes, environment reference, benchmark outputs, and the links that support day-to-day operating work."
      summary="Everything operational should stay easy to find, easy to scan, and easy to trust."
      sections={[
        {
          title: 'Release notes',
          body: 'Keep deployment, rollback, and environment reference material together so operators do not need to jump between scattered files.',
        },
        {
          title: 'Benchmark records',
          body: 'Group scale lab outputs, cache notes, and recent load summaries into one obvious operating surface.',
        },
        {
          title: 'Reference links',
          body: 'Point straight to logs, metrics, dashboards, runbooks, and key system notes with no vague labels.',
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
          <img src="/favicon.png" alt="" className="site-brand__mark" />
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
