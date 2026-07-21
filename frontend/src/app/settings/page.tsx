'use client'
import { useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import { getSettings, updateSettings, aiHealth } from '@/lib/api'
import type { AIHealth } from '@/lib/types'

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>({})
  const [form, setForm] = useState<any>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [aiStatus, setAiStatus] = useState<AIHealth | null>(null)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    getSettings().then((s: any) => { setSettings(s); setForm(s) })
    checkAI()
  }, [])

  const checkAI = async () => {
    setChecking(true)
    try {
      const h: any = await aiHealth()
      setAiStatus(h)
    } finally {
      setChecking(false)
    }
  }

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    setSaving(true)
    await updateSettings({ ollama_url: form.ollama_url, ollama_model: form.ollama_model })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    checkAI()
  }

  const COMMON_MODELS = ['llama3', 'llama3:8b', 'llama3:70b', 'mistral', 'phi3', 'gemma2', 'qwen2.5']

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-6 py-8">
        <PageHeader title="Settings" description="Configure your local AI provider and preferences." />

        {/* AI Status */}
        <div className="card p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900 text-sm">Ollama Status</h3>
            <button onClick={checkAI} disabled={checking} className="btn-ghost btn-sm">
              {checking ? 'Checking...' : 'Check Now'}
            </button>
          </div>

          {aiStatus ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${aiStatus.status === 'ok' ? 'bg-green-400' : 'bg-red-400'}`} />
                <span className="text-sm font-medium text-gray-900">
                  {aiStatus.status === 'ok' ? 'Connected' : 'Not Connected'}
                </span>
              </div>

              {aiStatus.status === 'ok' ? (
                <>
                  <p className="text-xs text-gray-400">URL: {aiStatus.url}</p>
                  <div className="flex items-center gap-2">
                    <p className="text-xs text-gray-400">Model: {aiStatus.model}</p>
                    {aiStatus.model_available ? (
                      <span className="badge-green text-xs">Available</span>
                    ) : (
                      <span className="badge-red text-xs">Not loaded</span>
                    )}
                  </div>
                  {!aiStatus.model_available && (
                    <div className="mt-2 p-3 bg-amber-50 rounded-lg text-xs text-amber-800">
                      <p className="font-medium mb-1">Model not found. To load it:</p>
                      <code className="block bg-amber-100 px-2 py-1 rounded font-mono">ollama pull {aiStatus.model}</code>
                    </div>
                  )}
                  {aiStatus.available_models?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-gray-400 mb-1">Available models:</p>
                      <div className="flex flex-wrap gap-1">
                        {aiStatus.available_models.map((m) => (
                          <span key={m} className="badge-gray text-xs">{m}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="p-3 bg-red-50 rounded-lg text-xs text-red-800">
                  <p className="font-medium mb-1">{aiStatus.message}</p>
                  <p className="mt-1">Start Ollama:</p>
                  <code className="block bg-red-100 px-2 py-1 rounded font-mono mt-1">ollama serve</code>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-gray-400">Checking...</div>
          )}
        </div>

        {/* Settings form */}
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-900 text-sm">Ollama Configuration</h3>

          <div>
            <label className="label">Ollama URL</label>
            <input
              className="input font-mono"
              value={form.ollama_url || ''}
              onChange={set('ollama_url')}
              placeholder="http://localhost:11434"
            />
            <p className="text-xs text-gray-400 mt-1">Default is http://localhost:11434</p>
          </div>

          <div>
            <label className="label">Model Name</label>
            <input
              className="input font-mono"
              value={form.ollama_model || ''}
              onChange={set('ollama_model')}
              placeholder="llama3"
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {COMMON_MODELS.map((m) => (
                <button
                  key={m}
                  onClick={() => setForm({ ...form, ollama_model: m })}
                  className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                    form.ollama_model === m ? 'bg-brand-100 text-brand-800 font-semibold' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              For cyber security work, llama3:70b or mistral:7b are recommended. Smaller models work for most tasks.
            </p>
          </div>

          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
          </button>
        </div>

        {/* Info */}
        <div className="mt-6 p-4 bg-gray-50 rounded-xl text-xs text-gray-500 space-y-2">
          <p className="font-medium text-gray-700">How to set up Ollama</p>
          <ol className="list-decimal list-inside space-y-1">
            <li>Install Ollama from <span className="font-mono">ollama.com</span></li>
            <li>Run <span className="font-mono bg-gray-100 px-1 rounded">ollama serve</span> in a terminal</li>
            <li>Pull a model: <span className="font-mono bg-gray-100 px-1 rounded">ollama pull llama3</span></li>
            <li>Come back here and click Check Now</li>
          </ol>
          <p className="mt-2">All AI processing happens on your machine. Nothing is sent to the cloud.</p>
        </div>
      </div>
    </AppShell>
  )
}
