const primaryVideo = {
  title: 'Main platform demo',
  description:
    'Start here for the shortest complete walkthrough of the product story, the live workload, and the operator-facing surfaces.',
  embedUrl: 'https://www.youtube.com/embed/gQ3E-KkvFGY',
  href: 'https://youtu.be/gQ3E-KkvFGY',
}

const supportingVideos = [
  {
    title: 'Reliability walkthrough',
    description:
      'Shows the Workspace fault flow, recovery watch, and the evidence attached to a live drill.',
    embedUrl: 'https://www.loom.com/embed/01e5d8258899486aa2f99ba0d7240f06',
    href: 'https://www.loom.com/share/01e5d8258899486aa2f99ba0d7240f06',
  },
  {
    title: 'Scalability walkthrough',
    description:
      'Covers the scale-out lane, runtime behavior under load, and how the result is surfaced in Performance.',
    embedUrl: 'https://www.loom.com/embed/6b63bbf844cd486b8ce725fb08069581',
    href: 'https://www.loom.com/share/6b63bbf844cd486b8ce725fb08069581',
  },
]

const documentationGroups = [
  {
    eyebrow: 'Start here',
    title: 'Core platform docs',
    links: [
      {
        title: 'Repository README',
        body: 'Top-level product framing, live demo links, architecture, and the main repo entry point.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/README.md',
      },
      {
        title: 'Platform narrative',
        body: 'Why the platform exists, what is in scope today, and where the control plane is headed.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/platform.md',
      },
      {
        title: 'GitHub repository',
        body: 'Browse the codebase, workflows, docs, and delivery path in one place.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack',
      },
    ],
  },
  {
    eyebrow: 'Quest docs',
    title: 'Reliability and scalability',
    links: [
      {
        title: 'Reliability',
        body: 'Fault drills, recovery flow, tier mapping, and failure behavior explained clearly.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/reliability.md',
      },
      {
        title: 'Scalability',
        body: 'Benchmark lanes, cache behavior, scale-out design, and the bottleneck story.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/scalability.md',
      },
      {
        title: 'Capacity plan',
        body: 'Measured baseline, scale-out, and cache-burst results with the limits called out directly.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/capacity-plan.md',
      },
    ],
  },
  {
    eyebrow: 'Technical reference',
    title: 'Operate and inspect',
    links: [
      {
        title: 'API docs',
        body: 'Reference workload and control-plane endpoints, plus example requests and responses.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/api.md',
      },
      {
        title: 'Deploy guide',
        body: 'Release flow, rollback steps, required secrets, and post-rollback verification.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/deploy.md',
      },
      {
        title: 'Decision log',
        body: 'The practical tradeoffs behind Redis, Nginx, Chaos Mesh, PostgreSQL pooling, and client scope.',
        href: 'https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack/blob/main/docs/decision-log.md',
      },
    ],
  },
]

type ContributorLinkKind = 'linkedin' | 'website' | 'github'

type Contributor = {
  name: string
  links: Array<{
    label: string
    href: string
    kind: ContributorLinkKind
  }>
}

const contributors: Contributor[] = [
  {
    name: 'Sanjay Baskaran',
    links: [
      { label: 'LinkedIn', href: 'https://www.linkedin.com/in/sanjayb-28/', kind: 'linkedin' },
      { label: 'Website', href: 'https://sanjaybaskaran.dev', kind: 'website' },
      { label: 'GitHub', href: 'https://github.com/sanjayb-28', kind: 'github' },
    ],
  },
  {
    name: 'Rahul Kanagaraj',
    links: [
      {
        label: 'LinkedIn',
        href: 'https://www.linkedin.com/in/rahulkanagaraj/',
        kind: 'linkedin',
      },
      { label: 'Website', href: 'https://rahul-kanagaraj.vercel.app/', kind: 'website' },
      { label: 'GitHub', href: 'https://github.com/rahulkanagaraj786', kind: 'github' },
    ],
  },
]

function SocialIcon({ kind }: { kind: ContributorLinkKind }) {
  if (kind === 'linkedin') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6.94 8.5H3.56V20h3.38V8.5Zm.22-3.56c0-1.08-.82-1.94-1.91-1.94s-1.91.86-1.91 1.94c0 1.07.82 1.94 1.9 1.94h.01c1.1 0 1.91-.87 1.91-1.94ZM20 12.86c0-3.47-1.85-5.08-4.32-5.08-1.99 0-2.88 1.1-3.38 1.88V8.5H8.94c.04.77 0 11.5 0 11.5h3.38v-6.42c0-.34.03-.68.12-.92.27-.68.89-1.38 1.93-1.38 1.36 0 1.9 1.04 1.9 2.57V20H20v-7.14Z" />
      </svg>
    )
  }

  if (kind === 'github') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2C6.48 2 2 6.6 2 12.26c0 4.52 2.87 8.35 6.84 9.7.5.1.68-.22.68-.49 0-.24-.01-1.04-.02-1.89-2.78.62-3.37-1.21-3.37-1.21-.46-1.2-1.11-1.52-1.11-1.52-.9-.63.07-.62.07-.62 1 .08 1.52 1.04 1.52 1.04.88 1.55 2.31 1.1 2.87.84.09-.66.35-1.1.63-1.35-2.22-.26-4.55-1.14-4.55-5.08 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.72 0 0 .84-.28 2.75 1.05A9.3 9.3 0 0 1 12 6.9c.85 0 1.71.12 2.52.36 1.9-1.33 2.74-1.05 2.74-1.05.56 1.42.21 2.46.1 2.72.64.72 1.03 1.63 1.03 2.75 0 3.95-2.34 4.82-4.57 5.07.36.32.68.95.68 1.92 0 1.38-.01 2.49-.01 2.83 0 .27.18.59.69.49A10.26 10.26 0 0 0 22 12.26C22 6.6 17.52 2 12 2Z" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 3h7v7h-2V6.41l-8.3 8.3-1.4-1.42 8.29-8.29H14V3ZM5 5h6v2H7v10h10v-4h2v6H5V5Z" />
    </svg>
  )
}

