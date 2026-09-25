'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { aiHealth } from '@/lib/api'
import type { AIHealth } from '@/lib/types'

const nav = [
  { href: '/', label: 'Dashboard', icon: '⬡' },
  { href: '/profile', label: 'My Profile', icon: '◈' },
  { href: '/cv', label: 'Master CV', icon: '◻' },
  { href: '/applications', label: 'Applications', icon: '◷' },
  { href: '/reachouts', label: 'Reach Outs', icon: '✉' },
  { href: '/scanner', label: 'Job Scanner', icon: '◉' },
  { href: '/linkedin', label: 'LinkedIn', icon: '◎' },
  { href: '/examples', label: 'Example CVs', icon: '◫' },
  { href: '/settings', label: 'Settings', icon: '◈' },
]

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [aiStatus, setAiStatus] = useState<AIHealth | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    aiHealth()
      .then((h) => setAiStatus(h as AIHealth))
      .catch(() => setAiStatus({ status: 'error', url: '', model: '', model_available: false, available_models: [], message: 'Ollama offline' }))
  }, [])

  useEffect(() => {
    const handleApiError = (event: Event) => {
      setApiError((event as CustomEvent<string>).detail || 'The request failed. Please try again.')
    }
    window.addEventListener('careerkit:api-error', handleApiError)
    return () => window.removeEventListener('careerkit:api-error', handleApiError)
  }, [])

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname.startsWith(href)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-56' : 'w-14'} flex-shrink-0 bg-brand-950 text-white flex flex-col transition-all duration-200`}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-brand-800">
          <div className="w-7 h-7 bg-brand-500 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
            CK
          </div>
          {sidebarOpen && (
            <span className="font-semibold text-sm text-white truncate">CareerKit Local</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-0.5 px-2 overflow-y-auto">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive(item.href)
                  ? 'bg-brand-700 text-white'
                  : 'text-brand-200 hover:bg-brand-800 hover:text-white'
              }`}
            >
              <span className="text-base w-5 text-center flex-shrink-0">{item.icon}</span>
              {sidebarOpen && <span className="truncate">{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* AI status */}
        <div className="px-3 py-3 border-t border-brand-800">
          {aiStatus && (
            <div className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs ${
              aiStatus.status === 'ok' && aiStatus.model_available
                ? 'text-green-400'
                : 'text-red-400'
            }`}>
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                aiStatus.status === 'ok' && aiStatus.model_available ? 'bg-green-400' : 'bg-red-400'
              }`} />
              {sidebarOpen && (
                <span className="truncate">
                  {aiStatus.status === 'ok' && aiStatus.model_available
                    ? `AI: ${aiStatus.model}`
                    : 'AI offline'}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="px-4 py-3 text-brand-400 hover:text-white text-xs border-t border-brand-800 text-left"
        >
          {sidebarOpen ? '← Collapse' : '→'}
        </button>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        {apiError && (
          <div role="alert" className="m-4 mb-0 flex items-start justify-between gap-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <span>{apiError}</span>
            <button type="button" onClick={() => setApiError(null)} className="font-medium hover:underline">
              Dismiss
            </button>
          </div>
        )}
        {children}
      </main>
    </div>
  )
}
