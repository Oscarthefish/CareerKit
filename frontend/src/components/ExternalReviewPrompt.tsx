'use client'
// Builds a review-and-rewrite prompt for an external assistant (ChatGPT) from
// the job advert and the current cover letter. Nothing is sent anywhere from
// here: the prompt is copied to the clipboard and shown so it can be pasted.
import { useState } from 'react'
import { coverLetterReviewPrompt } from '@/lib/api'
import { ExternalLinkIcon } from './ui/Icons'

export default function ExternalReviewPrompt({ appId }: { appId: number }) {
  const [prompt, setPrompt] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch {
      setCopied(false) // clipboard blocked - the text box below is the fallback
    }
  }

  const build = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await coverLetterReviewPrompt(appId)
      setPrompt(r.prompt)
      await copy(r.prompt)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not build the prompt')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button onClick={build} disabled={loading} className="btn-secondary">
        {loading ? 'Building...' : 'Review with ChatGPT'}
      </button>
      {error && <span className="text-xs text-red-600 self-center">{error}</span>}
      {prompt !== null && (
        <div className="basis-full card p-4 space-y-3 mt-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm text-gray-700 flex-1 min-w-[16rem]">
              {copied
                ? 'Prompt copied. Paste it into ChatGPT, then use Edit here to paste back the version you want.'
                : 'Copy this prompt into ChatGPT, then use Edit here to paste back the version you want.'}
            </p>
            <button onClick={() => copy(prompt)} className="btn-secondary btn-sm">{copied ? 'Copied' : 'Copy prompt'}</button>
            <a href="https://chatgpt.com/" target="_blank" rel="noopener noreferrer" className="btn-primary btn-sm inline-flex items-center gap-1.5">
              <ExternalLinkIcon width={14} height={14} />
              Open ChatGPT
            </a>
            <button onClick={() => setPrompt(null)} className="btn-ghost btn-sm">Close</button>
          </div>
          <textarea
            readOnly
            value={prompt}
            rows={12}
            onFocus={(e) => e.currentTarget.select()}
            className="input w-full font-mono text-xs leading-relaxed"
            aria-label="ChatGPT review prompt"
          />
        </div>
      )}
    </>
  )
}
