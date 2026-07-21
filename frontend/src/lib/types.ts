export interface Profile {
  id: number
  full_name: string | null
  email: string | null
  phone: string | null
  location: string | null
  linkedin_url: string | null
  website: string | null
  professional_summary: string | null
  target_roles: string[]
  nz_work_rights: string | null
  setup_complete: boolean
}

export interface WorkExperience {
  id: number
  company: string
  role: string
  start_date: string | null
  end_date: string | null
  is_current: boolean
  location: string | null
  description: string | null
  key_responsibilities: string[]
  technologies: string[]
  order_index: number
}

export interface Skill {
  id: number
  name: string
  category: string | null
  proficiency: string | null
  years_experience: number | null
  confidence: string
  notes: string | null
}

export interface Certification {
  id: number
  name: string
  issuer: string | null
  date_obtained: string | null
  expiry_date: string | null
  credential_id: string | null
  url: string | null
  in_progress: boolean
}

export interface Achievement {
  id: number
  title: string
  situation: string | null
  action: string | null
  result: string | null
  tools_involved: string[]
  skills_demonstrated: string[]
  who_benefited: string | null
  measurable_outcome: string | null
  confidence: string
  bullet_plain: string | null
  bullet_strong: string | null
  bullet_senior: string | null
  bullet_ats: string | null
  source: string | null
  notes: string | null
}

export interface Project {
  id: number
  name: string
  description: string | null
  role: string | null
  technologies: string[]
  outcomes: string | null
  url: string | null
  date_range: string | null
  confidence: string
}

export interface EvidenceItem {
  id: number
  title: string
  description: string | null
  tools_involved: string[]
  skills_demonstrated: string[]
  outcome: string | null
  value: string | null
  confidence: string
  notes: string | null
  source: string | null
}

export interface StylePreferences {
  bullet_style: string
  tone: string
  preferred_cv_length: string
  avoid_phrases: string[]
  preferred_phrases: string[]
  example_bullets: string[]
  notes: string | null
}

export interface ExampleCV {
  id: number
  filename: string
  original_filename: string
  tone: string | null
  bullet_style: string | null
  sections: string[]
  section_order: string[]
  strengths: string[]
  weaknesses: string[]
  layout_ideas: string[]
  formatting_notes: string | null
  created_at: string
}

export interface JobApplication {
  id: number
  company: string | null
  role: string | null
  recruiter_name: string | null
  location: string | null
  work_type: string | null
  salary_range: string | null
  status: string
  applied_date: string | null
  session_folder: string
  job_description_raw: string | null
  job_analysis: JobAnalysis | null
  match_scorecard: MatchScorecard | null
  cover_letter: string | null
  cv_adjustment_notes: string | null
  tailored_cv: string | null
  interview_prep: InterviewPrep | null
  linkedin_angle: string | null
  recruiter_message: string | null
  company_research: string | null
  session_notes: string | null
  created_at: string
  updated_at: string
}

export interface JobApplicationSummary {
  id: number
  company: string | null
  role: string | null
  location: string | null
  work_type: string | null
  status: string
  applied_date: string | null
  created_at: string
  has_analysis: boolean
  has_scorecard: boolean
  has_cover_letter: boolean
  has_interview_prep: boolean
}

export interface JobAnalysis {
  job_title: string
  company: string | null
  recruiter_name: string | null
  location: string
  work_type: string
  salary_range: string | null
  seniority_level: string
  required_skills: string[]
  preferred_skills: string[]
  key_responsibilities: string[]
  repeated_keywords: string[]
  hidden_priorities: string[]
  likely_pain_points: string[]
  likely_screening_criteria: string[]
  likely_interview_themes: string[]
  red_flags: string[]
  notes: string
}

export interface MatchScorecard {
  overall_fit: string
  fit_summary: string
  strong_matches: { skill: string; evidence: string }[]
  partial_matches: { skill: string; gap: string; evidence: string }[]
  quick_learning_gaps: { skill: string; rationale: string }[]
  genuine_gaps: { skill: string; impact: string }[]
  safe_claims: string[]
  claims_needing_review: string[]
  do_not_claim: string[]
  suggested_angle: string
  ats_keywords_to_include: string[]
  overall_recommendation: string
}

export interface InterviewQuestion {
  question: string
  why_likely: string
  concept_explanation?: string
  star_prompt?: string
  suggested_approach?: string
  suggested_framing?: string
}

export interface BrushUpTopic {
  topic: string
  why: string
  what_it_covers?: string
  key_areas?: string[]
  suggested_resources: string
}

export interface InterviewPrep {
  technical_questions: InterviewQuestion[]
  behavioural_questions: InterviewQuestion[]
  scenario_questions: InterviewQuestion[]
  gap_questions: InterviewQuestion[]
  questions_to_ask_recruiter: string[]
  questions_to_ask_employer: string[]
  brush_up_topics: BrushUpTopic[]
  preparation_plan: { day: string; tasks: string[] }[]
  company_research_notes: string
}

export interface ScanSearch {
  id: number
  name: string
  keywords: string
  sites: string[]
  last_scanned: string | null
  created_at: string
}

export interface ScannedJob {
  id: number
  title: string
  company: string | null
  location: string | null
  url: string
  description_snippet: string | null
  date_posted: string | null
  source: string
  source_name: string
  status: 'new' | 'seen' | 'dismissed'
  search_keywords: string | null
  first_seen: string
}

export interface ScanSiteStatus {
  display_name: string
  count: number
  error: string | null
  search_url: string | null
}

export interface ScanResult {
  new_jobs: number
  sites: Record<string, ScanSiteStatus>
  scanned_at: string
}

export interface AIHealth {
  status: string
  url: string
  model: string
  model_available: boolean
  available_models: string[]
  message?: string
}

export interface BrutalReview {
  first_impression: string
  top_third_strength: string
  top_third_notes: string
  target_role_clarity: string
  credibility_rating: string
  credibility_notes: string
  generic_rating: string
  generic_notes: string
  missing_evidence: string[]
  weak_bullets: string[]
  repeated_wording: string[]
  ats_issues: string[]
  readability_issues: string[]
  shortlisting_blockers: string[]
  priority_fixes: { rank: number; issue: string; fix: string }[]
  overall_verdict: string
}
