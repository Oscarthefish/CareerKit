const MAP: Record<string, { label: string; cls: string }> = {
  confirmed_hands_on: { label: 'Confirmed hands-on', cls: 'badge-green' },
  working_knowledge: { label: 'Working knowledge', cls: 'badge-green' },
  training_exposure: { label: 'Training exposure', cls: 'badge-yellow' },
  familiarity: { label: 'Familiarity', cls: 'badge-yellow' },
  interest: { label: 'Interest / planned', cls: 'badge-gray' },
  unverified: { label: 'Unverified', cls: 'badge-red' },
  do_not_include: { label: 'Do not include', cls: 'bg-gray-200 text-gray-600 badge' },
  // legacy values, kept so older records still render sensibly
  confirmed: { label: 'Confirmed', cls: 'badge-green' },
  inferred: { label: 'Inferred', cls: 'badge-yellow' },
  weak: { label: 'Weak', cls: 'badge-red' },
  do_not_use: { label: 'Do not use', cls: 'bg-gray-200 text-gray-600 badge' },
}

export default function ConfidenceBadge({ level }: { level: string }) {
  const cfg = MAP[level] || { label: level, cls: 'badge-gray' }
  return <span className={cfg.cls}>{cfg.label}</span>
}
