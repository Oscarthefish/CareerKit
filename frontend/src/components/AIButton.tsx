'use client'
import { useState } from 'react'

interface Props {
  label: string
  loadingLabel?: string
  onClick: () => Promise<void>
  className?: string
  variant?: 'primary' | 'secondary'
  disabled?: boolean
}

export default function AIButton({ label, loadingLabel, onClick, className = '', variant = 'primary', disabled }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleClick = async () => {
    setLoading(true)
    setError(null)
    try {
      await onClick()
    } catch (e: any) {
      setError(e.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={className}>
      <button
        onClick={handleClick}
        disabled={loading || disabled}
        className={variant === 'primary' ? 'btn-primary' : 'btn-secondary'}
      >
        {loading ? (
          <>
            <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            {loadingLabel || 'Generating...'}
          </>
        ) : label}
      </button>
      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}
