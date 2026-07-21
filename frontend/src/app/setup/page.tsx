'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { updateProfile, createWorkExperience, createSkill, createCertification } from '@/lib/api'
import TagInput from '@/components/TagInput'

const TARGET_ROLES = [
  'SOC Analyst', 'Senior SOC Analyst', 'Cyber Security Analyst',
  'Detection Engineer', 'Threat Intel Analyst', 'Security Operations Lead',
  'Security Engineer', 'Incident Responder', 'Penetration Tester',
]

const steps = [
  'Welcome',
  'Contact Details',
  'Target Roles',
  'Professional Summary',
  'Work History',
  'Skills',
  'Certifications',
  'Preferences',
  'Done',
]

export default function SetupWizard() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [contact, setContact] = useState({
    full_name: '', email: '', phone: '', location: '',
    linkedin_url: '', website: '', nz_work_rights: 'Citizen/PR',
  })
  const [targetRoles, setTargetRoles] = useState<string[]>([])
  const [summary, setSummary] = useState('')
  const [experience, setExperience] = useState([{
    company: '', role: '', start_date: '', end_date: '',
    is_current: false, location: '', description: '', key_responsibilities: [] as string[], technologies: [] as string[],
  }])
  const [skills, setSkills] = useState([{
    name: '', category: 'technical', proficiency: 'proficient', confidence: 'confirmed',
  }])
  const [certs, setCerts] = useState([{
    name: '', issuer: '', date_obtained: '', in_progress: false,
  }])
  const [style, setStyle] = useState({ tone: 'professional', preferred_cv_length: '2-pages' })

  const next = () => setStep((s) => Math.min(s + 1, steps.length - 1))
  const prev = () => setStep((s) => Math.max(s - 1, 0))

  const finish = async () => {
    setSaving(true)
    setError(null)
    try {
      await updateProfile({
        ...contact,
        professional_summary: summary,
        target_roles: targetRoles,
        setup_complete: true,
      })
      for (const exp of experience.filter((e) => e.company && e.role)) {
        await createWorkExperience(exp)
      }
      for (const sk of skills.filter((s) => s.name)) {
        await createSkill(sk)
      }
      for (const cert of certs.filter((c) => c.name)) {
        await createCertification(cert)
      }
      router.push('/')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-950 to-brand-800 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Progress bar */}
        <div className="h-1.5 bg-gray-100">
          <div
            className="h-full bg-brand-500 transition-all duration-300"
            style={{ width: `${(step / (steps.length - 1)) * 100}%` }}
          />
        </div>

        <div className="p-8">
          {/* Step indicator */}
          <div className="flex items-center justify-between mb-6">
            <span className="text-xs text-gray-400 font-medium">Step {step + 1} of {steps.length}</span>
            <span className="text-xs font-medium text-brand-600">{steps[step]}</span>
          </div>

          {/* Step content */}
          {step === 0 && <StepWelcome />}
          {step === 1 && <StepContact value={contact} onChange={setContact} />}
          {step === 2 && <StepTargetRoles value={targetRoles} onChange={setTargetRoles} presets={TARGET_ROLES} />}
          {step === 3 && <StepSummary value={summary} onChange={setSummary} />}
          {step === 4 && <StepExperience value={experience} onChange={setExperience} />}
          {step === 5 && <StepSkills value={skills} onChange={setSkills} />}
          {step === 6 && <StepCertifications value={certs} onChange={setCerts} />}
          {step === 7 && <StepPreferences value={style} onChange={setStyle} />}
          {step === 8 && <StepDone />}

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8">
            {step > 0 ? (
              <button onClick={prev} className="btn-secondary">Back</button>
            ) : <div />}

            {step < steps.length - 1 ? (
              <button onClick={next} className="btn-primary">
                {step === 0 ? 'Get Started' : 'Continue'}
              </button>
            ) : (
              <button onClick={finish} disabled={saving} className="btn-primary">
                {saving ? 'Saving...' : 'Finish Setup'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StepWelcome() {
  return (
    <div className="text-center">
      <div className="w-16 h-16 bg-brand-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
        <span className="text-3xl font-bold text-brand-700">CK</span>
      </div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to CareerKit Local</h2>
      <p className="text-gray-500 text-sm leading-relaxed max-w-md mx-auto">
        This wizard will help you build your master profile. It takes about 10 minutes.
        Everything is saved locally on your machine.
      </p>
      <div className="mt-6 grid grid-cols-3 gap-4 text-xs text-gray-500">
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="font-medium text-gray-700 mb-1">100% Local</div>
          Nothing leaves your machine
        </div>
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="font-medium text-gray-700 mb-1">NZ Focused</div>
          CV and cover letter style
        </div>
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="font-medium text-gray-700 mb-1">Cyber Security</div>
          Built for SOC and security roles
        </div>
      </div>
    </div>
  )
}

function StepContact({ value, onChange }: { value: any; onChange: (v: any) => void }) {
  const set = (k: string) => (e: any) => onChange({ ...value, [k]: e.target.value })
  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Contact Details</h2>
      <p className="text-sm text-gray-500 mb-5">These appear at the top of your CV.</p>
      <div className="space-y-4">
        <div className="form-row">
          <div>
            <label className="label">Full Name *</label>
            <input className="input" value={value.full_name} onChange={set('full_name')} placeholder="Jane Smith" />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={value.email} onChange={set('email')} placeholder="jane@example.com" />
          </div>
        </div>
        <div className="form-row">
          <div>
            <label className="label">Phone</label>
            <input className="input" value={value.phone} onChange={set('phone')} placeholder="021 000 0000" />
          </div>
          <div>
            <label className="label">Location</label>
            <input className="input" value={value.location} onChange={set('location')} placeholder="Auckland, New Zealand" />
          </div>
        </div>
        <div className="form-row">
          <div>
            <label className="label">LinkedIn URL</label>
            <input className="input" value={value.linkedin_url} onChange={set('linkedin_url')} placeholder="linkedin.com/in/janesmith" />
          </div>
          <div>
            <label className="label">Website</label>
            <input className="input" value={value.website} onChange={set('website')} placeholder="Optional" />
          </div>
        </div>
        <div>
          <label className="label">NZ Work Rights</label>
          <select className="input" value={value.nz_work_rights} onChange={set('nz_work_rights')}>
            <option>Citizen/PR</option>
            <option>Work Visa</option>
            <option>Student Visa</option>
            <option>Restricted</option>
          </select>
        </div>
      </div>
    </div>
  )
}

function StepTargetRoles({ value, onChange, presets }: { value: string[]; onChange: (v: string[]) => void; presets: string[] }) {
  const toggle = (role: string) => {
    onChange(value.includes(role) ? value.filter((r) => r !== role) : [...value, role])
  }
  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Target Roles</h2>
      <p className="text-sm text-gray-500 mb-5">Which roles are you applying for? Select all that apply.</p>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {presets.map((role) => (
          <button
            key={role}
            type="button"
            onClick={() => toggle(role)}
            className={`px-3 py-2.5 rounded-lg border text-sm text-left transition-colors ${
              value.includes(role)
                ? 'border-brand-500 bg-brand-50 text-brand-800 font-medium'
                : 'border-gray-200 text-gray-600 hover:border-brand-300'
            }`}
          >
            {role}
          </button>
        ))}
      </div>
      <TagInput
        value={value.filter((r) => !presets.includes(r))}
        onChange={(extras) => onChange([...value.filter((r) => presets.includes(r)), ...extras])}
        placeholder="Add a custom role..."
        label="Other roles"
      />
    </div>
  )
}

function StepSummary({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Professional Summary</h2>
      <p className="text-sm text-gray-500 mb-5">
        A few sentences about who you are and what you bring. Write it as you, not as a robot.
        No "results-driven professional" or "passionate about". Just say what you do.
      </p>
      <textarea
        className="textarea"
        rows={6}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g. I'm a security analyst with five years in SOC environments, focused on detection engineering and threat intelligence. I build detections, investigate alerts, and mentor junior analysts. I'm based in Auckland and currently looking for senior SOC or detection engineering roles."
      />
    </div>
  )
}

function StepExperience({ value, onChange }: { value: any[]; onChange: (v: any[]) => void }) {
  const update = (i: number, k: string, v: any) => {
    const next = [...value]
    next[i] = { ...next[i], [k]: v }
    onChange(next)
  }
  const add = () => onChange([...value, {
    company: '', role: '', start_date: '', end_date: '',
    is_current: false, location: '', description: '', key_responsibilities: [], technologies: [],
  }])

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Work History</h2>
      <p className="text-sm text-gray-500 mb-5">Add your most recent roles. You can add more later.</p>
      <div className="space-y-6">
        {value.map((exp, i) => (
          <div key={i} className="p-4 bg-gray-50 rounded-xl space-y-3">
            <div className="form-row">
              <div>
                <label className="label">Company</label>
                <input className="input" value={exp.company} onChange={(e) => update(i, 'company', e.target.value)} placeholder="Acme Corp" />
              </div>
              <div>
                <label className="label">Role Title</label>
                <input className="input" value={exp.role} onChange={(e) => update(i, 'role', e.target.value)} placeholder="SOC Analyst" />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label className="label">Start Date</label>
                <input className="input" value={exp.start_date} onChange={(e) => update(i, 'start_date', e.target.value)} placeholder="Jan 2022" />
              </div>
              <div>
                <label className="label">End Date</label>
                <input className="input" value={exp.end_date} onChange={(e) => update(i, 'end_date', e.target.value)}
                  placeholder="Present" disabled={exp.is_current} />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input type="checkbox" checked={exp.is_current} onChange={(e) => update(i, 'is_current', e.target.checked)} />
              Current role
            </label>
            <div>
              <label className="label">Brief Description</label>
              <textarea className="textarea" rows={2} value={exp.description}
                onChange={(e) => update(i, 'description', e.target.value)}
                placeholder="Key responsibilities and scope of the role" />
            </div>
            <TagInput
              value={exp.technologies}
              onChange={(v) => update(i, 'technologies', v)}
              label="Technologies Used"
              placeholder="Add tool or technology..."
            />
          </div>
        ))}
        <button type="button" onClick={add} className="btn-secondary w-full">+ Add another role</button>
      </div>
    </div>
  )
}

function StepSkills({ value, onChange }: { value: any[]; onChange: (v: any[]) => void }) {
  const update = (i: number, k: string, v: any) => {
    const next = [...value]
    next[i] = { ...next[i], [k]: v }
    onChange(next)
  }
  const add = () => onChange([...value, { name: '', category: 'technical', proficiency: 'proficient', confidence: 'confirmed' }])
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i))

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Skills</h2>
      <p className="text-sm text-gray-500 mb-5">Add your key skills. Be honest about confidence levels.</p>
      <div className="space-y-3">
        {value.map((sk, i) => (
          <div key={i} className="grid grid-cols-12 gap-2 items-center">
            <input className="input col-span-4" value={sk.name} onChange={(e) => update(i, 'name', e.target.value)} placeholder="Skill name" />
            <select className="input col-span-3" value={sk.category} onChange={(e) => update(i, 'category', e.target.value)}>
              <option value="technical">Technical</option>
              <option value="tool">Tool</option>
              <option value="process">Process</option>
              <option value="soft">Soft Skill</option>
            </select>
            <select className="input col-span-3" value={sk.confidence} onChange={(e) => update(i, 'confidence', e.target.value)}>
              <option value="confirmed">Confirmed</option>
              <option value="inferred">Inferred</option>
              <option value="weak">Weak</option>
            </select>
            <button type="button" onClick={() => remove(i)} className="col-span-2 text-red-400 hover:text-red-600 text-sm text-right">Remove</button>
          </div>
        ))}
        <button type="button" onClick={add} className="btn-secondary w-full btn-sm">+ Add skill</button>
      </div>
    </div>
  )
}

