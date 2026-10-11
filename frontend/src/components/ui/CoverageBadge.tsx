import type { Coverage } from '@/lib/types'

// Real coverage states only - matches the backend's own vocabulary exactly
// (services/matching/scoring.py: COVERAGE_ICON / COVERAGE_LABEL). Icon shape
// + text label together, never colour alone, per accessibility guidance.
const COVERAGE_META: Record<Coverage, { icon: string; label: string; className: string }> = {
  STRONG_EVIDENCE: { icon: '●', label: 'Strong evidence', className: 'badge-success' },
  PARTIAL_EVIDENCE: { icon: '◐', label: 'Partial evidence', className: 'badge-warning' },
  NO_EVIDENCE: { icon: '○', label: 'No evidence found', className: 'badge-neutral' },
  UNKNOWN: { icon: '?', label: "Can't determine", className: 'badge-neutral' },
}

export default function CoverageBadge({ coverage, className = '' }: { coverage: Coverage; className?: string }) {
  const meta = COVERAGE_META[coverage] ?? COVERAGE_META.UNKNOWN
  return (
    <span className={`${meta.className} ${className}`}>
      <span aria-hidden="true">{meta.icon}</span> {meta.label}
    </span>
  )
}
