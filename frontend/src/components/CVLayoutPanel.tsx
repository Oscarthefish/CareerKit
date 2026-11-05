'use client'
// Layout controls + preview for any CV (Master CV, Custom CV, Tailored CV).
//
// Layout is deliberately separate from tailoring: nothing here changes what
// the CV says, only how it's laid out. The backend (/api/cv/layout) returns
// the CV exactly as the exporters will lay it out plus its real rendered page
// count, so the formatted preview, the page view and the downloads all agree.
import { useEffect, useMemo, useState } from 'react'
import CVRenderer from './CVRenderer'
import { cvLayout, type CVLayoutParams } from '@/lib/api'
import type { CVLayoutResult } from '@/lib/types'

type Target = 'two_page' | 'unrestricted'
type SpacingPreset = 'standard' | 'compact'

interface Props {
  markdown: string
  /** Remembered layout choices are kept per kind of CV. */
  storageKey: string
  defaultTarget: Target
  exportUrl: (fmt: 'md' | 'docx' | 'pdf', params: CVLayoutParams) => string
  /** Extra buttons (e.g. Edit) shown beside the exports. */
  actions?: React.ReactNode
}

interface Saved {
  target: Target
  spacing: SpacingPreset
  order: string[]
  hide: string[]
}

function load(key: string, fallback: Saved): Saved {
  try {
    const raw = window.localStorage.getItem(`careerkit:cv-layout:${key}`)
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback
  } catch {
    return fallback
  }
}

function store(key: string, value: Saved) {
  try {
    window.localStorage.setItem(`careerkit:cv-layout:${key}`, JSON.stringify(value))
  } catch {
    // Private mode / storage disabled - choices just won't be remembered.
  }
}

const titleCase = (s: string) => s.toLowerCase().replace(/(^|\s|&|\/)(\w)/g, (m) => m.toUpperCase())

