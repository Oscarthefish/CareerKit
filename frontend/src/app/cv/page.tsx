'use client'
import { useEffect, useState, useCallback } from 'react'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import AIButton from '@/components/AIButton'
import CVRenderer from '@/components/CVRenderer'
import BannedPhrasesWidget from '@/components/BannedPhrasesWidget'
import { getCurrentCV, generateCV, brutalReview, saveCV, exportCV } from '@/lib/api'
import type { BrutalReview } from '@/lib/types'

export default function CVPage() {
  const [cvContent, setCvContent] = useState<string | null>(null)
  const [cvId, setCvId] = useState<number | null>(null)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [review, setReview] = useState<BrutalReview | null>(null)
  const [showReview, setShowReview] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data: any = await getCurrentCV()
      setCvContent(data.content_markdown)
      setCvId(data.id)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleGenerate = async () => {
    const data: any = await generateCV()
    setCvContent(data.content_markdown)
    setCvId(data.id)
  }

  const handleReview = async () => {
    const data: any = await brutalReview()
    setReview(data)
    setShowReview(true)
  }

  const handleSaveEdit = async () => {
    setSaving(true)
    try {
      await saveCV({ content_markdown: editContent, version_name: 'Manual edit' })
      setCvContent(editContent)
      setEditing(false)
      await load()
    } finally {
      setSaving(false)
    }
  }

  const startEdit = () => {
    setEditContent(cvContent || '')
    setEditing(true)
  }

  if (loading) {
    return <AppShell><div className="p-8 text-gray-400">Loading...</div></AppShell>
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <PageHeader
          title="Master CV"
          description="Your master CV is not regenerated for every job. Update it over time as you gain new skills and experience."
          action={
            <div className="flex items-center gap-2">
              {cvContent && (
                <>
                  <a href={exportCV('md')} download className="btn-secondary btn-sm">Export MD</a>
                  <a href={exportCV('docx')} download className="btn-secondary btn-sm">Export DOCX</a>
                  <a href={exportCV('pdf')} download className="btn-secondary btn-sm">Export PDF</a>
                </>
              )}
            </div>
          }
        />

        {!cvContent ? (
          <div className="card p-12 text-center">
            <div className="text-4xl mb-4">◻</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No CV yet</h2>
            <p className="text-sm text-gray-500 mb-6">
              Generate your master CV from your profile, or paste one in below.
            </p>
            <AIButton
              label="Generate Master CV from Profile"
              loadingLabel="Generating CV..."
              onClick={handleGenerate}
            />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* CV Actions */}
            <div className="lg:col-span-1 space-y-4">
              <div className="card p-4 space-y-2">
                <h3 className="text-sm font-semibold text-gray-700">Actions</h3>
                <AIButton label="Regenerate CV" loadingLabel="Generating..." onClick={handleGenerate} className="w-full" />
                {!editing && (
                  <button onClick={startEdit} className="btn-secondary w-full">Edit Manually</button>
                )}
                <div className="divider" />
                <AIButton
                  label="Brutal Recruiter Review"
                  loadingLabel="Reviewing..."
                  onClick={handleReview}
                  variant="secondary"
                  className="w-full"
                />
                <p className="text-xs text-gray-400">
                  Reviews your CV as a recruiter, hiring manager, HR screener, and ATS simultaneously.
                </p>
              </div>
              <div className="card p-4 space-y-2">
                <h3 className="text-sm font-semibold text-gray-700">Export</h3>
                <a href={exportCV('md')} download className="btn-secondary w-full text-center">Markdown</a>
                <a href={exportCV('docx')} download className="btn-secondary w-full text-center">Word DOCX</a>
                <a href={exportCV('pdf')} download className="btn-secondary w-full text-center">PDF</a>
              </div>
              <BannedPhrasesWidget />
            </div>

            {/* CV Content */}
            <div className="lg:col-span-2">
              {editing ? (
                <div className="card">
                  <div className="card-header flex items-center justify-between">
                    <h3 className="font-medium text-gray-900">Editing Markdown</h3>
                    <div className="flex gap-2">
                      <button onClick={() => setEditing(false)} className="btn-ghost btn-sm">Cancel</button>
                      <button onClick={handleSaveEdit} disabled={saving} className="btn-primary btn-sm">
                        {saving ? 'Saving...' : 'Save'}
                      </button>
                    </div>
                  </div>
                  <textarea
                    className="w-full p-6 font-mono text-xs text-gray-800 border-0 focus:ring-0 outline-none resize-none"
                    rows={50}
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                  />
                </div>
              ) : (
                <div>
                  <div className="flex items-center justify-between mb-3 px-1">
                    <p className="text-xs text-gray-400">Preview — scroll down to see full CV</p>
                    <button onClick={startEdit} className="btn-ghost btn-sm">Edit Markdown</button>
                  </div>
                  <CVRenderer markdown={cvContent!} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Brutal Review Panel */}
        {showReview && review && (
          <div className="mt-8 card">
            <div className="card-header flex items-center justify-between">
              <h2 className="font-semibold text-gray-900">Brutal Recruiter Review</h2>
              <button onClick={() => setShowReview(false)} className="btn-ghost btn-sm">Close</button>
            </div>
            <div className="p-6 space-y-6">
              {/* Overall verdict */}
              <div className="p-4 bg-gray-50 rounded-xl">
                <h3 className="font-semibold text-gray-900 mb-2">Overall Verdict</h3>
                <p className="text-sm text-gray-700">{review.overall_verdict}</p>
              </div>

              {/* Ratings grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <RatingCard label="Top Third" value={review.top_third_strength} notes={review.top_third_notes} />
                <RatingCard label="Role Clarity" value={review.target_role_clarity} />
                <RatingCard label="Credibility" value={review.credibility_rating} notes={review.credibility_notes} />
                <RatingCard label="Generic?" value={review.generic_rating} notes={review.generic_notes} />
              </div>

              {/* First impression */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">First Impression (10 seconds)</h3>
                <p className="text-sm text-gray-700">{review.first_impression}</p>
              </div>

              {/* Priority fixes */}
              {review.priority_fixes?.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-3">Priority Fixes</h3>
                  <div className="space-y-3">
                    {review.priority_fixes.map((fix) => (
                      <div key={fix.rank} className="flex gap-3 p-3 bg-gray-50 rounded-lg">
                        <span className="w-6 h-6 bg-red-100 text-red-700 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0">
                          {fix.rank}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{fix.issue}</p>
                          <p className="text-xs text-gray-500 mt-0.5">{fix.fix}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Issues lists */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <IssueList title="Shortlisting Blockers" items={review.shortlisting_blockers} color="red" />
                <IssueList title="Missing Evidence" items={review.missing_evidence} color="yellow" />
                <IssueList title="Weak Bullets" items={review.weak_bullets} color="yellow" />
                <IssueList title="ATS Issues" items={review.ats_issues} color="blue" />
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}

function RatingCard({ label, value, notes }: { label: string; value: string; notes?: string }) {
  const colorMap: Record<string, string> = {
    strong: 'bg-green-50 text-green-800',
    ok: 'bg-yellow-50 text-yellow-800',
    weak: 'bg-red-50 text-red-800',
    clear: 'bg-green-50 text-green-800',
    unclear: 'bg-yellow-50 text-yellow-800',
    missing: 'bg-red-50 text-red-800',
    high: 'bg-green-50 text-green-800',
    medium: 'bg-yellow-50 text-yellow-800',
    low: 'bg-red-50 text-red-800',
    specific: 'bg-green-50 text-green-800',
    somewhat_generic: 'bg-yellow-50 text-yellow-800',
    generic: 'bg-red-50 text-red-800',
  }
  const cls = colorMap[value] || 'bg-gray-50 text-gray-700'
  return (
    <div className={`p-3 rounded-lg ${cls}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-sm font-semibold capitalize mt-0.5">{value?.replace(/_/g, ' ')}</p>
      {notes && <p className="text-xs opacity-80 mt-1 line-clamp-2">{notes}</p>}
    </div>
  )
}

function IssueList({ title, items, color }: { title: string; items: string[]; color: string }) {
  if (!items?.length) return null
  const headerCls = color === 'red' ? 'text-red-700' : color === 'yellow' ? 'text-yellow-700' : 'text-blue-700'
  return (
    <div>
      <h3 className={`text-sm font-semibold ${headerCls} mb-2`}>{title}</h3>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-xs text-gray-700 flex gap-2">
            <span className="text-gray-400">-</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