function StepCertifications({ value, onChange }: { value: any[]; onChange: (v: any[]) => void }) {
  const update = (i: number, k: string, v: any) => {
    const next = [...value]
    next[i] = { ...next[i], [k]: v }
    onChange(next)
  }
  const add = () => onChange([...value, { name: '', issuer: '', date_obtained: '', in_progress: false }])
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i))

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Certifications</h2>
      <p className="text-sm text-gray-500 mb-5">Add certifications and training. Include in-progress ones.</p>
      <div className="space-y-3">
        {value.map((cert, i) => (
          <div key={i} className="p-3 bg-gray-50 rounded-lg space-y-2">
            <div className="form-row">
              <div>
                <label className="label">Certification Name</label>
                <input className="input" value={cert.name} onChange={(e) => update(i, 'name', e.target.value)} placeholder="CompTIA Security+" />
              </div>
              <div>
                <label className="label">Issuer</label>
                <input className="input" value={cert.issuer} onChange={(e) => update(i, 'issuer', e.target.value)} placeholder="CompTIA" />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label className="label">Date Obtained</label>
                <input className="input" value={cert.date_obtained} onChange={(e) => update(i, 'date_obtained', e.target.value)} placeholder="Mar 2023" />
              </div>
              <div className="flex items-end gap-3 pb-1">
                <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                  <input type="checkbox" checked={cert.in_progress} onChange={(e) => update(i, 'in_progress', e.target.checked)} />
                  In progress
                </label>
                <button type="button" onClick={() => remove(i)} className="text-red-400 hover:text-red-600 text-xs ml-auto">Remove</button>
              </div>
            </div>
          </div>
        ))}
        <button type="button" onClick={add} className="btn-secondary w-full btn-sm">+ Add certification</button>
      </div>
    </div>
  )
}