export default function CVLayoutPanel({ markdown, storageKey, defaultTarget, exportUrl, actions }: Props) {
  const fallback: Saved = { target: defaultTarget, spacing: 'standard', order: [], hide: [] }
  const [opts, setOpts] = useState<Saved>(fallback)
  const [ready, setReady] = useState(false)
  const [result, setResult] = useState<CVLayoutResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState<'formatted' | 'pages'>('formatted')
  const [showSections, setShowSections] = useState(false)
  const [pdfNonce, setPdfNonce] = useState(0)

  useEffect(() => {
    setOpts(load(storageKey, fallback))
    setReady(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey])

  const update = (patch: Partial<Saved>) => {
    const next = { ...opts, ...patch }
    setOpts(next)
    store(storageKey, next)
  }

  const params: CVLayoutParams = useMemo(
    () => ({ target: opts.target, spacing: opts.spacing, order: opts.order, hide: opts.hide }),
    [opts],
  )

  useEffect(() => {
    if (!ready || !markdown) return
    let cancelled = false
    setLoading(true)
    const t = setTimeout(async () => {
      try {
        const r = await cvLayout(markdown, params)
        if (!cancelled) {
          setResult(r)
          setError(null)
          setPdfNonce((n) => n + 1)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Could not lay out the CV')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 250)
    return () => {
      cancelled = true
      clearTimeout(t)
    }
  }, [markdown, params, ready])

  // Sections in display order: saved order first, then any new ones.
  const allSections = result?.sections ?? []
  const ordered = [
    ...opts.order.filter((s) => allSections.includes(s)),
    ...allSections.filter((s) => !opts.order.includes(s)),
  ]
  const move = (name: string, delta: number) => {
    const list = [...ordered]
    const i = list.indexOf(name)
    const j = i + delta
    if (i < 0 || j < 0 || j >= list.length) return
    ;[list[i], list[j]] = [list[j], list[i]]
    update({ order: list })
  }
  const toggle = (name: string) =>
    update({ hide: opts.hide.includes(name) ? opts.hide.filter((h) => h !== name) : [...opts.hide, name] })

  const fit = result?.fit
  const hiddenCount = opts.hide.filter((h) => allSections.includes(h)).length

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="card p-3 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label">Target length</label>
            <select className="input text-sm" value={opts.target} onChange={(e) => update({ target: e.target.value as Target })}>
              <option value="two_page">Two-page application CV</option>
              <option value="unrestricted">Unrestricted (master CV)</option>
            </select>
          </div>
          <div>
            <label className="label">Spacing</label>
            <select className="input text-sm" value={opts.spacing} onChange={(e) => update({ spacing: e.target.value as SpacingPreset })}>
              <option value="standard">Standard</option>
              <option value="compact">Compact</option>
            </select>
          </div>
          <button type="button" onClick={() => setShowSections((v) => !v)} className="btn-secondary btn-sm">
            Sections{hiddenCount ? ` (${hiddenCount} hidden)` : ''}
          </button>
          <div className="flex-1" />
          <div className="flex flex-wrap gap-2">
            {actions}
            <a href={exportUrl('md', params)} download className="btn-ghost btn-sm">MD</a>
            <a href={exportUrl('docx', params)} download className="btn-ghost btn-sm">DOCX</a>
            <a href={exportUrl('pdf', params)} download className="btn-ghost btn-sm">PDF</a>
          </div>
        </div>

        {showSections && (
          <div className="border-t pt-3" style={{ borderColor: 'var(--border-default)' }}>
            <p className="text-xs text-gray-500 mb-2">
              Order and include sections for this layout. Hidden sections stay in your CV; they&apos;re just left out of the preview and exports.
            </p>
            <ul className="space-y-1">
              {ordered.map((name, i) => (
                <li key={name} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={!opts.hide.includes(name)} onChange={() => toggle(name)} aria-label={`Include ${name}`} />
                  <span className={`flex-1 ${opts.hide.includes(name) ? 'text-gray-400 line-through' : 'text-gray-800'}`}>{titleCase(name)}</span>
                  <button type="button" className="btn-ghost btn-sm" disabled={i === 0} onClick={() => move(name, -1)} aria-label={`Move ${name} up`}>↑</button>
                  <button type="button" className="btn-ghost btn-sm" disabled={i === ordered.length - 1} onClick={() => move(name, 1)} aria-label={`Move ${name} down`}>↓</button>
                </li>
              ))}
            </ul>
            {(opts.order.length > 0 || opts.hide.length > 0) && (
              <button type="button" className="text-xs text-brand-600 hover:underline mt-2" onClick={() => update({ order: [], hide: [] })}>
                Reset to the CV&apos;s own order
              </button>
            )}
          </div>
        )}

        {/* Page count + notices */}
        <div className="flex flex-wrap items-center gap-3 text-xs" aria-live="polite">
          {fit && (
            <span className={`font-medium ${fit.fits ? 'text-gray-700' : 'text-amber-700'}`}>
              {fit.pages} page{fit.pages === 1 ? '' : 's'} on A4
              {fit.target_pages ? ` · target ${fit.target_pages}` : ''}
            </span>
          )}
          {fit?.tightened && <span className="text-gray-500">Spacing closed up slightly to avoid a nearly empty last page.</span>}
          {loading && <span className="text-gray-400">Measuring…</span>}
          {error && <span className="text-red-600">{error}</span>}
          <div className="flex-1" />
          <div className="inline-flex rounded-md border overflow-hidden" style={{ borderColor: 'var(--border-default)' }}>
            {(['formatted', 'pages'] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                className={`px-2.5 py-1 ${view === v ? 'bg-brand-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                {v === 'formatted' ? 'Formatted' : 'Page view (PDF)'}
              </button>
            ))}
          </div>
        </div>

        {fit && !fit.fits && fit.notice && (
          <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 space-y-2">
            <p>{fit.notice}</p>
            {fit.suggestions.length > 0 && (
              <>
                <p className="font-semibold">Suggested edits to review (nothing has been changed):</p>
                <ul className="list-disc pl-5 space-y-1">
                  {fit.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </>
            )}
          </div>
        )}
      </div>

      {/* Preview */}
      {view === 'formatted' ? (
        <CVRenderer markdown={result?.markdown ?? markdown} />
      ) : (
        <iframe
          key={pdfNonce}
          title="CV page view"
          src={exportUrl('pdf', { ...params, inline: true })}
          className="w-full rounded-lg border bg-gray-100"
          style={{ height: '1100px', borderColor: 'var(--border-default)' }}
        />
      )}
    </div>
  )
}
