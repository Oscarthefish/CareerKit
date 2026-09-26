'use client'
import { useState } from 'react'
import { createEvidence } from '@/lib/api'

interface Props {
  skillName: string
  context?: string
}

/** The Master CV Feedback Loop, in one place: when CareerKit finds a gap
 * (in one Job Match report, or a pattern across many), this asks the user
 * directly rather than inventing anything, and — only if they confirm —
 * captures it once as a new EvidenceItem so every future application
 * benefits from it. */
export default function EvidenceFeedbackWidget({ skillName, context }: Props) {
  const [stage, setStage] = useState<'ask' | 'form' | 'done' | 'dismissed'>('ask')
  const [description, setDescription] = useState('')
  const [outcome, setOutcome] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!description.trim()) return
    setSaving(true)
    try {
      await createEvidence({
        title: skillName,
        description,
        skills_demonstrated: [skillName],
        outcome: outcome || undefined,
        confidence: 'confirmed_hands_on',
        confidentiality_level: 'cv_safe',
        source: context ? `Master CV feedback loop — ${context}` : 'Master CV feedback loop',
      })
      setStage('done')
    } finally {
      setSaving(false)
    }
  }

  if (stage === 'done') {
    return <p className="text-xs text-green-700 mt-1">✓ Added to your Master CV — regenerate Job Match to see it reflected.</p>
  }
  if (stage === 'dismissed') {
    return <p className="text-xs text-gray-400 mt-1">Noted — not added.</p>
  }
  if (stage === 'form') {
    return (
      <div className="mt-2 p-3 bg-white border border-gray-200 rounded-lg space-y-2">
        <p className="text-xs font-medium text-gray-700">
          Tell CareerKit about it — this is added as a new piece of evidence on your Master CV, not invented.
        </p>
        <textarea
          className="textarea w-full text-xs"
          rows={2}
          placeholder="What did you do? (tool, context, scale)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <input
          className="input text-xs"
          placeholder="Outcome (optional)"
          value={outcome}
          onChange={(e) => setOutcome(e.target.value)}
        />
        <div className="flex gap-2">
          <button onClick={() => setStage('ask')} className="btn-ghost btn-sm">Cancel</button>
          <button onClick={handleSave} disabled={saving || !description.trim()} className="btn-primary btn-sm">
            {saving ? 'Saving...' : 'Add to Master CV'}
          </button>
        </div>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-2 mt-1">
      <span className="text-xs text-gray-500">Have you done this?</span>
      <button onClick={() => setStage('form')} className="text-xs text-brand-700 font-medium hover:underline">Yes</button>
      <button onClick={() => setStage('dismissed')} className="text-xs text-gray-400 hover:underline">No</button>
      <button onClick={() => setStage('dismissed')} className="text-xs text-gray-400 hover:underline">Not sure</button>
    </div>
  )
}