function StepPreferences({ value, onChange }: { value: any; onChange: (v: any) => void }) {
  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-1">Preferences</h2>
      <p className="text-sm text-gray-500 mb-5">How do you like your CV to read?</p>
      <div className="space-y-4">
        <div>
          <label className="label">Writing Tone</label>
          <select className="input" value={value.tone} onChange={(e) => onChange({ ...value, tone: e.target.value })}>
            <option value="professional">Professional and direct</option>
            <option value="confident">Confident and assertive</option>
            <option value="technical">Technical and precise</option>
          </select>
        </div>
        <div>
          <label className="label">Preferred CV Length</label>
          <select className="input" value={value.preferred_cv_length} onChange={(e) => onChange({ ...value, preferred_cv_length: e.target.value })}>
            <option value="1-page">1 page (Junior roles)</option>
            <option value="2-pages">2 pages (Standard)</option>
            <option value="3-pages">3 pages (Senior/extensive history)</option>
          </select>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
          <p className="font-medium text-gray-700 mb-1">Writing rules already set:</p>
          <ul className="space-y-1 text-xs">
            <li>No em dashes</li>
            <li>No generic AI phrases</li>
            <li>No keyword stuffing</li>
            <li>Direct, human language</li>
            <li>NZ professional tone</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

function StepDone() {
  return (
    <div className="text-center">
      <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
        <span className="text-3xl">✓</span>
      </div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">Profile Created</h2>
      <p className="text-sm text-gray-500 max-w-sm mx-auto">
        Your master profile is set up. You can add more detail at any time from the Profile section.
        Start your first job application whenever you are ready.
      </p>
      <div className="mt-6 grid grid-cols-2 gap-3 text-xs text-gray-500">
        <div className="p-3 bg-gray-50 rounded-lg text-left">
          <div className="font-medium text-gray-700 mb-1">Next: Generate your Master CV</div>
          Go to Master CV and click Generate
        </div>
        <div className="p-3 bg-gray-50 rounded-lg text-left">
          <div className="font-medium text-gray-700 mb-1">Or: Start a job application</div>
          Paste or upload a job description
        </div>
      </div>
    </div>
  )
}
