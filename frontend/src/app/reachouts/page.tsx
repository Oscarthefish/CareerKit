'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import { getReachOuts, deleteReachOut } from '@/lib/api'
import type { ReachOutSummary } from '@/lib/types'

const STATUS_COLORS: Record<string, string> = {
  identified: 'badge-gray',
  researched: 'badge-blue',
  letter_drafted: 'badge-purple',
  sent: 'badge-green',
  follow_up_due: 'badge-yellow',
  responded: 'badge-green',
  archived: 'badge-gray',
}

export default function ReachOutsPage() {
  const [items, setItems] = useState<ReachOutSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  const load = async () => {
    setLoading(true)
    try {
      const data: any = await getReachOuts()
      setItems(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'all' ? items : items.filter((r) => r.status === filter)
  const statuses = ['all', 'identified', 'researched', 'letter_drafted', 'sent', 'follow_up_due', 'responded', 'archived']

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.preventDefault()
    if (!confirm('Delete this reach out?')) return
    await deleteReachOut(id)
    setItems(items.filter((r) => r.id !== id))
  }

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <PageHeader
          title="Reach Outs"
          description="Speculative introductions to companies that aren't necessarily hiring right now. Research the business, then send a tailored introduction and CV so they think of you when something opens up."
          action={
            <Link href="/reachouts/new" className="btn-primary">New Reach Out</Link>
          }
        />

        <div className="flex items-center gap-2 mb-6 flex-wrap">
          {statuses.map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === status
                  ? 'bg-brand-700 text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-brand-300'
              }`}
            >
              {status === 'all'
                ? `All (${items.length})`
                : `${status.replace(/_/g, ' ')} (${items.filter((r) => r.status === status).length})`}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-gray-400 text-sm">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="card p-12 text-center">
            <div className="text-4xl mb-4">✉</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No reach outs yet</h2>
            <p className="text-sm text-gray-500 mb-6">
              Identify a company you would like to introduce yourself to, even if they are not actively hiring.
            </p>
            <Link href="/reachouts/new" className="btn-primary">Start a Reach Out</Link>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((r) => (
              <Link
                key={r.id}
                href={`/reachouts/${r.id}`}
                className="card flex items-center justify-between px-5 py-4 hover:border-brand-200 transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 truncate">{r.company_name}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                    {r.industry && <span>{r.industry}</span>}
                    {r.location && <span>· {r.location}</span>}
                    <span>· identified {new Date(r.created_at).toLocaleDateString('en-NZ')}</span>
                    {r.follow_up_date && <span>· follow up {r.follow_up_date}</span>}
                  </div>
                  <div className="flex items-center gap-1.5 mt-2">
                    <Pip active={r.has_research} label="Research" />
                    <Pip active={r.has_letter} label="Introduction Letter" />
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <span className={STATUS_COLORS[r.status] || 'badge-gray'}>{r.status.replace(/_/g, ' ')}</span>
                  <button
                    onClick={(e) => handleDelete(r.id, e)}
                    className="text-gray-300 hover:text-red-400 text-sm opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    ✕
                  </button>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}

function Pip({ active, label }: { active: boolean; label: string }) {
  return (
    <span title={label} className={`w-2 h-2 rounded-full ${active ? 'bg-green-400' : 'bg-gray-200'}`} />
  )
}
