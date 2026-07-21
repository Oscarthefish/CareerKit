const MAP: Record<string, { label: string; cls: string }> = {
  confirmed: { label: 'Confirmed', cls: 'badge-green' },
  inferred: { label: 'Inferred', cls: 'badge-yellow' },
  weak: { label: 'Weak', cls: 'badge-red' },
  do_not_use: { label: 'Do not use', cls: 'bg-gray-200 text-gray-600 badge' },
}

export default function ConfidenceBadge({ level }: { level: string }) {
  const cfg = MAP[level] || { label: level, cls: 'badge-gray' }
  return <span className={cfg.cls}>{cfg.label}</span>
}
