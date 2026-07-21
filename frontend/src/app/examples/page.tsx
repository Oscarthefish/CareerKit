'use client'
import { useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import FileUpload from '@/components/FileUpload'
import { getExamples, uploadExample, deleteExample } from '@/lib/api'
import type { ExampleCV } from '@/lib/types'

export default function ExamplesPage() {
  const [examples, setExamples] = useState<ExampleCV[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<ExampleCV | null>(null)

  const load = async () => {
    setLoading(true)
    const data: any = await getExamples()
    setExamples(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleUpload = async (file: File) => {
    await uploadExample(file)
    await load()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Remove this example?')) return
    await deleteExample(id)
    if (selected?.id === id) setSelected(null)
    await load()
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <PageHeader
          title="Example CVs"
          description="Upload CVs you admire for style inspiration. CareerKit extracts structure and formatting patterns only, not personal content."
        />

        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
          <strong>Privacy notice:</strong> Only upload CVs where you have permission to use them as style examples.
          CareerKit extracts section structure, tone, and formatting patterns only. No personal details are used.
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Upload + list */}
          <div className="lg:col-span-1 space-y-4">
            <FileUpload
              label="Upload example CV"
              hint="PDF, Word, text, or Markdown"
              accept=".pdf,.docx,.txt,.md"
              onFile={handleUpload}
            />

            {loading ? (
              <div className="text-sm text-gray-400">Loading...</div>
            ) : examples.length === 0 ? (
              <div className="text-sm text-gray-400 text-center py-4">No examples uploaded yet.</div>
            ) : (
              <div className="space-y-2">
                {examples.map((ex) => (
                  <div
                    key={ex.id}
                    onClick={() => setSelected(ex)}
                    className={`card p-4 cursor-pointer transition-colors ${selected?.id === ex.id ? 'border-brand-400 bg-brand-50' : 'hover:border-gray-300'}`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900 truncate">{ex.original_filename}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {ex.sections?.length} sections · {ex.tone} tone
                        </p>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(ex.id) }}
                        className="text-red-300 hover:text-red-500 text-xs ml-2"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Analysis detail */}
          <div className="lg:col-span-2">
            {!selected ? (
              <div className="card p-12 text-center text-gray-400">
                <p className="text-sm">Select an example to see the analysis</p>
              </div>
            ) : (
              <div className="card p-6 space-y-5">
                <div className="flex items-start justify-between">
                  <h3 className="font-semibold text-gray-900">{selected.original_filename}</h3>
                  <div className="flex gap-2 text-xs">
                    {selected.tone && <span className="badge-blue">{selected.tone}</span>}
                    {selected.bullet_style && <span className="badge-gray">{selected.bullet_style} bullets</span>}
                  </div>
                </div>

                {selected.formatting_notes && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Formatting Notes</h4>
                    <p className="text-sm text-gray-700">{selected.formatting_notes}</p>
                  </div>
                )}

                {selected.section_order?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Section Order</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {selected.section_order.map((s, i) => (
                        <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                          <span className="text-gray-400">{i + 1}.</span> {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {selected.strengths?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">Strengths</h4>
                      <ul className="space-y-1">
                        {selected.strengths.map((s, i) => (
                          <li key={i} className="text-xs text-gray-700 flex gap-1.5">
                            <span className="text-green-400">+</span> {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selected.weaknesses?.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">Weaknesses</h4>
                      <ul className="space-y-1">
                        {selected.weaknesses.map((s, i) => (
                          <li key={i} className="text-xs text-gray-700 flex gap-1.5">
                            <span className="text-red-400">-</span> {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {selected.layout_ideas?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-brand-700 uppercase tracking-wide mb-2">Layout Ideas Worth Borrowing</h4>
                    <ul className="space-y-1">
                      {selected.layout_ideas.map((idea, i) => (
                        <li key={i} className="text-xs text-gray-700 flex gap-1.5">
                          <span className="text-brand-400">→</span> {idea}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
