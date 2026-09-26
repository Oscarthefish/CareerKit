'use client'
import { useEffect, useState } from 'react'
import AppShell from '@/components/AppShell'
import PageHeader from '@/components/PageHeader'
import TagInput from '@/components/TagInput'
import ConfidenceBadge from '@/components/ConfidenceBadge'
import AIButton from '@/components/AIButton'
import {
  getProfile, updateProfile, getWorkExperience, createWorkExperience, updateWorkExperience, deleteWorkExperience,
  getSkills, createSkill, updateSkill, deleteSkill,
  getCertifications, createCertification, updateCertification, deleteCertification,
  getAchievements, createAchievement, updateAchievement, deleteAchievement, generateBullets,
  getProjects, createProject, updateProject, deleteProject,
  getEvidence, createEvidence, updateEvidence, deleteEvidence,
  getStyle, updateStyle,
  getTraining, createTraining, updateTraining, deleteTraining,
  getCommunity, createCommunity, updateCommunity, deleteCommunity,
} from '@/lib/api'

const TABS = ['Summary', 'Experience', 'Skills', 'Training', 'Community', 'Achievements', 'Certifications', 'Projects', 'Evidence', 'Style']

const CONFIDENCE_OPTIONS = [
  { value: 'confirmed_hands_on', label: 'Confirmed hands-on' },
  { value: 'working_knowledge', label: 'Working knowledge' },
  { value: 'training_exposure', label: 'Training exposure' },
  { value: 'familiarity', label: 'Familiarity' },
  { value: 'interest', label: 'Interest / planned learning' },
  { value: 'unverified', label: 'Unverified' },
  { value: 'do_not_include', label: 'Do not include' },
]

const CONFIDENTIALITY_OPTIONS = [
  { value: 'public', label: 'Public' },
  { value: 'cv_safe', label: 'CV-safe' },
  { value: 'recruiter_only', label: 'Recruiter-only' },
  { value: 'interview_only', label: 'Interview-only' },
  { value: 'confidential', label: 'Confidential' },
  { value: 'do_not_use', label: 'Do not use' },
]

