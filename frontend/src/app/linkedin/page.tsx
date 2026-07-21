'use client'
import { useState } from 'react'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import AIButton from '@/components/AIButton'
import { generateLinkedIn } from '@/lib/api'

export default function LinkedInPage() {
  const [result, setResult] = useState<any>(null)
  const [copied, setCopied] = useState<string | null>(null)

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-6 py-8">
        <PageHeader
          title="LinkedIn Builder"
          description="Generate LinkedIn content from your master profile. More personal than your CV but still professional."
        />

        {!result ? (
          <div className="card p-12 text-center">
            <div className="text-4xl mb-4">◎</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Generate LinkedIn Content</h2>
            <p className="text-sm text-gray-500 mb-6">
              This generates your headline, About section, experience summaries, skills list, and a recruiter intro message.
              Make sure your profile is complete before generating.
            </p>
            <AIButton
              label="Generate LinkedIn Content"
              loadingLabel="Generating..."
              onClick={async () => {
                const data: any = await generateLinkedIn()
                setResult(data)
              }}
            />
          </div>
        ) : (
          <div className="space-y-5">
            <div className="flex justify-end">
              <AIButton
                label="Regenerate"
                loadingLabel="Generating..."
                onClick={async () => {
                  const data: any = await generateLinkedIn()
                  setResult(data)
                }}
                variant="secondary"
              />
            </div>

            {/* Headline */}
            {result.headline && (
              <ContentBlock
                title="LinkedIn Headline"
                content={result.headline}
                onCopy={() => copy(result.headline, 'headline')}
                copied={copied === 'headline'}
                hint="Under 220 characters. Appears under your name."
              />
            )}

            {/* About */}
            {result.about && (
              <ContentBlock
                title="About Section"
                content={result.about}
                onCopy={() => copy(result.about, 'about')}
                copied={copied === 'about'}
                hint="3-4 paragraphs. Should sound human, not corporate."
                multiline
              />
            )}

            {/* Recruiter intro */}
            {result.recruiter_intro_message && (
              <ContentBlock
                title="Recruiter Intro Message"
                content={result.recruiter_intro_message}
                onCopy={() => copy(result.recruiter_intro_message, 'intro')}
                copied={copied === 'intro'}
                hint="Under 300 characters. For InMail or connection requests."
              />
            )}

            {/* Short bio */}
            {result.short_bio && (
              <ContentBlock
                title="Short Professional Bio"
                content={result.short_bio}
                onCopy={() => copy(result.short_bio, 'bio')}
                copied={copied === 'bio'}
                hint="One paragraph. Good for speaker profiles or conference pages."
                multiline
              />
            )}

            {/* Skills list */}
            {result.skills_list?.length > 0 && (
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-gray-900 text-sm">Skills to Add</h3>
                    <p className="text-xs text-gray-400 mt-0.5">Pin these to your LinkedIn skills section</p>
                  </div>
                  <button
                    onClick={() => copy(result.skills_list.join('\n'), 'skills')}
                    className="btn-ghost btn-sm"
                  >
                    {copied === 'skills' ? 'Copied!' : 'Copy All'}
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {result.skills_list.map((skill: string, i: number) => (
                    <span key={i} className="badge-blue">{skill}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Experience summaries */}
            {result.experience_summaries?.length > 0 && (
              <div className="card p-5">
                <h3 className="font-semibold text-gray-900 text-sm mb-4">Experience Summaries</h3>
                <div className="space-y-4">
                  {result.experience_summaries.map((exp: any, i: number) => (
                    <div key={i} className="p-4 bg-gray-50 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <p className="font-medium text-sm text-gray-900">{exp.role}</p>
                          {exp.company && <p className="text-xs text-gray-500">{exp.company}</p>}
                        </div>
                        <button
                          onClick={() => copy(Array.isArray(exp.summary) ? exp.summary.join('\n') : exp.summary, `exp-${i}`)}
                          className="btn-ghost btn-sm"
                        >
                          {copied === `exp-${i}` ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                      {Array.isArray(exp.summary) ? (
                        <ul className="space-y-1">
                          {exp.summary.map((s: string, j: number) => (
                            <li key={j} className="text-xs text-gray-700 flex gap-1.5">
                              <span className="text-gray-400">-</span> {s}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-gray-700">{exp.summary}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  )
}

function ContentBlock({ title, content, onCopy, copied, hint, multiline }: {
  title: string; content: string; onCopy: () => void; copied: boolean; hint?: string; multiline?: boolean
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
          {hint && <p className="text-xs text-gray-400 mt-0.5">{hint}</p>}
        </div>
        <button onClick={onCopy} className="btn-ghost btn-sm">
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div className={`${multiline ? 'whitespace-pre-wrap' : ''} text-sm text-gray-800 bg-gray-50 rounded-lg p-4 leading-relaxed`}>
        {content}
      </div>
    </div>
  )
}
