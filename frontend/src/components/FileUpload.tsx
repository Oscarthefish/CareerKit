'use client'
import { useRef, useState } from 'react'

interface Props {
  accept?: string
  label: string
  hint?: string
  onFile: (file: File) => Promise<void>
}

export default function FileUpload({ accept = '.pdf,.docx,.txt,.md', label, hint, onFile }: Props) {
  const ref = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handle = async (file: File) => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await onFile(file)
      setSuccess(`${file.name} uploaded successfully`)
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
          dragging ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400'
        }`}
        onClick={() => ref.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const file = e.dataTransfer.files[0]
          if (file) handle(file)
        }}
      >
        <input
          ref={ref}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handle(file)
          }}
        />
        {loading ? (
          <div className="flex flex-col items-center gap-2">
            <span className="inline-block w-6 h-6 border-2 border-brand-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-500">Uploading and analysing...</p>
          </div>
        ) : (
          <>
            <div className="text-3xl mb-2">↑</div>
            <p className="text-sm font-medium text-gray-700">{label}</p>
            {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
            <p className="text-xs text-gray-400 mt-2">{accept}</p>
          </>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {success && <p className="mt-2 text-sm text-green-600">{success}</p>}
    </div>
  )
}