function ConfidenceSelect({ value, onChange }: { value: string; onChange: (e: any) => void }) {
  return (
    <select className="input" value={value} onChange={onChange}>
      {CONFIDENCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

function ConfidentialitySelect({ value, onChange }: { value: string; onChange: (e: any) => void }) {
  return (
    <select className="input" value={value} onChange={onChange}>
      {CONFIDENTIALITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

export default function ProfilePage() {
  const [tab, setTab] = useState('Summary')

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <PageHeader title="My Profile" description="Your master profile. All AI-generated content is based on this data." />

        <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                tab === t ? 'bg-brand-700 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:border-brand-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === 'Summary' && <SummaryTab />}
        {tab === 'Experience' && <ExperienceTab />}
        {tab === 'Skills' && <SkillsTab />}
        {tab === 'Training' && <TrainingTab />}
        {tab === 'Community' && <CommunityTab />}
        {tab === 'Achievements' && <AchievementsTab />}
        {tab === 'Certifications' && <CertificationsTab />}
        {tab === 'Projects' && <ProjectsTab />}
        {tab === 'Evidence' && <EvidenceTab />}
        {tab === 'Style' && <StyleTab />}
      </div>
    </AppShell>
  )
}

function SummaryTab() {
  const [profile, setProfile] = useState<any>({})
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<any>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getProfile().then((p: any) => { setProfile(p); setForm(p) })
  }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    setSaving(true)
    await updateProfile(form)
    setSaving(false)
    setEditing(false)
    setProfile(form)
  }

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-900">Personal Details</h3>
        {!editing && <button onClick={() => setEditing(true)} className="btn-secondary btn-sm">Edit</button>}
      </div>

      {editing ? (
        <div className="space-y-4">
          <div className="form-row">
            <div><label className="label">Full Name</label><input className="input" value={form.full_name || ''} onChange={set('full_name')} /></div>
            <div><label className="label">Email</label><input className="input" value={form.email || ''} onChange={set('email')} /></div>
          </div>
          <div className="form-row">
            <div><label className="label">Phone</label><input className="input" value={form.phone || ''} onChange={set('phone')} /></div>
            <div><label className="label">Location</label><input className="input" value={form.location || ''} onChange={set('location')} /></div>
          </div>
          <div className="form-row">
            <div><label className="label">LinkedIn</label><input className="input" value={form.linkedin_url || ''} onChange={set('linkedin_url')} /></div>
            <div><label className="label">Website</label><input className="input" value={form.website || ''} onChange={set('website')} /></div>
          </div>
          <div>
            <label className="label">NZ Work Rights</label>
            <select className="input" value={form.nz_work_rights || ''} onChange={set('nz_work_rights')}>
              <option>Citizen/PR</option><option>Work Visa</option><option>Student Visa</option><option>Restricted</option>
            </select>
          </div>
          <div>
            <label className="label">Professional Summary</label>
            <textarea className="textarea" rows={5} value={form.professional_summary || ''} onChange={set('professional_summary')} />
          </div>
          <TagInput
            value={form.target_roles || []}
            onChange={(v) => setForm({ ...form, target_roles: v })}
            label="Target Roles"
            placeholder="Add a role..."
          />
          <div className="flex gap-2">
            <button onClick={save} disabled={saving} className="btn-primary">{saving ? 'Saving...' : 'Save'}</button>
            <button onClick={() => setEditing(false)} className="btn-ghost">Cancel</button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <ProfileRow label="Name" value={profile.full_name} />
          <ProfileRow label="Email" value={profile.email} />
          <ProfileRow label="Phone" value={profile.phone} />
          <ProfileRow label="Location" value={profile.location} />
          <ProfileRow label="LinkedIn" value={profile.linkedin_url} />
          <ProfileRow label="Work Rights" value={profile.nz_work_rights} />
          {profile.professional_summary && (
            <div className="col-span-2">
              <p className="text-xs text-gray-400 mb-1">Summary</p>
              <p className="text-gray-700 leading-relaxed">{profile.professional_summary}</p>
            </div>
          )}
          {profile.target_roles?.length > 0 && (
            <div className="col-span-2">
              <p className="text-xs text-gray-400 mb-1">Target Roles</p>
              <div className="flex flex-wrap gap-1.5">
                {profile.target_roles.map((r: string) => <span key={r} className="badge-blue">{r}</span>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ProfileRow({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-gray-900 mt-0.5">{value || <span className="text-gray-300">Not set</span>}</p>
    </div>
  )
}

function ExperienceTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = { company: '', employer_public_name: '', role: '', alternative_titles: [], start_date: '', end_date: '', is_current: false, location: '', description: '', key_responsibilities: [], technologies: [], order_index: 0, confidentiality_level: 'cv_safe' }
  const [form, setForm] = useState<any>(blank)

  const load = () => getWorkExperience().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (editId) { await updateWorkExperience(editId, form) } else { await createWorkExperience(form) }
    setAdding(false); setEditId(null); setForm(blank); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteWorkExperience(id); load() } }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm">+ Add Role</button>
      </div>

      {adding && (
        <div className="card p-5 space-y-3">
          <h3 className="font-semibold text-sm text-gray-900">{editId ? 'Edit Role' : 'Add Role'}</h3>
          <div className="form-row">
            <div><label className="label">Company</label><input className="input" value={form.company} onChange={set('company')} placeholder="Use a clear [placeholder] if not yet confirmed" /></div>
            <div><label className="label">Role Title</label><input className="input" value={form.role} onChange={set('role')} /></div>
          </div>
          <div className="form-row">
            <div><label className="label">Employer Public Name (optional)</label><input className="input" value={form.employer_public_name} onChange={set('employer_public_name')} placeholder="Redacted/generic name for public output" /></div>
            <div>
              <label className="label">Confidentiality</label>
              <ConfidentialitySelect value={form.confidentiality_level || 'cv_safe'} onChange={(e) => setForm({ ...form, confidentiality_level: e.target.value })} />
            </div>
          </div>
          <div className="form-row">
            <div><label className="label">Start Date</label><input className="input" value={form.start_date} onChange={set('start_date')} placeholder="Jan 2022" /></div>
            <div><label className="label">End Date</label><input className="input" value={form.end_date} onChange={set('end_date')} placeholder="Present" disabled={form.is_current} /></div>
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={form.is_current} onChange={(e) => setForm({ ...form, is_current: e.target.checked })} />
            Current role
          </label>
          <div><label className="label">Location</label><input className="input" value={form.location} onChange={set('location')} /></div>
          <div><label className="label">Description</label><textarea className="textarea" rows={3} value={form.description} onChange={set('description')} /></div>
          <TagInput value={form.alternative_titles} onChange={(v) => setForm({ ...form, alternative_titles: v })} label="Alternative Titles" placeholder="Add alternative title..." />
          <TagInput value={form.key_responsibilities} onChange={(v) => setForm({ ...form, key_responsibilities: v })} label="Key Responsibilities" placeholder="Add responsibility..." />
          <TagInput value={form.technologies} onChange={(v) => setForm({ ...form, technologies: v })} label="Technologies" placeholder="Add technology..." />
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}

      {items.map((item) => (
        <div key={item.id} className="card p-5">
          <div className="flex items-start justify-between mb-1">
            <div>
              <p className="font-semibold text-gray-900">{item.role}</p>
              <p className="text-sm text-gray-500">{item.company} {item.location ? `· ${item.location}` : ''}</p>
              <p className="text-xs text-gray-400 mt-0.5">{item.start_date} - {item.is_current ? 'Present' : item.end_date}</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => startEdit(item)} className="btn-ghost btn-sm">Edit</button>
              <button onClick={() => remove(item.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
            </div>
          </div>
          {item.description && <p className="text-sm text-gray-700 mt-2">{item.description}</p>}
          {item.technologies?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {item.technologies.map((t: string) => <span key={t} className="badge-gray text-xs">{t}</span>)}
            </div>
          )}
        </div>
      ))}

      {items.length === 0 && !adding && (
        <div className="text-sm text-gray-400 text-center py-8">No work experience added yet.</div>
      )}
    </div>
  )
}

function SkillsTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = { name: '', aliases: [], category: 'technical', proficiency: 'proficient', years_experience: '', last_used: '', production_experience: true, confidence: 'confirmed_hands_on', notes: '' }
  const [form, setForm] = useState<any>(blank)

  const load = () => getSkills().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    const data = { ...form, years_experience: form.years_experience ? Number(form.years_experience) : null }
    if (editId) { await updateSkill(editId, data) } else { await createSkill(data) }
    setAdding(false); setEditId(null); setForm(blank); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteSkill(id); load() } }

  const grouped = items.reduce((acc: any, s: any) => {
    const cat = s.category || 'other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(s)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm">+ Add Skill</button>
      </div>

      {adding && (
        <div className="card p-5 space-y-3">
          <div className="form-row">
            <div><label className="label">Skill Name</label><input className="input" value={form.name} onChange={set('name')} /></div>
            <div>
              <label className="label">Category</label>
              <select className="input" value={form.category} onChange={set('category')}>
                <option value="technical">Technical</option>
                <option value="tool">Tool / Platform</option>
                <option value="process">Process / Framework</option>
                <option value="soft">Soft Skill</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div>
              <label className="label">Proficiency</label>
              <select className="input" value={form.proficiency} onChange={set('proficiency')}>
                <option value="expert">Expert</option>
                <option value="proficient">Proficient</option>
                <option value="familiar">Familiar</option>
                <option value="learning">Learning</option>
              </select>
            </div>
            <div>
              <label className="label">Confidence Level</label>
              <ConfidenceSelect value={form.confidence} onChange={set('confidence')} />
            </div>
          </div>
          <div className="form-row">
            <div><label className="label">Years Experience</label><input className="input" type="number" step="0.5" value={form.years_experience} onChange={set('years_experience')} /></div>
            <div><label className="label">Last Used</label><input className="input" value={form.last_used} onChange={set('last_used')} placeholder="2024" /></div>
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={form.production_experience} onChange={(e) => setForm({ ...form, production_experience: e.target.checked })} />
            Production / hands-on experience (not just training)
          </label>
          <TagInput value={form.aliases} onChange={(v) => setForm({ ...form, aliases: v })} label="Aliases / legacy names" placeholder="e.g. Cisco Secure Endpoint" />
          <div><label className="label">Notes</label><input className="input" value={form.notes} onChange={set('notes')} /></div>
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}

      {Object.entries(grouped).map(([cat, skills]: any) => (
        <div key={cat} className="card p-5">
          <h3 className="font-semibold text-gray-700 text-sm capitalize mb-3">{cat}</h3>
          <div className="space-y-2">
            {skills.map((sk: any) => (
              <div key={sk.id} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-900">{sk.name}</span>
                  {sk.proficiency && <span className="badge-gray text-xs">{sk.proficiency}</span>}
                  <ConfidenceBadge level={sk.confidence} />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => startEdit(sk)} className="text-gray-400 hover:text-gray-600 text-xs">Edit</button>
                  <button onClick={() => remove(sk.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function AchievementsTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    title: '', situation: '', action: '', result: '',
    tools_involved: [], skills_demonstrated: [], who_benefited: '',
    measurable_outcome: '', confidence: 'confirmed_hands_on', confidentiality_level: 'cv_safe', source: '', notes: '',
    bullet_plain: '', bullet_strong: '', bullet_senior: '', bullet_ats: '',
  }
  const [form, setForm] = useState<any>(blank)
  const [generatingBullets, setGeneratingBullets] = useState(false)
  const [generatedBullets, setGeneratedBullets] = useState<any>(null)

  const load = () => getAchievements().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (editId) { await updateAchievement(editId, form) } else { await createAchievement(form) }
    setAdding(false); setEditId(null); setForm(blank); setGeneratedBullets(null); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteAchievement(id); load() } }

  const genBullets = async () => {
    setGeneratingBullets(true)
    try {
      const result: any = await generateBullets({
        situation: form.situation,
        action: form.action,
        tools: form.tools_involved.join(', '),
        who_benefited: form.who_benefited,
        result: form.result,
        measurable: form.measurable_outcome,
        confidence: form.confidence,
      })
      setGeneratedBullets(result)
      setForm({ ...form, ...result })
    } finally {
      setGeneratingBullets(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm">+ Add Achievement</button>
      </div>

      {adding && (
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-900 text-sm">{editId ? 'Edit Achievement' : 'New Achievement'}</h3>

          <div><label className="label">Title / Label</label><input className="input" value={form.title} onChange={set('title')} placeholder="e.g. Reduced MTTD by 40%" /></div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div><label className="label">What was the problem or situation?</label><textarea className="textarea" rows={3} value={form.situation} onChange={set('situation')} /></div>
            <div><label className="label">What did you do?</label><textarea className="textarea" rows={3} value={form.action} onChange={set('action')} /></div>
            <div><label className="label">What changed afterwards?</label><textarea className="textarea" rows={3} value={form.result} onChange={set('result')} /></div>
            <div><label className="label">Who benefited?</label><input className="input" value={form.who_benefited} onChange={set('who_benefited')} /></div>
            <div><label className="label">Can it be measured?</label><input className="input" value={form.measurable_outcome} onChange={set('measurable_outcome')} placeholder="e.g. 40% reduction in false positives" /></div>
            <div>
              <label className="label">Confidence</label>
              <ConfidenceSelect value={form.confidence} onChange={set('confidence')} />
            </div>
            <div>
              <label className="label">Confidentiality</label>
              <ConfidentialitySelect value={form.confidentiality_level || 'cv_safe'} onChange={(e) => setForm({ ...form, confidentiality_level: e.target.value })} />
            </div>
          </div>

          <TagInput value={form.tools_involved} onChange={(v) => setForm({ ...form, tools_involved: v })} label="Tools Involved" placeholder="Add tool..." />
          <TagInput value={form.skills_demonstrated} onChange={(v) => setForm({ ...form, skills_demonstrated: v })} label="Skills Demonstrated" placeholder="Add skill..." />

          <div className="flex items-center gap-3">
            <button onClick={genBullets} disabled={generatingBullets} className="btn-secondary btn-sm">
              {generatingBullets ? 'Generating...' : 'Generate Bullet Options (AI)'}
            </button>
          </div>

          {(form.bullet_strong || generatedBullets) && (
            <div className="space-y-3 p-4 bg-gray-50 rounded-xl">
              <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Generated Bullets</h4>
              {[
                { key: 'bullet_plain', label: 'Plain Version' },
                { key: 'bullet_strong', label: 'Strong CV Version' },
                { key: 'bullet_senior', label: 'Senior/Professional Version' },
                { key: 'bullet_ats', label: 'Short ATS-Friendly Version' },
              ].map(({ key, label }) => form[key] && (
                <div key={key}>
                  <p className="text-xs text-gray-400 mb-1">{label}</p>
                  <div className="flex gap-2 items-start">
                    <p className="text-sm text-gray-800 flex-1">{form[key]}</p>
                    <button
                      onClick={() => navigator.clipboard.writeText(form[key])}
                      className="text-xs text-gray-400 hover:text-brand-600 whitespace-nowrap"
                    >
                      Copy
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save Achievement</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}

      {items.map((item) => (
        <div key={item.id} className="card p-5">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-gray-900 text-sm">{item.title}</p>
              <ConfidenceBadge level={item.confidence} />
            </div>
            <div className="flex gap-2">
              <button onClick={() => startEdit(item)} className="btn-ghost btn-sm">Edit</button>
              <button onClick={() => remove(item.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
            </div>
          </div>
          {item.bullet_strong && (
            <p className="text-sm text-gray-700 italic mt-1">"{item.bullet_strong}"</p>
          )}
          {item.tools_involved?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {item.tools_involved.map((t: string) => <span key={t} className="badge-gray">{t}</span>)}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function CertificationsTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = { name: '', issuer: '', date_obtained: '', expiry_date: '', credential_id: '', url: '', in_progress: false, status: 'active', notes: '' }
  const [form, setForm] = useState<any>(blank)

  const load = () => getCertifications().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (editId) { await updateCertification(editId, form) } else { await createCertification(form) }
    setAdding(false); setEditId(null); setForm(blank); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteCertification(id); load() } }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm">+ Add Certification</button>
      </div>

      {adding && (
        <div className="card p-5 space-y-3">
          <div className="form-row">
            <div><label className="label">Certification Name</label><input className="input" value={form.name} onChange={set('name')} /></div>
            <div><label className="label">Issuer</label><input className="input" value={form.issuer} onChange={set('issuer')} /></div>
          </div>
          <div className="form-row">
            <div><label className="label">Date Obtained</label><input className="input" value={form.date_obtained} onChange={set('date_obtained')} placeholder="Mar 2023" /></div>
            <div><label className="label">Expiry Date</label><input className="input" value={form.expiry_date} onChange={set('expiry_date')} /></div>
          </div>
          <div className="form-row">
            <div><label className="label">Credential ID</label><input className="input" value={form.credential_id} onChange={set('credential_id')} /></div>
            <div><label className="label">URL</label><input className="input" value={form.url} onChange={set('url')} /></div>
          </div>
          <div className="form-row">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.in_progress} onChange={(e) => setForm({ ...form, in_progress: e.target.checked })} />
              In progress
            </label>
            <div>
              <label className="label">Status</label>
              <select className="input" value={form.status} onChange={set('status')}>
                <option value="active">Active</option>
                <option value="expired">Expired</option>
                <option value="retired_legacy">Retired / legacy accreditation</option>
                <option value="unverified_status">Unverified status</option>
              </select>
            </div>
          </div>
          <div><label className="label">Notes</label><input className="input" value={form.notes} onChange={set('notes')} placeholder="e.g. do not describe as PCNSE" /></div>
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}

      {items.map((item) => (
        <div key={item.id} className="card p-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <p className="font-semibold text-sm text-gray-900">{item.name}</p>
              {item.in_progress && <span className="badge-yellow">In Progress</span>}
              {item.status === 'retired_legacy' && <span className="badge-gray">Legacy</span>}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              {item.issuer} {item.date_obtained ? `· ${item.date_obtained}` : ''} {item.expiry_date ? `· Expires ${item.expiry_date}` : ''}
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => startEdit(item)} className="btn-ghost btn-sm">Edit</button>
            <button onClick={() => remove(item.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
          </div>
        </div>
      ))}
    </div>
  )
}

function ProjectsTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = { name: '', description: '', role: '', technologies: [], outcomes: '', url: '', date_range: '', confidence: 'confirmed' }
  const [form, setForm] = useState<any>(blank)

  const load = () => getProjects().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (editId) { await updateProject(editId, form) } else { await createProject(form) }
    setAdding(false); setEditId(null); setForm(blank); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteProject(id); load() } }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm">+ Add Project</button>
      </div>
      {adding && (
        <div className="card p-5 space-y-3">
          <div className="form-row">
            <div><label className="label">Project Name</label><input className="input" value={form.name} onChange={set('name')} /></div>
            <div><label className="label">Your Role</label><input className="input" value={form.role} onChange={set('role')} /></div>
          </div>
          <div><label className="label">Description</label><textarea className="textarea" rows={3} value={form.description} onChange={set('description')} /></div>
          <div><label className="label">Outcomes</label><textarea className="textarea" rows={2} value={form.outcomes} onChange={set('outcomes')} /></div>
          <div className="form-row">
            <div><label className="label">Date Range</label><input className="input" value={form.date_range} onChange={set('date_range')} placeholder="2023 - 2024" /></div>
            <div><label className="label">URL</label><input className="input" value={form.url} onChange={set('url')} /></div>
          </div>
          <TagInput value={form.technologies} onChange={(v) => setForm({ ...form, technologies: v })} label="Technologies" placeholder="Add technology..." />
          <select className="input" value={form.confidence} onChange={set('confidence')}>
            <option value="confirmed">Confirmed</option><option value="inferred">Inferred</option><option value="weak">Weak</option>
          </select>
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}
      {items.map((item) => (
        <div key={item.id} className="card p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-semibold text-sm text-gray-900">{item.name}</p>
              <p className="text-xs text-gray-400">{item.role} {item.date_range ? `· ${item.date_range}` : ''}</p>
              {item.description && <p className="text-sm text-gray-700 mt-1">{item.description}</p>}
            </div>
            <div className="flex gap-2">
              <button onClick={() => startEdit(item)} className="btn-ghost btn-sm">Edit</button>
              <button onClick={() => remove(item.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function EvidenceTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = { title: '', description: '', tools_involved: [], skills_demonstrated: [], outcome: '', value: '', confidence: 'confirmed', notes: '', source: '' }
  const [form, setForm] = useState<any>(blank)

  const load = () => getEvidence().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (editId) { await updateEvidence(editId, form) } else { await createEvidence(form) }
    setAdding(false); setEditId(null); setForm(blank); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteEvidence(id); load() } }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between mb-2">
        <p className="text-sm text-gray-500">Evidence items are raw facts and examples that support your CV claims.</p>
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm flex-shrink-0">+ Add Evidence</button>
      </div>
      {adding && (
        <div className="card p-5 space-y-3">
          <div><label className="label">Title</label><input className="input" value={form.title} onChange={set('title')} placeholder="e.g. Deployed Suricata IDS for 3 segments" /></div>
          <div><label className="label">Description</label><textarea className="textarea" rows={3} value={form.description} onChange={set('description')} /></div>
          <div className="form-row">
            <div><label className="label">Outcome</label><input className="input" value={form.outcome} onChange={set('outcome')} /></div>
            <div><label className="label">Value / Impact</label><input className="input" value={form.value} onChange={set('value')} /></div>
          </div>
          <TagInput value={form.tools_involved} onChange={(v) => setForm({ ...form, tools_involved: v })} label="Tools" placeholder="Add tool..." />
          <TagInput value={form.skills_demonstrated} onChange={(v) => setForm({ ...form, skills_demonstrated: v })} label="Skills Demonstrated" placeholder="Add skill..." />
          <div className="form-row">
            <div><label className="label">Source</label><input className="input" value={form.source} onChange={set('source')} placeholder="e.g. Work project Q3 2023" /></div>
            <div>
              <label className="label">Confidence</label>
              <select className="input" value={form.confidence} onChange={set('confidence')}>
                <option value="confirmed">Confirmed</option><option value="inferred">Inferred</option>
                <option value="weak">Weak</option><option value="do_not_use">Do Not Use</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}
      {items.map((item) => (
        <div key={item.id} className="card p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-semibold text-sm text-gray-900">{item.title}</p>
                <ConfidenceBadge level={item.confidence} />
              </div>
              {item.description && <p className="text-sm text-gray-600 mt-1">{item.description}</p>}
              {item.outcome && <p className="text-xs text-gray-400 mt-1">Outcome: {item.outcome}</p>}
            </div>
            <div className="flex gap-2">
              <button onClick={() => startEdit(item)} className="btn-ghost btn-sm">Edit</button>
              <button onClick={() => remove(item.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function TrainingTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    title: '', provider: '', date: '', delivery_type: 'classroom', duration: '',
    completion_status: 'completed', related_certification: '', tools: [], skills: [],
    evidence: '', include_by_default: true, confidence: 'confirmed_hands_on', notes: '',
  }
  const [form, setForm] = useState<any>(blank)

  const load = () => getTraining().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (editId) { await updateTraining(editId, form) } else { await createTraining(form) }
    setAdding(false); setEditId(null); setForm(blank); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteTraining(id); load() } }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        Training and courses, kept separate from certifications so a course is never presented as a passed exam.
      </p>
      <div className="flex justify-end">
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm">+ Add Training</button>
      </div>

      {adding && (
        <div className="card p-5 space-y-3">
          <div className="form-row">
            <div><label className="label">Title</label><input className="input" value={form.title} onChange={set('title')} /></div>
            <div><label className="label">Provider</label><input className="input" value={form.provider} onChange={set('provider')} /></div>
          </div>
          <div className="form-row">
            <div><label className="label">Date</label><input className="input" value={form.date} onChange={set('date')} placeholder="2017 or 18 March 2026" /></div>
            <div><label className="label">Duration</label><input className="input" value={form.duration} onChange={set('duration')} placeholder="Six-day classroom course" /></div>
          </div>
          <div className="form-row">
            <div>
              <label className="label">Delivery Type</label>
              <select className="input" value={form.delivery_type} onChange={set('delivery_type')}>
                <option value="classroom">Classroom</option>
                <option value="online">Online</option>
                <option value="self-paced">Self-paced</option>
                <option value="conference-workshop">Conference workshop</option>
              </select>
            </div>
            <div>
              <label className="label">Completion Status</label>
              <select className="input" value={form.completion_status} onChange={set('completion_status')}>
                <option value="completed">Completed</option>
                <option value="enrolled">Enrolled</option>
                <option value="in_progress">In progress</option>
                <option value="purchased_not_started">Purchased, not started</option>
                <option value="unconfirmed">Unconfirmed</option>
              </select>
            </div>
          </div>
          <div><label className="label">Related Certification (if any)</label><input className="input" value={form.related_certification} onChange={set('related_certification')} placeholder="Leave blank if this training did not lead to a certification" /></div>
          <TagInput value={form.tools} onChange={(v) => setForm({ ...form, tools: v })} label="Tools Covered" placeholder="Add tool..." />
          <TagInput value={form.skills} onChange={(v) => setForm({ ...form, skills: v })} label="Skills Covered" placeholder="Add skill..." />
          <div className="form-row">
            <div>
              <label className="label">Confidence</label>
              <ConfidenceSelect value={form.confidence} onChange={set('confidence')} />
            </div>
            <div><label className="label">Evidence</label><input className="input" value={form.evidence} onChange={set('evidence')} placeholder="Certificate, receipt, portal record..." /></div>
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={form.include_by_default} onChange={(e) => setForm({ ...form, include_by_default: e.target.checked })} />
            Include by default on generated CVs
          </label>
          <div><label className="label">Notes</label><input className="input" value={form.notes} onChange={set('notes')} /></div>
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}

      {items.map((item) => (
        <div key={item.id} className="card p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-semibold text-sm text-gray-900">{item.title}</p>
                <ConfidenceBadge level={item.confidence} />
                {item.completion_status !== 'completed' && <span className="badge-yellow">{item.completion_status.replace(/_/g, ' ')}</span>}
              </div>
              <p className="text-xs text-gray-400 mt-0.5">{item.provider} {item.date ? `· ${item.date}` : ''}</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => startEdit(item)} className="btn-ghost btn-sm">Edit</button>
              <button onClick={() => remove(item.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
            </div>
          </div>
        </div>
      ))}
      {items.length === 0 && !adding && (
        <div className="text-sm text-gray-400 text-center py-8">No training added yet.</div>
      )}
    </div>
  )
}

function CommunityTab() {
  const [items, setItems] = useState<any[]>([])
  const [adding, setAdding] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    event: '', location: '', date: '', participation_type: 'attendee',
    notes: '', evidence: '', include_on_cv: false, include_on_linkedin: true,
  }
  const [form, setForm] = useState<any>(blank)

  const load = () => getCommunity().then((r: any) => setItems(r))
  useEffect(() => { load() }, [])

  const set = (k: string) => (e: any) => setForm({ ...form, [k]: e.target.value })

  const save = async () => {
    if (editId) { await updateCommunity(editId, form) } else { await createCommunity(form) }
    setAdding(false); setEditId(null); setForm(blank); load()
  }

  const startEdit = (item: any) => { setForm(item); setEditId(item.id); setAdding(true) }
  const remove = async (id: number) => { if (confirm('Remove?')) { await deleteCommunity(id); load() } }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">Conferences, meetups and community involvement. Treated as professional engagement, not formal qualifications.</p>
      <div className="flex justify-end">
        <button onClick={() => { setForm(blank); setEditId(null); setAdding(true) }} className="btn-primary btn-sm">+ Add Event</button>
      </div>

      {adding && (
        <div className="card p-5 space-y-3">
          <div className="form-row">
            <div><label className="label">Event</label><input className="input" value={form.event} onChange={set('event')} /></div>
            <div><label className="label">Location</label><input className="input" value={form.location} onChange={set('location')} /></div>
          </div>
          <div className="form-row">
            <div><label className="label">Date</label><input className="input" value={form.date} onChange={set('date')} placeholder="2020 or 29 October 2020" /></div>
            <div>
              <label className="label">Participation Type</label>
              <select className="input" value={form.participation_type} onChange={set('participation_type')}>
                <option value="attendee">Attendee</option>
                <option value="regular_attendee">Regular attendee</option>
                <option value="participant">Participant</option>
                <option value="speaker">Speaker</option>
                <option value="organiser">Organiser</option>
              </select>
            </div>
          </div>
          <div><label className="label">Notes</label><input className="input" value={form.notes} onChange={set('notes')} /></div>
          <div><label className="label">Evidence</label><input className="input" value={form.evidence} onChange={set('evidence')} placeholder="Ticket, badge, confirmation email..." /></div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.include_on_cv} onChange={(e) => setForm({ ...form, include_on_cv: e.target.checked })} />
              Include on CV
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.include_on_linkedin} onChange={(e) => setForm({ ...form, include_on_linkedin: e.target.checked })} />
              Include on LinkedIn
            </label>
          </div>
          <div className="flex gap-2">
            <button onClick={save} className="btn-primary btn-sm">Save</button>
            <button onClick={() => { setAdding(false); setEditId(null) }} className="btn-ghost btn-sm">Cancel</button>
          </div>
        </div>
      )}

      {items.map((item) => (
        <div key={item.id} className="card p-4 flex items-center justify-between">
          <div>
            <p className="font-semibold text-sm text-gray-900">{item.event}</p>
            <p className="text-xs text-gray-400 mt-0.5">{item.location} {item.date ? `· ${item.date}` : ''} · {item.participation_type.replace(/_/g, ' ')}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => startEdit(item)} className="btn-ghost btn-sm">Edit</button>
            <button onClick={() => remove(item.id)} className="text-red-400 hover:text-red-600 text-xs">Remove</button>
          </div>
        </div>
      ))}
      {items.length === 0 && !adding && (
        <div className="text-sm text-gray-400 text-center py-8">No community involvement added yet.</div>
      )}
    </div>
  )
}

function StyleTab() {
  const [style, setStyleData] = useState<any>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => { getStyle().then((r: any) => setStyleData(r)) }, [])

  const set = (k: string) => (e: any) => setStyleData({ ...style, [k]: e.target.value })

  const save = async () => {
    setSaving(true)
    await updateStyle(style)
    setSaving(false)
  }

  return (
    <div className="card p-6 space-y-4">
      <h3 className="font-semibold text-gray-900 mb-2">Writing Style Preferences</h3>
      <div className="form-row">
        <div>
          <label className="label">Bullet Style</label>
          <select className="input" value={style.bullet_style || 'dash'} onChange={set('bullet_style')}>
            <option value="dash">Dash (-)</option><option value="dot">Dot (bullet)</option><option value="arrow">Arrow</option>
          </select>
        </div>
        <div>
          <label className="label">Tone</label>
          <select className="input" value={style.tone || 'professional'} onChange={set('tone')}>
            <option value="professional">Professional and direct</option>
            <option value="confident">Confident and assertive</option>
            <option value="technical">Technical and precise</option>
          </select>
        </div>
      </div>
      <div>
        <label className="label">Preferred CV Length</label>
        <select className="input" value={style.preferred_cv_length || '2-pages'} onChange={set('preferred_cv_length')}>
          <option value="1-page">1 page</option><option value="2-pages">2 pages</option><option value="3-pages">3 pages</option>
        </select>
      </div>
      <TagInput value={style.avoid_phrases || []} onChange={(v) => setStyleData({ ...style, avoid_phrases: v })} label="Phrases to Avoid" placeholder="Add phrase..." />
      <TagInput value={style.preferred_phrases || []} onChange={(v) => setStyleData({ ...style, preferred_phrases: v })} label="Preferred Phrases / Style Examples" placeholder="Add example..." />
      <div><label className="label">Additional Notes</label><textarea className="textarea" rows={3} value={style.notes || ''} onChange={set('notes')} placeholder="Any other writing preferences..." /></div>
      <button onClick={save} disabled={saving} className="btn-primary">{saving ? 'Saving...' : 'Save Preferences'}</button>
    </div>
  )
}
