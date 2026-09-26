const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function apiError(message: string): Error {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('careerkit:api-error', { detail: message }))
  }
  return new Error(message)
}

async function responseError(res: Response): Promise<Error> {
  const body = await res.json().catch(() => ({ detail: res.statusText }))
  return apiError(body.detail || `Request failed with HTTP ${res.status}`)
}

async function safeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init)
  } catch {
    throw apiError('Cannot reach the CareerKit API. Check that the backend is running on port 8000.')
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await safeFetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    throw await responseError(res)
  }
  return res.json()
}

// Health
export const health = () => request('/api/health')
export const aiHealth = () => request('/api/ai/health')

// Settings
export const getSettings = () => request('/api/settings')
export const updateSettings = (data: object) =>
  request('/api/settings', { method: 'PUT', body: JSON.stringify(data) })

// Profile
export const getProfile = () => request('/api/profile')
export const updateProfile = (data: object) =>
  request('/api/profile', { method: 'PUT', body: JSON.stringify(data) })

export const getWorkExperience = () => request('/api/profile/work-experience')
export const createWorkExperience = (data: object) =>
  request('/api/profile/work-experience', { method: 'POST', body: JSON.stringify(data) })
export const updateWorkExperience = (id: number, data: object) =>
  request(`/api/profile/work-experience/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteWorkExperience = (id: number) =>
  request(`/api/profile/work-experience/${id}`, { method: 'DELETE' })

export const getSkills = () => request('/api/profile/skills')
export const createSkill = (data: object) =>
  request('/api/profile/skills', { method: 'POST', body: JSON.stringify(data) })
export const updateSkill = (id: number, data: object) =>
  request(`/api/profile/skills/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteSkill = (id: number) =>
  request(`/api/profile/skills/${id}`, { method: 'DELETE' })

export const getCertifications = () => request('/api/profile/certifications')
export const createCertification = (data: object) =>
  request('/api/profile/certifications', { method: 'POST', body: JSON.stringify(data) })
export const updateCertification = (id: number, data: object) =>
  request(`/api/profile/certifications/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteCertification = (id: number) =>
  request(`/api/profile/certifications/${id}`, { method: 'DELETE' })

export const getAchievements = () => request('/api/profile/achievements')
export const createAchievement = (data: object) =>
  request('/api/profile/achievements', { method: 'POST', body: JSON.stringify(data) })
export const updateAchievement = (id: number, data: object) =>
  request(`/api/profile/achievements/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteAchievement = (id: number) =>
  request(`/api/profile/achievements/${id}`, { method: 'DELETE' })
export const generateBullets = (data: object) =>
  request('/api/profile/achievements/generate-bullets', { method: 'POST', body: JSON.stringify(data) })

export const getProjects = () => request('/api/profile/projects')
export const createProject = (data: object) =>
  request('/api/profile/projects', { method: 'POST', body: JSON.stringify(data) })
export const updateProject = (id: number, data: object) =>
  request(`/api/profile/projects/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteProject = (id: number) =>
  request(`/api/profile/projects/${id}`, { method: 'DELETE' })

export const getEvidence = () => request('/api/profile/evidence')
export const createEvidence = (data: object) =>
  request('/api/profile/evidence', { method: 'POST', body: JSON.stringify(data) })
export const updateEvidence = (id: number, data: object) =>
  request(`/api/profile/evidence/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteEvidence = (id: number) =>
  request(`/api/profile/evidence/${id}`, { method: 'DELETE' })

export const getStyle = () => request('/api/profile/style')
export const updateStyle = (data: object) =>
  request('/api/profile/style', { method: 'PUT', body: JSON.stringify(data) })

export const getTraining = () => request('/api/profile/training')
export const createTraining = (data: object) =>
  request('/api/profile/training', { method: 'POST', body: JSON.stringify(data) })
export const updateTraining = (id: number, data: object) =>
  request(`/api/profile/training/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteTraining = (id: number) =>
  request(`/api/profile/training/${id}`, { method: 'DELETE' })

export const getCommunity = () => request('/api/profile/community')
export const createCommunity = (data: object) =>
  request('/api/profile/community', { method: 'POST', body: JSON.stringify(data) })
export const updateCommunity = (id: number, data: object) =>
  request(`/api/profile/community/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteCommunity = (id: number) =>
  request(`/api/profile/community/${id}`, { method: 'DELETE' })

// CV
export const getCurrentCV = () => request('/api/cv/current')
export const getCVVersions = () => request('/api/cv/versions')
export const generateCV = (mode: string = 'cv_safe') => request(`/api/cv/generate?mode=${mode}`, { method: 'POST' })
export const saveCV = (data: object) =>
  request('/api/cv/save', { method: 'POST', body: JSON.stringify(data) })
export const brutalReview = () => request('/api/cv/review', { method: 'POST' })
export const checkATSHealth = () => request('/api/cv/ats-check', { method: 'POST' })
export const exportCV = (fmt: string) => `${API_BASE}/api/cv/export/${fmt}`

// Examples
export const getExamples = () => request('/api/examples')
export const deleteExample = (id: number) =>
  request(`/api/examples/${id}`, { method: 'DELETE' })
export const uploadExample = async (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  const res = await safeFetch(`${API_BASE}/api/examples/upload`, { method: 'POST', body: fd })
  if (!res.ok) {
    throw await responseError(res)
  }
  return res.json()
}

// Applications
export const getApplications = () => request('/api/applications')
export const getApplication = (id: number) => request(`/api/applications/${id}`)
export const createApplication = (data: object) =>
  request('/api/applications', { method: 'POST', body: JSON.stringify(data) })
export const updateApplication = (id: number, data: object) =>
  request(`/api/applications/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteApplication = (id: number) =>
  request(`/api/applications/${id}`, { method: 'DELETE' })

export const uploadJobDescription = async (id: number, file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  const res = await safeFetch(`${API_BASE}/api/applications/${id}/upload-jd`, { method: 'POST', body: fd })
  if (!res.ok) {
    throw await responseError(res)
  }
  return res.json()
}

export const analyzeJob = (id: number) =>
  request(`/api/applications/${id}/analyze`, { method: 'POST' })
export const generateScorecard = (id: number) =>
  request(`/api/applications/${id}/scorecard`, { method: 'POST' })
export const generateJobMatch = (id: number) =>
  request(`/api/applications/${id}/job-match`, { method: 'POST' })
export const generateCustomCV = (id: number, selectedFixes: string[]) =>
  request(`/api/applications/${id}/custom-cv`, { method: 'POST', body: JSON.stringify({ selected_fixes: selectedFixes }) })

// Master CV Feedback Loop
export const getSkillGaps = () => request('/api/insights/skill-gaps')
export const generateCoverLetter = (id: number) =>
  request(`/api/applications/${id}/cover-letter`, { method: 'POST' })
export const generateCVNotes = (id: number) =>
  request(`/api/applications/${id}/cv-notes`, { method: 'POST' })
export const generateInterviewPrep = (id: number) =>
  request(`/api/applications/${id}/interview-prep`, { method: 'POST' })
export const generateLinkedInAngle = (id: number) =>
  request(`/api/applications/${id}/linkedin`, { method: 'POST' })
export const generateTailoredCV = (id: number) =>
  request(`/api/applications/${id}/tailored-cv`, { method: 'POST' })
export const exportApplication = (id: number, fmt: string, section: string) =>
  `${API_BASE}/api/applications/${id}/export/${fmt}?section=${section}`

// Reach Outs
export const getReachOuts = () => request('/api/reachouts')
export const getReachOut = (id: number) => request(`/api/reachouts/${id}`)
export const createReachOut = (data: object) =>
  request('/api/reachouts', { method: 'POST', body: JSON.stringify(data) })
export const updateReachOut = (id: number, data: object) =>
  request(`/api/reachouts/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteReachOut = (id: number) =>
  request(`/api/reachouts/${id}`, { method: 'DELETE' })
export const generateReachOutLetter = (id: number) =>
  request(`/api/reachouts/${id}/generate-letter`, { method: 'POST' })
export const exportReachOut = (id: number, fmt: string, section: string) =>
  `${API_BASE}/api/reachouts/${id}/export/${fmt}?section=${section}`

// LinkedIn
export const generateLinkedIn = () => request('/api/linkedin/generate', { method: 'POST' })

// Scanner
export const getScanSearches = () => request('/api/scanner/searches')
export const createScanSearch = (data: object) =>
  request('/api/scanner/searches', { method: 'POST', body: JSON.stringify(data) })
export const deleteScanSearch = (id: number) =>
  request(`/api/scanner/searches/${id}`, { method: 'DELETE' })
export const runScan = (searchId: number) =>
  request('/api/scanner/scan', { method: 'POST', body: JSON.stringify({ search_id: searchId }) })
export const getScannedJobs = (params?: { status?: string; source?: string }) => {
  const qs = params ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]).toString() : ''
  return request(`/api/scanner/jobs${qs}`)
}
export const updateJobStatus = (id: number, status: string) =>
  request(`/api/scanner/jobs/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) })
export const startApplicationFromJob = (id: number) =>
  request(`/api/scanner/jobs/${id}/apply`, { method: 'POST' })
