'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import EmptyState from '@/components/ui/EmptyState'
import SkeletonBlock from '@/components/ui/Skeleton'
import JobStatus, { JOB_STATUSES, statusLabel } from '@/components/ui/JobStatus'
import { MatchChip } from '@/components/ui/MatchIndicator'
import { JobsIcon, ExternalLinkIcon } from '@/components/ui/Icons'
import { safeJobHref, jobLinkHost } from '@/components/ui/JobLink'
import { getApplications, deleteApplication } from '@/lib/api'
import type { JobApplicationSummary } from '@/lib/types'

function nextAction(app: JobApplicationSummary): string | null {
  if (!app.has_analysis) return 'Analyse this job'
  if (!app.has_job_match) return 'See how you match'
  if (app.status === 'interviewing' && !app.has_interview_prep) return 'Prepare for interview'
  if (app.status === 'draft' && !app.has_cover_letter) return 'Write a cover letter'
  return null
}

// "Active" = still in play; rejected and withdrawn jobs are closed.
const CLOSED_STATUSES = ['rejected', 'withdrawn']
const isActive = (a: JobApplicationSummary) => !CLOSED_STATUSES.includes(a.status)
const FILTER_KEY = 'careerkit.jobsFilter'

export default function ApplicationsPage() {
  const [apps, setApps] = useState<JobApplicationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilterState] = useState('active')

  useEffect(() => {
    try {
      const saved = localStorage.getItem(FILTER_KEY)
      if (saved) setFilterState(saved)
    } catch {}
  }, [])

  const setFilter = (f: string) => {
    setFilterState(f)
    try { localStorage.setItem(FILTER_KEY, f) } catch {}
  }

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

  const matches = (a: JobApplicationSummary, f: string) =>
    f === 'all' ? true : f === 'active' ? isActive(a) : a.status === f
  const filtered = apps.filter((a) => matches(a, filter))
  const filterLabel = (f: string) =>
    f === 'all' ? 'All' : f === 'active' ? 'Active' : statusLabel(f)
  const filterButton = (f: string) => {
    const count = apps.filter((a) => matches(a, f)).length
    return (
      <button
        key={f}
        onClick={() => setFilter(f)}
        aria-pressed={filter === f}
        className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
          filter === f
            ? 'bg-brand-700 text-white shadow-sm'
            : count === 0
              ? 'text-gray-400 hover:bg-white'
              : 'text-gray-700 hover:bg-white'
        }`}
      >
        {filterLabel(f)} <span className={filter === f ? 'opacity-80' : 'text-gray-400'}>{count}</span>
      </button>
    )
  }

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
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <span className="text-xs font-medium text-gray-500 mr-1">Show</span>
          <div
            role="group"
            aria-label="Filter jobs"
            className="inline-flex flex-wrap items-center gap-0.5 p-1 rounded-lg"
            style={{ background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-default)' }}
          >
            {filterButton('active')}
            {filterButton('all')}
            <span className="w-px h-4 mx-1 bg-gray-300" aria-hidden="true" />
            {JOB_STATUSES.map(filterButton)}
          </div>
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
              <EmptyState
                title={`No ${filterLabel(filter).toLowerCase()} jobs`}
                description="Try a different filter."
                action={<button onClick={() => setFilter('all')} className="btn-secondary">Show all jobs</button>}
              />
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
                      {safeJobHref(app.job_url) && <span>·</span>}
                      {safeJobHref(app.job_url) && (
                        <button
                          type="button"
                          onClick={(e) => {
                            // The whole row is a <Link>; a nested <a> is invalid HTML,
                            // so open the listing from a button instead.
                            e.preventDefault()
                            e.stopPropagation()
                            window.open(safeJobHref(app.job_url)!, '_blank', 'noopener,noreferrer')
                          }}
                          className="inline-flex items-center gap-1 text-brand-600 hover:underline"
                          title={app.job_url!}
                        >
                          <ExternalLinkIcon width={12} height={12} /> {jobLinkHost(safeJobHref(app.job_url)!)}
                        </button>
                      )}
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
