'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { aiHealth } from '@/lib/api'
import type { AIHealth } from '@/lib/types'
import {
  HomeIcon, JobsIcon, ProfileIcon, DocumentIcon, ScannerIcon, MailIcon, LinkedInIcon, StackIcon,
  SettingsIcon, ChevronLeftIcon,
} from '@/components/ui/Icons'

// Grouped to match the user's mental model (their job search) rather than
// the implementation's route list - only real, existing destinations.
const NAV_GROUPS: { label: string | null; items: { href: string; label: string; icon: typeof HomeIcon }[] }[] = [
  {
    label: null,
    items: [
      { href: '/', label: 'Home', icon: HomeIcon },
      { href: '/applications', label: 'Jobs', icon: JobsIcon },
      { href: '/profile', label: 'Career Profile', icon: ProfileIcon },
      { href: '/cv', label: 'Master CV', icon: DocumentIcon },
    ],
  },
  {
    label: 'Discover',
    items: [
      { href: '/scanner', label: 'Job Scanner', icon: ScannerIcon },
      { href: '/reachouts', label: 'Reach Outs', icon: MailIcon },
    ],
  },
  {
    label: 'Tools',
    items: [
      { href: '/linkedin', label: 'LinkedIn Builder', icon: LinkedInIcon },
      { href: '/examples', label: 'Example CVs', icon: StackIcon },
    ],
  },
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

  const aiOk = aiStatus?.status === 'ok' && aiStatus.model_available

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-app)' }}>
      {/* Sidebar */}
      <aside
        className={`${sidebarOpen ? 'w-60' : 'w-16'} flex-shrink-0 flex flex-col transition-all duration-200`}
        style={{ background: 'var(--text-primary)' }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 flex-shrink-0">
          <div className="w-7 h-7 bg-brand-500 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
            CK
          </div>
          {sidebarOpen && <span className="font-semibold text-sm text-white truncate">CareerKit</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 px-2 overflow-y-auto">
          {NAV_GROUPS.map((group, gi) => (
            <div key={gi} className={gi > 0 ? 'mt-5' : ''}>
              {group.label && sidebarOpen && (
                <p className="px-3 mb-1.5 text-[11px] font-medium uppercase tracking-wide text-white/35">
                  {group.label}
                </p>
              )}
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.href)
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      title={!sidebarOpen ? item.label : undefined}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                        active ? 'bg-brand-600 text-white' : 'text-white/60 hover:bg-white/10 hover:text-white'
                      }`}
                    >
                      <Icon className="flex-shrink-0" />
                      {sidebarOpen && <span className="truncate">{item.label}</span>}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Settings + AI status */}
        <div className="px-2 pb-2 pt-2 border-t border-white/10 space-y-0.5">
          <Link
            href="/settings"
            title={!sidebarOpen ? 'Settings' : undefined}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive('/settings') ? 'bg-brand-600 text-white' : 'text-white/60 hover:bg-white/10 hover:text-white'
            }`}
          >
            <SettingsIcon className="flex-shrink-0" />
            {sidebarOpen && <span className="truncate">Settings</span>}
          </Link>

          {aiStatus && (
            <div
              title={aiOk ? `AI: ${aiStatus.model}` : (aiStatus.message || 'AI offline')}
              className="flex items-center gap-3 px-3 py-2 text-xs text-white/40"
            >
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${aiOk ? 'bg-green-400' : 'bg-red-400'}`} />
              {sidebarOpen && <span className="truncate">{aiOk ? `AI ready · ${aiStatus.model}` : 'AI offline'}</span>}
            </div>
          )}

          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-white/40 hover:text-white hover:bg-white/10 transition-colors"
          >
            <ChevronLeftIcon className={`flex-shrink-0 transition-transform ${sidebarOpen ? '' : 'rotate-180'}`} />
            {sidebarOpen && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        {apiError && (
          <div role="alert" className="m-4 mb-0 flex items-start justify-between gap-4 rounded-lg px-4 py-3 text-sm" style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', color: 'var(--danger-text)' }}>
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
