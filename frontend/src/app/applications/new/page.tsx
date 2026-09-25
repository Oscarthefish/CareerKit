'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import FileUpload from '@/components/FileUpload'
import { createApplication, uploadJobDescription, analyzeJob } from '@/lib/api'

export default function NewApplicationPage() {
  const router = useRouter()
  const [step, setStep] = useState<'input' | 'details' | 'analyzing'>('input')
  const [jdText, setJdText] = useState('')
  const [inputMode, setInputMode] = useState<'paste' | 'upload'>('paste')
  const [details, setDetails] = useState({ company: '', role: '', recruiter_name: '', location: '', work_type: '', salary_range: '' })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handlePasteNext = () => {
    if (!jdText.trim()) {
      setError('Please paste the job description first.')
      return
    }
    setError(null)
    setStep('details')
  }

  const handleCreate = async () => {
    setCreating(true)
    setError(null)
    try {
      const app: any = await createApplication({
        ...details,
        job_description_raw: jdText || undefined,
      })
      if (jdText || app.job_description_raw) {
        setStep('analyzing')
        try {
          await analyzeJob(app.id)
        } catch (e) {
          // Analysis failed but app was created - still navigate
        }
      }
      router.push(`/applications/${app.id}`)
    } catch (e: any) {
      setError(e.message)
      setCreating(false)
    }
  }

  const set = (k: string) => (e: any) => setDetails({ ...details, [k]: e.target.value })

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-6 py-8">
        <PageHeader
          title="New Job Application"
          description="Paste or upload the job description to get started."
        />

        {step === 'analyzing' ? (
          <div className="card p-12 text-center">
            <div className="inline-block w-8 h-8 border-2 border-brand-600 border-t-transparent rounded-full animate-spin mb-4" />
            <h2 className="text-lg font-semibold text-gray-900 mb-1">Analysing job description...</h2>
            <p className="text-sm text-gray-500">Extracting role details, keywords, and requirements</p>
          </div>
        ) : step === 'input' ? (
          <div className="space-y-6">
            {/* Mode toggle */}
            <div className="flex rounded-lg border border-gray-200 p-1 bg-white w-fit">
              <button
                onClick={() => setInputMode('paste')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  inputMode === 'paste' ? 'bg-brand-700 text-white' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Paste Text
              </button>
              <button
                onClick={() => setInputMode('upload')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  inputMode === 'upload' ? 'bg-brand-700 text-white' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Upload File
              </button>
            </div>

            {inputMode === 'paste' ? (
              <div>
                <label className="label">Job Description</label>
                <textarea
                  className="textarea"
                  rows={16}
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  placeholder="Paste the full job description here. Include the responsibilities, requirements, company description, and any other details. The more complete this is, the better the analysis."
                />
                {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
                <div className="flex justify-end mt-4">
                  <button onClick={handlePasteNext} className="btn-primary">Continue</button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <FileUpload
                  label="Drop your job description here or click to browse"
                  hint="PDF, Word, plain text, or Markdown"
                  accept=".pdf,.docx,.txt,.md"
                  onFile={async (file) => {
                    const app: any = await createApplication({})
                    await uploadJobDescription(app.id, file)
                    router.push(`/applications/${app.id}`)
                  }}
                />
                <p className="text-xs text-gray-400 text-center">
                  Or{' '}
                  <button onClick={() => setInputMode('paste')} className="text-brand-600 hover:underline">
                    paste the job description as text
                  </button>
                </p>
              </div>
            )}

            <div className="pt-4 border-t border-gray-100">
              <p className="text-xs text-gray-400 mb-3">Or start without a job description and add it later:</p>
              <button
                onClick={() => setStep('details')}
                className="btn-secondary btn-sm"
              >
                Start with just the company and role name
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className={`p-4 rounded-xl text-sm ${jdText ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-500'}`}>
              {jdText
                ? `Job description ready (${jdText.length.toLocaleString()} characters). Analysis will run automatically.`
                : 'No job description. You can add it later on the application page.'}
            </div>

            <div className="card p-5 space-y-4">
              <h3 className="font-semibold text-gray-900 text-sm">Optional details</h3>
              <p className="text-xs text-gray-400 -mt-2">
                These will be auto-filled from the job description if you provided one. Add any you know already.
              </p>
              <div className="form-row">
                <div>
                  <label className="label">Company</label>
                  <input className="input" value={details.company} onChange={set('company')} placeholder="Acme Corp" />
                </div>
                <div>
                  <label className="label">Role Title</label>
                  <input className="input" value={details.role} onChange={set('role')} placeholder="SOC Analyst" />
                </div>
              </div>
              <div className="form-row">
                <div>
                  <label className="label">Recruiter Name</label>
                  <input className="input" value={details.recruiter_name} onChange={set('recruiter_name')} placeholder="Optional" />
                </div>
                <div>
                  <label className="label">Location</label>
                  <input className="input" value={details.location} onChange={set('location')} placeholder="Auckland, NZ" />
                </div>
              </div>
              <div className="form-row">
                <div>
                  <label className="label">Work Type</label>
                  <select className="input" value={details.work_type} onChange={set('work_type')}>
                    <option value="">Unknown</option>
                    <option>remote</option>
                    <option>hybrid</option>
                    <option>on-site</option>
                  </select>
                </div>
                <div>
                  <label className="label">Salary Range</label>
                  <input className="input" value={details.salary_range} onChange={set('salary_range')} placeholder="$90k-$110k" />
                </div>
              </div>
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <div className="flex justify-between">
              <button onClick={() => setStep('input')} className="btn-secondary">Back</button>
              <button onClick={handleCreate} disabled={creating} className="btn-primary">
                {creating ? 'Creating...' : 'Create Application'}
              </button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}
