'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import EmptyState from '@/components/ui/EmptyState'
import SkeletonBlock from '@/components/ui/Skeleton'
import JobStatus, { JOB_STATUSES, statusLabel } from '@/components/ui/JobStatus'
import { MatchChip } from '@/components/ui/MatchIndicator'
import { JobsIcon } from '@/components/ui/Icons'
import { getApplications, deleteApplication } from '@/lib/api'
import type { JobApplicationSummary } from '@/lib/types'

function nextAction(app: JobApplicationSummary): string | null {
  if (!app.has_analysis) return 'Analyse this job'
  if (!app.has_job_match) return 'See how you match'
  if (app.status === 'interviewing' && !app.has_interview_prep) return 'Prepare for interview'
  if (app.status === 'draft' && !app.has_cover_letter) return 'Write a cover letter'
  return null
}

export default function ApplicationsPage() {
  const [apps, setApps] = useState<JobApplicationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  const load = async () => {
    setLoading(true)
    try {
      const data: any = await getApplications()
      setApps(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'all' ? apps : apps.filter((a) => a.status === filter)

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Delete this application? This cannot be undone.')) return
    await deleteApplication(id)
    setApps(apps.filter((a) => a.id !== id))
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <PageHeader
          title="Jobs"
          description="Every role you're considering, with its match and current status."
          action={<Link href="/applications/new" className="btn-primary">+ Add job</Link>}
        />

        {/* Filters */}
        <div className="flex items-center gap-1.5 mb-5 overflow-x-auto">
          {['all', ...JOB_STATUSES].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                filter === status ? 'bg-brand-700 text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {status === 'all' ? `All (${apps.length})` : `${statusLabel(status)} (${apps.filter((a) => a.status === status).length})`}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="surface p-6"><SkeletonBlock rows={4} /></div>
        ) : filtered.length === 0 ? (
          <div className="surface">
            {apps.length === 0 ? (
              <EmptyState
                icon={<JobsIcon width={32} height={32} />}
                title="Your job search starts here"
                description="Add a role you're considering and CareerKit can compare it with your experience, identify genuine gaps, and help prepare your application."
                action={<Link href="/applications/new" className="btn-primary">Add your first job</Link>}
              />
            ) : (
              <EmptyState title="No jobs in this view" description="Try a different filter." />
            )}
          </div>
        ) : (
          <div className="surface divide-y" style={{ borderColor: 'var(--border-default)' }}>
            {filtered.map((app) => {
              const action = nextAction(app)
              return (
                <Link
                  key={app.id}
                  href={`/applications/${app.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">
                      {app.role || 'Untitled role'}
                      {app.company ? <span className="text-gray-500 font-normal"> · {app.company}</span> : null}
                    </p>
                    <div className="flex items-center gap-3 text-caption mt-0.5">
                      {app.location && <span>{app.location}</span>}
                      {app.work_type && <span>· {app.work_type}</span>}
                      <span>· Added {new Date(app.created_at).toLocaleDateString('en-NZ')}</span>
                    </div>
                    {action && <p className="text-xs text-brand-700 font-medium mt-1.5">{action} →</p>}
                  </div>
                  <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                    {app.job_match_score != null && <MatchChip score={app.job_match_score} band={app.job_match_band} />}
                    <JobStatus status={app.status} />
                    <button
                      onClick={(e) => handleDelete(app.id, e)}
                      className="text-gray-300 hover:text-red-500 text-sm opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-label="Delete application"
                    >
                      ✕
                    </button>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </AppShell>
  )
}
