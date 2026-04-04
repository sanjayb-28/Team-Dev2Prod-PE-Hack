interface SurfaceSection {
  title: string
  body: string
}

interface SurfacePageProps {
  eyebrow: string
  title: string
  intro: string
  summary: string
  sections: SurfaceSection[]
}

export default function SurfacePage({
  eyebrow,
  title,
  intro,
  summary,
  sections,
}: SurfacePageProps) {
  return (
    <div className="surface-page">
      <section className="surface-page__hero">
        <div className="section-heading">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{intro}</p>
        </div>
        <p className="surface-page__summary">{summary}</p>
      </section>

      <section className="surface-page__grid">
        {sections.map((section) => (
          <article key={section.title} className="surface-panel">
            <strong>{section.title}</strong>
            <p>{section.body}</p>
          </article>
        ))}
      </section>
    </div>
  )
}
