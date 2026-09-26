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
  employer_public_name: string | null
  role: string
  alternative_titles: string[]
  start_date: string | null
  end_date: string | null
  is_current: boolean
  location: string | null
  description: string | null
  key_responsibilities: string[]
  technologies: string[]
  order_index: number
  confidentiality_level: string
}

export interface Skill {
  id: number
  name: string
  aliases: string[]
  category: string | null
  proficiency: string | null
  years_experience: number | null
  last_used: string | null
  production_experience: boolean
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
  status: string
  notes: string | null
}

export interface Training {
  id: number
  title: string
  provider: string | null
  date: string | null
  delivery_type: string | null
  duration: string | null
  completion_status: string
  related_certification: string | null
  tools: string[]
  skills: string[]
  evidence: string | null
  include_by_default: boolean
  confidence: string
  notes: string | null
}

export interface CommunityInvolvement {
  id: number
  event: string
  location: string | null
  date: string | null
  participation_type: string
  notes: string | null
  evidence: string | null
  include_on_cv: boolean
  include_on_linkedin: boolean
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
  confidentiality_level: string
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
  confidentiality_level: string
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
  confidentiality_level: string
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
  job_match_result: JobMatchResult | null
  cover_letter: string | null
  cv_adjustment_notes: string | null
  tailored_cv: string | null
  custom_cv: string | null
  custom_cv_fixes_applied: string[] | null
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
  has_job_match: boolean
  has_cover_letter: boolean
  has_interview_prep: boolean
  job_match_score: number | null
  job_match_band: string | null
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

// --- CV Match Report (Job Match engine) ---

export type EvidenceLevel = 'EXPLICIT' | 'INFERRED' | 'POSSIBLE' | 'NOT_FOUND'
export type Coverage = 'STRONG_EVIDENCE' | 'PARTIAL_EVIDENCE' | 'NO_EVIDENCE' | 'UNKNOWN'
export type RequirementImportance = 'critical' | 'important' | 'desirable'
export type RequirementType =
  | 'hard_skill' | 'tool' | 'methodology' | 'responsibility' | 'certification' | 'industry' | 'soft_skill'
export type TitleMatchState = 'EXACT_MATCH' | 'STRONG_EQUIVALENT' | 'RELATED_TITLE' | 'WEAK_ALIGNMENT' | 'NO_ALIGNMENT'
export type RecommendationTier = 'SAFE_OPTIMISATION' | 'EVIDENCE_NEEDED' | 'DO_NOT_ADD'

export interface SubScore {
  score: number | null
  requirement_count: number
}

export interface JobMatchScore {
  overall: number
  band: string
  sub_scores: {
    hard_skills: SubScore
    experience_seniority: SubScore
    qualifications: SubScore
    soft_skills: SubScore
    industry_context: SubScore
    job_title: SubScore
  }
}

export interface TitleMatch {
  state: TitleMatchState
  matched_title: string | null
  explanation: string
  job_title: string
}

export interface RequirementCoverageRow {
  name: string
  type: RequirementType
  importance: RequirementImportance
  coverage: Coverage
  icon: string
  label: string
  sources: string[]
  rationale: string
}

export interface HardSkillRow {
  skill: string
  importance: RequirementImportance
  coverage: Coverage
  assessment: string
  sources: string[]
}

export interface KeywordCoverage {
  matched: number
  partial: number
  missing: number
  total: number
  coverage_pct: number
  by_category: Record<string, { matched: number; partial: number; missing: number }>
}

export interface PriorityFix {
  requirement: string
  type: string
  importance: RequirementImportance
  coverage: Coverage
  tier: RecommendationTier
  severity: 'critical' | 'high' | 'medium' | 'low'
  message: string
}

export interface JobMatchResult {
  job_match: JobMatchScore
  title_match: TitleMatch
  ats_check: AtsCheckResult | null
  recruiter_readiness: RecruiterReadinessScore | null
  requirement_coverage: RequirementCoverageRow[]
  hard_skills: HardSkillRow[]
  keyword_coverage: KeywordCoverage
  priority_fixes: { top: PriorityFix[]; more: PriorityFix[] }
  requirements_by_importance: { critical: string[]; important: string[]; desirable: string[] }
}

export interface CustomCvScores {
  job_match: number
  ats_check: number | null
  recruiter_readiness: number | null
}

export interface CustomCvResult {
  custom_cv: string
  selection_summary: string
  before: CustomCvScores
  after: CustomCvScores
  ats_check: AtsCheckResult
  recruiter_readiness: RecruiterReadinessScore | null
}

// --- Master CV Feedback Loop ---

export interface SkillGap {
  skill: string
  appearances: number
  weak_count: number
  sample_roles: string[]
}

export interface SkillGapsResult {
  skill_gaps: SkillGap[]
  applications_considered: number
}

// --- ATS Compatibility (Master CV Health Check) ---

export type CheckStatus = 'pass' | 'warn' | 'fail' | 'info'

export interface AtsCheck {
  id: string
  category: 'content' | 'document'
  label: string
  status: CheckStatus
  detail: string
  weight: number
}

export interface AtsCheckResult {
  score: number
  band: string
  content_checks: AtsCheck[]
  document_checks: AtsCheck[]
  ats_parsed_view?: string
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

export interface ReachOut {
  id: number
  company_name: string
  website_url: string | null
  linkedin_url: string | null
  industry: string | null
  location: string | null
  company_size: string | null
  research_summary: string | null
  culture_notes: string | null
  tech_security_notes: string | null
  recent_news: string | null
  angle: string | null
  contact_name: string | null
  contact_role: string | null
  contact_email: string | null
  status: string
  date_identified: string | null
  date_sent: string | null
  follow_up_date: string | null
  intro_letter: string | null
  cv_notes: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ReachOutSummary {
  id: number
  company_name: string
  industry: string | null
  location: string | null
  status: string
  date_identified: string | null
  date_sent: string | null
  follow_up_date: string | null
  created_at: string
  has_research: boolean
  has_letter: boolean
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
  readiness?: RecruiterReadinessScore
}

export interface RecruiterReadinessScore {
  score: number
  band: string
  sub_scores: {
    first_impression: number
    credibility: number
    achievement_quality: number
    readability: number
    shortlisting_readiness: number
  }
}
