'use client'
import { useEffect, useState, useRef } from 'react'
import { getStyle, updateStyle } from '@/lib/api'

export default function BannedPhrasesWidget() {
  const [phrases, setPhrases] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getStyle().then((data: any) => {
      const raw = data.avoid_phrases
      setPhrases(Array.isArray(raw) ? raw : (typeof raw === 'string' ? JSON.parse(raw || '[]') : []))
    })
  }, [])

  const save = async (updated: string[]) => {
    setSaving(true)
    try {
      await updateStyle({ avoid_phrases: updated })
    } finally {
      setSaving(false)
    }
  }

  const addPhrase = () => {
    const trimmed = input.trim()
    if (!trimmed || phrases.includes(trimmed)) {
      setInput('')
      return
    }
    const updated = [...phrases, trimmed]
    setPhrases(updated)
    setInput('')
    save(updated)
  }

  const removePhrase = (phrase: string) => {
    const updated = phrases.filter(p => p !== phrase)
    setPhrases(updated)
    save(updated)
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); addPhrase() }
  }

  return (
    <div className="card p-4">
      <button
        className="flex items-center justify-between w-full"
        onClick={() => { setExpanded(!expanded); if (!expanded) setTimeout(() => inputRef.current?.focus(), 50) }}
      >
        <h3 className="text-sm font-semibold text-gray-700">Excluded Phrases</h3>
        <span className="text-xs text-gray-400 flex items-center gap-1">
          {phrases.length > 0 && <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-medium">{phrases.length}</span>}
          <span>{expanded ? '▲' : '▼'}</span>
        </span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-gray-400">
            Words and phrases the AI will never use. Add your own here — a base list of clichés is always applied automatically.
          </p>

          {phrases.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {phrases.map(phrase => (
                <span
                  key={phrase}
                  className="inline-flex items-center gap-1 bg-red-50 text-red-800 text-xs px-2 py-0.5 rounded-full border border-red-200"
                >
                  {phrase}
                  <button
                    onClick={() => removePhrase(phrase)}
                    className="text-red-400 hover:text-red-700 leading-none ml-0.5"
                    title="Remove"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Add a phrase..."
              className="input flex-1 text-xs py-1.5"
            />
            <button
              onClick={addPhrase}
              disabled={!input.trim() || saving}
              className="btn-primary btn-sm px-3"
            >
              {saving ? '...' : 'Add'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
