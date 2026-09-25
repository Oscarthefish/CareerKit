'use client'
import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import AIButton from '@/components/AIButton'
import BannedPhrasesWidget from '@/components/BannedPhrasesWidget'
import { getReachOut, updateReachOut, generateReachOutLetter, exportReachOut } from '@/lib/api'
import type { ReachOut } from '@/lib/types'

const TABS = ['Overview', 'Research', 'Introduction Letter', 'CV Notes', 'Notes']
const STATUS_OPTIONS = ['identified', 'researched', 'letter_drafted', 'sent', 'follow_up_due', 'responded', 'archived']

export default function ReachOutDetailPage() {
  const { id } = useParams()
  const reachOutId = Number(id)
  const [item, setItem] = useState<ReachOut | null>(null)
  const [tab, setTab] = useState('Overview')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const data: any = await getReachOut(reachOutId)
      setItem(data)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Unable to load this reach out')
    } finally {
      setLoading(false)
    }
  }, [reachOutId])

  useEffect(() => { load() }, [load])

  const refresh = () => load()

  const handleStatusChange = async (status: string) => {
    await updateReachOut(reachOutId, {
      status,
      date_sent: status === 'sent' ? new Date().toISOString().split('T')[0] : undefined,
    })
    refresh()
  }

  if (loading) {
    return <AppShell><div className="p-8 text-gray-400">Loading...</div></AppShell>
  }

  if (loadError || !item) {
    return (
      <AppShell>
        <div className="p-8">
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {loadError || 'Reach out not found.'}
          </div>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-6">
          <Link href="/reachouts" className="text-xs text-gray-400 hover:text-brand-600">← Reach Outs</Link>
          <div className="flex items-start justify-between mt-2">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{item.company_name}</h1>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                {item.industry && <span>{item.industry}</span>}
                {item.location && <span>· {item.location}</span>}
              </div>
            </div>
            <select
              value={item.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="input w-auto text-sm"
            >
              {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
        </div>

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

        {tab === 'Overview' && <TabOverview item={item} refresh={refresh} id={reachOutId} />}
        {tab === 'Research' && <TabResearch item={item} refresh={refresh} id={reachOutId} />}
        {tab === 'Introduction Letter' && <TabLetter item={item} refresh={refresh} id={reachOutId} />}
        {tab === 'CV Notes' && <TabCVNotes item={item} refresh={refresh} id={reachOutId} />}
        {tab === 'Notes' && <TabNotes item={item} refresh={refresh} id={reachOutId} />}
      </div>
    </AppShell>
  )
}

function TabOverview({ item, refresh, id }: { item: ReachOut; refresh: () => void; id: number }) {
  const [editing, setEditing] = useState(false)
  const [values, setValues] = useState({
    company_name: item.company_name,
    website_url: item.website_url || '',
    linkedin_url: item.linkedin_url || '',
    industry: item.industry || '',
    location: item.location || '',
    company_size: item.company_size || '',
    contact_name: item.contact_name || '',
    contact_role: item.contact_role || '',
    contact_email: item.contact_email || '',
    follow_up_date: item.follow_up_date || '',
  })
  const [saving, setSaving] = useState(false)

  const set = (k: string) => (e: any) => setValues({ ...values, [k]: e.target.value })

  const save = async () => {
    setSaving(true)
    await updateReachOut(id, values)
    setSaving(false)
    setEditing(false)
    refresh()
  }

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Company Details</h3>
          {!editing && <button onClick={() => setEditing(true)} className="btn-ghost btn-sm">Edit</button>}
        </div>

        {editing ? (
          <div className="space-y-4">
            <div className="form-row">
              <div><label className="label">Company Name</label><input className="input" value={values.company_name} onChange={set('company_name')} /></div>
              <div><label className="label">Company Size</label><input className="input" value={values.company_size} onChange={set('company_size')} placeholder="e.g. 50-200 employees" /></div>
            </div>
            <div className="form-row">
              <div><label className="label">Website URL</label><input className="input" value={values.website_url} onChange={set('website_url')} /></div>
              <div><label className="label">LinkedIn URL</label><input className="input" value={values.linkedin_url} onChange={set('linkedin_url')} /></div>
            </div>
            <div className="form-row">
              <div><label className="label">Industry</label><input className="input" value={values.industry} onChange={set('industry')} /></div>
              <div><label className="label">Location</label><input className="input" value={values.location} onChange={set('location')} /></div>
            </div>
            <div className="form-row">
              <div><label className="label">Contact Name</label><input className="input" value={values.contact_name} onChange={set('contact_name')} placeholder="Optional" /></div>
              <div><label className="label">Contact Role</label><input className="input" value={values.contact_role} onChange={set('contact_role')} placeholder="Optional" /></div>
            </div>
            <div className="form-row">
              <div><label className="label">Contact Email</label><input className="input" value={values.contact_email} onChange={set('contact_email')} placeholder="Optional" /></div>
              <div><label className="label">Follow-up Date</label><input type="date" className="input" value={values.follow_up_date} onChange={set('follow_up_date')} /></div>
            </div>
            <div className="flex gap-2">
              <button onClick={save} disabled={saving} className="btn-primary btn-sm">{saving ? 'Saving...' : 'Save'}</button>
              <button onClick={() => setEditing(false)} className="btn-ghost btn-sm">Cancel</button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <InfoCard label="Website" value={item.website_url} />
            <InfoCard label="LinkedIn" value={item.linkedin_url} />
            <InfoCard label="Company Size" value={item.company_size} />
            <InfoCard label="Contact" value={item.contact_name ? `${item.contact_name}${item.contact_role ? ` (${item.contact_role})` : ''}` : null} />
            <InfoCard label="Contact Email" value={item.contact_email} />
            <InfoCard label="Follow-up Date" value={item.follow_up_date} />
          </div>
        )}
      </div>

      <div className="card p-5 bg-brand-50 border-brand-100">
        <h3 className="font-semibold text-gray-900 text-sm mb-2">How this works</h3>
        <p className="text-sm text-gray-700 leading-relaxed">
          Ollama runs locally and has no internet access, so it cannot research this company itself.
          Fill in the Research tab yourself, or ask an assistant with web access to research the company
          and paste the findings in. Once research is in place, the Introduction Letter tab can draft a
          first pass with the local AI, ready for you to edit.
        </p>
      </div>
    </div>
  )
}

function TabResearch({ item, refresh, id }: { item: ReachOut; refresh: () => void; id: number }) {
  const [editing, setEditing] = useState(false)
  const [values, setValues] = useState({
    research_summary: item.research_summary || '',
    culture_notes: item.culture_notes || '',
    tech_security_notes: item.tech_security_notes || '',
    recent_news: item.recent_news || '',
    angle: item.angle || '',
  })
  const [saving, setSaving] = useState(false)

  const set = (k: string) => (e: any) => setValues({ ...values, [k]: e.target.value })

  const save = async () => {
    setSaving(true)
    await updateReachOut(id, values)
    setSaving(false)
    setEditing(false)
    refresh()
  }

  const hasAny = item.research_summary || item.culture_notes || item.tech_security_notes || item.recent_news || item.angle

  if (!hasAny && !editing) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">No research yet. Add what you know about the business, its culture, and why it is worth reaching out to.</p>
        <button onClick={() => setEditing(true)} className="btn-primary">Add Research</button>
      </div>
    )
  }

  const fields: { key: keyof typeof values; label: string; placeholder: string; rows: number }[] = [
    { key: 'research_summary', label: 'Business Overview', placeholder: 'What the company does, market position, size, recent direction...', rows: 5 },
    { key: 'culture_notes', label: 'Culture', placeholder: 'Values, working style, public culture signals (careers page, Glassdoor, employee posts)...', rows: 4 },
    { key: 'tech_security_notes', label: 'Tech / Security Posture', placeholder: 'Known stack, vendors, past incidents, job ads mentioning security tooling...', rows: 4 },
    { key: 'recent_news', label: 'Recent News', placeholder: 'Funding, expansion, leadership changes, incidents...', rows: 3 },
    { key: 'angle', label: 'Angle', placeholder: 'Why reach out now, and what specifically to pitch them on...', rows: 3 },
  ]

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Company Research</h3>
          {!editing && <button onClick={() => setEditing(true)} className="btn-secondary btn-sm">Edit</button>}
        </div>

        {editing ? (
          <div className="space-y-4">
            {fields.map((f) => (
              <div key={f.key}>
                <label className="label">{f.label}</label>
                <textarea className="textarea w-full" rows={f.rows} value={values[f.key]} onChange={set(f.key)} placeholder={f.placeholder} />
              </div>
            ))}
            <div className="flex gap-2">
              <button onClick={save} disabled={saving} className="btn-primary btn-sm">{saving ? 'Saving...' : 'Save'}</button>
              <button onClick={() => setEditing(false)} className="btn-ghost btn-sm">Cancel</button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {fields.map((f) => item[f.key] && (
              <div key={f.key}>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{f.label}</h4>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{item[f.key]}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function TabLetter({ item, refresh, id }: { item: ReachOut; refresh: () => void; id: number }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(item.intro_letter || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    await updateReachOut(id, { intro_letter: value })
    setSaving(false)
    setEditing(false)
    refresh()
  }

  if (!item.intro_letter && !editing) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-sm mb-4">No introduction letter yet. Generate a first draft with the local AI or write your own.</p>
        <div className="flex items-center justify-center gap-3">
          {item.research_summary ? (
            <AIButton
              label="Generate Introduction Letter"
              loadingLabel="Writing..."
              onClick={async () => { await generateReachOutLetter(id); refresh() }}
            />
          ) : (
            <p className="text-xs text-gray-400">Add company research first for a usable draft.</p>
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
          {item.research_summary && (
            <AIButton label="Regenerate" loadingLabel="Writing..." onClick={async () => { await generateReachOutLetter(id); refresh() }} variant="secondary" />
          )}
          {!editing && <button onClick={() => { setValue(item.intro_letter || ''); setEditing(true) }} className="btn-secondary">Edit</button>}
        </div>
        <div className="flex gap-2">
          <a href={exportReachOut(id, 'md', 'intro-letter')} download className="btn-ghost btn-sm">MD</a>
          <a href={exportReachOut(id, 'docx', 'intro-letter')} download className="btn-ghost btn-sm">DOCX</a>
          <a href={exportReachOut(id, 'pdf', 'intro-letter')} download className="btn-ghost btn-sm">PDF</a>
        </div>
      </div>

      {editing ? (
        <div className="card">
          <textarea
            className="w-full p-6 text-sm text-gray-800 border-0 focus:ring-0 outline-none resize-none font-sans leading-relaxed"
            rows={24}
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
          <div className="prose-cv max-w-none whitespace-pre-wrap">{item.intro_letter}</div>
        </div>
      )}
      <BannedPhrasesWidget />
    </div>
  )
}

function TabCVNotes({ item, refresh, id }: { item: ReachOut; refresh: () => void; id: number }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(item.cv_notes || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    await updateReachOut(id, { cv_notes: value })
    setSaving(false)
    setEditing(false)
    refresh()
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-gray-900">CV Emphasis Notes</h3>
          <p className="text-xs text-gray-400 mt-0.5">Notes on which parts of your master CV to lead with when sending it speculatively to this company (not a full tailored CV, just what to emphasise).</p>
        </div>
        {!editing && <button onClick={() => { setValue(item.cv_notes || ''); setEditing(true) }} className="btn-secondary btn-sm">Edit</button>}
      </div>
      {editing ? (
        <>
          <textarea
            className="textarea w-full"
            rows={14}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. Lead with the Cortex XDR migration and the SOC team build given their growth stage; downplay desktop support history."
          />
          <div className="flex gap-2 mt-3">
            <button onClick={save} disabled={saving} className="btn-primary btn-sm">Save</button>
            <button onClick={() => setEditing(false)} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </>
      ) : (
        <div className="prose-cv whitespace-pre-wrap text-sm text-gray-700 min-h-[100px]">
          {item.cv_notes || <span className="text-gray-400">No notes yet.</span>}
        </div>
      )}
    </div>
  )
}

function TabNotes({ item, refresh, id }: { item: ReachOut; refresh: () => void; id: number }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(item.notes || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    await updateReachOut(id, { notes: value })
    setSaving(false)
    setEditing(false)
    refresh()
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Notes</h3>
        {!editing && <button onClick={() => { setValue(item.notes || ''); setEditing(true) }} className="btn-secondary btn-sm">Edit</button>}
      </div>
      {editing ? (
        <>
          <textarea
            className="textarea w-full"
            rows={16}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Anything else worth tracking: who referred you, timing considerations, follow-up plan..."
          />
          <div className="flex gap-2 mt-3">
            <button onClick={save} disabled={saving} className="btn-primary btn-sm">Save</button>
            <button onClick={() => setEditing(false)} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </>
      ) : (
        <div className="prose-cv whitespace-pre-wrap text-sm text-gray-700 min-h-[100px]">
          {item.notes || <span className="text-gray-400">No notes yet.</span>}
        </div>
      )}
    </div>
  )
}

function InfoCard({ label, value }: { label: string; value: string | undefined | null }) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg">
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm font-medium text-gray-900 break-words">{value || '-'}</p>
    </div>
  )
}
