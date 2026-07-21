'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import { getProfile, getApplications, aiHealth } from '@/lib/api'
import type { Profile, JobApplicationSummary, AIHealth } from '@/lib/types'

const STATUS_COLORS: Record<string, string> = {
  draft: 'badge-gray',
  applied: 'badge-blue',
  interviewing: 'badge-purple',
  offered: 'badge-green',
  rejected: 'badge-red',
  withdrawn: 'badge-gray',
}

export default function Dashboard() {
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
        <div className="flex items-center justify-center h-full">
          <div className="text-gray-400">Loading...</div>
        </div>
      </AppShell>
    )
  }

  const recentApps = applications.slice(0, 5)
  const activeApps = applications.filter((a) => ['applied', 'interviewing'].includes(a.status))

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            {profile?.full_name ? `Welcome back, ${profile.full_name.split(' ')[0]}` : 'Dashboard'}
          </h1>
          <p className="mt-1 text-gray-500 text-sm">
            {profile?.target_roles?.length
              ? `Targeting: ${profile.target_roles.slice(0, 3).join(', ')}`
              : 'Set your target roles in your profile'}
          </p>
        </div>

        {/* AI Status Banner */}
        {ai && (ai.status !== 'ok' || !ai.model_available) && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm">
            <p className="font-medium text-amber-800">Ollama is not running or the model is not loaded</p>
            <p className="text-amber-700 mt-1">
              Start Ollama with: <code className="bg-amber-100 px-1.5 py-0.5 rounded font-mono text-xs">ollama serve</code>
              {' '}then load your model: <code className="bg-amber-100 px-1.5 py-0.5 rounded font-mono text-xs">ollama pull {ai.model || 'llama3'}</code>
            </p>
            <Link href="/settings" className="text-amber-800 underline text-xs mt-1 inline-block">
              Check settings
            </Link>
          </div>
        )}

        {/* Quick stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Applications" value={applications.length} href="/applications" />
          <StatCard label="Active" value={activeApps.length} href="/applications" />
          <StatCard label="Interviews" value={applications.filter((a) => a.status === 'interviewing').length} href="/applications" />
          <StatCard label="Offers" value={applications.filter((a) => a.status === 'offered').length} href="/applications" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quick actions */}
          <div className="lg:col-span-1">
            <div className="card">
              <div className="card-header">
                <h2 className="font-semibold text-gray-900 text-sm">Quick Actions</h2>
              </div>
              <div className="card-body space-y-2 p-4">
                <QuickAction href="/applications/new" label="New Job Application" desc="Start a new application" />
                <QuickAction href="/cv" label="Master CV" desc="View or update your CV" />
                <QuickAction href="/profile" label="Edit Profile" desc="Update skills and history" />
                <QuickAction href="/linkedin" label="LinkedIn Builder" desc="Generate LinkedIn content" />
                <QuickAction href="/examples" label="Upload Example CV" desc="Add a CV for style analysis" />
              </div>
            </div>
          </div>

          {/* Recent applications */}
          <div className="lg:col-span-2">
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 text-sm">Recent Applications</h2>
                <Link href="/applications" className="text-xs text-brand-600 hover:underline">View all</Link>
              </div>
              <div className="divide-y divide-gray-50">
                {recentApps.length === 0 ? (
                  <div className="px-6 py-8 text-center text-sm text-gray-400">
                    No applications yet.{' '}
                    <Link href="/applications/new" className="text-brand-600 hover:underline">Start one</Link>
                  </div>
                ) : (
                  recentApps.map((app) => (
                    <Link key={app.id} href={`/applications/${app.id}`} className="flex items-center justify-between px-6 py-3 hover:bg-gray-50 transition-colors">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {app.role || 'Unknown role'}{app.company ? ` at ${app.company}` : ''}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {app.location || ''} {app.work_type ? `· ${app.work_type}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={STATUS_COLORS[app.status] || 'badge-gray'}>
                          {app.status}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}

function StatCard({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    <Link href={href} className="card p-4 hover:border-brand-200 transition-colors">
      <p className="text-2xl font-bold text-brand-700">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </Link>
  )
}

function QuickAction({ href, label, desc }: { href: string; label: string; desc: string }) {
  return (
    <Link href={href} className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group">
      <div className="w-2 h-2 rounded-full bg-brand-400 group-hover:bg-brand-600 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-gray-800 group-hover:text-brand-700">{label}</p>
        <p className="text-xs text-gray-400">{desc}</p>
      </div>
    </Link>
  )
}
