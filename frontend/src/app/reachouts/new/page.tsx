'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import { createReachOut } from '@/lib/api'

export default function NewReachOutPage() {
  const router = useRouter()
  const [details, setDetails] = useState({ company_name: '', website_url: '', linkedin_url: '', industry: '', location: '' })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (k: string) => (e: any) => setDetails({ ...details, [k]: e.target.value })

  const handleCreate = async () => {
    if (!details.company_name.trim()) {
      setError('Company name is required.')
      return
    }
    setCreating(true)
    setError(null)
    try {
      const r: any = await createReachOut({
        ...details,
        date_identified: new Date().toISOString().split('T')[0],
      })
      router.push(`/reachouts/${r.id}`)
    } catch (e: any) {
      setError(e.message)
      setCreating(false)
    }
  }

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-6 py-8">
        <PageHeader
          title="New Reach Out"
          description="Just the basics to get started. Research, the introduction letter, and CV notes are all added on the next page."
        />

        <div className="card p-5 space-y-4">
          <div>
            <label className="label">Company Name *</label>
            <input className="input" value={details.company_name} onChange={set('company_name')} placeholder="Acme Security Ltd" />
          </div>
          <div className="form-row">
            <div>
              <label className="label">Website URL</label>
              <input className="input" value={details.website_url} onChange={set('website_url')} placeholder="https://acme.co.nz" />
            </div>
            <div>
              <label className="label">LinkedIn URL</label>
              <input className="input" value={details.linkedin_url} onChange={set('linkedin_url')} placeholder="https://linkedin.com/company/acme" />
            </div>
          </div>
          <div className="form-row">
            <div>
              <label className="label">Industry</label>
              <input className="input" value={details.industry} onChange={set('industry')} placeholder="Financial Services" />
            </div>
            <div>
              <label className="label">Location</label>
              <input className="input" value={details.location} onChange={set('location')} placeholder="Auckland, NZ" />
            </div>
          </div>
        </div>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="flex justify-end mt-4">
          <button onClick={handleCreate} disabled={creating} className="btn-primary">
            {creating ? 'Creating...' : 'Create Reach Out'}
          </button>
        </div>
      </div>
    </AppShell>
  )
}
