'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import AIButton from '@/components/AIButton'
import {
  getScanSearches, createScanSearch, deleteScanSearch,
  runScan, getScannedJobs, updateJobStatus, startApplicationFromJob
} from '@/lib/api'
import type { ScanSearch, ScannedJob, ScanResult, ScanSiteStatus } from '@/lib/types'

const ALL_SITES = [
  { key: 'seek', label: 'Seek NZ' },
  { key: 'absoluteit', label: 'Absolute IT' },
  { key: 'hays', label: 'Hays NZ' },
  { key: 'potentia', label: 'Potentia' },
  { key: 'trademe', label: 'Trade Me Jobs' },
]

const SOURCE_COLOURS: Record<string, string> = {
  seek: 'bg-blue-100 text-blue-800',
  absoluteit: 'bg-purple-100 text-purple-800',
  hays: 'bg-green-100 text-green-800',
  potentia: 'bg-orange-100 text-orange-800',
  trademe: 'bg-teal-100 text-teal-800',
}

export default function ScannerPage() {
  const router = useRouter()
  const [searches, setSearches] = useState<ScanSearch[]>([])
  const [selectedSearch, setSelectedSearch] = useState<ScanSearch | null>(null)
  const [jobs, setJobs] = useState<ScannedJob[]>([])
  const [statusTab, setStatusTab] = useState<'new' | 'seen' | 'dismissed'>('new')
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [lastScanResult, setLastScanResult] = useState<ScanResult | null>(null)
  const [scanning, setScanning] = useState(false)
  const [showNewSearch, setShowNewSearch] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadSearches = useCallback(async () => {
    const data: any = await getScanSearches()
    setSearches(data)
    if (data.length > 0 && !selectedSearch) setSelectedSearch(data[0])
  }, [selectedSearch])

  const loadJobs = useCallback(async () => {
    const params: any = { status: statusTab }
    if (sourceFilter) params.source = sourceFilter
    const data: any = await getScannedJobs(params)
    setJobs(data)
  }, [statusTab, sourceFilter])

  useEffect(() => {
    Promise.all([loadSearches(), loadJobs()]).finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadJobs() }, [statusTab, sourceFilter])

  const handleScan = async () => {
    if (!selectedSearch) return
    setScanning(true)
    try {
      const result: any = await runScan(selectedSearch.id)
      setLastScanResult(result)
      await loadJobs()
      await loadSearches()
    } finally {
      setScanning(false)
    }
  }

  const handleStatus = async (job: ScannedJob, status: 'seen' | 'dismissed' | 'new') => {
    await updateJobStatus(job.id, status)
    setJobs(prev => prev.filter(j => j.id !== job.id))
  }

  const handleApply = async (job: ScannedJob) => {
    const result: any = await startApplicationFromJob(job.id)
    setJobs(prev => prev.filter(j => j.id !== job.id))
    router.push(`/applications/${result.application_id}`)
  }

  const displayedJobs = jobs.filter(j =>
    j.status === statusTab && (!sourceFilter || j.source === sourceFilter)
  )

  const counts = {
    new: jobs.filter(j => j.status === 'new').length,
    seen: jobs.filter(j => j.status === 'seen').length,
    dismissed: jobs.filter(j => j.status === 'dismissed').length,
  }

  if (loading) return <AppShell><div className="p-8 text-gray-400">Loading...</div></AppShell>

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto px-6 py-8">
        <PageHeader
          title="Job Scanner"
          description="Scan NZ job sites for new listings matching your skills. Results are deduplicated — each job only appears once."
        />

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-4">
            {/* Saved searches */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">Saved Searches</h3>
                <button onClick={() => setShowNewSearch(true)} className="btn-ghost btn-sm text-xs">+ New</button>
              </div>
              {searches.length === 0 ? (
                <p className="text-xs text-gray-400">No searches yet. Create one to get started.</p>
              ) : (
                <div className="space-y-1">
                  {searches.map(s => (
                    <button
                      key={s.id}
                      onClick={() => setSelectedSearch(s)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                        selectedSearch?.id === s.id
                          ? 'bg-brand-100 text-brand-900 font-medium'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <p className="truncate">{s.name}</p>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{s.keywords}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Selected search detail */}
            {selectedSearch && (
              <div className="card p-4 space-y-3">
                <h3 className="text-sm font-semibold text-gray-700">{selectedSearch.name}</h3>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Keywords</p>
                  <p className="text-sm text-gray-900">{selectedSearch.keywords}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Sites</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedSearch.sites.map(s => (
                      <span key={s} className={`text-xs px-1.5 py-0.5 rounded ${SOURCE_COLOURS[s] || 'bg-gray-100 text-gray-700'}`}>
                        {ALL_SITES.find(x => x.key === s)?.label || s}
                      </span>
                    ))}
                  </div>
                </div>
                {selectedSearch.last_scanned && (
                  <p className="text-xs text-gray-400">
                    Last scanned: {new Date(selectedSearch.last_scanned).toLocaleString('en-NZ')}
                  </p>
                )}
                <AIButton
                  label="Scan Now"
                  loadingLabel="Scanning..."
                  onClick={handleScan}
                  className="w-full"
                  disabled={scanning}
                />
                <button
                  onClick={async () => {
                    await deleteScanSearch(selectedSearch.id)
                    setSelectedSearch(null)
                    await loadSearches()
                  }}
                  className="btn-ghost btn-sm w-full text-red-500 hover:text-red-700"
                >
                  Delete search
                </button>
              </div>
            )}

            {/* Scan result summary */}
            {lastScanResult && (
              <div className="card p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Last Scan</h3>
                <p className="text-xs text-gray-500 mb-2">
                  {lastScanResult.new_jobs} new job{lastScanResult.new_jobs !== 1 ? 's' : ''} found
                </p>
                <div className="space-y-2">
                  {Object.entries(lastScanResult.sites).map(([key, s]: [string, ScanSiteStatus]) => (
                    <div key={key} className="text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 font-medium">{s.display_name}</span>
                        {!s.error ? (
                          <span className="text-green-600">{s.count} found</span>
                        ) : s.search_url ? (
                          <a href={s.search_url} target="_blank" rel="noopener noreferrer"
                             className="text-brand-600 hover:underline">Browse ↗</a>
                        ) : (
                          <span className="text-red-400">Error</span>
                        )}
                      </div>
                      {s.error && s.search_url && (
                        <p className="text-gray-400 text-[10px] mt-0.5">Requires browser — click Browse to open</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Source filter */}
            {jobs.length > 0 && (
              <div className="card p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Filter by Site</h3>
                <div className="space-y-1">
                  <button
                    onClick={() => setSourceFilter('')}
                    className={`w-full text-left text-xs px-2 py-1 rounded ${!sourceFilter ? 'bg-brand-100 text-brand-900 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}
                  >
                    All sites
                  </button>
                  {ALL_SITES.map(site => {
                    const count = jobs.filter(j => j.source === site.key && j.status === statusTab).length
                    if (count === 0) return null
                    return (
                      <button
                        key={site.key}
                        onClick={() => setSourceFilter(sourceFilter === site.key ? '' : site.key)}
                        className={`w-full text-left text-xs px-2 py-1 rounded flex items-center justify-between ${sourceFilter === site.key ? 'bg-brand-100 text-brand-900 font-medium' : 'text-gray-600 hover:bg-gray-100'}`}
                      >
                        <span>{site.label}</span>
                        <span className="text-gray-400">{count}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Main content */}
          <div className="lg:col-span-3 space-y-4">
            {/* New search form */}
            {showNewSearch && (
              <NewSearchForm
                onSave={async (data) => {
                  await createScanSearch(data)
                  await loadSearches()
                  setShowNewSearch(false)
                }}
                onCancel={() => setShowNewSearch(false)}
              />
            )}

            {/* Status tabs */}
            <div className="flex items-center gap-1 border-b border-gray-200">
              {(['new', 'seen', 'dismissed'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setStatusTab(tab)}
                  className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors capitalize ${
                    statusTab === tab
                      ? 'border-brand-600 text-brand-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab}
                  {counts[tab] > 0 && (
                    <span className={`ml-1.5 px-1.5 py-0.5 text-xs rounded-full ${
                      tab === 'new' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-600'
                    }`}>{counts[tab]}</span>
                  )}
                </button>
              ))}
            </div>

            {/* Empty states */}
            {searches.length === 0 ? (
              <div className="card p-12 text-center">
                <div className="text-4xl mb-4">◉</div>
                <h2 className="text-lg font-semibold text-gray-900 mb-2">No searches set up</h2>
                <p className="text-sm text-gray-500 mb-4">Create a saved search with your keywords and which sites to scan.</p>
                <button onClick={() => setShowNewSearch(true)} className="btn-primary">Create Search</button>
              </div>
            ) : displayedJobs.length === 0 ? (
              <div className="card p-10 text-center">
                <p className="text-gray-500 text-sm">
                  {statusTab === 'new'
                    ? 'No new jobs. Select a search and click Scan Now to check for new listings.'
                    : `No ${statusTab} jobs.`}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {displayedJobs.map(job => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onMarkSeen={() => handleStatus(job, 'seen')}
                    onDismiss={() => handleStatus(job, 'dismissed')}
                    onMarkNew={() => handleStatus(job, 'new')}
                    onApply={() => handleApply(job)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}


function NewSearchForm({
  onSave, onCancel
}: { onSave: (data: object) => Promise<void>; onCancel: () => void }) {
  const [name, setName] = useState('')
  const [keywords, setKeywords] = useState('')
  const [sites, setSites] = useState<string[]>(ALL_SITES.map(s => s.key))
  const [saving, setSaving] = useState(false)

  const toggle = (key: string) =>
    setSites(prev => prev.includes(key) ? prev.filter(s => s !== key) : [...prev, key])

  const save = async () => {
    if (!name.trim() || !keywords.trim()) return
    setSaving(true)
    try { await onSave({ name: name.trim(), keywords: keywords.trim(), sites }) }
    finally { setSaving(false) }
  }

  return (
    <div className="card p-5">
      <h3 className="font-semibold text-gray-900 mb-4">New Saved Search</h3>
      <div className="space-y-3">
        <div>
          <label className="label">Search Name</label>
          <input
            className="input"
            placeholder="e.g. Cyber Security NZ"
            value={name}
            onChange={e => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="label">Keywords</label>
          <input
            className="input"
            placeholder="e.g. cyber security SOC analyst"
            value={keywords}
            onChange={e => setKeywords(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">Space-separated. All terms are used together in the search.</p>
        </div>
        <div>
          <label className="label">Sites to Scan</label>
          <div className="flex flex-wrap gap-2 mt-1">
            {ALL_SITES.map(site => (
              <button
                key={site.key}
                onClick={() => toggle(site.key)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  sites.includes(site.key)
                    ? 'bg-brand-600 text-white border-brand-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
                }`}
              >
                {site.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex gap-2 pt-1">
          <button onClick={save} disabled={saving || !name.trim() || !keywords.trim()} className="btn-primary">
            {saving ? 'Saving...' : 'Save Search'}
          </button>
          <button onClick={onCancel} className="btn-ghost">Cancel</button>
        </div>
      </div>
    </div>
  )
}


function JobCard({
  job, onMarkSeen, onDismiss, onMarkNew, onApply
}: {
  job: ScannedJob
  onMarkSeen: () => void
  onDismiss: () => void
  onMarkNew: () => void
  onApply: () => void
}) {
  const [applying, setApplying] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const doApply = async () => {
    setApplying(true)
    try { await onApply() }
    finally { setApplying(false) }
  }

  const sourceColor = SOURCE_COLOURS[job.source] || 'bg-gray-100 text-gray-700'

  return (
    <div className="card p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sourceColor}`}>
              {job.source_name}
            </span>
            {job.date_posted && (
              <span className="text-xs text-gray-400">{job.date_posted}</span>
            )}
            {job.first_seen && (
              <span className="text-xs text-gray-400">
                Found {new Date(job.first_seen).toLocaleDateString('en-NZ')}
              </span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 text-sm leading-snug">{job.title}</h3>
          {(job.company || job.location) && (
            <p className="text-sm text-gray-500 mt-0.5">
              {[job.company, job.location].filter(Boolean).join(' · ')}
            </p>
          )}
          {job.description_snippet && (
            <div>
              <p className={`text-xs text-gray-600 mt-1.5 leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>
                {job.description_snippet}
              </p>
              {job.description_snippet.length > 120 && (
                <button onClick={() => setExpanded(!expanded)} className="text-xs text-brand-600 mt-0.5">
                  {expanded ? 'Less' : 'More'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={job.status === 'new' ? onMarkSeen : undefined}
          className="btn-secondary btn-sm"
        >
          View Listing ↗
        </a>
        <button
          onClick={doApply}
          disabled={applying}
          className="btn-primary btn-sm"
        >
          {applying ? 'Creating...' : 'Start Application'}
        </button>
        <div className="flex-1" />
        {job.status === 'new' && (
          <button onClick={onMarkSeen} className="btn-ghost btn-sm text-xs">Mark Seen</button>
        )}
        {job.status !== 'dismissed' && (
          <button onClick={onDismiss} className="btn-ghost btn-sm text-xs text-gray-400">Dismiss</button>
        )}
        {job.status === 'dismissed' && (
          <button onClick={onMarkNew} className="btn-ghost btn-sm text-xs">Restore</button>
        )}
      </div>
    </div>
  )
}
