import { startTransition, useEffect, useState } from 'react'

import HomePage from './pages/HomePage'
import PerformancePage from './pages/PerformancePage'
import SurfacePage from './pages/SurfacePage'
import WorkspacePage from './pages/WorkspacePage'

type PageName = 'home' | 'workspace' | 'performance' | 'operations'

type InternalNavEntry = { kind: 'internal'; page: PageName; label: string; path: string }
type ExternalNavEntry = { kind: 'external'; label: string; path: string; info?: string }

const pageMeta: InternalNavEntry[] = [
  { kind: 'internal', page: 'home', label: 'Home', path: '/' },
  { kind: 'internal', page: 'workspace', label: 'Workspace', path: '/workspace' },
  { kind: 'internal', page: 'performance', label: 'Performance', path: '/performance' },
  { kind: 'internal', page: 'operations', label: 'Documentation', path: '/operations' },
]

const navEntries: Array<InternalNavEntry | ExternalNavEntry> = [
  ...pageMeta,
  {
    kind: 'external',
    label: 'URL Shortener',
    path: '/shortener/',
    info: 'This is the live demo workload. The platform is broader than this one target, but the cluster stays locked today so the demo remains predictable.',
  },
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

function NavInfo({ label }: { label: string }) {
  const [open, setOpen] = useState(false)

  return (
    <span
      className="nav-info"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="nav-info__trigger"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        i
      </button>
      {open ? <span className="nav-info__panel">{label}</span> : null}
    </span>
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
    return <PerformancePage />
  }

  return (
    <SurfacePage
      eyebrow="Documentation"
      title="Keep the platform architecture, operating model, and product story in one place."
      intro="This page explains how the product is structured, how the main surfaces relate to one another, and what the platform is designed to make visible."
      summary="Use this area to document the platform itself: the architecture, the user model, and the core ideas behind the workspace, performance, and workload surfaces."
      sections={[
        {
          title: 'Architecture',
          body: 'Dev2Prod is organized around a client shell, a control plane, and a live application surface. The client keeps the operating picture readable, while the control plane gathers state, starts experiments, and returns the resulting evidence.',
        },
        {
          title: 'Operating model',
          body: 'Workspace focuses on controlled faults and recovery, Performance focuses on scale and cache behavior, and Documentation explains how the product is shaped. Each surface stays narrow so the platform remains easy to read.',
        },
        {
          title: 'Product story',
          body: 'The product is built to help operators understand application behavior under pressure. Instead of scattering signals across dashboards, terminals, and notes, Dev2Prod keeps the story of stress, recovery, and scale in one place.',
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
            <small>Cluster resilience workspace</small>
          </span>
        </a>

        <nav className="site-nav" aria-label="Primary">
          {navEntries.map((entry) =>
            entry.kind === 'internal' ? (
              <AppNavLink
                key={entry.page}
                active={entry.page === page}
                href={entry.path}
                label={entry.label}
                onNavigate={() => navigate(entry.page)}
              />
            ) : (
              <span key={entry.path} className="site-nav__item">
                <a href={entry.path} className="site-nav__link">
                  {entry.label}
                </a>
                {entry.info ? <NavInfo label={entry.info} /> : null}
              </span>
            ),
          )}
        </nav>
      </header>

      <main className="site-main">{renderPage(page, navigate)}</main>
    </div>
  )
}
