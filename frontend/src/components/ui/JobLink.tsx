'use client'
import { useState } from 'react'
import { ExternalLinkIcon } from './Icons'

/** Only http(s) links are ever rendered as hrefs (the backend enforces the
 * same rule, this guards against anything stored before it did). */
export function safeJobHref(url: string | null | undefined): string | null {
  if (!url) return null
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : null
  } catch {
    return null
  }
}

/** "www.seek.co.nz" -> "seek.co.nz" - a readable "where I found it" label. */
export function jobLinkHost(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/** Header link to the original listing, with inline add/edit. */
export function JobLinkEditor({ url, onSave }: { url: string | null; onSave: (url: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(url || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const href = safeJobHref(url)

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      await onSave(value.trim())
      setEditing(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save the link')
    } finally {
      setSaving(false)
    }
  }

  if (editing) {
    return (
      <div className="mt-2">
        <div className="flex items-center gap-2">
          <input
            className="input text-sm max-w-md"
            value={value}
            autoFocus
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') save()
              if (e.key === 'Escape') { setValue(url || ''); setEditing(false) }
            }}
            placeholder="https://www.seek.co.nz/job/..."
          />
          <button onClick={save} disabled={saving} className="btn-primary btn-sm">{saving ? 'Saving...' : 'Save'}</button>
          <button onClick={() => { setValue(url || ''); setEditing(false); setError(null) }} className="btn-secondary btn-sm">Cancel</button>
        </div>
        <p className="text-xs text-gray-400 mt-1">Leave blank and save to remove the link.</p>
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 mt-2 text-sm">
      {href ? (
        <>
          <a href={href} target="_blank" rel="noopener noreferrer" className="btn-secondary btn-sm inline-flex items-center gap-1.5">
            <ExternalLinkIcon width={14} height={14} />
            View listing on {jobLinkHost(href)}
          </a>
          <button onClick={() => setEditing(true)} className="text-xs text-gray-500 hover:text-brand-600 underline">Edit link</button>
        </>
      ) : (
        <button onClick={() => setEditing(true)} className="btn-secondary btn-sm inline-flex items-center gap-1.5">
          <ExternalLinkIcon width={14} height={14} />
          Add job listing link
        </button>
      )}
    </div>
  )
}
