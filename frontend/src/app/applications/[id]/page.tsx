'use client'
import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import AIButton from '@/components/AIButton'
import FileUpload from '@/components/FileUpload'
import BannedPhrasesWidget from '@/components/BannedPhrasesWidget'
import CVRenderer from '@/components/CVRenderer'
import EvidenceFeedbackWidget from '@/components/EvidenceFeedbackWidget'
import {
  getApplication, updateApplication, analyzeJob, generateScorecard, generateJobMatch, generateCustomCV,
  generateCoverLetter, generateCVNotes, generateInterviewPrep,
  generateLinkedInAngle, generateTailoredCV, uploadJobDescription, exportApplication
} from '@/lib/api'
import type {
  JobApplication, JobAnalysis, MatchScorecard, InterviewPrep, BrushUpTopic, InterviewQuestion,
  JobMatchResult, Coverage, RecommendationTier, PriorityFix, CustomCvResult,
} from '@/lib/types'

const TABS = ['Overview', 'Job Analysis', 'Job Match', 'Match Scorecard', 'Cover Letter', 'CV Notes', 'Interview Prep', 'LinkedIn', 'Notes']

const STATUS_OPTIONS = ['draft', 'applied', 'interviewing', 'offered', 'rejected', 'withdrawn']

export default function ApplicationDetailPage() {
  const { id } = useParams()
  const appId = Number(id)
  const [app, setApp] = useState<JobApplication | null>(null)
  const [tab, setTab] = useState('Overview')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [editingNotes, setEditingNotes] = useState(false)
  const [notesValue, setNotesValue] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const data: any = await getApplication(appId)
      setApp(data)
      setNotesValue(data.session_notes || '')
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Unable to load this application')
    } finally {
      setLoading(false)
    }
  }, [appId])

  useEffect(() => { load() }, [load])

  const refresh = () => load()

  const handleStatusChange = async (status: string) => {
    await updateApplication(appId, { status, applied_date: status === 'applied' ? new Date().toISOString().split('T')[0] : undefined })
    refresh()
  }

  const saveNotes = async () => {
    await updateApplication(appId, { session_notes: notesValue })
    setEditingNotes(false)
    refresh()
  }

  if (loading) {
    return <AppShell><div className="p-8 text-gray-400">Loading...</div></AppShell>
  }

  if (loadError || !app) {
    return (
      <AppShell>
        <div className="p-8">
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {loadError || 'Application not found.'}
          </div>
        </div>
      </AppShell>
    )
  }

  const title = `${app.role || 'Application'}${app.company ? ` at ${app.company}` : ''}`

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/applications" className="text-xs text-gray-400 hover:text-brand-600">← Applications</Link>
          <div className="flex items-start justify-between mt-2">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                {app.location && <span>{app.location}</span>}
                {app.work_type && <span>· {app.work_type}</span>}
                {app.salary_range && <span>· {app.salary_range}</span>}
              </div>
            </div>
            <select
              value={app.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="input w-auto text-sm"
            >
              {STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Progress bar */}
        <div className="flex items-center gap-2 mb-6 p-4 bg-gray-50 rounded-xl">
          {['Analysis', 'Scorecard', 'Cover Letter', 'Interview Prep'].map((step, i) => {
            const done = [!!app.job_analysis, !!app.match_scorecard, !!app.cover_letter, !!app.interview_prep][i]
            return (
              <div key={step} className="flex items-center gap-2 flex-1">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                  done ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-400'
                }`}>
                  {done ? '✓' : i + 1}
                </div>
                <span className={`text-xs font-medium ${done ? 'text-green-700' : 'text-gray-400'}`}>{step}</span>
                {i < 3 && <div className={`flex-1 h-px ${done ? 'bg-green-300' : 'bg-gray-200'}`} />}
              </div>
            )
          })}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                tab === t ? 'bg-brand-700 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:border-brand-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === 'Overview' && <TabOverview app={app} refresh={refresh} appId={appId} />}
        {tab === 'Job Analysis' && <TabJobAnalysis app={app} refresh={refresh} appId={appId} />}
        {tab === 'Job Match' && <TabJobMatch app={app} refresh={refresh} appId={appId} />}
        {tab === 'Match Scorecard' && <TabScorecard app={app} refresh={refresh} appId={appId} />}
        {tab === 'Cover Letter' && <TabCoverLetter app={app} refresh={refresh} appId={appId} />}
        {tab === 'CV Notes' && <TabCVNotes app={app} refresh={refresh} appId={appId} />}
        {tab === 'Interview Prep' && <TabInterviewPrep app={app} refresh={refresh} appId={appId} />}
        {tab === 'LinkedIn' && <TabLinkedIn app={app} refresh={refresh} appId={appId} />}
        {tab === 'Notes' && (
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Session Notes & Company Research</h3>
              {!editingNotes && (
                <button onClick={() => setEditingNotes(true)} className="btn-secondary btn-sm">Edit</button>
              )}
            </div>
            {editingNotes ? (
              <>
                <textarea
                  className="textarea w-full"
                  rows={20}
                  value={notesValue}
                  onChange={(e) => setNotesValue(e.target.value)}
                  placeholder="Add company research, recruiter notes, salary research, LinkedIn notes, SEEK notes, or anything else relevant to this application."
                />
                <div className="flex gap-2 mt-3">
                  <button onClick={saveNotes} className="btn-primary btn-sm">Save</button>
                  <button onClick={() => setEditingNotes(false)} className="btn-ghost btn-sm">Cancel</button>
                </div>
              </>
            ) : (
              <div className="prose-cv whitespace-pre-wrap text-sm text-gray-700 min-h-[100px]">
                {app.session_notes || <span className="text-gray-400">No notes yet. Click Edit to add company research, recruiter notes, or anything relevant.</span>}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  )
}

function TabOverview({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  const [editing, setEditing] = useState(false)
  const [jdValue, setJdValue] = useState(app.job_description_raw || '')
  const [saving, setSaving] = useState(false)

  const saveJD = async () => {
    setSaving(true)
    await updateApplication(appId, { job_description_raw: jdValue })
    setSaving(false)
    setEditing(false)
    refresh()
  }

  return (
    <div className="space-y-4">
      {/* JD section */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Job Description</h3>
          <div className="flex gap-2">
            {!editing && <button onClick={() => setEditing(true)} className="btn-ghost btn-sm">Edit</button>}
          </div>
        </div>
        {!app.job_description_raw && !editing ? (
          <div className="space-y-3">
            <p className="text-sm text-gray-400">No job description yet. Paste it or upload a file.</p>
            <FileUpload
              label="Upload job description"
              accept=".pdf,.docx,.txt,.md"
              onFile={async (file) => {
                await uploadJobDescription(appId, file)
                refresh()
              }}
            />
            <button onClick={() => setEditing(true)} className="btn-secondary btn-sm">Paste text</button>
          </div>
        ) : editing ? (
          <>
            <textarea className="textarea w-full" rows={16} value={jdValue} onChange={(e) => setJdValue(e.target.value)} />
            <div className="flex gap-2 mt-2">
              <button onClick={saveJD} disabled={saving} className="btn-primary btn-sm">{saving ? 'Saving...' : 'Save'}</button>
              <button onClick={() => setEditing(false)} className="btn-ghost btn-sm">Cancel</button>
            </div>
          </>
        ) : (
          <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto bg-gray-50 rounded-lg p-4">
            {app.job_description_raw}
          </div>
        )}
      </div>

      {/* Run analysis */}
      {app.job_description_raw && !app.job_analysis && (
        <div className="card p-5 flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-900 text-sm">Ready to analyse</p>
            <p className="text-xs text-gray-400 mt-0.5">Extract role requirements, keywords, and screening criteria</p>
          </div>
          <AIButton
            label="Analyse Job Description"
            loadingLabel="Analysing..."
            onClick={async () => { await analyzeJob(appId); refresh() }}
          />
        </div>
      )}

      {/* Quick actions */}
      {app.job_analysis && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Generate Application Materials</h3>
          <div className="grid grid-cols-2 gap-2">
            {!app.match_scorecard && (
              <AIButton label="Match Scorecard" loadingLabel="Scoring..." onClick={async () => { await generateScorecard(appId); refresh() }} />
            )}
            {app.match_scorecard && !app.cover_letter && (
              <AIButton label="Cover Letter" loadingLabel="Writing..." onClick={async () => { await generateCoverLetter(appId); refresh() }} />
            )}
            {app.match_scorecard && !app.cv_adjustment_notes && (
              <AIButton label="CV Adjustment Notes" loadingLabel="Generating..." onClick={async () => { await generateCVNotes(appId); refresh() }} variant="secondary" />
            )}
            {app.job_analysis && !app.interview_prep && (
              <AIButton label="Interview Prep Pack" loadingLabel="Preparing..." onClick={async () => { await generateInterviewPrep(appId); refresh() }} variant="secondary" />
            )}
            {app.job_analysis && !app.linkedin_angle && (
              <AIButton label="LinkedIn Angle" loadingLabel="Generating..." onClick={async () => { await generateLinkedInAngle(appId); refresh() }} variant="secondary" />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function TabJobAnalysis({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  const analysis = app.job_analysis as JobAnalysis | null

  if (!analysis) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">No analysis yet. Add a job description first.</p>
        {app.job_description_raw && (
          <AIButton
            label="Analyse Job Description"
            loadingLabel="Analysing..."
            onClick={async () => { await analyzeJob(appId); refresh() }}
          />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2 mb-2">
        <AIButton label="Re-analyse" loadingLabel="Analysing..." onClick={async () => { await analyzeJob(appId); refresh() }} variant="secondary" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <InfoCard label="Job Title" value={analysis.job_title} />
        <InfoCard label="Location" value={analysis.location} />
        <InfoCard label="Work Type" value={analysis.work_type} />
        <InfoCard label="Seniority" value={analysis.seniority_level} />
        <InfoCard label="Salary" value={analysis.salary_range || 'Not stated'} />
        <InfoCard label="Recruiter" value={analysis.recruiter_name || 'Not stated'} />
      </div>

      {analysis.notes && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-2 text-sm">Summary</h3>
          <p className="text-sm text-gray-700">{analysis.notes}</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ListCard title="Required Skills" items={analysis.required_skills} />
        <ListCard title="Preferred Skills" items={analysis.preferred_skills} />
        <ListCard title="Key Responsibilities" items={analysis.key_responsibilities} />
        <ListCard title="Repeated Keywords" items={analysis.repeated_keywords} highlight />
        <ListCard title="Hidden Priorities" items={analysis.hidden_priorities} />
        <ListCard title="Likely Pain Points" items={analysis.likely_pain_points} />
        <ListCard title="Likely Interview Themes" items={analysis.likely_interview_themes} />
        <ListCard title="Red Flags" items={analysis.red_flags} color="red" />
      </div>
    </div>
  )
}

const COVERAGE_BADGE: Record<Coverage, string> = {
  STRONG_EVIDENCE: 'badge-green',
  PARTIAL_EVIDENCE: 'badge-yellow',
  NO_EVIDENCE: 'badge-red',
  UNKNOWN: 'badge-gray',
}

const TIER_BADGE: Record<RecommendationTier, string> = {
  SAFE_OPTIMISATION: 'badge-green',
  EVIDENCE_NEEDED: 'badge-yellow',
  DO_NOT_ADD: 'badge-red',
}

const TIER_LABEL: Record<RecommendationTier, string> = {
  SAFE_OPTIMISATION: 'Safe optimisation',
  EVIDENCE_NEEDED: 'Evidence needed',
  DO_NOT_ADD: 'Do not add',
}

const SEVERITY_ICON: Record<PriorityFix['severity'], string> = {
  critical: '🔴', high: '🟠', medium: '🟡', low: '🟢',
}

function ScoreDial({ label, score }: { label: string; score: number }) {
  const color = score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600'
  return (
    <div className="text-center">
      <div className={`text-3xl font-bold ${color}`}>{score}%</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function TabJobMatch({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  const [expandedSub, setExpandedSub] = useState<string | null>(null)
  const [showAllFixes, setShowAllFixes] = useState(false)
  const result = app.job_match_result as JobMatchResult | null

  if (!result) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">Generate a Job Match report to see an explainable score against this role.</p>
        {app.job_analysis ? (
          <AIButton
            label="Generate Job Match Report"
            loadingLabel="Analysing (this can take a few minutes on a local model)..."
            onClick={async () => { await generateJobMatch(appId); refresh() }}
          />
        ) : (
          <p className="text-xs text-gray-400">Run job analysis first.</p>
        )}
      </div>
    )
  }

  const { job_match, title_match, requirement_coverage, hard_skills, keyword_coverage, priority_fixes } = result
  const subScoreEntries = Object.entries(job_match.sub_scores).filter(([, v]) => v.score !== null) as
    [string, { score: number; requirement_count: number }][]
  const subScoreLabel: Record<string, string> = {
    hard_skills: 'Hard Skills', experience_seniority: 'Experience', qualifications: 'Qualifications',
    soft_skills: 'Soft Skills', industry_context: 'Industry Context', job_title: 'Job Title',
  }
  const fixesToShow = showAllFixes ? [...priority_fixes.top, ...priority_fixes.more] : priority_fixes.top

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <AIButton
          label="Regenerate"
          loadingLabel="Analysing..."
          onClick={async () => { await generateJobMatch(appId); refresh() }}
          variant="secondary"
        />
      </div>

      {/* Hero score */}
      <div className="card p-6 text-center">
        <div className="text-5xl font-bold text-brand-700">{job_match.overall}%</div>
        <div className="text-sm font-semibold text-gray-600 mt-1">JOB MATCH · {job_match.band}</div>
        <p className="text-xs text-gray-400 mt-3 max-w-lg mx-auto">
          CareerKit Job Match estimates how closely your CV aligns with this job description.
          Employers and ATS platforms use different methods and may not assign a comparable score.
          A high score does not guarantee an interview — aim for accurate, relevant alignment rather
          than maximising the score.
        </p>
        {(result.ats_check || result.recruiter_readiness) && (
          <div className="flex justify-center gap-10 mt-5 pt-5 border-t border-gray-100">
            {result.ats_check && (
              <ScoreDial label={`ATS Compatibility · ${result.ats_check.band}`} score={result.ats_check.score} />
            )}
            {result.recruiter_readiness && (
              <ScoreDial
                label={`Recruiter Readiness · ${result.recruiter_readiness.band}`}
                score={result.recruiter_readiness.score}
              />
            )}
          </div>
        )}
      </div>

      {/* Explainability breakdown */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-4 text-sm">Why this score</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {subScoreEntries.map(([key, v]) => (
            <button key={key} onClick={() => setExpandedSub(expandedSub === key ? null : key)} className="text-left">
              <ScoreDial label={subScoreLabel[key] || key} score={v.score} />
            </button>
          ))}
        </div>
        {expandedSub && (
          <div className="mt-4 pt-4 border-t border-gray-100 text-xs text-gray-600">
            {subScoreLabel[expandedSub]} is based on {job_match.sub_scores[expandedSub as keyof typeof job_match.sub_scores].requirement_count} requirement(s)
            of this type, each weighted by how essential it is to the role (critical / important / desirable) and how strongly your Master CV evidences it.
            See the Requirement Coverage and Hard Skills tables below for the detail behind this number.
          </div>
        )}
      </div>

      {/* Job title */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-2 text-sm">Job Title & Seniority</h3>
        <div className="flex items-center gap-2 mb-1">
          <span className={TIER_BADGE[title_match.state === 'EXACT_MATCH' || title_match.state === 'STRONG_EQUIVALENT' ? 'SAFE_OPTIMISATION' : title_match.state === 'NO_ALIGNMENT' ? 'DO_NOT_ADD' : 'EVIDENCE_NEEDED']}>
            {title_match.state.replace(/_/g, ' ')}
          </span>
          {title_match.matched_title && <span className="text-sm text-gray-700">{title_match.matched_title}</span>}
        </div>
        <p className="text-xs text-gray-500">{title_match.explanation}</p>
      </div>

      {/* Priority fixes */}
      {(priority_fixes.top.length > 0) && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-3 text-sm">Priority Improvements</h3>
          <div className="space-y-3">
            {fixesToShow.map((f, i) => (
              <div key={i} className="flex gap-2 text-sm">
                <span>{SEVERITY_ICON[f.severity]}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{f.requirement}</span>
                    <span className={TIER_BADGE[f.tier]}>{TIER_LABEL[f.tier]}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{f.message}</p>
                  {f.tier === 'EVIDENCE_NEEDED' && (
                    <EvidenceFeedbackWidget
                      skillName={f.requirement}
                      context={`${app.role || 'this role'}${app.company ? ` at ${app.company}` : ''}`}
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
          {priority_fixes.more.length > 0 && (
            <button onClick={() => setShowAllFixes(!showAllFixes)} className="btn-ghost btn-sm mt-3">
              {showAllFixes ? 'Show fewer' : `View all findings (${priority_fixes.more.length} more)`}
            </button>
          )}
        </div>
      )}

      {/* Requirement coverage */}
      <div className="card p-5 overflow-x-auto">
        <h3 className="font-semibold text-gray-900 mb-3 text-sm">Requirement Coverage</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
              <th className="pb-2 font-medium">Requirement</th>
              <th className="pb-2 font-medium">Importance</th>
              <th className="pb-2 font-medium">Coverage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {requirement_coverage.map((r, i) => (
              <tr key={i}>
                <td className="py-2 pr-3 text-gray-900">{r.name}</td>
                <td className="py-2 pr-3 text-xs text-gray-500 capitalize">{r.importance}</td>
                <td className="py-2">
                  <span className={COVERAGE_BADGE[r.coverage]}>{r.icon} {r.label}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Hard skills */}
      <div className="card p-5 overflow-x-auto">
        <h3 className="font-semibold text-gray-900 mb-3 text-sm">Hard Skills Analysis</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
              <th className="pb-2 font-medium">Skill</th>
              <th className="pb-2 font-medium">Job importance</th>
              <th className="pb-2 font-medium">CV coverage</th>
              <th className="pb-2 font-medium">Assessment</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {hard_skills.map((s, i) => (
              <tr key={i}>
                <td className="py-2 pr-3 text-gray-900">{s.skill}</td>
                <td className="py-2 pr-3 text-xs text-gray-500 capitalize">{s.importance}</td>
                <td className="py-2 pr-3"><span className={COVERAGE_BADGE[s.coverage]}>{COVERAGE_LABEL_SHORT[s.coverage]}</span></td>
                <td className="py-2 text-xs text-gray-600">{s.assessment}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Keyword coverage */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-3 text-sm">Keyword Coverage</h3>
        <div className="flex items-center gap-4 mb-3 text-sm">
          <span className="text-green-700 font-medium">{keyword_coverage.matched} matched</span>
          <span className="text-yellow-700 font-medium">{keyword_coverage.partial} partial</span>
          <span className="text-red-700 font-medium">{keyword_coverage.missing} missing</span>
          <span className="text-gray-400 ml-auto">{keyword_coverage.coverage_pct}% coverage</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {Object.entries(keyword_coverage.by_category).map(([cat, stats]) => (
            <div key={cat} className="p-3 bg-gray-50 rounded-lg text-xs">
              <p className="font-semibold text-gray-700 capitalize mb-1">{cat.replace(/_/g, ' ')}</p>
              <p className="text-gray-500">{stats.matched} matched · {stats.partial} partial · {stats.missing} missing</p>
            </div>
          ))}
        </div>
      </div>

      {/* Custom CV creation + rescan */}
      <CustomCvPanel app={app} result={result} appId={appId} refresh={refresh} />
    </div>
  )
}

function CustomCvPanel({
  app, result, appId, refresh,
}: { app: JobApplication; result: JobMatchResult; appId: number; refresh: () => void }) {
  const allFixes = [...result.priority_fixes.top, ...result.priority_fixes.more]
  const safeFixes = allFixes.filter((f) => f.tier === 'SAFE_OPTIMISATION')
  const lockedFixes = allFixes.filter((f) => f.tier !== 'SAFE_OPTIMISATION')

  const [selected, setSelected] = useState<Set<string>>(new Set(safeFixes.map((f) => f.requirement)))
  const [step, setStep] = useState<'select' | 'review'>('select')
  const [cvResult, setCvResult] = useState<CustomCvResult | null>(
    app.custom_cv ? { custom_cv: app.custom_cv, applied_fixes: app.custom_cv_fixes_applied || [] } as CustomCvResult : null
  )

  const toggle = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const handleGenerate = async () => {
    const data: any = await generateCustomCV(appId, Array.from(selected))
    setCvResult(data)
    refresh()
  }

  if (safeFixes.length === 0 && !cvResult) {
    return (
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-2 text-sm">Create Custom CV</h3>
        <p className="text-xs text-gray-400">
          No changes are currently backed by evidence in your Master CV — nothing safe to apply yet.
        </p>
      </div>
    )
  }

  return (
    <div className="card p-5">
      <h3 className="font-semibold text-gray-900 mb-1 text-sm">Create Custom CV</h3>
      <p className="text-xs text-gray-400 mb-4">
        Applies only the changes below to a new copy of your Master CV. Changes still needing evidence are
        shown but can't be selected — add the evidence to your Master CV first.
      </p>

      {step === 'select' && (
        <>
          <div className="space-y-2 mb-4">
            {safeFixes.map((f) => (
              <label key={f.requirement} className="flex items-start gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={selected.has(f.requirement)}
                  onChange={() => toggle(f.requirement)}
                  className="mt-1"
                />
                <div>
                  <span className="font-medium text-gray-900">{f.requirement}</span>
                  <p className="text-xs text-gray-500">{f.message}</p>
                </div>
              </label>
            ))}
            {lockedFixes.map((f) => (
              <div key={f.requirement} className="flex items-start gap-2 text-sm opacity-50">
                <input type="checkbox" checked={false} disabled className="mt-1" />
                <div>
                  <span className="font-medium text-gray-900">{f.requirement}</span>
                  <span className={`ml-2 ${TIER_BADGE[f.tier]}`}>{TIER_LABEL[f.tier]}</span>
                  <p className="text-xs text-gray-500">{f.message}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">{selected.size} change{selected.size === 1 ? '' : 's'} selected</span>
            <button
              onClick={() => setStep('review')}
              disabled={selected.size === 0}
              className="btn-secondary btn-sm ml-auto"
            >
              Review Selected Changes
            </button>
          </div>
        </>
      )}

      {step === 'review' && (
        <>
          <div className="space-y-2 mb-4">
            {safeFixes.filter((f) => selected.has(f.requirement)).map((f) => (
              <div key={f.requirement} className="p-3 bg-gray-50 rounded-lg text-sm">
                <span className="font-medium text-gray-900">{f.requirement}</span>
                <p className="text-xs text-gray-500 mt-0.5">{f.message}</p>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={() => setStep('select')} className="btn-ghost btn-sm">Back</button>
            <AIButton
              label={`Generate Custom CV (${selected.size} change${selected.size === 1 ? '' : 's'})`}
              loadingLabel="Generating and rescanning..."
              onClick={handleGenerate}
            />
          </div>
        </>
      )}

      {cvResult && (cvResult.before || cvResult.after) && (
        <div className="mt-6 pt-6 border-t border-gray-100">
          <h4 className="font-semibold text-gray-900 mb-3 text-sm">Before → After</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <RescanScore label="Job Match" before={cvResult.before?.job_match} after={cvResult.after?.job_match} />
            <RescanScore label="ATS Compatibility" before={cvResult.before?.ats_check} after={cvResult.after?.ats_check} />
            <RescanScore label="Recruiter Readiness" before={cvResult.before?.recruiter_readiness} after={cvResult.after?.recruiter_readiness} />
          </div>
          <p className="text-xs text-gray-400 mb-4">
            Job Match measures evidence in your structured Master CV data, so it typically won't move from
            wording changes alone — that's intentional, not a bug: CareerKit won't inflate this score just
            because the CV reads better. ATS Compatibility and Recruiter Readiness are text-driven and
            reflect the real improvement above.
          </p>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-400">Applied: {cvResult.applied_fixes.join(', ')}</p>
            <div className="flex gap-2">
              <a href={exportApplication(appId, 'md', 'custom-cv')} download className="btn-ghost btn-sm">MD</a>
              <a href={exportApplication(appId, 'docx', 'custom-cv')} download className="btn-ghost btn-sm">DOCX</a>
              <a href={exportApplication(appId, 'pdf', 'custom-cv')} download className="btn-ghost btn-sm">PDF</a>
            </div>
          </div>
          <CVRenderer markdown={cvResult.custom_cv} />
        </div>
      )}
    </div>
  )
}

function RescanScore({ label, before, after }: { label: string; before?: number | null; after?: number | null }) {
  const improved = before != null && after != null && after > before
  return (
    <div className="p-3 bg-gray-50 rounded-lg text-center">
      <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
      <p className="text-sm">
        <span className="text-gray-400">{before ?? '—'}%</span>
        <span className="mx-1 text-gray-300">→</span>
        <span className={`font-bold ${improved ? 'text-green-600' : 'text-gray-700'}`}>{after ?? '—'}%</span>
      </p>
    </div>
  )
}

const COVERAGE_LABEL_SHORT: Record<Coverage, string> = {
  STRONG_EVIDENCE: 'Strong', PARTIAL_EVIDENCE: 'Limited', NO_EVIDENCE: 'None', UNKNOWN: 'Unknown',
}

function TabScorecard({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  const scorecard = app.match_scorecard as MatchScorecard | null

  const FIT_STYLES: Record<string, string> = {
    strong: 'bg-green-100 text-green-800 border-green-200',
    good: 'bg-blue-100 text-blue-800 border-blue-200',
    stretch: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    weak: 'bg-red-100 text-red-800 border-red-200',
    not_recommended: 'bg-red-200 text-red-900 border-red-300',
  }

  if (!scorecard) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">No scorecard yet. Run job analysis first.</p>
        {app.job_analysis && (
          <AIButton
            label="Generate Match Scorecard"
            loadingLabel="Scoring..."
            onClick={async () => { await generateScorecard(appId); refresh() }}
          />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <AIButton label="Regenerate" loadingLabel="Scoring..." onClick={async () => { await generateScorecard(appId); refresh() }} variant="secondary" />
      </div>

      {/* Overall fit */}
      <div className={`p-5 rounded-xl border ${FIT_STYLES[scorecard.overall_fit] || 'bg-gray-50'}`}>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-lg font-bold capitalize">{scorecard.overall_fit?.replace(/_/g, ' ')}</span>
          <span className="text-sm opacity-70">fit</span>
        </div>
        <p className="text-sm">{scorecard.fit_summary}</p>
      </div>

      {/* Suggested angle */}
      {scorecard.suggested_angle && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-2 text-sm">Suggested Angle</h3>
          <p className="text-sm text-gray-700">{scorecard.suggested_angle}</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Strong matches */}
        {scorecard.strong_matches?.length > 0 && (
          <div className="card p-4">
            <h3 className="font-semibold text-green-700 text-sm mb-3">Strong Matches</h3>
            <div className="space-y-2">
              {scorecard.strong_matches.map((m, i) => (
                <div key={i} className="text-sm">
                  <span className="font-medium text-gray-900">{m.skill}</span>
                  {m.evidence && <p className="text-xs text-gray-500 mt-0.5">{m.evidence}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Partial matches */}
        {scorecard.partial_matches?.length > 0 && (
          <div className="card p-4">
            <h3 className="font-semibold text-yellow-700 text-sm mb-3">Partial Matches</h3>
            <div className="space-y-2">
              {scorecard.partial_matches.map((m, i) => (
                <div key={i} className="text-sm">
                  <span className="font-medium text-gray-900">{m.skill}</span>
                  {m.gap && <p className="text-xs text-gray-500 mt-0.5">{m.gap}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick learning */}
        {scorecard.quick_learning_gaps?.length > 0 && (
          <div className="card p-4">
            <h3 className="font-semibold text-blue-700 text-sm mb-3">Can Learn Quickly</h3>
            <div className="space-y-2">
              {scorecard.quick_learning_gaps.map((g, i) => (
                <div key={i} className="text-sm">
                  <span className="font-medium text-gray-900">{g.skill}</span>
                  {g.rationale && <p className="text-xs text-gray-500 mt-0.5">{g.rationale}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Genuine gaps */}
        {scorecard.genuine_gaps?.length > 0 && (
          <div className="card p-4">
            <h3 className="font-semibold text-red-700 text-sm mb-3">Genuine Gaps</h3>
            <div className="space-y-2">
              {scorecard.genuine_gaps.map((g, i) => (
                <div key={i} className="text-sm">
                  <span className="font-medium text-gray-900">{g.skill}</span>
                  {g.impact && <p className="text-xs text-gray-500 mt-0.5">{g.impact}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Claims guidance */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {scorecard.safe_claims?.length > 0 && (
          <div className="p-4 bg-green-50 rounded-xl">
            <h3 className="font-semibold text-green-800 text-xs mb-2">Safe to Claim</h3>
            <ul className="space-y-1 text-xs text-green-700">
              {scorecard.safe_claims.map((c, i) => <li key={i}>- {c}</li>)}
            </ul>
          </div>
        )}
        {scorecard.claims_needing_review?.length > 0 && (
          <div className="p-4 bg-yellow-50 rounded-xl">
            <h3 className="font-semibold text-yellow-800 text-xs mb-2">Needs Care</h3>
            <ul className="space-y-1 text-xs text-yellow-700">
              {scorecard.claims_needing_review.map((c, i) => <li key={i}>- {c}</li>)}
            </ul>
          </div>
        )}
        {scorecard.do_not_claim?.length > 0 && (
          <div className="p-4 bg-red-50 rounded-xl">
            <h3 className="font-semibold text-red-800 text-xs mb-2">Do Not Claim</h3>
            <ul className="space-y-1 text-xs text-red-700">
              {scorecard.do_not_claim.map((c, i) => <li key={i}>- {c}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* ATS keywords */}
      {scorecard.ats_keywords_to_include?.length > 0 && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">ATS Keywords to Include Naturally</h3>
          <div className="flex flex-wrap gap-1.5">
            {scorecard.ats_keywords_to_include.map((k, i) => (
              <span key={i} className="badge-blue">{k}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TabCoverLetter({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(app.cover_letter || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    await updateApplication(appId, { cover_letter: value })
    setSaving(false)
    setEditing(false)
    refresh()
  }

  if (!app.cover_letter && !editing) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">No cover letter yet. Generate one or write your own.</p>
        <div className="flex items-center justify-center gap-3">
          {app.job_analysis ? (
            <AIButton
              label="Generate Cover Letter"
              loadingLabel="Writing..."
              onClick={async () => { await generateCoverLetter(appId); refresh() }}
            />
          ) : (
            <p className="text-xs text-gray-400">Run job analysis first to generate a cover letter.</p>
          )}
          <button onClick={() => { setValue(''); setEditing(true) }} className="btn-secondary">Write Manually</button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <AIButton label="Regenerate" loadingLabel="Writing..." onClick={async () => { await generateCoverLetter(appId); refresh() }} variant="secondary" />
          {!editing && <button onClick={() => { setValue(app.cover_letter || ''); setEditing(true) }} className="btn-secondary">Edit</button>}
        </div>
        <div className="flex gap-2">
          <a href={exportApplication(appId, 'md', 'cover-letter')} download className="btn-ghost btn-sm">MD</a>
          <a href={exportApplication(appId, 'docx', 'cover-letter')} download className="btn-ghost btn-sm">DOCX</a>
          <a href={exportApplication(appId, 'pdf', 'cover-letter')} download className="btn-ghost btn-sm">PDF</a>
        </div>
      </div>

      {editing ? (
        <div className="card">
          <textarea
            className="w-full p-6 text-sm text-gray-800 border-0 focus:ring-0 outline-none resize-none font-sans leading-relaxed"
            rows={30}
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <div className="px-6 py-3 border-t border-gray-100 flex gap-2">
            <button onClick={save} disabled={saving} className="btn-primary btn-sm">{saving ? 'Saving...' : 'Save'}</button>
            <button onClick={() => setEditing(false)} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      ) : (
        <div className="card p-8">
          <div className="prose-cv max-w-none whitespace-pre-wrap">{app.cover_letter}</div>
        </div>
      )}
      <BannedPhrasesWidget />
    </div>
  )
}

function TabCVNotes({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  const [showTailored, setShowTailored] = useState(false)
  const [editingTailored, setEditingTailored] = useState(false)
  const [tailoredValue, setTailoredValue] = useState(app.tailored_cv || '')
  const [savingTailored, setSavingTailored] = useState(false)

  const saveTailored = async () => {
    setSavingTailored(true)
    await updateApplication(appId, { tailored_cv: tailoredValue })
    setSavingTailored(false)
    setEditingTailored(false)
    refresh()
  }

  if (!app.cv_adjustment_notes) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">Generate notes on how to adjust your master CV for this role.</p>
        {app.match_scorecard ? (
          <AIButton
            label="Generate CV Adjustment Notes"
            loadingLabel="Generating..."
            onClick={async () => { await generateCVNotes(appId); refresh() }}
          />
        ) : (
          <p className="text-xs text-gray-400">Run match scorecard first.</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* CV Notes */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">Adjustment Notes</h3>
          <div className="flex gap-2">
            <AIButton label="Regenerate Notes" loadingLabel="Generating..." onClick={async () => { await generateCVNotes(appId); refresh() }} variant="secondary" />
            <a href={exportApplication(appId, 'md', 'cv-notes')} download className="btn-ghost btn-sm">Export MD</a>
          </div>
        </div>
        <div className="card p-6 prose-cv" dangerouslySetInnerHTML={{ __html: markdownToHtml(app.cv_adjustment_notes) }} />
      </div>

      {/* Tailored CV */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Tailored One-Off CV</h3>
            <p className="text-xs text-gray-400 mt-0.5">A version of your master CV with the above changes applied, generated for this specific role.</p>
          </div>
          <div className="flex gap-2">
            {app.tailored_cv && !editingTailored && (
              <>
                <button onClick={() => setShowTailored(!showTailored)} className="btn-ghost btn-sm">
                  {showTailored ? 'Hide' : 'View'}
                </button>
                <button onClick={() => { setTailoredValue(app.tailored_cv || ''); setEditingTailored(true); setShowTailored(true) }} className="btn-secondary btn-sm">Edit</button>
                <a href={exportApplication(appId, 'md', 'tailored-cv')} download className="btn-ghost btn-sm">MD</a>
                <a href={exportApplication(appId, 'docx', 'tailored-cv')} download className="btn-ghost btn-sm">DOCX</a>
                <a href={exportApplication(appId, 'pdf', 'tailored-cv')} download className="btn-ghost btn-sm">PDF</a>
              </>
            )}
            <AIButton
              label={app.tailored_cv ? 'Regenerate' : 'Generate Tailored CV'}
              loadingLabel="Tailoring CV..."
              onClick={async () => { await generateTailoredCV(appId); refresh(); setShowTailored(true); setEditingTailored(false) }}
              variant={app.tailored_cv ? 'secondary' : 'primary'}
            />
          </div>
        </div>
        {showTailored && editingTailored && (
          <div className="border-t border-gray-100">
            <textarea
              className="w-full p-6 text-sm text-gray-800 border-0 focus:ring-0 outline-none resize-none font-sans leading-relaxed"
              rows={30}
              value={tailoredValue}
              onChange={(e) => setTailoredValue(e.target.value)}
            />
            <div className="px-6 py-3 border-t border-gray-100 flex gap-2">
              <button onClick={saveTailored} disabled={savingTailored} className="btn-primary btn-sm">{savingTailored ? 'Saving...' : 'Save'}</button>
              <button onClick={() => setEditingTailored(false)} className="btn-ghost btn-sm">Cancel</button>
            </div>
          </div>
        )}
        {showTailored && !editingTailored && app.tailored_cv && (
          <div className="p-4 border-t border-gray-100">
            <CVRenderer markdown={app.tailored_cv} />
          </div>
        )}
      </div>
    </div>
  )
}

function TabInterviewPrep({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  const prep = app.interview_prep as InterviewPrep | null
  const [openSection, setOpenSection] = useState<string | null>('technical_questions')

  if (!prep) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">Generate your interview preparation pack.</p>
        {app.job_analysis ? (
          <AIButton
            label="Generate Interview Prep Pack"
            loadingLabel="Preparing..."
            onClick={async () => { await generateInterviewPrep(appId); refresh() }}
          />
        ) : (
          <p className="text-xs text-gray-400">Run job analysis first.</p>
        )}
      </div>
    )
  }

  const sections: { key: keyof InterviewPrep; title: string; promptField: keyof InterviewQuestion }[] = [
    { key: 'technical_questions', title: 'Technical Questions', promptField: 'star_prompt' },
    { key: 'behavioural_questions', title: 'Behavioural Questions', promptField: 'star_prompt' },
    { key: 'scenario_questions', title: 'Scenario Questions', promptField: 'suggested_approach' },
    { key: 'gap_questions', title: 'Gap Questions', promptField: 'suggested_framing' },
  ]

  const hasContent =
    sections.some(({ key }) => (prep[key] as InterviewQuestion[] | undefined)?.length) ||
    prep.brush_up_topics?.length ||
    prep.preparation_plan?.length ||
    prep.questions_to_ask_recruiter?.length ||
    prep.questions_to_ask_employer?.length

  if (!hasContent) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-1">The last generation did not return a usable interview prep pack.</p>
        <p className="text-xs text-gray-400 mb-4">This can happen with a small local model. Try again, or switch to a larger model in Settings.</p>
        <AIButton label="Regenerate" loadingLabel="Preparing..." onClick={async () => { await generateInterviewPrep(appId); refresh() }} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <AIButton label="Regenerate" loadingLabel="Preparing..." onClick={async () => { await generateInterviewPrep(appId); refresh() }} variant="secondary" />
      </div>

      {sections.map(({ key, title, promptField }) => {
        const questions = (prep[key] as InterviewQuestion[]) || []
        if (!questions.length) return null
        return (
          <div key={key} className="card">
            <button
              onClick={() => setOpenSection(openSection === key ? null : key)}
              className="w-full card-header flex items-center justify-between text-left"
            >
              <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
              <span className="text-gray-400">{openSection === key ? '▲' : '▼'}</span>
            </button>
            {openSection === key && (
              <div className="divide-y divide-gray-50">
                {questions.map((q, i) => (
                  <div key={i} className="px-6 py-4 space-y-2">
                    <p className="font-medium text-sm text-gray-900">{q.question}</p>
                    {q.why_likely && <p className="text-xs text-gray-400">Why likely: {q.why_likely}</p>}
                    {q.concept_explanation && (
                      <div className="p-3 bg-gray-50 rounded-lg text-xs text-gray-700 border-l-2 border-gray-300">
                        <span className="font-semibold text-gray-600 block mb-0.5">What this is about</span>
                        {q.concept_explanation}
                      </div>
                    )}
                    {q[promptField] && (
                      <div className="p-3 bg-brand-50 rounded-lg text-xs text-brand-900 border-l-2 border-brand-300">
                        <span className="font-semibold block mb-0.5">Your talking points</span>
                        {q[promptField]}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}

      {/* Questions to ask */}
      {(prep.questions_to_ask_recruiter?.length > 0 || prep.questions_to_ask_employer?.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ListCard title="Questions for Recruiter" items={prep.questions_to_ask_recruiter} />
          <ListCard title="Questions for Employer" items={prep.questions_to_ask_employer} />
        </div>
      )}

      {/* Brush up topics */}
      {prep.brush_up_topics?.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4 text-sm">Brush-up Topics</h3>
          <div className="space-y-4">
            {prep.brush_up_topics.map((t: BrushUpTopic, i: number) => (
              <div key={i} className="p-4 bg-amber-50 rounded-xl border border-amber-100">
                <p className="font-semibold text-amber-900 text-sm">{t.topic}</p>
                {t.what_it_covers && (
                  <p className="text-xs text-amber-800 mt-1.5 leading-relaxed">{t.what_it_covers}</p>
                )}
                {t.why && (
                  <p className="text-xs text-amber-700 mt-1"><span className="font-medium">Why relevant:</span> {t.why}</p>
                )}
                {t.key_areas && t.key_areas.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-amber-800 mb-1">Key areas to study:</p>
                    <ul className="space-y-0.5">
                      {t.key_areas.map((area, j) => (
                        <li key={j} className="text-xs text-amber-700 flex gap-1.5">
                          <span className="text-amber-400 mt-0.5 flex-shrink-0">▸</span>
                          <span>{area}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {t.suggested_resources && (
                  <p className="text-xs text-amber-600 mt-2 pt-2 border-t border-amber-200">
                    <span className="font-medium">Resources:</span> {t.suggested_resources}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prep plan */}
      {prep.preparation_plan?.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-3 text-sm">Preparation Plan</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {prep.preparation_plan.map((day, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded-lg text-sm">
                <p className="font-semibold text-gray-800 mb-2">{day.day}</p>
                <ul className="space-y-1">
                  {day.tasks.map((task, j) => <li key={j} className="text-xs text-gray-600">- {task}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TabLinkedIn({ app, refresh, appId }: { app: JobApplication; refresh: () => void; appId: number }) {
  if (!app.linkedin_angle) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">Generate a LinkedIn angle for this specific role.</p>
        {app.job_analysis ? (
          <AIButton
            label="Generate LinkedIn Angle"
            loadingLabel="Generating..."
            onClick={async () => { await generateLinkedInAngle(appId); refresh() }}
          />
        ) : (
          <p className="text-xs text-gray-400">Run job analysis first.</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <AIButton label="Regenerate" loadingLabel="Generating..." onClick={async () => { await generateLinkedInAngle(appId); refresh() }} variant="secondary" />
        <a href={exportApplication(appId, 'md', 'linkedin')} download className="btn-ghost btn-sm">Export MD</a>
      </div>
      <div className="card p-6 prose-cv" dangerouslySetInnerHTML={{ __html: markdownToHtml(app.linkedin_angle) }} />
    </div>
  )
}

// Helper components
function InfoCard({ label, value }: { label: string; value: string | undefined | null }) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg">
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-gray-900 capitalize">{value || '-'}</p>
    </div>
  )
}

function ListCard({ title, items, highlight, color }: { title: string; items: string[]; highlight?: boolean; color?: string }) {
  if (!items?.length) return null
  return (
    <div className="card p-4">
      <h3 className={`font-semibold text-sm mb-2 ${color === 'red' ? 'text-red-700' : 'text-gray-900'}`}>{title}</h3>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className={`text-xs flex gap-1.5 ${color === 'red' ? 'text-red-700' : 'text-gray-700'}`}>
            <span className="text-gray-300">-</span>
            {highlight ? <span className="badge-blue">{item}</span> : item}
          </li>
        ))}
      </ul>
    </div>
  )
}

function markdownToHtml(md: string): string {
  const escaped = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')

  return escaped
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^---+$/gm, '<hr/>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, (m) => `<ul>${m}</ul>`)
    .replace(/^(?!<[hul]|<hr)(.+)$/gm, '<p>$1</p>')
    .replace(/<\/ul>\s*<ul>/g, '')
}
