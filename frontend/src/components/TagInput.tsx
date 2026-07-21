'use client'
import { useState, KeyboardEvent } from 'react'

interface Props {
  value: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  label?: string
}

export default function TagInput({ value, onChange, placeholder = 'Add item...', label }: Props) {
  const [input, setInput] = useState('')

  const add = () => {
    const trimmed = input.trim()
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed])
    }
    setInput('')
  }

  const remove = (tag: string) => onChange(value.filter((t) => t !== tag))

  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      add()
    } else if (e.key === 'Backspace' && !input && value.length) {
      remove(value[value.length - 1])
    }
  }

  return (
    <div>
      {label && <label className="label">{label}</label>}
      <div className="flex flex-wrap gap-1.5 p-2 border border-gray-300 rounded-lg bg-white min-h-[42px] focus-within:ring-1 focus-within:ring-brand-500 focus-within:border-brand-500">
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-brand-100 text-brand-800 rounded text-xs font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={() => remove(tag)}
              className="text-brand-500 hover:text-brand-800 font-bold leading-none"
            >
              ×
            </button>
          </span>
        ))}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          onBlur={add}
          placeholder={value.length === 0 ? placeholder : ''}
          className="flex-1 min-w-[120px] text-sm bg-transparent outline-none placeholder:text-gray-400"
        />
      </div>
      <p className="mt-1 text-xs text-gray-400">Press Enter or comma to add</p>
    </div>
  )
}
