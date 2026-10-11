interface Props {
  title: string
  description?: string
  action?: React.ReactNode
}

// Lighter-weight than PageHeader - for a sub-section within a page that
// shouldn't be wrapped in another nested card to establish hierarchy.
// Whitespace + heading + optional divider does the job instead.
export default function SectionHeader({ title, description, action }: Props) {
  return (
    <div className="flex items-start justify-between gap-4 mb-3">
      <div>
        <h2 className="text-section-heading">{title}</h2>
        {description && <p className="text-supporting mt-0.5">{description}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}
