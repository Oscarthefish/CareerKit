'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import JobStatus from '@/components/ui/JobStatus'
import { MatchChip } from '@/components/ui/MatchIndicator'
import EmptyState from '@/components/ui/EmptyState'
import SkeletonBlock from '@/components/ui/Skeleton'
import { JobsIcon } from '@/components/ui/Icons'
import { getProfile, getApplications, aiHealth } from '@/lib/api'
import type { Profile, JobApplicationSummary, AIHealth } from '@/lib/types'

const OPEN_STATUSES = ['draft', 'applied', 'interviewing']

export default function Home() {
  const router = useRouter()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [applications, setApplications] = useState<JobApplicationSummary[]>([])
  const [ai, setAi] = useState<AIHealth | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getProfile().then((r: any) => setProfile(r)).catch(() => null),
      getApplications().then((r: any) => setApplications(r)).catch(() => []),
      aiHealth().then((r: any) => setAi(r)).catch(() => null),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!loading && profile && !profile.setup_complete) {
      router.push('/setup')
    }
  }, [loading, profile, router])

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto px-6 py-8">
          <SkeletonBlock rows={4} />
        </div>
      </AppShell>
    )
  }

  const openApps = applications.filter((a) => OPEN_STATUSES.includes(a.status))
  const firstName = profile?.full_name?.split(' ')[0]

  // Real, computable "needs attention" signals only - never invented ones
  // the data model can't actually support (e.g. no interview date field
  // exists, so no "interview in 2 days" claim is made).
  const needsAnalysis = applications.filter((a) => OPEN_STATUSES.includes(a.status) && !a.has_analysis)
  const readyToMatch = applications.filter((a) => a.has_analysis && !a.has_job_match)
  const needsInterviewPrep = applications.filter((a) => a.status === 'interviewing' && !a.has_interview_prep)
  const attention = [
    ...needsInterviewPrep.map((a) => ({ app: a, action: 'Prepare for interview', tab: 'Interview Prep' })),
    ...readyToMatch.map((a) => ({ app: a, action: 'See how you match', tab: 'Job Match' })),
    ...needsAnalysis.map((a) => ({ app: a, action: 'Analyse this job', tab: 'Job Analysis' })),
  ].slice(0, 5)

  const stateLine = applications.length === 0
    ? 'Add your first job to get started.'
    : `${openApps.length} ${openApps.length === 1 ? 'application' : 'applications'} in progress${attention.length ? ` · ${attention.length} need${attention.length === 1 ? 's' : ''} your attention` : ''}.`

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-page-title">{firstName ? `Welcome back, ${firstName}` : 'Welcome back'}</h1>
            <p className="text-supporting mt-1">{stateLine}</p>
          </div>
          <Link href="/applications/new" className="btn-primary flex-shrink-0">+ Add job</Link>
        </div>

        {/* AI status */}
        {ai && (ai.status !== 'ok' || !ai.model_available) && (
          <div className="mb-6 p-4 rounded-xl text-sm" style={{ background: 'var(--warning-bg)', border: '1px solid var(--warning-border)' }}>
            <p className="font-medium" style={{ color: 'var(--warning-text)' }}>Ollama is not running or the model is not loaded</p>
            <p className="mt-1" style={{ color: 'var(--warning-text)' }}>
              Start Ollama with: <code className="bg-white/60 px-1.5 py-0.5 rounded font-mono text-xs">ollama serve</code>
              {' '}then load your model: <code className="bg-white/60 px-1.5 py-0.5 rounded font-mono text-xs">ollama pull {ai.model || 'llama3'}</code>
            </p>
            <Link href="/settings" className="underline text-xs mt-1 inline-block" style={{ color: 'var(--warning-text)' }}>Check settings</Link>
          </div>
        )}

        {applications.length === 0 ? (
          <div className="surface">
            <EmptyState
              icon={<JobsIcon width={32} height={32} />}
              title="Your job search starts here"
              description="Add a role you're considering and CareerKit can compare it with your experience, identify genuine gaps, and help prepare your application."
              action={<Link href="/applications/new" className="btn-primary">Add your first job</Link>}
            />
          </div>
        ) : (
          <div className="space-y-8">
            {/* Attention */}
            {attention.length > 0 && (
              <section>
                <h2 className="text-section-heading mb-3">Needs your attention</h2>
                <div className="surface divide-y" style={{ borderColor: 'var(--border-default)' }}>
                  {attention.map(({ app, action }, i) => (
                    <Link
                      key={`${app.id}-${i}`}
                      href={`/applications/${app.id}`}
                      className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-gray-50 transition-colors"
                      style={{ borderColor: 'var(--border-default)' }}
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {app.role || 'Untitled role'}{app.company ? ` · ${app.company}` : ''}
                        </p>
                        <p className="text-caption mt-0.5">{action}</p>
                      </div>
                      <span className="text-sm text-brand-700 font-medium flex-shrink-0">Open →</span>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            {/* Active applications */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-section-heading">Active applications</h2>
                <Link href="/applications" className="text-sm text-brand-700 hover:underline">View all</Link>
              </div>
              <div className="surface divide-y" style={{ borderColor: 'var(--border-default)' }}>
                {(openApps.length ? openApps : applications).slice(0, 6).map((app) => (
                  <Link
                    key={app.id}
                    href={`/applications/${app.id}`}
                    className="flex items-center justify-between gap-4 px-5 py-3.5 hover:bg-gray-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {app.role || 'Untitled role'}{app.company ? ` · ${app.company}` : ''}
                      </p>
                      <p className="text-caption mt-0.5">
                        {app.location || 'Location not set'}{app.work_type ? ` · ${app.work_type}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {app.job_match_score != null && <MatchChip score={app.job_match_score} band={app.job_match_band} />}
                      <JobStatus status={app.status} />
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </AppShell>
  )
}
