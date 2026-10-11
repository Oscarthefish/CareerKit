interface Props {
  title: string
  description?: string
  action?: React.ReactNode
  icon?: React.ReactNode
}

export default function EmptyState({ title, description, action, icon }: Props) {
  return (
    <div className="text-center py-14 px-6">
      {icon && <div className="mb-4 flex justify-center text-brand-400">{icon}</div>}
      <h3 className="text-section-heading mb-1.5">{title}</h3>
      {description && <p className="text-supporting max-w-sm mx-auto mb-5">{description}</p>}
      {action}
    </div>
  )
}
