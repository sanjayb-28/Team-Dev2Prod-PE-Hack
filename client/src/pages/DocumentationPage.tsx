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
    </div>
  )
}