function VideoCard({
  title,
  description,
  embedUrl,
  href,
  featured = false,
}: {
  title: string
  description: string
  embedUrl: string
  href: string
  featured?: boolean
}) {
  return (
    <article
      className={featured ? 'documentation-video documentation-video--featured' : 'documentation-video'}
    >
      <div className="documentation-video__media">
        <iframe
          src={embedUrl}
          title={title}
          loading="lazy"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          referrerPolicy="strict-origin-when-cross-origin"
          allowFullScreen
        />
      </div>
      <div className="documentation-video__copy">
        <p className="eyebrow">{featured ? 'Featured walkthrough' : 'Supporting walkthrough'}</p>
        <h2>{title}</h2>
        <p>{description}</p>
        <a className="button" href={href} target="_blank" rel="noreferrer">
          Open video
        </a>
      </div>
    </article>
  )
}

export default function DocumentationPage() {
  return (
    <div className="documentation-page">
      <section className="performance-hero documentation-hero">
        <div className="section-heading">
          <p className="eyebrow">Documentation</p>
          <h1>One place for the platform story, technical docs, and demo walkthroughs.</h1>
          <p>
            This page collects the shortest path through Dev2Prod: watch the main demo, inspect the
            repo, and jump straight into the documents that explain how the platform is built and
            why it behaves the way it does.
          </p>
        </div>

        <div className="performance-hero__summary documentation-hero__summary">
          <div className="presence presence--live">
            <span className="presence__dot" />
            Documentation hub
          </div>

          <dl className="performance-stats">
            <div>
              <dt>Watch first</dt>
              <dd>Main platform demo</dd>
            </div>
            <div>
              <dt>Read next</dt>
              <dd>README and platform docs</dd>
            </div>
            <div>
              <dt>Repo</dt>
              <dd>Source, workflows, and manuals</dd>
            </div>
          </dl>

          <div className="documentation-hero__actions">
            <a
              className="button button--primary"
              href="https://youtu.be/gQ3E-KkvFGY"
              target="_blank"
              rel="noreferrer"
            >
              Watch main demo
            </a>
            <a
              className="button"
              href="https://github.com/sanjayb-28/Team-Dev2Prod-PE-Hack"
              target="_blank"
              rel="noreferrer"
            >
              Open GitHub repo
            </a>
          </div>
        </div>
      </section>

      <section className="documentation-section documentation-section--videos">
        <header className="performance-section__header">
          <div className="section-heading">
            <p className="eyebrow">Watch</p>
            <h2>Main demo and supporting walkthroughs</h2>
            <p>
              Start with the full platform walkthrough, then jump into the focused reliability and
              scalability recordings if you want the shorter proof paths.
            </p>
          </div>
        </header>

        <div className="documentation-video-stack">
          <VideoCard {...primaryVideo} featured />

          <div className="documentation-video-grid">
            {supportingVideos.map((video) => (
              <VideoCard key={video.title} {...video} />
            ))}
          </div>
        </div>
      </section>

      <section className="documentation-section">
        <header className="performance-section__header">
          <div className="section-heading">
            <p className="eyebrow">Read</p>
            <h2>Direct links to the docs that matter most</h2>
            <p>
              These links go straight to the repo pages that explain the platform, the two quest
              tracks, the operational model, and the measured runtime story.
            </p>
          </div>
        </header>

        <div className="documentation-groups">
          {documentationGroups.map((group) => (
            <section key={group.title} className="documentation-group">
              <div className="documentation-group__header">
                <p className="eyebrow">{group.eyebrow}</p>
                <h3>{group.title}</h3>
              </div>

              <div className="documentation-link-grid">
                {group.links.map((link) => (
                  <a
                    key={link.title}
                    className="documentation-link-card"
                    href={link.href}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span className="documentation-link-card__eyebrow">Open doc</span>
                    <strong>{link.title}</strong>
                    <p>{link.body}</p>
                  </a>
                ))}
              </div>
            </section>
          ))}
        </div>
      </section>

      <section className="documentation-section">
        <header className="performance-section__header">
          <div className="section-heading">
            <p className="eyebrow">People</p>
            <h2>Contributors</h2>
            <p>
              Direct links to the contributors behind Dev2Prod, including their LinkedIn, personal
              sites, and GitHub profiles.
            </p>
          </div>
        </header>

        <div className="documentation-contributors">
          {contributors.map((contributor) => (
            <article key={contributor.name} className="documentation-contributor-card">
              <div className="documentation-contributor-card__header">
                <strong>{contributor.name}</strong>
              </div>

              <div className="documentation-contributor-card__links">
                {contributor.links.map((link) => (
                  <a
                    key={link.label}
                    className="documentation-contributor-card__link"
                    href={link.href}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span className="documentation-contributor-card__icon">
                      <SocialIcon kind={link.kind} />
                    </span>
                    <span>{link.label}</span>
                  </a>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
