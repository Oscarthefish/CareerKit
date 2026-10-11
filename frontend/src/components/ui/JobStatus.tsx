// Single source of truth for the job status vocabulary. Matches the real
// backend column exactly (backend/app/models/job.py: draft, applied,
// interviewing, offered, rejected, withdrawn) - never invent a status the
// data model doesn't support.
export const JOB_STATUSES = ['draft', 'applied', 'interviewing', 'offered', 'rejected', 'withdrawn'] as const
export type JobStatusValue = (typeof JOB_STATUSES)[number]

const STATUS_META: Record<string, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'badge-neutral' },
  applied: { label: 'Applied', className: 'badge-info' },
  interviewing: { label: 'Interviewing', className: 'badge bg-purple-50 text-purple-700' },
  offered: { label: 'Offer', className: 'badge-success' },
  rejected: { label: 'Rejected', className: 'badge-danger' },
  withdrawn: { label: 'Withdrawn', className: 'badge-neutral' },
}

export function statusLabel(status: string): string {
  return STATUS_META[status]?.label ?? status
}

export default function JobStatus({ status, className = '' }: { status: string; className?: string }) {
  const meta = STATUS_META[status] ?? { label: status, className: 'badge-neutral' }
  return <span className={`${meta.className} ${className}`}>{meta.label}</span>
}
