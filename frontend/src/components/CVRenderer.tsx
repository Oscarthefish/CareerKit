'use client'
// In-app CV preview. Mirrors the block rules in
// backend/app/services/cv_layout/blocks.py and the PDF/DOCX exporters, so the
// preview reads the same as the exported document: single column, left-aligned
// 10.5pt text, "Role — Company" with dates right-aligned, and "####" sub-group
// labels whose entries use a hanging indent instead of bullet dots.

type Block =
  | { kind: 'name' | 'subtitle' | 'section' | 'group' | 'bullet' | 'entry' | 'continuation' | 'para'; text: string }
  | { kind: 'contact'; parts: string[] }
  | { kind: 'role'; role: string; org: string; dates: string }

function parseRole(line: string): { role: string; org: string; dates: string } {
  const parts = line.split('|').map((p) => p.trim())
  if (parts.length === 1) return { role: parts[0], org: '', dates: '' }
  if (parts.length === 2) {
    return /\d{4}|present|current/i.test(parts[1])
      ? { role: parts[0], org: '', dates: parts[1] }
      : { role: parts[0], org: parts[1], dates: '' }
  }
  return { role: parts[0], org: parts.slice(1, -1).filter(Boolean).join(', '), dates: parts[parts.length - 1] }
}

export function parseCV(md: string): Block[] {
  const lines = (md || '').split('\n')
  const blocks: Block[] = []
  let i = 0
  if (lines.some((l) => l.trim().startsWith('# '))) {
    while (i < lines.length && !lines[i].trim().startsWith('# ')) i++
  }
  let inGroup = false
  let header = false
  for (; i < lines.length; i++) {
    const raw = lines[i].replace(/\s+$/, '')
    const s = raw.trim()
    if (!s || /^-{3,}$/.test(s) || s === '<!-- pagebreak -->') continue
    if (s.startsWith('# ')) {
      blocks.push({ kind: 'name', text: s.slice(2).trim() })
      header = true
      continue
    }
    if (header && !s.startsWith('#')) {
      if (s.includes('|') || s.includes('@')) {
        blocks.push({ kind: 'contact', parts: s.split('|').map((p) => p.trim()).filter(Boolean) })
        header = false
      } else if (!blocks.some((b) => b.kind === 'subtitle' || b.kind === 'contact')) {
        blocks.push({ kind: 'subtitle', text: s })
      } else {
        header = false
        blocks.push({ kind: 'para', text: s })
      }
      continue
    }
    header = false
    if (s.startsWith('#### ')) {
      blocks.push({ kind: 'group', text: s.slice(5).trim() })
      inGroup = true
    } else if (s.startsWith('### ')) {
      blocks.push({ kind: 'role', ...parseRole(s.slice(4)) })
      inGroup = false
    } else if (s.startsWith('## ')) {
      blocks.push({ kind: 'section', text: s.slice(3).trim() })
      inGroup = false
    } else if (s.startsWith('- ') || s.startsWith('* ')) {
      blocks.push({ kind: inGroup ? 'entry' : 'bullet', text: s.slice(2).trim() })
    } else if (/^[ \t]/.test(raw) && blocks.length && ['bullet', 'entry', 'continuation'].includes(blocks[blocks.length - 1].kind)) {
      blocks.push({ kind: 'continuation', text: s })
    } else {
      blocks.push({ kind: 'para', text: s })
    }
  }
  return blocks
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function inlineHtml(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
}

const html = (text: string) => ({ __html: inlineHtml(text) })

export default function CVRenderer({ markdown }: { markdown: string }) {
  const blocks = parseCV(markdown)
  const nodes: React.ReactNode[] = []
  let i = 0
  while (i < blocks.length) {
    const b = blocks[i]
    const key = `b-${i}`
    if (b.kind === 'bullet' || b.kind === 'continuation') {
      // Group a run of bullets (with their continuation lines) into one list.
      const items: React.ReactNode[] = []
      while (i < blocks.length && (blocks[i].kind === 'bullet' || blocks[i].kind === 'continuation')) {
        const item = blocks[i] as { kind: string; text: string }
        items.push(
          item.kind === 'bullet'
            ? <li key={i} className="cv-bullet" dangerouslySetInnerHTML={html(item.text)} />
            : <li key={i} className="cv-continuation" dangerouslySetInnerHTML={html(item.text)} />,
        )
        i++
      }
      nodes.push(<ul key={key} className="cv-list">{items}</ul>)
      continue
    }
    if (b.kind === 'entry') {
      const items: React.ReactNode[] = []
      while (i < blocks.length && blocks[i].kind === 'entry') {
        items.push(<li key={i} className="cv-entry" dangerouslySetInnerHTML={html((blocks[i] as { text: string }).text)} />)
        i++
      }
      nodes.push(<ul key={key} className="cv-entries">{items}</ul>)
      continue
    }
    switch (b.kind) {
      case 'name':
        nodes.push(<h1 key={key} className="cv-name">{b.text}</h1>)
        break
      case 'subtitle':
        nodes.push(<p key={key} className="cv-subtitle">{b.text}</p>)
        break
      case 'contact':
        nodes.push(<p key={key} className="cv-contact">{b.parts.join('  |  ')}</p>)
        break
      case 'section':
        nodes.push(<h2 key={key} className="cv-section">{b.text}</h2>)
        break
      case 'group':
        nodes.push(<h4 key={key} className="cv-group">{b.text}</h4>)
        break
      case 'role':
        nodes.push(
          <div key={key} className="cv-role">
            <span className="cv-role-text">
              <strong dangerouslySetInnerHTML={html(b.role)} />
              {b.org && <span> — {b.org}</span>}
            </span>
            {b.dates && <span className="cv-role-dates">{b.dates}</span>}
          </div>,
        )
        break
      case 'para':
        nodes.push(<p key={key} className="cv-para" dangerouslySetInnerHTML={html(b.text)} />)
        break
    }
    i++
  }

  return (
    <div className="cv-document">
      <div className="cv-page">{nodes}</div>
    </div>
  )
}
