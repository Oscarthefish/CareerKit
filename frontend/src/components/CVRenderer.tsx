'use client'

interface CVSection {
  type: 'name' | 'contact' | 'h2' | 'h3' | 'bullet' | 'text' | 'blank'
  content: string
}

const SECTION_ICONS: Record<string, string> = {
  'PROFESSIONAL PROFILE': '▸',
  'PROFILE': '▸',
  'SUMMARY': '▸',
  'KEY SKILLS': '◈',
  'SKILLS': '◈',
  'TOOLS AND TECHNOLOGIES': '⊞',
  'TOOLS': '⊞',
  'TECHNOLOGIES': '⊞',
  'PROFESSIONAL EXPERIENCE': '◷',
  'EXPERIENCE': '◷',
  'WORK EXPERIENCE': '◷',
  'SELECTED ACHIEVEMENTS': '◆',
  'ACHIEVEMENTS': '◆',
  'TRAINING AND CERTIFICATIONS': '◎',
  'CERTIFICATIONS': '◎',
  'TRAINING': '◎',
  'EDUCATION': '◉',
  'PROJECTS': '◫',
  'EVIDENCE': '◧',
}

function detectContactType(item: string): string {
  const s = item.toLowerCase()
  if (s.includes('@')) return 'email'
  if (/^\+?[\d\s\-().]{7,}$/.test(item.trim())) return 'phone'
  if (s.includes('linkedin')) return 'linkedin'
  if (s.startsWith('http') || (s.includes('.') && !s.includes(' '))) return 'web'
  return 'location'
}

const CONTACT_ICONS: Record<string, string> = {
  email: '✉',
  phone: '✆',
  linkedin: 'in',
  web: '⊕',
  location: '◎',
}

function parse(md: string): CVSection[] {
  const lines = md.split('\n')
  const sections: CVSection[] = []
  let foundName = false

  for (const raw of lines) {
    const line = raw.trimEnd()
    const stripped = line.trim()

    if (!foundName && !stripped.startsWith('# ')) continue

    if (stripped.startsWith('# ')) {
      foundName = true
      sections.push({ type: 'name', content: stripped.slice(2).trim() })
    } else if (stripped.startsWith('## ')) {
      sections.push({ type: 'h2', content: stripped.slice(3).trim() })
    } else if (stripped.startsWith('### ')) {
      sections.push({ type: 'h3', content: stripped.slice(4).trim() })
    } else if (stripped.startsWith('- ') || stripped.startsWith('* ')) {
      sections.push({ type: 'bullet', content: stripped.slice(2).trim() })
    } else if (/^---+$/.test(stripped)) {
      // skip HR
    } else if (!stripped) {
      sections.push({ type: 'blank', content: '' })
    } else {
      // Contact line detection: right after name, contains | or @
      const prev = sections.filter(s => s.type !== 'blank').slice(-1)[0]
      if (prev?.type === 'name' && (stripped.includes('|') || stripped.includes('@'))) {
        sections.push({ type: 'contact', content: stripped })
      } else {
        sections.push({ type: 'text', content: stripped })
      }
    }
  }

  return sections
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
    .replace(/`(.+?)`/g, '<code style="font-family:monospace;font-size:0.9em;background:#f1f5f9;padding:0 3px;border-radius:3px">$1</code>')
}

export default function CVRenderer({ markdown }: { markdown: string }) {
  const sections = parse(markdown)
  const nodes: React.ReactNode[] = []
  let i = 0

  while (i < sections.length) {
    const s = sections[i]

    // Name
    if (s.type === 'name') {
      nodes.push(
        <div key={i} className="cv-name-block">
          <h1 className="cv-name">{s.content}</h1>
        </div>
      )
      i++
      continue
    }

    // Contact row
    if (s.type === 'contact') {
      const parts = s.content.split('|').map(p => p.trim()).filter(Boolean)
      nodes.push(
        <div key={i} className="cv-contact-row">
          {parts.map((p, j) => {
            const type = detectContactType(p)
            const icon = CONTACT_ICONS[type]
            return (
              <span key={j} className="cv-contact-item">
                <span className="cv-contact-icon">{icon}</span>
                <span>{p}</span>
              </span>
            )
          })}
        </div>
      )
      i++
      continue
    }

    // Section heading ##
    if (s.type === 'h2') {
      const label = s.content.toUpperCase()
      const icon = SECTION_ICONS[label] || '▸'
      nodes.push(
        <div key={i} className="cv-section-head">
          <span className="cv-section-icon">{icon}</span>
          <span className="cv-section-label">{label}</span>
          <div className="cv-section-rule" />
        </div>
      )
      i++
      continue
    }

    // Role header ###
    if (s.type === 'h3') {
      const parts = s.content.split('|').map(p => p.trim())
      const role = inlineHtml(parts[0] || '')
      const company = parts[1] || ''
      const dates = parts[2] || ''
      nodes.push(
        <div key={i} className="cv-role">
          <div className="cv-role-info">
            <span className="cv-role-title" dangerouslySetInnerHTML={{ __html: role }} />
            {company && <span className="cv-role-company">{company}</span>}
          </div>
          {dates && <span className="cv-role-dates">{dates}</span>}
        </div>
      )
      i++
      continue
    }

    // Bullets — collect a run
    if (s.type === 'bullet') {
      const bullets: string[] = [s.content]
      i++
      while (i < sections.length && sections[i].type === 'bullet') {
        bullets.push(sections[i].content)
        i++
      }
      nodes.push(
        <ul key={`ul-${i}`} className="cv-list">
          {bullets.map((b, j) => (
            <li key={j}>
              <span className="cv-bullet-dot" />
              <span dangerouslySetInnerHTML={{ __html: inlineHtml(b) }} />
            </li>
          ))}
        </ul>
      )
      continue
    }

    // Skip blank lines that just add noise
    if (s.type === 'blank') {
      i++
      continue
    }

    // Plain text paragraph
    if (s.type === 'text' && s.content) {
      nodes.push(
        <p key={i} className="cv-para" dangerouslySetInnerHTML={{ __html: inlineHtml(s.content) }} />
      )
    }

    i++
  }

  return (
    <div className="cv-document">
      {/* Top accent strip */}
      <div className="cv-accent-strip" />
      <div className="cv-page">
        {nodes}
      </div>
    </div>
  )
}
