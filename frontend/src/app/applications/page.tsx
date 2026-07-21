'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import { getApplications, deleteApplication } from '@/lib/api'
import type { JobApplicationSummary } from '@/lib/types'

const STATUS_COLORS: Record<string, string> = {
  draft: 'badge-gray',
  applied: 'badge-blue',
  interviewing: 'badge-purple',
  offered: 'badge-green',
  rejected: 'badge-red',
  withdrawn: 'badge-gray',
}

const FIT_COLORS: Record<string, string> = {
  strong: 'text-green-700',
  good: 'text-blue-700',
  stretch: 'text-yellow-700',
  weak: 'text-red-700',
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
    if (!confirm('Delete this application?')) return
    await deleteApplication(id)
    setApps(apps.filter((a) => a.id !== id))
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <PageHeader
          title="Job Applications"
          description="Each application is saved as a complete session with CV notes, cover letter, and interview prep."
          action={
            <Link href="/applications/new" className="btn-primary">New Application</Link>
          }
        />

        {/* Filters */}
        <div className="flex items-center gap-2 mb-6">
          {['all', 'draft', 'applied', 'interviewing', 'offered', 'rejected'].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === status
                  ? 'bg-brand-700 text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-brand-300'
              }`}
            >
              {status === 'all' ? `All (${apps.length})` : `${status} (${apps.filter((a) => a.status === status).length})`}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-gray-400 text-sm">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="card p-12 text-center">
            <div className="text-4xl mb-4">◷</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No applications yet</h2>
            <p className="text-sm text-gray-500 mb-6">
              Start by pasting or uploading a job description.
            </p>
            <Link href="/applications/new" className="btn-primary">Start New Application</Link>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((app) => (
              <Link
                key={app.id}
                href={`/applications/${app.id}`}
                className="card flex items-center justify-between px-5 py-4 hover:border-brand-200 transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-sm font-semibold text-gray-900 truncate">
                      {app.role || 'Unknown Role'}
                      {app.company ? <span className="text-gray-500 font-normal"> at {app.company}</span> : null}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    {app.location && <span>{app.location}</span>}
                    {app.work_type && <span>· {app.work_type}</span>}
                    <span>· {new Date(app.created_at).toLocaleDateString('en-NZ')}</span>
                  </div>
                  {/* Progress indicators */}
                  <div className="flex items-center gap-1.5 mt-2">
                    <Pip active={app.has_analysis} label="Analysis" />
                    <Pip active={app.has_scorecard} label="Scorecard" />
                    <Pip active={app.has_cover_letter} label="Cover Letter" />
                    <Pip active={app.has_interview_prep} label="Interview Prep" />
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <span className={STATUS_COLORS[app.status] || 'badge-gray'}>{app.status}</span>
                  <button
                    onClick={(e) => handleDelete(app.id, e)}
                    className="text-gray-300 hover:text-red-400 text-sm opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    ✕
                  </button>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}

function Pip({ active, label }: { active: boolean; label: string }) {
  return (
    <span title={label} className={`w-2 h-2 rounded-full ${active ? 'bg-green-400' : 'bg-gray-200'}`} />
  )
}
